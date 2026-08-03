from django.contrib import admin
from alerts.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('mission', 'subsystem', 'severity', 'status', 'created_at')
    list_filter = ('severity', 'status', 'subsystem')
    search_fields = ('mission__spacecraft_name', 'description')
