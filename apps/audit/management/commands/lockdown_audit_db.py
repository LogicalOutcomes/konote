"""
Management command: lockdown_audit_db

Restricts the audit_writer database role to INSERT + SELECT only on the
audit_log table. This must run AFTER Django migrations so the table exists.

Safe to run multiple times (idempotent) — it revokes and re-grants each time.

Usage:
    python manage.py lockdown_audit_db
"""

from django.core.management.base import BaseCommand
from django.db import connections
from psycopg.sql import SQL, Identifier


class Command(BaseCommand):
    help = (
        "Lock down the audit database: revoke UPDATE/DELETE from audit_writer, "
        "grant only SELECT + INSERT on audit_log and USAGE on sequences."
    )

    def handle(self, *args, **options):
        connection = connections["audit"]
        db_user = connection.settings_dict["USER"]

        self.stdout.write(f"Locking down audit database for role '{db_user}'...")

        with connection.cursor() as cursor:
            # Check the audit_log table exists before attempting grants
            cursor.execute(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables"
                "  WHERE table_schema = 'public' AND table_name = 'audit_log'"
                ")"
            )
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                self.stdout.write(
                    self.style.WARNING(
                        "audit_log table does not exist yet — skipping lockdown. "
                        "Run migrations first, then re-run this command."
                    )
                )
                return

            # Revoke everything, then grant only what's needed.
            # This is idempotent: safe to run repeatedly.
            # Use psycopg.sql.Identifier for the role name to prevent SQL injection.
            role = Identifier(db_user)

            cursor.execute(SQL("REVOKE ALL ON audit_log FROM {};").format(role))
            self.stdout.write(f"  REVOKED all privileges on audit_log from {db_user}")

            cursor.execute(SQL("GRANT SELECT, INSERT ON audit_log TO {};").format(role))
            self.stdout.write(f"  GRANTED SELECT, INSERT on audit_log to {db_user}")

            # Sequences are needed for auto-increment primary keys
            cursor.execute(
                SQL("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {};").format(role)
            )
            self.stdout.write(f"  GRANTED USAGE on all sequences to {db_user}")

            # Also grant audit_reader SELECT access while we're here
            cursor.execute(
                "SELECT EXISTS (SELECT FROM pg_roles WHERE rolname = 'audit_reader')"
            )
            reader_exists = cursor.fetchone()[0]

            if reader_exists:
                cursor.execute("GRANT SELECT ON audit_log TO audit_reader;")
                self.stdout.write("  GRANTED SELECT on audit_log to audit_reader")

        self.stdout.write(
            self.style.SUCCESS(
                "Audit database locked down successfully. "
                "The audit_writer role can now only INSERT and SELECT."
            )
        )
