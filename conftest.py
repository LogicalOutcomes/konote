"""
Pytest configuration for KoNote Web.

This file configures Django before any test collection happens,
preventing the ImproperlyConfigured error when tests import Django models.
"""
import os

import django
import pytest


def pytest_configure():
    """Set up Django settings before any test collection."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "konote.settings.test")
    django.setup()


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    """Set up test databases including the audit database."""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        # Create tables for both databases
        call_command("migrate", "--run-syncdb", verbosity=0)
        call_command("migrate", "--database=audit", "--run-syncdb", verbosity=0)
