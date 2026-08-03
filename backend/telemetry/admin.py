from django.contrib import admin
from telemetry.models import Telemetry


@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = ('mission', 'timestamp', 'temperature', 'battery_voltage', 'fuel_level', 'is_anomaly', 'anomaly_score')
    list_filter = ('is_anomaly', 'mission')
    search_fields = ('mission__spacecraft_name',)
    ordering = ('-timestamp',)
