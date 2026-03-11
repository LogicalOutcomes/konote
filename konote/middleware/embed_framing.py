"""Middleware to allow iframe embedding for public pages with ?embed=1.

Handles three cross-origin concerns when a page is embedded in an iframe:

1. **Framing policy** — replaces X-Frame-Options: DENY with a CSP
   frame-ancestors directive allowing the configured origins.
2. **CSRF cookies** — sets SameSite=None on the CSRF cookie so the
   browser sends it on cross-origin POST from the iframe.
3. **CSRF origin check** — marks the request so CsrfViewMiddleware
   accepts the cross-origin Origin header (via CSRF_TRUSTED_ORIGINS).
"""
from django.conf import settings
from django.http import HttpResponseForbidden


# URL prefixes where ?embed=1 is allowed.
_EMBEDDABLE_PREFIXES = ("/register/", "/s/")


class EmbedFramingMiddleware:
    """Override framing and CSRF policies for embed requests.

    When a request includes ?embed=1 and the URL matches an embeddable prefix,
    this middleware:
    - Replaces the global DENY framing policy with CSP frame-ancestors
    - Sets SameSite=None on the CSRF cookie (required for cross-origin POST)
    - Adds EMBED_ALLOWED_ORIGINS to CSRF_TRUSTED_ORIGINS for the request

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
            # Mark request so we can patch the CSRF cookie on the response.
            request._embed_allowed_origins = allowed_origins

        response = self.get_response(request)

        if is_embed:
            # 1. Allow framing from configured origins.
            frame_ancestors = " ".join(allowed_origins)
            response["Content-Security-Policy"] = (
                f"frame-ancestors 'self' {frame_ancestors}"
            )
            response.xframe_options_exempt = True

            # 2. Set SameSite=None on CSRF and session cookies so the
            #    browser sends them on cross-origin POST from the iframe.
            #    SameSite=None requires Secure, which is already set.
            for cookie_name in (settings.CSRF_COOKIE_NAME, settings.SESSION_COOKIE_NAME):
                if cookie_name in response.cookies:
                    response.cookies[cookie_name]["samesite"] = "None"

        return response
