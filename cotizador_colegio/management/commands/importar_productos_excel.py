from django.core.management.base import BaseCommand
from cotizador_colegio.models import Editorial, Producto
from django.conf import settings
import pandas as pd
import os


class Command(BaseCommand):
    help = "Importa productos desde el Excel oficial de cotización"

    def handle(self, *args, **options):

        # =====================================================
        # 📌 CONFIGURACIÓN
        # =====================================================
        ruta_excel = os.path.join(
            settings.BASE_DIR,
            "FORMATO DE COTIZACIÓN.xlsx"
        )

        hoja = "PRECIOS POR EDITORIAL"

        if not os.path.exists(ruta_excel):
            self.stderr.write(self.style.ERROR(
                f"No se encontró el archivo: {ruta_excel}"
            ))
            return

        # =====================================================
        # 📌 LECTURA DEL EXCEL
        # =====================================================
        df = pd.read_excel(ruta_excel, sheet_name=hoja)

        # -----------------------------------------------------
        # 🔒 NORMALIZAR COLUMNAS (blindaje total)
        # -----------------------------------------------------
        df.columns = (
            df.columns
            .str.strip()
            .str.upper()
            .str.replace("Á", "A")
            .str.replace("É", "E")
            .str.replace("Í", "I")
            .str.replace("Ó", "O")
            .str.replace("Ú", "U")
        )

        columnas_esperadas = {
            "EDITORIAL",
            "CODIGO",
            "DESCRIPCION COMPLETA",
            "NIVEL",
            "GRADO",
            "AREA",
            "PVP 26 CON IGV",
            "DESC PROVEEDOR",
            "PRECIO PROVEEDOR",
        }

        faltantes = columnas_esperadas - set(df.columns)
        if faltantes:
            self.stderr.write(
                self.style.ERROR(f"Faltan columnas en el Excel: {faltantes}")
            )
            return

        # =====================================================
        # 🔑 CLAVE: ARRASTRAR EDITORIALES VACÍAS
        # =====================================================
        # Esto corrige editoriales fusionadas o repetidas visualmente
        df["EDITORIAL"] = df["EDITORIAL"].ffill()

        # =====================================================
        # 📌 IMPORTACIÓN
        # =====================================================
        creados = 0
        actualizados = 0

        for index, row in df.iterrows():

            # -------------------------
            # Validación mínima segura
            # -------------------------
            if pd.isna(row["EDITORIAL"]):
                continue

            nombre_editorial = str(row["EDITORIAL"]).strip()
            if not nombre_editorial:
                continue

            # Código: si viene vacío, se genera uno único
            codigo = row["CODIGO"]
            if pd.isna(codigo) or str(codigo).strip() == "":
                codigo = f"SIN-COD-{index}"
            else:
                codigo = str(codigo).strip()

            editorial, _ = Editorial.objects.get_or_create(
                nombre=nombre_editorial
            )

            producto, created = Producto.objects.update_or_create(
                editorial=editorial,
                codigo=codigo,
                defaults={
                    "nombre": str(row["DESCRIPCION COMPLETA"]).strip()
                        if not pd.isna(row["DESCRIPCION COMPLETA"]) else "",
                    "nivel": str(row["NIVEL"]).strip()
                        if not pd.isna(row["NIVEL"]) else "",
                    "grado": str(row["GRADO"]).strip()
                        if not pd.isna(row["GRADO"]) else "",
                    "area": str(row["AREA"]).strip()
                        if not pd.isna(row["AREA"]) else "",
                    "pvp_2026": row["PVP 26 CON IGV"]
                        if not pd.isna(row["PVP 26 CON IGV"]) else 0,
                    "descuento_proveedor": row["DESC PROVEEDOR"]
                        if not pd.isna(row["DESC PROVEEDOR"]) else 0,
                    "precio_proveedor": row["PRECIO PROVEEDOR"]
                        if not pd.isna(row["PRECIO PROVEEDOR"]) else 0,
                    "estado": True,
                }
            )

            if created:
                creados += 1
            else:
                actualizados += 1

        # =====================================================
        # ✅ RESULTADO FINAL
        # =====================================================
        self.stdout.write(self.style.SUCCESS(
            f"Importación completada ✔ | "
            f"Creados: {creados} | Actualizados: {actualizados}"
        ))
