"""
Preflight check for KoNote local development.

Validates the local environment is ready for running Django: settings module,
database backends, connectivity, migrations, test data, and the QA scenario
holdout repo.

Usage:
    python manage.py preflight
"""

import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "Validate the local development environment is ready for running Django."

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("KoNote Preflight Check")
        self.stdout.write("=" * 55)

        critical_ok = True

        # 1. Settings module
        self._check_settings_module()

        # 2. Database backends
        self._check_database_backends()

        # 3. Database connectivity (critical)
        if not self._check_database_connectivity():
            critical_ok = False

        # 4. Migrations current (warning only)
        self._check_migrations()

        # 5. Test data exists (warning only)
        self._check_test_data()

        # 6. Holdout repo
        if not self._check_holdout_repo():
            critical_ok = False

        # Summary
        self.stdout.write("")
        if critical_ok:
            self.stdout.write(self.style.SUCCESS(
                "Preflight PASSED — ready to run"
            ))
            sys.exit(0)
        else:
            self.stdout.write(self.style.ERROR(
                "Preflight FAILED — fix issues above"
            ))
            sys.exit(1)

    # ------------------------------------------------------------------
    # 1. Settings module
    # ------------------------------------------------------------------

    def _check_settings_module(self):
        module = settings.SETTINGS_MODULE
        self.stdout.write(f"  Settings module: {module}")
        if "production" in module:
            self.stdout.write(self.style.WARNING(
                "  [WARN] Production settings active — is this intentional locally?"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f"  [PASS] Settings module: {module}"))

    # ------------------------------------------------------------------
    # 2. Database backends
    # ------------------------------------------------------------------

    def _check_database_backends(self):
        for alias, config in settings.DATABASES.items():
            engine = config.get("ENGINE", "unknown")
            self.stdout.write(f"  Database '{alias}': {engine}")

            # Flag if PostgreSQL resolved but .env might intend SQLite
            if "postgresql" in engine:
                env_db_url = os.environ.get("DATABASE_URL", "")
                if "sqlite" in env_db_url.lower():
                    self.stdout.write(self.style.WARNING(
                        f"  [WARN] '{alias}' resolved to PostgreSQL but "
                        f"DATABASE_URL contains 'sqlite'"
                    ))

    # ------------------------------------------------------------------
    # 3. Database connectivity (critical)
    # ------------------------------------------------------------------

    def _check_database_connectivity(self):
        all_ok = True
        for alias in settings.DATABASES:
            try:
                connections[alias].ensure_connection()
                self.stdout.write(self.style.SUCCESS(
                    f"  [PASS] Database '{alias}' connection OK"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"  [FAIL] Database '{alias}' connection failed: {e}"
                ))
                all_ok = False
        return all_ok

    # ------------------------------------------------------------------
    # 4. Migrations current (warning only)
    # ------------------------------------------------------------------

    def _check_migrations(self):
        try:
            from django.db.migrations.executor import MigrationExecutor

            connection = connections["default"]
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

            if plan:
                self.stdout.write(self.style.WARNING(
                    f"  [WARN] {len(plan)} unapplied migration(s) pending"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    "  [PASS] All migrations applied"
                ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"  [WARN] Could not check migrations: {e}"
            ))

    # ------------------------------------------------------------------
    # 5. Test data exists (warning only)
    # ------------------------------------------------------------------

    def _check_test_data(self):
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            if User.objects.filter(username="demo-worker-1").exists():
                self.stdout.write(self.style.SUCCESS(
                    "  [PASS] Demo user 'demo-worker-1' found"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    "  [WARN] Demo user 'demo-worker-1' not found — "
                    "run: python manage.py seed && python manage.py seed_demo_data"
                ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"  [WARN] Could not check test data: {e}"
            ))

    # ------------------------------------------------------------------
    # 6. Holdout repo
    # ------------------------------------------------------------------

    def _check_holdout_repo(self):
        default_path = str(settings.BASE_DIR.parent / "konote-qa-scenarios")
        holdout_dir = os.environ.get("SCENARIO_HOLDOUT_DIR", default_path)

        if os.path.isdir(holdout_dir):
            self.stdout.write(self.style.SUCCESS(
                f"  [PASS] Holdout repo found: {holdout_dir}"
            ))
            return True
        else:
            self.stdout.write(self.style.ERROR(
                f"  [FAIL] Holdout repo not found: {holdout_dir}"
            ))
            return False
