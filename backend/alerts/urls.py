"""
Alerts app URL configuration.
"""
from rest_framework.routers import DefaultRouter
from alerts.views import AlertViewSet

router = DefaultRouter()
router.register(r'alerts', AlertViewSet, basename='alert')

urlpatterns = router.urls
