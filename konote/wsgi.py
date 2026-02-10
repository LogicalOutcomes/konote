"""WSGI config for KoNote Web."""
import os
from django.core.wsgi import get_wsgi_application


def get_default_settings():
    """
    Auto-detect deployment environment and return appropriate settings module.

    Detection order:
    1. Explicit DJANGO_SETTINGS_MODULE (always respected)
    2. Railway (RAILWAY_ENVIRONMENT)
    3. Azure App Service (WEBSITE_SITE_NAME)
    4. Elestio (ELESTIO_VM_NAME)
    5. Any deployment with DATABASE_URL
    6. Default to production (WSGI is typically production)
    """
    # If explicitly set, respect that
    if "DJANGO_SETTINGS_MODULE" in os.environ:
        return os.environ["DJANGO_SETTINGS_MODULE"]

    # Auto-detect Railway
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        return "konote.settings.production"

    # Auto-detect Azure App Service
    if os.environ.get("WEBSITE_SITE_NAME"):
        return "konote.settings.production"

    # Auto-detect Elestio
    if os.environ.get("ELESTIO_VM_NAME"):
        return "konote.settings.production"

    # Default to production for WSGI (gunicorn is typically production)
    return "konote.settings.production"


os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_default_settings())
application = get_wsgi_application()
