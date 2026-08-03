"""
Alerts service — creates alerts from anomaly results with duplicate suppression.
"""
import logging
from alerts.models import Alert, AlertStatus

logger = logging.getLogger(__name__)


class AlertService:
    @staticmethod
    def create_if_needed(mission, anomaly_result: dict, telemetry_record, explanation: dict) -> Alert | None:
        """
        Create an alert if no unresolved alert already exists for the same subsystem.
        Returns the created Alert or None if suppressed.
        """
        subsystem = anomaly_result.get('affected_subsystem', 'UNKNOWN')
        severity = anomaly_result.get('severity', 'LOW')

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
