"""
Missions API URL configuration.

Uses DRF's DefaultRouter to auto-generate REST routes for MissionViewSet.
The router's URLs are included under /api/ by spaceguard/urls.py, so the
full paths are:

  /api/missions/                     GET (list) / POST (create)
  /api/missions/{id}/                GET (retrieve) / PATCH / DELETE
  /api/missions/{id}/health/         GET  — health score from latest analysis
  /api/missions/{id}/anomalies/      GET  — paginated anomalous telemetry
  /api/missions/{id}/alerts/         GET  — alerts for this mission
  /api/missions/{id}/weather/        GET  — space-weather risk
  /api/missions/{id}/analyze/        POST — run the AI pipeline
  /api/missions/{id}/assistant/      POST — ask the AI assistant a question
"""
from rest_framework.routers import DefaultRouter
from missions.views import MissionViewSet

# Create a router and register the ViewSet under the 'missions' prefix;
# DRF then builds all the list/detail/action routes automatically
router = DefaultRouter()
router.register(r'missions', MissionViewSet, basename='mission')

# The router also serves a browsable API root page at /api/
urlpatterns = router.urls
