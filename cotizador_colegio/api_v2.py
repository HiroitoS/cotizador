from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import (
    Producto,
    Editorial,
    Cotizacion,
    Adopcion,
    Pedido,
)

from .pricing import calcular_item

# ✅ Importamos SOLO lo que realmente existe en serializers.py
from .serializers import (
    ProductoCatalogoSerializer,
    CotizacionPanelSerializer,
    CotizacionDetalleSerializer,
    AdopcionPanelSerializer,
    DetalleAdopcionSerializer,   # ✅ este sí existe
    PedidoSerializer,            # ✅ este sí existe
)


# =========================================================
# ✅ PAGINACIÓN ESTÁNDAR (V2)
# =========================================================
class StandardPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 200


# =========================================================
# ✅ PRODUCTOS V2 (LIST + FILTERS)
# /api/v2/productos/
# /api/v2/productos/filtros/
# =========================================================
class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductoCatalogoSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Producto.objects.select_related("editorial").filter(estado=True).order_by("id")

        search = self.request.query_params.get("search")
        editorial = self.request.query_params.get("editorial")  # puede venir ID o nombre
        nivel = self.request.query_params.get("nivel")
        area = self.request.query_params.get("area")
        grado = self.request.query_params.get("grado")

        if search:
            qs = qs.filter(
                Q(nombre__icontains=search)
                | Q(codigo__icontains=search)
                | Q(editorial__nombre__icontains=search)
            )

        if editorial:
            try:
                eid = int(editorial)
                qs = qs.filter(editorial_id=eid)
            except Exception:
                qs = qs.filter(editorial__nombre__iexact=editorial)

        if nivel:
            qs = qs.filter(nivel__iexact=nivel)

        if area:
            qs = qs.filter(area__iexact=area)

        if grado:
            qs = qs.filter(grado__iexact=grado)

        return qs

    @action(detail=False, methods=["get"], url_path="filtros")
    def filtros(self, request):
        qs = Producto.objects.select_related("editorial").filter(estado=True)

        editoriales = list(
            Editorial.objects.filter(productos__estado=True)
            .distinct()
            .order_by("nombre")
            .values("id", "nombre")
        )

        niveles = list(
            qs.values_list("nivel", flat=True)
            .distinct()
            .exclude(nivel="")
            .order_by("nivel")
        )
        areas = list(
            qs.values_list("area", flat=True)
            .distinct()
            .exclude(area="")
            .order_by("area")
        )
        grados = list(
            qs.values_list("grado", flat=True)
            .distinct()
            .exclude(grado="")
            .order_by("grado")
        )

        return Response(
            {
                "editoriales": editoriales,
                "niveles": niveles,
                "areas": areas,
                "grados": grados,
            },
            status=200,
        )


# =========================================================
# ✅ COTIZACIONES V2 (PANEL + DETALLE)
# =========================================================
class CotizacionViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            Cotizacion.objects.select_related("institucion", "asesor")
            .prefetch_related("detalles__producto__editorial")
            .order_by("-id")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CotizacionDetalleSerializer
        return CotizacionPanelSerializer


# =========================================================
# ✅ ADOPCIONES V2 (PANEL + DETALLE)
# =========================================================
class AdopcionViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            Adopcion.objects.select_related("cotizacion__institucion", "cotizacion__asesor")
            .prefetch_related("detalles__producto__editorial", "cotizacion__detalles")
            .order_by("-id")
        )

    def get_serializer_class(self):
        # En tu caso usaremos el mismo serializer para list/retrieve
        return AdopcionPanelSerializer


# =========================================================
# ✅ PEDIDOS V2
# =========================================================
class PedidoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PedidoSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            Pedido.objects.select_related("adopcion__cotizacion")
            .prefetch_related("detalles__producto__editorial")
            .order_by("-id")
        )


# =========================================================
# ✅ CALCULO V2 (OPCIONAL)
# =========================================================
class CalculoViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"], url_path="detalle")
    def detalle(self, request):
        try:
            producto_id = request.data.get("producto_id")
            tipo_venta = request.data.get("tipo_venta")

            if not producto_id:
                return Response({"detail": "producto_id es requerido"}, status=400)

            producto = get_object_or_404(
                Producto.objects.select_related("editorial"),
                id=producto_id
            )

            out = calcular_item(tipo_venta, producto, request.data)
            return Response(out, status=200)

        except Exception as e:
            return Response({"detail": f"Error cálculo: {str(e)}"}, status=400)

    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):
        try:
            tipo_venta = request.data.get("tipo_venta")
            items = request.data.get("items", [])

            if not tipo_venta:
                return Response({"detail": "tipo_venta es requerido"}, status=400)

            if not isinstance(items, list) or not items:
                return Response({"detail": "items debe ser una lista no vacía"}, status=400)

            ids = [x.get("producto_id") for x in items if x.get("producto_id")]
            productos = {
                p.id: p
                for p in Producto.objects.filter(id__in=ids).select_related("editorial")
            }

            out_items = []
            for x in items:
                pid = x.get("producto_id")
                if not pid or pid not in productos:
                    continue
                out_items.append(calcular_item(tipo_venta, productos[pid], x))

            return Response({"tipo_venta": tipo_venta, "items": out_items}, status=200)

        except Exception as e:
            return Response({"detail": f"Error batch: {str(e)}"}, status=400)
