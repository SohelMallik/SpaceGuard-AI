"""
Anomaly app serializers.
"""
from rest_framework import serializers
from anomaly.models import AIAnalysis


class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = '__all__'
        read_only_fields = ('id', 'created_at')
