from io import BytesIO
from datetime import datetime
import os

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepInFrame
)

# ====================================================
# Helpers
# ====================================================

def mon(v):
    try:
        if v is None or v == "":
            return "—"
        return f"S/ {float(v):,.2f}"
    except Exception:
        return "—"


def txt(v):
    if v is None:
        return "—"
    s = str(v).strip()
    return s.upper() if s else "—"


def _tipo_venta_legible(raw_tv: str) -> str:
    raw = (raw_tv or "").upper().strip()
    m = {
        "PV": "Punto de Venta",
        "PUNTO_DE_VENTA": "Punto de Venta",
        "PUNTO DE VENTA": "Punto de Venta",
        "FERIA": "Feria",
        "CONSIGNA": "Consignación",
    }
    return m.get(raw, raw or "—")


def _logo(styles, w=110, h=70):
    logo_path = os.path.join(
        settings.BASE_DIR, "cotizador_colegio", "static", "img", "img_book_express.png"
    )
    if os.path.exists(logo_path):
        return Image(logo_path, width=w, height=h)
    return Paragraph("<b>BOOK EXPRESS</b>", styles["H1"])


def _add_style(styles, style_obj):
    """Evita error si el nombre de estilo ya existe."""
    if style_obj.name in styles.byName:
        return
    styles.add(style_obj)


def _styles():
    styles = getSampleStyleSheet()

    _add_style(styles, ParagraphStyle(
        name="TINY",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#6B7280"),
    ))
    _add_style(styles, ParagraphStyle(
        name="SMALL",
        parent=styles["Normal"],
        fontSize=8.2,
        leading=10.5,
    ))
    _add_style(styles, ParagraphStyle(
        name="SMALL_B",
        parent=styles["Normal"],
        fontSize=8.2,
        leading=10.5,
        fontName="Helvetica-Bold",
    ))

    # ✅ NO usar CJK aquí (evita cortar palabras por letras)
    _add_style(styles, ParagraphStyle(
        name="CELL",
        parent=styles["Normal"],
        fontSize=8.0,
        leading=10.2,
        wordWrap="LTR",
    ))
    _add_style(styles, ParagraphStyle(
        name="CELL_C",
        parent=styles["Normal"],
        fontSize=8.0,
        leading=10.2,
        alignment=1,
        wordWrap="LTR",
    ))

    # ✅ SOLO para PRODUCTO: sí permitimos wrap controlado
    _add_style(styles, ParagraphStyle(
        name="CELL_WRAP",
        parent=styles["Normal"],
        fontSize=8.0,
        leading=10.2,
        wordWrap="CJK",
    ))

    _add_style(styles, ParagraphStyle(
        name="H1",
        parent=styles["Title"],
        fontSize=15,
        leading=17,
    ))
    return styles


def _measure_text(s: str, font="Helvetica", size=8.0) -> float:
    s = (s or "").strip()
    if not s:
        return 0
    return stringWidth(s, font, size)


def _clamp(v, a, b):
    return max(a, min(b, v))


def _kif_2lines(paragraph: Paragraph, width: float, height: float = 22):
    """Máx ~2 líneas. Shrink si se pasa."""
    return KeepInFrame(width, height, [paragraph], mode="shrink")


def _kif_1line(paragraph: Paragraph, width: float, height: float = 12):
    """1 línea para columnas cortas (Nivel/Grado/Editorial)."""
    return KeepInFrame(width, height, [paragraph], mode="shrink")


def _table_kv(title: str, rows, total_width: float, styles):
    """
    Tabla tipo ficha (label / value) look ejecutivo.
    Ajusta el ancho de label según la etiqueta más larga.
    """
    labels = [str(r[0]) for r in rows]
    max_label = max([_measure_text(lbl.upper() + ":", "Helvetica-Bold", 8.2) for lbl in labels] + [0])
    label_w = _clamp(max_label + 18, total_width * 0.26, total_width * 0.36)
    value_w = total_width - label_w

    data = [[Paragraph(f"<b>{txt(title)}</b>", styles["SMALL_B"]), ""]]
    for label, value in rows:
        data.append([
            Paragraph(f"<b>{txt(label)}:</b>", styles["SMALL_B"]),
            Paragraph(txt(value), styles["SMALL"]),
        ])

    t = Table(data, colWidths=[label_w, value_w])
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F6FB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0B2B3C")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C7D2E5")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E0EE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _header_row(headers, styles):
    return [Paragraph(f"<b>{h}</b>", styles["CELL_C"]) for h in headers]


