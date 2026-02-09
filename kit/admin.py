from django.contrib import admin
from .models import Kit, KitItem


class KitItemInline(admin.TabularInline):
    model = KitItem
    extra = 1


@admin.register(Kit)
class KitAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo", "activo", "codigo_barra", "created_at")
    list_filter = ("tipo", "activo")
    search_fields = ("nombre", "codigo_barra")
    inlines = [KitItemInline]


@admin.register(KitItem)
class KitItemAdmin(admin.ModelAdmin):
    list_display = ("id", "kit", "producto", "cantidad", "orden")
    search_fields = ("kit__nombre", "producto__nombre", "producto__codigo")
