"""
Alerts app views — alert list and status update.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from alerts.models import Alert
from alerts.serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        alert_status = self.request.query_params.get('status')
        mission_id = self.request.query_params.get('mission')
        if alert_status:
            qs = qs.filter(status=alert_status)
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        return qs
