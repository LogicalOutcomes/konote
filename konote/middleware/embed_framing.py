"""Middleware to allow iframe embedding for public pages with ?embed=1.

Handles two cross-origin concerns when a page is embedded in an iframe:

1. **Framing policy** — replaces X-Frame-Options: DENY with a CSP
   frame-ancestors directive allowing the configured origins.
2. **CSRF cookies** — sets SameSite=None on CSRF and session cookies so
   the browser sends them on cross-origin POST from the iframe.
"""
from django.conf import settings
from django.http import HttpResponseForbidden


# Must match prefixes in konote/urls.py — update both together.
_EMBEDDABLE_PREFIXES = ("/register/", "/s/")


class EmbedFramingMiddleware:
    """Override framing and cookie policies for embed requests.

    When a request includes ?embed=1 and the URL matches an embeddable prefix,
    this middleware:
    - Replaces the global DENY framing policy with CSP frame-ancestors
    - Sets SameSite=None on CSRF and session cookies (required for cross-origin POST)

    If EMBED_ALLOWED_ORIGINS is empty, the embed request gets a 403.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._allowed_origins = getattr(settings, "EMBED_ALLOWED_ORIGINS", [])
        if self._allowed_origins:
            self._csp_header = (
                "frame-ancestors 'self' " + " ".join(self._allowed_origins)
            )
        else:
            self._csp_header = None
        self._cookie_names = (settings.CSRF_COOKIE_NAME, settings.SESSION_COOKIE_NAME)

    def __call__(self, request):
        is_embed = (
            request.GET.get("embed") == "1"
            and request.path.startswith(_EMBEDDABLE_PREFIXES)
        )
        if not is_embed:
            response = self.get_response(request)
            return response

        if not self._csp_header:
            return HttpResponseForbidden(
                "Iframe embedding is not enabled for this instance. "
                "Set EMBED_ALLOWED_ORIGINS in the environment."
            )

        response = self.get_response(request)

        # 1. Allow framing from configured origins.
        response["Content-Security-Policy"] = self._csp_header
        response.xframe_options_exempt = True
        # Remove X-Frame-Options: DENY set by XFrameOptionsMiddleware.
        # CSP frame-ancestors is the authoritative directive.
        if "X-Frame-Options" in response:
            del response["X-Frame-Options"]

        # 2. Set SameSite=None on CSRF and session cookies so the
        #    browser sends them on cross-origin POST from the iframe.
        #    SameSite=None requires Secure, which is already set globally.
        for cookie_name in self._cookie_names:
            if cookie_name in response.cookies:
                response.cookies[cookie_name]["samesite"] = "None"

        return response
