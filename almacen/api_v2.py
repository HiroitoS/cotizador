from django.db import transaction
from django.db.models import Q, F

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import (
    Almacen,
    Ingreso,
    Transferencia,
    Stock,
    MovimientoStock,
    EstadoTransferencia,
)

from .serializers import (
    AlmacenSerializer,
    IngresoWriteSerializer,
    IngresoReadSerializer,
    TransferenciaWriteSerializer,
    TransferenciaReadSerializer,
    StockSerializer,
    StockAlertaSerializer,
    StockConfigSerializer,
    MovimientoStockSerializer,
    AjusteStockSerializer,
)

from .services_stock import (
    aplicar_ingreso,
    confirmar_transferencia,
    confirmar_ajuste,
)


class StandardPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 200


# =========================================================
# ALMACENES
# =========================================================
class AlmacenViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Almacen.objects.filter(activo=True).order_by("tipo", "nombre")
    serializer_class = AlmacenSerializer
    pagination_class = None


# =========================================================
# INGRESOS
# =========================================================
class IngresoViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = (
            Ingreso.objects.select_related("almacen_destino", "proveedor")
            .prefetch_related("detalles__producto__editorial")
            .order_by("-id")
        )

        search = self.request.query_params.get("search")
        proveedor = self.request.query_params.get("proveedor")
        almacen = self.request.query_params.get("almacen")

        if search:
            qs = qs.filter(
                Q(numero_documento__icontains=search)
                | Q(proveedor__nombre__icontains=search)
            )
        if proveedor:
            qs = qs.filter(proveedor_id=proveedor)
        if almacen:
            qs = qs.filter(almacen_destino_id=almacen)

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return IngresoWriteSerializer
        return IngresoReadSerializer

    @action(detail=True, methods=["post"], url_path="procesar")
    def procesar(self, request, pk=None):
        ingreso = self.get_object()
        try:
            with transaction.atomic():
                aplicar_ingreso(ingreso)
            return Response({"detail": "Ingreso procesado correctamente."}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


# =========================================================
# TRANSFERENCIAS
# =========================================================
class TransferenciaViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = (
            Transferencia.objects.select_related("almacen_origen", "almacen_destino")
            .prefetch_related("detalles__producto__editorial")
            .order_by("-id")
        )

        search = self.request.query_params.get("search")
        estado = self.request.query_params.get("estado")
        origen = self.request.query_params.get("origen")
        destino = self.request.query_params.get("destino")

        if search:
            qs = qs.filter(numero_documento__icontains=search)
        if estado:
            qs = qs.filter(estado=estado)
        if origen:
            qs = qs.filter(almacen_origen_id=origen)
        if destino:
            qs = qs.filter(almacen_destino_id=destino)

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TransferenciaWriteSerializer
        return TransferenciaReadSerializer

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        trans = self.get_object()

        if trans.estado != EstadoTransferencia.BORRADOR:
            return Response({"detail": "Solo se puede confirmar una transferencia en BORRADOR."}, status=400)

        try:
            with transaction.atomic():
                confirmar_transferencia(trans)
            return Response({"detail": "Transferencia confirmada correctamente."}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, pk=None):
        trans = self.get_object()
        if trans.estado == EstadoTransferencia.CONFIRMADA:
            return Response({"detail": "No se puede anular una transferencia CONFIRMADA."}, status=400)

        trans.estado = EstadoTransferencia.ANULADA
        trans.save(update_fields=["estado"])
        return Response({"detail": "Transferencia anulada."}, status=200)


# =========================================================
# STOCK + ALERTAS + CONFIG
# =========================================================
class StockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Stock.objects.select_related("almacen", "producto__editorial").order_by(
            "almacen__tipo", "producto__nombre"
        )

        almacen = self.request.query_params.get("almacen")
        editorial = self.request.query_params.get("editorial")
        search = self.request.query_params.get("search")

        if almacen:
            qs = qs.filter(almacen_id=almacen)
        if editorial:
            qs = qs.filter(producto__editorial_id=editorial)
        if search:
            qs = qs.filter(
                Q(producto__nombre__icontains=search)
                | Q(producto__codigo__icontains=search)
            )

        return qs

    # ✅ GET /api/almacen/v2/stock/alertas/?almacen=1
    @action(detail=False, methods=["get"], url_path="alertas")
    def alertas(self, request):
        qs = self.get_queryset()

        # Solo donde hay configuración de mínimos/reposición
        qs = qs.filter(Q(stock_minimo__gt=0) | Q(punto_reposicion__gt=0))

        # Alerta si está <= mínimo o <= reposición
        qs = qs.filter(
            Q(stock_minimo__gt=0, cantidad_actual__lte=F("stock_minimo")) |
            Q(punto_reposicion__gt=0, cantidad_actual__lte=F("punto_reposicion"))
        )

        page = self.paginate_queryset(qs)
        ser = StockAlertaSerializer(page if page is not None else qs, many=True)

        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    # ✅ GET/PATCH /api/almacen/v2/stock/{id}/config/
    @action(detail=True, methods=["get", "patch"], url_path="config")
    def config(self, request, pk=None):
        stock = self.get_object()

        # GET: ver configuración actual (para navegador)
        if request.method.lower() == "get":
            return Response(StockConfigSerializer(stock).data, status=200)

        # PATCH: actualizar config
        ser = StockConfigSerializer(stock, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(StockConfigSerializer(stock).data, status=200)


# =========================================================
# KARDEX / MOVIMIENTOS
# =========================================================
class MovimientoStockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovimientoStockSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = MovimientoStock.objects.select_related("almacen", "producto__editorial").order_by("-fecha", "-id")

        almacen = self.request.query_params.get("almacen")
        producto = self.request.query_params.get("producto")
        tipo = self.request.query_params.get("tipo")
        search = self.request.query_params.get("search")

        if almacen:
            qs = qs.filter(almacen_id=almacen)
        if producto:
            qs = qs.filter(producto_id=producto)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if search:
            qs = qs.filter(
                Q(numero_documento__icontains=search)
                | Q(producto__nombre__icontains=search)
            )

        return qs


# =========================================================
# AJUSTES (endpoint simple)
# POST /api/almacen/v2/ajustes/
# =========================================================
class AjusteStockViewSet(viewsets.ViewSet):
    serializer_class = AjusteStockSerializer

    def create(self, request):
        ser = AjusteStockSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        data = ser.validated_data
        try:
            with transaction.atomic():
                confirmar_ajuste(
                    almacen_id=data["almacen_id"],
                    motivo=data["motivo"],
                    tipo_documento=data.get("tipo_documento", "OTRO"),
                    numero_documento=data.get("numero_documento", ""),
                    items=data["items"],
                )
            return Response({"detail": "Ajuste aplicado correctamente."}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
