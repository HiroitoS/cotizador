from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KitViewSet

router = DefaultRouter()
router.register(r"kits", KitViewSet, basename="kit-kits")

urlpatterns = [
    path("v1/", include(router.urls)),
]
