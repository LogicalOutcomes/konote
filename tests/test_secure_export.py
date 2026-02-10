"""Tests for Phase 3 Secure Export Links — model, download, revoke, manage, and cleanup."""
import os
import shutil
import tempfile
import uuid
from datetime import timedelta
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.audit.models import AuditLog
from apps.auth_app.models import User
from apps.reports.models import SecureExportLink
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# ─── Helper ──────────────────────────────────────────────────────────


def _create_link(user, export_dir, **overrides):
    """
    Create a SecureExportLink with a real file on disk.

    Returns the link and the file path. Caller is responsible for cleanup
    (handled by tearDown in each test class).
    """
    link_id = overrides.pop("id", uuid.uuid4())
    filename = overrides.pop("filename", "test_export.csv")
    content = overrides.pop("content", "record_id,metric,value\nTEST-001,Score,5")
    expires_at = overrides.pop("expires_at", timezone.now() + timedelta(hours=24))
    export_type = overrides.pop("export_type", "metrics")
    client_count = overrides.pop("client_count", 1)
    recipient = overrides.pop("recipient", "Self — for my own records")

    safe_filename = f"{link_id}_{filename}"
    file_path = os.path.join(export_dir, safe_filename)

    os.makedirs(export_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    link = SecureExportLink.objects.create(
        id=link_id,
        created_by=user,
        expires_at=expires_at,
        export_type=export_type,
        client_count=client_count,
        includes_notes=overrides.pop("includes_notes", False),
        contains_pii=overrides.pop("contains_pii", True),
        recipient=recipient,
        filename=filename,
        file_path=file_path,
        revoked=overrides.pop("revoked", False),
        revoked_by=overrides.pop("revoked_by", None),
        revoked_at=overrides.pop("revoked_at", None),
        filters_json=overrides.pop("filters_json", "{}"),
    )
    return link


# ═════════════════════════════════════════════════════════════════════
# 1. Model tests — SecureExportLink
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SecureExportLinkModelTest(TestCase):
    """Test SecureExportLink model methods and properties."""

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    # ── is_valid() ────────────────────────────────────────────────

    def test_is_valid_returns_false_for_revoked_link(self):
        """A revoked link should not be valid, even if it hasn't expired."""
        link = _create_link(
            self.admin,
            self.export_dir,
            revoked=True,
            revoked_by=self.admin,
            revoked_at=timezone.now(),
        )
        self.assertFalse(link.is_valid())

    def test_is_valid_returns_false_for_expired_link(self):
        """A link past its expiry time should not be valid."""
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(link.is_valid())

    def test_is_valid_returns_true_for_active_link(self):
        """An active, non-expired, non-revoked link should be valid."""
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() + timedelta(hours=12),
        )
        self.assertTrue(link.is_valid())

    # ── file_exists ───────────────────────────────────────────────

    def test_file_exists_returns_false_for_nonexistent_path(self):
        """file_exists should return False when the file has been deleted."""
        link = _create_link(self.admin, self.export_dir)
        # Remove the file manually
        os.remove(link.file_path)
        self.assertFalse(link.file_exists)

    def test_file_exists_returns_true_when_file_present(self):
        """file_exists should return True when the file is on disk."""
        link = _create_link(self.admin, self.export_dir)
        self.assertTrue(link.file_exists)

    # ── status_display ────────────────────────────────────────────

    def test_status_display_revoked(self):
        """status_display should return 'Revoked' for a revoked link."""
        link = _create_link(
            self.admin,
            self.export_dir,
            revoked=True,
            revoked_by=self.admin,
            revoked_at=timezone.now(),
        )
        self.assertEqual(link.status_display, "Revoked")

    def test_status_display_expired(self):
        """status_display should return 'Expired' for an expired link."""
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertEqual(link.status_display, "Expired")

    def test_status_display_file_missing(self):
        """status_display should return 'File Missing' when file is gone."""
        link = _create_link(self.admin, self.export_dir)
        os.remove(link.file_path)
        self.assertEqual(link.status_display, "File Missing")

    def test_status_display_active(self):
        """status_display should return 'Active' for a healthy link."""
        link = _create_link(self.admin, self.export_dir)
        self.assertEqual(link.status_display, "Active")

    def test_status_display_revoked_takes_priority_over_expired(self):
        """If a link is both revoked and expired, 'Revoked' wins."""
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(hours=1),
            revoked=True,
            revoked_by=self.admin,
            revoked_at=timezone.now(),
        )
        self.assertEqual(link.status_display, "Revoked")

    # ── __str__ ───────────────────────────────────────────────────

    def test_str_representation(self):
        """__str__ should include export type and status."""
        link = _create_link(self.admin, self.export_dir, export_type="cmt")
        result = str(link)
        self.assertIn("cmt", result)
        self.assertIn("Active", result)


