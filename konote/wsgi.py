"""WSGI config for KoNote Web."""
import os
from django.core.wsgi import get_wsgi_application


def get_default_settings():
    """
    Return appropriate settings module.

    WSGI is used by Gunicorn in production (Docker Compose / OVHcloud VPS).
    Respects DJANGO_SETTINGS_MODULE if explicitly set.
    """
    if "DJANGO_SETTINGS_MODULE" in os.environ:
        return os.environ["DJANGO_SETTINGS_MODULE"]

    # WSGI is always production (Gunicorn)
    return "konote.settings.production"


os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_default_settings())
application = get_wsgi_application()
