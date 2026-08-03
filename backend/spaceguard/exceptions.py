"""
SpaceGuard AI — Custom DRF Exception Handler
Returns consistent JSON error responses instead of Django HTML error pages.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Override DRF default handler to return structured JSON errors."""
    response = exception_handler(exc, context)

    if response is not None:
        return Response(
            {
                'error': True,
                'status_code': response.status_code,
                'detail': response.data,
            },
            status=response.status_code,
        )

    # Unhandled server error — log it, return 500 JSON
    logger.exception('Unhandled server error: %s', exc)
    return Response(
        {
            'error': True,
            'status_code': 500,
            'detail': 'An internal server error occurred. Please contact mission control support.',
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
