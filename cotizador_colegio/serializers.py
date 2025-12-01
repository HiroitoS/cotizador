from rest_framework import serializers
from .models import (
    Libro,
    Cotizacion,
    DetalleCotizacion,
    InstitucionEducativa,
    AsesorComercial,
    Adopcion,
    DetalleAdopcion,
    Pedido,
)

# ------------------------------------------------------------------------
# LIBROS
# ------------------------------------------------------------------------
class LibroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = [
            "id",
            "empresa",
            "nivel",
            "grado",
            "area",
            "serie",
            "descripcion_completa",
            "soporte",
            "pvp_2026_con_igv",
        ]


# ------------------------------------------------------------------------
# PANEL COTIZACIONES
# ------------------------------------------------------------------------
class CotizacionPanelSerializer(serializers.ModelSerializer):
    institucion = serializers.CharField(source="institucion.nombre", read_only=True)
    asesor = serializers.CharField(source="asesor.nombre", read_only=True)
    tipo_venta = serializers.SerializerMethodField()

    class Meta:
        model = Cotizacion
        fields = ["id", "numero_cotizacion", "institucion", "asesor", "tipo_venta", "fecha", "estado"]

    def get_tipo_venta(self, obj):
        """
        Obtenemos tipo_venta del primer detalle (en BD está en DetalleCotizacion).
        Mapea a: PUNTO_DE_VENTA | FERIA | CONSIGNA | — cuando no hay detalles.
        """
        det = obj.detalles.first()
        if not det:
            return "—"

        tv = (det.tipo_venta or "").upper().strip()
        if tv in ("PV", "PUNTO_DE_VENTA", "PUNTO DE VENTA"):
            return "PUNTO_DE_VENTA"
        if tv == "FERIA":
            return "FERIA"
        if tv == "CONSIGNA":
            return "CONSIGNA"
        return "—"


# ------------------------------------------------------------------------
# DETALLES PARA APROBAR (MODAL ADOPCIÓN)
# ------------------------------------------------------------------------
class DetalleCotizacionAdopcionSerializer(serializers.ModelSerializer):
    libro_id = serializers.IntegerField(source="libro.id", read_only=True)
    pvp_2026_con_igv = serializers.DecimalField(max_digits=10, decimal_places=2, source="libro.pvp_2026_con_igv", read_only=True)
    tipo_venta = serializers.CharField(read_only=True)


    descripcion = serializers.CharField(source="libro.descripcion_completa", read_only=True)
    area = serializers.CharField(source="libro.area", read_only=True)
    grado = serializers.CharField(source="libro.grado", read_only=True)
    es_plan_lector = serializers.SerializerMethodField()

    class Meta:
        model = DetalleCotizacion
        fields = [
            "id",
            "libro_id",
            "tipo_venta",
            "pvp_2026_con_igv",
            "descripcion",
            "area",
            "grado",
            "es_plan_lector",
        ]

    def get_es_plan_lector(self, obj):
        a = obj.libro.area or ""
        return "lector" in a.lower()



class CotizacionDetalleSerializer(serializers.ModelSerializer):
    """
    Serializer que usa el modal de aprobación:
    trae cabecera (institución/asesor/fecha) + lista de libros con flag plan lector.
    """
    institucion = serializers.CharField(source="institucion.nombre", read_only=True)
    asesor = serializers.CharField(source="asesor.nombre", read_only=True)
    detalles = serializers.SerializerMethodField()

    class Meta:
        model = Cotizacion
        fields = ["id", "numero_cotizacion", "institucion", "asesor", "fecha", "detalles"]

    def get_detalles(self, obj):
        qs = obj.detalles.select_related("libro").all()
        return DetalleCotizacionAdopcionSerializer(qs, many=True).data


