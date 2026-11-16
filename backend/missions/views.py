"""
Missions app views — API ViewSet + Dashboard views.

Two kinds of views live here:
1. MissionViewSet — the REST API (JSON) for missions, including AI actions.
2. Dashboard functions — server-rendered HTML pages for the browser UI.
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

# One shared instance used by every request (fetches NASA/NOAA space-weather data)
_weather_service = SpaceWeatherService()

logger = logging.getLogger(__name__)


class MissionViewSet(viewsets.ModelViewSet):
    """
    CRUD for missions plus custom actions: health, anomalies, analyze, assistant.

    Default ModelViewSet routes (registered under /api/ in the router):
      GET    /api/missions/        -> list missions
      POST   /api/missions/        -> create a mission
      GET    /api/missions/{id}/   -> retrieve one mission
      PATCH  /api/missions/{id}/   -> partially update a mission
      DELETE /api/missions/{id}/   -> delete a mission
    The @action methods below add extra routes for AI/health features.
    """
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    # AI actions (analyze / assistant) are throttled at '10/min' per client —
    # see spaceguard.throttling.ActionScopedRateThrottle
    throttle_scope_analyze = 'ai'
    throttle_scope_assistant = 'ai'

    @action(detail=True, methods=['get'])
    def health(self, request, pk=None):
        """GET /api/missions/{id}/health/ — health score from latest analysis."""
        # get_object() fetches the Mission by the pk in the URL (404 if missing)
        mission = self.get_object()
        # Newest AIAnalysis row for this mission (DB query, ordered by created_at)
        latest = mission.ai_analyses.order_by('-created_at').first()
        if not latest:
            return Response(
                {'detail': 'No analysis available yet. POST to /analyze/ first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Just the 'health' section of the stored result JSON, e.g.
        # {"health_score": 87, "status": "GOOD", ...}
        return Response(latest.result.get('health', {}))

    @action(detail=True, methods=['get'])
    def anomalies(self, request, pk=None):
        """GET /api/missions/{id}/anomalies/ — paginated anomalous telemetry records."""
        mission = self.get_object()
        # Only telemetry rows the AI flagged as abnormal, newest first
        qs = mission.telemetry_records.filter(is_anomaly=True).order_by('-timestamp')
        # paginate_queryset slices the queryset according to DRF page size
        page = self.paginate_queryset(qs)
        serializer = TelemetrySerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        """GET /api/missions/{id}/alerts/ — all alerts for this mission."""
        mission = self.get_object()
        # Fetch every alert linked to this mission (no pagination here)
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
        # Asks the SpaceWeatherService (external NOAA/NASA data) for that date
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
        # Grab the most recent telemetry snapshot to analyse
        latest_telemetry = mission.telemetry_records.order_by('-timestamp').first()
        if not latest_telemetry:
            return Response(
                {'detail': 'No telemetry data available for this mission.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Imported here (not at top) to avoid import cycles with the ai app
        from ai.pipeline import run_analysis_pipeline
        try:
            # Runs the whole pipeline: anomaly detection -> health score ->
            # predictions -> Granite explanation -> alert creation
            result = run_analysis_pipeline(latest_telemetry)
        except Exception as exc:
            # Log the full traceback server-side; return a generic message
            logger.exception('Analysis pipeline failed for mission %d: %s', mission.pk, exc)
            return Response(
                {'detail': 'AI analysis pipeline failed. Check server logs for details.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(result)

    @action(detail=True, methods=['post'])
    def assistant(self, request, pk=None):
        """POST /api/missions/{id}/assistant/ — mission AI assistant."""
        # The question arrives as JSON: {"question": "Why is the battery low?"}
        mission = self.get_object()
        question = request.data.get('question', '').strip()
        if not question:
            return Response(
                {'detail': 'A question is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(question) > 500:
            return Response(
                {'detail': 'Question must be 500 characters or fewer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Build context from database — no invented values
        # We gather ONLY real facts from the DB so the LLM (Granite) answers
        # from actual mission state instead of making things up.
        latest_telemetry = mission.telemetry_records.order_by('-timestamp').first()
        latest_analysis = mission.ai_analyses.order_by('-created_at').first()
        # Up to 5 still-open alerts (NEW or INVESTIGATING) as plain dicts
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

        # The single context dict handed to the Granite model as its
        # "knowledge base" for answering the question:
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
            # These three come from the stored AIAnalysis.result JSON (empty
            # dicts if no analysis has run yet)
            'health': latest_analysis.result.get('health', {}) if latest_analysis else {},
            'latest_anomaly': latest_analysis.result.get('anomaly', {}) if latest_analysis else {},
            'latest_explanation': latest_analysis.result.get('explanation', {}) if latest_analysis else {},
            'active_alerts': recent_alerts,
            'space_weather': space_weather,
        }

        # Send (context + question) to the Granite LLM; imported locally to
        # avoid a circular import with the ai app
        from ai.pipeline import get_granite
        result = get_granite().ask_assistant(context, question)
        return Response(result)


# ─── Dashboard template views ───────────────────────────────────────────────
# These render HTML pages (server-side) rather than JSON API responses.

def dashboard_home(request):
    """Main dashboard — shows first active mission or all missions list."""
    missions = Mission.objects.filter(status='ACTIVE').order_by('-created_at')
    if missions.exists():
        # If any active mission exists, jump straight into its dashboard
        return mission_dashboard(request, missions.first().pk)
    # Otherwise show a list of all missions and let the user pick one
    all_missions = Mission.objects.all()
    return render(request, 'dashboard/home.html', {'missions': all_missions})


def mission_dashboard(request, pk):
    """Mission-specific dashboard with telemetry, health, charts, alerts."""
    # 404s if the mission doesn't exist
    mission = get_object_or_404(Mission, pk=pk)
    # Three independent DB queries for the "cards" at the top of the page
    latest_telemetry = mission.telemetry_records.order_by('-timestamp').first()
    latest_analysis = mission.ai_analyses.order_by('-created_at').first()
    active_alerts = mission.alerts.filter(status__in=['NEW', 'INVESTIGATING']).order_by('-created_at')[:10]
    all_missions = Mission.objects.all()

    # Chart data — last 50 records, oldest-first
    # (reversed so line charts read left-to-right in time order)
    chart_records = list(mission.telemetry_records.order_by('-timestamp')[:50])
    chart_records.reverse()
    # One series per sensor channel; serialized to JSON for Chart.js
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

    # Fill from the latest analysis if one exists, else leave empty dicts
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

    # Everything the template needs, bundled into the context
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
    # Last 200 readings (oldest-first for charting), plus all alerts
    all_records = list(mission.telemetry_records.order_by('-timestamp')[:200])
    all_records.reverse()
    all_alerts = mission.alerts.all()
    all_missions = Mission.objects.all()

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
        'health_score': [],  # Will be populated from AIAnalysis records below
    }

    # Build health_score from AIAnalysis records keyed by telemetry_id
    # One DB query fetches all analyses for these 200 readings at once,
    # then we index them by telemetry_id for quick lookup per record.
    telemetry_ids = [r.id for r in all_records]
    analyses = AIAnalysis.objects.filter(
        telemetry_id__in=telemetry_ids
    ).values('telemetry_id', 'result')
    analysis_map = {}
    for a in analyses:
        # Keep the latest analysis per telemetry record
        analysis_map[a['telemetry_id']] = a['result']
    # Fall back to 100 ("perfect health") where no analysis exists
    chart_data['health_score'] = [
        analysis_map.get(r.id, {}).get('health', {}).get('health_score', 100)
        for r in all_records
    ]

    return render(request, 'analytics/history.html', {
        'mission': mission,
        'all_missions': all_missions,
        'all_alerts': all_alerts,
        'chart_data_json': json.dumps(chart_data),
        'telemetry_count': len(all_records),
    })


def spaceguard_dashboard(request):
    """SpaceGuard AI — Space Weather Intelligence Dashboard (standalone SPA)."""
    # Just serves the static single-page app; it fetches its own data
    return render(request, 'spaceguard_dashboard.html')
