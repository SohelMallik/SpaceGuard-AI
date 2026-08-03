"""
Telemetry app models — spacecraft sensor readings.
"""
from django.db import models
from missions.models import Mission


class Telemetry(models.Model):
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='telemetry_records',
    )
    timestamp = models.DateTimeField(db_index=True)
    temperature = models.FloatField(help_text='Degrees Celsius')
    battery_voltage = models.FloatField(help_text='Volts')
    battery_current = models.FloatField(help_text='Amperes')
    fuel_level = models.FloatField(help_text='Percentage 0-100')
    radiation = models.FloatField(help_text='mSv')
    pressure = models.FloatField(help_text='kPa')
    signal_strength = models.FloatField(help_text='dBm')
    velocity = models.FloatField(help_text='km/s')
    power_consumption = models.FloatField(help_text='Watts')
    # AI analysis results (populated after analysis pipeline runs)
    anomaly_score = models.FloatField(null=True, blank=True)
    is_anomaly = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['mission', 'timestamp']),
        ]

    def __str__(self):
        return f'Telemetry [{self.mission.spacecraft_name}] @ {self.timestamp}'
