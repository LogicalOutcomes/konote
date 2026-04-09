"""Tests for Phase 3.5 Export Permission Alignment (PERM1-10).

Verifies that export access follows the role model:
- Admin: system config + aggregate exports + manage/revoke links + download oversight
- Program Manager: individual data exports (with elevated friction) scoped to programs
- Executive: aggregate-only exports scoped to their programs
- Staff/Front Desk: no export access (but staff can generate per-client PDFs)

Only program managers can access individual client data in report exports
(with friction: elevated delay + admin notification). Admins without PM
roles, executives, and all other roles receive aggregate summaries only.
"""
import os
import shutil
import tempfile
import uuid

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet
from datetime import timedelta

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.reports.models import SecureExportLink
from apps.reports.utils import can_create_export, can_download_pii_export, get_manageable_programs, is_aggregate_only_user
import konote.encryption as enc_module
from apps.auth_app.constants import (
    ROLE_EXECUTIVE,
    ROLE_PROGRAM_MANAGER,
    ROLE_RECEPTIONIST,
    ROLE_STAFF,
)

TEST_KEY = Fernet.generate_key().decode()


def _create_link(user, export_dir, **overrides):
    """Create a SecureExportLink with a real file on disk."""
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
        contains_pii=overrides.pop("contains_pii", False),
        recipient=recipient,
        filename=filename,
        file_path=file_path,
        revoked=overrides.pop("revoked", False),
        filters_json=overrides.pop("filters_json", "{}"),
    )
    return link


# ═════════════════════════════════════════════════════════════════════
# 1. can_create_export() helper tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CanCreateExportHelperTest(TestCase):
    """Test the can_create_export() permission helper."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )

        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        # PM manages program A only
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        # Staff in program A
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role=ROLE_STAFF
        )
        # Executive in program A
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )

    # ── Admin ────────────────────────────────────────────────────

    def test_admin_can_create_metrics_export(self):
        self.assertTrue(can_create_export(self.admin, "metrics"))

    def test_admin_can_create_funder_report(self):
        self.assertTrue(can_create_export(self.admin, "standard_report"))

    def test_admin_can_export_any_program(self):
        self.assertTrue(can_create_export(self.admin, "metrics", program=self.program_a))
        self.assertTrue(can_create_export(self.admin, "metrics", program=self.program_b))

    # ── Program Manager ──────────────────────────────────────────

    def test_pm_can_create_metrics_export(self):
        self.assertTrue(can_create_export(self.pm_user, "metrics"))

    def test_pm_can_create_funder_report(self):
        self.assertTrue(can_create_export(self.pm_user, "standard_report"))

    def test_pm_can_export_own_program(self):
        self.assertTrue(can_create_export(self.pm_user, "metrics", program=self.program_a))

    def test_pm_cannot_export_other_program(self):
        self.assertFalse(can_create_export(self.pm_user, "metrics", program=self.program_b))

    # ── Staff ────────────────────────────────────────────────────

    def test_staff_cannot_create_any_export(self):
        self.assertFalse(can_create_export(self.staff_user, "metrics"))
        self.assertFalse(can_create_export(self.staff_user, "standard_report"))

    # ── Executive ────────────────────────────────────────────────

    def test_executive_can_create_metrics_export(self):
        self.assertTrue(can_create_export(self.exec_user, "metrics"))

    def test_executive_can_create_funder_report(self):
        self.assertTrue(can_create_export(self.exec_user, "standard_report"))

    def test_executive_can_export_own_program(self):
        self.assertTrue(can_create_export(self.exec_user, "metrics", program=self.program_a))

    def test_executive_cannot_export_other_program(self):
        self.assertFalse(can_create_export(self.exec_user, "metrics", program=self.program_b))


# ═════════════════════════════════════════════════════════════════════
# 2. get_manageable_programs() helper tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GetManageableProgramsTest(TestCase):
    """Test the get_manageable_programs() scoping helper."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")
        self.archived = Program.objects.create(name="Archived", status="archived")

        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )

    def test_admin_sees_all_active_programs(self):
        programs = get_manageable_programs(self.admin)
        self.assertIn(self.program_a, programs)
        self.assertIn(self.program_b, programs)
        self.assertNotIn(self.archived, programs)

    def test_pm_sees_only_managed_programs(self):
        programs = get_manageable_programs(self.pm_user)
        self.assertIn(self.program_a, programs)
        self.assertNotIn(self.program_b, programs)
        self.assertNotIn(self.archived, programs)


# ═════════════════════════════════════════════════════════════════════
# 3. Metrics export view permission tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricsExportPermissionTest(TestCase):
    """Test export_form view permissions for different roles."""

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )
        self.receptionist = User.objects.create_user(
            username="frontdesk", password="testpass123", is_admin=False, display_name="FD"
        )

        self.program_a = Program.objects.create(name="Program A")

        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role=ROLE_STAFF
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program_a, role=ROLE_RECEPTIONIST
        )

    def test_admin_can_access_metrics_export(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)

    def test_pm_can_access_metrics_export(self):
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)

    def test_staff_gets_403_on_metrics_export(self):
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 403)

    def test_executive_can_access_metrics_export(self):
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)

    def test_receptionist_gets_403_on_metrics_export(self):
        self.http_client.login(username="frontdesk", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 403)


