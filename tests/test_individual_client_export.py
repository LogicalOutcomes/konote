"""Tests for individual client data export via SecureExportLink (QA-R7-PRIVACY1).

Covers:
- JSON format generates valid JSON with correct structure
- SecureExportLink is created with correct expiry and metadata
- Permission check — only users with report.data_extract can access
- Audit log entry is created with secure_link delivery
- Idempotency nonce prevents duplicate exports
"""
import json
import os
import shutil
import tempfile
import uuid
from datetime import timedelta

from cryptography.fernet import Fernet
from django.test import Client as HttpClient, TestCase, override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole
from apps.reports.models import SecureExportLink
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class IndividualClientExportTestBase(TestCase):
    """Base class with shared setup for individual client export tests."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")

        # Program
        self.program = Program.objects.create(name="Housing First")

        # Program manager — has report.data_extract permission
        self.pm_user = User.objects.create_user(
            username="pm_user", password="testpass123", display_name="PM User"
        )
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program, role="program_manager"
        )

        # Staff user — does NOT have report.data_extract permission
        self.staff_user = User.objects.create_user(
            username="staff_user", password="testpass123", display_name="Staff User"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program, role="staff"
        )

        # Client
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program
        )

        self.http_client = HttpClient()
        self.export_url = f"/reports/participant/{self.client_file.pk}/export/"

    def tearDown(self):
        enc_module._fernet = None
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def _post_export(self, user, fmt="json", with_nonce=True, **extra_data):
        """Helper to POST the export form as a given user."""
        self.http_client.force_login(user)

        # Get form page first to obtain nonce
        if with_nonce:
            response = self.http_client.get(self.export_url)
            nonce = response.context.get("export_nonce", "")
        else:
            nonce = ""

        data = {
            "format": fmt,
            "include_plans": "1",
            "include_notes": "1",
            "include_metrics": "1",
            "include_events": "1",
            "include_custom_fields": "1",
            "recipient": "self",
            "recipient_reason": "PIPEDA data portability request",
        }
        if with_nonce:
            data["_export_nonce"] = nonce
        data.update(extra_data)

        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            return self.http_client.post(self.export_url, data)


class JSONFormatTest(IndividualClientExportTestBase):
    """JSON format generates valid JSON with correct structure."""

    def test_json_export_creates_valid_json(self):
        """Exported JSON file should be valid and contain expected keys."""
        response = self._post_export(self.pm_user, fmt="json")
        self.assertEqual(response.status_code, 200)

        # A SecureExportLink should have been created
        link = SecureExportLink.objects.first()
        self.assertIsNotNone(link)
        self.assertTrue(link.filename.endswith(".json"))

        # Read the saved file and parse as JSON
        with open(link.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("export_metadata", data)
        self.assertIn("client", data)
        self.assertEqual(data["export_metadata"]["format_version"], "1.0")
        self.assertEqual(data["client"]["first_name"], "Jane")
        self.assertEqual(data["client"]["last_name"], "Doe")

    def test_json_export_includes_programs_array(self):
        """JSON export should contain programs with nested structure."""
        response = self._post_export(self.pm_user, fmt="json")
        link = SecureExportLink.objects.first()

        with open(link.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("programs", data["client"])
        self.assertIsInstance(data["client"]["programs"], list)
        # Should have at least one program (Housing First)
        self.assertGreaterEqual(len(data["client"]["programs"]), 1)
        program = data["client"]["programs"][0]
        self.assertEqual(program["name"], "Housing First")

    def test_json_export_includes_events_and_custom_fields(self):
        """JSON export should include events and custom_fields arrays."""
        response = self._post_export(self.pm_user, fmt="json")
        link = SecureExportLink.objects.first()

        with open(link.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("events", data["client"])
        self.assertIn("custom_fields", data["client"])
        self.assertIsInstance(data["client"]["events"], list)
        self.assertIsInstance(data["client"]["custom_fields"], list)

    def test_json_export_metadata_has_exported_by(self):
        """export_metadata should include the exporter's display name."""
        response = self._post_export(self.pm_user, fmt="json")
        link = SecureExportLink.objects.first()

        with open(link.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["export_metadata"]["exported_by"], "PM User")


