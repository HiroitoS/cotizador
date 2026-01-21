from rest_framework import serializers
from .models import (
    Editorial,
    Producto,
    InstitucionEducativa,
    AsesorComercial,
    Cotizacion,
    DetalleCotizacion,
    Adopcion,
    DetalleAdopcion,
    Pedido,
    DetallePedido,
)


# ==========================
# EDITORIALES / PRODUCTOS
# ==========================
class EditorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Editorial
        fields = ["id", "nombre", "estado"]


class ProductoSerializer(serializers.ModelSerializer):
    editorial_nombre = serializers.CharField(source="editorial.nombre", read_only=True)

    # alias para compatibilidad con frontend
    pvp_2026_con_igv = serializers.DecimalField(
        source="pvp_2026", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Producto
        fields = [
            "id",
            "editorial",
            "editorial_nombre",
            "codigo",
            "nombre",
            "nivel",
            "grado",
            "area",
            "serie",
            "pvp_2026",
            "pvp_2026_con_igv",
            "descuento_proveedor",
            "precio_proveedor",
            "estado",
        ]


# ==========================
# MAESTROS
# ==========================
class InstitucionEducativaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitucionEducativa
        fields = "__all__"


class AsesorComercialSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsesorComercial
        fields = "__all__"


# ==========================
# COTIZACIONES
# ==========================
class DetalleCotizacionSerializer(serializers.ModelSerializer):
    # Info producto
    producto_id = serializers.IntegerField(source="producto.id", read_only=True)
    descripcion = serializers.CharField(source="producto.nombre", read_only=True)
    area = serializers.CharField(source="producto.area", read_only=True)
    grado = serializers.CharField(source="producto.grado", read_only=True)
    nivel = serializers.CharField(source="producto.nivel", read_only=True)
    editorial = serializers.CharField(source="producto.editorial.nombre", read_only=True)
    pvp_2026_con_igv = serializers.DecimalField(
        source="producto.pvp_2026", max_digits=10, decimal_places=2, read_only=True
    )

    # tu tabla usa:
    utilidad_be_x_un = serializers.SerializerMethodField()
    roi_percent = serializers.SerializerMethodField()

    def get_utilidad_be_x_un(self, obj):
        # En tu backend guardas compatibilidad histórica:
        # roi_ie = utilidad BE x unidad
        return obj.roi_ie

    def get_roi_percent(self, obj):
        try:
            if obj.precio_proveedor and obj.precio_proveedor > 0:
                return (obj.roi_ie / obj.precio_proveedor) * 100
        except Exception:
            pass
        return 0

    class Meta:
        model = DetalleCotizacion
        fields = [
            "id",
            "cotizacion",
            "producto",
            "producto_id",
            "descripcion",
            "area",
            "grado",
            "nivel",
            "editorial",
            "pvp_2026_con_igv",
            "cantidad",
            "precio_be",
            "desc_proveedor",
            "precio_proveedor",
            "descuento_ie",
            "precio_ie",
            "precio_ppff",
            "utilidad_ie",
            "roi_ie",
            "utilidad_be_x_un",
            "roi_percent",
            "tipo_venta",
        ]


class CotizacionSerializer(serializers.ModelSerializer):
    institucion_nombre = serializers.CharField(source="institucion.nombre", read_only=True)
    asesor_nombre = serializers.CharField(source="asesor.nombre", read_only=True)
    detalles = DetalleCotizacionSerializer(many=True, read_only=True)

    # ✅ Para mostrar tipo de venta también en detalle
    tipo_venta = serializers.SerializerMethodField()

    def get_tipo_venta(self, obj):
        det = obj.detalles.first()
        return det.tipo_venta if det else ""

    class Meta:
        model = Cotizacion
        fields = [
            "id",
            "numero_cotizacion",
            "institucion",
            "institucion_nombre",
            "asesor",
            "asesor_nombre",
            "fecha",
            "estado",
            "motivo_rechazo",
            "tipo_venta",
            "detalles",
        ]


class CotizacionListSerializer(serializers.ModelSerializer):
    institucion = serializers.CharField(source="institucion.nombre", read_only=True)
    asesor = serializers.CharField(source="asesor.nombre", read_only=True)

    # ✅ Panel pide tipo_venta pero no existe en Cotizacion: lo calculamos
    tipo_venta = serializers.SerializerMethodField()

    def get_tipo_venta(self, obj):
        det = obj.detalles.first()
        return det.tipo_venta if det else ""

    class Meta:
        model = Cotizacion
        fields = [
            "id",
            "numero_cotizacion",
            "institucion",
            "asesor",
            "fecha",
            "estado",
            "tipo_venta",
        ]


# ==========================
# ADOPCIONES
# ==========================
class DetalleAdopcionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    area = serializers.CharField(source="producto.area", read_only=True)
    grado = serializers.CharField(source="producto.grado", read_only=True)
    pvp_2026 = serializers.DecimalField(
        source="producto.pvp_2026", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = DetalleAdopcion
        fields = [
            "id",
            "adopcion",
            "producto",
            "producto_nombre",
            "area",
            "grado",
            "pvp_2026",
            "cantidad_adoptada",
            "mes_lectura",
        ]


class AdopcionSerializer(serializers.ModelSerializer):
    numero_cotizacion = serializers.CharField(source="cotizacion.numero_cotizacion", read_only=True)
    institucion = serializers.CharField(source="cotizacion.institucion.nombre", read_only=True)
    asesor = serializers.CharField(source="cotizacion.asesor.nombre", read_only=True)
    detalles = DetalleAdopcionSerializer(many=True, read_only=True)

    # ✅ Alias que el frontend está usando (a.fecha)
    fecha = serializers.DateField(source="fecha_adopcion", read_only=True)

    # ✅ tipo_venta para panel adopciones
    tipo_venta = serializers.SerializerMethodField()

    def get_tipo_venta(self, obj):
        det = obj.cotizacion.detalles.first()
        return det.tipo_venta if det else ""

    class Meta:
        model = Adopcion
        fields = [
            "id",
            "cotizacion",
            "numero_cotizacion",
            "institucion",
            "asesor",
            "fecha_adopcion",
            "fecha",
            "cantidad_total",
            "tipo_venta",
            "detalles",
        ]


# ==========================
# PEDIDOS
# ==========================
class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetallePedido
        fields = ["id", "pedido", "producto", "producto_nombre", "cantidad", "precio_proveedor"]


class PedidoSerializer(serializers.ModelSerializer):
    numero_cotizacion = serializers.CharField(source="adopcion.cotizacion.numero_cotizacion", read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = ["id", "adopcion", "numero_cotizacion", "fecha_pedido", "estado", "detalles"]


# =========================================================
# ✅ Serializers extra para API V2 (para que NO reviente api_v2.py)
# =========================================================

class ProductoCatalogoSerializer(serializers.ModelSerializer):
    editorial_id = serializers.IntegerField(source="editorial.id", read_only=True)
    editorial_nombre = serializers.CharField(source="editorial.nombre", read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id",
            "codigo",
            "nombre",
            "nivel",
            "area",
            "grado",
            "serie",
            "pvp_2026",
            "editorial_id",
            "editorial_nombre",
        ]


# Aliases que api_v2.py importa
CotizacionPanelSerializer = CotizacionListSerializer
CotizacionDetalleSerializer = CotizacionSerializer
AdopcionPanelSerializer = AdopcionSerializer
