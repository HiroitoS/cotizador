from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # ✅ PRODUCTOS
    ListarProductosView,
    FiltrosProductosView,

    # ✅ COTIZACIONES (V1)
    GuardarCotizacionView,
    ListarCotizacionesView,
    CambiarEstadoCotizacionView,
    CalcularDetalleView,
    DetalleCotizacionRetrieveView,
    PDFCotizacionView,
    CalcularBatchView,

    # ✅ ADOPCIONES (V1)
    CrearAdopcionView,
    ListarAdopcionesView,
    ExportarAdopcionPDFView,

    # ✅ PEDIDOS (V1)
    ListarPedidosView,
    CrearPedidoView,

    # ✅ MAESTROS (V1)
    ListarAsesoresView,
    ListarColegiosView,
)

from .services_excel import (
    ExportCotizacionesExcelView,
    ExportAdopcionesExcelView,
    ExportGeneralExcelView,
)

# ✅ API V2 (ViewSets + Router)
from .api_v2 import (
    ProductoViewSet,
    CotizacionViewSet,
    AdopcionViewSet,
    PedidoViewSet,
)

router = DefaultRouter()
router.register(r"productos", ProductoViewSet, basename="v2-productos")
router.register(r"cotizaciones", CotizacionViewSet, basename="v2-cotizaciones")
router.register(r"adopciones", AdopcionViewSet, basename="v2-adopciones")
router.register(r"pedidos", PedidoViewSet, basename="v2-pedidos")

urlpatterns = [
    # =========================
    # PRODUCTOS (V1)
    # =========================
    path("productos/listar/", ListarProductosView.as_view(), name="listar_productos"),
    path("productos/filtros/", FiltrosProductosView.as_view(), name="productos_filtros"),

    # =========================
    # COTIZACIONES (V1 - NO ROMPER)
    # =========================
    path("cotizaciones/guardar/", GuardarCotizacionView.as_view(), name="guardar_cotizacion"),
    path("cotizaciones/listar/", ListarCotizacionesView.as_view(), name="listar_cotizaciones"),
    path("cotizaciones/<int:pk>/", DetalleCotizacionRetrieveView.as_view(), name="detalle_cotizacion"),
    path("cotizaciones/<int:pk>/estado/", CambiarEstadoCotizacionView.as_view(), name="cambiar_estado_cotizacion"),
    path("cotizaciones/calcular_detalle/", CalcularDetalleView.as_view(), name="calcular_detalle"),
    path("cotizaciones/<int:pk>/pdf/", PDFCotizacionView.as_view(), name="pdf_cotizacion"),
    path("cotizaciones/calcular_batch/", CalcularBatchView.as_view()),


    # =========================
    # ADOPCIONES (V1)
    # =========================
    path("adopciones/crear/", CrearAdopcionView.as_view(), name="crear_adopcion"),
    path("adopciones/listar/", ListarAdopcionesView.as_view(), name="listar_adopciones"),
    path("adopciones/<int:adopcion_id>/pdf/", ExportarAdopcionPDFView.as_view(), name="adopcion_pdf"),

    # =========================
    # PEDIDOS (V1)
    # =========================
    path("pedidos/listar/", ListarPedidosView.as_view(), name="listar_pedidos"),
    path("pedidos/crear/", CrearPedidoView.as_view(), name="crear_pedido"),

    # =========================
    # REPORTES EXCEL (V1)
    # =========================
    path("reportes/cotizaciones_excel/", ExportCotizacionesExcelView.as_view(), name="reporte_cotizaciones_excel"),
    path("reportes/adopciones_excel/", ExportAdopcionesExcelView.as_view(), name="reporte_adopciones_excel"),
    path("reportes/general_excel/", ExportGeneralExcelView.as_view(), name="reporte_general_excel"),

    # =========================
    # MAESTROS (V1)
    # =========================
    path("asesores/listar/", ListarAsesoresView.as_view(), name="listar_asesores"),
    path("colegios/listar/", ListarColegiosView.as_view(), name="listar_colegios"),

    # =========================
    # API V2 (Router)
    # =========================
    path("v2/", include(router.urls)),
]
