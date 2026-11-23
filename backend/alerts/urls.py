"""
Alerts app URL configuration.

Uses DRF's DefaultRouter to auto-generate REST routes for AlertViewSet.
Included under /api/ by spaceguard/urls.py, so the full paths are:

  /api/alerts/        GET (list, filterable with ?status= & ?mission=) / POST
  /api/alerts/{id}/   GET / PATCH (e.g. change status to RESOLVED) / DELETE
"""
from rest_framework.routers import DefaultRouter
from alerts.views import AlertViewSet

# Register the ViewSet under the 'alerts' prefix; DRF builds the routes
router = DefaultRouter()
router.register(r'alerts', AlertViewSet, basename='alert')

urlpatterns = router.urls
