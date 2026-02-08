"""Tests for audit log views: list, export, and program-scoped audit log."""
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.audit.models import AuditLog
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _create_audit_entry(**kwargs):
    """Helper to create an AuditLog entry in the audit database."""
    defaults = {
        "event_timestamp": timezone.now(),
        "user_id": 1,
        "user_display": "Test User",
        "action": "view",
        "resource_type": "clients",
        "is_demo_context": False,
    }
    defaults.update(kwargs)
    return AuditLog.objects.using("audit").create(**defaults)


# ── audit_log_list view (/admin/audit/) ──────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AuditLogListTests(TestCase):
    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )

    # ── Permission checks ────────────────────────────────────────

    def test_admin_can_view_audit_log(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/")
        self.assertEqual(resp.status_code, 200)

    def test_non_admin_gets_403(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/admin/audit/")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_user_redirects_to_login(self):
        resp = self.client.get("/admin/audit/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    # ── Filtering ────────────────────────────────────────────────

    def test_filter_by_action(self):
        _create_audit_entry(action="login", user_display="Alice")
        _create_audit_entry(action="export", user_display="Bob")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/", {"action": "login"})
        self.assertEqual(resp.status_code, 200)
        # Page should contain only the login entry
        page = resp.context["page"]
        actions = [e.action for e in page.object_list]
        self.assertIn("login", actions)
        self.assertNotIn("export", actions)

    def test_filter_by_user_display(self):
        _create_audit_entry(user_display="Alice Admin")
        _create_audit_entry(user_display="Bob Staff")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/", {"user_display": "Alice"})
        page = resp.context["page"]
        displays = [e.user_display for e in page.object_list]
        self.assertIn("Alice Admin", displays)
        self.assertNotIn("Bob Staff", displays)

    def test_filter_by_resource_type(self):
        _create_audit_entry(resource_type="clients")
        _create_audit_entry(resource_type="programs")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/", {"resource_type": "clients"})
        page = resp.context["page"]
        types = [e.resource_type for e in page.object_list]
        self.assertIn("clients", types)
        self.assertNotIn("programs", types)

    def test_filter_by_demo_real(self):
        _create_audit_entry(is_demo_context=False, user_display="Real")
        _create_audit_entry(is_demo_context=True, user_display="Demo")
        self.client.login(username="admin", password="testpass123")

        # Filter for real only
        resp = self.client.get("/admin/audit/", {"demo_filter": "real"})
        page = resp.context["page"]
        displays = [e.user_display for e in page.object_list]
        self.assertIn("Real", displays)
        self.assertNotIn("Demo", displays)

    def test_filter_by_demo_demo(self):
        _create_audit_entry(is_demo_context=False, user_display="Real")
        _create_audit_entry(is_demo_context=True, user_display="Demo")
        self.client.login(username="admin", password="testpass123")

        # Filter for demo only
        resp = self.client.get("/admin/audit/", {"demo_filter": "demo"})
        page = resp.context["page"]
        displays = [e.user_display for e in page.object_list]
        self.assertIn("Demo", displays)
        self.assertNotIn("Real", displays)

    def test_filter_by_date_from(self):
        old = _create_audit_entry(
            event_timestamp=timezone.make_aware(
                timezone.datetime(2025, 1, 1, 12, 0)
            ),
            user_display="Old",
        )
        recent = _create_audit_entry(
            event_timestamp=timezone.make_aware(
                timezone.datetime(2026, 6, 15, 12, 0)
            ),
            user_display="Recent",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/", {"date_from": "2026-01-01"})
        page = resp.context["page"]
        displays = [e.user_display for e in page.object_list]
        self.assertIn("Recent", displays)
        self.assertNotIn("Old", displays)

    def test_filter_by_date_to(self):
        old = _create_audit_entry(
            event_timestamp=timezone.make_aware(
                timezone.datetime(2025, 1, 1, 12, 0)
            ),
            user_display="Old",
        )
        recent = _create_audit_entry(
            event_timestamp=timezone.make_aware(
                timezone.datetime(2026, 6, 15, 12, 0)
            ),
            user_display="Recent",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/", {"date_to": "2025-12-31"})
        page = resp.context["page"]
        displays = [e.user_display for e in page.object_list]
        self.assertIn("Old", displays)
        self.assertNotIn("Recent", displays)

    # ── Pagination ───────────────────────────────────────────────

    def test_pagination_returns_50_per_page(self):
        # Create 55 entries so there are 2 pages
        for i in range(55):
            _create_audit_entry(user_display=f"User {i}")
        self.client.login(username="admin", password="testpass123")

        resp = self.client.get("/admin/audit/")
        page = resp.context["page"]
        self.assertEqual(len(page.object_list), 50)
        self.assertTrue(page.has_next())

        resp2 = self.client.get("/admin/audit/", {"page": "2"})
        page2 = resp2.context["page"]
        self.assertEqual(len(page2.object_list), 5)
        self.assertFalse(page2.has_next())


# ── audit_log_export view (/admin/audit/export/) ────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AuditLogExportTests(TestCase):
    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123",
            is_admin=True, display_name="Admin User",
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False
        )

    # ── Permission checks ────────────────────────────────────────

    def test_admin_can_export_csv(self):
        _create_audit_entry(user_display="Alice", action="login")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertIn("audit_log_", resp["Content-Disposition"])

    def test_non_admin_gets_403(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/admin/audit/export/")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_user_redirects_to_login(self):
        resp = self.client.get("/admin/audit/export/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    # ── CSV content ──────────────────────────────────────────────

    def test_csv_contains_header_row(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/export/")
        content = resp.content.decode("utf-8")
        # Header row should contain these column names
        self.assertIn("Timestamp", content)
        self.assertIn("User", content)
        self.assertIn("Action", content)
        self.assertIn("Resource Type", content)

    def test_csv_contains_entry_data(self):
        _create_audit_entry(
            user_display="TestExportUser",
            action="create",
            resource_type="clients",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/export/")
        content = resp.content.decode("utf-8")
        self.assertIn("TestExportUser", content)
        self.assertIn("create", content)

    # ── Export creates audit log entry ───────────────────────────

    def test_export_creates_audit_log_entry(self):
        """The export view itself should log an 'export' action."""
        self.client.login(username="admin", password="testpass123")
        count_before = AuditLog.objects.using("audit").filter(
            action="export", resource_type="audit_log"
        ).count()

        self.client.get("/admin/audit/export/")

        count_after = AuditLog.objects.using("audit").filter(
            action="export", resource_type="audit_log"
        ).count()
        self.assertEqual(count_after, count_before + 1)

    def test_export_audit_entry_records_user(self):
        """The export audit entry should record the exporting user's ID."""
        self.client.login(username="admin", password="testpass123")
        self.client.get("/admin/audit/export/")
        entry = AuditLog.objects.using("audit").filter(
            action="export", resource_type="audit_log"
        ).latest("event_timestamp")
        self.assertEqual(entry.user_id, self.admin.pk)

    # ── Export respects filters ──────────────────────────────────

    def test_export_respects_action_filter(self):
        _create_audit_entry(action="login", user_display="LoginUser")
        _create_audit_entry(action="create", user_display="CreateUser")
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/audit/export/", {"action": "login"})
        content = resp.content.decode("utf-8")
        self.assertIn("LoginUser", content)
        self.assertNotIn("CreateUser", content)


# ── program_audit_log view (/audit/program/<id>/) ───────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramAuditLogTests(TestCase):
    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()

        # Create users
        self.manager = User.objects.create_user(
            username="manager", password="testpass123", is_admin=False
        )
        self.executive = User.objects.create_user(
            username="exec", password="testpass123", is_admin=False
        )
        self.caseworker = User.objects.create_user(
            username="caseworker", password="testpass123", is_admin=False
        )
        self.outsider = User.objects.create_user(
            username="outsider", password="testpass123", is_admin=False
        )

        # Create a program
        self.program = Program.objects.create(
            name="Housing Support", status="active"
        )

        # Assign roles
        UserProgramRole.objects.create(
            user=self.manager, program=self.program,
            role="program_manager", status="active",
        )
        UserProgramRole.objects.create(
            user=self.executive, program=self.program,
            role="executive", status="active",
        )
        UserProgramRole.objects.create(
            user=self.caseworker, program=self.program,
            role="staff", status="active",
        )

        # Create a client enrolled in the program
        self.client_file = ClientFile.objects.create(is_demo=False)
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()

        self.enrolment = ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="enrolled",
        )

    def _url(self):
        return f"/audit/program/{self.program.pk}/"

    # ── Permission checks ────────────────────────────────────────

    def test_program_manager_can_view(self):
        self.client.login(username="manager", password="testpass123")
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)

    def test_executive_can_view(self):
        self.client.login(username="exec", password="testpass123")
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)

    def test_caseworker_gets_403(self):
        """Staff (caseworker) role does not have access to program audit log."""
        self.client.login(username="caseworker", password="testpass123")
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 403)

    def test_non_member_gets_403(self):
        """User with no role in the program cannot view its audit log."""
        self.client.login(username="outsider", password="testpass123")
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_user_redirects_to_login(self):
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_inactive_role_gets_403(self):
        """A removed role should not grant access."""
        removed_user = User.objects.create_user(
            username="removed", password="testpass123", is_admin=False
        )
        UserProgramRole.objects.create(
            user=removed_user, program=self.program,
            role="program_manager", status="removed",
        )
        self.client.login(username="removed", password="testpass123")
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 403)

    def test_nonexistent_program_returns_404(self):
        self.client.login(username="manager", password="testpass123")
        resp = self.client.get("/audit/program/99999/")
        self.assertEqual(resp.status_code, 404)

    # ── Scoping: only shows program-related entries ──────────────

    def test_shows_entries_with_matching_program_id(self):
        """Entries with program_id matching the program should appear."""
        _create_audit_entry(
            program_id=self.program.pk,
            user_display="MatchByProgram",
            resource_type="notes",
        )
        _create_audit_entry(
            program_id=self.program.pk + 100,
            user_display="OtherProgram",
            resource_type="notes",
        )
        self.client.login(username="manager", password="testpass123")
        resp = self.client.get(self._url())
        page = resp.context["page"]
        displays = [e.user_display for e in page.object_list]
        self.assertIn("MatchByProgram", displays)
        self.assertNotIn("OtherProgram", displays)

    def test_shows_entries_for_enrolled_clients(self):
        """Entries about clients enrolled in the program should appear."""
        _create_audit_entry(
            resource_type="clients",
            resource_id=self.client_file.pk,
            user_display="ClientEntry",
        )
        # Entry for a client NOT in this program
        _create_audit_entry(
            resource_type="clients",
            resource_id=99999,
            user_display="UnrelatedClient",
        )
        self.client.login(username="manager", password="testpass123")
        resp = self.client.get(self._url())
        page = resp.context["page"]
        displays = [e.user_display for e in page.object_list]
        self.assertIn("ClientEntry", displays)
        self.assertNotIn("UnrelatedClient", displays)

    # ── Filtering within program audit log ───────────────────────

    def test_filter_by_action_in_program_log(self):
        _create_audit_entry(
            program_id=self.program.pk, action="create", user_display="Creator"
        )
        _create_audit_entry(
            program_id=self.program.pk, action="delete", user_display="Deleter"
        )
        self.client.login(username="manager", password="testpass123")
        resp = self.client.get(self._url(), {"action": "create"})
        page = resp.context["page"]
        actions = [e.action for e in page.object_list]
        self.assertIn("create", actions)
        self.assertNotIn("delete", actions)
