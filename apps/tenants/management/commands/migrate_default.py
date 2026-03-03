"""Management command to run migrations on the default database.

Problem
-------
django_tenants replaces `migrate` with `migrate_schemas`, which:
  1. Applies SHARED_APPS migrations to the public schema.
  2. Applies TENANT_APPS migrations to each non-public tenant schema.

In a single-agency deployment (schema_name='public'), step 2 has zero schemas
to process — `.exclude(schema_name='public')` matches nothing.  Additionally,
TenantSyncRouter.allow_migrate() returns False for TENANT_APPS when
connection.schema_name equals PUBLIC_SCHEMA_NAME, so even a plain
`manage.py migrate` cannot apply them there.

Result: any new TENANT_APP migration (plans, events, clients, etc.) is NEVER
applied to the public schema after the initial flat-to-tenant upgrade.

Fix
---
This command temporarily removes TenantSyncRouter from DATABASE_ROUTERS and
runs Django's standard migrate, allowing ALL pending migrations (shared AND
tenant-app) to be applied to the public schema.  AuditRouter stays in place
so audit-app migrations are still directed only to the 'audit' database.

Usage in entrypoint.sh
----------------------
    python manage.py migrate_default --noinput

Run this BEFORE `manage.py migrate` (migrate_schemas) so the public schema
is up to date before per-tenant schemas are processed.
"""

from django.core.management.commands.migrate import Command as DjangoMigrateCommand


class Command(DjangoMigrateCommand):
    help = (
        "Apply all pending migrations to the default database's public schema, "
        "bypassing TenantSyncRouter so TENANT_APPS migrations run in "
        "single-agency deployments where schema_name='public'."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.set_defaults(database="default")

    def handle(self, *args, **options):
        from django.conf import settings as django_settings
        from django.db import router as dj_router

        # TenantSyncRouter.allow_migrate() returns False for TENANT_APPS
        # (plans, events, clients, etc.) whenever connection.schema_name equals
        # PUBLIC_SCHEMA_NAME ('public').  This permanently prevents those
        # migrations from being applied to the public schema.
        # We temporarily remove TenantSyncRouter so all pending migrations can
        # run.  After this command completes the original router list is
        # restored.
        original_routers = list(django_settings.DATABASE_ROUTERS)
        filtered_routers = [
            r for r in original_routers
            if not (isinstance(r, str) and "TenantSyncRouter" in r)
        ]
        django_settings.DATABASE_ROUTERS = filtered_routers

        # ConnectionRouter.routers is a @cached_property; clear it so Django
        # re-instantiates routers from the updated DATABASE_ROUTERS list.
        # Also reset _routers to None so the cached_property re-reads settings.
        dj_router._routers = None
        try:
            del dj_router.__dict__["routers"]
        except KeyError:
            pass

        try:
            super().handle(*args, **options)
        finally:
            # Always restore the original router list.
            django_settings.DATABASE_ROUTERS = original_routers
            dj_router._routers = None
            try:
                del dj_router.__dict__["routers"]
            except KeyError:
                pass
