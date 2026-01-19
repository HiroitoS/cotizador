from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from django.conf import settings
import os
from datetime import datetime


# ====================================================
# 🔧 FUNCIONES AUXILIARES
# ====================================================

def mon(v):
    """Devuelve número en formato S/ con 2 decimales o guion si es None/0 inválido."""
    try:
        if v is None:
            return "—"
        return f"S/ {float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def txt(v):
    """Texto limpio en mayúsculas o guion si está vacío."""
    if v is None or str(v).strip() == "":
        return "—"
    return str(v).upper()


# ====================================================
# 🧾 COTIZACIÓN PDF
# ====================================================

def generar_pdf_cotizacion(cotizacion, response):
    """Genera PDF horizontal de la cotización con tipo de venta como columna adicional."""
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    elementos = []
    styles = getSampleStyleSheet()

    # ---- Logo y encabezado ----
    logo_path = os.path.join(
        settings.BASE_DIR, "cotizador_colegio", "static", "img", "img_book_express.png"
    )
    logo = (
        Image(logo_path, width=4 * cm, height=3 * cm)
        if os.path.exists(logo_path)
        else Paragraph("<b>BOOK EXPRESS</b>", styles["Title"])
    )
    titulo = Paragraph("<b>COTIZACIÓN COMERCIAL</b>", styles["Title"])
    numero = Paragraph(f"<b>{cotizacion.numero_cotizacion}</b>", styles["Normal"])

    encabezado = Table([[logo, titulo, numero]], colWidths=[5 * cm, 18 * cm, 5 * cm])
    encabezado.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ])
    )
    elementos.append(encabezado)
    elementos.append(Spacer(1, 0.5 * cm))

    inst = cotizacion.institucion
    asesor = cotizacion.asesor
    detalles = cotizacion.detalles.all()

    # ---- DATOS IE ----
    nombre_ie = getattr(inst, "nombre_ie", None) or getattr(inst, "nombre", "—")

    datos_ie = [
        ["1. DATOS DE LA INSTITUCIÓN EDUCATIVA", ""],
        ["Nombre IE:", txt(nombre_ie)],
        ["Nivel educativo:", txt(getattr(inst, "nivel_educativo", ""))],
        ["Dirección:", txt(getattr(inst, "direccion", ""))],
        ["Provincia:", txt(getattr(inst, "provincia", ""))],
        ["Teléfono:", txt(getattr(inst, "telefono", ""))],
        ["Directivo(a):", txt(getattr(inst, "director", ""))],
    ]
    datos_ie2 = [
        ["Código Modular:", txt(getattr(inst, "codigo_modular", ""))],
        ["Distrito:", txt(getattr(inst, "distrito", ""))],
        ["Departamento:", txt(getattr(inst, "departamento", ""))],
        ["Correo:", txt(getattr(inst, "correo_institucional", ""))],
        ["", ""], ["", ""], ["", ""],
    ]

    tabla_ie = Table([[Table(datos_ie), Table(datos_ie2)]], colWidths=[12 * cm, 12 * cm])
    tabla_ie.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ])
    )
    elementos.append(tabla_ie)
    elementos.append(Spacer(1, 0.5 * cm))

    # ---- DATOS ASESOR ----
    datos_asesor = [
        ["2. DATOS DEL REPRESENTANTE COMERCIAL", ""],
        ["Nombre:", txt(getattr(asesor, "nombre", ""))],
        ["Teléfono:", txt(getattr(asesor, "telefono", ""))],
        ["Zona / Región:", txt(getattr(asesor, "zona", ""))],
        ["Empresa / Editorial:", "BOOK EXPRESS"],
        ["Correo:", txt(getattr(asesor, "correo", ""))],
    ]
    tabla_asesor = Table(datos_asesor, colWidths=[6 * cm, 16 * cm])
    tabla_asesor.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elementos.append(tabla_asesor)
    elementos.append(Spacer(1, 0.3 * cm))

    # ---- Tipo de Venta ----
    primer_det = detalles.first()
    if primer_det:
        raw_tv = (primer_det.tipo_venta or "").upper().strip()
        MAPEO = {
            "PV": "Punto de Venta",
            "PUNTO_DE_VENTA": "Punto de Venta",
            "PUNTO DE VENTA": "Punto de Venta",
            "FERIA": "Feria",
            "CONSIGNA": "Consignación",
        }
        tipo_legible = MAPEO.get(raw_tv, raw_tv)
    else:
        tipo_legible = "—"

    tabla_tipo = Table(
        [
            ["3. TIPO DE VENTA", ""],
            ["Tipo de Venta:", tipo_legible],
        ],
        colWidths=[6 * cm, 16 * cm],
    )
    tabla_tipo.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elementos.append(tabla_tipo)
    elementos.append(Spacer(1, 0.4 * cm))

    # ---- TABLA PRINCIPAL con columna TIPO DE VENTA ----
    headers = [
        "Editorial", "Nivel", "Grado", "Área", "Descripción", "PVP 2026", "Tipo Venta"
    ]

    tipo_up = raw_tv if primer_det else "PV"

    if tipo_up in ("FERIA", "PV", "PUNTO_DE_VENTA", "PUNTO DE VENTA"):
        headers += ["Precio IE", "PPFF", "Utilidad IE"]
        modo = "PV"
    else:
        headers += ["Precio BE", "Precio Consigna"]
        modo = "CONSIGNA"

    data = [headers]

    for d in detalles:
        fila = [
            d.libro.empresa,
            d.libro.nivel,
            d.libro.grado,
            d.libro.area,
            d.libro.descripcion_completa,
            mon(d.libro.pvp_2026_con_igv),
            tipo_legible,
        ]
        if modo == "PV":
            fila += [
                mon(d.precio_ie),
                mon(d.precio_ppff),
                mon(d.utilidad_ie),
            ]
        else:
            fila += [
                mon(d.precio_be),
                mon(d.precio_consigna),
            ]
        data.append(fila)

    tabla = Table(data, repeatRows=1)
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ])
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 0.7 * cm))

    pie = Paragraph(
        (
            f"<para align='center'><font size=8 color=grey>"
            f"Book Express © {datetime.now().year} – Generado automáticamente."
            f"</font></para>"
        ),
        styles["Normal"],
    )
    elementos.append(pie)

    doc.build(elementos)


