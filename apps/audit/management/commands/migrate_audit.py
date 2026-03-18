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

    def handle(self, *args, **options):
        self._heal_audit_ghosts(options.get("database", "audit"))
        super().handle(*args, **options)

    def _heal_audit_ghosts(self, db_alias):
        """Remove ghost migration records from the audit database.

        If a migration is recorded as applied but its schema changes (columns)
        are missing from the actual table, delete the record so Django will
        re-apply it.
        """
        from django.db import connections
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.operations.fields import AddField
        from django.db.migrations.recorder import MigrationRecorder

        connection = connections[db_alias]
        recorder = MigrationRecorder(connection)
        if not recorder.has_table():
            return

        applied = set(recorder.applied_migrations())
        if not applied:
            return

        # Only check audit app migrations.
        audit_applied = {(app, name) for app, name in applied if app == "audit"}
        if not audit_applied:
            return

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        to_remove = set()

        with connection.cursor() as cursor:
            for app, name in sorted(audit_applied):
                try:
                    migration = loader.get_migration(app, name)
                except KeyError:
                    continue

                for op in migration.operations:
                    if not isinstance(op, AddField):
                        continue
                    try:
                        from django.apps import apps as django_apps
                        model = django_apps.get_model(app, op.model_name)
                        field = model._meta.get_field(op.name)
                        col_name = field.column
                    except Exception:
                        continue
                    if col_name is None or field.many_to_many:
                        continue

                    table_name = model._meta.db_table
                    cursor.execute(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = %s AND column_name = %s
                        """,
                        [table_name, col_name],
                    )
                    if not cursor.fetchone():
                        to_remove.add((app, name))
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Audit ghost detected: {app}.{name}"
                                f" — column {op.model_name}.{op.name} is missing."
                                f" Will re-apply."
                            )
                        )
                        break

        for app, name in sorted(to_remove):
            recorder.record_unapplied(app, name)
            self.stdout.write(
                self.style.NOTICE(
                    f"    Removed audit record: {app}.{name}"
                )
            )
