"""
Alerts app serializers.
"""
from rest_framework import serializers
from alerts.models import Alert


class AlertSerializer(serializers.ModelSerializer):
    """
    Exposes every field of the Alert model as JSON.

    Exposed fields: id, mission, telemetry, subsystem, severity, description,
    recommended_action, status, created_at.
    Validation: subsystem / severity / status must be valid TextChoices
    values (enforced automatically by the model's choices=).
    """
    class Meta:
        model = Alert
        # '__all__' = every model field is included in the JSON output
        fields = '__all__'
        # Clients cannot set these: id comes from the DB and created_at is
        # auto_now_add. (mission/telemetry are writable so tests/tools can
        # create alerts, but in practice the AlertService creates them.)
        read_only_fields = ('id', 'created_at')
