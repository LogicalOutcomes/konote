"""Parametrized permission enforcement test (Wave 6A).

Tests all 48 permission keys x 4 roles = 192 cases. For each (role, key)
pair, makes an HTTP request to the URL protected by that key and asserts:
  - DENY -> 403 (or 302 redirect for executives on client-scoped URLs)
  - ALLOW / SCOPED / GATED / PER_FIELD -> NOT 403

Keys with field-level enforcement (no URL to test):
  client.view_name, client.view_contact, client.view_safety,
  client.view_medications, client.view_clinical,
  custom_field.view, custom_field.edit,
  consent.view, intake.view, intake.edit

Keys with no dedicated view or URL:
  alert.view (shown on client detail page — implicit)
  attendance.check_in, attendance.view_report (view-level checks)
  metric.view_aggregate (enforced by is_aggregate_only_user in views)
  note.delete, plan.delete, client.delete (destructive, admin workflow)

Admin keys (enforced by @admin_required, not the permission matrix):
  user.manage, settings.manage, program.manage
  Tested separately — non-admin users should always get 403.

Matrix-enforced keys under /admin/ URL:
  audit.view — middleware exempts /admin/audit/, view uses @requires_permission
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.auth_app.models import User
from apps.auth_app.permissions import (
    ALLOW,
    DENY,
    PERMISSIONS,
    can_access,
)
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert
from apps.groups.models import Group
from apps.notes.models import ProgressNote
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()

# --- Permission key to URL mapping ---
# Each entry maps a permission key to a representative URL for testing.
# Keys with "skip" are not tested via URL (field-level or no view).

PERMISSION_URL_MAP = {
    # Client keys
    "client.create": {"url": "/clients/create/"},
    "client.edit": {"url": "/clients/{client_id}/edit/"},
    "client.edit_contact": {"url": "/clients/{client_id}/edit-contact/"},
    "client.view_name": {"skip": "field_level"},
    "client.view_contact": {"skip": "field_level"},
    "client.view_safety": {"skip": "field_level"},
    "client.view_medications": {"skip": "field_level"},
    "client.view_clinical": {"skip": "field_level"},
    "client.delete": {"skip": "admin_erasure_workflow"},

    # Consent / intake keys
    "consent.manage": {"url": "/clients/{client_id}/consent/edit/"},
    "consent.view": {"skip": "field_level"},
    "intake.view": {"skip": "no_decorator"},
    "intake.edit": {"skip": "no_decorator"},

    # Note keys
    "note.view": {"url": "/notes/client/{client_id}/"},
    "note.create": {"url": "/notes/client/{client_id}/quick/"},
    "note.edit": {"url": "/notes/{note_id}/cancel/"},
    "note.delete": {"skip": "no_view"},

    # Plan keys
    "plan.view": {"url": "/plans/client/{client_id}/"},
    "plan.edit": {"url": "/plans/client/{client_id}/sections/create/"},
    "plan.delete": {"skip": "no_view"},

    # Group keys
    "group.view_roster": {"url": "/groups/"},
    "group.view_detail": {"url": "/groups/{group_id}/"},
    "group.create": {"url": "/groups/create/"},
    "group.edit": {"url": "/groups/{group_id}/edit/"},
    "group.log_session": {"url": "/groups/{group_id}/session/"},
    "group.manage_members": {"url": "/groups/{group_id}/member/add/"},
    "group.manage_content": {"url": "/groups/{group_id}/milestone/"},
    "group.view_report": {"url": "/groups/{group_id}/attendance/"},

    # Event / alert keys
    "event.view": {"url": "/events/client/{client_id}/"},
    "event.create": {"url": "/events/client/{client_id}/create/"},
    "alert.view": {"skip": "implicit"},
    "alert.create": {"url": "/events/client/{client_id}/alerts/create/"},
    "alert.cancel": {"url": "/events/alerts/{alert_id}/cancel/"},
    "alert.recommend_cancel": {"url": "/events/alerts/{alert_id}/recommend-cancel/"},
    "alert.review_cancel_recommendation": {"url": "/events/alerts/recommendations/"},

    # Meeting keys
    "meeting.view": {"skip": "implicit_own_meetings"},
    "meeting.create": {"url": "/events/client/{client_id}/meetings/create/"},
    "meeting.edit": {"skip": "uses_event_create_decorator"},

    # Communication keys
    "communication.log": {"url": "/communications/client/{client_id}/quick-log/"},
    "communication.view": {"skip": "timeline_integration"},

    # Metric / report keys
    "metric.view_individual": {"url": "/reports/client/{client_id}/analysis/"},
    "metric.view_aggregate": {"skip": "view_internal"},
    "report.program_report": {"url": "/reports/export/"},
    "report.funder_report": {"url": "/reports/export/"},
    "report.data_extract": {"url": "/reports/client/{client_id}/export/"},

    # Insights
    "insights.view": {"url": "/reports/insights/"},

    # Attendance keys
    "attendance.check_in": {"skip": "view_level"},
    "attendance.view_report": {"skip": "view_level"},

    # Custom field keys
    "custom_field.view": {"skip": "per_field"},
    "custom_field.edit": {"skip": "per_field"},

    # Erasure
    "erasure.manage": {"url": "/erasure/"},

    # Admin keys — enforced by @admin_required, not permission matrix
    "user.manage": {"url": "/admin/users/", "admin_only": True},
    "settings.manage": {"url": "/admin/settings/", "admin_only": True},
    "program.manage": {"url": "/programs/create/", "admin_only": True},

    # audit.view — lives under /admin/ but middleware exempts it;
    # enforced by @requires_permission("audit.view", allow_admin=True)
    "audit.view": {"url": "/admin/audit/"},
}

ALL_ROLES = ["receptionist", "staff", "program_manager", "executive"]


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PermissionEnforcementTest(TestCase):
    """Test every permission key x role pair against the enforcement layer.

    Uses subTest() for parametrization so all failures are reported at once,
    not just the first one.
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )

        # Create one user per role, all in the same program
        self.users = {}
        for role in ALL_ROLES:
            user = User.objects.create_user(
                username=f"test_{role}",
                password="testpass123",
                display_name=f"Test {role.replace('_', ' ').title()}",
            )
            UserProgramRole.objects.create(
                user=user, program=self.program, role=role, status="active",
            )
            self.users[role] = user

        # Client enrolled in the program
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

        # Group in the program
        self.group = Group.objects.create(
            name="Test Group", program=self.program, group_type="activity",
        )

        # Alert on the client (authored by staff)
        self.alert = Alert.objects.create(
            client_file=self.client_file,
            content="Test safety alert.",
            author=self.users["staff"],
            author_program=self.program,
        )

        # Note on the client (authored by staff)
        self.note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="quick",
            author=self.users["staff"],
            author_program=self.program,
            notes_text="Test progress note.",
        )

    def tearDown(self):
        enc_module._fernet = None

    def _build_url(self, url_template):
        """Replace placeholders with real object IDs."""
        return (
            url_template
            .replace("{client_id}", str(self.client_file.pk))
            .replace("{group_id}", str(self.group.pk))
            .replace("{alert_id}", str(self.alert.pk))
            .replace("{note_id}", str(self.note.pk))
        )

    # ------------------------------------------------------------------
    # Main parametrized test
    # ------------------------------------------------------------------

    def test_permission_matrix_enforcement(self):
        """All 48 permission keys x 4 roles: DENY -> 403, others -> not 403."""
        for role in ALL_ROLES:
            user = self.users[role]
            for perm_key, config in PERMISSION_URL_MAP.items():
                with self.subTest(role=role, permission=perm_key):
                    # Skip keys without URL-based enforcement
                    if "skip" in config:
                        continue

                    # Admin-only keys: separate check
                    if config.get("admin_only"):
                        self._assert_admin_only(role, user, perm_key, config["url"])
                        continue

                    url = self._build_url(config["url"])
                    expected_level = can_access(role, perm_key)

                    self.client.login(username=user.username, password="testpass123")
                    response = self.client.get(url)
                    self.client.logout()

                    if expected_level == DENY:
                        # Executive middleware may redirect (302) instead of 403
                        self.assertIn(
                            response.status_code,
                            (403, 302),
                            f"{role} should be DENIED for {perm_key} at {url}, "
                            f"got {response.status_code}",
                        )
                    else:
                        self.assertNotIn(
                            response.status_code,
                            (403,),
                            f"{role} should NOT get 403 for {perm_key} at {url} "
                            f"(level={expected_level}), got 403",
                        )

    def _assert_admin_only(self, role, user, perm_key, url_template):
        """Admin keys: only admin users should get through."""
        url = self._build_url(url_template)
        self.client.login(username=user.username, password="testpass123")
        response = self.client.get(url)
        self.client.logout()

        # Non-admin users should always get 403 or redirect
        if not user.is_admin:
            self.assertIn(
                response.status_code,
                (403, 302),
                f"Non-admin {role} should be blocked from {perm_key} at {url}, "
                f"got {response.status_code}",
            )

    # ------------------------------------------------------------------
    # Matrix completeness checks
    # ------------------------------------------------------------------

    def test_all_permission_keys_covered(self):
        """Every key in the PERMISSIONS matrix is mapped in PERMISSION_URL_MAP."""
        all_matrix_keys = set()
        for role_perms in PERMISSIONS.values():
            all_matrix_keys.update(role_perms.keys())

        mapped_keys = set(PERMISSION_URL_MAP.keys())
        missing = all_matrix_keys - mapped_keys
        self.assertEqual(
            missing,
            set(),
            f"Permission keys in matrix but not in URL map: {sorted(missing)}",
        )

    def test_all_roles_have_same_keys(self):
        """All roles define the same set of permission keys (no gaps)."""
        all_keys = set()
        for role_perms in PERMISSIONS.values():
            all_keys.update(role_perms.keys())

        for role in ALL_ROLES:
            role_keys = set(PERMISSIONS[role].keys())
            missing = all_keys - role_keys
            with self.subTest(role=role):
                self.assertEqual(
                    missing,
                    set(),
                    f"Role '{role}' is missing keys: {sorted(missing)}",
                )

    def test_url_map_keys_exist_in_matrix(self):
        """Every key in the URL map exists in the permission matrix."""
        all_matrix_keys = set()
        for role_perms in PERMISSIONS.values():
            all_matrix_keys.update(role_perms.keys())

        for perm_key in PERMISSION_URL_MAP:
            with self.subTest(permission=perm_key):
                self.assertIn(
                    perm_key,
                    all_matrix_keys,
                    f"URL map key '{perm_key}' not found in permission matrix",
                )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminPermissionTest(TestCase):
    """Verify admin-only routes reject all non-admin users."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(
            name="Test Program", colour_hex="#10B981",
        )

        # Admin user
        self.admin = User.objects.create_user(
            username="test_admin", password="testpass123",
            display_name="Test Admin", is_admin=True,
        )
        UserProgramRole.objects.create(
            user=self.admin, program=self.program,
            role="program_manager", status="active",
        )

        # Non-admin users
        self.non_admins = {}
        for role in ALL_ROLES:
            user = User.objects.create_user(
                username=f"nonadmin_{role}",
                password="testpass123",
                display_name=f"Non-Admin {role.title()}",
            )
            UserProgramRole.objects.create(
                user=user, program=self.program, role=role, status="active",
            )
            self.non_admins[role] = user

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_access_admin_routes(self):
        """Admin user gets 200 on admin-only URLs."""
        admin_urls = [
            url_config["url"]
            for perm_key, url_config in PERMISSION_URL_MAP.items()
            if url_config.get("admin_only")
        ]
        self.client.login(username="test_admin", password="testpass123")
        for url in admin_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotIn(
                    response.status_code,
                    (403,),
                    f"Admin should access {url}, got {response.status_code}",
                )

    def test_non_admin_blocked_from_admin_routes(self):
        """Non-admin users get 403 or redirect on admin-only URLs."""
        admin_urls = [
            url_config["url"]
            for perm_key, url_config in PERMISSION_URL_MAP.items()
            if url_config.get("admin_only")
        ]
        for role, user in self.non_admins.items():
            self.client.login(username=user.username, password="testpass123")
            for url in admin_urls:
                with self.subTest(role=role, url=url):
                    response = self.client.get(url)
                    self.assertIn(
                        response.status_code,
                        (403, 302),
                        f"Non-admin {role} should be blocked from {url}, "
                        f"got {response.status_code}",
                    )
            self.client.logout()
