"""
Anomaly app models — AIAnalysis records for storing generated analysis.
"""
from django.db import models
from missions.models import Mission
from telemetry.models import Telemetry


class AnalysisType(models.TextChoices):
    ANOMALY = 'ANOMALY', 'Anomaly Detection'
    HEALTH = 'HEALTH', 'Health Score'
    PREDICTION = 'PREDICTION', 'Trend Prediction'
    EXPLANATION = 'EXPLANATION', 'AI Explanation'


class AIAnalysis(models.Model):
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='ai_analyses',
    )
    telemetry = models.ForeignKey(
        Telemetry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_analyses',
    )
    analysis_type = models.CharField(
        max_length=15,
        choices=AnalysisType.choices,
        default=AnalysisType.ANOMALY,
    )
    input_context = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    raw_response = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'AIAnalysis [{self.analysis_type}] for {self.mission.spacecraft_name} @ {self.created_at}'