def _data_table(data, col_widths, header_bg):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0B2B3C")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C7D2E5")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E0EE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _smart_widths(W, rows_text, base_spec):
    """
    Anchos dinámicos por contenido.
    base_spec: lista de dict {key,min,max,header,weight}
    """
    pref = {}
    for spec in base_spec:
        key = spec["key"]
        mx = 0
        for r in rows_text:
            mx = max(mx, _measure_text(str(r.get(key, ""))[:42], "Helvetica", 8.0))
        mx = max(mx, _measure_text(str(spec.get("header", key)), "Helvetica-Bold", 8.0))
        pref[key] = mx

    total_pref = sum(pref.values()) or 1

    widths = {}
    for spec in base_spec:
        key = spec["key"]
        p = (pref[key] / total_pref) * spec.get("weight", 1.0)
        widths[key] = p

    total_p = sum(widths.values()) or 1
    for k in list(widths.keys()):
        widths[k] = widths[k] / total_p

    clamped = {}
    for spec in base_spec:
        key = spec["key"]
        clamped[key] = _clamp(widths[key], spec["min"], spec["max"])

    s = sum(clamped.values()) or 1
    delta = 1.0 - s

    flex = []
    for spec in base_spec:
        key = spec["key"]
        if delta > 0 and clamped[key] < spec["max"] - 1e-6:
            flex.append(key)
        if delta < 0 and clamped[key] > spec["min"] + 1e-6:
            flex.append(key)

    if flex:
        share = delta / len(flex)
        for key in flex:
            spec = next(x for x in base_spec if x["key"] == key)
            clamped[key] = _clamp(clamped[key] + share, spec["min"], spec["max"])

    return [W * clamped[spec["key"]] for spec in base_spec]


# ====================================================
# PDF COTIZACIÓN (CLIENTE)
# - Siempre "Precio IE"
# - Sin "Utilidad IE"
# - Producto máx 2 líneas
# ====================================================

