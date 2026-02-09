from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_v2 import (
    AlmacenViewSet,
    IngresoViewSet,
    TransferenciaViewSet,
    StockViewSet,
    MovimientoStockViewSet,
    AjusteStockViewSet,
)

router = DefaultRouter()
router.register(r"almacenes", AlmacenViewSet, basename="almacen-almacenes")
router.register(r"ingresos", IngresoViewSet, basename="almacen-ingresos")
router.register(r"transferencias", TransferenciaViewSet, basename="almacen-transferencias")
router.register(r"stock", StockViewSet, basename="almacen-stock")
router.register(r"movimientos", MovimientoStockViewSet, basename="almacen-movimientos")
router.register(r"ajustes", AjusteStockViewSet, basename="almacen-ajustes")

urlpatterns = [
    path("v2/", include(router.urls)),
]
