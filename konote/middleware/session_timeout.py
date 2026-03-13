"""Middleware to apply the admin-configurable session timeout.

Reads ``session_timeout_minutes`` from ``InstanceSetting`` (cached) and
calls ``request.session.set_expiry()`` so that Django's server-side
session engine honours the value the administrator chose in Settings.

Without this middleware, ``SESSION_COOKIE_AGE`` in settings.py is the
only timeout — and it ignores the admin setting entirely.
"""

from django.core.cache import cache


class SessionTimeoutMiddleware:
    """Set per-request session expiry from the admin-configurable timeout."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, "session"):
            timeout_minutes = self._get_timeout_minutes()
            request.session.set_expiry(timeout_minutes * 60)
        return self.get_response(request)

    @staticmethod
    def _get_timeout_minutes():
        """Return timeout in minutes from InstanceSetting (cached)."""
        cached = cache.get("instance_settings")
        if cached and "session_timeout_minutes" in cached:
            try:
                return int(cached["session_timeout_minutes"])
            except (ValueError, TypeError):
                pass

        # Cache miss — read from DB (same pattern as context_processors)
        try:
            from apps.admin_settings.models import InstanceSetting

            value = InstanceSetting.get_all().get("session_timeout_minutes", "30")
            return int(value)
        except Exception:
            return 30
