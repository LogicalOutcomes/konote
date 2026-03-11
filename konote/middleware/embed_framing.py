"""Middleware to allow iframe embedding for public pages with ?embed=1."""
from django.conf import settings
from django.http import HttpResponseForbidden


# URL prefixes where ?embed=1 is allowed.
_EMBEDDABLE_PREFIXES = ("/register/", "/s/")


class EmbedFramingMiddleware:
    """Override X-Frame-Options and CSP frame-ancestors for embed requests.

    When a request includes ?embed=1 and the URL matches an embeddable prefix,
    this middleware replaces the global DENY framing policy with a policy that
    allows the origins listed in settings.EMBED_ALLOWED_ORIGINS.

    If EMBED_ALLOWED_ORIGINS is empty, the embed request gets a 403.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_embed = (
            request.GET.get("embed") == "1"
            and any(request.path.startswith(p) for p in _EMBEDDABLE_PREFIXES)
        )

        if is_embed:
            allowed_origins = getattr(settings, "EMBED_ALLOWED_ORIGINS", [])
            if not allowed_origins:
                return HttpResponseForbidden(
                    "Iframe embedding is not enabled for this instance. "
                    "Set EMBED_ALLOWED_ORIGINS in the environment."
                )

        response = self.get_response(request)

        if is_embed:
            frame_ancestors = " ".join(allowed_origins)
            response["Content-Security-Policy"] = (
                f"frame-ancestors 'self' {frame_ancestors}"
            )
            response.xframe_options_exempt = True

        return response
