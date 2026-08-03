from django.contrib import admin
from missions.models import Mission


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'spacecraft_name', 'status', 'launch_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'spacecraft_name')
