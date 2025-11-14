# cotizador_colegio/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
# --------------------------
# Enumeraciones profesionales
# --------------------------
class TipoVenta(models.TextChoices):
    FERIA = "FERIA", "Feria"
    CONSIGNA = "CONSIGNA", "Consignación"
    PUNTO_DE_VENTA = "PUNTO_DE_VENTA", "Punto de Venta"

class EstadoCotizacion(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    ENVIADA = "ENVIADA", "Enviada"
    APROBADA = "APROBADA", "Aprobada"
    ADOPTADA = "ADOPTADA", "Adoptada"
    RECHAZADA = "RECHAZADA", "Rechazada"

class EstadoPedido(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    EMITIDO = "EMITIDO", "Emitido"
    ENVIADO = "ENVIADO", "Enviado a proveedor"
    CONFIRMADO = "CONFIRMADO", "Confirmado por proveedor"
    CANCELADO = "CANCELADO", "Cancelado"

# =====================================================
#  LIBRO
# =====================================================
class Libro(models.Model):
    empresa = models.CharField(max_length=100)
    nivel = models.CharField(max_length=50)
    grado = models.CharField(max_length=50)
    area = models.CharField(max_length=100)
    serie = models.CharField(max_length=100, blank=True, null=True)
    descripcion_completa = models.TextField()
    tipo_inventario = models.CharField(max_length=50, blank=True, null=True)
    soporte = models.CharField(max_length=50, blank=True, null=True)
    pvp_2026_con_igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    año_catalogo = models.CharField(max_length=10, blank=True, null=True)
    isbn = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "libros"
        verbose_name = "Libro"
        verbose_name_plural = "Libros"
        indexes = [
            models.Index(fields=["empresa", "nivel", "grado", "area"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.descripcion_completa}"

# =====================================================
#  INSTITUCIÓN EDUCATIVA
# =====================================================
class InstitucionEducativa(models.Model):
    nombre = models.CharField(max_length=200)
    codigo_modular = models.CharField(max_length=50, blank=True, null=True)
    nivel_educativo = models.CharField(max_length=150, blank=True, null=True)
    direccion = models.CharField(max_length=250, blank=True, null=True)
    distrito = models.CharField(max_length=100, blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    departamento = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    correo_institucional = models.EmailField(blank=True, null=True)
    director = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        db_table = "instituciones_educativas"
    def __str__(self): return self.nombre

# =====================================================
#  ASESOR COMERCIAL
# =====================================================
class AsesorComercial(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    zona = models.CharField(max_length=100, blank=True, null=True)
    empresa_editorial = models.CharField(max_length=150, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    cargo = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=[("ACTIVO", "Activo"), ("INACTIVO", "Inactivo")],
        default="ACTIVO",
    )

    class Meta:
        db_table = "asesores_comerciales"
    def __str__(self): return f"{self.nombre} ({self.empresa_editorial or 'Sin Editorial'})"

# =====================================================
#  COTIZACIÓN
# =====================================================
class Cotizacion(models.Model):
    numero_cotizacion = models.CharField(max_length=20, unique=True, blank=True, null=True)
    institucion = models.ForeignKey("InstitucionEducativa", on_delete=models.PROTECT, related_name="cotizaciones")
    asesor = models.ForeignKey("AsesorComercial", on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADA", "Aprobada"),
        ("RECHAZADA", "Rechazada"),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")
    motivo_rechazo = models.TextField(blank=True, null=True, verbose_name="Motivo de rechazo")

    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "cotizaciones"

    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            last = Cotizacion.objects.all().order_by("id").last()
            new_number = (last.id + 1) if last else 1
            self.numero_cotizacion = f"COT-{str(new_number).zfill(5)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero_cotizacion or f"Sin número"

# =====================================================
#  DETALLE DE COTIZACIÓN (con cálculos automáticos)
# =====================================================
class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, related_name="detalles", on_delete=models.CASCADE)
    libro = models.ForeignKey("Libro", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)

    # valores ingresados
    precio_be = models.DecimalField(max_digits=10, decimal_places=2)
    desc_proveedor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_ie = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_ppff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    desc_consigna = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comision = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    precio_proveedor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_consigna = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_coordinado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    utilidad_ie = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    roi_ie = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    roi_consigna = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    tipo_venta = models.CharField(max_length=20, choices=TipoVenta.choices)


    class Meta:
        db_table = "detalle_cotizacion"

    def compute_metrics(self):
        ZERO = Decimal("0")

        # Asegurar decimales
        precio_be = Decimal(str(self.precio_be or 0))
        desc_prov = Decimal(str(self.desc_proveedor or 0)) / Decimal("100")
        precio_ppff = Decimal(str(self.precio_ppff or 0)) if self.precio_ppff else None
        precio_ie = Decimal(str(self.precio_ie or 0)) if self.precio_ie else None
        desc_consg = Decimal(str(self.desc_consigna or 0)) / Decimal("100") if self.desc_consigna else None
        comision = Decimal(str(self.comision or 0)) if self.comision else None

        # PRECIO PROVEEDOR
        self.precio_proveedor = (precio_be * (1 - desc_prov)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # PV / FERIA -------------------------------------
        if self.tipo_venta in ("PV", "FERIA"):
            if precio_ie is not None and precio_ppff is not None:
                utilidad = (precio_ppff - precio_ie)
                self.utilidad_ie = utilidad.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                self.roi_ie = (precio_ie - self.precio_proveedor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            self.precio_consigna = None
            self.precio_coordinado = None
            self.roi_consigna = None

        # CONSIGNA --------------------------------------
        elif self.tipo_venta == "CONSIGNA":
            if desc_consg is not None:
                self.precio_consigna = (precio_be * (1 - desc_consg)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                com_monto = comision.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                self.precio_coordinado = (self.precio_consigna - com_monto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                self.utilidad_ie = (precio_be - self.precio_consigna).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                self.roi_consigna = (self.precio_coordinado - self.precio_proveedor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            self.roi_ie = None

    def save(self, *args, **kwargs):
        self.compute_metrics()
        super().save(*args, **kwargs)

# =====================================================
#  ADOPCIÓN
# =====================================================
class Adopcion(models.Model):
    cotizacion = models.OneToOneField(Cotizacion, on_delete=models.PROTECT, related_name="adopcion")
    fecha_adopcion = models.DateField(auto_now_add=True)
    modalidad = models.CharField(max_length=50, blank=True, null=True)
    observaciones_finales = models.TextField(blank=True, null=True)
    firma_director = models.CharField(max_length=150, blank=True, null=True)
    firma_asesor = models.CharField(max_length=150, blank=True, null=True)
    archivo_pdf = models.FileField(upload_to="adopciones/", blank=True, null=True)
    cantidad_total = models.PositiveIntegerField(default=0)  # suma de detalles

    class Meta:
        db_table = "adopciones"
    def __str__(self): return f"Adopción de {self.cotizacion.numero_cotizacion or self.cotizacion.id}"

class DetalleAdopcion(models.Model):
    MESES_CHOICES = [
        ("ENERO","Enero"),("FEBRERO","Febrero"),("MARZO","Marzo"),("ABRIL","Abril"),("MAYO","Mayo"),("JUNIO","Junio"),
        ("JULIO","Julio"),("AGOSTO","Agosto"),("SETIEMBRE","Setiembre"),("OCTUBRE","Octubre"),("NOVIEMBRE","Noviembre"),("DICIEMBRE","Diciembre"),
    ]
    adopcion = models.ForeignKey(Adopcion, on_delete=models.CASCADE, related_name="detalles")
    libro = models.ForeignKey(Libro, on_delete=models.PROTECT)
    cantidad_adoptada = models.PositiveIntegerField(default=0)
    mes_lectura = models.CharField(max_length=20, blank=True, null=True, choices=MESES_CHOICES)

    class Meta:
        db_table = "detalles_adopcion"
    def __str__(self): return f"{self.libro.descripcion_completa} ({self.cantidad_adoptada})"

# =====================================================
#  PEDIDO AL PROVEEDOR
# =====================================================
class Pedido(models.Model):
    adopcion = models.OneToOneField(Adopcion, on_delete=models.PROTECT, related_name="pedido")
    fecha_pedido = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=EstadoPedido.choices, default=EstadoPedido.BORRADOR)
    proveedor = models.CharField(max_length=150, blank=True, null=True)  # opcional
    observaciones = models.TextField(blank=True, null=True)
    total_costo = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # suma de (precio_proveedor*cantidad)

    class Meta:
        db_table = "pedidos"
    def __str__(self): return f"Pedido #{self.id} - Adopción {self.adopcion_id}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    libro = models.ForeignKey(Libro, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=0)
    precio_proveedor = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # fijo al momento de emitir

    class Meta:
        db_table = "detalles_pedido"
    def __str__(self): return f"Pedido {self.pedido_id} - {self.libro.descripcion_completa[:40]}"