# ═════════════════════════════════════════════════════════════════════
# 4. Funder report view permission tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FunderReportPermissionTest(TestCase):
    """Test funder_report_form view permissions for different roles."""

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )

        self.program_a = Program.objects.create(name="Program A")

        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role=ROLE_STAFF
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )

    def test_admin_can_access_funder_report(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/funder-report/")
        self.assertEqual(resp.status_code, 200)

    def test_pm_can_access_funder_report(self):
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/reports/funder-report/")
        self.assertEqual(resp.status_code, 200)

    def test_staff_gets_403_on_funder_report(self):
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get("/reports/funder-report/")
        self.assertEqual(resp.status_code, 403)

    def test_executive_can_access_funder_report(self):
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.get("/reports/funder-report/")
        self.assertEqual(resp.status_code, 200)


# ═════════════════════════════════════════════════════════════════════
# 5. Download permission tests (PERM4)
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DownloadExportPermissionTest(TestCase):
    """Test download_export: creator can download own, admin any, others blocked."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.pm_user2 = User.objects.create_user(
            username="pm2", password="testpass123", is_admin=False, display_name="PM2"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )

        self.program_a = Program.objects.create(name="Program A")
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.pm_user2, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings()
    def test_creator_can_download_own_aggregate_export(self):
        """A PM who created an aggregate export should be able to download it."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.pm_user, self.export_dir, contains_pii=False)
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 200)

    @override_settings()
    def test_admin_can_download_any_export(self):
        """Admin should be able to download any export, even ones they didn't create."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.pm_user, self.export_dir, contains_pii=False)
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 200)

    @override_settings()
    def test_other_pm_cannot_download_someone_elses_export(self):
        """A PM should NOT be able to download another PM's export."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.pm_user, self.export_dir, contains_pii=False)
        self.http_client.login(username="pm2", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 403)

    @override_settings()
    def test_staff_cannot_download_export(self):
        """Staff users should not be able to download any export."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.admin, self.export_dir, contains_pii=False)
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 403)

    @override_settings()
    def test_pm_can_download_own_pii_export(self):
        """PM CAN download PII exports they created (PM is the data steward role)."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.pm_user, self.export_dir, contains_pii=True)
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 200)

    @override_settings()
    def test_executive_cannot_download_pii_export(self):
        """Executive cannot download PII exports (no PM role)."""
        exec_user = User.objects.create_user(
            username="exec_dl", password="testpass123", is_admin=False, display_name="Exec"
        )
        UserProgramRole.objects.create(
            user=exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(exec_user, self.export_dir, contains_pii=True)
        self.http_client.login(username="exec_dl", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 403)

    @override_settings()
    def test_admin_can_download_pii_export(self):
        """Admin can still download PII-containing exports."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.pm_user, self.export_dir, contains_pii=True)
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 200)

    @override_settings()
    def test_pm_can_download_aggregate_export(self):
        """PM can still download their own aggregate (non-PII) exports."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        link = _create_link(self.pm_user, self.export_dir, contains_pii=False)
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get(f"/reports/download/{link.id}/")
        self.assertEqual(resp.status_code, 200)


# ═════════════════════════════════════════════════════════════════════
# 7. Manage/revoke stays admin-only (PERM5)
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ManageRevokePermissionTest(TestCase):
    """Verify manage and revoke views remain admin-only (PERM5)."""

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )

        self.program_a = Program.objects.create(name="Program A")
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def test_pm_gets_403_on_manage_links(self):
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 403)

    def test_pm_gets_403_on_revoke_link(self):
        link = _create_link(self.pm_user, self.export_dir)
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.post(f"/reports/export-links/{link.id}/revoke/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_manage_links(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export-links/")
        self.assertEqual(resp.status_code, 200)


# ═════════════════════════════════════════════════════════════════════
# 8. Context processor tests — has_export_access
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExportAccessContextTest(TestCase):
    """Test that has_export_access is correctly set in template context."""

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )

        self.program_a = Program.objects.create(name="Program A")
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role=ROLE_STAFF
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )

    def _get_context(self, username):
        """Log in and hit the home page to get template context."""
        self.http_client.login(username=username, password="testpass123")
        resp = self.http_client.get("/", follow=True)
        return resp.context or {}

    def test_admin_has_export_access(self):
        ctx = self._get_context("admin")
        self.assertTrue(ctx.get("has_export_access"))

    def test_pm_has_export_access(self):
        ctx = self._get_context("pm")
        self.assertTrue(ctx.get("has_export_access"))

    def test_staff_does_not_have_export_access(self):
        ctx = self._get_context("staff")
        self.assertFalse(ctx.get("has_export_access"))

    def test_executive_has_export_access(self):
        ctx = self._get_context("exec")
        self.assertTrue(ctx.get("has_export_access"))


