from django.http import HttpResponse
from django.views import View
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as XLImage
from decimal import Decimal
import os
from datetime import datetime
from django.conf import settings

from .models import DetalleCotizacion, Adopcion, Pedido


# ============================================================
# 🎨 PALETA CORPORATIVA
# ============================================================
COLOR_AZUL = "1F4E78"
COLOR_BLANCO = "FFFFFF"
COLOR_NEGRO = "000000"


def safe(value):
    if value is None:
        return ""
    # si es numero y es negativo, lo puedes dejar tal cual o clipear.
    # Si quieres mostrar negativos para ROI, comenta esto:
    if isinstance(value, (int, float, Decimal)) and value < 0:
        return float(value)  # ✅ no lo clamps a 0 (mejor para auditoría)
    return value


def ajustar_columnas(ws):
    for col in ws.columns:
        max_length = 0
        letter = None

        for cell in col:
            if hasattr(cell, "column_letter"):
                letter = cell.column_letter
                break

        if not letter:
            continue

        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass

        ws.column_dimensions[letter].width = max_length + 2


def agregar_encabezado_keyfacil(ws, titulo):
    ws.insert_rows(1, amount=2)

    for row in range(1, 3):
        for col in range(1, 12):
            cell = ws.cell(row=row, column=col)
            cell.fill = PatternFill(
                start_color=COLOR_AZUL,
                end_color=COLOR_AZUL,
                fill_type="solid"
            )

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 28

    # Logo (ajusta si tu ruta real es diferente)
    logo_path = os.path.join(settings.BASE_DIR, "cotizador_colegio", "static", "img", "img_book_express.png")
    if os.path.exists(logo_path):
        img = XLImage(logo_path)
        img.width = 150
        img.height = 60
        ws.add_image(img, "A1")

    fecha = datetime.now().strftime("%d/%m/%Y")
    titulo_final = f"{titulo.upper()} – {fecha}"

    ws.merge_cells("D1:K2")
    c = ws["D1"]
    c.value = titulo_final
    c.font = Font(size=18, bold=True, color=COLOR_BLANCO)
    c.alignment = Alignment(horizontal="center", vertical="center")


