from io import BytesIO
from datetime import datetime
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def es_plan_lector(libro):
    area = (libro.area or "").lower()
    return "lector" in area

def _label(c, x, y, label, value):
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, f"{label}:")
    c.setFont("Helvetica", 9)
    c.drawString(x + 4.2*cm, y, str(value or ""))

def generar_pdf_adopcion(adopcion):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 2*cm
    y = height - margin

    # LOGO
    try:
        logo = settings.BASE_DIR / "cotizador_colegio/static/img/book_express.jpg"
        c.drawImage(str(logo), margin, y-2.2*cm, width=4.5*cm, preserveAspectRatio=True, mask='auto')
    except:
        pass

    # TÍTULO
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin+5.3*cm, y-0.6*cm, "FICHA DE ADOPCIÓN")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin+5.3*cm, y-1.2*cm, "DE MATERIALES EDUCATIVOS")

    # Empresa
    c.setFont("Helvetica", 9)
    c.drawRightString(width - margin, y-0.6*cm, "BOOK EXPRESS S.A.C.")
    c.drawRightString(width - margin, y-1.05*cm, "Jr. Omar Yali 371 - Huancayo")
    c.drawRightString(width - margin, y-1.5*cm, "934 941 161  - contacto@book-express.com")

    y -= 2.8*cm

    cot = adopcion.cotizacion
    inst = cot.institucion
    ases = cot.asesor

    # I.E.
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "1. DATOS DE LA INSTITUCIÓN EDUCATIVA")
    y -= 0.8*cm
    col = margin; col2 = width/2

    datos_ie = [
        ("Nombre IE", inst.nombre),
        ("Nivel educativo", inst.nivel_educativo),
        ("Dirección", inst.direccion),
        ("Distrito", inst.distrito),
        ("Provincia", inst.provincia),
        ("Departamento", inst.departamento),
        ("Teléfono", inst.telefono),
        ("Correo", inst.correo_institucional),
        ("Director(a)", inst.director),
        ("Código Modular", inst.codigo_modular),
    ]

    for label, value in datos_ie:
        _label(c, col, y, label, value)
        y -= 0.5*cm

    y -= 0.7*cm

    # REPRESENTANTE
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "2. DATOS DEL REPRESENTANTE COMERCIAL")
    y -= 0.8*cm

    datos_rep = [
        ("Nombre", ases.nombre),
        ("Empresa / Editorial", ases.empresa_editorial),
        ("Teléfono", ases.telefono),
        ("Correo", ases.correo),
        ("Zona / Región", ases.zona),
    ]

    for label, value in datos_rep:
        _label(c, col, y, label, value)
        y -= 0.5*cm

    y -= 0.7*cm

    # TABLA LIBROS
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "3. DETALLE DE LIBROS ADOPTADOS")
    y -= 0.6*cm

    headers = ["Descripción", "Cantidad", "Mes lectura"]
    widths = [9.5*cm, 2.0*cm, 3.0*cm]
    x = margin

    c.setFont("Helvetica-Bold", 9)
    for h, w in zip(headers, widths):
        c.setFillColor(colors.black)
        c.rect(x, y-0.45*cm, w, 0.55*cm, fill=1)
        c.setFillColor(colors.white)
        c.drawString(x+0.15*cm, y-0.25*cm, h)
        x += w
    y -= 0.55*cm

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)

    for det in adopcion.detalles.all():
        libro = det.libro
        fila = [
            libro.descripcion_completa[:80],
            str(det.cantidad_adoptada),
            det.mes_lectura if es_plan_lector(libro) else "—"
        ]
        x = margin
        for val, w in zip(fila, widths):
            c.rect(x, y-0.48*cm, w, 0.48*cm)
            c.drawString(x+0.12*cm, y-0.32*cm, val)
            x += w
        y -= 0.48*cm

    y -= 1*cm

    # FIRMAS
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "4. FIRMAS")
    y -= 1*cm

    c.line(margin, y, margin+7*cm, y)
    c.drawString(margin, y-0.4*cm, "Directivo")

    c.line(width-7*cm-margin, y, width-margin, y)
    c.drawString(width-7*cm-margin, y-0.4*cm, "Representante Comercial")

    c.showPage()
    c.save()
    return buffer.getvalue()
