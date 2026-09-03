"""
Missions app views — API ViewSet + Dashboard views.
"""
import json
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView

from missions.models import Mission
from missions.serializers import MissionSerializer
from telemetry.models import Telemetry
from telemetry.serializers import TelemetrySerializer
from anomaly.models import AIAnalysis
from anomaly.serializers import AIAnalysisSerializer
from alerts.models import Alert
from alerts.serializers import AlertSerializer
from ai.space_weather_service import SpaceWeatherService

_weather_service = SpaceWeatherService()

logger = logging.getLogger(__name__)


class MissionViewSet(viewsets.ModelViewSet):
    """
    CRUD for missions plus custom actions: health, anomalies, analyze, assistant.
    """
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer

    @action(detail=True, methods=['get'])
    def health(self, request, pk=None):
        """GET /api/missions/{id}/health/ — health score from latest analysis."""
        mission = self.get_object()
        latest = mission.ai_analyses.order_by('-created_at').first()
        if not latest:
            return Response(
                {'detail': 'No analysis available yet. POST to /analyze/ first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(latest.result.get('health', {}))

    @action(detail=True, methods=['get'])
    def anomalies(self, request, pk=None):
        """GET /api/missions/{id}/anomalies/ — paginated anomalous telemetry records."""
        mission = self.get_object()
        qs = mission.telemetry_records.filter(is_anomaly=True).order_by('-timestamp')
        page = self.paginate_queryset(qs)
        serializer = TelemetrySerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        """GET /api/missions/{id}/alerts/ — all alerts for this mission."""
        mission = self.get_object()
        alerts = mission.alerts.all()
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def weather(self, request, pk=None):
        """GET /api/missions/{id}/weather/ — current space weather risk for this mission."""
        mission = self.get_object()
        # Use the latest telemetry timestamp's date, or today if no telemetry
        latest = mission.telemetry_records.order_by('-timestamp').first()
        query_date = latest.timestamp.date() if latest else None
        risk = _weather_service.get_risk_for_date(query_date)
        return Response({
            'mission': mission.name,
            'spacecraft': mission.spacecraft_name,
            'space_weather': risk,
        })

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """POST /api/missions/{id}/analyze/ — run full AI pipeline on latest telemetry."""
        mission = self.get_object()
        latest_telemetry = mission.telemetry_records.order_by('-timestamp').first()
        if not latest_telemetry:
            return Response(
                {'detail': 'No telemetry data available for this mission.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from ai.pipeline import run_analysis_pipeline
        result = run_analysis_pipeline(latest_telemetry)
        return Response(result)

    @action(detail=True, methods=['post'])
    def assistant(self, request, pk=None):
        """POST /api/missions/{id}/assistant/ — mission AI assistant."""
        mission = self.get_object()
        question = request.data.get('question', '').strip()
        if not question:
            return Response(
                {'detail': 'A question is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Build context from database — no invented values
        latest_telemetry = mission.telemetry_records.order_by('-timestamp').first()
        latest_analysis = mission.ai_analyses.order_by('-created_at').first()
        recent_alerts = list(mission.alerts.filter(
            status__in=['NEW', 'INVESTIGATING']
        ).values('subsystem', 'severity', 'description', 'status')[:5])

        if not latest_telemetry:
            return Response({
                'answer': 'Insufficient telemetry data is available to determine this.',
                'source': 'System',
            })

        # Space weather for the telemetry date
        space_weather = _weather_service.get_risk_for_date(
            latest_telemetry.timestamp.date()
        )

        context = {
            'mission_name': mission.name,
            'spacecraft': mission.spacecraft_name,
            'mission_status': mission.status,
            'latest_telemetry': {
                'timestamp': str(latest_telemetry.timestamp),
                'temperature': latest_telemetry.temperature,
                'battery_voltage': latest_telemetry.battery_voltage,
                'battery_current': latest_telemetry.battery_current,
                'fuel_level': latest_telemetry.fuel_level,
                'radiation': latest_telemetry.radiation,
                'pressure': latest_telemetry.pressure,
                'signal_strength': latest_telemetry.signal_strength,
                'velocity': latest_telemetry.velocity,
                'power_consumption': latest_telemetry.power_consumption,
                'is_anomaly': latest_telemetry.is_anomaly,
                'anomaly_score': float(latest_telemetry.anomaly_score) if latest_telemetry.anomaly_score is not None else None,
            },
            'health': latest_analysis.result.get('health', {}) if latest_analysis else {},
            'latest_anomaly': latest_analysis.result.get('anomaly', {}) if latest_analysis else {},
            'latest_explanation': latest_analysis.result.get('explanation', {}) if latest_analysis else {},
            'active_alerts': recent_alerts,
            'space_weather': space_weather,
        }

        from ai.granite_service import GraniteService
        granite = GraniteService()
        result = granite.ask_assistant(context, question)
        return Response(result)


# ─── Dashboard template views ───────────────────────────────────────────────

def dashboard_home(request):
    """Main dashboard — shows first active mission or all missions list."""
    missions = Mission.objects.filter(status='ACTIVE').order_by('-created_at')
    if missions.exists():
        return mission_dashboard(request, missions.first().pk)
    all_missions = Mission.objects.all()
    return render(request, 'dashboard/home.html', {'missions': all_missions})


def mission_dashboard(request, pk):
    """Mission-specific dashboard with telemetry, health, charts, alerts."""
    mission = get_object_or_404(Mission, pk=pk)
    latest_telemetry = mission.telemetry_records.order_by('-timestamp').first()
    latest_analysis = mission.ai_analyses.order_by('-created_at').first()
    active_alerts = mission.alerts.filter(status__in=['NEW', 'INVESTIGATING']).order_by('-created_at')[:10]
    all_missions = Mission.objects.all()

    # Chart data — last 50 records, oldest-first
    chart_records = list(mission.telemetry_records.order_by('-timestamp')[:50])
    chart_records.reverse()
    chart_data = {
        'labels': [r.timestamp.strftime('%H:%M:%S') for r in chart_records],
        'temperature': [r.temperature for r in chart_records],
        'battery_voltage': [r.battery_voltage for r in chart_records],
        'fuel_level': [r.fuel_level for r in chart_records],
        'signal_strength': [r.signal_strength for r in chart_records],
        'radiation': [r.radiation for r in chart_records],
        'pressure': [r.pressure for r in chart_records],
        'velocity': [r.velocity for r in chart_records],
        'power_consumption': [r.power_consumption for r in chart_records],
    }

    health = {}
    anomaly = {}
    explanation = {}
    predictions = []
    if latest_analysis:
        health = latest_analysis.result.get('health', {})
        anomaly = latest_analysis.result.get('anomaly', {})
        explanation = latest_analysis.result.get('explanation', {})
        predictions = latest_analysis.result.get('predictions', [])

    # Space weather for this mission's latest telemetry date
    weather_date = latest_telemetry.timestamp.date() if latest_telemetry else None
    space_weather = _weather_service.get_risk_for_date(weather_date)

    context = {
        'mission': mission,
        'all_missions': all_missions,
        'latest_telemetry': latest_telemetry,
        'health': health,
        'anomaly': anomaly,
        'explanation': explanation,
        'predictions': predictions,
        'active_alerts': active_alerts,
        'chart_data_json': json.dumps(chart_data),
        'alert_count': active_alerts.count(),
        'space_weather': space_weather,
    }
    return render(request, 'dashboard/index.html', context)


def history_view(request, pk):
    """Historical analytics page."""
    mission = get_object_or_404(Mission, pk=pk)
    all_records = list(mission.telemetry_records.order_by('-timestamp')[:200])
    all_records.reverse()
    all_alerts = mission.alerts.all()

    chart_data = {
        'labels': [r.timestamp.strftime('%Y-%m-%d %H:%M') for r in all_records],
        'temperature': [r.temperature for r in all_records],
        'battery_voltage': [r.battery_voltage for r in all_records],
        'fuel_level': [r.fuel_level for r in all_records],
        'signal_strength': [r.signal_strength for r in all_records],
        'radiation': [r.radiation for r in all_records],
        'pressure': [r.pressure for r in all_records],
        'velocity': [r.velocity for r in all_records],
        'power_consumption': [r.power_consumption for r in all_records],
        'health_score': [
            r.anomaly_score * -100 + 100 if r.anomaly_score else 100
            for r in all_records
        ],
    }

    return render(request, 'analytics/history.html', {
        'mission': mission,
        'all_alerts': all_alerts,
        'chart_data_json': json.dumps(chart_data),
        'telemetry_count': len(all_records),
    })


def spaceguard_dashboard(request):
    """SpaceGuard AI — Space Weather Intelligence Dashboard (standalone SPA)."""
    return render(request, 'spaceguard_dashboard.html')
