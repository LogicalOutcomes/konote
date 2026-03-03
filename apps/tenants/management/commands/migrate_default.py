"""Management command to run migrations on the default database.

Problem
-------
django_tenants replaces the standard `migrate` command with `migrate_schemas`,
which routes tenant-app migrations (e.g. `clients`) only to *tenant* PostgreSQL
schemas.  The *public* schema (used by management commands such as `seed`, and
by the initial single-tenant installation) is skipped by TenantSyncRouter.

This means that when a new migration is added to a tenant app (e.g.
`clients.0034`), running `manage.py migrate` (= `migrate_schemas`) does NOT
apply it to the public schema -- the table there is left behind.

This command imports Django's original migrate Command directly (bypassing
the django_tenants override) and defaults the database to "default".  Because
it uses the real migrate, TenantSyncRouter is not involved, so all pending
migrations are applied directly to whichever schema the connection is in
(the public schema in production).

Usage in entrypoint.sh
----------------------
    python manage.py migrate_default --noinput

Run this BEFORE `manage.py migrate` (the django_tenants migrate_schemas) so
the public schema is always up to date.
"""

from django.core.management.commands.migrate import Command as DjangoMigrateCommand


class Command(DjangoMigrateCommand):
    help = (
        "Run Django migrations on the default database, bypassing django-tenants "
        "schema routing so the public schema is kept in sync."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        # Default --database to "default" (explicit for clarity).
        parser.set_defaults(database="default")
