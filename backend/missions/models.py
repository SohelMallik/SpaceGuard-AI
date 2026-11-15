"""
Mission app models — Mission and MissionStatus definitions.

The Mission model is the "root" of the whole app: a Mission represents a real
spaceflight mission (e.g. a satellite or probe that is being monitored).
Everything else hangs off it, like branches on a tree:

    Mission ──> Telemetry   (regular sensor readings from the spacecraft)
            ──> AIAnalysis  (AI results computed from those readings)
            ──> Alert       (warnings raised when something looks wrong)
"""
from django.db import models


class MissionStatus(models.TextChoices):
    """
    The possible lifecycle states of a mission.

    TextChoices is Django's way of defining a fixed set of string options
    (like an enum). In the database only the short code is stored ('ACTIVE'),
    while the second value ('Active') is the human-readable label shown in
    forms and the admin site.
    """
    ACTIVE = 'ACTIVE', 'Active'          # Spacecraft is up and being monitored right now
    STANDBY = 'STANDBY', 'Standby'       # Alive but idle / not actively monitored
    COMPLETED = 'COMPLETED', 'Completed' # Mission objectives finished
    LOST = 'LOST', 'Lost Contact'        # No signal received from the spacecraft


class Mission(models.Model):
    """
    One monitored space mission (a spacecraft and its status).

    Related objects (defined in the other apps via ForeignKey):
      - telemetry_records : Telemetry rows streaming from this spacecraft
      - ai_analyses       : AIAnalysis rows produced by the AI pipeline
      - alerts            : Alert rows raised when anomalies are detected
    """
    # Human-friendly mission name, e.g. "Demo Mission Alpha"
    name = models.CharField(max_length=200)
    # Optional free-text description of what the mission does
    description = models.TextField(blank=True, default='')
    # Name of the physical spacecraft, e.g. "ISS-Alpha" or "Deep-Probe-1"
    spacecraft_name = models.CharField(max_length=200)
    # When the spacecraft launched. null=True means the DB allows "no value",
    # blank=True means the Django form/admin field is optional.
    launch_date = models.DateField(null=True, blank=True)
    # Current lifecycle state, limited to the MissionStatus choices above
    status = models.CharField(
        max_length=20,
        choices=MissionStatus.choices,
        default=MissionStatus.ACTIVE,
    )
    # Filled in automatically by Django the first time the row is saved
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest missions first when we list them
        ordering = ['-created_at']

    def __str__(self):
        # Shown in the admin site and logs, e.g. "Demo Mission Alpha (ISS-Alpha)"
        return f'{self.name} ({self.spacecraft_name})'
