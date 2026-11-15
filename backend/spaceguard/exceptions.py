"""
SpaceGuard AI — Custom DRF Exception Handler
Returns consistent JSON error responses instead of Django HTML error pages.

WHY THIS FILE EXISTS
--------------------
Without it, errors from the API would look inconsistent: some would be
DRF's JSON format, while unhandled Python errors would produce Django's
big HTML debug page (or a plain HTML 500 page in production). With this
handler registered in settings.py
('EXCEPTION_HANDLER': 'spaceguard.exceptions.custom_exception_handler'),
EVERY API error — expected or not — comes back as the same JSON shape:

    {"error": true, "status_code": <int>, "detail": <what went wrong>}

That single shape makes error handling on the frontend simple and uniform.

There are no custom exception *classes* in this project; the handler below
normalises whatever exception a view raises (DRF's ValidationError,
PermissionDenied, Http404, or an unexpected bug) into that JSON format.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

# Uses the 'django' logger config from settings.LOGGING (console handler).
logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Override DRF default handler to return structured JSON errors."""
    # Step 1: let DRF do its normal work first. `exception_handler`
    # returns a Response for API-aware exceptions (validation errors,
    # auth failures, throttling, 404s...) or None for anything else
    # (i.e. a genuine unexpected server error).
    response = exception_handler(exc, context)

    # Step 2: known/handled API exception -> reshape DRF's response into
    # our uniform {"error", "status_code", "detail"} envelope. The HTTP
    # status code stays exactly as DRF chose it (400, 401, 403, 404, 429...).
    if response is not None:
        return Response(
            {
                'error': True,
                'status_code': response.status_code,
                'detail': response.data,
            },
            status=response.status_code,
        )

    # Step 3: unhandled server error — log it, return 500 JSON
    # `logger.exception` records the full traceback, which is what
    # developers need to debug the bug. The client only sees a generic,
    # safe message (never internal details, which could leak secrets).
    logger.exception('Unhandled server error: %s', exc)
    return Response(
        {
            'error': True,
            'status_code': 500,
            'detail': 'An internal server error occurred. Please contact mission control support.',
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
