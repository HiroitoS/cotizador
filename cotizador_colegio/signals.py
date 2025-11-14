# cotizador_colegio/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal, ROUND_HALF_UP
from .models import (
    DetalleCotizacion, Cotizacion,
    DetallePedido, Pedido,
    DetalleAdopcion, Adopcion
)

# ✅ Recalcular monto_total en Cotización basado en tipo_venta por detalle
def _recalcular_monto_total(cot: Cotizacion):
    total = Decimal("0.00")

    for d in cot.detalles.all():
        tv = d.tipo_venta  # ✅ ahora se toma del detalle

        if tv in ("PV", "FERIA"):
            base = d.precio_ie or Decimal("0.00")
        elif tv == "CONSIGNA":
            base = (
                d.precio_coordinado or
                d.precio_consigna or
                d.precio_be or Decimal("0.00")
            )
        else:
            base = Decimal("0.00")

        total += base * (d.cantidad or 0)

    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if cot.monto_total != total:
        cot.monto_total = total
        cot.save(update_fields=["monto_total"])


@receiver([post_save, post_delete], sender=DetalleCotizacion)
def detalle_cotizacion_changed(sender, instance, **kwargs):
    _recalcular_monto_total(instance.cotizacion)


# ✅ Recalcular total_costo del Pedido
def _recalcular_total_costo(ped: Pedido):
    total = Decimal("0.00")
    for d in ped.detalles.all():
        total += (d.precio_proveedor or Decimal("0.00")) * (d.cantidad or 0)

    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if ped.total_costo != total:
        ped.total_costo = total
        ped.save(update_fields=["total_costo"])


@receiver([post_save, post_delete], sender=DetallePedido)
def detalle_pedido_changed(sender, instance, **kwargs):
    _recalcular_total_costo(instance.pedido)


# ✅ Mantener cantidad_total de adopción
@receiver([post_save, post_delete], sender=DetalleAdopcion)
def detalle_adopcion_changed(sender, instance, **kwargs):
    adop = instance.adopcion
    total = sum(x.cantidad_adoptada for x in adop.detalles.all())
    if adop.cantidad_total != total:
        adop.cantidad_total = total
        adop.save(update_fields=["cantidad_total"])
