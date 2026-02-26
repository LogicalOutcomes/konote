"""
Management command to verify database consistency after a backup/restore.

Checks table counts, encryption health, audit DB connectivity,
migration state, and foreign-key integrity across both databases.

Usage:
    python manage.py verify_backup_restore
    python manage.py verify_backup_restore --database default
    python manage.py verify_backup_restore --sample-size 25
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connections

from apps.clients.models import ClientFile
from apps.plans.models import PlanSection, PlanTarget
from apps.notes.models import ProgressNote
from apps.audit.models import AuditLog
from apps.programs.models import Program

import io
import sys

User = get_user_model()


class Command(BaseCommand):
    help = "Verify database consistency after a backup/restore."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            choices=["default", "audit", "both"],
            default="both",
            help='Which database to verify: "default", "audit", or "both" (default: both).',
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=10,
            help="Number of encrypted client records to test (default: 10).",
        )

    def handle(self, *args, **options):
        db_choice = options["database"]
        sample_size = options["sample_size"]
        results = {}

        check_default = db_choice in ("default", "both")
        check_audit = db_choice in ("audit", "both")

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Backup/Restore Verification ===\n"))

        # ── 1. Table counts ────────────────────────────────────────
        if check_default:
            results["table_counts"] = self._check_table_counts()

        # ── 2. Encryption health ───────────────────────────────────
        if check_default:
            results["encryption"] = self._check_encryption(sample_size)

        # ── 3. Audit DB connectivity ───────────────────────────────
        if check_audit:
            results["audit_db"] = self._check_audit_db()

        # ── 4. Migrations ─────────────────────────────────────────
        results["migrations"] = self._check_migrations(check_default, check_audit)

        # ── 5. Foreign-key integrity ──────────────────────────────
        if check_default:
            results["fk_integrity"] = self._check_fk_integrity()

        # ── Summary ───────────────────────────────────────────────
        self._print_summary(results)

    # ── Check implementations ──────────────────────────────────────

    def _check_table_counts(self):
        self.stdout.write(self.style.MIGRATE_HEADING("1. Table Counts (default database)"))
        tables = [
            ("auth_user (Users)", User.objects.using("default").count()),
            ("client_files (Participants)", ClientFile.objects.using("default").count()),
            ("plan_targets (Plan Targets)", PlanTarget.objects.using("default").count()),
            ("progress_notes (Progress Notes)", ProgressNote.objects.using("default").count()),
            ("programs (Programs)", Program.objects.using("default").count()),
            ("plan_sections (Plan Sections)", PlanSection.objects.using("default").count()),
        ]
        for label, count in tables:
            self.stdout.write(f"   {label}: {count:,}")
        self.stdout.write("")
        return True

    def _check_encryption(self, sample_size):
        self.stdout.write(self.style.MIGRATE_HEADING("2. Encryption Health"))
        total = ClientFile.objects.using("default").count()
        if total == 0:
            self.stdout.write("   No client records found — skipping encryption check.")
            self.stdout.write("")
            return True

        sample = list(ClientFile.objects.using("default").order_by("pk")[:sample_size])
        passed = 0
        failed = 0
        for client in sample:
            try:
                # Access the property accessors — these decrypt under the hood
                _ = client.first_name
                _ = client.last_name
                if client.first_name == "[DECRYPTION ERROR]" or client.last_name == "[DECRYPTION ERROR]":
                    failed += 1
                else:
                    passed += 1
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"   Client #{client.pk}: {exc}"))

        tested = passed + failed
        self.stdout.write(f"   Tested {tested} of {total:,} client records.")
        self.stdout.write(f"   Decrypted OK: {passed}   Failed: {failed}")
        self.stdout.write("")

        return failed == 0

    def _check_audit_db(self):
        self.stdout.write(self.style.MIGRATE_HEADING("3. Audit Database Connectivity"))
        try:
            conn = connections["audit"]
            conn.ensure_connection()
            count = AuditLog.objects.using("audit").count()
            self.stdout.write(f"   audit_log rows: {count:,}")
            self.stdout.write("")
            return True
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"   Could not connect to audit database: {exc}"))
            self.stdout.write("")
            return False

    def _check_migrations(self, check_default, check_audit):
        self.stdout.write(self.style.MIGRATE_HEADING("4. Migration Status"))
        all_ok = True

        for db_alias in ["default", "audit"]:
            if db_alias == "default" and not check_default:
                continue
            if db_alias == "audit" and not check_audit:
                continue

            # Capture showmigrations --plan output and look for unapplied [ ]
            buf = io.StringIO()
            call_command("showmigrations", "--plan", database=db_alias, verbosity=0, stdout=buf)
            output = buf.getvalue()
            unapplied = [line.strip() for line in output.splitlines() if line.strip().startswith("[ ]")]

            if unapplied:
                all_ok = False
                self.stdout.write(self.style.WARNING(f"   {db_alias}: {len(unapplied)} unapplied migration(s)"))
                for m in unapplied[:5]:
                    self.stdout.write(f"      {m}")
                if len(unapplied) > 5:
                    self.stdout.write(f"      ... and {len(unapplied) - 5} more")
            else:
                self.stdout.write(self.style.SUCCESS(f"   {db_alias}: all migrations applied"))

        self.stdout.write("")
        return all_ok

    def _check_fk_integrity(self):
        self.stdout.write(self.style.MIGRATE_HEADING("5. Foreign-Key Integrity"))
        issues = []

        # ProgressNote → ClientFile
        orphan_notes = (
            ProgressNote.objects.using("default")
            .exclude(client_file__in=ClientFile.objects.using("default").values_list("pk", flat=True))
            .count()
        )
        if orphan_notes:
            issues.append(f"   {orphan_notes} ProgressNote(s) with missing ClientFile")

        # PlanTarget → PlanSection
        orphan_targets = (
            PlanTarget.objects.using("default")
            .exclude(plan_section__in=PlanSection.objects.using("default").values_list("pk", flat=True))
            .count()
        )
        if orphan_targets:
            issues.append(f"   {orphan_targets} PlanTarget(s) with missing PlanSection")

        # PlanTarget → ClientFile
        orphan_target_clients = (
            PlanTarget.objects.using("default")
            .exclude(client_file__in=ClientFile.objects.using("default").values_list("pk", flat=True))
            .count()
        )
        if orphan_target_clients:
            issues.append(f"   {orphan_target_clients} PlanTarget(s) with missing ClientFile")

        # PlanSection → ClientFile
        orphan_sections = (
            PlanSection.objects.using("default")
            .exclude(client_file__in=ClientFile.objects.using("default").values_list("pk", flat=True))
            .count()
        )
        if orphan_sections:
            issues.append(f"   {orphan_sections} PlanSection(s) with missing ClientFile")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS("   No orphaned foreign-key references found."))

        self.stdout.write("")
        return len(issues) == 0

    # ── Summary ────────────────────────────────────────────────────

    def _print_summary(self, results):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Summary ==="))
        all_pass = True
        for check_name, passed in results.items():
            label = check_name.replace("_", " ").title()
            if passed:
                self.stdout.write(self.style.SUCCESS(f"   PASS  {label}"))
            else:
                self.stdout.write(self.style.ERROR(f"   FAIL  {label}"))
                all_pass = False

        self.stdout.write("")
        if all_pass:
            self.stdout.write(self.style.SUCCESS("All checks passed. Backup restore is healthy."))
        else:
            self.stdout.write(self.style.ERROR("One or more checks FAILED. Review output above."))
