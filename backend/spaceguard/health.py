"""
SpaceGuard AI — health check endpoint.

A tiny, dependency-free endpoint that monitoring systems (uptime monitors,
load balancers, container orchestrators like Kubernetes, or simply a
developer's browser) can poll to confirm the service is alive AND able to
reach its database.

Mounted in spaceguard/urls.py at:  GET /api/health/
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

    Response body:
        {"status": "ok"|"unhealthy", "database": "ok"|"error: ...",
         "timestamp": "<ISO-8601 UTC time>"}

    The status code is what monitoring tools look at:
        200 -> service is fine, keep sending traffic
        503 -> something is broken, take this instance out of rotation
    """
    # Check 1: database connectivity. A `SELECT 1` is the cheapest possible
    # query — it proves a real connection to the database works end to end
    # (network, credentials, engine up) without touching any tables.
    database = 'ok'
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception as exc:  # noqa: BLE001 — report any DB failure
        # Any failure (connection refused, auth error, timeout...) is
        # reported by its class name rather than crashing the endpoint —
        # a health check must itself stay up so it can report bad health.
        database = f'error: {type(exc).__name__}'
        logger.error('Health check database failure: %s', exc)

    # Check 2 (implicit): if this code is running at all, the Django
    # process itself is alive. Combine with the DB result for the verdict.
    healthy = database == 'ok'
    return JsonResponse(
        {
            'status': 'ok' if healthy else 'unhealthy',
            'database': database,
            'timestamp': timezone.now().isoformat(),
        },
        status=200 if healthy else 503,
    )
