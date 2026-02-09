from decimal import Decimal
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Kit
from .serializers import KitWriteSerializer, KitReadSerializer
from .services import costear_kit, expandir_kit

DEC_0 = Decimal("0.00")


class StandardPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 200


class KitViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        pvp_expr = Coalesce(
            F("items__cantidad") * F("items__producto__pvp_2026"),
            Value(0),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )

        return (
            Kit.objects.prefetch_related("items__producto__editorial")
            .annotate(
                total_items=Coalesce(Sum("items__cantidad"), Value(0)),
                pvp_total=Coalesce(Sum(pvp_expr), Value(0), output_field=DecimalField(max_digits=14, decimal_places=2)),
            )
            .order_by("-id")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return KitWriteSerializer
        return KitReadSerializer

    @action(detail=True, methods=["get"], url_path="resumen")
    def resumen(self, request, pk=None):
        """
        GET /api/kit/v1/kits/{id}/resumen/?almacen=1
        Devuelve pvp_total (kit) + costo_estimado_total (desde Stock.costo_promedio por almacén)
        """
        kit = self.get_object()
        almacen_id = request.query_params.get("almacen")

        if not almacen_id:
            # Solo PVP (sin costeo)
            return Response(
                {
                    "kit_id": kit.id,
                    "nombre": kit.nombre,
                    "pvp_total": str(getattr(kit, "pvp_total", DEC_0)),
                    "costo_estimado_total": None,
                    "almacen_id": None,
                    "nota": "Envía ?almacen=ID para calcular costo_estimado_total.",
                },
                status=200,
            )

        data = costear_kit(kit=kit, almacen_id=int(almacen_id))
        data["nota"] = "costo_estimado_total usa Stock.costo_promedio del almacén."
        return Response(data, status=200)

    @action(detail=True, methods=["get"], url_path="expandir")
    def expandir(self, request, pk=None):
        """
        GET /api/kit/v1/kits/{id}/expandir/?multiplicador=1
        Devuelve la receta del kit (lista de productos con cantidades).
        Útil para picking / almacén / preparación de packs.
        """
        kit = self.get_object()
        multiplicador = int(request.query_params.get("multiplicador", 1) or 1)

        lineas = expandir_kit(kit, multiplicador=multiplicador)
        return Response(
            {
                "kit_id": kit.id,
                "nombre": kit.nombre,
                "multiplicador": multiplicador,
                "lineas": [l.__dict__ for l in lineas],
            },
            status=200,
        )
