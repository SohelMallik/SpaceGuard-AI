"""
SpaceGuard AI — DRF throttle classes.
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
    """

    def allow_request(self, request, view):
        action = getattr(view, 'action', None)
        scope = getattr(view, f'throttle_scope_{action}', None) if action else None
        if scope is None:
            return True  # not throttled for this action

        self.scope = scope
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Drop any timestamps outside the window
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
        return self.throttle_success()
