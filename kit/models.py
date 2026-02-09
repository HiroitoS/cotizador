from __future__ import annotations

from decimal import Decimal
from django.db import models

DEC_0 = Decimal("0.00")
DEC_2 = Decimal("0.01")


def q2(x: Decimal) -> Decimal:
    try:
        return (x or DEC_0).quantize(DEC_2)
    except Exception:
        return DEC_0


class TipoKit(models.TextChoices):
    KIT = "KIT", "Kit"
    PACK = "PACK", "Pack"
    COMBO = "COMBO", "Combo"


class Kit(models.Model):
    """
    Kit/Pack: composición de productos.
    NO guarda costo fijo (eso viene del almacén por compras).
    """
    nombre = models.CharField(max_length=200)

    # ✅ opcional, por si luego quieres escanear / buscar por barcode
    codigo_barra = models.CharField(max_length=80, blank=True, default="", db_index=True)

    tipo = models.CharField(max_length=20, choices=TipoKit.choices, default=TipoKit.KIT)
    activo = models.BooleanField(default=True)
    observacion = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kit/Pack"
        verbose_name_plural = "Kits/Packs"
        indexes = [
            models.Index(fields=["nombre", "tipo", "activo"]),
            models.Index(fields=["codigo_barra"]),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_tipo_display()})"


class KitItem(models.Model):
    kit = models.ForeignKey("kit.Kit", on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(
        "cotizador_colegio.Producto",
        on_delete=models.PROTECT,
        related_name="kit_items",
    )
    cantidad = models.PositiveIntegerField(default=1)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Item de Kit"
        verbose_name_plural = "Items de Kit"
        constraints = [
            models.UniqueConstraint(fields=["kit", "producto"], name="uniq_kit_producto"),
            models.CheckConstraint(check=models.Q(cantidad__gt=0), name="chk_kititem_cantidad_gt0"),
        ]
        ordering = ["orden", "id"]

    def __str__(self) -> str:
        return f"{self.kit.nombre} -> {self.producto.nombre} x {self.cantidad}"

    @property
    def pvp_subtotal(self) -> Decimal:
        pvp = getattr(self.producto, "pvp_2026", DEC_0) or DEC_0
        return q2(Decimal(self.cantidad) * Decimal(pvp))
