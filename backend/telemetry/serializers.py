"""
Telemetry app serializers with sensor field validation.
"""
from rest_framework import serializers
from telemetry.models import Telemetry


class TelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetry
        fields = '__all__'
        read_only_fields = ('id', 'anomaly_score', 'is_anomaly')

    def validate_temperature(self, value):
        if not -100 <= value <= 300:
            raise serializers.ValidationError('Temperature must be between -100 and 300°C.')
        return value

    def validate_battery_voltage(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Battery voltage must be between 0 and 100V.')
        return value

    def validate_fuel_level(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Fuel level must be between 0 and 100%.')
        return value

    def validate_radiation(self, value):
        if not 0 <= value <= 10000:
            raise serializers.ValidationError('Radiation must be between 0 and 10000 mSv.')
        return value

    def validate_signal_strength(self, value):
        if not -200 <= value <= 0:
            raise serializers.ValidationError('Signal strength must be between -200 and 0 dBm.')
        return value
