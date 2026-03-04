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

Ghost-migration healing
-----------------------
An older version of this command (before PR #249) ran Django's migrate with
TenantSyncRouter still in place.  TenantSyncRouter blocked the ALTER TABLE SQL
but Django's recorder still wrote the migration as applied in django_migrations.

Result: columns like metric_definitions.warn_min were recorded as applied but
never actually added to the database ("ghost records").  On subsequent runs the
bypass code finds those records and reports "No migrations to apply", while the
columns are still missing.

The _remove_ghost_tenant_migrations helper detects these by querying
information_schema and deletes any ghost records before super().handle() runs,
so Django will re-apply the truly missing schema changes cleanly.

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

    # ------------------------------------------------------------------
    # Ghost-migration healing
    # ------------------------------------------------------------------

    def _remove_ghost_tenant_migrations(self, connection):
        """Remove django_migrations records whose schema changes were never applied.

        When TenantSyncRouter is in place, Django skips the ALTER TABLE /
        CREATE TABLE SQL for TENANT_APPS but still calls
        recorder.record_applied().  This healer detects such "ghost" records
        by comparing what django_migrations claims was applied against what
        information_schema actually contains, then deletes the ghost records so
        that the subsequent super().handle() call can re-apply them properly.

        Only AddField and CreateModel operations are checked — these are the
        structural changes that leave a detectable signature in
        information_schema.columns / information_schema.tables.
        """
        from django.apps import apps as django_apps
        from django.conf import settings as django_settings
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.operations.fields import AddField
        from django.db.migrations.operations.models import CreateModel
        from django.db.migrations.recorder import MigrationRecorder

        recorder = MigrationRecorder(connection)
        if not recorder.has_table():
            return
        applied = recorder.applied_migrations()
        if not applied:
            return

        shared_labels = {app.rsplit(".", 1)[-1] for app in django_settings.SHARED_APPS}
        tenant_labels = {
            app.rsplit(".", 1)[-1]
            for app in django_settings.TENANT_APPS
            if app.rsplit(".", 1)[-1] not in shared_labels
        }

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        apps_to_check = {app for (app, _) in applied if app in tenant_labels}

        with connection.cursor() as cursor:
            for app_label in sorted(apps_to_check):
                app_applied = sorted(
                    name for (a, name) in applied if a == app_label
                )
                ghost_found = False

                for migration_name in app_applied:
                    if ghost_found:
                        # Cascade: once a ghost is found, subsequent
                        # migrations for this app may also be incomplete.
                        recorder.record_unapplied(app_label, migration_name)
                        self.stdout.write(
                            self.style.NOTICE(
                                f"    Removed dependent ghost record:"
                                f" {app_label}.{migration_name}"
                            )
                        )
                        continue

                    try:
                        migration = loader.get_migration(app_label, migration_name)
                    except KeyError:
                        # File missing (squashed or deleted) — skip.
                        continue

                    for op in migration.operations:
                        if isinstance(op, AddField):
                            try:
                                model = django_apps.get_model(app_label, op.model_name)
                                field = model._meta.get_field(op.name)
                                table_name = model._meta.db_table
                                col_name = field.column
                            except Exception:
                                continue

                            cursor.execute(
                                """
                                SELECT 1
                                FROM information_schema.columns
                                WHERE table_schema = 'public'
                                  AND table_name   = %s
                                  AND column_name  = %s
                                """,
                                [table_name, col_name],
                            )
                            if not cursor.fetchone():
                                ghost_found = True
                                recorder.record_unapplied(app_label, migration_name)
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  Ghost migration detected:"
                                        f" {app_label}.{migration_name}"
                                        f" — column {table_name}.{col_name}"
                                        f" is missing from the database."
                                        f" Record removed; will re-apply."
                                    )
                                )
                                break

                        elif isinstance(op, CreateModel):
                            try:
                                model = django_apps.get_model(app_label, op.name)
                                table_name = model._meta.db_table
                            except LookupError:
                                table_name = f"{app_label}_{op.name.lower()}"

                            cursor.execute(
                                """
                                SELECT 1
                                FROM information_schema.tables
                                WHERE table_schema = 'public'
                                  AND table_name   = %s
                                """,
                                [table_name],
                            )
                            if not cursor.fetchone():
                                ghost_found = True
                                recorder.record_unapplied(app_label, migration_name)
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  Ghost migration detected:"
                                        f" {app_label}.{migration_name}"
                                        f" — table {table_name}"
                                        f" is missing from the database."
                                        f" Record removed; will re-apply."
                                    )
                                )
                                break

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        from django.conf import settings as django_settings
        from django.db import connections, router as dj_router

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
            # Heal ghost records BEFORE running migrate.  Ghost records exist
            # when a previous run recorded migrations in django_migrations but
            # TenantSyncRouter silently skipped the underlying SQL.
            db_name = options.get("database", "default")
            self._remove_ghost_tenant_migrations(connections[db_name])

            super().handle(*args, **options)
        finally:
            # Always restore the original router list.
            django_settings.DATABASE_ROUTERS = original_routers
            dj_router._routers = None
            try:
                del dj_router.__dict__["routers"]
            except KeyError:
                pass
