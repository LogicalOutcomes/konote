#!/usr/bin/env python
"""Django management command entry point."""
import os
import sys


def get_default_settings():
    """
    Auto-detect deployment environment and return appropriate settings module.

    Detection order:
    1. Explicit DJANGO_SETTINGS_MODULE (always respected)
    2. Any production deployment with DATABASE_URL (Docker Compose, OVHcloud, Azure)
    3. Local development (default)

    To force development settings when DATABASE_URL is set locally,
    set KONOTE_LOCAL_DEV=1.
    """
    if "DJANGO_SETTINGS_MODULE" in os.environ:
        return os.environ["DJANGO_SETTINGS_MODULE"]

    # Auto-detect production (has DATABASE_URL but not local dev override)
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
