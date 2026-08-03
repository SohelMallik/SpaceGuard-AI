from django.contrib import admin
from anomaly.models import AIAnalysis


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ('mission', 'analysis_type', 'created_at')
    list_filter = ('analysis_type',)
    search_fields = ('mission__spacecraft_name',)
