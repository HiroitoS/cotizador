import os
import django
import pandas as pd

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Cotizador.settings")
django.setup()

from cotizador.Cotizador.CopiaSeguridad.models_old import Libro

# Ruta del archivo Excel
excel_path = "BASE COTIZADOR.xlsx"

# 🔹 Leer la hoja de Excel (asegúrate que se llame BRUÑO o la hoja que corresponda)
df = pd.read_excel(excel_path, sheet_name="BRUÑO", header=0)

print("Columnas detectadas en el Excel:", df.columns.tolist())

# 🔹 Renombrar columnas para que coincidan con el modelo
df = df.rename(columns={
    "EMPRESA": "empresa",
    "NIVEL": "nivel",
    "GRADO": "grado",
    "ÁREA": "area",
    "SERIE": "serie",
    "DESCRIPCIÓN COMPLETA": "descripcion_completa",
    "TIPO DE INV": "tipo_inventario",
    "SOPORTE": "soporte",
    "PVP 2026 CON IGV": "pvp_2026_con_igv"
})

# 🔹 Reemplazar NaN por valores vacíos o 0
df = df.fillna({"pvp_2026_con_igv": 0})
df = df.fillna("")

# 🔹 Insertar registros evitando duplicados
insertados = 0
duplicados = 0

for _, row in df.iterrows():
    exists = Libro.objects.filter(
        empresa=row["empresa"],
        nivel=row["nivel"],
        grado=row["grado"],
        area=row["area"],
        descripcion_completa=row["descripcion_completa"]
    ).exists()

    if exists:
        duplicados += 1
    else:
        Libro.objects.create(
            empresa=row["empresa"],
            nivel=row["nivel"],
            grado=row["grado"],
            area=row["area"],
            serie=row["serie"],
            descripcion_completa=row["descripcion_completa"],
            tipo_inventario=row["tipo_inventario"],
            soporte=row["soporte"],
            pvp_2026_con_igv=row["pvp_2026_con_igv"]
        )
        insertados += 1

print(f"✅ Libros insertados: {insertados}")
print(f"⚠️ Libros duplicados (omitidos): {duplicados}")
