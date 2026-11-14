"""
SpaceGuard AI — DRF throttle classes.

Throttling = rate limiting at the API layer. DRF rejects requests with an
HTTP 429 response when a client makes too many requests in a given period.

This module defines ONE custom throttle class that works together with the
settings in settings.py:

  * 'DEFAULT_THROTTLE_RATES': {'ai': '10/min'}  <- named "scopes" and rates
  * 'DEFAULT_THROTTLE_CLASSES': ['spaceguard.throttling.ActionScopedRateThrottle']

A "scope" is just a named bucket with a rate (e.g. the 'ai' bucket allows
10 requests per minute). Individual ViewSet actions opt into a bucket by
setting a `throttle_scope_<action>` attribute (see the class docstring below).

Key = who is being counted:
  * Logged-in users are counted per user ( ScopedRateThrottle uses the
    username in the cache key, via get_cache_key from SimpleRateThrottle).
  * Anonymous (not logged-in) clients are counted per IP address.
  * So one heavy user cannot exhaust another user's budget.
"""
from rest_framework.throttling import ScopedRateThrottle


class ActionScopedRateThrottle(ScopedRateThrottle):
    """
    ScopedRateThrottle variant for ViewSet actions.

    Reads the throttle scope from a ``throttle_scope_<action>`` attribute on the
    ViewSet, e.g.::

        class MissionViewSet(viewsets.ModelViewSet):
            throttle_scope_assistant = 'ai'
            throttle_scope_analyze = 'ai'

    Views without a matching per-action attribute are not throttled, so the
    default ScopedRateThrottle behaviour (exempt unless ``throttle_scope`` is
    set) is preserved.

    Why per-action scopes? DRF's stock ScopedRateThrottle only looks at a
    single `throttle_scope` attribute for the whole view. We often want the
    same ViewSet to throttle only its expensive actions (like `assistant`
    and `analyze`, which call an AI model) while leaving cheap list/detail
    actions unlimited. This class makes the scope name depend on which
    action is being requested.
    """

    def allow_request(self, request, view):
        # DRF calls this for every request to decide: allow or 429?
        # Must return True to allow, False (throttle_failure) to reject.

        # Step 1: which ViewSet action is running? ('list', 'retrieve',
        # 'assistant', 'analyze', ...). `view.action` is None outside ViewSets.
        action = getattr(view, 'action', None)
        # Step 2: does the ViewSet define a scope for THIS action,
        # e.g. `throttle_scope_assistant = 'ai'`?
        scope = getattr(view, f'throttle_scope_{action}', None) if action else None
        if scope is None:
            return True  # not throttled for this action

        # Step 3: resolve the rate for this scope from settings
        # ('DEFAULT_THROTTLE_RATES' -> {'ai': '10/min'}), then split the
        # rate string into a request count and a duration in seconds
        # (e.g. ('10/min') -> num_requests=10, duration=60).
        self.scope = scope
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        # Step 4: build the cache key that identifies WHO is being counted
        # (per user for authenticated requests, per IP for anonymous ones).
        # A None key means "cannot identify" -> err on the side of allowing.
        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        # Step 5: load the client's recent request timestamps from the cache.
        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Drop any timestamps outside the window
        # (the list is ordered oldest-first, so we pop from the end until
        # every remaining timestamp is inside the current duration window —
        # this makes it a "sliding" window rather than a fixed one).
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        # Step 6: is the client already at their request budget?
        if len(self.history) >= self.num_requests:
            # Over budget -> throttle_failure() returns False, DRF then
            # responds with HTTP 429.
            return self.throttle_failure()
        # Under budget -> throttle_success() records this request's timestamp
        # back into the cache and returns True (allowed).
        return self.throttle_success()
