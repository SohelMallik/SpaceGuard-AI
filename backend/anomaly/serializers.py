"""
Anomaly app serializers.
"""
from rest_framework import serializers
from anomaly.models import AIAnalysis


class AIAnalysisSerializer(serializers.ModelSerializer):
    """
    Exposes every field of the AIAnalysis model as JSON.

    Exposed fields: id, mission, telemetry, analysis_type, input_context,
    result, raw_response, created_at. The 'result' JSON is what the
    dashboard reads (health score, anomaly info, explanation…).
    """
    class Meta:
        model = AIAnalysis
        # '__all__' = every model field is included in the JSON output
        fields = '__all__'
        # Clients cannot set these — the DB fills them in automatically
        read_only_fields = ('id', 'created_at')
