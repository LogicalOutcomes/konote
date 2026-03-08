"""
Management command to verify database consistency after a backup/restore.

Checks table counts, encryption health, audit DB connectivity,
migration state, and foreign-key integrity across both databases.

Usage:
    python manage.py verify_backup_restore
    python manage.py verify_backup_restore --database default
    python manage.py verify_backup_restore --sample-size 25
    python manage.py verify_backup_restore --pre-restore /path/to/backup.sql
    python manage.py verify_backup_restore --full
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connections

from apps.clients.models import ClientFile
from apps.plans.models import PlanSection, PlanTarget
from apps.notes.models import ProgressNote
from apps.audit.models import AuditLog
from apps.programs.models import Program

import io
import os
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
        parser.add_argument(
            "--pre-restore",
            metavar="DUMP_FILE",
            help="Validate a backup dump file before restoring. "
                 "Checks that the file exists, is non-empty, and looks like a pg_dump output.",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Test ALL encrypted records instead of just a sample.",
        )

    def handle(self, *args, **options):
        # Handle --pre-restore mode: validate the dump file and exit.
        if options["pre_restore"]:
            ok = self._validate_dump_file(options["pre_restore"])
            if not ok:
                raise CommandError("Pre-restore validation failed. Do not proceed with restore.")
            return

        db_choice = options["database"]
        sample_size = options["sample_size"]
        full_check = options["full"]
        results = {}

        check_default = db_choice in ("default", "both")
        check_audit = db_choice in ("audit", "both")

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Backup/Restore Verification ===\n"))

        # ── 1. Table counts ────────────────────────────────────────
        if check_default:
            results["table_counts"] = self._check_table_counts()

        # ── 2a. Encryption key round-trip ────────────────────────────
        if check_default:
            results["encryption_key"] = self._check_encryption_roundtrip()

        # ── 2b. Encryption health ───────────────────────────────────
        if check_default:
            results["encryption"] = self._check_encryption(sample_size, full_check)

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

    def _check_encryption_roundtrip(self):
        """Verify FIELD_ENCRYPTION_KEY can round-trip encrypt and decrypt."""
        self.stdout.write(self.style.MIGRATE_HEADING("2a. Encryption Key Round-Trip"))
        try:
            from apps.clients.encryption import encrypt_field, decrypt_field
            test_value = "verify-backup-restore-test"
            encrypted = encrypt_field(test_value)
            decrypted = decrypt_field(encrypted)
            if decrypted == test_value:
                self.stdout.write(self.style.SUCCESS("   FIELD_ENCRYPTION_KEY round-trip OK."))
                self.stdout.write("")
                return True
            else:
                self.stdout.write(self.style.ERROR(
                    f"   FAIL: Round-trip mismatch. Expected '{test_value}', got '{decrypted}'."
                ))
                self.stdout.write("")
                return False
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"   FAIL: Encryption round-trip error: {exc}"))
            self.stdout.write("")
            return False

    def _check_encryption(self, sample_size, full_check=False):
        self.stdout.write(self.style.MIGRATE_HEADING("2. Encryption Health"))
        all_passed = True

        # Check ClientFile (first_name, last_name)
        all_passed = self._check_encrypted_model(
            model=ClientFile,
            model_label="ClientFile",
            fields=["first_name", "last_name"],
            error_sentinel="[DECRYPTION ERROR]",
            sample_size=sample_size,
            full_check=full_check,
        ) and all_passed

        # Check ProgressNote (notes_text, summary)
        all_passed = self._check_encrypted_model(
            model=ProgressNote,
            model_label="ProgressNote",
            fields=["notes_text", "summary"],
            error_sentinel="[DECRYPTION ERROR]",
            sample_size=sample_size,
            full_check=full_check,
            # Only check notes that actually have encrypted content
            filter_kwargs={"_notes_text_encrypted__gt": b""},
        ) and all_passed

        self.stdout.write("")
        return all_passed

    def _check_encrypted_model(self, model, model_label, fields, error_sentinel,
                               sample_size, full_check=False, filter_kwargs=None):
        """Check decryption health for a single model's encrypted fields."""
        qs = model.objects.using("default")
        if filter_kwargs:
            qs = qs.filter(**filter_kwargs)
        total = qs.count()

        if total == 0:
            self.stdout.write(f"   {model_label}: no records — skipped.")
            return True

        if full_check:
            records = qs.order_by("pk").iterator()
            limit_label = f"all {total:,}"
        else:
            records = list(qs.order_by("pk")[:sample_size])
            limit_label = f"sample of {min(sample_size, total)}/{total:,}"

        passed = 0
        failed = 0
        for record in records:
            try:
                has_error = False
                for field in fields:
                    val = getattr(record, field)
                    if val == error_sentinel:
                        has_error = True
                        break
                if has_error:
                    failed += 1
                else:
                    passed += 1
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"   {model_label} #{record.pk}: {exc}"))

        tested = passed + failed
        self.stdout.write(f"   {model_label}: tested {tested} ({limit_label}). OK: {passed}  Failed: {failed}")

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

    # ── Pre-restore validation ──────────────────────────────────────

    def _validate_dump_file(self, dump_path):
        """Validate a pg_dump file before restoring."""
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Pre-Restore Validation ===\n"))
        ok = True

        # Check file exists
        if not os.path.exists(dump_path):
            self.stdout.write(self.style.ERROR(f"   FAIL: File not found: {dump_path}"))
            return False
        self.stdout.write(self.style.SUCCESS(f"   File exists: {dump_path}"))

        # Check file size > 0
        file_size = os.path.getsize(dump_path)
        if file_size == 0:
            self.stdout.write(self.style.ERROR("   FAIL: File is empty (0 bytes)."))
            return False
        size_mb = file_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f"   File size: {size_mb:.1f} MB ({file_size:,} bytes)"))

        # Check first line contains pg_dump signature
        try:
            with open(dump_path, "r", errors="replace") as f:
                first_line = f.readline(1024)
            if "PostgreSQL" in first_line or "pg_dump" in first_line:
                self.stdout.write(self.style.SUCCESS(
                    "   Text-format pg_dump detected (header contains PostgreSQL/pg_dump signature)."
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    "   FAIL: First line does not contain 'PostgreSQL' or 'pg_dump'. "
                    "This may not be a valid text-format database dump. "
                    "Note: binary/custom-format dumps are not supported by this check — "
                    "use 'pg_restore --list <file>' to validate those."
                ))
                self.stdout.write(f"   First line: {first_line.strip()[:120]}")
                ok = False
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"   FAIL: Could not read file: {exc}"))
            ok = False

        self.stdout.write("")
        if ok:
            self.stdout.write(self.style.SUCCESS("Pre-restore validation passed. Safe to proceed with restore."))
        return ok

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
