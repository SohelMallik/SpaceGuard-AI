"""
Alerts app views — alert list and status update.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from alerts.models import Alert
from alerts.serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    """
    REST API for alerts (registered at /api/alerts/ by the router).

    Routes handled:
      GET    /api/alerts/         -> list alerts (filterable, see below)
      POST   /api/alerts/         -> create an alert manually
      GET    /api/alerts/{id}/    -> retrieve one alert
      PATCH  /api/alerts/{id}/    -> update (usually to change status)
      DELETE /api/alerts/{id}/    -> delete an alert

    GET filters (query params):
      ?status=NEW|INVESTIGATING|RESOLVED
      ?mission=<mission_id>
    e.g. GET /api/alerts/?mission=1&status=NEW
    """
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    # Restrict to read + partial update: no PUT (full replace).
    # PATCH is what the UI uses to move alerts through the workflow
    # (NEW -> INVESTIGATING -> RESOLVED).
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        # Start from the default queryset, then apply optional filters
        # from the URL query string
        qs = super().get_queryset()
        alert_status = self.request.query_params.get('status')
        mission_id = self.request.query_params.get('mission')
        if alert_status:
            qs = qs.filter(status=alert_status)
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        return qs
