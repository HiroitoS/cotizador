# cotizador_colegio/apps.py
from django.apps import AppConfig

class CotizadorColegioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cotizador_colegio"

    def ready(self):
        from . import signals  # noqa
