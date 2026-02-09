from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

# =========================================================
# Helpers
# =========================================================
DEC_0 = Decimal("0.00")
DEC_2 = Decimal("0.01")


def d0(x) -> Decimal:
    try:
        if x is None or x == "":
            return DEC_0
        return Decimal(str(x))
    except Exception:
        return DEC_0


def q2(x: Decimal) -> Decimal:
    return d0(x).quantize(DEC_2)


# =========================================================
# ALMACEN
# =========================================================
class TipoAlmacen(models.TextChoices):
    PRINCIPAL = "PRINCIPAL", "Principal"
    PUNTO_VENTA = "PUNTO_VENTA", "Punto de Venta"
    FERIA = "FERIA", "Feria"
    CONSIGNA = "CONSIGNA", "Consignación"


class Almacen(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    tipo = models.CharField(max_length=20, choices=TipoAlmacen.choices, default=TipoAlmacen.PRINCIPAL)
    es_principal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


# =========================================================
# DOCUMENTOS
# =========================================================
class TipoDocumento(models.TextChoices):
    FACTURA = "FACTURA", "Factura"
    GUIA_REMISION = "GUIA_REMISION", "Guía de Remisión"
    BOLETA = "BOLETA", "Boleta"
    NOTA_CREDITO = "NOTA_CREDITO", "Nota de Crédito"
    INVENTARIO = "INVENTARIO", "Inventario"
    OTRO = "OTRO", "Otro"


# =========================================================
# INGRESO (ENTRADA)
# =========================================================
class Ingreso(models.Model):
    almacen_destino = models.ForeignKey("almacen.Almacen", on_delete=models.PROTECT, related_name="ingresos")

    # Proveedor = Editorial (app cotizador_colegio)
    proveedor = models.ForeignKey(
        "cotizador_colegio.Editorial",
        on_delete=models.PROTECT,
        related_name="ingresos",
        null=True,
        blank=True,
    )

    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, default=TipoDocumento.FACTURA)
    numero_documento = models.CharField(max_length=60)

    fecha_documento = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    observacion = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Ingreso"
        verbose_name_plural = "Ingresos"
        indexes = [
            models.Index(fields=["numero_documento"]),
            models.Index(fields=["fecha_documento"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_documento", "numero_documento", "proveedor"],
                name="uniq_ingreso_doc_proveedor",
            )
        ]

    def __str__(self):
        prov = getattr(self.proveedor, "nombre", None) or "Sin proveedor"
        return f"{self.get_tipo_documento_display()} {self.numero_documento} - {prov}"


class IngresoDetalle(models.Model):
    ingreso = models.ForeignKey("almacen.Ingreso", on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(
        "cotizador_colegio.Producto",
        on_delete=models.PROTECT,
        related_name="ingresos_detalle",
    )

    cantidad = models.PositiveIntegerField(default=0)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=DEC_0)

    class Meta:
        verbose_name = "Detalle de Ingreso"
        verbose_name_plural = "Detalles de Ingreso"
        constraints = [
            models.CheckConstraint(check=models.Q(cantidad__gte=0), name="chk_ing_det_cantidad_gte0"),
            models.CheckConstraint(check=models.Q(costo_unitario__gte=0), name="chk_ing_det_costo_gte0"),
        ]

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"

    @property
    def subtotal(self) -> Decimal:
        return q2(d0(self.costo_unitario) * Decimal(int(self.cantidad or 0)))


# =========================================================
# TRANSFERENCIA
# =========================================================
class EstadoTransferencia(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    ANULADA = "ANULADA", "Anulada"


class Transferencia(models.Model):
    almacen_origen = models.ForeignKey("almacen.Almacen", on_delete=models.PROTECT, related_name="transferencias_salida")
    almacen_destino = models.ForeignKey(
        "almacen.Almacen", on_delete=models.PROTECT, related_name="transferencias_entrada"
    )

    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, default=TipoDocumento.GUIA_REMISION)
    numero_documento = models.CharField(max_length=60)
    fecha_documento = models.DateField(default=timezone.now)

    estado = models.CharField(max_length=20, choices=EstadoTransferencia.choices, default=EstadoTransferencia.BORRADOR)
    observacion = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transferencia"
        verbose_name_plural = "Transferencias"
        indexes = [
            models.Index(fields=["numero_documento"]),
            models.Index(fields=["fecha_documento"]),
            models.Index(fields=["estado"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(almacen_origen=models.F("almacen_destino")),
                name="chk_transfer_origen_destino_distintos",
            )
        ]

    def __str__(self):
        return f"Transferencia {self.numero_documento} ({self.get_estado_display()})"


class TransferenciaDetalle(models.Model):
    transferencia = models.ForeignKey("almacen.Transferencia", on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(
        "cotizador_colegio.Producto",
        on_delete=models.PROTECT,
        related_name="transferencias_detalle",
    )
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Detalle de Transferencia"
        verbose_name_plural = "Detalles de Transferencia"
        constraints = [
            models.CheckConstraint(check=models.Q(cantidad__gte=0), name="chk_trans_det_cantidad_gte0"),
        ]

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"


# =========================================================
# STOCK (ÚNICO - con mínimos)
# =========================================================
class Stock(models.Model):
    almacen = models.ForeignKey("almacen.Almacen", on_delete=models.PROTECT, related_name="stocks")
    producto = models.ForeignKey("cotizador_colegio.Producto", on_delete=models.PROTECT, related_name="stocks")

    cantidad_actual = models.IntegerField(default=0)

    # ✅ alertas
    stock_minimo = models.IntegerField(default=0)
    punto_reposicion = models.IntegerField(default=0)

    valorizado_actual = models.DecimalField(max_digits=14, decimal_places=2, default=DEC_0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        constraints = [
            models.UniqueConstraint(fields=["almacen", "producto"], name="uniq_stock_almacen_producto"),
            models.CheckConstraint(check=models.Q(stock_minimo__gte=0), name="chk_stock_minimo_gte0"),
            models.CheckConstraint(check=models.Q(punto_reposicion__gte=0), name="chk_punto_reposicion_gte0"),
        ]

    def __str__(self):
        return f"{self.almacen.nombre} - {self.producto.nombre}"

    @property
    def costo_promedio(self) -> Decimal:
        if (self.cantidad_actual or 0) <= 0:
            return DEC_0
        return q2(d0(self.valorizado_actual) / Decimal(self.cantidad_actual))


# =========================================================
# KARDEX / MOVIMIENTO
# =========================================================
class TipoMovimiento(models.TextChoices):
    INGRESO = "INGRESO", "Ingreso"
    TRANSFERENCIA_SALIDA = "TRANSFERENCIA_SALIDA", "Transferencia (Salida)"
    TRANSFERENCIA_INGRESO = "TRANSFERENCIA_INGRESO", "Transferencia (Ingreso)"
    DEVOLUCION = "DEVOLUCION", "Devolución"
    AJUSTE_POS = "AJUSTE_POS", "Ajuste (+)"
    AJUSTE_NEG = "AJUSTE_NEG", "Ajuste (-)"


class MovimientoStock(models.Model):
    almacen = models.ForeignKey("almacen.Almacen", on_delete=models.PROTECT, related_name="movimientos")
    producto = models.ForeignKey(
        "cotizador_colegio.Producto", on_delete=models.PROTECT, related_name="movimientos_stock"
    )

    tipo = models.CharField(max_length=30, choices=TipoMovimiento.choices)
    fecha = models.DateTimeField(default=timezone.now)

    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, default=TipoDocumento.OTRO)
    numero_documento = models.CharField(max_length=60, blank=True, default="")

    entrada = models.PositiveIntegerField(default=0)
    salida = models.PositiveIntegerField(default=0)

    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=DEC_0)
    costo_total = models.DecimalField(max_digits=14, decimal_places=2, default=DEC_0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["tipo"]),
            models.Index(fields=["numero_documento"]),
        ]

    def __str__(self):
        return f"{self.tipo} - {self.producto} ({self.almacen})"


# =========================================================
# AJUSTE (DOCUMENTO ERP)
# =========================================================
class TipoAjuste(models.TextChoices):
    POSITIVO = "POSITIVO", "Aumenta Stock (+)"
    NEGATIVO = "NEGATIVO", "Disminuye Stock (-)"


class MotivoAjuste(models.TextChoices):
    MERMA = "MERMA", "Merma / Daño"
    PERDIDA = "PERDIDA", "Pérdida / Robo"
    CONTEO = "CONTEO", "Diferencia por Conteo"
    ERROR = "ERROR", "Error Operativo"
    OTRO = "OTRO", "Otro"


class EstadoAjuste(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    ANULADO = "ANULADO", "Anulado"


class AjusteStock(models.Model):
    almacen = models.ForeignKey("almacen.Almacen", on_delete=models.PROTECT, related_name="ajustes")

    tipo_ajuste = models.CharField(max_length=20, choices=TipoAjuste.choices)
    motivo = models.CharField(max_length=20, choices=MotivoAjuste.choices, default=MotivoAjuste.OTRO)

    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices, default=TipoDocumento.INVENTARIO)
    numero_documento = models.CharField(max_length=60, blank=True, default="")

    fecha_documento = models.DateField(default=timezone.now)

    estado = models.CharField(max_length=20, choices=EstadoAjuste.choices, default=EstadoAjuste.BORRADOR)
    observacion = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ajustes_creados",
    )

    class Meta:
        verbose_name = "Ajuste de Stock"
        verbose_name_plural = "Ajustes de Stock"
        indexes = [
            models.Index(fields=["fecha_documento"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["numero_documento"]),
        ]

    def __str__(self):
        return f"Ajuste {self.id} ({self.get_estado_display()}) - {self.almacen.nombre}"


class AjusteStockDetalle(models.Model):
    ajuste = models.ForeignKey("almacen.AjusteStock", on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(
        "cotizador_colegio.Producto", on_delete=models.PROTECT, related_name="ajustes_detalle"
    )

    cantidad = models.PositiveIntegerField(default=0)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Detalle de Ajuste"
        verbose_name_plural = "Detalles de Ajuste"
        constraints = [
            models.CheckConstraint(check=models.Q(cantidad__gte=0), name="chk_ajuste_det_cantidad_gte0"),
        ]

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"