# ═════════════════════════════════════════════════════════════════════
# 2. Download view tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DownloadExportViewTest(TestCase):
    """Test the download_export view for permission, validity, and audit."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def _make_url(self, link):
        return f"/reports/download/{link.id}/"

    # ── Permission ────────────────────────────────────────────────

    def test_non_admin_gets_403(self):
        """Non-admin users should get 403 before any validity check."""
        link = _create_link(self.admin, self.export_dir)
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_user_redirected_to_login(self):
        """Anonymous users should be redirected to the login page."""
        link = _create_link(self.admin, self.export_dir)
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    # ── Successful download ───────────────────────────────────────

    @override_settings()
    def test_admin_can_download_active_link(self):
        """Admin should be able to download a valid, active link."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        csv_content = "record_id,metric,value\nTEST-001,Housing,7"
        link = _create_link(
            self.admin,
            self.export_dir,
            content=csv_content,
            filename="housing_export.csv",
        )
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 200)
        # FileResponse streams the file — read the full content
        downloaded = b"".join(resp.streaming_content).decode("utf-8")
        # Windows may add \r\n line endings, so check the key data is present
        self.assertIn("record_id,metric,value", downloaded)
        self.assertIn("TEST-001,Housing,7", downloaded)
        # Check Content-Disposition header for the correct filename
        self.assertIn("housing_export.csv", resp["Content-Disposition"])

    # ── Expired link ──────────────────────────────────────────────

    @override_settings()
    def test_expired_link_shows_expired_page(self):
        """Downloading an expired link should show the expired reason page."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "expired")

    # ── Revoked link ──────────────────────────────────────────────

    @override_settings()
    def test_revoked_link_shows_revoked_page(self):
        """Downloading a revoked link should show the revoked reason page."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(
            self.admin,
            self.export_dir,
            revoked=True,
            revoked_by=self.admin,
            revoked_at=timezone.now(),
        )
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "revoked")

    # ── Missing file ──────────────────────────────────────────────

    @override_settings()
    def test_missing_file_shows_missing_page(self):
        """When the export file no longer exists, show the missing page."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir)
        # Remove the file from disk
        os.remove(link.file_path)
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "no longer available")

    # ── Path traversal defence ────────────────────────────────────

    @override_settings()
    def test_path_traversal_returns_403(self):
        """A link with a file_path outside SECURE_EXPORT_DIR should be blocked."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir)
        # Tamper with the file path to point outside the export directory.
        # Create a file outside the export dir so file_exists returns True.
        outside_dir = tempfile.mkdtemp(prefix="konote_outside_")
        outside_file = os.path.join(outside_dir, "stolen.csv")
        with open(outside_file, "w") as f:
            f.write("secret data")
        SecureExportLink.objects.filter(pk=link.pk).update(file_path=outside_file)

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 403)

        # Clean up the outside directory
        shutil.rmtree(outside_dir, ignore_errors=True)

    # ── Download tracking ─────────────────────────────────────────

    @override_settings()
    def test_download_increments_download_count(self):
        """Each download should increment the download_count field."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir)
        self.assertEqual(link.download_count, 0)

        self.http_client.login(username="admin", password="testpass123")
        self.http_client.get(self._make_url(link))

        link.refresh_from_db()
        self.assertEqual(link.download_count, 1)

        # Download again
        self.http_client.get(self._make_url(link))
        link.refresh_from_db()
        self.assertEqual(link.download_count, 2)

    @override_settings()
    def test_download_updates_last_downloaded_fields(self):
        """Download should set last_downloaded_at and last_downloaded_by."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir)
        self.assertIsNone(link.last_downloaded_at)
        self.assertIsNone(link.last_downloaded_by)

        self.http_client.login(username="admin", password="testpass123")
        self.http_client.get(self._make_url(link))

        link.refresh_from_db()
        self.assertIsNotNone(link.last_downloaded_at)
        self.assertEqual(link.last_downloaded_by, self.admin)

    # ── Audit log ─────────────────────────────────────────────────

    @override_settings()
    def test_download_creates_audit_log_entry(self):
        """Each download should create an audit log entry."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir)

        audit_count_before = AuditLog.objects.using("audit").filter(
            resource_type="export_download"
        ).count()

        self.http_client.login(username="admin", password="testpass123")
        self.http_client.get(self._make_url(link))

        audit_count_after = AuditLog.objects.using("audit").filter(
            resource_type="export_download"
        ).count()
        self.assertEqual(audit_count_after, audit_count_before + 1)

        # Verify audit entry content
        audit_entry = AuditLog.objects.using("audit").filter(
            resource_type="export_download"
        ).first()
        self.assertEqual(audit_entry.action, "export")
        self.assertEqual(audit_entry.user_id, self.admin.pk)
        self.assertEqual(audit_entry.metadata["link_id"], str(link.id))

    # ── 404 for non-existent link ─────────────────────────────────

    def test_nonexistent_link_returns_404(self):
        """Requesting a link UUID that doesn't exist should return 404."""
        self.http_client.login(username="admin", password="testpass123")
        fake_id = uuid.uuid4()
        resp = self.http_client.get(f"/reports/download/{fake_id}/")
        self.assertEqual(resp.status_code, 404)