# ═════════════════════════════════════════════════════════════════════
# 9. is_aggregate_only_user() helper tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class IsAggregateOnlyUserTest(TestCase):
    """Test the is_aggregate_only_user() permission helper."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.dual_user = User.objects.create_user(
            username="dual", password="testpass123", is_admin=False, display_name="Dual"
        )

        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        # Dual user: executive in program A, PM in program B
        UserProgramRole.objects.create(
            user=self.dual_user, program=self.program_a, role=ROLE_EXECUTIVE
        )
        UserProgramRole.objects.create(
            user=self.dual_user, program=self.program_b, role=ROLE_PROGRAM_MANAGER
        )

    def test_admin_without_pm_role_is_aggregate_only(self):
        """Admin (system config role) gets aggregate data only."""
        self.assertTrue(is_aggregate_only_user(self.admin))

    def test_executive_is_aggregate_only(self):
        self.assertTrue(is_aggregate_only_user(self.exec_user))

    def test_pm_is_not_aggregate_only(self):
        """PMs get individual data in exports (with elevated friction)."""
        self.assertFalse(is_aggregate_only_user(self.pm_user))

    def test_dual_role_user_with_pm_is_not_aggregate_only(self):
        """User with PM role in any program gets individual data."""
        self.assertFalse(is_aggregate_only_user(self.dual_user))

    def test_admin_with_pm_role_is_not_aggregate_only(self):
        """Admin who also has PM role gets individual data via the PM role."""
        admin_pm = User.objects.create_user(
            username="admin_pm", password="testpass123", is_admin=True, display_name="AdminPM"
        )
        UserProgramRole.objects.create(
            user=admin_pm, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        self.assertFalse(is_aggregate_only_user(admin_pm))

    def test_can_download_pii_admin(self):
        """Admin can download PII exports for oversight."""
        self.assertTrue(can_download_pii_export(self.admin))

    def test_can_download_pii_pm(self):
        """PM can download PII exports they create."""
        self.assertTrue(can_download_pii_export(self.pm_user))

    def test_cannot_download_pii_executive(self):
        """Executive cannot download PII exports."""
        self.assertFalse(can_download_pii_export(self.exec_user))


# ═════════════════════════════════════════════════════════════════════
# 10. Executive aggregate export content tests
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExecutiveAggregateExportTest(TestCase):
    """Verify executive exports contain ONLY aggregate data — no client IDs or author names.

    This is the critical security test for the metric.view_individual=DENY fix.
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
        from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric

        # Users
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin User"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM User"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec User"
        )

        # Program
        self.program = Program.objects.create(name="Test Program")

        # Roles
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program, role=ROLE_EXECUTIVE
        )

        # Client
        self.client_file = ClientFile.objects.create(record_id="REC-TEST-001")
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.save()

        # Enrolment
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program
        )

        # Metric
        self.metric_def = MetricDefinition.objects.create(
            name="Test Engagement", is_enabled=True
        )

        # Plan chain
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Test Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file,
        )
        target.name = "Improve engagement"
        target.description = "Test target"
        target.save()
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric_def)

        # Progress note with metric value
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick", author=self.pm_user,
        )
        note_target = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target,
        )
        MetricValue.objects.create(
            progress_note_target=note_target, metric_def=self.metric_def, value="8",
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def _submit_export(self, username):
        """Submit the metric export form and return the CSV content."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        self.http_client.login(username=username, password="testpass123")
        resp = self.http_client.post("/reports/export/", {
            "program": self.program.pk,
            "date_from": "2020-01-01",
            "date_to": "2030-12-31",
            "metrics": [self.metric_def.pk],
            "format": "csv",
            "recipient": "Self — for my own records",
            "recipient_reason": "Testing export permissions",
        })
        return resp

    # ── Executive: aggregate only ────────────────────────────────

    def test_executive_csv_has_no_record_ids(self):
        """Executive export must NOT contain any client record ID."""
        resp = self._submit_export("exec")
        self.assertEqual(resp.status_code, 200)
        # Find the secure link and read the file content
        link = SecureExportLink.objects.order_by("-created_at").first()
        self.assertIsNotNone(link)
        with open(link.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # The client record_id format is like REC-XXXX or a numeric ID —
        # but more importantly, "Client Record ID" header should be absent
        self.assertNotIn("Client Record ID", content)
        self.assertNotIn(self.client_file.record_id, content)

    def test_executive_csv_has_aggregate_headers(self):
        """Executive export must contain aggregate column headers."""
        resp = self._submit_export("exec")
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.order_by("-created_at").first()
        with open(link.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Metric Name", content)
        self.assertIn("Participants Measured", content)
        self.assertIn("Average", content)
        self.assertIn("Min", content)
        self.assertIn("Max", content)

    def test_executive_csv_has_no_author_names(self):
        """Executive export must NOT contain any staff author names."""
        resp = self._submit_export("exec")
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.order_by("-created_at").first()
        with open(link.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("PM User", content)
        self.assertNotIn("Author", content)

    def test_executive_csv_has_aggregate_mode_header(self):
        """Executive export must indicate aggregate mode in the header."""
        resp = self._submit_export("exec")
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.order_by("-created_at").first()
        with open(link.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Aggregate Summary", content)

    # ── Admin: aggregate only (system config role) ──────────────

    def test_admin_gets_aggregate_only(self):
        """Admin (no PM role) gets aggregate data only — system config role, not data access."""
        resp = self._submit_export("admin")
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.order_by("-created_at").first()
        with open(link.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("Client Record ID", content)
        self.assertIn("Aggregate Summary", content)
        self.assertFalse(link.contains_pii)

    # ── PM: individual data (with friction) ───────────────────

    def test_pm_gets_individual_data(self):
        """PM export contains individual client data (with elevated friction)."""
        resp = self._submit_export("pm")
        self.assertEqual(resp.status_code, 200)
        link = SecureExportLink.objects.order_by("-created_at").first()
        with open(link.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Client Record ID", content)
        self.assertIn(self.client_file.record_id, content)
        self.assertTrue(link.contains_pii)
        self.assertTrue(link.is_elevated)

    # ── Form template context ────────────────────────────────────

    def test_executive_form_shows_aggregate_banner(self):
        """GET as executive should set is_aggregate_only in template context."""
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get("is_aggregate_only"))

    def test_admin_form_shows_aggregate_banner(self):
        """GET as admin (no PM role) should set is_aggregate_only."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get("is_aggregate_only"))

    def test_pm_form_does_not_show_aggregate_banner(self):
        """GET as PM should NOT set is_aggregate_only — PM gets individual data."""
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context.get("is_aggregate_only"))
        self.assertTrue(resp.context.get("is_pm_export"))


# ═════════════════════════════════════════════════════════════════════
# 11. Individual client export permission tests (SECURITY FIX)
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class IndividualClientExportPermissionTest(TestCase):
    """Verify individual client export is restricted by report.data_extract permission.

    Uses @requires_permission("report.data_extract") which is ALLOW for
    program_manager and DENY for all other roles. PMs handle PIPEDA
    data portability requests for clients in their programs.
    """

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        from apps.clients.models import ClientFile, ClientProgramEnrolment

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )
        self.receptionist = User.objects.create_user(
            username="frontdesk", password="testpass123", is_admin=False, display_name="FD"
        )

        self.program_a = Program.objects.create(name="Program A")

        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role=ROLE_STAFF
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program_a, role=ROLE_RECEPTIONIST
        )

        # Admin needs a program role to pass ProgramAccessMiddleware
        # (admins without program roles are blocked from client URLs)
        UserProgramRole.objects.create(
            user=self.admin, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )

        # Create a client for the export endpoint
        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program_a
        )

    def _export_url(self):
        return f"/reports/participant/{self.client_file.pk}/export/"

    def test_admin_can_access_individual_client_export(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(self._export_url())
        self.assertEqual(resp.status_code, 200)

    def test_staff_gets_403_on_individual_client_export(self):
        """Staff must NOT be able to export individual client data."""
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get(self._export_url())
        self.assertEqual(resp.status_code, 403)

    def test_pm_can_access_individual_client_export(self):
        """Program managers can export individual client data (PIPEDA data portability)."""
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get(self._export_url())
        self.assertEqual(resp.status_code, 200)

    def test_executive_redirected_from_individual_client_export(self):
        """Executives are redirected away from client URLs by ProgramAccessMiddleware."""
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.get(self._export_url())
        # ProgramAccessMiddleware redirects executives to dashboard (302)
        self.assertEqual(resp.status_code, 302)

    def test_receptionist_gets_403_on_individual_client_export(self):
        """Receptionists cannot export individual client data."""
        self.http_client.login(username="frontdesk", password="testpass123")
        resp = self.http_client.get(self._export_url())
        self.assertEqual(resp.status_code, 403)


# ═════════════════════════════════════════════════════════════════════
# 12. client_progress_pdf — admin-only (downloadable PII export)
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientProgressPdfPermissionTest(TestCase):
    """Verify client_progress_pdf uses metric.view_individual permission.

    Staff (PROGRAM) and PM (ALLOW) can generate PDFs for clients in their
    programs. Executive (DENY) and receptionist (DENY) cannot. Admin-only
    users without program roles are blocked by _get_client_or_403().
    """

    databases = ["default", "audit"]  # PDF export writes to the audit log

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        from apps.clients.models import ClientFile, ClientProgramEnrolment

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )

        self.program_a = Program.objects.create(name="Program A")

        UserProgramRole.objects.create(
            user=self.admin, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role=ROLE_STAFF
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )

        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program_a
        )

    def _pdf_url(self):
        return f"/reports/participant/{self.client_file.pk}/pdf/"

    def test_pm_can_download_client_pdf(self):
        """PM CAN download client progress PDF (metric.view_individual=ALLOW)."""
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get(self._pdf_url())
        # 200 if WeasyPrint available, 503 if missing (Windows)
        self.assertIn(resp.status_code, [200, 503])

    def test_staff_can_download_client_pdf(self):
        """Staff CAN download client progress PDF (metric.view_individual=PROGRAM)."""
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get(self._pdf_url())
        # 200 if WeasyPrint available, 503 if missing (Windows)
        self.assertIn(resp.status_code, [200, 503])

    def test_executive_cannot_download_client_pdf(self):
        """Executive must NOT be able to download client progress PDF."""
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.get(self._pdf_url())
        # Either 403 (requires_permission) or 302 (ProgramAccessMiddleware redirect)
        self.assertIn(resp.status_code, [302, 403])


