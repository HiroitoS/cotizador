# cotizador_colegio/services.py
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import (
    Cotizacion, DetalleCotizacion, InstitucionEducativa, AsesorComercial,
    EstadoCotizacion, Adopcion, DetalleAdopcion, Pedido, DetallePedido, Libro, TipoVenta
)

def to_decimal(value):
    try:
        if value in [None, ""]: return None
        return Decimal(str(value).replace(",", "").strip())
    except Exception:
        return None

@transaction.atomic
def guardar_cotizacion(data):
    tipo_venta = data.get("tipo_venta")
    institucion_data = data.get("institucion")
    asesor_data = data.get("asesor")
    detalles_data = data.get("detalles", [])

    institucion, _ = InstitucionEducativa.objects.get_or_create(
        nombre=institucion_data.get("nombre_ie"),
        defaults={
            "codigo_modular": institucion_data.get("codigo_modular"),
            "nivel_educativo": institucion_data.get("nivel_educativo"),
            "direccion": institucion_data.get("direccion"),
            "distrito": institucion_data.get("distrito"),
            "provincia": institucion_data.get("provincia"),
            "departamento": institucion_data.get("departamento"),
            "telefono": institucion_data.get("telefono"),
            "correo_institucional": institucion_data.get("correo_institucional"),
            "director": institucion_data.get("director"),
        },
    )

    asesor, _ = AsesorComercial.objects.get_or_create(
        nombre=asesor_data.get("nombre"),
        defaults={
            "telefono": asesor_data.get("telefono"),
            "zona": asesor_data.get("zona"),
            "empresa_editorial": asesor_data.get("empresa_editorial"),
            "correo": asesor_data.get("correo"),
            "cargo": asesor_data.get("cargo"),
        },
    )

    cotizacion = Cotizacion.objects.create(
        institucion=institucion,
        asesor=asesor,
        tipo_venta=tipo_venta,
    )

    for d in detalles_data:
        DetalleCotizacion.objects.create(
            cotizacion=cotizacion,
            libro_id=d.get("libro"),
            cantidad=d.get("cantidad", 1),
            precio_be=to_decimal(d.get("precio_be")),
            precio_ie=to_decimal(d.get("precio_ie")),
            precio_ppff=to_decimal(d.get("precio_ppff")),
            desc_proveedor=to_decimal(d.get("desc_proveedor")),
            desc_consigna=to_decimal(d.get("desc_consigna")),
            comision=to_decimal(d.get("comision")),
        )
    cotizacion.refresh_from_db()
    return cotizacion

@transaction.atomic
def cambiar_estado_cotizacion(cotizacion: Cotizacion, nuevo_estado: str, usuario=None):
    actual = cotizacion.estado
    if actual == EstadoCotizacion.RECHAZADA and nuevo_estado == EstadoCotizacion.APROBADA:
        raise ValidationError("No se puede aprobar una cotización rechazada.")
    if actual == nuevo_estado:
        return cotizacion
    cotizacion.estado = nuevo_estado
    cotizacion.save(update_fields=["estado"])
    # Si pasa a APROBADA, podemos crear la adopción base vacía (o con detalles)
    if nuevo_estado == EstadoCotizacion.APROBADA and not hasattr(cotizacion, "adopcion"):
        crear_adopcion_desde_cotizacion(cotizacion)
    return cotizacion

@transaction.atomic
def crear_adopcion_desde_cotizacion(cotizacion: Cotizacion) -> Adopcion:
    # Crear adopción y copiar detalles con cantidades = 0 (el asesor las llenará)
    adopcion = Adopcion.objects.create(cotizacion=cotizacion)
    for det in cotizacion.detalles.all():
        DetalleAdopcion.objects.create(
            adopcion=adopcion,
            libro=det.libro,
            cantidad_adoptada=0,  # el asesor define luego
            mes_lectura=None,
        )
    cotizacion.estado = EstadoCotizacion.ADOPTADA  # opcional: marcar como ADOPTADA al crear ficha
    cotizacion.save(update_fields=["estado"])
    return adopcion

@transaction.atomic
def generar_pedido_desde_adopcion(adopcion: Adopcion) -> Pedido:
    # Crear pedido con precio_proveedor capturado desde el libro (o desde cotización si quieres)
    pedido = Pedido.objects.create(adopcion=adopcion, estado="BORRADOR")
    for det in adopcion.detalles.all():
        # Obtener precio_proveedor desde la última cotización (detalle correspondiente)
        det_cot = DetalleCotizacion.objects.filter(
            cotizacion=adopcion.cotizacion, libro=det.libro
        ).first()
        precio_proveedor = det_cot.precio_proveedor if det_cot else Decimal("0.00")
        DetallePedido.objects.create(
            pedido=pedido,
            libro=det.libro,
            cantidad=det.cantidad_adoptada or 0,
            precio_proveedor=precio_proveedor or Decimal("0.00"),
        )
    pedido.refresh_from_db()
    return pedido
