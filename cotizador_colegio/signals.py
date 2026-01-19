# cotizador_colegio/signals.py
from decimal import Decimal, ROUND_HALF_UP
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

from .models import DetallePedido, Pedido, DetalleAdopcion, Adopcion


# ============================
# ✅ Recalcular total_costo del Pedido
# ============================
def _recalcular_total_costo(ped: Pedido):
    total = Decimal("0.00")
    for d in ped.detalles.all():
        total += (d.precio_proveedor or Decimal("0.00")) * (d.cantidad or 0)

    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Solo guarda si cambió
    if ped.total_costo != total:
        ped.total_costo = total
        ped.save(update_fields=["total_costo"])


@receiver([post_save, post_delete], sender=DetallePedido)
def detalle_pedido_changed(sender, instance, **kwargs):
    _recalcular_total_costo(instance.pedido)


# ============================
# ✅ Mantener cantidad_total de adopción
# ============================
@receiver([post_save, post_delete], sender=DetalleAdopcion)
def detalle_adopcion_changed(sender, instance, **kwargs):
    """
    Mantiene cantidad_total en Adopcion actualizado según DetalleAdopcion.cantidad_adoptada
    """
    adop = instance.adopcion
    total = adop.detalles.aggregate(s=Sum("cantidad_adoptada"))["s"] or 0

    if adop.cantidad_total != total:
        adop.cantidad_total = total
        adop.save(update_fields=["cantidad_total"])
