"""Production settings — secure defaults."""
import os
from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# HTTPS — Railway handles TLS at the edge, so we don't redirect internally.
# SECURE_PROXY_SSL_HEADER tells Django to trust the proxy's forwarded header.
SECURE_SSL_REDIRECT = False  # Railway edge handles HTTPS redirect
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSP — production overrides
# ─────────────────────────────────────────────────────────────────────
# Report URI: set CSP_REPORT_URI_ENDPOINT in your environment to receive
# browser reports when a CSP violation occurs (e.g. a Sentry or report-uri
# endpoint). Leave unset to disable reporting.
#
# Note on 'unsafe-inline' for styles: Pico CSS currently requires it.
# If you vendor Pico locally in future, you can remove 'unsafe-inline'
# from CSP_STYLE_SRC in base.py for a tighter policy.
# ─────────────────────────────────────────────────────────────────────
_csp_report_uri = os.environ.get("CSP_REPORT_URI_ENDPOINT")
if _csp_report_uri:
    CSP_REPORT_URI = (_csp_report_uri,)
