"""
Alerts app models — alert lifecycle management.
"""
from django.db import models
from missions.models import Mission
from telemetry.models import Telemetry


class Subsystem(models.TextChoices):
    THERMAL = 'THERMAL', 'Thermal Control'
    ELECTRICAL = 'ELECTRICAL', 'Electrical Power'
    COMMUNICATION = 'COMMUNICATION', 'Communication'
    PROPULSION = 'PROPULSION', 'Propulsion'
    RADIATION = 'RADIATION', 'Radiation Protection'
    ENVIRONMENTAL = 'ENVIRONMENTAL', 'Environmental Control'
    NAVIGATION = 'NAVIGATION', 'Navigation'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class Severity(models.TextChoices):
    LOW = 'LOW', 'Low'
    MODERATE = 'MODERATE', 'Moderate'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class AlertStatus(models.TextChoices):
    NEW = 'NEW', 'New'
    INVESTIGATING = 'INVESTIGATING', 'Investigating'
    RESOLVED = 'RESOLVED', 'Resolved'


class Alert(models.Model):
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    telemetry = models.ForeignKey(
        Telemetry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
    )
    subsystem = models.CharField(
        max_length=20,
        choices=Subsystem.choices,
        default=Subsystem.UNKNOWN,
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.LOW,
    )
    description = models.TextField()
    recommended_action = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=15,
        choices=AlertStatus.choices,
        default=AlertStatus.NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.severity}] {self.subsystem} alert — {self.mission.spacecraft_name}'