def generar_pdf_cotizacion(cotizacion) -> bytes:
    buffer = BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=16,
        bottomMargin=16,
    )
    W = doc.width
    elementos = []

    # Header
    head = Table(
        [[
            _logo(styles),
            Paragraph("<b>COTIZACIÓN COMERCIAL</b>", styles["H1"]),
            Paragraph(f"<b>{txt(getattr(cotizacion, 'numero_cotizacion', '') or cotizacion.id)}</b>", styles["SMALL_B"]),
        ]],
        colWidths=[W * 0.18, W * 0.64, W * 0.18],
    )
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
    ]))
    elementos.append(head)
    elementos.append(Spacer(1, 8))

    inst = getattr(cotizacion, "institucion", None)
    asesor = getattr(cotizacion, "asesor", None)
    primer_det = cotizacion.detalles.first() if hasattr(cotizacion, "detalles") else None

    raw_tv = (getattr(primer_det, "tipo_venta", "") or "").upper().strip()
    es_pv = raw_tv in ("PV", "PUNTO_DE_VENTA", "PUNTO DE VENTA", "FERIA")
    tipo_legible = _tipo_venta_legible(raw_tv)

    nombre_ie = getattr(inst, "nombre_ie", None) or getattr(inst, "nombre", None)

    left = _table_kv(
        "1. DATOS DE LA INSTITUCIÓN EDUCATIVA",
        [
            ("Nombre IE", nombre_ie),
            ("Dirección", getattr(inst, "direccion", "")),
            ("Distrito", getattr(inst, "distrito", "")),
            ("Provincia", getattr(inst, "provincia", "")),
            ("Departamento", getattr(inst, "departamento", "")),
            ("Código modular", getattr(inst, "codigo_modular", "")),
        ],
        total_width=W * 0.50,
        styles=styles,
    )
    right = _table_kv(
        "2. REPRESENTANTE COMERCIAL",
        [
            ("Nombre", getattr(asesor, "nombre", "")),
            ("Teléfono", getattr(asesor, "telefono", "")),
            ("Correo", getattr(asesor, "correo", "")),
        ],
        total_width=W * 0.50,
        styles=styles,
    )

    bloques = Table([[left, right]], colWidths=[W * 0.50, W * 0.50])
    bloques.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(bloques)
    elementos.append(Spacer(1, 6))

    tipo_block = _table_kv("3. TIPO DE VENTA", [("Tipo", tipo_legible)], total_width=W, styles=styles)
    elementos.append(tipo_block)
    elementos.append(Spacer(1, 8))

    headers = ["Editorial", "Nivel", "Grado", "Área", "Producto", "PVP 2026", "Precio IE"]
    if es_pv:
        headers.append("PPFF")

    data = [_header_row(headers, styles)]

    detalles = cotizacion.detalles.all() if hasattr(cotizacion, "detalles") else []

    # para anchos dinámicos
    rows_text = []
    for d in detalles:
        p = getattr(d, "producto", None)
        editorial = getattr(getattr(p, "editorial", None), "nombre", "") or getattr(p, "empresa", "")
        rows_text.append({
            "editorial": txt(editorial),
            "nivel": txt(getattr(p, "nivel", "")),
            "grado": txt(getattr(p, "grado", "")),
            "area": txt(getattr(p, "area", "")),
            "producto": txt(getattr(p, "nombre", "") or getattr(p, "descripcion_completa", "")),
            "pvp": mon(getattr(p, "pvp_2026", None) or getattr(p, "pvp_2026_con_igv", None)),
            "precio_ie": mon(getattr(d, "precio_ie", None) or getattr(d, "precio_consigna", None)),
            "ppff": mon(getattr(d, "precio_ppff", None)),
        })

    base = [
        {"key": "editorial", "header": "Editorial", "min": 0.11, "max": 0.16, "weight": 1.0},
        {"key": "nivel", "header": "Nivel", "min": 0.08, "max": 0.12, "weight": 0.9},
        {"key": "grado", "header": "Grado", "min": 0.08, "max": 0.12, "weight": 0.9},
        {"key": "area", "header": "Área", "min": 0.10, "max": 0.16, "weight": 1.0},
        {"key": "producto", "header": "Producto", "min": 0.32, "max": 0.44, "weight": 2.2},
        {"key": "pvp", "header": "PVP 2026", "min": 0.09, "max": 0.12, "weight": 1.0},
        {"key": "precio_ie", "header": "Precio IE", "min": 0.09, "max": 0.12, "weight": 1.0},
    ]
    if es_pv:
        base.append({"key": "ppff", "header": "PPFF", "min": 0.06, "max": 0.10, "weight": 0.9})

    col_widths = _smart_widths(W, rows_text, base)

    for d in detalles:
        p = getattr(d, "producto", None)
        editorial = getattr(getattr(p, "editorial", None), "nombre", "") or getattr(p, "empresa", "")

        producto_val = txt(getattr(p, "nombre", "") or getattr(p, "descripcion_completa", ""))

        producto_cell = _kif_2lines(
            Paragraph(producto_val, styles["CELL_WRAP"]),
            width=col_widths[4],
            height=22
        )

        # ✅ 1 línea para evitar cortes feos por letras
        editorial_cell = _kif_1line(Paragraph(txt(editorial), styles["CELL"]), col_widths[0])
        nivel_cell = _kif_1line(Paragraph(txt(getattr(p, "nivel", "")), styles["CELL_C"]), col_widths[1])
        grado_cell = _kif_1line(Paragraph(txt(getattr(p, "grado", "")), styles["CELL_C"]), col_widths[2])

        pvp = getattr(p, "pvp_2026", None) or getattr(p, "pvp_2026_con_igv", None)

        # siempre "Precio IE"
        precio_ie = getattr(d, "precio_ie", None)
        if precio_ie in (None, "", 0):
            precio_ie = getattr(d, "precio_consigna", None)

        row = [
            editorial_cell,
            nivel_cell,
            grado_cell,
            Paragraph(txt(getattr(p, "area", "")), styles["CELL"]),
            producto_cell,
            Paragraph(mon(pvp), styles["CELL_C"]),
            Paragraph(mon(precio_ie), styles["CELL_C"]),
        ]
        if es_pv:
            row.append(Paragraph(mon(getattr(d, "precio_ppff", None)), styles["CELL_C"]))

        data.append(row)

    tabla = _data_table(data, col_widths, header_bg=colors.HexColor("#EAF1FB"))
    elementos.append(tabla)

    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph(
        f"<para align='center'><font size='7' color='#6B7280'>"
        f"Book Express © {datetime.now().year} — Documento generado automáticamente."
        f"</font></para>",
        styles["TINY"],
    ))

    doc.build(elementos)
    return buffer.getvalue()


# ====================================================
# PDF ADOPCIÓN (CLIENTE)
# - NO muestra Tipo Venta en la tabla
# - Producto máx 2 líneas
# ====================================================