# ═════════════════════════════════════════════════════════════════════
# 3. Revoke view tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RevokeExportLinkViewTest(TestCase):
    """Test the revoke_export_link view for permissions, PRG pattern, and cleanup."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.admin2 = User.objects.create_user(
            username="admin2", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def _make_url(self, link):
        return f"/reports/export-links/{link.id}/revoke/"

    # ── Permission ────────────────────────────────────────────────

    def test_non_admin_gets_403(self):
        """Non-admin users should get 403 when trying to revoke."""
        link = _create_link(self.admin, self.export_dir)
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.post(self._make_url(link))
        self.assertEqual(resp.status_code, 403)

    # ── Method restriction ────────────────────────────────────────

    def test_get_request_returns_405(self):
        """GET should return 405 Method Not Allowed, not 403."""
        self.http_client.login(username="admin", password="testpass123")
        link = _create_link(self.admin, self.export_dir)
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 405)

    # ── Successful revocation ─────────────────────────────────────

    def test_post_revokes_the_link(self):
        """POST should set revoked=True, revoked_by, and revoked_at."""
        link = _create_link(self.admin, self.export_dir)
        self.assertFalse(link.revoked)

        self.http_client.login(username="admin2", password="testpass123")
        self.http_client.post(self._make_url(link))

        link.refresh_from_db()
        self.assertTrue(link.revoked)
        self.assertEqual(link.revoked_by, self.admin2)
        self.assertIsNotNone(link.revoked_at)

    # ── Already-revoked link ──────────────────────────────────────

    def test_already_revoked_link_redirects_with_info_message(self):
        """Revoking an already-revoked link should redirect with an info message."""
        link = _create_link(
            self.admin,
            self.export_dir,
            revoked=True,
            revoked_by=self.admin,
            revoked_at=timezone.now(),
        )
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(self._make_url(link), follow=True)
        # Should have followed the redirect to the manage page
        self.assertEqual(resp.status_code, 200)
        # Check for the info message
        messages_list = list(resp.context["messages"])
        self.assertTrue(
            any("already revoked" in str(m) for m in messages_list),
            f"Expected 'already revoked' message, got: {messages_list}",
        )

    # ── File deletion on revoke ───────────────────────────────────

    def test_revoking_deletes_the_file_from_disk(self):
        """After revocation, the export file should be removed from disk."""
        link = _create_link(self.admin, self.export_dir)
        self.assertTrue(os.path.exists(link.file_path))

        self.http_client.login(username="admin", password="testpass123")
        self.http_client.post(self._make_url(link))

        self.assertFalse(os.path.exists(link.file_path))

    # ── Audit log ─────────────────────────────────────────────────

    def test_revocation_creates_audit_log_entry(self):
        """Revoking a link should create an audit log entry."""
        link = _create_link(self.admin, self.export_dir)

        audit_count_before = AuditLog.objects.using("audit").filter(
            resource_type="export_link_revoked"
        ).count()

        self.http_client.login(username="admin", password="testpass123")
        self.http_client.post(self._make_url(link))

        audit_count_after = AuditLog.objects.using("audit").filter(
            resource_type="export_link_revoked"
        ).count()
        self.assertEqual(audit_count_after, audit_count_before + 1)

        # Verify audit entry details
        audit_entry = AuditLog.objects.using("audit").filter(
            resource_type="export_link_revoked"
        ).first()
        self.assertEqual(audit_entry.action, "update")
        self.assertEqual(audit_entry.user_id, self.admin.pk)
        self.assertEqual(audit_entry.metadata["link_id"], str(link.id))
        self.assertEqual(audit_entry.metadata["export_type"], "metrics")

    # ── Post/Redirect/Get ─────────────────────────────────────────

    def test_revoke_returns_302_redirect(self):
        """Revocation should use Post/Redirect/Get (302 redirect)."""
        link = _create_link(self.admin, self.export_dir)
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(self._make_url(link))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("export-links", resp.url)

    # ── 404 for non-existent link ─────────────────────────────────

    def test_nonexistent_link_returns_404(self):
        """Revoking a link UUID that doesn't exist should return 404."""
        self.http_client.login(username="admin", password="testpass123")
        fake_id = uuid.uuid4()
        resp = self.http_client.post(f"/reports/export-links/{fake_id}/revoke/")
        self.assertEqual(resp.status_code, 404)


