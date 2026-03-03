"""
Management command to run migrations on the audit database.

django-tenants replaces the standard `migrate` command with `migrate_schemas`,
which calls `connection.set_schema()` on every database connection.  The audit
database uses the standard Django PostgreSQL backend (not
`django_tenants.postgresql_backend`), so it does not have `set_schema`, which
causes an AttributeError when the entrypoint runs:

    python manage.py migrate --database=audit

This command imports Django's original migrate Command *directly* (bypassing
the django-tenants override that Django's command-lookup mechanism would find)
and defaults the database to "audit" so the entrypoint can simply call:

    python manage.py migrate_audit
"""

# Import from Django's module path directly, not through Django's command
# lookup, so we get the real migrate Command — not the django-tenants override.
from django.core.management.commands.migrate import Command as DjangoMigrateCommand


class Command(DjangoMigrateCommand):
    help = "Run Django migrations on the audit database (bypasses django-tenants schema routing)."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        # Default --database to "audit" so callers don't have to specify it.
        parser.set_defaults(database="audit")
