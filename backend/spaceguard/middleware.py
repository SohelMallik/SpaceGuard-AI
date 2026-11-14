"""
SpaceGuard AI — custom middleware (rate limiting).

This module implements a lightweight, IP-based rate limiter that protects
the /api/ write endpoints (POST/PUT/PATCH/DELETE) from being flooded.

It complements DRF's built-in throttling (see spaceguard/throttling.py):
DRF throttling targets specific expensive actions (e.g. the AI endpoints),
while this middleware is a coarse "safety net" applied to ALL API writes,
even ones that don't have DRF throttles attached.
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

# Logger named after this module; messages appear via the root logger config.
logger = logging.getLogger(__name__)

# HTTP methods that modify data. Read-only methods (GET, HEAD, OPTIONS) are
# never counted against the limit — only "writes" can exhaust it.
WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


class RateLimitMiddleware:
    """
    IP-based rate limiter for /api/ write requests.

    Acts as a safety net in addition to DRF throttling:
    - Limits the number of write requests per client IP within a sliding window.
    - Converts django-ratelimit's Ratelimited exception into a JSON 429 response.

    How it works, in plain terms:
    * For every incoming request, `__call__` runs BEFORE the view.
    * If the client IP has already made too many write requests in the
      configured window (RATELIMIT_API_WINDOW seconds, max
      RATELIMIT_API_MAX_WRITES requests), the request is rejected
      immediately with an HTTP 429 response and never reaches the view.
    * Otherwise the request is passed down the middleware chain normally.
    """

    def __init__(self, get_response):
        # Django calls this once at startup. `get_response` is the rest of
        # the middleware stack + the view; we keep it so we can hand the
        # request on when the client is not rate limited.
        self.get_response = get_response

    def __call__(self, request):
        # Runs once per incoming HTTP request.
        # Step 1: decide whether this client has exceeded the write limit.
        if self._is_limited(request):
            # Step 2a: over the limit — short-circuit and reply 429 without
            # touching the view or the database at all.
            return self._rate_limited_response()
        # Step 2b: under the limit — continue to the view as usual and
        # return its response (possibly modified by other middleware).
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Map django-ratelimit's Ratelimited exception to a JSON 429 response."""
        # Django calls process_exception whenever a view raises. The
        # django-ratelimit package signals "too many requests" by raising
        # Ratelimited; we intercept it here and turn it into a friendly
        # JSON response instead of an HTML error page. Returning None lets
        # Django handle any other exception normally.
        if isinstance(exception, Ratelimited):
            return self._rate_limited_response()
        return None

    def _is_limited(self, request) -> bool:
        # Returns True when the request should be BLOCKED, False when it
        # may proceed. Implemented as a sliding window kept in Django's cache.
        # Check 1: is rate limiting switched on at all? (settings toggle)
        if not getattr(settings, 'API_RATE_LIMIT_ENABLED', True):
            return False
        # Check 2: only /api/ paths are protected; pages, admin, static
        # files are never limited.
        if not request.path.startswith('/api/'):
            return False
        # Check 3: only data-changing methods count towards the limit.
        if request.method not in WRITE_METHODS:
            return False
        # Never block monitoring/health endpoints
        # (load balancers / uptime monitors must always be able to reach them).
        if request.path.rstrip('/').endswith('health'):
            return False

        # Now count this request against the client's budget.
        window = getattr(settings, 'RATELIMIT_API_WINDOW', 60)
        max_writes = getattr(settings, 'RATELIMIT_API_MAX_WRITES', 120)
        # Identify the client by IP address (REMOTE_ADDR). Behind a proxy you
        # may need X-Forwarded-For instead — kept simple for this prototype.
        ident = request.META.get('REMOTE_ADDR', 'unknown')
        cache_key = f'rate-limit-api:{ident}'

        # Sliding window: the cache stores a list of timestamps of recent
        # write requests from this IP. Drop entries older than the window,
        # so the window "slides" forward with time.
        now = time.time()
        history = [t for t in cache.get(cache_key, []) if t > now - window]
        if len(history) >= max_writes:
            # Already at the budget — reject and log a warning for ops.
            logger.warning('Rate limit exceeded for %s (%s %s)', ident, request.method, request.path)
            return True
        # Still under the budget — record this request's timestamp and allow.
        # The cache entry expires after `window` seconds, cleaning itself up.
        history.append(now)
        cache.set(cache_key, history, window)
        return False

    @staticmethod
    def _rate_limited_response():
        # The JSON body the client receives when blocked.
        # 429 = "Too Many Requests"; clients should retry later.
        return JsonResponse(
            {'detail': 'Too many requests. Please try again later.'},
            status=429,
        )