# ═════════════════════════════════════════════════════════════════════
# 4. Manage view tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ManageExportLinksViewTest(TestCase):
    """Test the manage_export_links admin view."""

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def test_non_admin_gets_403(self):
        """Non-admin users should get 403 on the manage page."""
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_sees_manage_page(self):
        """Admin users should be able to access the manage page."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_sees_recent_links(self):
        """The manage page should list links created within the last 7 days."""
        link = _create_link(self.admin, self.export_dir, filename="recent.csv")
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 200)
        # The link should appear in the response context
        self.assertIn(link, resp.context["links"])

    def test_unauthenticated_user_redirected(self):
        """Anonymous users should be redirected to login."""
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)


# ═════════════════════════════════════════════════════════════════════
# 5. Cleanup command tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CleanupExpiredExportsCommandTest(TestCase):
    """Test the cleanup_expired_exports management command."""

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings()
    def test_deletes_expired_links_db_record_and_file(self):
        """Command should delete DB records and files for links expired > 1 day ago."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        # Create a link that expired 2 days ago (past the 1-day grace period)
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(days=2),
            filename="expired_old.csv",
        )
        file_path = link.file_path
        link_id = link.id
        self.assertTrue(os.path.exists(file_path))

        out = StringIO()
        call_command("cleanup_expired_exports", stdout=out)

        # DB record should be gone
        self.assertFalse(
            SecureExportLink.objects.filter(id=link_id).exists()
        )
        # File should be gone
        self.assertFalse(os.path.exists(file_path))

    @override_settings()
    def test_keeps_non_expired_links(self):
        """Command should not touch links that haven't expired yet."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() + timedelta(hours=12),
            filename="still_active.csv",
        )
        file_path = link.file_path

        out = StringIO()
        call_command("cleanup_expired_exports", stdout=out)

        # DB record should still exist
        self.assertTrue(
            SecureExportLink.objects.filter(id=link.id).exists()
        )
        # File should still exist
        self.assertTrue(os.path.exists(file_path))

    @override_settings()
    def test_keeps_recently_expired_links_within_grace_period(self):
        """Links expired less than 1 day ago should be kept (grace period)."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        # Expired 12 hours ago — within the 1-day grace period
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(hours=12),
            filename="just_expired.csv",
        )

        out = StringIO()
        call_command("cleanup_expired_exports", stdout=out)

        # Should still exist because it's within the grace period
        self.assertTrue(
            SecureExportLink.objects.filter(id=link.id).exists()
        )
        self.assertTrue(os.path.exists(link.file_path))

    @override_settings()
    def test_cleans_up_orphan_files(self):
        """Files in the export dir with no matching DB record should be removed."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        os.makedirs(self.export_dir, exist_ok=True)

        # Create an orphan file (no matching SecureExportLink in the database)
        orphan_path = os.path.join(self.export_dir, "orphan_file.csv")
        with open(orphan_path, "w") as f:
            f.write("orphaned data")
        self.assertTrue(os.path.exists(orphan_path))

        out = StringIO()
        call_command("cleanup_expired_exports", stdout=out)

        # Orphan file should be deleted
        self.assertFalse(os.path.exists(orphan_path))

    @override_settings()
    def test_does_not_delete_files_with_active_db_records(self):
        """Orphan cleanup should not remove files that belong to active links."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() + timedelta(hours=12),
            filename="active_link.csv",
        )

        out = StringIO()
        call_command("cleanup_expired_exports", stdout=out)

        # File should still exist (it has a matching DB record)
        self.assertTrue(os.path.exists(link.file_path))

    @override_settings()
    def test_dry_run_does_not_delete_anything(self):
        """--dry-run should report what would be deleted but not actually delete."""
        settings.SECURE_EXPORT_DIR = self.export_dir

        # Expired link (past grace period)
        link = _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(days=2),
            filename="dry_run_expired.csv",
        )
        file_path = link.file_path
        link_id = link.id

        # Orphan file
        orphan_path = os.path.join(self.export_dir, "dry_run_orphan.csv")
        with open(orphan_path, "w") as f:
            f.write("orphan data")

        out = StringIO()
        call_command("cleanup_expired_exports", "--dry-run", stdout=out)

        # DB record should still exist
        self.assertTrue(
            SecureExportLink.objects.filter(id=link_id).exists()
        )
        # Both files should still exist
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(os.path.exists(orphan_path))

        # Output should mention dry run
        output_text = out.getvalue()
        self.assertIn("DRY RUN", output_text)

    @override_settings()
    def test_command_summary_output(self):
        """Command should print a summary of what was deleted."""
        settings.SECURE_EXPORT_DIR = self.export_dir

        # Create an expired link past grace period
        _create_link(
            self.admin,
            self.export_dir,
            expires_at=timezone.now() - timedelta(days=2),
            filename="summary_test.csv",
        )

        out = StringIO()
        call_command("cleanup_expired_exports", stdout=out)

        output_text = out.getvalue()
        # Should report that it deleted expired link(s)
        self.assertIn("1 expired link", output_text)