# ═════════════════════════════════════════════════════════════════════
# 13. client_analysis — requires metric.view_individual permission
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientAnalysisPermissionTest(TestCase):
    """Verify client_analysis enforces metric.view_individual permission.

    Executives have metric.view_individual=DENY and must not access
    individual client metric charts.
    """

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        from apps.clients.models import ClientFile, ClientProgramEnrolment

        self.pm_user = User.objects.create_user(
            username="pm", password="testpass123", is_admin=False, display_name="PM"
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False, display_name="Staff"
        )
        self.exec_user = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False, display_name="Exec"
        )
        self.receptionist = User.objects.create_user(
            username="frontdesk", password="testpass123", is_admin=False, display_name="FD"
        )

        self.program_a = Program.objects.create(name="Program A")

        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role=ROLE_PROGRAM_MANAGER
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role=ROLE_STAFF
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role=ROLE_EXECUTIVE
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program_a, role=ROLE_RECEPTIONIST
        )

        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program_a
        )

    def _analysis_url(self):
        return f"/reports/participant/{self.client_file.pk}/analysis/"

    def test_executive_cannot_view_client_analysis(self):
        """Executive must NOT see individual client metrics (metric.view_individual=DENY)."""
        self.http_client.login(username="exec", password="testpass123")
        resp = self.http_client.get(self._analysis_url())
        # Either 403 (requires_permission) or 302 (ProgramAccessMiddleware)
        self.assertIn(resp.status_code, [302, 403])

    def test_receptionist_cannot_view_client_analysis(self):
        """Receptionist must NOT see individual client metrics (metric.view_individual=DENY)."""
        self.http_client.login(username="frontdesk", password="testpass123")
        resp = self.http_client.get(self._analysis_url())
        self.assertEqual(resp.status_code, 403)


