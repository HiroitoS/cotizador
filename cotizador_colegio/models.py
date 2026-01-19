from django.db import models
from decimal import Decimal, ROUND_HALF_UP

# ==========================
# ENUMERACIONES
# ==========================

class TipoVenta(models.TextChoices):
    FERIA = "FERIA", "Feria"
    CONSIGNA = "CONSIGNA", "Consignación"
    PUNTO_DE_VENTA = "PUNTO_DE_VENTA", "Punto de Venta"


class EstadoCotizacion(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    APROBADA = "APROBADA", "Aprobada"
    ADOPTADA = "ADOPTADA", "Adoptada"
    RECHAZADA = "RECHAZADA", "Rechazada"


class EstadoPedido(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    EMITIDO = "EMITIDO", "Emitido"
    ENVIADO = "ENVIADO", "Enviado a proveedor"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    CANCELADO = "CANCELADO", "Cancelado"


# ==========================
# EDITORIALES Y PRODUCTOS
# ==========================

class Editorial(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "editoriales"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    editorial = models.ForeignKey(
        Editorial,
        on_delete=models.PROTECT,
        related_name="productos"
    )

    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)

    nivel = models.CharField(max_length=50, blank=True)
    grado = models.CharField(max_length=50, blank=True)
    area = models.CharField(max_length=100, blank=True)
    serie = models.CharField(max_length=100, blank=True)

    pvp_2026 = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_proveedor = models.DecimalField(max_digits=5, decimal_places=2)
    precio_proveedor = models.DecimalField(max_digits=10, decimal_places=2)

    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "productos"
        unique_together = ("editorial", "codigo")

    def __str__(self):
        return f"{self.editorial.nombre} - {self.nombre}"


# ==========================
# INSTITUCIÓN EDUCATIVA
# ==========================

class InstitucionEducativa(models.Model):
    nombre = models.CharField(max_length=200)
    codigo_modular = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.CharField(max_length=250, blank=True, null=True)
    distrito = models.CharField(max_length=100, blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    departamento = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "instituciones_educativas"

    def __str__(self):
        return self.nombre


# ==========================
# ASESOR COMERCIAL
# ==========================

class AsesorComercial(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=[("ACTIVO", "Activo"), ("INACTIVO", "Inactivo")],
        default="ACTIVO"
    )

    class Meta:
        db_table = "asesores_comerciales"

    def __str__(self):
        return self.nombre


# ==========================
# COTIZACIÓN
# ==========================

class Cotizacion(models.Model):
    numero_cotizacion = models.CharField(max_length=20, unique=True, blank=True, null=True)
    institucion = models.ForeignKey(InstitucionEducativa, on_delete=models.PROTECT, related_name="cotizaciones")
    asesor = models.ForeignKey(AsesorComercial, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    motivo_rechazo = models.TextField(null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=EstadoCotizacion.choices,
        default=EstadoCotizacion.PENDIENTE
    )

    class Meta:
        db_table = "cotizaciones"

    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            last = Cotizacion.objects.order_by("id").last()
            num = (last.id + 1) if last else 1
            self.numero_cotizacion = f"COT-{str(num).zfill(5)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero_cotizacion


# ==========================
# DETALLE COTIZACIÓN
# ==========================

class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, related_name="detalles", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)

    cantidad = models.PositiveIntegerField(default=1)

    # valores base
    precio_be = models.DecimalField(max_digits=10, decimal_places=2)
    desc_proveedor = models.DecimalField(max_digits=5, decimal_places=2)
    precio_proveedor = models.DecimalField(max_digits=10, decimal_places=2)

    # IE
    descuento_ie = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    precio_ie = models.DecimalField(max_digits=10, decimal_places=2)
    precio_ppff = models.DecimalField(max_digits=10, decimal_places=2)

    utilidad_ie = models.DecimalField(max_digits=10, decimal_places=2)
    roi_ie = models.DecimalField(max_digits=10, decimal_places=2)

    tipo_venta = models.CharField(max_length=20, choices=TipoVenta.choices)

    class Meta:
        db_table = "detalle_cotizacion"

    def __str__(self):
        return f"{self.producto.nombre} ({self.cantidad})"


# ==========================
# ADOPCIÓN
# ==========================

class Adopcion(models.Model):
    cotizacion = models.OneToOneField(Cotizacion, on_delete=models.PROTECT, related_name="adopcion")
    fecha_adopcion = models.DateField(auto_now_add=True)
    cantidad_total = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "adopciones"

    def __str__(self):
        return f"Adopción {self.cotizacion.numero_cotizacion}"


class DetalleAdopcion(models.Model):
    MESES_CHOICES = [
        ("ENERO", "Enero"),
        ("FEBRERO", "Febrero"),
        ("MARZO", "Marzo"),
        ("ABRIL", "Abril"),
        ("MAYO", "Mayo"),
        ("JUNIO", "Junio"),
        ("JULIO", "Julio"),
        ("AGOSTO", "Agosto"),
        ("SETIEMBRE", "Setiembre"),
        ("OCTUBRE", "Octubre"),
        ("NOVIEMBRE", "Noviembre"),
        ("DICIEMBRE", "Diciembre"),
    ]

    adopcion = models.ForeignKey(
        Adopcion,
        related_name="detalles",
        on_delete=models.CASCADE
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
    )

    cantidad_adoptada = models.PositiveIntegerField(default=0)

    mes_lectura = models.CharField(
        max_length=20,
        choices=MESES_CHOICES,
        blank=True,
        null=True
    )

    class Meta:
        db_table = "detalles_adopcion"

    def __str__(self):
        return f"{self.producto.nombre} ({self.cantidad_adoptada})"

# ==========================
# PEDIDO
# ==========================

class Pedido(models.Model):
    adopcion = models.OneToOneField(Adopcion, on_delete=models.PROTECT, related_name="pedido")
    fecha_pedido = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=EstadoPedido.choices, default=EstadoPedido.BORRADOR)

    class Meta:
        db_table = "pedidos"

    def __str__(self):
        return f"Pedido {self.id}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name="detalles", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_proveedor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "detalles_pedido"

    def __str__(self):
        return f"{self.producto.nombre} ({self.cantidad})"