# ═════════════════════════════════════════════════════════════════════
# 6. Phase 4 — Elevated export model tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, ELEVATED_EXPORT_DELAY_MINUTES=10)
class ElevatedExportModelTest(TestCase):
    """Test is_available, available_at, and status_display for elevated exports."""

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    # ── is_available ───────────────────────────────────────────────

    def test_is_available_true_for_non_elevated(self):
        """Non-elevated exports should always be available immediately."""
        link = _create_link(self.admin, self.export_dir, includes_notes=False)
        self.assertFalse(link.is_elevated)
        self.assertTrue(link.is_available)

    def test_is_available_false_for_elevated_within_delay(self):
        """Elevated exports should not be available during the delay window."""
        link = _create_link(
            self.admin, self.export_dir,
            includes_notes=True,
        )
        # Mark as elevated manually (since _create_link doesn't auto-set it)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)
        link.refresh_from_db()
        self.assertTrue(link.is_elevated)
        # Just created — should be within the 10-minute delay
        self.assertFalse(link.is_available)

    def test_is_available_true_for_elevated_past_delay(self):
        """Elevated exports should be available after the delay period."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)
        link.refresh_from_db()
        # Backdate created_at to 15 minutes ago (past the 10-min delay)
        SecureExportLink.objects.filter(pk=link.pk).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )
        link.refresh_from_db()
        self.assertTrue(link.is_available)

    # ── available_at ───────────────────────────────────────────────

    def test_available_at_none_for_non_elevated(self):
        """Non-elevated exports should have no available_at time."""
        link = _create_link(self.admin, self.export_dir)
        self.assertIsNone(link.available_at)

    def test_available_at_set_for_elevated(self):
        """Elevated exports should have available_at = created_at + delay."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)
        link.refresh_from_db()
        expected = link.created_at + timedelta(minutes=10)
        self.assertEqual(link.available_at, expected)

    # ── status_display ─────────────────────────────────────────────

    def test_status_display_pending_for_elevated_in_delay(self):
        """Elevated exports in the delay window should show 'Pending'."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)
        link.refresh_from_db()
        self.assertEqual(link.status_display, "Pending")

    def test_status_display_active_for_elevated_past_delay(self):
        """Elevated exports past the delay should show 'Active'."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(
            is_elevated=True,
            created_at=timezone.now() - timedelta(minutes=15),
        )
        link.refresh_from_db()
        self.assertEqual(link.status_display, "Active")

    def test_status_display_revoked_overrides_pending(self):
        """Revoked takes priority over Pending for elevated exports."""
        link = _create_link(
            self.admin, self.export_dir,
            revoked=True, revoked_by=self.admin, revoked_at=timezone.now(),
        )
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)
        link.refresh_from_db()
        self.assertEqual(link.status_display, "Revoked")


