"""
Telemetry app models — spacecraft sensor readings.

Telemetry is the stream of measurements a spacecraft sends back to Earth:
temperature, battery levels, signal strength, etc. Each Telemetry row is one
"snapshot" of the spacecraft's health at a single moment in time.

Relationship chain in this app:
    Mission ──(one)──< Telemetry ──(one)──< AIAnalysis / Alert
A Mission has many Telemetry records; each Telemetry record can trigger one
AI analysis and/or one alert if it looks abnormal.
"""
from django.db import models
from missions.models import Mission


class Telemetry(models.Model):
    """
    One sensor-reading snapshot from a spacecraft at a specific timestamp.
    """
    # The mission this reading belongs to.
    # CASCADE: if the Mission row is deleted, all of its telemetry readings
    # are deleted too (readings are meaningless without their mission).
    # related_name lets us write mission.telemetry_records from the other side.
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='telemetry_records',
    )
    # When the reading was taken. db_index=True makes lookups by time fast
    # (we always sort/filter by timestamp).
    timestamp = models.DateTimeField(db_index=True)
    # Everything below is one sensor channel. Units are in the help_text,
    # which shows up in forms and the API docs.
    temperature = models.FloatField(help_text='Degrees Celsius')            # Interior/exterior temp in °C, typical spacecraft range about -20 to +60
    battery_voltage = models.FloatField(help_text='Volts')                  # Battery voltage in volts, normal range roughly 22-32V
    battery_current = models.FloatField(help_text='Amperes')                # Battery current draw in amperes
    fuel_level = models.FloatField(help_text='Percentage 0-100')            # Remaining propellant as a percentage (0 = empty, 100 = full tank)
    radiation = models.FloatField(help_text='mSv')                          # Ionizing radiation dose rate in millisieverts
    pressure = models.FloatField(help_text='kPa')                           # Internal pressure in kilopascals
    signal_strength = models.FloatField(help_text='dBm')                    # Radio signal strength in dBm, closer to 0 is stronger
    velocity = models.FloatField(help_text='km/s')                          # Orbital/flight speed in kilometres per second
    power_consumption = models.FloatField(help_text='Watts')                # Total power draw in watts
    # AI analysis results (populated after analysis pipeline runs)
    # Confidence score from the anomaly detector, 0.0 to 1.0. Null until the
    # AI pipeline has processed this record.
    anomaly_score = models.FloatField(null=True, blank=True)
    # True once the AI decides this reading is abnormal
    is_anomaly = models.BooleanField(default=False)

    class Meta:
        # Newest readings first by default
        ordering = ['-timestamp']
        indexes = [
            # Composite index: "give me the readings for mission X between
            # time A and B" is the single most common query in the app.
            models.Index(fields=['mission', 'timestamp']),
        ]

    def __str__(self):
        # e.g. "Telemetry [ISS-Alpha] @ 2024-06-01 03:00:00+00:00"
        return f'Telemetry [{self.mission.spacecraft_name}] @ {self.timestamp}'
