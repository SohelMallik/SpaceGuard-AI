"""
Telemetry app URL configuration.

Included under /api/ by spaceguard/urls.py, giving these full paths:
"""
from django.urls import path
from telemetry.views import MissionTelemetryView

# Bind HTTP POST to the ViewSet methods explicitly (a plain ViewSet has no
# auto-created routes for these, so we map them by hand):
telemetry_upload = MissionTelemetryView.as_view({'post': 'upload'})
telemetry_create = MissionTelemetryView.as_view({'post': 'create'})

urlpatterns = [
    # POST /api/missions/<mission_id>/telemetry/          — ingest one JSON reading
    path('missions/<int:mission_pk>/telemetry/', telemetry_create, name='mission-telemetry'),
    # POST /api/missions/<mission_id>/telemetry/upload/   — bulk CSV upload (multipart file)
    path('missions/<int:mission_pk>/telemetry/upload/', telemetry_upload, name='telemetry-upload'),
]
