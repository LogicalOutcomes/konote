#!/usr/bin/env python
"""Django management command entry point."""
import os
import sys


def get_default_settings():
    """
    Auto-detect deployment environment and return appropriate settings module.

    Detection order:
    1. Explicit DJANGO_SETTINGS_MODULE (always respected)
    2. Railway (RAILWAY_ENVIRONMENT)
    3. Azure App Service (WEBSITE_SITE_NAME)
    4. Elestio (ELESTIO_VM_NAME)
    5. Any production deployment with DATABASE_URL (Docker, etc.)
    6. Local development (default)

    To force development settings when DATABASE_URL is set locally,
    set KONOTE_LOCAL_DEV=1.
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

    # Auto-detect any production deployment (has DATABASE_URL but not local dev)
    # This catches Docker, Kubernetes, or any other platform
    if os.environ.get("DATABASE_URL") and not os.environ.get("KONOTE_LOCAL_DEV"):
        return "konote.settings.production"

    # Default to development for local work
    return "konote.settings.development"


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_default_settings())
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed and "
            "available on your PYTHONPATH environment variable."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