def escribir_encabezados(ws, columnas):
    while ws.max_row < 3:
        ws.append([])

    ws.append(columnas)
    fila = ws.max_row

    for cell in ws[fila]:
        cell.fill = PatternFill(start_color=COLOR_AZUL, end_color=COLOR_AZUL, fill_type="solid")
        cell.font = Font(color=COLOR_BLANCO, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(
            left=Side(style="thin", color=COLOR_NEGRO),
            right=Side(style="thin", color=COLOR_NEGRO),
            top=Side(style="thin", color=COLOR_NEGRO),
            bottom=Side(style="thin", color=COLOR_NEGRO),
        )


# ============================================================
# 📌 EXPORTAR COTIZACIONES
# ============================================================
class ExportCotizacionesExcelView(View):
    def get(self, request, *args, **kwargs):
        detalles = (
            DetalleCotizacion.objects
            .select_related("cotizacion", "cotizacion__asesor", "cotizacion__institucion", "producto", "producto__editorial")
            .all()
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Cotizaciones"

        agregar_encabezado_keyfacil(ws, "REPORTE DE COTIZACIONES")

        columnas = [
            "Editorial", "Nivel", "Grado", "Área", "Producto",
            "PVP 2026", "Tipo de Venta",
            "Precio BE", "% Desc Proveedor", "Precio Proveedor",
            "% Desc IE", "Dscto IE (S/)", "Precio IE",
            "Precio PPFF",
            "% Desc Consigna", "Comisión (S/)",
            "Utilidad IE", "ROI (S/)",
            "Asesor", "Institución", "Fecha",
        ]

        escribir_encabezados(ws, columnas)

        for d in detalles:
            cot = d.cotizacion
            prod = d.producto

            # texto tipo venta
            tv = (getattr(d, "tipo_venta", "") or "").upper()
            tv_map = {
                "PV": "Punto de Venta",
                "PUNTO_DE_VENTA": "Punto de Venta",
                "FERIA": "Feria",
                "CONSIGNA": "Consignación",
            }
            tv_txt = tv_map.get(tv, tv)

            precio_be = getattr(d, "precio_be", None)
            descuento_ie = getattr(d, "descuento_ie", None)
            descuento_ie_monto = None
            precio_ie = getattr(d, "precio_ie", None)

            if precio_be is not None and descuento_ie is not None:
                try:
                    descuento_ie_monto = (Decimal(str(precio_be)) * Decimal(str(descuento_ie)) / Decimal("100")).quantize(Decimal("0.01"))
                except Exception:
                    descuento_ie_monto = ""

            ws.append([
                safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else "",
                safe(getattr(prod, "nivel", "")),
                safe(getattr(prod, "grado", "")),
                safe(getattr(prod, "area", "")),
                safe(getattr(prod, "nombre", "")),
                safe(getattr(prod, "pvp_2026", "")),
                safe(tv_txt),

                safe(precio_be),
                safe(getattr(d, "desc_proveedor", "")),
                safe(getattr(d, "precio_proveedor", "")),

                safe(descuento_ie),
                safe(descuento_ie_monto),
                safe(precio_ie),

                safe(getattr(d, "precio_ppff", "")),
                safe(getattr(d, "desc_consigna", "")),
                safe(getattr(d, "comision", "")),

                safe(getattr(d, "utilidad_ie", "")),
                safe(getattr(d, "roi_ie", "")),

                safe(getattr(cot.asesor, "nombre", "")) if getattr(cot, "asesor", None) else "",
                safe(getattr(cot.institucion, "nombre", "")) if getattr(cot, "institucion", None) else "",
                safe(cot.fecha.strftime("%d/%m/%Y") if getattr(cot, "fecha", None) else ""),
            ])

        ajustar_columnas(ws)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Cotizaciones_{timezone.now().date()}.xlsx"'
        wb.save(response)
        return response


# ============================================================
# 📌 EXPORTAR ADOPCIONES
# ============================================================
class ExportAdopcionesExcelView(View):
    def get(self, request, *args, **kwargs):
        wb = Workbook()
        ws = wb.active
        ws.title = "Adopciones"

        agregar_encabezado_keyfacil(ws, "REPORTE DE ADOPCIONES")

        columnas = [
            "N° Cotización", "Institución", "Asesor",
            "Editorial", "Producto", "Nivel", "Grado", "Área",
            "Cantidad", "Mes Lectura",
        ]
        escribir_encabezados(ws, columnas)

        adopciones = (
            Adopcion.objects
            .select_related("cotizacion", "cotizacion__institucion", "cotizacion__asesor")
            .prefetch_related("detalles__producto", "detalles__producto__editorial")
        )

        for adop in adopciones:
            for det in adop.detalles.all():
                prod = det.producto
                ws.append([
                    safe(getattr(adop.cotizacion, "numero_cotizacion", "")),
                    safe(getattr(adop.cotizacion.institucion, "nombre", "")) if getattr(adop.cotizacion, "institucion", None) else "",
                    safe(getattr(adop.cotizacion.asesor, "nombre", "")) if getattr(adop.cotizacion, "asesor", None) else "",

                    safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else "",
                    safe(getattr(prod, "nombre", "")),
                    safe(getattr(prod, "nivel", "")),
                    safe(getattr(prod, "grado", "")),
                    safe(getattr(prod, "area", "")),

                    safe(getattr(det, "cantidad_adoptada", "")),
                    safe(getattr(det, "mes_lectura", "")),
                ])

        ajustar_columnas(ws)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Adopciones_{timezone.now().date()}.xlsx"'
        wb.save(response)
        return response


# ============================================================
# 📌 EXPORTACIÓN GENERAL (2 HOJAS)
# ============================================================
class ExportGeneralExcelView(View):
    def get(self, request, *args, **kwargs):
        wb = Workbook()

        # Hoja 1: Cotizaciones
        ws1 = wb.active
        ws1.title = "Cotizaciones"
        agregar_encabezado_keyfacil(ws1, "REPORTE GENERAL – COTIZACIONES")

        columnas_cot = [
            "Editorial", "Nivel", "Grado", "Área", "Producto",
            "PVP 2026", "Tipo de Venta",
            "Precio BE", "% Desc Proveedor", "Precio Proveedor",
            "% Desc IE", "Dscto IE (S/)", "Precio IE",
            "Precio PPFF",
            "% Desc Consigna", "Comisión (S/)",
            "Utilidad IE", "ROI (S/)",
            "Asesor", "Institución", "Fecha",
        ]
        escribir_encabezados(ws1, columnas_cot)

        detalles = (
            DetalleCotizacion.objects
            .select_related("cotizacion", "cotizacion__asesor", "cotizacion__institucion", "producto", "producto__editorial")
            .all()
        )

        for d in detalles:
            cot = d.cotizacion
            prod = d.producto

            tv = (getattr(d, "tipo_venta", "") or "").upper()
            tv_map = {
                "PV": "Punto de Venta",
                "PUNTO_DE_VENTA": "Punto de Venta",
                "FERIA": "Feria",
                "CONSIGNA": "Consignación",
            }
            tv_txt = tv_map.get(tv, tv)

            precio_be = getattr(d, "precio_be", None)
            descuento_ie = getattr(d, "descuento_ie", None)
            descuento_ie_monto = None
            if precio_be is not None and descuento_ie is not None:
                try:
                    descuento_ie_monto = (Decimal(str(precio_be)) * Decimal(str(descuento_ie)) / Decimal("100")).quantize(Decimal("0.01"))
                except Exception:
                    descuento_ie_monto = ""

            ws1.append([
                safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else "",
                safe(getattr(prod, "nivel", "")),
                safe(getattr(prod, "grado", "")),
                safe(getattr(prod, "area", "")),
                safe(getattr(prod, "nombre", "")),
                safe(getattr(prod, "pvp_2026", "")),
                safe(tv_txt),

                safe(getattr(d, "precio_be", "")),
                safe(getattr(d, "desc_proveedor", "")),
                safe(getattr(d, "precio_proveedor", "")),

                safe(getattr(d, "descuento_ie", "")),
                safe(descuento_ie_monto),
                safe(getattr(d, "precio_ie", "")),

                safe(getattr(d, "precio_ppff", "")),
                safe(getattr(d, "desc_consigna", "")),
                safe(getattr(d, "comision", "")),

                safe(getattr(d, "utilidad_ie", "")),
                safe(getattr(d, "roi_ie", "")),

                safe(getattr(cot.asesor, "nombre", "")) if getattr(cot, "asesor", None) else "",
                safe(getattr(cot.institucion, "nombre", "")) if getattr(cot, "institucion", None) else "",
                safe(cot.fecha.strftime("%d/%m/%Y") if getattr(cot, "fecha", None) else ""),
            ])

        ajustar_columnas(ws1)

        # Hoja 2: Adopciones
        ws2 = wb.create_sheet("Adopciones")
        agregar_encabezado_keyfacil(ws2, "REPORTE GENERAL – ADOPCIONES")

        columnas_adop = [
            "N° Cotización", "Institución", "Asesor",
            "Editorial", "Producto", "Nivel", "Grado", "Área",
            "Cantidad", "Mes Lectura",
        ]
        escribir_encabezados(ws2, columnas_adop)

        adopciones = (
            Adopcion.objects
            .select_related("cotizacion", "cotizacion__institucion", "cotizacion__asesor")
            .prefetch_related("detalles__producto", "detalles__producto__editorial")
        )

        for adop in adopciones:
            for det in adop.detalles.all():
                prod = det.producto
                ws2.append([
                    safe(getattr(adop.cotizacion, "numero_cotizacion", "")),
                    safe(getattr(adop.cotizacion.institucion, "nombre", "")) if getattr(adop.cotizacion, "institucion", None) else "",
                    safe(getattr(adop.cotizacion.asesor, "nombre", "")) if getattr(adop.cotizacion, "asesor", None) else "",

                    safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else "",
                    safe(getattr(prod, "nombre", "")),
                    safe(getattr(prod, "nivel", "")),
                    safe(getattr(prod, "grado", "")),
                    safe(getattr(prod, "area", "")),

                    safe(getattr(det, "cantidad_adoptada", "")),
                    safe(getattr(det, "mes_lectura", "")),
                ])

        ajustar_columnas(ws2)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="ReporteGeneral_{timezone.now().date()}.xlsx"'
        wb.save(response)
        return response

# ============================================================
# ✅ REPORTES INTERNOS (BOOK EXPRESS) - ADOPCIONES
# ============================================================

from collections import defaultdict


def _tipo_venta_from_cot(cot):
    """
    Tipo de venta se guarda por detalle de cotización.
    Para reportes usamos el primer detalle como referencia.
    """
    try:
        det = cot.detalles.first()
        tv = (getattr(det, "tipo_venta", "") or "").upper().strip()
        tv_map = {
            "PV": "Punto de Venta",
            "PUNTO_DE_VENTA": "Punto de Venta",
            "PUNTO DE VENTA": "Punto de Venta",
            "FERIA": "Feria",
            "CONSIGNA": "Consignación",
        }
        return tv_map.get(tv, tv)
    except Exception:
        return ""


class ExportAdopcionesPorColegioExcelView(View):
    """
    ✅ Reporte interno:
    - Hoja 1: DETALLE (línea por producto adoptado)
    - Hoja 2: RESUMEN (totales por Colegio + Editorial)
    Filtros opcionales por query params:
      - institucion_id
      - editorial_id
      - fecha_desde (YYYY-MM-DD)
      - fecha_hasta (YYYY-MM-DD)
    """
    def get(self, request, *args, **kwargs):
        institucion_id = request.GET.get("institucion_id")
        editorial_id = request.GET.get("editorial_id")
        fecha_desde = request.GET.get("fecha_desde")
        fecha_hasta = request.GET.get("fecha_hasta")

        qs = (
            Adopcion.objects
            .select_related("cotizacion", "cotizacion__institucion", "cotizacion__asesor")
            .prefetch_related("detalles__producto", "detalles__producto__editorial", "cotizacion__detalles")
        )

        # filtros
        if institucion_id:
            qs = qs.filter(cotizacion__institucion_id=institucion_id)

        if fecha_desde:
            qs = qs.filter(fecha_adopcion__date__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha_adopcion__date__lte=fecha_hasta)

        wb = Workbook()

        # ==========================
        # HOJA DETALLE
        # ==========================
        ws = wb.active
        ws.title = "Detalle"
        agregar_encabezado_keyfacil(ws, "ADOPCIONES POR COLEGIO (DETALLE)")

        columnas = [
            "Fecha Adopción", "N° Cotización",
            "Institución", "Asesor", "Tipo Venta",
            "Editorial", "Producto", "Nivel", "Grado", "Área",
            "Cantidad", "Mes Lectura",
        ]
        escribir_encabezados(ws, columnas)

        # acumulador para resumen: (colegio, editorial) -> total_qty
        resumen = defaultdict(int)

        for adop in qs:
            cot = adop.cotizacion
            inst = getattr(cot, "institucion", None)
            asesor = getattr(cot, "asesor", None)

            tv_txt = _tipo_venta_from_cot(cot)

            fecha_txt = ""
            try:
                if getattr(adop, "fecha_adopcion", None):
                    fecha_txt = adop.fecha_adopcion.strftime("%d/%m/%Y")
            except Exception:
                fecha_txt = ""

            for det in adop.detalles.all():
                prod = det.producto

                # si filtras por editorial_id lo aplicamos por detalle (más correcto)
                if editorial_id and str(getattr(prod, "editorial_id", "")) != str(editorial_id):
                    continue

                editorial_nombre = safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else ""
                inst_nombre = safe(getattr(inst, "nombre", "")) if inst else ""
                asesor_nombre = safe(getattr(asesor, "nombre", "")) if asesor else ""
                qty = int(getattr(det, "cantidad_adoptada", 0) or 0)

                ws.append([
                    safe(fecha_txt),
                    safe(getattr(cot, "numero_cotizacion", "")),
                    inst_nombre,
                    asesor_nombre,
                    safe(tv_txt),

                    editorial_nombre,
                    safe(getattr(prod, "nombre", "")),
                    safe(getattr(prod, "nivel", "")),
                    safe(getattr(prod, "grado", "")),
                    safe(getattr(prod, "area", "")),

                    safe(qty),
                    safe(getattr(det, "mes_lectura", "")),
                ])

                resumen[(inst_nombre, editorial_nombre)] += qty

        ajustar_columnas(ws)

        # ==========================
        # HOJA RESUMEN
        # ==========================
        ws2 = wb.create_sheet("Resumen")
        agregar_encabezado_keyfacil(ws2, "ADOPCIONES POR COLEGIO (RESUMEN)")

        columnas2 = ["Institución", "Editorial", "Total Unidades Adoptadas"]
        escribir_encabezados(ws2, columnas2)

        for (inst_nombre, editorial_nombre), total_qty in sorted(resumen.items(), key=lambda x: (x[0][0], x[0][1])):
            ws2.append([inst_nombre, editorial_nombre, total_qty])

        ajustar_columnas(ws2)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Adopciones_Por_Colegio_{timezone.now().date()}.xlsx"'
        wb.save(response)
        return response


class ExportAdopcionesPorEditorialExcelView(View):
    """
    ✅ Reporte interno:
    - Hoja 1: DETALLE (línea por producto adoptado)
    - Hoja 2: RESUMEN (totales por Editorial + Colegio)
    Filtros opcionales por query params:
      - editorial_id
      - institucion_id
      - fecha_desde (YYYY-MM-DD)
      - fecha_hasta (YYYY-MM-DD)
    """
    def get(self, request, *args, **kwargs):
        institucion_id = request.GET.get("institucion_id")
        editorial_id = request.GET.get("editorial_id")
        fecha_desde = request.GET.get("fecha_desde")
        fecha_hasta = request.GET.get("fecha_hasta")

        qs = (
            Adopcion.objects
            .select_related("cotizacion", "cotizacion__institucion", "cotizacion__asesor")
            .prefetch_related("detalles__producto", "detalles__producto__editorial", "cotizacion__detalles")
        )

        if institucion_id:
            qs = qs.filter(cotizacion__institucion_id=institucion_id)

        if fecha_desde:
            qs = qs.filter(fecha_adopcion__date__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha_adopcion__date__lte=fecha_hasta)

        wb = Workbook()

        # ==========================
        # HOJA DETALLE
        # ==========================
        ws = wb.active
        ws.title = "Detalle"
        agregar_encabezado_keyfacil(ws, "ADOPCIONES POR EDITORIAL (DETALLE)")

        columnas = [
            "Fecha Adopción", "N° Cotización",
            "Editorial", "Producto",
            "Nivel", "Grado", "Área",
            "Institución", "Asesor", "Tipo Venta",
            "Cantidad", "Mes Lectura",
        ]
        escribir_encabezados(ws, columnas)

        resumen = defaultdict(int)  # (editorial, colegio) -> total_qty

        for adop in qs:
            cot = adop.cotizacion
            inst = getattr(cot, "institucion", None)
            asesor = getattr(cot, "asesor", None)
            tv_txt = _tipo_venta_from_cot(cot)

            fecha_txt = ""
            try:
                if getattr(adop, "fecha_adopcion", None):
                    fecha_txt = adop.fecha_adopcion.strftime("%d/%m/%Y")
            except Exception:
                fecha_txt = ""

            inst_nombre = safe(getattr(inst, "nombre", "")) if inst else ""
            asesor_nombre = safe(getattr(asesor, "nombre", "")) if asesor else ""

            for det in adop.detalles.all():
                prod = det.producto
                if editorial_id and str(getattr(prod, "editorial_id", "")) != str(editorial_id):
                    continue

                editorial_nombre = safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else ""
                qty = int(getattr(det, "cantidad_adoptada", 0) or 0)

                ws.append([
                    safe(fecha_txt),
                    safe(getattr(cot, "numero_cotizacion", "")),

                    editorial_nombre,
                    safe(getattr(prod, "nombre", "")),
                    safe(getattr(prod, "nivel", "")),
                    safe(getattr(prod, "grado", "")),
                    safe(getattr(prod, "area", "")),

                    inst_nombre,
                    asesor_nombre,
                    safe(tv_txt),

                    safe(qty),
                    safe(getattr(det, "mes_lectura", "")),
                ])

                resumen[(editorial_nombre, inst_nombre)] += qty

        ajustar_columnas(ws)

        # ==========================
        # HOJA RESUMEN
        # ==========================
        ws2 = wb.create_sheet("Resumen")
        agregar_encabezado_keyfacil(ws2, "ADOPCIONES POR EDITORIAL (RESUMEN)")

        columnas2 = ["Editorial", "Institución", "Total Unidades Adoptadas"]
        escribir_encabezados(ws2, columnas2)

        for (editorial_nombre, inst_nombre), total_qty in sorted(resumen.items(), key=lambda x: (x[0][0], x[0][1])):
            ws2.append([editorial_nombre, inst_nombre, total_qty])

        ajustar_columnas(ws2)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Adopciones_Por_Editorial_{timezone.now().date()}.xlsx"'
        wb.save(response)
        return response


# ============================================================
# ✅ REPORTES INTERNOS (BOOK EXPRESS) - PEDIDOS
# ============================================================

class ExportPedidosPorColegioExcelView(View):
    """
    ✅ Reporte interno:
    - Hoja 1: DETALLE (línea por producto pedido)
    - Hoja 2: RESUMEN (totales por Colegio + Editorial)
    Filtros opcionales:
      - institucion_id
      - editorial_id
      - fecha_desde (YYYY-MM-DD)
      - fecha_hasta (YYYY-MM-DD)
    """
    def get(self, request, *args, **kwargs):
        institucion_id = request.GET.get("institucion_id")
        editorial_id = request.GET.get("editorial_id")
        fecha_desde = request.GET.get("fecha_desde")
        fecha_hasta = request.GET.get("fecha_hasta")

        qs = (
            Pedido.objects
            .select_related(
                "adopcion",
                "adopcion__cotizacion",
                "adopcion__cotizacion__institucion",
                "adopcion__cotizacion__asesor",
            )
            .prefetch_related("detalles__producto", "detalles__producto__editorial", "adopcion__cotizacion__detalles")
        )

        if institucion_id:
            qs = qs.filter(adopcion__cotizacion__institucion_id=institucion_id)

        if fecha_desde:
            qs = qs.filter(fecha_pedido__date__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha_pedido__date__lte=fecha_hasta)

        wb = Workbook()

        # ==========================
        # HOJA DETALLE
        # ==========================
        ws = wb.active
        ws.title = "Detalle"
        agregar_encabezado_keyfacil(ws, "PEDIDOS POR COLEGIO (DETALLE)")

        columnas = [
            "Fecha Pedido", "Estado Pedido",
            "N° Cotización",
            "Institución", "Asesor", "Tipo Venta",
            "Editorial", "Producto", "Nivel", "Grado", "Área",
            "Cantidad",
            "Costo Proveedor (Unit)", "Costo Proveedor (Total)",
        ]
        escribir_encabezados(ws, columnas)

        resumen = defaultdict(int)  # (colegio, editorial) -> total_qty

        for ped in qs:
            adop = ped.adopcion
            cot = adop.cotizacion if adop else None
            inst = getattr(cot, "institucion", None)
            asesor = getattr(cot, "asesor", None)

            tv_txt = _tipo_venta_from_cot(cot) if cot else ""

            fecha_txt = ""
            try:
                if getattr(ped, "fecha_pedido", None):
                    fecha_txt = ped.fecha_pedido.strftime("%d/%m/%Y")
            except Exception:
                fecha_txt = ""

            inst_nombre = safe(getattr(inst, "nombre", "")) if inst else ""
            asesor_nombre = safe(getattr(asesor, "nombre", "")) if asesor else ""
            num_cot = safe(getattr(cot, "numero_cotizacion", "")) if cot else ""

            for det in ped.detalles.all():
                prod = det.producto

                if editorial_id and str(getattr(prod, "editorial_id", "")) != str(editorial_id):
                    continue

                editorial_nombre = safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else ""
                qty = int(getattr(det, "cantidad", 0) or 0)

                costo_unit = getattr(det, "precio_proveedor", None)
                try:
                    costo_total = (Decimal(str(costo_unit or 0)) * Decimal(str(qty))).quantize(Decimal("0.01"))
                except Exception:
                    costo_total = 0

                ws.append([
                    safe(fecha_txt),
                    safe(getattr(ped, "estado", "")),
                    num_cot,
                    inst_nombre,
                    asesor_nombre,
                    safe(tv_txt),

                    editorial_nombre,
                    safe(getattr(prod, "nombre", "")),
                    safe(getattr(prod, "nivel", "")),
                    safe(getattr(prod, "grado", "")),
                    safe(getattr(prod, "area", "")),

                    safe(qty),
                    safe(costo_unit),
                    safe(costo_total),
                ])

                resumen[(inst_nombre, editorial_nombre)] += qty

        ajustar_columnas(ws)

        # ==========================
        # HOJA RESUMEN
        # ==========================
        ws2 = wb.create_sheet("Resumen")
        agregar_encabezado_keyfacil(ws2, "PEDIDOS POR COLEGIO (RESUMEN)")

        columnas2 = ["Institución", "Editorial", "Total Unidades Pedidas"]
        escribir_encabezados(ws2, columnas2)

        for (inst_nombre, editorial_nombre), total_qty in sorted(resumen.items(), key=lambda x: (x[0][0], x[0][1])):
            ws2.append([inst_nombre, editorial_nombre, total_qty])

        ajustar_columnas(ws2)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Pedidos_Por_Colegio_{timezone.now().date()}.xlsx"'
        wb.save(response)
        return response


class ExportPedidosPorEditorialExcelView(View):
    """
    ✅ Reporte interno:
    - Hoja 1: DETALLE (línea por producto pedido)
    - Hoja 2: RESUMEN (totales por Editorial + Colegio)
    Filtros opcionales:
      - editorial_id
      - institucion_id
      - fecha_desde (YYYY-MM-DD)
      - fecha_hasta (YYYY-MM-DD)
    """
    def get(self, request, *args, **kwargs):
        institucion_id = request.GET.get("institucion_id")
        editorial_id = request.GET.get("editorial_id")
        fecha_desde = request.GET.get("fecha_desde")
        fecha_hasta = request.GET.get("fecha_hasta")

        qs = (
            Pedido.objects
            .select_related(
                "adopcion",
                "adopcion__cotizacion",
                "adopcion__cotizacion__institucion",
                "adopcion__cotizacion__asesor",
            )
            .prefetch_related("detalles__producto", "detalles__producto__editorial", "adopcion__cotizacion__detalles")
        )

        if institucion_id:
            qs = qs.filter(adopcion__cotizacion__institucion_id=institucion_id)

        if fecha_desde:
            qs = qs.filter(fecha_pedido__date__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha_pedido__date__lte=fecha_hasta)

        wb = Workbook()

        # ==========================
        # HOJA DETALLE
        # ==========================
        ws = wb.active
        ws.title = "Detalle"
        agregar_encabezado_keyfacil(ws, "PEDIDOS POR EDITORIAL (DETALLE)")

        columnas = [
            "Fecha Pedido", "Estado Pedido",
            "Editorial", "Producto", "Nivel", "Grado", "Área",
            "Institución", "Asesor", "Tipo Venta",
            "Cantidad",
            "Costo Proveedor (Unit)", "Costo Proveedor (Total)",
        ]
        escribir_encabezados(ws, columnas)

        resumen = defaultdict(int)  # (editorial, colegio) -> total_qty

        for ped in qs:
            adop = ped.adopcion
            cot = adop.cotizacion if adop else None
            inst = getattr(cot, "institucion", None)
            asesor = getattr(cot, "asesor", None)

            tv_txt = _tipo_venta_from_cot(cot) if cot else ""

            fecha_txt = ""
            try:
                if getattr(ped, "fecha_pedido", None):
                    fecha_txt = ped.fecha_pedido.strftime("%d/%m/%Y")
            except Exception:
                fecha_txt = ""

            inst_nombre = safe(getattr(inst, "nombre", "")) if inst else ""
            asesor_nombre = safe(getattr(asesor, "nombre", "")) if asesor else ""

            for det in ped.detalles.all():
                prod = det.producto

                if editorial_id and str(getattr(prod, "editorial_id", "")) != str(editorial_id):
                    continue

                editorial_nombre = safe(getattr(prod.editorial, "nombre", "")) if getattr(prod, "editorial", None) else ""
                qty = int(getattr(det, "cantidad", 0) or 0)

                costo_unit = getattr(det, "precio_proveedor", None)
                try:
                    costo_total = (Decimal(str(costo_unit or 0)) * Decimal(str(qty))).quantize(Decimal("0.01"))
                except Exception:
                    costo_total = 0

                ws.append([
                    safe(fecha_txt),
                    safe(getattr(ped, "estado", "")),

                    editorial_nombre,
                    safe(getattr(prod, "nombre", "")),
                    safe(getattr(prod, "nivel", "")),
                    safe(getattr(prod, "grado", "")),
                    safe(getattr(prod, "area", "")),

                    inst_nombre,
                    asesor_nombre,
                    safe(tv_txt),

                    safe(qty),
                    safe(costo_unit),
                    safe(costo_total),
                ])

                resumen[(editorial_nombre, inst_nombre)] += qty

        ajustar_columnas(ws)

        # ==========================
        # HOJA RESUMEN
        # ==========================
        ws2 = wb.create_sheet("Resumen")
        agregar_encabezado_keyfacil(ws2, "PEDIDOS POR EDITORIAL (RESUMEN)")

        columnas2 = ["Editorial", "Institución", "Total Unidades Pedidas"]
        escribir_encabezados(ws2, columnas2)

        for (editorial_nombre, inst_nombre), total_qty in sorted(resumen.items(), key=lambda x: (x[0][0], x[0][1])):
            ws2.append([editorial_nombre, inst_nombre, total_qty])

        ajustar_columnas(ws2)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Pedidos_Por_Editorial_{timezone.now().date()}.xlsx"'
        wb.save(response)
        return response

# =========================
# REPORTE RENTABILIDAD (BOOK EXPRESS)
# =========================
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.http import HttpResponse
from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .models import Cotizacion, DetalleCotizacion, Adopcion, DetalleAdopcion


def _tv_from_cot(cot: Cotizacion) -> str:
    try:
        det = cot.detalles.first()
        return (det.tipo_venta or "") if det else ""
    except Exception:
        return ""


def _tv_legible(raw: str) -> str:
    r = (raw or "").upper().strip()
    m = {
        "PV": "Punto de Venta",
        "PUNTO_DE_VENTA": "Punto de Venta",
        "PUNTO DE VENTA": "Punto de Venta",
        "FERIA": "Feria",
        "CONSIGNA": "Consignación",
    }
    return m.get(r, raw or "")


def _to_decimal(x):
    try:
        if x is None or x == "":
            return Decimal("0")
        return Decimal(str(x))
    except Exception:
        return Decimal("0")


def _money(x: Decimal) -> float:
    # excel trabaja mejor con float (solo para salida)
    try:
        return float(x)
    except Exception:
        return 0.0


def _pct(x: Decimal) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


class ExportRentabilidadExcelView(APIView):
    """
    GET /api/reportes/rentabilidad_excel/?fecha_desde=2026-01-01&fecha_hasta=2026-12-31
                                   &colegio_id=1&editorial_id=2&tipo_venta=CONSIGNA&estado=APROBADA
    Genera un Excel interno (Book Express) de rentabilidad.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # -----------------------
        # Filtros
        # -----------------------
        fecha_desde = request.query_params.get("fecha_desde")  # YYYY-MM-DD
        fecha_hasta = request.query_params.get("fecha_hasta")
        colegio_id = request.query_params.get("colegio_id")
        editorial_id = request.query_params.get("editorial_id")
        tipo_venta = request.query_params.get("tipo_venta")
        estado = request.query_params.get("estado")

        qs = (
            Cotizacion.objects
            .select_related("institucion", "asesor")
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetalleCotizacion.objects.select_related("producto__editorial").order_by("id")
                )
            )
            .order_by("-id")
        )

        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)
        if colegio_id:
            qs = qs.filter(institucion_id=colegio_id)
        if estado:
            qs = qs.filter(estado=estado)

        # tipo_venta es por detalle -> filtramos por el primer detalle (simple y práctico)
        # Si quieres “estricto”, luego lo mejoramos con annotate/subquery.
        if tipo_venta:
            qs = [c for c in qs if _tv_from_cot(c) == tipo_venta]
        else:
            qs = list(qs)

        # -----------------------
        # Mapa de cantidades de adopción (si existe adopción)
        # clave: (cotizacion_id, producto_id) -> cantidad_adoptada
        # -----------------------
        cot_ids = [c.id for c in qs]
        adopciones = (
            Adopcion.objects
            .filter(cotizacion_id__in=cot_ids)
            .prefetch_related("detalles")
        )

        adop_qty = {}
        for a in adopciones:
            for d in a.detalles.all():
                adop_qty[(a.cotizacion_id, d.producto_id)] = int(d.cantidad_adoptada or 0)

        # -----------------------
        # Armar filas detalle + agregados
        # -----------------------
        detalle_rows = []
        sum_colegio = defaultdict(lambda: {
            "unidades": 0,
            "venta": Decimal("0"),
            "costo": Decimal("0"),
            "utilidad": Decimal("0"),
        })
        sum_editorial = defaultdict(lambda: {
            "unidades": 0,
            "venta": Decimal("0"),
            "costo": Decimal("0"),
            "utilidad": Decimal("0"),
        })

        total_utilidad = Decimal("0")
        total_unidades = 0

        for cot in qs:
            tv_raw = _tv_from_cot(cot)
            tv_leg = _tv_legible(tv_raw)

            for det in cot.detalles.all():
                prod = det.producto
                if not prod:
                    continue

                # filtro editorial si viene
                if editorial_id:
                    try:
                        if int(editorial_id) != int(prod.editorial_id or 0):
                            continue
                    except Exception:
                        pass

                colegio = getattr(cot.institucion, "nombre", "") or ""
                asesor = getattr(cot.asesor, "nombre", "") if cot.asesor_id else ""

                editorial = getattr(prod.editorial, "nombre", "") if prod.editorial_id else ""
                producto = getattr(prod, "nombre", "") or ""
                nivel = getattr(prod, "nivel", "") or ""
                area = getattr(prod, "area", "") or ""
                grado = getattr(prod, "grado", "") or ""

                # cantidad: si existe adopción, usar esa cantidad; sino, usar detalle.cantidad o 1
                qty = adop_qty.get((cot.id, det.producto_id))
                if qty is None or qty <= 0:
                    qty = int(det.cantidad or 1)

                # PVP / BE
                pvp = _to_decimal(det.precio_be)

                # Precio IE: siempre
                precio_ie = _to_decimal(det.precio_ie)
                if precio_ie <= 0:
                    # por si tu consigna guarda en otro campo
                    precio_ie = _to_decimal(getattr(det, "precio_consigna", 0))

                # PPFF
                ppff = _to_decimal(det.precio_ppff)

                # Proveedor
                precio_prov = _to_decimal(det.precio_proveedor)

                # ✅ utilidad BE x un = roi_ie (compat histórica en tu modelo)
                utilidad_un = _to_decimal(det.roi_ie)
                utilidad_total = utilidad_un * Decimal(qty)

                # ROI %
                roi_pct = Decimal("0")
                if precio_prov > 0:
                    roi_pct = (utilidad_un / precio_prov) * Decimal("100")

                # “venta” para gerencia:
                # - Si PV/FERIA: normalmente venta real = PPFF (si lo usan así)
                # - Si CONSIGNA: venta = Precio IE (porque no hay PPFF)
                venta_unit = precio_ie
                tvu = (tv_raw or "").upper().strip()
                if tvu in ("PV", "PUNTO_DE_VENTA", "PUNTO DE VENTA", "FERIA"):
                    # si PPFF está, úsalo como venta real
                    if ppff > 0:
                        venta_unit = ppff

                venta_total = venta_unit * Decimal(qty)
                costo_total = precio_prov * Decimal(qty)

                detalle_rows.append([
                    cot.fecha.strftime("%Y-%m-%d") if cot.fecha else "",
                    cot.numero_cotizacion or str(cot.id),
                    cot.estado or "",
                    colegio,
                    asesor,
                    editorial,
                    producto,
                    nivel,
                    area,
                    grado,
                    tv_leg,
                    qty,
                    _money(pvp),
                    _money(precio_ie),
                    _money(ppff),
                    _money(precio_prov),
                    _money(utilidad_un),
                    _money(utilidad_total),
                    _pct(roi_pct),
                ])

                # agregados
                sum_colegio[colegio]["unidades"] += qty
                sum_colegio[colegio]["venta"] += venta_total
                sum_colegio[colegio]["costo"] += costo_total
                sum_colegio[colegio]["utilidad"] += utilidad_total

                sum_editorial[editorial]["unidades"] += qty
                sum_editorial[editorial]["venta"] += venta_total
                sum_editorial[editorial]["costo"] += costo_total
                sum_editorial[editorial]["utilidad"] += utilidad_total

                total_utilidad += utilidad_total
                total_unidades += qty

        # -----------------------
        # Excel
        # -----------------------
        wb = Workbook()

        thin = Side(style="thin", color="CBD5E1")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        header_fill = PatternFill("solid", fgColor="E8F0FE")
        header_font = Font(bold=True, color="111827")
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left = Alignment(horizontal="left", vertical="top", wrap_text=True)

        def style_header(ws, row=1):
            for cell in ws[row]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center
                cell.border = border

        def style_table(ws, start_row=2):
            for row in ws.iter_rows(min_row=start_row, max_row=ws.max_row, max_col=ws.max_column):
                for c in row:
                    c.border = border
                    # alinear texto vs números (simple)
                    if isinstance(c.value, (int, float)):
                        c.alignment = center
                    else:
                        c.alignment = left

        def autosize(ws):
            # autosize simple por longitud (no perfecto, pero ayuda)
            for col in range(1, ws.max_column + 1):
                max_len = 0
                for row in range(1, ws.max_row + 1):
                    v = ws.cell(row=row, column=col).value
                    if v is None:
                        continue
                    v = str(v)
                    if len(v) > max_len:
                        max_len = len(v)
                ws.column_dimensions[get_column_letter(col)].width = min(max(10, max_len + 2), 45)

        # -----------------------
        # Hoja 1: DETALLE
        # -----------------------
        ws = wb.active
        ws.title = "DETALLE"

        headers = [
            "Fecha", "N° Cotización", "Estado",
            "Colegio", "Asesor",
            "Editorial", "Producto", "Nivel", "Área", "Grado",
            "Tipo Venta", "Cantidad",
            "PVP (BE)", "Precio IE", "PPFF",
            "Costo Proveedor",
            "Utilidad BE x un",
            "Utilidad BE Total",
            "ROI %"
        ]
        ws.append(headers)
        for r in detalle_rows:
            ws.append(r)

        style_header(ws, 1)
        style_table(ws, 2)
        ws.freeze_panes = "A2"
        autosize(ws)

        # -----------------------
        # Hoja 2: COLEGIOS
        # -----------------------
        ws2 = wb.create_sheet("COLEGIOS")
        ws2.append(["Colegio", "Unidades", "Venta Total", "Costo Total", "Utilidad Total", "ROI % (aprox)"])

        for colegio, agg in sorted(sum_colegio.items(), key=lambda x: x[1]["utilidad"], reverse=True):
            venta = agg["venta"]
            costo = agg["costo"]
            utilidad = agg["utilidad"]
            roi = Decimal("0")
            if costo > 0:
                roi = (utilidad / costo) * Decimal("100")

            ws2.append([
                colegio,
                agg["unidades"],
                _money(venta),
                _money(costo),
                _money(utilidad),
                _pct(roi),
            ])

        style_header(ws2, 1)
        style_table(ws2, 2)
        ws2.freeze_panes = "A2"
        autosize(ws2)

        # -----------------------
        # Hoja 3: EDITORIALES
        # -----------------------
        ws3 = wb.create_sheet("EDITORIALES")
        ws3.append(["Editorial", "Unidades", "Venta Total", "Costo Total", "Utilidad Total", "ROI % (aprox)"])

        for editorial, agg in sorted(sum_editorial.items(), key=lambda x: x[1]["utilidad"], reverse=True):
            venta = agg["venta"]
            costo = agg["costo"]
            utilidad = agg["utilidad"]
            roi = Decimal("0")
            if costo > 0:
                roi = (utilidad / costo) * Decimal("100")

            ws3.append([
                editorial,
                agg["unidades"],
                _money(venta),
                _money(costo),
                _money(utilidad),
                _pct(roi),
            ])

        style_header(ws3, 1)
        style_table(ws3, 2)
        ws3.freeze_panes = "A2"
        autosize(ws3)

        # -----------------------
        # Hoja 4: KPIS
        # -----------------------
        ws4 = wb.create_sheet("KPIS")
        ws4.append(["Indicador", "Valor"])
        ws4.append(["Total Unidades", total_unidades])
        ws4.append(["Utilidad Total (BE)", _money(total_utilidad)])

        # Top 10 Colegios por utilidad
        ws4.append(["", ""])
        ws4.append(["Top 10 Colegios (por utilidad)", ""])
        ws4.append(["Colegio", "Utilidad"])
        for colegio, agg in list(sorted(sum_colegio.items(), key=lambda x: x[1]["utilidad"], reverse=True))[:10]:
            ws4.append([colegio, _money(agg["utilidad"])])

        # Top 10 Editoriales por utilidad
        ws4.append(["", ""])
        ws4.append(["Top 10 Editoriales (por utilidad)", ""])
        ws4.append(["Editorial", "Utilidad"])
        for editorial, agg in list(sorted(sum_editorial.items(), key=lambda x: x[1]["utilidad"], reverse=True))[:10]:
            ws4.append([editorial, _money(agg["utilidad"])])

        # estilo
        for row in ws4.iter_rows(min_row=1, max_row=ws4.max_row, min_col=1, max_col=2):
            for c in row:
                c.border = border
                c.alignment = left

        ws4["A1"].fill = header_fill
        ws4["A1"].font = header_font
        ws4["B1"].fill = header_fill
        ws4["B1"].font = header_font

        ws4.column_dimensions["A"].width = 40
        ws4.column_dimensions["B"].width = 20

        # -----------------------
        # Respuesta HTTP
        # -----------------------
        resp = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        fname = f"Rentabilidad_BE_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'

        wb.save(resp)
        return resp
