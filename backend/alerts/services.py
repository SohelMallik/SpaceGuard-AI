"""
Alerts service — creates alerts from anomaly results with duplicate suppression.
"""
import logging
from alerts.models import Alert, AlertStatus

logger = logging.getLogger(__name__)


class AlertService:
    @staticmethod
    def create_if_needed(mission, anomaly_result: dict, telemetry_record, explanation: dict) -> 'Alert | None':
        """
        Create an alert if no unresolved alert already exists for the same subsystem.
        Returns the created Alert or None if suppressed.
        """
        subsystem = anomaly_result.get('affected_subsystem', 'UNKNOWN')
        severity = anomaly_result.get('severity', 'LOW')

        # Only create for MODERATE and above
        if severity not in ('MODERATE', 'HIGH', 'CRITICAL'):
            return None

        # Duplicate suppression — skip if open alert exists for this subsystem
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
        """
        existing = mission.alerts.filter(
            subsystem='RADIATION',
            status__in=[AlertStatus.NEW, AlertStatus.INVESTIGATING],
        ).first()
        if existing:
            return None

        risk_score = space_weather.get('risk_score', 0)
        kp = space_weather.get('max_kp_index', 0)
        xclass = space_weather.get('xclass_flares_48h', 0)
        alert = Alert.objects.create(
            mission=mission,
            telemetry=telemetry_record,
            subsystem='RADIATION',
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
