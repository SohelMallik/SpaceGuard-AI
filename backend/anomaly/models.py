"""
Anomaly app models — AIAnalysis records for storing generated analysis.

Every time the AI pipeline runs (on new telemetry, or when someone clicks
"Analyze"), it writes an AIAnalysis row here: a snapshot of what the AI
concluded. The result JSON typically contains sections like 'health',
'anomaly', 'explanation' and 'predictions'.

Chain: Mission -> Telemetry (the input readings) -> AIAnalysis (the output).
"""
from django.db import models
from missions.models import Mission
from telemetry.models import Telemetry


class AnalysisType(models.TextChoices):
    """
    Which kind of AI run this record holds. TextChoices = fixed string
    options; the DB stores the code ('ANOMALY'), the longer text is the
    human-readable label.
    """
    ANOMALY = 'ANOMALY', 'Anomaly Detection'   # Did anything look abnormal?
    HEALTH = 'HEALTH', 'Health Score'          # Overall 0-100 health score
    PREDICTION = 'PREDICTION', 'Trend Prediction'  # Where values are heading
    EXPLANATION = 'EXPLANATION', 'AI Explanation'  # Plain-English diagnosis


class AIAnalysis(models.Model):
    """
    The stored output of one AI analysis run for one mission.
    """
    # Which mission was analysed.
    # CASCADE: deleting the Mission deletes its analysis history too.
    # related_name lets us write mission.ai_analyses.
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='ai_analyses',
    )
    # The telemetry snapshot the analysis was based on, if any.
    # SET_NULL: deleting the telemetry row must not delete the analysis
    # record — we just lose the exact input link. null/blank allow analyses
    # that are not tied to a single reading.
    telemetry = models.ForeignKey(
        Telemetry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_analyses',
    )
    # What kind of run this was (choices above)
    analysis_type = models.CharField(
        max_length=15,
        choices=AnalysisType.choices,
        default=AnalysisType.ANOMALY,
    )
    # JSON snapshot of the inputs fed to the model (sensor values, context…)
    input_context = models.JSONField(default=dict)
    # JSON with the AI results, e.g. {'health': {...}, 'anomaly': {...}, ...}
    result = models.JSONField(default=dict)
    # The model's raw text output, kept for debugging/auditing
    raw_response = models.TextField(blank=True, default='')
    # Set automatically when the row is first created
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest analyses first
        ordering = ['-created_at']

    def __str__(self):
        # e.g. "AIAnalysis [ANOMALY] for ISS-Alpha @ 2024-06-01 03:05:00+00:00"
        return f'AIAnalysis [{self.analysis_type}] for {self.mission.spacecraft_name} @ {self.created_at}'
