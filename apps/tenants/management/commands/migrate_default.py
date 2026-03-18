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

Two-phase algorithm:
  Phase 1 — Physical detection: scan TENANT_APP migrations and check
    information_schema for missing columns (AddField) and tables (CreateModel).
    Collect refs into a to_remove set without touching the DB yet.
  Phase 2 — Dependency propagation: walk ALL applied migrations repeatedly
    and add any whose dependency is in to_remove.  Repeat until stable.
    This handles cross-app chains (e.g. auth_app.0001 depends on auth.0012).
  Phase 3 — Bulk removal: delete all records in to_remove from
    django_migrations in one pass.

When ghosts were removed and the healer re-queues initial migrations, tables
that already exist (e.g. auth_app_user from a reseed that only cleared rows)
would cause CREATE TABLE to fail.  fake_initial=True tells Django to skip
CreateModel for tables that already exist, so those migrations are faked
instead of re-executed.

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

    def _constraint_exists(self, cursor, table_name, constraint_name):
        """Return True when a named constraint already exists on a public table."""
        if cursor.db.vendor != "postgresql":
            constraints = cursor.db.introspection.get_constraints(cursor, table_name)
            return constraint_name in constraints

        cursor.execute(
            """
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            WHERE n.nspname = 'public'
              AND t.relname = %s
              AND c.conname = %s
            """,
            [table_name, constraint_name],
        )
        return bool(cursor.fetchone())

    def _operation_schema_exists(self, cursor, app_label, op):
        """Return True when the schema change for a migration operation already exists."""
        from django.apps import apps as django_apps
        from django.db.migrations.operations.fields import AddField
        from django.db.migrations.operations.models import AddConstraint, CreateModel

        if isinstance(op, AddField):
            try:
                model = django_apps.get_model(app_label, op.model_name)
                field = model._meta.get_field(op.name)
                table_name = model._meta.db_table
                col_name = field.column
            except Exception:
                return None

            # M2M fields don't have a column on the source table.
            # Check both the column value and the field type, because
            # ManyToManyField with through tables returns a non-None
            # .column (the attname) despite having no physical column.
            if col_name is None or field.many_to_many:
                return None

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
            return bool(cursor.fetchone())

        if isinstance(op, CreateModel):
            # Skip swappable models whose missing table can be legitimate.
            if getattr(op, 'options', {}).get('swappable'):
                return None

            try:
                model = django_apps.get_model(app_label, op.name)
                table_name = model._meta.db_table
            except LookupError:
                return None

            cursor.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name   = %s
                """,
                [table_name],
            )
            return bool(cursor.fetchone())

        if isinstance(op, AddConstraint):
            try:
                model = django_apps.get_model(app_label, op.model_name)
                table_name = model._meta.db_table
                constraint_name = op.constraint.name
            except Exception:
                return None

            return self._constraint_exists(cursor, table_name, constraint_name)

        return None

    # ------------------------------------------------------------------
    # Ghost-migration healing
    # ------------------------------------------------------------------

    def _remove_ghost_tenant_migrations(self, connection):
        """Remove django_migrations records whose schema changes were never applied.

        Returns True if any records were removed (caller should enable
        fake_initial so re-applied initial migrations skip tables that already
        exist on disk), or False if the database is clean.
        """
        import re
        from django.conf import settings as django_settings
        from django.db.migrations.exceptions import InconsistentMigrationHistory
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.recorder import MigrationRecorder
        from django.db import router as dj_router

        recorder = MigrationRecorder(connection)
        if not recorder.has_table():
            return False
        applied = set(recorder.applied_migrations())
        if not applied:
            return False

        shared_labels = {app.rsplit(".", 1)[-1] for app in django_settings.SHARED_APPS}
        tenant_labels = {
            app.rsplit(".", 1)[-1]
            for app in django_settings.TENANT_APPS
            if app.rsplit(".", 1)[-1] not in shared_labels
        }

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        apps_to_check = {app for (app, _) in applied if app in tenant_labels}

        # --- Phase 1: physically detect missing schema ---
        to_remove = set()
        # Constraints missing from migrations already recorded as applied.
        # These are NOT removed — instead, created directly after Phase 3
        # to break the fake_initial cycle where initial migrations containing
        # both CreateModel and AddConstraint get fully faked (tables exist),
        # leaving the constraint un-created forever.
        missing_constraints = []  # list of (app_label, AddConstraint op)

        with connection.cursor() as cursor:
            for app_label in sorted(apps_to_check):
                for migration_name in sorted(
                    name for (a, name) in applied if a == app_label
                ):
                    try:
                        migration = loader.get_migration(app_label, migration_name)
                    except KeyError:
                        continue

                    for op in migration.operations:
                        exists = self._operation_schema_exists(cursor, app_label, op)
                        if exists is None:
                            continue

                        if not exists:
                            # Missing constraints are handled separately: we
                            # create them directly rather than re-queuing the
                            # whole migration (which fake_initial would skip).
                            from django.db.migrations.operations.models import AddConstraint
                            if isinstance(op, AddConstraint):
                                missing_constraints.append((app_label, op))
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  Missing constraint detected:"
                                        f" {app_label}.{migration_name}"
                                        f" — {op.constraint.name}. Will create directly."
                                    )
                                )
                                continue

                            to_remove.add((app_label, migration_name))

                            if hasattr(op, "model_name") and hasattr(op, "name"):
                                missing_object = f"column {op.model_name}.{op.name}"
                            else:
                                missing_object = "schema object"

                            self.stdout.write(
                                self.style.WARNING(
                                    f"  Ghost migration detected:"
                                    f" {app_label}.{migration_name}"
                                    f" — {missing_object} is missing. Will re-apply."
                                )
                            )
                            break

        # --- Phase 2: orphan detection + transitive propagation ---
        #
        # This phase runs UNCONDITIONALLY — it catches two situations:
        #
        # (a) Migrations added to to_remove in Phase 1 have downstream
        #     dependents in other apps (e.g. auth_app.0001 → auth.0012).
        #
        # (b) A previous boot's healer already removed some records from
        #     django_migrations (e.g. auth.0001–0012), but crashed before
        #     removing their dependents (e.g. auth_app.0001_initial).  On
        #     the next boot Phase 1 finds nothing (tables now missing from
        #     applied, not detectable via information_schema), so Phase 2
        #     must independently catch these "orphaned" dependents.
        #
        # Strategy: any applied migration whose dependency is absent from the
        # current `applied` snapshot must also be removed.  We skip deps that
        # belong to a different database entirely (e.g. audit app → audit DB)
        # using router.allow_migrate — this is more reliable than checking
        # apps_in_scope because the dep's app may have already been healed out
        # of `applied` on a previous boot.
        #
        # Repeat until the set stabilises (handles chains of arbitrary depth).

        changed = True
        while changed:
            changed = False
            for app, name in set(applied):
                if (app, name) in to_remove:
                    continue
                try:
                    migration = loader.get_migration(app, name)
                except KeyError:
                    continue
                for dep in migration.dependencies:
                    if len(dep) != 2:
                        continue
                    dep_app, dep_name = dep
                    if dep_name in ("__first__", "__latest__"):
                        continue
                    # Skip deps that route to a different database entirely
                    # (e.g. audit app → audit DB).  We only want to propagate
                    # for deps that legitimately belong to THIS database —
                    # using allow_migrate is correct even after TenantSyncRouter
                    # is removed, because AuditRouter still blocks audit deps.
                    if not dj_router.allow_migrate(connection.alias, dep_app):
                        continue
                    dep_key = (dep_app, dep_name)
                    # Trigger if dep is already absent from applied OR was
                    # flagged for removal in Phase 1 or an earlier iteration.
                    if dep_key not in applied or dep_key in to_remove:
                        to_remove.add((app, name))
                        changed = True
                        break

        # --- Phase 3: bulk removal ---
        # (runs only when Phase 1/2 found ghost/orphan records)
        for app_label, migration_name in sorted(to_remove):
            recorder.record_unapplied(app_label, migration_name)
            self.stdout.write(
                self.style.NOTICE(
                    f"    Removed record: {app_label}.{migration_name}"
                )
            )

        # --- Phase 3.5: create missing constraints directly ---
        #
        # Constraints detected as missing in Phase 1 are NOT re-queued (which
        # would cause fake_initial to skip them along with the CreateModel in
        # their initial migration).  Instead, create them directly via
        # schema_editor so they exist before Django's migrate runs.
        if missing_constraints:
            from django.apps import apps as django_apps

            for app_label, op in missing_constraints:
                try:
                    model = django_apps.get_model(app_label, op.model_name)
                    with connection.schema_editor() as editor:
                        editor.add_constraint(model, op.constraint)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    Created constraint: {op.constraint.name}"
                        )
                    )
                except Exception as exc:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    Could not create constraint"
                            f" {op.constraint.name}: {exc}"
                        )
                    )

        # --- Phase 4: direct consistency pre-flight ---
        #
        # Phases 1–3 propagate through the dependency graph but Phase 2 skips
        # deps with dep_name == '__first__' (used by swappable_dependency, e.g.
        # admin.0001_initial -> ('auth_app', '__first__')).  Phase 4 runs
        # Django's own check_consistent_history iteratively, removing whichever
        # migration it reports as inconsistent until the database is clean.
        # This is the authoritative catch-all for any shape Phase 2 missed.
        phase4_removed = False
        while True:
            try:
                MigrationLoader(connection).check_consistent_history(connection)
                break
            except InconsistentMigrationHistory as exc:
                m = re.match(r"Migration (\w+)\.(\w+) is applied", str(exc))
                if not m:
                    raise
                bad_app, bad_name = m.group(1), m.group(2)
                recorder.record_unapplied(bad_app, bad_name)
                self.stdout.write(
                    self.style.NOTICE(
                        f"    Pre-flight removed: {bad_app}.{bad_name}"
                    )
                )
                phase4_removed = True

        return bool(to_remove or phase4_removed or missing_constraints)

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
            ghosts_removed = self._remove_ghost_tenant_migrations(connections[db_name])

            if ghosts_removed:
                # Some initial migrations were re-queued.  If their tables
                # already exist on disk (e.g. after a reseed that only cleared
                # rows), CreateModel would fail.  fake_initial tells Django to
                # skip CreateModel when the target table already exists.
                options["fake_initial"] = True

            # Phase 5: catch duplicate column/table/constraint errors and dependency-order
            # errors during migration application.
            #
            # Two scenarios handled:
            #
            # (a) DuplicateColumn / DuplicateTable / DuplicateObject — a pending migration tries to
            #     ADD schema that already exists.  This means the schema was applied
            #     manually or by a previous run that crashed before recording it.
            #     Fix: find the migration(s) where ALL schema-creating operations
            #     already exist in the DB and fake them.  We require ALL checkable
            #     operations to pass so we don't falsely fake a migration that only
            #     partially applied (which would leave genuinely missing schema
            #     un-created on the next run).
            #
            # (b) InconsistentMigrationHistory — a migration is recorded as applied
            #     but one of its dependencies is not.  This happens when Phase 5(a)
            #     fakes a migration whose dependency is a pure RunPython (data
            #     migration) with no schema to verify, so it was never faked.
            #     Fix: parse the error to identify the missing dependency and fake it.
            import re as _re
            import psycopg.errors as psycopg_errors
            from django.db import ProgrammingError as DjProgrammingError
            from django.db.migrations.exceptions import InconsistentMigrationHistory
            from django.db.migrations.executor import MigrationExecutor
            from django.db.migrations.recorder import MigrationRecorder

            connection = connections[db_name]
            recorder = MigrationRecorder(connection)

            for _attempt in range(500):  # safety limit
                try:
                    super().handle(*args, **options)
                    break

                except InconsistentMigrationHistory as e:
                    # "Migration app.name is applied before its dependency app.name"
                    m = _re.match(
                        r"Migration (\w+)\.(\w+) is applied before its dependency"
                        r" (\w+)\.(\w+)",
                        str(e),
                    )
                    if not m:
                        raise
                    dep_app, dep_name = m.group(3), m.group(4)
                    recorder.record_applied(dep_app, dep_name)
                    self.stdout.write(
                        self.style.NOTICE(
                            f"  Phase 5: auto-faked {dep_app}.{dep_name}"
                            f" (missing dependency)"
                        )
                    )

                except DjProgrammingError as e:
                    cause = e.__cause__
                    if not isinstance(
                        cause,
                        (
                            psycopg_errors.DuplicateColumn,
                            psycopg_errors.DuplicateTable,
                            psycopg_errors.DuplicateObject,
                        ),
                    ):
                        raise

                    # Find pending migrations where ALL schema-creating operations
                    # already exist in the DB, and fake only those.
                    # Requiring ALL to pass prevents falsely faking migrations that
                    # only partially applied (e.g. a migration that creates two
                    # tables where only one exists).
                    executor = MigrationExecutor(connection)
                    applied = executor.loader.applied_migrations  # dict, not callable
                    faked_any = False

                    with connection.cursor() as cursor:
                        for app, name in sorted(executor.loader.disk_migrations):
                            if (app, name) in applied:
                                continue
                            migration = executor.loader.disk_migrations[(app, name)]

                            # Collect pass/fail for every schema-checkable operation.
                            checks: list[bool] = []
                            for op in migration.operations:
                                exists = self._operation_schema_exists(cursor, app, op)
                                if exists is not None:
                                    checks.append(exists)

                            # Fake only when every checkable op already exists
                            # (and there is at least one checkable op).
                            if checks and all(checks):
                                recorder.record_applied(app, name)
                                self.stdout.write(
                                    self.style.NOTICE(
                                        f"  Phase 5: auto-faked {app}.{name}"
                                        f" (schema already exists)"
                                    )
                                )
                                faked_any = True

                    if not faked_any:
                        raise  # no progress possible
            else:
                raise RuntimeError(
                    "migrate_default Phase 5: exceeded safety limit faking"
                    " duplicate-schema migrations"
                )
        finally:
            # Always restore the original router list.
            django_settings.DATABASE_ROUTERS = original_routers
            dj_router._routers = None
            try:
                del dj_router.__dict__["routers"]
            except KeyError:
                pass
