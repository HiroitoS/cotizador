from __future__ import annotations

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import (
    Stock,
    MovimientoStock,
    TipoMovimiento,
    TipoDocumento,
    EstadoTransferencia,
)

DEC_0 = Decimal("0.00")


def d0(x) -> Decimal:
    try:
        if x is None or x == "":
            return DEC_0
        return Decimal(str(x))
    except Exception:
        return DEC_0


def _get_or_create_stock_locked(almacen_id: int, producto_id: int) -> Stock:
    """
    Trae el stock con lock. Si no existe, lo crea y lo vuelve a leer con lock.
    """
    stock = (
        Stock.objects.select_for_update()
        .filter(almacen_id=almacen_id, producto_id=producto_id)
        .first()
    )
    if stock:
        return stock

    Stock.objects.create(
        almacen_id=almacen_id,
        producto_id=producto_id,
        cantidad_actual=0,
        stock_minimo=0,
        punto_reposicion=0,
        valorizado_actual=DEC_0,
    )

    return Stock.objects.select_for_update().get(
        almacen_id=almacen_id, producto_id=producto_id
    )


def _kardex(
    *,
    almacen_id: int,
    producto_id: int,
    tipo: str,
    tipo_documento: str,
    numero_documento: str,
    entrada: int = 0,
    salida: int = 0,
    costo_unitario: Decimal = DEC_0,
):
    entrada = int(entrada or 0)
    salida = int(salida or 0)
    costo_unitario = d0(costo_unitario)

    if entrada > 0:
        costo_total = (costo_unitario * Decimal(entrada)).quantize(Decimal("0.01"))
    elif salida > 0:
        costo_total = (costo_unitario * Decimal(salida)).quantize(Decimal("0.01"))
    else:
        costo_total = DEC_0

    MovimientoStock.objects.create(
        almacen_id=almacen_id,
        producto_id=producto_id,
        tipo=tipo,
        fecha=timezone.now(),
        tipo_documento=tipo_documento or TipoDocumento.OTRO,
        numero_documento=numero_documento or "",
        entrada=entrada,
        salida=salida,
        costo_unitario=costo_unitario,
        costo_total=costo_total,
    )


# =========================================================
# INGRESO: aplica stock + valorizado + kardex
# =========================================================
def aplicar_ingreso(ingreso) -> None:
    """
    Procesa un ingreso:
    - suma cantidades a stock
    - suma valorizado según el costo_unitario del detalle
    - kardex INGRESO por item
    IMPORTANTE: llámalo dentro de transaction.atomic() desde el ViewSet.
    """
    if not ingreso:
        raise ValueError("Ingreso inválido.")

    if not ingreso.detalles.exists():
        raise ValueError("El ingreso no tiene detalles.")

    almacen_id = ingreso.almacen_destino_id

    for det in ingreso.detalles.select_related("producto").all():
        if (det.cantidad or 0) <= 0:
            continue

        producto_id = det.producto_id
        cant = int(det.cantidad)
        costo_u = d0(det.costo_unitario)

        stock = _get_or_create_stock_locked(almacen_id, producto_id)

        # valorizado se suma al costo real de la compra (detalle)
        stock.cantidad_actual = int(stock.cantidad_actual or 0) + cant
        stock.valorizado_actual = (
            d0(stock.valorizado_actual) + (Decimal(cant) * costo_u)
        ).quantize(Decimal("0.01"))

        stock.save(update_fields=["cantidad_actual", "valorizado_actual", "updated_at"])

        _kardex(
            almacen_id=almacen_id,
            producto_id=producto_id,
            tipo=TipoMovimiento.INGRESO,
            tipo_documento=getattr(ingreso, "tipo_documento", TipoDocumento.OTRO),
            numero_documento=getattr(ingreso, "numero_documento", ""),
            entrada=cant,
            salida=0,
            costo_unitario=costo_u,
        )


