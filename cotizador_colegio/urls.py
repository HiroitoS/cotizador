from django.urls import path
from .views import (
    ListarLibrosView,
    GuardarCotizacionView,
    ListarCotizacionesView,
    CambiarEstadoCotizacionView,
    CalcularDetalleView,
    DetalleCotizacionRetrieveView,
    CrearAdopcionView,
    ListarPedidosView,
    filtros_libros,
    ListarAsesoresView,
    ListarColegiosView,
    PDFCotizacionView,
    PDFAdopcionView,
    ExportCotizacionesExcelView,
    ExportAdopcionesExcelView,
    ExportarAdopcionPDFView,
    ExportGeneralExcelView,
    ListarAdopcionesView,
)

urlpatterns = [
    # Libros y filtros
    path("libros/", ListarLibrosView.as_view(), name="listar_libros"),
    path("libros/filtros/", filtros_libros, name="filtros_libros"),

    # Cotizaciones
    path("cotizaciones/guardar/", GuardarCotizacionView.as_view(), name="guardar_cotizacion"),
    path("cotizaciones/listar/", ListarCotizacionesView.as_view(), name="listar_cotizaciones"),
    path("cotizaciones/<int:pk>/", DetalleCotizacionRetrieveView.as_view(), name="detalle_cotizacion"),
    path("cotizaciones/estado/<int:pk>/", CambiarEstadoCotizacionView.as_view(), name="cambiar_estado_cotizacion"),
    path("cotizaciones/calcular_detalle/", CalcularDetalleView.as_view(), name="calcular_detalle"),

    # PDFs
    path("adopciones/<int:adopcion_id>/pdf/", ExportarAdopcionPDFView.as_view(), name="exportar_adopcion_pdf"),
    path("cotizaciones/<int:pk>/pdf/", PDFCotizacionView.as_view(), name="pdf_cotizacion"),
    path("adopciones/<int:pk>/pdf/", PDFAdopcionView.as_view(), name="pdf_adopcion"),

    # Adopciones
    path("adopciones/crear/", CrearAdopcionView.as_view(), name="crear_adopcion"),
    path("adopciones/listar/", ListarAdopcionesView.as_view(), name="listar_adopciones"),

    # Pedidos
    path("pedidos/listar/", ListarPedidosView.as_view(), name="listar_pedidos"),

    # Export Excel (reportes globales)
    path("reportes/cotizaciones_excel/", ExportCotizacionesExcelView.as_view(), name="reporte_cotizaciones_excel"),
    path("reportes/adopciones_excel/", ExportAdopcionesExcelView.as_view(), name="reporte_adopciones_excel"),
    path("reportes/general_excel/", ExportGeneralExcelView.as_view(), name="reporte_general_excel"),
    
    # ASESORES y COLEGIOS (ENDPOINTS QUE NECESITA TU FRONT)
    path("asesores/listar/", ListarAsesoresView.as_view(), name="listar_asesores"),
    path("colegios/listar/", ListarColegiosView.as_view(), name="listar_colegios"),

]