# ═════════════════════════════════════════════════════════════════════
# 14. HTML report rendering regression test
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class HtmlReportRenderingTest(TestCase):
    """Regression test: HTML format must use html_outcome_report.html, not the PDF template.

    Previously, requesting HTML format returned the WeasyPrint PDF template
    (pdf_funder_report.html) which rendered as unstyled HTML with @page CSS.
    This test ensures the correct browser-friendly template is used.
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.http_client = Client()

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
        from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(
            user=self.admin, program=self.program, role=ROLE_PROGRAM_MANAGER
        )

        self.client_file = ClientFile.objects.create(record_id="REC-HTML-001")
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program
        )

        self.metric_def = MetricDefinition.objects.create(
            name="HTML Test Metric", is_enabled=True
        )

        section = PlanSection.objects.create(
            client_file=self.client_file, name="Test Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file,
        )
        target.name = "Test target"
        target.description = "Test"
        target.save()
        PlanTargetMetric.objects.create(plan_target=target, metric_def=self.metric_def)

        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick", author=self.admin,
        )
        note_target = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target,
        )
        MetricValue.objects.create(
            progress_note_target=note_target, metric_def=self.metric_def, value="7",
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings()
    def test_html_export_uses_styled_template(self):
        """HTML export must contain styled HTML (not WeasyPrint @page CSS)."""
        settings.SECURE_EXPORT_DIR = self.export_dir
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post("/reports/export/", {
            "program": self.program.pk,
            "date_from": "2020-01-01",
            "date_to": "2030-12-31",
            "metrics": [self.metric_def.pk],
            "format": "html",
            "recipient": "Self — for my own records",
            "recipient_reason": "Testing HTML rendering",
        })
        self.assertEqual(resp.status_code, 200)

        # The response should contain the secure link page, find the file
        link = SecureExportLink.objects.order_by("-created_at").first()
        self.assertIsNotNone(link)
        with open(link.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must have styled HTML elements from html_outcome_report.html
        self.assertIn("stat-box", content, "HTML export missing stat-box class — wrong template used")
        self.assertIn("report-header-bar", content, "HTML export missing report-header-bar — wrong template used")
        # Must NOT have WeasyPrint-specific CSS
        self.assertNotIn("@page", content, "HTML export contains @page CSS — PDF template was used")


# ═════════════════════════════════════════════════════════════════════
# 15. SecureExportLink.export_type validation test
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ExportTypeValidationTest(TestCase):
    """Verify SecureExportLink rejects unknown export_type values on save."""

    def setUp(self):
        enc_module._fernet = None
        self.export_dir = tempfile.mkdtemp(prefix="konote_test_exports_")
        self.user = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin"
        )

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def test_valid_export_type_accepted(self):
        """Known export types should save without error."""
        from django.core.exceptions import ValidationError
        for type_code, _ in SecureExportLink.EXPORT_TYPE_CHOICES:
            try:
                _create_link(self.user, self.export_dir, export_type=type_code)
            except ValidationError:
                self.fail(f"Valid export_type '{type_code}' raised ValidationError")

    def test_unknown_export_type_rejected(self):
        """Unknown export_type (e.g. old 'funder_report') must raise ValidationError."""
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as cm:
            _create_link(self.user, self.export_dir, export_type="funder_report")
        self.assertIn("export_type", cm.exception.message_dict)

    def test_bogus_export_type_rejected(self):
        """Completely invalid export_type must raise ValidationError."""
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            _create_link(self.user, self.export_dir, export_type="nonexistent_type")


# ═════════════════════════════════════════════════════════════════════
# 8. Evaluator Export (Confidential) — per-user grant only
# ═════════════════════════════════════════════════════════════════════
# Regression guard for the governance model in
# tasks/eval-export-governance.md: report.evaluation_export is DENY for
# all roles by default and must be granted per-user. Admins are the
# *granters*, not the *operators*, so an admin without the explicit
# grant must NOT reach the evaluation export view. This test exists
# because PR #617 / #622 removed an `is_admin` bypass in
# apps/reports/utils.can_create_evaluation_export — do not add one back
# without also updating these tests and the governance doc.


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluatorExportPermissionTest(TestCase):
    """Verify the evaluation_export view and helper honour per-user grant."""

    url = "/reports/evaluation-export/"

    def setUp(self):
        enc_module._fernet = None

    # Helper-level tests (pure function — no view/template rendering)
    def test_helper_denies_admin_without_grant(self):
        from apps.reports.utils import can_create_evaluation_export
        admin = User.objects.create_user(
            username="admin_no_grant", password="x",
            is_admin=True, display_name="Admin NoGrant",
            evaluation_export_granted=False,
        )
        self.assertFalse(can_create_evaluation_export(admin))

    def test_helper_allows_granted_non_admin(self):
        from apps.reports.utils import can_create_evaluation_export
        user = User.objects.create_user(
            username="granted_staff", password="x",
            is_admin=False, display_name="Granted Staff",
            evaluation_export_granted=True,
        )
        self.assertTrue(can_create_evaluation_export(user))

    def test_helper_denies_granted_user_without_flag(self):
        from apps.reports.utils import can_create_evaluation_export
        user = User.objects.create_user(
            username="plain_pm", password="x",
            is_admin=False, display_name="Plain PM",
        )
        self.assertFalse(can_create_evaluation_export(user))

    # View-level tests
    def test_view_returns_403_for_admin_without_grant(self):
        """The actual regression guard: the view must not rely on is_admin."""
        admin = User.objects.create_user(
            username="admin_view_403", password="x",
            is_admin=True, display_name="Admin 403",
            evaluation_export_granted=False,
        )
        c = Client()
        c.force_login(admin)
        resp = c.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_view_redirects_anonymous_to_login(self):
        """@login_required runs before the permission check."""
        resp = Client().get(self.url)
        self.assertEqual(resp.status_code, 302)


# ═════════════════════════════════════════════════════════════════════
# 9. EVAL-GOV1 — EvaluationExportGrant model, signal, form, views
# ═════════════════════════════════════════════════════════════════════
# The grant model + admin UI that enforces the two-person governance
# control: ED authorises an evaluation engagement → Admin records the
# grant in KoNote with a reason. See tasks/eval-export-governance.md
# and tasks/phase-eval-gov1-prompt.md for the full spec.
#
# The cached `User.evaluation_export_granted` boolean is kept as a
# denormalised hot-path flag and must stay in sync with active grants
# via post_save signal. Both the helper and the view read the cached
# flag, so signal correctness is load-bearing.


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportGrantModelTest(TestCase):
    """EvaluationExportGrant model basics: creation, ordering, unique constraint."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="grant_admin", password="x",
            is_admin=True, display_name="Grant Admin",
        )
        self.target = User.objects.create_user(
            username="grant_target", password="x",
            display_name="Grant Target",
        )

    def test_create_grant_persists_fields(self):
        from apps.auth_app.models import EvaluationExportGrant
        grant = EvaluationExportGrant.objects.create(
            user=self.target,
            granted_by=self.admin,
            reason="Board approved evaluation with Llewelyn Consulting, MOU 2026-04-15.",
        )
        grant.refresh_from_db()
        self.assertEqual(grant.user, self.target)
        self.assertEqual(grant.granted_by, self.admin)
        self.assertTrue(grant.active)
        self.assertIsNotNone(grant.granted_at)
        self.assertIsNone(grant.revoked_at)

    def test_grants_order_newest_first(self):
        from apps.auth_app.models import EvaluationExportGrant
        first = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="First grant for Youth Employment evaluation Q1-2026.",
        )
        first.active = False
        first.save()
        second = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Second grant for follow-up evaluation Q3-2026.",
        )
        grants = list(EvaluationExportGrant.objects.filter(user=self.target))
        self.assertEqual(grants[0], second)
        self.assertEqual(grants[1], first)

    def test_unique_active_grant_per_user(self):
        """The partial unique constraint prevents two active grants for one user."""
        from django.db import IntegrityError, transaction
        from apps.auth_app.models import EvaluationExportGrant
        EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="First grant — evaluation engagement with University X.",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EvaluationExportGrant.objects.create(
                    user=self.target, granted_by=self.admin,
                    reason="Duplicate grant attempt — should be blocked by constraint.",
                )

    def test_can_regrant_after_revoke(self):
        """Once the first grant is marked inactive, a new grant can be created."""
        from apps.auth_app.models import EvaluationExportGrant
        first = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Initial grant for evaluation 2026-Q1 with Llewelyn.",
        )
        first.active = False
        first.revoked_at = timezone.now()
        first.revoked_by = self.admin
        first.save()

        second = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Re-grant for a new evaluation engagement 2026-Q3.",
        )
        self.assertTrue(second.active)
        self.assertEqual(
            EvaluationExportGrant.objects.filter(user=self.target, active=True).count(),
            1,
        )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportGrantSignalTest(TestCase):
    """The post_save signal must keep User.evaluation_export_granted in sync."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="signal_admin", password="x",
            is_admin=True, display_name="Signal Admin",
        )
        self.target = User.objects.create_user(
            username="signal_target", password="x",
            display_name="Signal Target",
        )

    def test_creating_grant_sets_cached_flag(self):
        from apps.auth_app.models import EvaluationExportGrant
        self.assertFalse(self.target.evaluation_export_granted)
        EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Granted for program evaluation with external consultants.",
        )
        self.target.refresh_from_db()
        self.assertTrue(self.target.evaluation_export_granted)

    def test_marking_grant_inactive_clears_cached_flag(self):
        from apps.auth_app.models import EvaluationExportGrant
        grant = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Grant to be revoked for signal-sync test case.",
        )
        self.target.refresh_from_db()
        self.assertTrue(self.target.evaluation_export_granted)

        grant.active = False
        grant.revoked_at = timezone.now()
        grant.revoked_by = self.admin
        grant.save()
        self.target.refresh_from_db()
        self.assertFalse(self.target.evaluation_export_granted)

    def test_signal_scoped_to_target_user_only(self):
        from apps.auth_app.models import EvaluationExportGrant
        other = User.objects.create_user(
            username="signal_other", password="x",
            display_name="Signal Other",
        )
        EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Grant for target user only — should not affect other user.",
        )
        self.target.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(self.target.evaluation_export_granted)
        self.assertFalse(other.evaluation_export_granted)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportGrantFormTest(TestCase):
    """EvaluationExportGrantForm enforces a meaningful reason."""

    def _form(self, reason):
        from apps.auth_app.forms import EvaluationExportGrantForm
        return EvaluationExportGrantForm(data={"reason": reason})

    def test_blank_reason_rejected(self):
        self.assertFalse(self._form("").is_valid())

    def test_short_reason_rejected(self):
        self.assertFalse(self._form("ok").is_valid())
        self.assertFalse(self._form("test grant").is_valid())  # 10 chars, still too short

    def test_reason_at_minimum_length_accepted(self):
        # 15 chars, meaningful
        self.assertTrue(self._form("Board approved.").is_valid())

    def test_long_reason_accepted(self):
        reason = (
            "ED approved evaluation with Llewelyn Consulting; "
            "MOU signed 2026-04-15, expires 2026-12-31."
        )
        self.assertTrue(self._form(reason).is_valid())

    def test_reason_at_max_length_accepted(self):
        from apps.auth_app.forms import EvaluationExportGrantForm
        reason = "x" * EvaluationExportGrantForm.REASON_MAX_LENGTH
        self.assertTrue(self._form(reason).is_valid())

    def test_reason_over_max_length_rejected(self):
        from apps.auth_app.forms import EvaluationExportGrantForm
        reason = "x" * (EvaluationExportGrantForm.REASON_MAX_LENGTH + 1)
        self.assertFalse(self._form(reason).is_valid())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportGrantViewTest(TestCase):
    """Admin grant/revoke flow end-to-end."""

    databases = {"default", "audit"}

    list_url = "/manage/users/evaluation-export/"
    create_url = "/manage/users/evaluation-export/new/"

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="view_admin", password="x",
            is_admin=True, display_name="View Admin",
        )
        self.target = User.objects.create_user(
            username="view_target", password="x",
            display_name="View Target",
        )
        self.outsider = User.objects.create_user(
            username="view_outsider", password="x",
            display_name="View Outsider",
        )

    # List view -------------------------------------------------------

    def test_list_view_200_for_admin(self):
        c = Client()
        c.force_login(self.admin)
        resp = c.get(self.list_url)
        self.assertEqual(resp.status_code, 200)

    def test_list_view_denies_non_admin_without_user_manage(self):
        c = Client()
        c.force_login(self.outsider)
        resp = c.get(self.list_url)
        self.assertIn(resp.status_code, (302, 403))

    def test_list_view_shows_granted_users(self):
        from apps.auth_app.models import EvaluationExportGrant
        EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="ED authorised evaluation with Prosper Canada cohort 2026.",
        )
        c = Client()
        c.force_login(self.admin)
        resp = c.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "View Target")
        self.assertContains(resp, "Prosper Canada cohort")

    # Create view -----------------------------------------------------

    def test_create_view_get_200_for_admin(self):
        c = Client()
        c.force_login(self.admin)
        resp = c.get(f"{self.create_url}?user_id={self.target.pk}")
        self.assertEqual(resp.status_code, 200)

    def test_create_view_post_creates_grant(self):
        from apps.auth_app.models import EvaluationExportGrant
        c = Client()
        c.force_login(self.admin)
        resp = c.post(self.create_url, {
            "user_id": self.target.pk,
            "reason": "ED authorised Youth Employment evaluation with Llewelyn Consulting 2026.",
        })
        self.assertEqual(resp.status_code, 302)
        grant = EvaluationExportGrant.objects.get(user=self.target, active=True)
        self.assertEqual(grant.granted_by, self.admin)
        self.target.refresh_from_db()
        self.assertTrue(self.target.evaluation_export_granted)

    def test_create_view_rejects_blank_reason(self):
        from apps.auth_app.models import EvaluationExportGrant
        c = Client()
        c.force_login(self.admin)
        resp = c.post(self.create_url, {
            "user_id": self.target.pk,
            "reason": "",
        })
        self.assertEqual(resp.status_code, 200)  # re-render form with errors
        self.assertFalse(
            EvaluationExportGrant.objects.filter(user=self.target).exists()
        )

    def test_create_view_rejects_duplicate_active_grant(self):
        from apps.auth_app.models import EvaluationExportGrant
        EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="First grant is already active for this user.",
        )
        c = Client()
        c.force_login(self.admin)
        resp = c.post(self.create_url, {
            "user_id": self.target.pk,
            "reason": "Attempt to create a second active grant — should fail.",
        })
        # Form re-renders with a clear error, no second grant written
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            EvaluationExportGrant.objects.filter(
                user=self.target, active=True,
            ).count(),
            1,
        )

    def test_create_view_denies_non_admin(self):
        c = Client()
        c.force_login(self.outsider)
        resp = c.post(self.create_url, {
            "user_id": self.target.pk,
            "reason": "Outsider should not be able to grant this permission.",
        })
        self.assertIn(resp.status_code, (302, 403))

    # Revoke view -----------------------------------------------------

    def test_revoke_view_marks_grant_inactive(self):
        from apps.auth_app.models import EvaluationExportGrant
        grant = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Grant that will be revoked in this test scenario.",
        )
        self.target.refresh_from_db()
        self.assertTrue(self.target.evaluation_export_granted)

        c = Client()
        c.force_login(self.admin)
        resp = c.post(f"/manage/users/evaluation-export/{grant.pk}/revoke/")
        self.assertEqual(resp.status_code, 302)

        grant.refresh_from_db()
        self.assertFalse(grant.active)
        self.assertIsNotNone(grant.revoked_at)
        self.assertEqual(grant.revoked_by, self.admin)

        self.target.refresh_from_db()
        self.assertFalse(self.target.evaluation_export_granted)

    def test_revoke_view_denies_non_admin(self):
        from apps.auth_app.models import EvaluationExportGrant
        grant = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Grant that outsider should not be able to revoke.",
        )
        c = Client()
        c.force_login(self.outsider)
        resp = c.post(f"/manage/users/evaluation-export/{grant.pk}/revoke/")
        self.assertIn(resp.status_code, (302, 403))
        grant.refresh_from_db()
        self.assertTrue(grant.active)

    # Self-grant --------------------------------------------------------
    #
    # Admins CAN grant themselves the permission (a single-person small
    # agency may need it), but the grant row records target == granted_by
    # so EVAL-GOV2 can surface it on the dashboard as something to review.

    def test_admin_can_self_grant(self):
        from apps.auth_app.models import EvaluationExportGrant
        c = Client()
        c.force_login(self.admin)
        resp = c.post(self.create_url, {
            "user_id": self.admin.pk,
            "reason": "Sole administrator self-grant for a board-approved evaluation.",
        })
        self.assertEqual(resp.status_code, 302)
        grant = EvaluationExportGrant.objects.get(user=self.admin, active=True)
        self.assertEqual(grant.granted_by, self.admin)

    # Audit trail -------------------------------------------------------
    #
    # Every grant create, revoke, and rejected attempt must leave an
    # audit trail so a privacy officer can answer "who has held this
    # permission, and who has tried to obtain it?" The audit DB is the
    # only place where rejected attempts are recorded.

    def test_grant_success_writes_audit_row(self):
        from apps.audit.models import AuditLog
        c = Client()
        c.force_login(self.admin)
        c.post(self.create_url, {
            "user_id": self.target.pk,
            "reason": "ED approved Youth Employment evaluation engagement 2026-Q2.",
        })
        log = AuditLog.objects.using("audit").filter(
            resource_type="evaluation_export_grant",
            action="create",
        ).latest("event_timestamp")
        self.assertEqual(log.user_id, self.admin.pk)
        self.assertEqual(log.metadata["target_user_id"], self.target.pk)
        self.assertIn("Youth Employment", log.metadata["reason"])
        self.assertTrue(log.metadata["active"])

    def test_revoke_writes_audit_row(self):
        from apps.auth_app.models import EvaluationExportGrant
        from apps.audit.models import AuditLog
        grant = EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Grant that will be revoked and audit-checked.",
        )
        c = Client()
        c.force_login(self.admin)
        c.post(f"/manage/users/evaluation-export/{grant.pk}/revoke/")
        log = AuditLog.objects.using("audit").filter(
            resource_type="evaluation_export_grant",
            action="update",
        ).latest("event_timestamp")
        self.assertEqual(log.user_id, self.admin.pk)
        self.assertEqual(log.metadata["grant_id"], grant.pk)
        self.assertFalse(log.metadata["active"])
        self.assertEqual(log.metadata["revoked_by_id"], self.admin.pk)

    def test_rejected_invalid_user_writes_audit_row(self):
        from apps.audit.models import AuditLog
        c = Client()
        c.force_login(self.admin)
        c.post(self.create_url, {
            "user_id": "999999",  # nonexistent
            "reason": "Attempt to grant to a nonexistent user for the audit test.",
        })
        log = AuditLog.objects.using("audit").filter(
            resource_type="evaluation_export_grant",
            action="access_denied",
        ).latest("event_timestamp")
        self.assertEqual(log.metadata["outcome"], "rejected")
        self.assertEqual(log.metadata["failure_reason"], "invalid_user")
        self.assertEqual(log.metadata["attempted_user_id"], "999999")

    def test_rejected_duplicate_writes_audit_row(self):
        from apps.auth_app.models import EvaluationExportGrant
        from apps.audit.models import AuditLog
        EvaluationExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="Existing active grant that a second attempt should hit.",
        )
        c = Client()
        c.force_login(self.admin)
        c.post(self.create_url, {
            "user_id": self.target.pk,
            "reason": "Second attempt should fail due to duplicate active grant.",
        })
        log = AuditLog.objects.using("audit").filter(
            resource_type="evaluation_export_grant",
            action="access_denied",
        ).latest("event_timestamp")
        self.assertEqual(log.metadata["failure_reason"], "duplicate_active_grant")
        self.assertEqual(log.metadata["attempted_user_id"], str(self.target.pk))

    def test_rejected_short_reason_writes_audit_row(self):
        from apps.audit.models import AuditLog
        c = Client()
        c.force_login(self.admin)
        c.post(self.create_url, {
            "user_id": self.target.pk,
            "reason": "ok",  # too short, in blocklist
        })
        log = AuditLog.objects.using("audit").filter(
            resource_type="evaluation_export_grant",
            action="access_denied",
        ).latest("event_timestamp")
        self.assertEqual(log.metadata["failure_reason"], "reason_validation_failed")
        self.assertEqual(log.metadata["attempted_user_id"], str(self.target.pk))
        self.assertEqual(log.metadata["raw_reason"], "ok")
        self.assertIn("reason", log.metadata["form_errors"])

    # Concurrent-grant race ---------------------------------------------

    def test_concurrent_grant_race_caught_by_db_constraint(self):
        """Simulate two admins racing past the view-level duplicate check.

        We monkey-patch the view's pre-check by creating a grant between
        the candidate-set read and the create() call via a post_save
        signal that would only fire in a real race. Easier: create the
        first grant *directly*, then POST a second — the view's set is
        stale (read before the direct create), so the check passes, but
        the DB constraint fires.

        In this test we use a simpler approach: directly exercise the
        IntegrityError path by calling the view twice in quick succession
        with the candidate-set cached in the first request's state. The
        partial unique constraint at the DB layer is the real guarantee;
        we just want to confirm the view handles it gracefully.
        """
        from apps.auth_app.models import EvaluationExportGrant
        from apps.audit.models import AuditLog

        # Create a grant directly so the next POST's view-level check
        # still thinks the user is available (because it reads
        # users_with_active_grants at the TOP of the view, but here we
        # insert the competing grant AFTER that would-be read). We
        # simulate by using the ORM directly from a second test user,
        # then POST.
        #
        # Easier path: craft a scenario where the view's
        # users_with_active_grants set doesn't include the target, then
        # insert the competing grant before the .create() would run.
        # We can't literally interleave requests in a single-process
        # test, so instead we directly test the except branch by
        # pre-inserting a grant and bypassing the view-level check via
        # a form POST with a handcrafted state.
        #
        # Practical approach: the partial unique constraint is tested
        # at the model level (test_unique_active_grant_per_user). What
        # matters for the VIEW is that any IntegrityError from create()
        # becomes a re-render, not a 500. We force that by mocking
        # EvaluationExportGrant.objects.create to raise IntegrityError.
        from unittest.mock import patch
        from django.db import IntegrityError

        c = Client()
        c.force_login(self.admin)

        # Exclude the target from active grants (so the view-level
        # duplicate check passes), then patch .create() on the model
        # manager to raise IntegrityError as the DB would in a race.
        with patch(
            "apps.auth_app.admin_views.EvaluationExportGrant.objects.create",
            side_effect=IntegrityError("simulated race"),
        ):
            resp = c.post(self.create_url, {
                "user_id": self.target.pk,
                "reason": "Valid reason that would normally create a grant successfully.",
            })

        # View re-renders with the duplicate error, not a 500
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            EvaluationExportGrant.objects.filter(user=self.target).exists()
        )
        # Audit row records the race
        log = AuditLog.objects.using("audit").filter(
            resource_type="evaluation_export_grant",
            action="access_denied",
        ).latest("event_timestamp")
        self.assertEqual(
            log.metadata["failure_reason"], "race_duplicate_active_grant",
        )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportGrantAdminOnlyTest(TestCase):
    """Regression guard: the grant views are admin-only.

    The DRR and governance doc both specify that only system admins
    grant `report.evaluation_export`. A Program Manager with
    `user.manage: PROGRAM` in their own programs would otherwise reach
    `@requires_permission("user.manage", allow_admin=True)` and could
    grant or revoke system-wide. This test locks in `@admin_required`.
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="PM Program")
        self.pm = User.objects.create_user(
            username="pm_grant_denied", password="x",
            display_name="PM Grant Denied",
        )
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role=ROLE_PROGRAM_MANAGER,
        )
        self.admin = User.objects.create_user(
            username="admin_grant_ok", password="x",
            is_admin=True, display_name="Admin Grant OK",
        )

    def _as(self, user):
        c = Client()
        c.force_login(user)
        return c

    def test_pm_with_user_manage_cannot_reach_list(self):
        resp = self._as(self.pm).get("/manage/users/evaluation-export/")
        self.assertEqual(resp.status_code, 403)

    def test_pm_with_user_manage_cannot_reach_create(self):
        resp = self._as(self.pm).get("/manage/users/evaluation-export/new/")
        self.assertEqual(resp.status_code, 403)

    def test_pm_with_user_manage_cannot_post_grant(self):
        from apps.auth_app.models import EvaluationExportGrant
        target = User.objects.create_user(
            username="pm_grant_target", password="x",
            display_name="Target",
        )
        resp = self._as(self.pm).post("/manage/users/evaluation-export/new/", {
            "user_id": target.pk,
            "reason": "PM attempting to grant the permission to another user.",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            EvaluationExportGrant.objects.filter(user=target).exists()
        )

    def test_pm_with_user_manage_cannot_revoke(self):
        from apps.auth_app.models import EvaluationExportGrant
        target = User.objects.create_user(
            username="pm_revoke_target", password="x",
            display_name="Target",
        )
        grant = EvaluationExportGrant.objects.create(
            user=target, granted_by=self.admin,
            reason="Grant created by admin — PM should not be able to revoke.",
        )
        resp = self._as(self.pm).post(
            f"/manage/users/evaluation-export/{grant.pk}/revoke/"
        )
        self.assertEqual(resp.status_code, 403)
        grant.refresh_from_db()
        self.assertTrue(grant.active)

    def test_admin_still_reaches_list(self):
        resp = self._as(self.admin).get("/manage/users/evaluation-export/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportGrantDjangoAdminReadonlyTest(TestCase):
    """The Django admin must not allow direct editing of the cached flag.

    EVAL-GOV1 removes the bypass where an admin could flip
    evaluation_export_granted on /admin/auth_app/user/<id>/change/
    without creating a grant row. This test guards against that
    regression by inspecting the registered UserAdmin.
    """

    def setUp(self):
        enc_module._fernet = None

    def test_cached_flag_is_readonly_in_django_admin(self):
        from django.contrib import admin as django_admin
        from apps.auth_app.models import User as UserModel

        user_admin = django_admin.site._registry[UserModel]
        self.assertIn("evaluation_export_granted", user_admin.readonly_fields)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportGrantIntegrationTest(TestCase):
    """End-to-end: grant via admin UI → user hits report → revoke → 403."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="int_admin", password="x",
            is_admin=True, display_name="Int Admin",
        )
        self.target = User.objects.create_user(
            username="int_target", password="x",
            display_name="Int Target",
        )

    def test_grant_then_revoke_cycle_controls_access(self):
        from apps.auth_app.models import EvaluationExportGrant

        # Before grant: 403
        c = Client()
        c.force_login(self.target)
        resp = c.get("/reports/evaluation-export/")
        self.assertEqual(resp.status_code, 403)

        # Admin grants via the admin UI
        admin_c = Client()
        admin_c.force_login(self.admin)
        admin_c.post("/manage/users/evaluation-export/new/", {
            "user_id": self.target.pk,
            "reason": "ED approved evaluation engagement — integration test scenario.",
        })

        # Now accessible
        resp = c.get("/reports/evaluation-export/")
        self.assertEqual(resp.status_code, 200)

        # Admin revokes
        grant = EvaluationExportGrant.objects.get(user=self.target, active=True)
        admin_c.post(f"/manage/users/evaluation-export/{grant.pk}/revoke/")

        # Access denied again
        resp = c.get("/reports/evaluation-export/")
        self.assertEqual(resp.status_code, 403)
