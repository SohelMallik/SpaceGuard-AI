"""
Alerts service — creates alerts from anomaly results with duplicate suppression.

This sits between the AI pipeline and the database: when the pipeline
detects a problem, AlertService decides whether an Alert row should be
created. Its two jobs are (1) ignore trivial problems and (2) avoid
spamming the same warning over and over.
"""
import logging
from alerts.models import Alert, AlertStatus

logger = logging.getLogger(__name__)


class AlertService:
    """
    Stateless helper class — all methods are @staticmethod, so you call
    them directly, e.g. AlertService.create_if_needed(...)
    """

    @staticmethod
    def create_if_needed(mission, anomaly_result: dict, telemetry_record, explanation: dict) -> 'Alert | None':
        """
        Create an alert if no unresolved alert already exists for the same subsystem.
        Returns the created Alert or None if suppressed.

        Args:
            mission:          the Mission the anomaly belongs to
            anomaly_result:   AI output, e.g. {'severity': 'HIGH', 'affected_subsystem': 'THERMAL'}
            telemetry_record: the Telemetry row that triggered it (linked to the Alert)
            explanation:      AI's plain-English diagnosis, e.g. {'detected_problem': ...}
        """
        # Which subsystem is affected and how bad it is (with safe defaults)
        subsystem = anomaly_result.get('affected_subsystem', 'UNKNOWN')
        severity = anomaly_result.get('severity', 'LOW')

        # Only create for MODERATE and above
        # LOW problems are logged elsewhere but don't deserve an alert
        if severity not in ('MODERATE', 'HIGH', 'CRITICAL'):
            return None

        # Duplicate suppression — skip if open alert exists for this subsystem
        # Without this, ingesting 200 anomalous readings would create 200
        # identical alerts; instead we keep the first one until it's RESOLVED.
        existing = mission.alerts.filter(
            subsystem=subsystem,
            status__in=[AlertStatus.NEW, AlertStatus.INVESTIGATING],
        ).first()

        if existing:
            logger.info(
                'Suppressed duplicate alert for subsystem %s on mission %s',
                subsystem, mission.name,
            )
            return None

        # Use the AI's wording when available, fall back to generic text
        description = explanation.get('detected_problem', f'Anomaly detected in {subsystem} subsystem.')
        recommended_action = explanation.get(
            'recommended_action',
            'Review telemetry data and consult mission protocols.',
        )

        alert = Alert.objects.create(
            mission=mission,
            telemetry=telemetry_record,
            subsystem=subsystem,
            severity=severity,
            description=description,
            recommended_action=recommended_action,
            status=AlertStatus.NEW,
        )
        logger.info('Created alert %d for mission %s (%s / %s)', alert.id, mission.name, subsystem, severity)
        return alert

    @staticmethod
    def create_weather_alert_if_needed(mission, space_weather: dict, telemetry_record) -> 'Alert | None':
        """
        Create a RADIATION alert when space weather reaches EXTREME level.
        Suppressed if an open RADIATION alert already exists.

        Unlike create_if_needed, this is triggered by external space-weather
        data (solar storms) rather than by the spacecraft's own telemetry.
        """
        # Same duplicate suppression pattern as above, hardcoded to RADIATION
        existing = mission.alerts.filter(
            subsystem='RADIATION',
            status__in=[AlertStatus.NEW, AlertStatus.INVESTIGATING],
        ).first()
        if existing:
            return None

        # Pull the risk numbers for the human-readable description
        risk_score = space_weather.get('risk_score', 0)
        kp = space_weather.get('max_kp_index', 0)
        xclass = space_weather.get('xclass_flares_48h', 0)
        alert = Alert.objects.create(
            mission=mission,
            telemetry=telemetry_record,
            subsystem='RADIATION',
            # Extreme space weather is always treated as CRITICAL
            severity='CRITICAL',
            description=(
                f'EXTREME space weather detected. Risk score: {risk_score}/100. '
                f'X-class flares (48h): {xclass}. Max Kp-index: {kp}. '
                'Spacecraft may be exposed to hazardous solar particle radiation.'
            ),
            recommended_action=(
                'Switch spacecraft to safe mode. Reduce non-essential power loads. '
                'Orient solar panels edge-on. Suspend EVA activities. '
                'Monitor radiation sensor continuously until risk level drops below HIGH.'
            ),
            status=AlertStatus.NEW,
        )
        logger.info('Created EXTREME weather RADIATION alert %d for %s', alert.id, mission.name)
        return alert