# ------------------------------------------------------------------------
# COTIZACIÓN (DETALLE PARA PDF/VER)
# Encabezados según modalidad (PV/FERIA vs CONSIGNA)
# ------------------------------------------------------------------------
class DetalleParaPDFSerializer(serializers.ModelSerializer):
    # columnas comunes
    empresa = serializers.CharField(source="libro.empresa", read_only=True)
    nivel = serializers.CharField(source="libro.nivel", read_only=True)
    grado = serializers.CharField(source="libro.grado", read_only=True)
    area = serializers.CharField(source="libro.area", read_only=True)
    descripcion_completa = serializers.CharField(source="libro.descripcion_completa", read_only=True)
    pvp_2026_con_igv = serializers.DecimalField(max_digits=10, decimal_places=2, source="libro.pvp_2026_con_igv", read_only=True)

    # PV / FERIA
    precio_ie = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    precio_ppff = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    utilidad_ie = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    # CONSIGNA
    desc_consigna = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    precio_consigna = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = DetalleCotizacion
        fields = [
            # comunes
            "empresa", "nivel", "grado", "area", "descripcion_completa", "pvp_2026_con_igv",
            # pv/feria
            "precio_ie", "precio_ppff", "utilidad_ie",
            # consigna
            "desc_consigna", "precio_consigna",
        ]


class CotizacionSerializer(serializers.ModelSerializer):
    """
    Para ver/descargar PDF de la cotización con sus detalles ya formateados.
    """
    institucion = serializers.CharField(source="institucion.nombre", read_only=True)
    asesor = serializers.CharField(source="asesor.nombre", read_only=True)
    tipo_venta = serializers.SerializerMethodField()
    detalles = DetalleParaPDFSerializer(many=True, source="detalles")

    class Meta:
        model = Cotizacion
        fields = [
            "id", "numero_cotizacion", "institucion", "asesor", "fecha", "estado",
            "tipo_venta", "detalles"
        ]

    def get_tipo_venta(self, obj):
        det = obj.detalles.first()
        if not det:
            return "—"
        tv = (det.tipo_venta or "").upper().strip()
        if tv in ("PV", "PUNTO_DE_VENTA", "PUNTO DE VENTA"):
            return "PUNTO_DE_VENTA"
        if tv == "FERIA":
            return "FERIA"
        if tv == "CONSIGNA":
            return "CONSIGNA"
        return "—"


# ------------------------------------------------------------------------
# ADOPCIONES (PANEL)
# ------------------------------------------------------------------------
class AdopcionPanelSerializer(serializers.ModelSerializer):
    numero_cotizacion = serializers.CharField(source="cotizacion.numero_cotizacion", read_only=True)
    institucion = serializers.CharField(source="cotizacion.institucion.nombre", read_only=True)
    asesor = serializers.CharField(source="cotizacion.asesor.nombre", read_only=True)
    tipo_venta = serializers.SerializerMethodField()
    fecha = serializers.SerializerMethodField()

    class Meta:
        model = Adopcion
        fields = [
            "id",
            "numero_cotizacion",
            "institucion",
            "asesor",
            "tipo_venta",
            "fecha",
            "modalidad",
            "cantidad_total",
        ]

    def get_tipo_venta(self, obj):
        """Lee el tipo de venta desde el primer detalle de la cotización."""
        det = obj.cotizacion.detalles.first()
        if not det:
            return "—"

        MAPEO = {
            "PV": "Punto de Venta",
            "PUNTO_DE_VENTA": "Punto de Venta",
            "PUNTO DE VENTA": "Punto de Venta",
            "FERIA": "Feria",
            "CONSIGNA": "Consignación",
        }

        clave = (det.tipo_venta or "").upper().strip()
        return MAPEO.get(clave, clave)

    def get_fecha(self, obj):
        return obj.fecha_adopcion.strftime("%d/%m/%Y")



# ------------------------------------------------------------------------
# PEDIDOS (B - mantener)
# ------------------------------------------------------------------------
class PedidoSerializer(serializers.ModelSerializer):
    numero_cotizacion = serializers.CharField(source="adopcion.cotizacion.numero_cotizacion", read_only=True)
    institucion = serializers.CharField(source="adopcion.cotizacion.institucion.nombre", read_only=True)

    class Meta:
        model = Pedido
        fields = ["id", "numero_cotizacion", "institucion", "fecha_pedido", "estado"]
# ------------------------------------------------------------------------
# ASESORES / INSTITUCIONES (faltaban)
# ------------------------------------------------------------------------
class AsesorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsesorComercial
        fields = ["id", "nombre", "correo", "telefono", "estado"]


class InstitucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitucionEducativa
        fields = ["id", "nombre", "codigo_modular", "direccion", "distrito", "provincia", "departamento"]