def generar_pdf_adopcion(adopcion) -> bytes:
    buffer = BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=16,
        bottomMargin=16,
    )
    W = doc.width
    elementos = []

    cot = getattr(adopcion, "cotizacion", None)
    inst = getattr(cot, "institucion", None) if cot else None
    asesor = getattr(cot, "asesor", None) if cot else None
    primer_det = cot.detalles.first() if cot and hasattr(cot, "detalles") else None

    raw_tv = (getattr(primer_det, "tipo_venta", "") or "").upper().strip()
    tipo_legible = _tipo_venta_legible(raw_tv)

    adop_num = getattr(adopcion, "id", "")

    head = Table(
        [[
            _logo(styles),
            Paragraph("<b>FICHA DE ADOPCIÓN</b>", styles["H1"]),
            Paragraph(f"<b>ADOP-{str(adop_num).zfill(5)}</b>", styles["SMALL_B"]),
        ]],
        colWidths=[W * 0.18, W * 0.64, W * 0.18],
    )
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
    ]))
    elementos.append(head)
    elementos.append(Spacer(1, 8))

    nombre_ie = getattr(inst, "nombre_ie", None) or getattr(inst, "nombre", None)

    left = _table_kv(
        "1. DATOS DE LA INSTITUCIÓN EDUCATIVA",
        [
            ("Nombre IE", nombre_ie),
            ("Dirección", getattr(inst, "direccion", "")),
            ("Distrito", getattr(inst, "distrito", "")),
            ("Provincia", getattr(inst, "provincia", "")),
            ("Departamento", getattr(inst, "departamento", "")),
        ],
        total_width=W * 0.50,
        styles=styles,
    )
    right = _table_kv(
        "2. REPRESENTANTE COMERCIAL",
        [
            ("Nombre", getattr(asesor, "nombre", "")),
            ("Teléfono", getattr(asesor, "telefono", "")),
            ("Correo", getattr(asesor, "correo", "")),
        ],
        total_width=W * 0.50,
        styles=styles,
    )

    bloques = Table([[left, right]], colWidths=[W * 0.50, W * 0.50])
    bloques.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(bloques)
    elementos.append(Spacer(1, 6))

    tipo_block = _table_kv("3. TIPO DE VENTA", [("Tipo", tipo_legible)], total_width=W, styles=styles)
    elementos.append(tipo_block)
    elementos.append(Spacer(1, 8))

    headers = ["Editorial", "Nivel", "Grado", "Área", "Producto", "Cantidad", "Mes Lectura"]
    data = [_header_row(headers, styles)]

    detalles = adopcion.detalles.all() if hasattr(adopcion, "detalles") else []

    rows_text = []
    for d in detalles:
        p = getattr(d, "producto", None)
        editorial = getattr(getattr(p, "editorial", None), "nombre", "") or getattr(p, "empresa", "")
        rows_text.append({
            "editorial": txt(editorial),
            "nivel": txt(getattr(p, "nivel", "")),
            "grado": txt(getattr(p, "grado", "")),
            "area": txt(getattr(p, "area", "")),
            "producto": txt(getattr(p, "nombre", "") or getattr(p, "descripcion_completa", "")),
            "cantidad": str(getattr(d, "cantidad_adoptada", "")),
            "mes": str(getattr(d, "mes_lectura", "") or "—"),
        })

    base = [
        {"key": "editorial", "header": "Editorial", "min": 0.12, "max": 0.18, "weight": 1.0},
        {"key": "nivel", "header": "Nivel", "min": 0.09, "max": 0.13, "weight": 0.9},
        {"key": "grado", "header": "Grado", "min": 0.09, "max": 0.13, "weight": 0.9},
        {"key": "area", "header": "Área", "min": 0.12, "max": 0.18, "weight": 1.0},
        {"key": "producto", "header": "Producto", "min": 0.36, "max": 0.46, "weight": 2.2},
        {"key": "cantidad", "header": "Cantidad", "min": 0.07, "max": 0.10, "weight": 0.9},
        {"key": "mes", "header": "Mes Lectura", "min": 0.08, "max": 0.12, "weight": 0.9},
    ]

    col_widths = _smart_widths(W, rows_text, base)

    for d in detalles:
        p = getattr(d, "producto", None)
        editorial = getattr(getattr(p, "editorial", None), "nombre", "") or getattr(p, "empresa", "")

        producto_val = txt(getattr(p, "nombre", "") or getattr(p, "descripcion_completa", ""))

        producto_cell = _kif_2lines(
            Paragraph(producto_val, styles["CELL_WRAP"]),
            width=col_widths[4],
            height=22
        )

        editorial_cell = _kif_1line(Paragraph(txt(editorial), styles["CELL"]), col_widths[0])
        nivel_cell = _kif_1line(Paragraph(txt(getattr(p, "nivel", "")), styles["CELL_C"]), col_widths[1])
        grado_cell = _kif_1line(Paragraph(txt(getattr(p, "grado", "")), styles["CELL_C"]), col_widths[2])

        mes = getattr(d, "mes_lectura", None) or "—"

        row = [
            editorial_cell,
            nivel_cell,
            grado_cell,
            Paragraph(txt(getattr(p, "area", "")), styles["CELL"]),
            producto_cell,
            Paragraph(txt(getattr(d, "cantidad_adoptada", "")), styles["CELL_C"]),
            Paragraph(txt(mes), styles["CELL_C"]),
        ]
        data.append(row)

    tabla = _data_table(data, col_widths, header_bg=colors.HexColor("#ECF7F1"))
    elementos.append(tabla)

    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph(
        f"<para align='center'><font size='7' color='#6B7280'>"
        f"Book Express © {datetime.now().year} — Documento generado automáticamente."
        f"</font></para>",
        styles["TINY"],
    ))

    doc.build(elementos)
    return buffer.getvalue()
