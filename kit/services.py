from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, List

from django.db.models import Prefetch

from almacen.models import Stock
from .models import Kit, KitItem

DEC_0 = Decimal("0.00")
DEC_2 = Decimal("0.01")


def q2(x: Decimal) -> Decimal:
    try:
        return (x or DEC_0).quantize(DEC_2)
    except Exception:
        return DEC_0


@dataclass
class LineaProducto:
    producto_id: int
    producto_nombre: str
    editorial_nombre: str
    codigo: str
    cantidad: int


def obtener_kit_por_barcode(barcode: str) -> Kit:
    """
    Busca un kit por codigo_barra (opcional).
    """
    kit = (
        Kit.objects.prefetch_related(
            Prefetch("items", queryset=KitItem.objects.select_related("producto__editorial"))
        )
        .filter(codigo_barra=barcode, activo=True)
        .first()
    )
    if not kit:
        raise ValueError("Kit no encontrado o inactivo.")
    return kit


def expandir_kit(kit: Kit, multiplicador: int = 1) -> List[LineaProducto]:
    """
    Devuelve las líneas de productos del kit:
    - multiplicador=1 => receta normal
    - multiplicador=20 => 20 packs (cantidad se multiplica por 20)
    """
    if multiplicador <= 0:
        raise ValueError("multiplicador debe ser > 0")

    # asegurar items cargados con producto+editorial
    kit = (
        Kit.objects.prefetch_related(
            Prefetch("items", queryset=KitItem.objects.select_related("producto__editorial"))
        )
        .get(pk=kit.pk)
    )

    out: List[LineaProducto] = []
    for it in kit.items.all():
        prod = it.producto
        out.append(
            LineaProducto(
                producto_id=prod.id,
                producto_nombre=getattr(prod, "nombre", "") or "",
                editorial_nombre=getattr(getattr(prod, "editorial", None), "nombre", "") or "",
                codigo=getattr(prod, "codigo", "") or "",
                cantidad=int(it.cantidad) * int(multiplicador),
            )
        )
    return out


def expandir_por_barcode(barcode: str, multiplicador: int = 1):
    kit = obtener_kit_por_barcode(barcode)
    return kit, expandir_kit(kit, multiplicador=multiplicador)


def costear_kit(*, kit: Kit, almacen_id: int) -> dict[str, Any]:
    """
    Costeo usando Stock.costo_promedio por almacén.
    Retorna PVP total + costo_total + detalle.
    """
    kit = (
        Kit.objects.prefetch_related(
            Prefetch("items", queryset=KitItem.objects.select_related("producto__editorial").order_by("orden", "id"))
        )
        .get(pk=kit.pk)
    )

    producto_ids = [it.producto_id for it in kit.items.all()]

    stocks = Stock.objects.filter(almacen_id=almacen_id, producto_id__in=producto_ids)
    stock_map = {s.producto_id: s for s in stocks}

    pvp_total = DEC_0
    costo_total = DEC_0
    items_out = []

    for it in kit.items.all():
        prod = it.producto
        cant = int(it.cantidad or 0)

        pvp_u = getattr(prod, "pvp_2026", DEC_0) or DEC_0
        pvp_sub = q2(Decimal(cant) * Decimal(pvp_u))
        pvp_total += pvp_sub

        st = stock_map.get(it.producto_id)
        costo_u = st.costo_promedio if st else DEC_0
        costo_sub = q2(Decimal(cant) * Decimal(costo_u))
        costo_total += costo_sub

        items_out.append(
            {
                "producto_id": it.producto_id,
                "producto_codigo": getattr(prod, "codigo", "") or "",
                "producto_nombre": prod.nombre,
                "editorial_nombre": getattr(getattr(prod, "editorial", None), "nombre", "") or "",
                "cantidad": cant,
                "pvp_unitario": q2(Decimal(pvp_u)),
                "pvp_subtotal": pvp_sub,
                "costo_promedio_unitario": q2(Decimal(costo_u)),
                "costo_subtotal": costo_sub,
                "stock_actual": int(st.cantidad_actual) if st else 0,
                "tiene_stock_registrado": bool(st),
            }
        )

    return {
        "kit_id": kit.id,
        "nombre": kit.nombre,
        "almacen_id": almacen_id,
        "pvp_total": q2(pvp_total),
        "costo_estimado_total": q2(costo_total),
        "items": items_out,
    }
