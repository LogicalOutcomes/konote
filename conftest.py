"""
Pytest configuration for KoNote Web.

This file configures Django before any test collection happens,
preventing the ImproperlyConfigured error when tests import Django models.

Multi-tenancy: provides a `tenant` fixture that creates a test agency
with its own schema, so tests run within a tenant context automatically.
Tests that use SQLite (the default for speed) skip tenant schema creation
since SQLite doesn't support PostgreSQL schemas — they run normally.
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
    """Set up test databases including the audit database.

    When using SQLite, we bypass django-tenants' migrate_schemas command
    (which requires PostgreSQL) and call Django's original migrate directly.
    """
    with django_db_blocker.unblock():
        if _using_postgresql():
            from django.core.management import call_command
            call_command("migrate_schemas", "--shared", verbosity=0)
            call_command("migrate", "--database=audit", "--run-syncdb", verbosity=0)
        else:
            # SQLite: call Django's original migrate, not django-tenants' override
            from django.core.management.commands.migrate import Command as MigrateCommand
            _common_opts = dict(
                run_syncdb=True, verbosity=0,
                app_label=None, migration_name=None, no_color=False,
                fake=False, fake_initial=False, plan=False,
                check_unapplied=False, prune=False,
                skip_checks=True, force_color=False,
                interactive=False,
            )
            migrate_cmd = MigrateCommand()
            migrate_cmd.execute(database="default", **_common_opts)
            migrate_cmd = MigrateCommand()
            migrate_cmd.execute(database="audit", **_common_opts)


def _using_postgresql():
    """Check if tests are running against PostgreSQL (vs SQLite)."""
    from django.conf import settings
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    return "postgresql" in engine


@pytest.fixture
def tenant(db):
    """Create a test tenant with its own schema.

    When running against PostgreSQL, this creates a real Agency + AgencyDomain
    in the shared schema, then sets the connection to use the tenant schema.

    When running against SQLite (default for fast tests), this creates the
    Agency and Domain objects but cannot create a real schema. Tests still
    get the tenant objects for any code that checks request.tenant.

    Usage:
        def test_something(tenant):
            # tenant is an Agency instance
            # connection is set to the tenant's schema (on PostgreSQL)
            ...
    """
    from apps.tenants.models import Agency, AgencyDomain

    agency = Agency(
        name="Test Agency",
        short_code="test-agency",
        schema_name="test_agency",
    )
    agency.save()

    AgencyDomain.objects.create(
        domain="test-agency.localhost",
        tenant=agency,
        is_primary=True,
    )

    if _using_postgresql():
        from django.db import connection
        connection.set_tenant(agency)

    yield agency

    if _using_postgresql():
        from django.db import connection
        connection.set_schema_to_public()
