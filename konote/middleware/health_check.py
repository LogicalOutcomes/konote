"""Health check middleware for KoNote.

Handles GET /health/ before TenantMainMiddleware attempts domain lookup.
TenantMainMiddleware requires a resolvable tenant domain — internal health
checks from Railway / Docker or load-balancers arrive on an IP or an
unregistered host, causing a 404/500 before the app is reachable.

This middleware intercepts /health/ first and returns a minimal 200 response
so the orchestrator knows the container is alive.
"""

from django.http import HttpResponse


class HealthCheckMiddleware:
    """Return 200 OK for GET /health/ without hitting tenant resolution."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and request.path == "/health/":
            return HttpResponse("ok", content_type="text/plain", status=200)
        return self.get_response(request)