# ═════════════════════════════════════════════════════════════════════
# 7. Phase 4 — Elevated export download delay tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, ELEVATED_EXPORT_DELAY_MINUTES=10)
class ElevatedExportDownloadTest(TestCase):
    """Test that elevated exports enforce the download delay."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def _make_url(self, link):
        return f"/reports/download/{link.id}/"

    @override_settings()
    def test_elevated_export_in_delay_shows_pending_page(self):
        """Trying to download an elevated export during delay shows pending page."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pending")

    @override_settings()
    def test_elevated_export_past_delay_serves_file(self):
        """Elevated exports past the delay should serve the file normally."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir, content="test,data\n1,2")
        SecureExportLink.objects.filter(pk=link.pk).update(
            is_elevated=True,
            created_at=timezone.now() - timedelta(minutes=15),
        )

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 200)
        # Should be a file download, not the pending page
        self.assertIn("attachment", resp.get("Content-Disposition", ""))

    @override_settings()
    def test_non_elevated_export_serves_immediately(self):
        """Non-elevated exports should serve immediately (no delay)."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir, content="test,data\n1,2")

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._make_url(link))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment", resp.get("Content-Disposition", ""))


# ═════════════════════════════════════════════════════════════════════
# 8. Phase 4 — Elevation flag logic tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, ELEVATED_EXPORT_DELAY_MINUTES=10)
class ElevationFlagLogicTest(TestCase):
    """Test that _save_export_and_create_link sets is_elevated correctly."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
            email="admin@example.com",
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_high_client_count_sets_elevated(self):
        """Exports with 100+ clients should be flagged as elevated."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        from apps.reports.views import _save_export_and_create_link
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/reports/export/")
        request.user = self.admin

        link = _save_export_and_create_link(
            request=request,
            content="test data",
            filename="big_export.csv",
            export_type="client_data",
            client_count=150,
            includes_notes=False,
            recipient="Self — for my own records",
        )
        self.assertTrue(link.is_elevated)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_includes_notes_sets_elevated(self):
        """Exports that include notes should be flagged as elevated."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        from apps.reports.views import _save_export_and_create_link
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/reports/export/")
        request.user = self.admin

        link = _save_export_and_create_link(
            request=request,
            content="test data",
            filename="notes_export.csv",
            export_type="metrics",
            client_count=5,
            includes_notes=True,
            recipient="Self — for my own records",
        )
        self.assertTrue(link.is_elevated)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_small_export_without_notes_not_elevated(self):
        """Exports with <100 clients and no notes should not be elevated."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        from apps.reports.views import _save_export_and_create_link
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/reports/export/")
        request.user = self.admin

        link = _save_export_and_create_link(
            request=request,
            content="test data",
            filename="small_export.csv",
            export_type="metrics",
            client_count=10,
            includes_notes=False,
            recipient="Self — for my own records",
        )
        self.assertFalse(link.is_elevated)


