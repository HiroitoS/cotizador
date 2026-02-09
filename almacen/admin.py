from django.contrib import admin
from .models import (
    Almacen,
    Ingreso, IngresoDetalle,
    Transferencia, TransferenciaDetalle,
    Stock, MovimientoStock
)

@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo", "es_principal", "activo", "created_at")
    list_filter = ("tipo", "es_principal", "activo")
    search_fields = ("nombre",)

admin.site.register(Ingreso)
admin.site.register(IngresoDetalle)
admin.site.register(Transferencia)
admin.site.register(TransferenciaDetalle)
admin.site.register(Stock)
admin.site.register(MovimientoStock)
