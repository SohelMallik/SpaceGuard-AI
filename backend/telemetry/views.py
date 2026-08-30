"""
Telemetry app views — ingest single records and bulk CSV upload.
"""
import io
import logging
import pandas as pd
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

from missions.models import Mission
from telemetry.models import Telemetry
from telemetry.serializers import TelemetrySerializer

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    'timestamp', 'temperature', 'battery_voltage', 'battery_current',
    'fuel_level', 'radiation', 'pressure', 'signal_strength', 'velocity', 'power_consumption',
]


class TelemetryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Telemetry is read via missions nested route.
    Ingestion happens through MissionTelemetryView.
    """
    serializer_class = TelemetrySerializer

    def get_queryset(self):
        mission_pk = self.kwargs.get('mission_pk')
        if mission_pk:
            return Telemetry.objects.filter(mission_id=mission_pk)
        return Telemetry.objects.all()


class MissionTelemetryView(viewsets.ViewSet):
    """
    Handles telemetry ingestion and CSV upload for a specific mission.
    Auto-runs the AI pipeline on each ingested record.
    """
    parser_classes = [MultiPartParser]

    def create(self, request, mission_pk=None):
        """POST /api/missions/{id}/telemetry/ — ingest a single telemetry record."""
        mission = get_object_or_404(Mission, pk=mission_pk)
        data = request.data.copy()
        data['mission'] = mission.id

        serializer = TelemetrySerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        telemetry = serializer.save()

        # Auto-run AI pipeline
        try:
            from ai.pipeline import run_analysis_pipeline
            analysis = run_analysis_pipeline(telemetry)
        except Exception as exc:
            logger.error('Pipeline error for telemetry %d: %s', telemetry.id, exc)
            analysis = {'error': str(exc)}

        return Response(
            {'telemetry': serializer.data, 'analysis': analysis},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='upload', parser_classes=[MultiPartParser])
    def upload(self, request, mission_pk=None):
        """POST /api/missions/{id}/telemetry/upload/ — bulk CSV upload."""
        mission = get_object_or_404(Mission, pk=mission_pk)
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        if not csv_file.name.endswith('.csv'):
            return Response({'detail': 'Only .csv files are accepted.'}, status=status.HTTP_400_BAD_REQUEST)

        # Max 10MB
        if csv_file.size > 10 * 1024 * 1024:
            return Response({'detail': 'File size exceeds 10MB limit.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content))
        except Exception as exc:
            return Response({'detail': f'Failed to parse CSV: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            return Response(
                {'detail': f'Missing required columns: {missing_cols}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        records_created = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                ts = pd.to_datetime(row['timestamp'])
                if ts.tzinfo is None:
                    ts = ts.tz_localize('UTC')
                telemetry = Telemetry.objects.create(
                    mission=mission,
                    timestamp=ts,
                    temperature=float(row['temperature']),
                    battery_voltage=float(row['battery_voltage']),
                    battery_current=float(row['battery_current']),
                    fuel_level=float(row['fuel_level']),
                    radiation=float(row['radiation']),
                    pressure=float(row['pressure']),
                    signal_strength=float(row['signal_strength']),
                    velocity=float(row['velocity']),
                    power_consumption=float(row['power_consumption']),
                )
                records_created += 1
            except Exception as exc:
                errors.append({'row': idx, 'error': str(exc)})

        # Run pipeline on latest record after bulk insert
        if records_created > 0:
            try:
                latest = mission.telemetry_records.order_by('-timestamp').first()
                from ai.pipeline import run_analysis_pipeline
                run_analysis_pipeline(latest)
            except Exception as exc:
                logger.error('Post-upload pipeline error: %s', exc)

        return Response({
            'records_created': records_created,
            'errors': errors[:20],  # cap error list for readability
        }, status=status.HTTP_201_CREATED)
