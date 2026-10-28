"""
SpaceGuard AI — custom middleware (rate limiting).
"""
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

try:
    from ratelimit.exceptions import Ratelimited       # standard django-ratelimit layout
except ImportError:  # pragma: no cover
    from django_ratelimit.exceptions import Ratelimited  # alternate layout

logger = logging.getLogger(__name__)

WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


class RateLimitMiddleware:
    """
    IP-based rate limiter for /api/ write requests.

    Acts as a safety net in addition to DRF throttling:
    - Limits the number of write requests per client IP within a sliding window.
    - Converts django-ratelimit's Ratelimited exception into a JSON 429 response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_limited(request):
            return self._rate_limited_response()
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Map django-ratelimit's Ratelimited exception to a JSON 429 response."""
        if isinstance(exception, Ratelimited):
            return self._rate_limited_response()
        return None

    def _is_limited(self, request) -> bool:
        if not getattr(settings, 'API_RATE_LIMIT_ENABLED', True):
            return False
        if not request.path.startswith('/api/'):
            return False
        if request.method not in WRITE_METHODS:
            return False
        # Never block monitoring/health endpoints
        if request.path.rstrip('/').endswith('health'):
            return False

        window = getattr(settings, 'RATELIMIT_API_WINDOW', 60)
        max_writes = getattr(settings, 'RATELIMIT_API_MAX_WRITES', 120)
        ident = request.META.get('REMOTE_ADDR', 'unknown')
        cache_key = f'rate-limit-api:{ident}'

        now = time.time()
        history = [t for t in cache.get(cache_key, []) if t > now - window]
        if len(history) >= max_writes:
            logger.warning('Rate limit exceeded for %s (%s %s)', ident, request.method, request.path)
            return True
        history.append(now)
        cache.set(cache_key, history, window)
        return False

    @staticmethod
    def _rate_limited_response():
        return JsonResponse(
            {'detail': 'Too many requests. Please try again later.'},
            status=429,
        )
