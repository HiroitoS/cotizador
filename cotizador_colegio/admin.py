# cotizador_colegio/admin.py
from django.contrib import admin
from .models import (
    InstitucionEducativa,
    AsesorComercial,
    Cotizacion,
    DetalleCotizacion,
    Adopcion,
    DetalleAdopcion,
    Pedido,
    DetallePedido,
    Editorial,
    Producto,
)


# -------------------------
# INLINE: Detalle Cotización
# -------------------------
class DetalleCotizacionInline(admin.TabularInline):
    model = DetalleCotizacion
    extra = 0


# -------------------------
# COTIZACIONES
# -------------------------
@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "numero_cotizacion",
        "institucion",
        "asesor",
        "fecha",
        "estado",
    )
    list_filter = ("estado", "fecha")
    search_fields = (
        "numero_cotizacion",
        "institucion__nombre",
        "asesor__nombre",
    )
    ordering = ("-fecha",)
    inlines = [DetalleCotizacionInline]


@admin.register(DetalleCotizacion)
class DetalleCotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "cotizacion",
        "producto",
        "tipo_venta",
        "precio_be",
        "precio_ie",
        "precio_ppff",
        "precio_proveedor",
    )
    list_filter = ("tipo_venta", "producto__editorial")
    search_fields = ("producto__nombre",)


# -------------------------
# CATÁLOGO
# -------------------------
@admin.register(Editorial)
class EditorialAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado")
    search_fields = ("nombre",)
    list_filter = ("estado",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "editorial",
        "codigo",
        "nombre",
        "nivel",
        "grado",
        "area",
        "pvp_2026",
        "precio_proveedor",
        "estado",
    )
    list_filter = ("editorial", "nivel", "grado", "area", "estado")
    search_fields = ("nombre", "codigo")
    ordering = ("editorial", "nombre")


# -------------------------
# OTROS MODELOS
# -------------------------
admin.site.register(InstitucionEducativa)
admin.site.register(AsesorComercial)
admin.site.register(Adopcion)
admin.site.register(DetalleAdopcion)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
