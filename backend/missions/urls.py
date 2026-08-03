"""
Missions API URL configuration.
"""
from rest_framework.routers import DefaultRouter
from missions.views import MissionViewSet

router = DefaultRouter()
router.register(r'missions', MissionViewSet, basename='mission')

urlpatterns = router.urls
