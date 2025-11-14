from django.db import models
from django.contrib.auth.models import User

# =====================================================
#  MODELO: LIBRO
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
    año_catalogo = models.CharField(max_length=10, blank=True, null=True)  # opcional
    isbn = models.CharField(max_length=50, blank=True, null=True)          # opcional

    class Meta:
        db_table = "libros"
        verbose_name = "Libro"
        verbose_name_plural = "Libros"

    def __str__(self):
        return f"{self.empresa} - {self.descripcion_completa}"


# =====================================================
#  MODELO: INSTITUCIÓN EDUCATIVA
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
        verbose_name = "Institución Educativa"
        verbose_name_plural = "Instituciones Educativas"

    def __str__(self):
        return self.nombre


# =====================================================
#  MODELO: ASESOR COMERCIAL
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
        default="ACTIVO"
    )

    class Meta:
        db_table = "asesores_comerciales"
        verbose_name = "Asesor Comercial"
        verbose_name_plural = "Asesores Comerciales"

    def __str__(self):
        return f"{self.nombre} ({self.empresa_editorial or 'Sin Editorial'})"


# =====================================================
#  MODELO: COTIZACIÓN
# =====================================================
from django.db import models
from django.contrib.auth.models import User

class Cotizacion(models.Model):
    TIPO_VENTA_CHOICES = [
        ("FERIA", "Feria"),
        ("CONSIGNA", "Consignación"),
        ("PUNTO_DE_VENTA", "Punto de Venta"),
    ]

    ESTADO_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("ENVIADA", "Enviada"),
        ("APROBADA", "Aprobada"),
        ("ADOPTADA", "Adoptada"),
        ("RECHAZADA", "Rechazada"),
    ]

    numero_cotizacion = models.CharField(max_length=20, unique=True, blank=True, null=True)
    institucion = models.ForeignKey("InstitucionEducativa", on_delete=models.CASCADE, related_name="cotizaciones")
    asesor = models.ForeignKey("AsesorComercial", on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # ✅ opcional
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_venta = models.CharField(max_length=20, choices=TIPO_VENTA_CHOICES, default="FERIA")
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default="PENDIENTE")
    observaciones = models.TextField(blank=True, null=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "cotizaciones"
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"

    def __str__(self):
        return f"Cotización {self.numero_cotizacion or self.id}"



# =====================================================
#  MODELO: DETALLE DE COTIZACIÓN
# =====================================================
class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(
        Cotizacion,
        on_delete=models.CASCADE,
        related_name="detalles"
    )
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    # Precios editables/ingresados por usuario (según flujo)
    precio_be = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_ie = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_consigna = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_coordinado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_ppff = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Porcentajes ingresados
    desc_proveedor = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    desc_consigna = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comision = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Métricas calculadas
    precio_proveedor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    utilidad_ie = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    roi_ie = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    roi_consigna = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "detalles_cotizacion"
        verbose_name = "Detalle de Cotización"
        verbose_name_plural = "Detalles de Cotización"

    def __str__(self):
        return f"Detalle #{self.id} - {self.libro.descripcion_completa[:40]}"


# =====================================================
#  MODELO: ADOPCIÓN
# =====================================================
class Adopcion(models.Model):
    cotizacion = models.OneToOneField(
        Cotizacion,
        on_delete=models.CASCADE,
        related_name="adopcion"
    )
    fecha_adopcion = models.DateField(auto_now_add=True)
    modalidad = models.CharField(max_length=50, blank=True, null=True)
    observaciones_finales = models.TextField(blank=True, null=True)
    firma_director = models.CharField(max_length=150, blank=True, null=True)
    firma_asesor = models.CharField(max_length=150, blank=True, null=True)
    archivo_pdf = models.FileField(upload_to="adopciones/", blank=True, null=True)
    cantidad_adoptada = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "adopciones"
        verbose_name = "Adopción"
        verbose_name_plural = "Adopciones"

    def __str__(self):
        return f"Adopción de {self.cotizacion.numero_cotizacion or self.cotizacion.id}"


class DetalleAdopcion(models.Model):
    adopcion = models.ForeignKey(
        "Adopcion",
        on_delete=models.CASCADE,
        related_name="detalles"
    )
    libro = models.ForeignKey("Libro", on_delete=models.PROTECT)
    cantidad_adoptada = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "detalles_adopcion"
        verbose_name = "Detalle de Adopción"
        verbose_name_plural = "Detalles de Adopción"

    def __str__(self):
        return f"{self.libro.descripcion_completa} ({self.cantidad_adoptada} adoptados)"
