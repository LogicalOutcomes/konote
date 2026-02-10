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
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        # Staff in program A
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )
        # Executive in program A
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
        )

    # ── Admin ────────────────────────────────────────────────────

    def test_admin_can_create_metrics_export(self):
        self.assertTrue(can_create_export(self.admin, "metrics"))

    def test_admin_can_create_funder_report(self):
        self.assertTrue(can_create_export(self.admin, "funder_report"))

    def test_admin_can_export_any_program(self):
        self.assertTrue(can_create_export(self.admin, "metrics", program=self.program_a))
        self.assertTrue(can_create_export(self.admin, "metrics", program=self.program_b))

    # ── Program Manager ──────────────────────────────────────────

    def test_pm_can_create_metrics_export(self):
        self.assertTrue(can_create_export(self.pm_user, "metrics"))

    def test_pm_can_create_funder_report(self):
        self.assertTrue(can_create_export(self.pm_user, "funder_report"))

    def test_pm_can_export_own_program(self):
        self.assertTrue(can_create_export(self.pm_user, "metrics", program=self.program_a))

    def test_pm_cannot_export_other_program(self):
        self.assertFalse(can_create_export(self.pm_user, "metrics", program=self.program_b))

    # ── Staff ────────────────────────────────────────────────────

    def test_staff_cannot_create_any_export(self):
        self.assertFalse(can_create_export(self.staff_user, "metrics"))
        self.assertFalse(can_create_export(self.staff_user, "funder_report"))

    # ── Executive ────────────────────────────────────────────────

    def test_executive_can_create_metrics_export(self):
        self.assertTrue(can_create_export(self.exec_user, "metrics"))

    def test_executive_can_create_funder_report(self):
        self.assertTrue(can_create_export(self.exec_user, "funder_report"))

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
            user=self.pm_user, program=self.program_a, role="program_manager"
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
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program_a, role="receptionist"
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
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
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
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.pm_user2, program=self.program_a, role="program_manager"
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
            user=exec_user, program=self.program_a, role="executive"
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
            user=self.pm_user, program=self.program_a, role="program_manager"
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
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
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
            user=self.exec_user, program=self.program_a, role="executive"
        )
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        # Dual user: executive in program A, PM in program B
        UserProgramRole.objects.create(
            user=self.dual_user, program=self.program_a, role="executive"
        )
        UserProgramRole.objects.create(
            user=self.dual_user, program=self.program_b, role="program_manager"
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
            user=admin_pm, program=self.program_a, role="program_manager"
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
            user=self.pm_user, program=self.program, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program, role="executive"
        )

        # Client
        self.client_file = ClientFile.objects.create()
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
            "recipient": "self",
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
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program_a, role="receptionist"
        )

        # Admin needs a program role to pass ProgramAccessMiddleware
        # (admins without program roles are blocked from client URLs)
        UserProgramRole.objects.create(
            user=self.admin, program=self.program_a, role="program_manager"
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
        return f"/reports/client/{self.client_file.pk}/export/"

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

    Staff (SCOPED) and PM (ALLOW) can generate PDFs for clients in their
    programs. Executive (DENY) and receptionist (DENY) cannot. Admin-only
    users without program roles are blocked by _get_client_or_403().
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

        self.program_a = Program.objects.create(name="Program A")

        UserProgramRole.objects.create(
            user=self.admin, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
        )

        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program_a
        )

    def _pdf_url(self):
        return f"/reports/client/{self.client_file.pk}/pdf/"

    def test_pm_can_download_client_pdf(self):
        """PM CAN download client progress PDF (metric.view_individual=ALLOW)."""
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get(self._pdf_url())
        # 200 if WeasyPrint available, 503 if missing (Windows)
        self.assertIn(resp.status_code, [200, 503])

    def test_staff_can_download_client_pdf(self):
        """Staff CAN download client progress PDF (metric.view_individual=SCOPED)."""
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
            user=self.pm_user, program=self.program_a, role="program_manager"
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program_a, role="staff"
        )
        UserProgramRole.objects.create(
            user=self.exec_user, program=self.program_a, role="executive"
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program_a, role="receptionist"
        )

        self.client_file = ClientFile.objects.create()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program_a
        )

    def _analysis_url(self):
        return f"/reports/client/{self.client_file.pk}/analysis/"

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
