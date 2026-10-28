"""
SpaceGuard AI — health check endpoint.
"""
import logging

from django.db import connection
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


def health_check(request):
    """
    GET /api/health/ — liveness/readiness probe.

    Verifies the process is up and the database is reachable.
    Returns 200 when healthy, 503 when the database is unavailable.
    """
    database = 'ok'
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception as exc:  # noqa: BLE001 — report any DB failure
        database = f'error: {type(exc).__name__}'
        logger.error('Health check database failure: %s', exc)

    healthy = database == 'ok'
    return JsonResponse(
        {
            'status': 'ok' if healthy else 'unhealthy',
            'database': database,
            'timestamp': timezone.now().isoformat(),
        },
        status=200 if healthy else 503,
    )
