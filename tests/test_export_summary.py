"""Tests for the send_export_summary management command.

Covers:
- Dry run shows summary without sending email
- Sends summary email when exports exist
- Sends quiet-week email when no exports exist
- Custom --days flag changes the query window
- Graceful exit when no admin emails found
- Demo admins excluded from recipients
"""
import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.reports.models import SecureExportLink
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _create_export(user, **overrides):
    """Create a SecureExportLink record for testing (no file on disk needed)."""
    defaults = {
        "id": uuid.uuid4(),
        "created_by": user,
        "expires_at": timezone.now() + timedelta(hours=24),
        "export_type": "metrics",
        "client_count": 5,
        "includes_notes": False,
        "contains_pii": True,
        "recipient": "Self",
        "filename": "test.csv",
        "file_path": "/tmp/fake_export.csv",
        "filters_json": "{}",
    }
    defaults.update(overrides)
    return SecureExportLink.objects.create(**defaults)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class SendExportSummaryTests(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="summary_admin",
            password="testpass123",
            display_name="Admin User",
            is_admin=True,
        )
        self.admin.email = "admin@example.com"
        self.admin.save()

        self.staff = User.objects.create_user(
            username="summary_staff",
            password="testpass123",
            display_name="Staff User",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_dry_run_does_not_send(self):
        """--dry-run shows the summary but does not send email."""
        _create_export(self.staff)
        out = StringIO()
        call_command("send_export_summary", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("DRY RUN", output)
        self.assertIn("Total exports: 1", output)
        self.assertEqual(len(mail.outbox), 0)

    def test_sends_summary_with_exports(self):
        """Creates exports and verifies the email is sent with correct content."""
        _create_export(self.staff, export_type="client_data", client_count=10)
        _create_export(self.staff, export_type="metrics", client_count=3)
        _create_export(self.staff, export_type="metrics", is_elevated=True, client_count=150)
        out = StringIO()
        call_command("send_export_summary", stdout=out)
        output = out.getvalue()
        self.assertIn("Summary sent to 1 admin(s)", output)
        self.assertEqual(len(mail.outbox), 1)
        email_msg = mail.outbox[0]
        self.assertIn("Export Activity Summary", email_msg.subject)
        self.assertIn("admin@example.com", email_msg.to)

    def test_no_exports_sends_quiet_week(self):
        """When no exports exist, still sends email confirming system is running."""
        out = StringIO()
        call_command("send_export_summary", stdout=out)
        output = out.getvalue()
        self.assertIn("Total exports: 0", output)
        self.assertIn("Summary sent to 1 admin(s)", output)
        self.assertEqual(len(mail.outbox), 1)
        # The email body should mention no exports
        self.assertIn("No exports", mail.outbox[0].body)

    def test_custom_days_flag(self):
        """--days 14 includes exports from the last 14 days."""
        # Export from 10 days ago (outside 7-day default, inside 14-day window)
        old_export = _create_export(self.staff)
        SecureExportLink.objects.filter(pk=old_export.pk).update(
            created_at=timezone.now() - timedelta(days=10),
        )
        out7 = StringIO()
        call_command("send_export_summary", "--dry-run", stdout=out7)
        self.assertIn("Total exports: 0", out7.getvalue())

        out14 = StringIO()
        call_command("send_export_summary", "--dry-run", "--days", "14", stdout=out14)
        self.assertIn("Total exports: 1", out14.getvalue())

    def test_no_admins_skips_gracefully(self):
        """When no admin emails exist, the command exits without crashing."""
        self.admin.is_active = False
        self.admin.save()
        _create_export(self.staff)
        out = StringIO()
        call_command("send_export_summary", stdout=out)
        output = out.getvalue()
        self.assertIn("No admin email addresses found", output)
        self.assertEqual(len(mail.outbox), 0)

    def test_excludes_demo_admins(self):
        """Demo admin users do not receive the summary email."""
        self.admin.is_demo = True
        self.admin.save()
        # Create a real (non-demo) admin
        real_admin = User.objects.create_user(
            username="real_admin",
            password="testpass123",
            display_name="Real Admin",
            is_admin=True,
        )
        real_admin.email = "real@example.com"
        real_admin.save()

        _create_export(self.staff)
        out = StringIO()
        call_command("send_export_summary", stdout=out)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("real@example.com", mail.outbox[0].to)
        self.assertNotIn("admin@example.com", mail.outbox[0].to)

    def test_aggregations_correct(self):
        """Verifies type breakdown and elevated/downloaded/revoked counts."""
        _create_export(self.staff, export_type="client_data")
        _create_export(self.staff, export_type="client_data", is_elevated=True)
        _create_export(self.staff, export_type="metrics", download_count=3)
        _create_export(self.staff, export_type="funder_report", revoked=True)
        out = StringIO()
        call_command("send_export_summary", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("Elevated: 1", output)
        self.assertIn("Downloaded: 1", output)
        self.assertIn("Revoked: 1", output)
        self.assertIn("Total exports: 4", output)

    def test_top_exporters_listed(self):
        """Top exporters section shows staff who created exports."""
        _create_export(self.staff)
        _create_export(self.staff)
        out = StringIO()
        call_command("send_export_summary", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("Staff User", output)
        self.assertIn("2", output)
