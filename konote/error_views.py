"""Custom error handlers that render styled error pages."""

from django.template.response import TemplateResponse

# Exception messages that are safe to display to users.
# All PermissionDenied exceptions in KoNote use intentional user-facing messages.
# This safeguard prevents accidentally exposing technical details from third-party
# libraries that might raise PermissionDenied with internal information.
_SAFE_MESSAGE_MAX_LENGTH = 500


def permission_denied_view(request, exception):
    """
    Custom 403 handler that renders a styled error page.

    Django calls this when a PermissionDenied exception is raised.
    The middleware handles its own 403s with _forbidden_response().
    """
    # Only show the exception message if it's a reasonable user-facing string
    message = str(exception) if exception else None
    if message and len(message) > _SAFE_MESSAGE_MAX_LENGTH:
        message = None

    return TemplateResponse(
        request,
        "403.html",
        {"exception": message},
        status=403,
    )
