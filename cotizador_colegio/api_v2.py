from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Producto, Cotizacion, Adopcion, Pedido, DetalleCotizacion, EstadoCotizacion
from .serializers import (
    ProductoCatalogoSerializer,
    CotizacionPanelSerializer,
    CotizacionDetalleSerializer,
    AdopcionPanelSerializer,
    PedidoSerializer,
)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .pricing import calcular_item


class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Producto.objects.select_related("editorial").filter(estado=True).order_by("nombre")
    serializer_class = ProductoCatalogoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["editorial", "nivel", "grado", "area"]
    search_fields = ["nombre", "codigo"]


class CotizacionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cotizacion.objects.select_related("institucion", "asesor").prefetch_related("detalles__producto").order_by("-id")
    serializer_class = CotizacionPanelSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CotizacionDetalleSerializer
        return CotizacionPanelSerializer

    @action(detail=False, methods=["post"], url_path="calcular-batch")
    def calcular_batch(self, request):
        """
        POST /api/v2/cotizaciones/calcular-batch/
        { tipo_venta, items: [{producto_id, precio_be, descuento_ie, precio_ppff, desc_consigna, comision, comi_coo}] }
        """
        data = request.data or {}
        tipo_venta = (data.get("tipo_venta") or "").upper().strip()
        items = data.get("items") or []

        if not tipo_venta:
            return Response({"detail": "tipo_venta es requerido."}, status=400)
        if not isinstance(items, list) or not items:
            return Response({"detail": "items debe ser una lista no vacía."}, status=400)

        out_items = []
        for it in items:
            pid = it.get("producto_id")
            if not pid:
                return Response({"detail": "Cada item requiere producto_id."}, status=400)

            producto = get_object_or_404(Producto, id=pid)
            try:
                calc = calcular_item(tipo_venta, producto, it)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

            out_items.append(calc)

        # totales simples (fase 1)
        total_bruto = sum([float(i.get("precio_ie", i.get("precio_consigna", 0))) for i in out_items])
        total_utilidad = sum([float(i.get("utilidad_be_x_un", 0)) for i in out_items])

        return Response({
            "tipo_venta": tipo_venta,
            "items": out_items,
            "totales": {
                "total_bruto": round(total_bruto, 2),
                "total_utilidad": round(total_utilidad, 2),
            }
        }, status=200)

    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):
        cot = self.get_object()
        estado = (request.data.get("estado") or "").upper().strip()

        if estado not in ["APROBADA", "RECHAZADA", "PENDIENTE", "ADOPTADA"]:
            return Response({"detail": "Estado inválido."}, status=400)

        cot.estado = estado
        cot.save(update_fields=["estado"])
        return Response({"detail": "Estado actualizado.", "estado": cot.estado}, status=200)


class AdopcionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Adopcion.objects.select_related("cotizacion", "cotizacion__institucion", "cotizacion__asesor").order_by("-id")
    serializer_class = AdopcionPanelSerializer


class PedidoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pedido.objects.select_related("adopcion").order_by("-fecha_pedido")
    serializer_class = PedidoSerializer