# =========================================================
# TRANSFERENCIA: descuenta origen + suma destino + kardex
# - NO permite stock negativo
# - La salida se costea al costo_promedio del stock origen
# =========================================================
def confirmar_transferencia(trans) -> None:
    """
    Confirma transferencia:
    - valida estado BORRADOR
    - descuenta stock del origen
    - suma stock al destino al mismo costo promedio del origen
    - kardex salida/entrada
    """
    if not trans:
        raise ValueError("Transferencia inválida.")

    if trans.estado != EstadoTransferencia.BORRADOR:
        raise ValueError("Solo se puede confirmar una transferencia en estado BORRADOR.")

    if trans.almacen_origen_id == trans.almacen_destino_id:
        raise ValueError("El almacén origen y destino deben ser distintos.")

    if not trans.detalles.exists():
        raise ValueError("La transferencia no tiene detalles.")

    origen_id = trans.almacen_origen_id
    destino_id = trans.almacen_destino_id

    # evitar deadlocks: lock en orden por id de almacén
    lock_first, lock_second = sorted([origen_id, destino_id])

    detalles = list(trans.detalles.all())

    for det in detalles:
        if (det.cantidad or 0) <= 0:
            continue

        pid = det.producto_id
        cant = int(det.cantidad)

        # locks consistentes (mismo orden siempre)
        _get_or_create_stock_locked(lock_first, pid)
        _get_or_create_stock_locked(lock_second, pid)

        stock_origen = _get_or_create_stock_locked(origen_id, pid)
        stock_destino = _get_or_create_stock_locked(destino_id, pid)

        disponible = int(stock_origen.cantidad_actual or 0)
        if disponible < cant:
            raise ValueError(
                f"Stock insuficiente en almacén origen para producto {pid}. "
                f"Disponible: {disponible}, requerido: {cant}"
            )

        costo_u = d0(stock_origen.costo_promedio)  # salida al costo promedio del origen

        # ORIGEN: resta cantidad y valorizado
        stock_origen.cantidad_actual = disponible - cant
        stock_origen.valorizado_actual = (
            d0(stock_origen.valorizado_actual) - (Decimal(cant) * costo_u)
        ).quantize(Decimal("0.01"))

        if stock_origen.cantidad_actual == 0:
            stock_origen.valorizado_actual = DEC_0

        if stock_origen.cantidad_actual < 0 or stock_origen.valorizado_actual < 0:
            raise ValueError("Operación inválida: el stock origen quedaría negativo.")

        stock_origen.save(update_fields=["cantidad_actual", "valorizado_actual", "updated_at"])

        _kardex(
            almacen_id=origen_id,
            producto_id=pid,
            tipo=TipoMovimiento.TRANSFERENCIA_SALIDA,
            tipo_documento=trans.tipo_documento,
            numero_documento=trans.numero_documento,
            entrada=0,
            salida=cant,
            costo_unitario=costo_u,
        )

        # DESTINO: suma cantidad y valorizado al mismo costo_u
        stock_destino.cantidad_actual = int(stock_destino.cantidad_actual or 0) + cant
        stock_destino.valorizado_actual = (
            d0(stock_destino.valorizado_actual) + (Decimal(cant) * costo_u)
        ).quantize(Decimal("0.01"))

        stock_destino.save(update_fields=["cantidad_actual", "valorizado_actual", "updated_at"])

        _kardex(
            almacen_id=destino_id,
            producto_id=pid,
            tipo=TipoMovimiento.TRANSFERENCIA_INGRESO,
            tipo_documento=trans.tipo_documento,
            numero_documento=trans.numero_documento,
            entrada=cant,
            salida=0,
            costo_unitario=costo_u,
        )

    trans.estado = EstadoTransferencia.CONFIRMADA
    trans.save(update_fields=["estado"])


# =========================================================
# AJUSTE DE STOCK (ERP): POS / NEG con motivo
# =========================================================
def confirmar_ajuste(
    *,
    almacen_id: int,
    motivo: str,
    tipo_documento: str = "OTRO",
    numero_documento: str = "",
    items: list[dict],
) -> None:
    """
    Ajuste ERP:
    - POS: suma stock. Si viene costo_unitario lo usa; si no, usa costo_promedio actual.
    - NEG: resta stock (no permite negativo). Costea al costo_promedio.
    - Kardex guarda el motivo en el numero_documento si no se envía.
    """
    if not items:
        raise ValueError("items vacío")

    for it in items:
        pid = int(it["producto_id"])
        tipo = it["tipo"]  # POS | NEG
        cant = int(it["cantidad"])

        if cant <= 0:
            raise ValueError("cantidad debe ser > 0")

        stock = _get_or_create_stock_locked(almacen_id, pid)
        costo_prom = d0(stock.costo_promedio)

        if tipo == "POS":
            costo_u = d0(it.get("costo_unitario")) if it.get("costo_unitario") is not None else costo_prom

            stock.cantidad_actual = int(stock.cantidad_actual or 0) + cant
            stock.valorizado_actual = (
                d0(stock.valorizado_actual) + (Decimal(cant) * costo_u)
            ).quantize(Decimal("0.01"))
            stock.save(update_fields=["cantidad_actual", "valorizado_actual", "updated_at"])

            _kardex(
                almacen_id=almacen_id,
                producto_id=pid,
                tipo=TipoMovimiento.AJUSTE_POS,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento or f"AJUSTE+ ({motivo})",
                entrada=cant,
                salida=0,
                costo_unitario=costo_u,
            )

        elif tipo == "NEG":
            disponible = int(stock.cantidad_actual or 0)
            if disponible < cant:
                raise ValueError(
                    f"Stock insuficiente para ajuste NEG. Producto {pid}: "
                    f"disponible={disponible}, requerido={cant}"
                )

            costo_u = costo_prom
            stock.cantidad_actual = disponible - cant
            stock.valorizado_actual = (
                d0(stock.valorizado_actual) - (Decimal(cant) * costo_u)
            ).quantize(Decimal("0.01"))

            if stock.cantidad_actual == 0:
                stock.valorizado_actual = DEC_0

            if stock.cantidad_actual < 0 or stock.valorizado_actual < 0:
                raise ValueError("Operación inválida: stock quedaría negativo.")

            stock.save(update_fields=["cantidad_actual", "valorizado_actual", "updated_at"])

            _kardex(
                almacen_id=almacen_id,
                producto_id=pid,
                tipo=TipoMovimiento.AJUSTE_NEG,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento or f"AJUSTE- ({motivo})",
                entrada=0,
                salida=cant,
                costo_unitario=costo_u,
            )

        else:
            raise ValueError("tipo debe ser POS o NEG")
