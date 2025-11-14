# cotizador_colegio/admin.py
from django.contrib import admin
from .models import (
    Libro, InstitucionEducativa, AsesorComercial,
    Cotizacion, DetalleCotizacion,
    Adopcion, DetalleAdopcion,
    Pedido, DetallePedido
)

class DetalleCotizacionInline(admin.TabularInline):
    model = DetalleCotizacion
    extra = 0


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("numero_cotizacion", "institucion", "asesor", "fecha", "estado", "monto_total")
    list_filter = ("estado", "fecha")
    search_fields = ("numero_cotizacion", "institucion__nombre", "asesor__nombre")
    ordering = ("-fecha",)
    inlines = [DetalleCotizacionInline]

@admin.register(DetalleCotizacion)
class DetalleCotizacionAdmin(admin.ModelAdmin):
    list_display = ("cotizacion", "libro", "tipo_venta", "precio_be", "precio_ie", "precio_ppff")
    list_filter = ("tipo_venta",)


admin.site.register(Libro)
admin.site.register(InstitucionEducativa)
admin.site.register(AsesorComercial)
admin.site.register(Adopcion)
admin.site.register(DetalleAdopcion)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
