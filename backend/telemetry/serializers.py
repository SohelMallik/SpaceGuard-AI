"""
Telemetry app serializers with sensor field validation.

The TelemetrySerializer both serializes Telemetry rows to JSON and validates
incoming sensor values against realistic physical ranges before saving them.
The validate_* methods below are DRF hooks: they run automatically on every
create/update for the matching field name.
"""
from rest_framework import serializers
from telemetry.models import Telemetry


class TelemetrySerializer(serializers.ModelSerializer):
    """
    Exposes every Telemetry field, plus sanity checks on key sensors.

    Exposed fields: all Telemetry model fields (mission, timestamp, the ten
    sensor channels, anomaly_score, is_anomaly).
    """
    class Meta:
        model = Telemetry
        # '__all__' = every model field is included in the JSON output
        fields = '__all__'
        # Clients cannot set these: id comes from the DB, and anomaly_score /
        # is_anomaly are only ever set by the AI analysis pipeline.
        read_only_fields = ('id', 'anomaly_score', 'is_anomaly')

    # ── Field validators: reject physically impossible sensor values ─────

    def validate_temperature(self, value):
        """Temperature must be plausible for a spacecraft: -100 to +300 °C."""
        if not -100 <= value <= 300:
            raise serializers.ValidationError('Temperature must be between -100 and 300°C.')
        return value

    def validate_battery_voltage(self, value):
        """Battery voltage must be 0-100 V (typical bus is ~22-32 V)."""
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Battery voltage must be between 0 and 100V.')
        return value

    def validate_fuel_level(self, value):
        """Fuel level is a percentage, so it must be 0-100."""
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Fuel level must be between 0 and 100%.')
        return value

    def validate_radiation(self, value):
        """Radiation dose rate must be 0-10000 mSv."""
        if not 0 <= value <= 10000:
            raise serializers.ValidationError('Radiation must be between 0 and 10000 mSv.')
        return value

    def validate_signal_strength(self, value):
        """Signal strength in dBm: 0 is strongest, -200 is essentially silence."""
        if not -200 <= value <= 0:
            raise serializers.ValidationError('Signal strength must be between -200 and 0 dBm.')
        return value