# ====================================================
# 📗 ADOPCIÓN PDF
# ====================================================

def generar_pdf_adopcion(adopcion, response):
    """Genera PDF horizontal de la ficha de adopción."""
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20,
    )
    elementos = []
    styles = getSampleStyleSheet()

    logo_path = os.path.join(
        settings.BASE_DIR, "cotizador_colegio", "static", "img", "img_book_express.png"
    )
    logo = (
        Image(logo_path, width=3.5 * cm, height=2.5 * cm)
        if os.path.exists(logo_path)
        else Paragraph("<b>BOOK EXPRESS</b>", styles["Title"])
    )
    titulo = Paragraph("<b>FICHA DE ADOPCIÓN</b>", styles["Title"])
    numero = Paragraph(f"<b>N° ADOP-{str(adopcion.id).zfill(5)}</b>", styles["Normal"])

    encabezado = Table([[logo, titulo, numero]], colWidths=[4.5 * cm, 18 * cm, 4 * cm])
    encabezado.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ])
    )
    elementos.append(encabezado)
    elementos.append(Spacer(1, 0.3 * cm))

    cot = adopcion.cotizacion
    inst = cot.institucion
    asesor = cot.asesor

    # ---- Datos del colegio ----
    datos_ie = [
        ["1. DATOS DE LA INSTITUCIÓN EDUCATIVA", ""],
        ["Nombre IE:", txt(inst.nombre)],
        ["Nivel educativo:", txt(getattr(inst, "nivel_educativo", ""))],
        ["Dirección:", txt(inst.direccion)],
        ["Provincia:", txt(inst.provincia)],
        ["Teléfono:", txt(inst.telefono)],
        ["Directivo(a):", txt(inst.director)],
    ]
    datos_ie2 = [
        ["Código Modular:", txt(getattr(inst, "codigo_modular", ""))],
        ["Distrito:", txt(inst.distrito)],
        ["Departamento:", txt(inst.departamento)],
        ["Correo:", txt(inst.correo_institucional)],
        ["", ""], ["", ""], ["", ""],
    ]

    tabla_ie = Table([[Table(datos_ie), Table(datos_ie2)]], colWidths=[12 * cm, 12 * cm])
    tabla_ie.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elementos.append(tabla_ie)
    elementos.append(Spacer(1, 0.3 * cm))

    # ---- Datos del asesor ----
    datos_asesor = [
        ["2. DATOS DEL REPRESENTANTE COMERCIAL", ""],
        ["Nombre:", txt(asesor.nombre)],
        ["Teléfono:", txt(asesor.telefono)],
        ["Zona / Región:", txt(asesor.zona)],
        ["Empresa / Editorial:", "BOOK EXPRESS"],
        ["Correo:", txt(asesor.correo)],
    ]
    tabla_asesor = Table(datos_asesor, colWidths=[5 * cm, 16 * cm])
    tabla_asesor.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elementos.append(tabla_asesor)
    elementos.append(Spacer(1, 0.4 * cm))

    # ---- Tipo de Venta ----
    primer_det = cot.detalles.first()
    if primer_det:
        raw_tv = (primer_det.tipo_venta or "").upper().strip()
        MAPEO = {
            "PV": "Punto de Venta",
            "PUNTO_DE_VENTA": "Punto de Venta",
            "PUNTO DE VENTA": "Punto de Venta",
            "FERIA": "Feria",
            "CONSIGNA": "Consignación",
        }
        tipo_legible = MAPEO.get(raw_tv, raw_tv)
    else:
        tipo_legible = "—"

    tabla_tipo = Table(
        [
            ["3. TIPO DE VENTA", ""],
            ["Tipo de Venta:", tipo_legible],
        ],
        colWidths=[5 * cm, 16 * cm],
    )
    tabla_tipo.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elementos.append(tabla_tipo)
    elementos.append(Spacer(1, 0.4 * cm))

    # ---- TABLA PRINCIPAL CON TIPO DE VENTA ----
    headers = [
        "Editorial",
        "Nivel",
        "Grado",
        "Área",
        "Descripción",
        "PVP 2026",
        "Tipo Venta",
        "Cantidad",
        "Mes de Lectura"
    ]

    data = [headers]

    for d in adopcion.detalles.all():
        libro = d.libro
        area_lower = str(libro.area or "").lower()
        data.append([
            libro.empresa,
            libro.nivel,
            libro.grado,
            libro.area,
            libro.descripcion_completa,
            mon(libro.pvp_2026_con_igv),
            tipo_legible,
            d.cantidad_adoptada,
            d.mes_lectura if "lector" in area_lower else "—",
        ])

    tabla = Table(
        data,
        repeatRows=1,
        colWidths=[
            3 * cm, 2.3 * cm, 2.3 * cm, 2.5 * cm,
            8.2 * cm, 2.6 * cm, 2.5 * cm, 2.5 * cm, 3 * cm
        ],
    )
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#006633")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ])
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 0.5 * cm))

    # ---- Firmas ----
    firmas = [
        ["___________________________", "___________________________"],
        ["Directivo(a)", "Asesor Comercial"],
        [txt(inst.director), txt(asesor.nombre)],
    ]
    tabla_firmas = Table(firmas, colWidths=[12 * cm, 12 * cm])
    tabla_firmas.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ])
    )
    elementos.append(tabla_firmas)
    elementos.append(Spacer(1, 0.4 * cm))

    pie = Paragraph(
        (
            f"<para align='center'><font size=7 color=grey>"
            f"Book Express © {datetime.now().year} – Documento generado automáticamente por el sistema Book Express."
            f"</font></para>"
        ),
        styles["Normal"],
    )
    elementos.append(pie)

    doc.build(elementos)
