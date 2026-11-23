"""
Alerts app models — alert lifecycle management.

An Alert is a warning that "something needs a human's attention", raised
either by the AI anomaly pipeline (see alerts/services.py) or by extreme
space-weather conditions. Alerts always belong to a Mission and usually
point at the Telemetry record that triggered them.
"""
from django.db import models
from missions.models import Mission
from telemetry.models import Telemetry


class Subsystem(models.TextChoices):
    """
    Which part of the spacecraft the alert is about.

    TextChoices = a fixed set of string options (an enum). The DB stores the
    short code ('THERMAL'); the longer text is the display label.
    """
    THERMAL = 'THERMAL', 'Thermal Control'                  # Heaters, radiators, temperature control
    ELECTRICAL = 'ELECTRICAL', 'Electrical Power'           # Batteries, solar panels, power bus
    COMMUNICATION = 'COMMUNICATION', 'Communication'        # Antennas and radio links
    PROPULSION = 'PROPULSION', 'Propulsion'                 # Thrusters and fuel systems
    RADIATION = 'RADIATION', 'Radiation Protection'         # Shielding and radiation exposure
    ENVIRONMENTAL = 'ENVIRONMENTAL', 'Environmental Control'# Air / pressure / life-support style systems
    NAVIGATION = 'NAVIGATION', 'Navigation'                 # Attitude control and guidance
    UNKNOWN = 'UNKNOWN', 'Unknown'                          # Fallback when the AI cannot tell


class Severity(models.TextChoices):
    """
    How serious the alert is, from LOW (informational) to CRITICAL
    (act immediately). Only MODERATE and above actually create alerts —
    see AlertService.create_if_needed.
    """
    LOW = 'LOW', 'Low'
    MODERATE = 'MODERATE', 'Moderate'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class AlertStatus(models.TextChoices):
    """
    Where the alert is in its human workflow:
    NEW -> an operator picks it up -> INVESTIGATING -> RESOLVED.
    An alert in NEW or INVESTIGATING is considered "open".
    """
    NEW = 'NEW', 'New'
    INVESTIGATING = 'INVESTIGATING', 'Investigating'
    RESOLVED = 'RESOLVED', 'Resolved'


class Alert(models.Model):
    """
    A warning for one mission, tied to the subsystem that has a problem.
    """
    # The mission the alert belongs to.
    # CASCADE: deleting the Mission deletes its alerts too (they belong to it).
    # related_name lets us write mission.alerts.
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    # The telemetry reading that triggered this alert, if any.
    # SET_NULL: if that telemetry row is ever deleted we keep the alert, but
    # its link becomes NULL — history of warnings should survive cleanup.
    # null/blank=True allow alerts with no telemetry (e.g. weather alerts).
    telemetry = models.ForeignKey(
        Telemetry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
    )
    # Which spacecraft subsystem has the problem (choices above)
    subsystem = models.CharField(
        max_length=20,
        choices=Subsystem.choices,
        default=Subsystem.UNKNOWN,
    )
    # How urgent it is (choices above)
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.LOW,
    )
    # Human-readable description of what went wrong (often AI-generated)
    description = models.TextField()
    # Suggested fix / next step (also often AI-generated)
    recommended_action = models.TextField(blank=True, default='')
    # Where this alert is in the operator workflow (choices above)
    status = models.CharField(
        max_length=15,
        choices=AlertStatus.choices,
        default=AlertStatus.NEW,
    )
    # Set automatically when the alert row is first created
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest alerts first
        ordering = ['-created_at']

    def __str__(self):
        # e.g. "[CRITICAL] ELECTRICAL alert — ISS-Alpha"
        return f'[{self.severity}] {self.subsystem} alert — {self.mission.spacecraft_name}'