# ═════════════════════════════════════════════════════════════════════
# 9. Phase 4 — Email notification tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    ELEVATED_EXPORT_DELAY_MINUTES=10,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ElevatedExportEmailTest(TestCase):
    """Test that elevated exports send email notifications to admins."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
            email="admin@example.com",
        )
        self.admin2 = User.objects.create_user(
            username="admin2", password="testpass123", is_admin=True,
            email="admin2@example.com",
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings()
    def test_elevated_export_sends_email_to_admins(self):
        """Creating an elevated export should send email to all active admins."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        from django.core import mail
        from apps.reports.views import _save_export_and_create_link
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/reports/export/")
        request.user = self.admin

        _save_export_and_create_link(
            request=request,
            content="test data",
            filename="elevated_export.csv",
            export_type="client_data",
            client_count=200,
            includes_notes=False,
            recipient="Funder: United Way",
        )

        # Should have sent one email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Elevated Export Alert", email.subject)
        self.assertIn("200 clients", email.subject)
        # Should be sent to both admins
        self.assertIn("admin@example.com", email.to)
        self.assertIn("admin2@example.com", email.to)

    @override_settings()
    def test_non_elevated_export_does_not_send_email(self):
        """Non-elevated exports should not trigger any email notification."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        from django.core import mail
        from apps.reports.views import _save_export_and_create_link
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/reports/export/")
        request.user = self.admin

        _save_export_and_create_link(
            request=request,
            content="test data",
            filename="small_export.csv",
            export_type="metrics",
            client_count=5,
            includes_notes=False,
            recipient="Self — for my own records",
        )

        self.assertEqual(len(mail.outbox), 0)

    @override_settings()
    def test_elevated_export_sets_admin_notified_at(self):
        """The admin_notified_at timestamp should be set after notification."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        from apps.reports.views import _save_export_and_create_link
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/reports/export/")
        request.user = self.admin

        link = _save_export_and_create_link(
            request=request,
            content="test data",
            filename="elevated_export.csv",
            export_type="client_data",
            client_count=200,
            includes_notes=False,
            recipient="Self — for my own records",
        )
        link.refresh_from_db()
        self.assertIsNotNone(link.admin_notified_at)

    @override_settings()
    def test_email_body_contains_export_details(self):
        """The notification email should include relevant export details."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        from django.core import mail
        from apps.reports.views import _save_export_and_create_link
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/reports/export/")
        request.user = self.admin

        _save_export_and_create_link(
            request=request,
            content="test data",
            filename="notes_export.csv",
            export_type="metrics",
            client_count=50,
            includes_notes=True,
            recipient="Colleague: Jane Smith",
        )

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("50 clients", body)
        self.assertIn("clinical notes", body)
        self.assertIn("Colleague: Jane Smith", body)


# ═════════════════════════════════════════════════════════════════════
# 10. Phase 4 — Admin manage view with pending elevated
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, ELEVATED_EXPORT_DELAY_MINUTES=10)
class ManageElevatedExportLinksTest(TestCase):
    """Test that the manage view shows pending elevated exports."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def test_pending_elevated_in_context(self):
        """Pending elevated exports should appear in the pending_elevated context."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["pending_elevated"]), 1)

    def test_no_pending_elevated_when_past_delay(self):
        """Elevated exports past delay should not be in pending_elevated."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(
            is_elevated=True,
            created_at=timezone.now() - timedelta(minutes=15),
        )

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["pending_elevated"]), 0)

    def test_pending_elevated_shows_alert_banner(self):
        """When there are pending elevated exports, the alert banner should show."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertContains(resp, "pending review")

    def test_revoke_pending_elevated_export_works(self):
        """Admins should be able to revoke a pending elevated export."""
        link = _create_link(self.admin, self.export_dir)
        SecureExportLink.objects.filter(pk=link.pk).update(is_elevated=True)

        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            f"/reports/export-links/{link.id}/revoke/",
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

        link.refresh_from_db()
        self.assertTrue(link.revoked)
