"""
Telemetry app URL configuration.
"""
from django.urls import path
from telemetry.views import MissionTelemetryView

telemetry_upload = MissionTelemetryView.as_view({'post': 'upload'})
telemetry_create = MissionTelemetryView.as_view({'post': 'create'})

urlpatterns = [
    path('missions/<int:mission_pk>/telemetry/', telemetry_create, name='mission-telemetry'),
    path('missions/<int:mission_pk>/telemetry/upload/', telemetry_upload, name='telemetry-upload'),
]
