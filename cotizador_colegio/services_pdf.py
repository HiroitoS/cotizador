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
    """Genera PDF horizontal de la cotización con cabeceras estandarizadas.

    Cabeceras SIEMPRE: Editorial, Nivel, Grado, Área, Descripción, PVP 2026
    Si PV/FERIA: + Precio IE, PPFF, Utilidad IE
    Si CONSIGNA: + Precio BE, Precio Consigna
    """
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

    # ---- Datos del colegio ----
    inst = cotizacion.institucion
    asesor = cotizacion.asesor
    detalles = cotizacion.detalles.all()
    tipo = detalles.first().tipo_venta if detalles.exists() else "—"

    # Compatibilidad con nombre / nombre_ie
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

    # ---- Asesor comercial ----
    datos_asesor = [
        ["2. DATOS DEL REPRESENTANTE COMERCIAL", ""],
        ["Nombre:", txt(getattr(asesor, "nombre", ""))],
        ["Teléfono:", txt(getattr(asesor, "telefono", ""))],
        ["Zona / Región:", txt(getattr(asesor, "region", getattr(asesor, "zona", "")))],
        ["Empresa / Editorial:", "BOOK EXPRESS"],
        ["Correo:", txt(getattr(asesor, "correo", ""))],
    ]
    tabla_asesor = Table(datos_asesor, colWidths=[5 * cm, 16 * cm])
    tabla_asesor.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elementos.append(tabla_asesor)
    elementos.append(Spacer(1, 0.5 * cm))

    # ---- Tabla principal (cabeceras estables + extras por tipo) ----
    headers = [
        "Editorial", "Nivel", "Grado", "Área", "Descripción", "PVP 2026"
    ]
    tipo_upper = (tipo or "").upper().strip()
    if tipo_upper in ("FERIA", "PV", "PUNTO_DE_VENTA", "PUNTO DE VENTA"):
        headers += ["Precio IE", "PPFF", "Utilidad IE"]
        modo = "PV"
    elif tipo_upper == "CONSIGNA":
        headers += ["Precio BE", "Precio Consigna"]
        modo = "CONSIGNA"
    else:
        # fallback (trátalo como PV)
        headers += ["Precio IE", "PPFF", "Utilidad IE"]
        modo = "PV"

    data = [headers]

    for d in detalles:
        fila = [
            d.libro.empresa,
            d.libro.nivel,
            d.libro.grado,
            d.libro.area,
            d.libro.descripcion_completa,
            mon(d.libro.pvp_2026_con_igv),  # SIEMPRE PVP 2026
        ]
        if modo == "PV":
            fila += [
                mon(getattr(d, "precio_ie", None)),
                mon(getattr(d, "precio_ppff", None)),
                mon(getattr(d, "utilidad_ie", None)),
            ]
        else:  # CONSIGNA
            fila += [
                mon(getattr(d, "precio_be", None)),        # BE real (puede ser > PVP)
                mon(getattr(d, "precio_consigna", None)),
            ]
        data.append(fila)

    # Ajuste de anchos: descripción más amplia para evitar desbordes
    # (Deja que ReportLab calcule, pero con un leve sesgo vía repeatRows y estilos)
    tabla = Table(data, repeatRows=1)
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ])
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 0.7 * cm))

    # ---- Pie de página ----
    pie = Paragraph(
        (
            f"<para align='center'><font size=8 color=grey>"
            f"Book Express © {datetime.now().year} – Generado automáticamente por el sistema Book Express."
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
    """Genera el PDF horizontal de la ficha de adopción.

    Cabeceras SIEMPRE: Editorial, Nivel, Grado, Área, Descripción, PVP 2026, Cantidad, Mes de Lectura
    """
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20,
    )
    elementos = []
    styles = getSampleStyleSheet()

    # ---- Encabezado ----
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

    # ---- Datos colegio y asesor ----
    cot = adopcion.cotizacion
    inst = getattr(cot, "institucion", None)
    asesor = getattr(cot, "asesor", None)

    nombre_ie = getattr(inst, "nombre_ie", None) or getattr(inst, "nombre", "—")

    datos_ie = [
        ["1. DATOS DE LA INSTITUCIÓN EDUCATIVA", ""],
        ["Nombre IE:", txt(getattr(inst, "nombre", nombre_ie))],
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
    tabla_ie = Table(
        [[
            Table(datos_ie, colWidths=[4.3 * cm, 7.7 * cm]),
            Table(datos_ie2, colWidths=[4.3 * cm, 7.7 * cm]),
        ]],
        colWidths=[12 * cm, 12 * cm],
    )
    tabla_ie.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ])
    )
    elementos.append(tabla_ie)
    elementos.append(Spacer(1, 0.3 * cm))

    datos_asesor = [
        ["2. DATOS DEL REPRESENTANTE COMERCIAL", ""],
        ["Nombre:", txt(getattr(asesor, "nombre", ""))],
        ["Teléfono:", txt(getattr(asesor, "telefono", ""))],
        ["Zona / Región:", txt(getattr(asesor, "region", getattr(asesor, "zona", "")))],
        ["Empresa / Editorial:", "BOOK EXPRESS"],
        ["Correo:", txt(getattr(asesor, "correo", ""))],
    ]
    tabla_asesor = Table(datos_asesor, colWidths=[5 * cm, 16 * cm])
    tabla_asesor.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ])
    )
    elementos.append(tabla_asesor)
    elementos.append(Spacer(1, 0.4 * cm))

    # ---- Detalle (cabeceras unificadas con PVP 2026) ----
    headers = [
        "Editorial", "Nivel", "Grado", "Área", "Descripción", "PVP 2026",
        "Cantidad", "Mes de Lectura"
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
            mon(getattr(libro, "pvp_2026_con_igv", None)),
            d.cantidad_adoptada,
            d.mes_lectura if "lector" in area_lower else "—",
        ])

    tabla = Table(
        data,
        repeatRows=1,
        colWidths=[3.0 * cm, 2.2 * cm, 2.2 * cm, 2.5 * cm, 8.0 * cm, 2.5 * cm, 2.5 * cm, 3.0 * cm],
    )
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#006633")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ("LEFTPADDING", (0, 0), (-1, -1), 1),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ])
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 0.5 * cm))

    # ---- Firmas ----
    firmas = [
        ["___________________________", "___________________________"],
        ["Directivo(a)", "Asesor Comercial"],
        [txt(getattr(inst, "director", "")), txt(getattr(asesor, "nombre", ""))],
    ]
    tabla_firmas = Table(firmas, colWidths=[12 * cm, 12 * cm])
    tabla_firmas.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elementos.append(tabla_firmas)
    elementos.append(Spacer(1, 0.4 * cm))

    # ---- Pie ----
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