class SecureExportLinkCreationTest(IndividualClientExportTestBase):
    """SecureExportLink is created with correct expiry and metadata."""

    def test_link_created_with_correct_export_type(self):
        """Export should create a SecureExportLink with type 'individual_client'."""
        self._post_export(self.pm_user, fmt="csv")
        link = SecureExportLink.objects.first()

        self.assertIsNotNone(link)
        self.assertEqual(link.export_type, "individual_client")

    def test_link_expires_in_future(self):
        """Link should expire approximately 24 hours from now."""
        before = timezone.now()
        self._post_export(self.pm_user, fmt="json")
        after = timezone.now()

        link = SecureExportLink.objects.first()
        # Expiry should be ~24 hours from creation
        expected_min = before + timedelta(hours=23, minutes=59)
        expected_max = after + timedelta(hours=24, minutes=1)
        self.assertGreaterEqual(link.expires_at, expected_min)
        self.assertLessEqual(link.expires_at, expected_max)

    def test_link_has_correct_metadata(self):
        """Link should have client_count=1, contains_pii=True, and correct recipient."""
        self._post_export(self.pm_user, fmt="json")
        link = SecureExportLink.objects.first()

        self.assertEqual(link.client_count, 1)
        self.assertTrue(link.contains_pii)
        self.assertTrue(link.includes_notes)
        self.assertIn("self", link.recipient.lower())

    def test_link_file_exists_on_disk(self):
        """The exported file should exist at the path stored in the link."""
        self._post_export(self.pm_user, fmt="json")
        link = SecureExportLink.objects.first()

        self.assertTrue(os.path.exists(link.file_path))

    def test_csv_format_also_creates_link(self):
        """CSV exports should also go through SecureExportLink now."""
        self._post_export(self.pm_user, fmt="csv")
        link = SecureExportLink.objects.first()

        self.assertIsNotNone(link)
        self.assertTrue(link.filename.endswith(".csv"))

    def test_confirmation_page_rendered(self):
        """After export, user should see the confirmation page with download link."""
        response = self._post_export(self.pm_user, fmt="json")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/client_export_ready.html")
        self.assertContains(response, "Export Ready")


class PermissionTest(IndividualClientExportTestBase):
    """Only users with report.data_extract can access the export view."""

    def test_staff_cannot_access_export(self):
        """Staff users should be denied — report.data_extract is DENY for staff."""
        self.http_client.force_login(self.staff_user)
        response = self.http_client.get(self.export_url)
        self.assertEqual(response.status_code, 403)

    def test_pm_can_access_export_form(self):
        """Program managers should see the export form."""
        self.http_client.force_login(self.pm_user)
        response = self.http_client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        """Anonymous users should be redirected to login."""
        response = self.http_client.get(self.export_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)


class AuditLogTest(IndividualClientExportTestBase):
    """Audit log entry is created with secure_link delivery metadata."""

    def test_audit_log_created_on_export(self):
        """Exporting should create an audit log entry in the audit database."""
        self._post_export(self.pm_user, fmt="json")

        logs = AuditLog.objects.using("audit").filter(
            action="export",
            resource_type="individual_client_export",
            resource_id=self.client_file.pk,
        )
        self.assertEqual(logs.count(), 1)

    def test_audit_log_contains_delivery_secure_link(self):
        """Audit metadata should include delivery=secure_link and link_id."""
        self._post_export(self.pm_user, fmt="json")

        log = AuditLog.objects.using("audit").filter(
            action="export",
            resource_type="individual_client_export",
        ).first()
        self.assertIsNotNone(log)
        metadata = log.metadata
        self.assertEqual(metadata.get("delivery"), "secure_link")
        self.assertIn("link_id", metadata)

    def test_audit_log_records_format(self):
        """Audit metadata should include the export format."""
        self._post_export(self.pm_user, fmt="json")

        log = AuditLog.objects.using("audit").filter(
            action="export",
            resource_type="individual_client_export",
        ).first()
        self.assertEqual(log.metadata.get("format"), "json")


class IdempotencyNonceTest(IndividualClientExportTestBase):
    """Idempotency nonce prevents duplicate exports."""

    def test_duplicate_nonce_shows_warning(self):
        """Submitting the same nonce twice should show duplicate warning."""
        self.http_client.force_login(self.pm_user)

        # Get the form to get a nonce
        response = self.http_client.get(self.export_url)
        nonce = response.context.get("export_nonce", "")

        data = {
            "format": "json",
            "include_plans": "1",
            "include_notes": "1",
            "include_metrics": "1",
            "include_events": "1",
            "include_custom_fields": "1",
            "recipient": "self",
            "recipient_reason": "Test",
            "_export_nonce": nonce,
        }

        # First submission — should succeed
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            response1 = self.http_client.post(self.export_url, data)
        self.assertEqual(response1.status_code, 200)
        self.assertTemplateUsed(response1, "reports/client_export_ready.html")

        # Second submission with same nonce — should show duplicate warning
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            response2 = self.http_client.post(self.export_url, data)
        self.assertEqual(response2.status_code, 200)
        self.assertTemplateUsed(response2, "reports/client_export_form.html")
        self.assertTrue(response2.context.get("duplicate_warning", False))

    def test_no_nonce_field_skips_check(self):
        """When _export_nonce field is absent, idempotency check is skipped."""
        self.http_client.force_login(self.pm_user)

        data = {
            "format": "json",
            "include_plans": "1",
            "include_notes": "1",
            "include_metrics": "1",
            "include_events": "1",
            "include_custom_fields": "1",
            "recipient": "self",
            "recipient_reason": "Test",
            # Deliberately omit _export_nonce
        }

        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            response = self.http_client.post(self.export_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/client_export_ready.html")
