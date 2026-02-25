"""Tests for GATED clinical access (PERM-P6)."""
from datetime import timedelta

from django.test import TestCase, Client as HttpClient, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.admin_settings.models import InstanceSetting
from apps.auth_app.models import AccessGrant, AccessGrantReason, User
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _setup_tier3():
    """Set access tier to 3 (Clinical Safeguards)."""
    InstanceSetting.objects.update_or_create(
        setting_key="access_tier",
        defaults={"setting_value": "3"},
    )


def _create_reason(label="Clinical supervision"):
    """Create and return an active AccessGrantReason."""
    return AccessGrantReason.objects.get_or_create(
        label=label,
        defaults={"is_active": True, "sort_order": 1},
    )[0]


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessGrantModelTest(TestCase):
    """Tests for the AccessGrant model."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="pm", password="testpass123",
        )
        self.program = Program.objects.create(name="Test Program")
        self.reason = _create_reason()

    def test_is_valid_when_active_and_not_expired(self):
        grant = AccessGrant.objects.create(
            user=self.user,
            program=self.program,
            reason=self.reason,
            justification="Supervision review",
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertTrue(grant.is_valid)

    def test_is_expired_when_past_expiry(self):
        grant = AccessGrant.objects.create(
            user=self.user,
            program=self.program,
            reason=self.reason,
            justification="Supervision review",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(grant.is_expired)
        self.assertFalse(grant.is_valid)

    def test_is_not_valid_when_revoked(self):
        grant = AccessGrant.objects.create(
            user=self.user,
            program=self.program,
            reason=self.reason,
            justification="Supervision review",
            expires_at=timezone.now() + timedelta(days=7),
            is_active=False,
        )
        self.assertFalse(grant.is_valid)

    def test_str_representation(self):
        grant = AccessGrant.objects.create(
            user=self.user,
            program=self.program,
            reason=self.reason,
            justification="Test",
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.assertIn("program", str(grant))


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessGrantReasonTest(TestCase):
    """Tests for the configurable AccessGrantReason model."""

    def setUp(self):
        enc_module._fernet = None

    def test_default_reasons_exist_after_seed(self):
        """Default reasons are created by the data migration."""
        # Simulate what the seed migration does
        defaults = [
            "Clinical supervision",
            "Complaint investigation",
            "Safety concern",
            "Quality assurance",
            "Intake / case assignment",
        ]
        for label in defaults:
            AccessGrantReason.objects.get_or_create(
                label=label, defaults={"is_active": True}
            )
        self.assertEqual(AccessGrantReason.objects.filter(is_active=True).count(), 5)

    def test_deactivated_reason_not_shown(self):
        reason = _create_reason("Old reason")
        reason.is_active = False
        reason.save()
        active = AccessGrantReason.objects.filter(is_active=True)
        self.assertNotIn(reason, active)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GatedDecoratorTest(TestCase):
    """Tests that the decorator handles GATED correctly at different tiers."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.pm = User.objects.create_user(
            username="pm", password="testpass123",
        )
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role="program_manager",
        )
        self.reason = _create_reason()

    def test_tier_1_allows_pm_without_grant(self):
        """At Tier 1, GATED is relaxed to ALLOW — PM can view notes freely."""
        InstanceSetting.objects.update_or_create(
            setting_key="access_tier",
            defaults={"setting_value": "1"},
        )
        self.http_client.login(username="pm", password="testpass123")

        # note.view is GATED for PM, but Tier 1 relaxes it
        # Access note_list for a client — we need a client for this
        from apps.clients.models import ClientFile
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-001", status="active",
        )
        # Create enrolment
        from apps.clients.models import ClientProgramEnrolment
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        resp = self.http_client.get(f"/notes/participant/{client.pk}/")
        # Should get 200 (access granted) not a redirect
        self.assertEqual(resp.status_code, 200)

    def test_tier_2_allows_pm_without_grant(self):
        """At Tier 2, GATED is relaxed to ALLOW."""
        InstanceSetting.objects.update_or_create(
            setting_key="access_tier",
            defaults={"setting_value": "2"},
        )
        self.http_client.login(username="pm", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-002", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        resp = self.http_client.get(f"/notes/participant/{client.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_tier_3_redirects_pm_without_grant(self):
        """At Tier 3, PM without an active grant is redirected to justification form."""
        _setup_tier3()
        self.http_client.login(username="pm", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-003", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        resp = self.http_client.get(f"/notes/participant/{client.pk}/")
        # Should redirect to the justification form
        self.assertEqual(resp.status_code, 302)
        self.assertIn("access-grant/request", resp.url)
        self.assertIn("note.view", resp.url)

    def test_tier_3_allows_pm_with_active_grant(self):
        """At Tier 3, PM with a valid grant can access clinical data."""
        _setup_tier3()
        self.http_client.login(username="pm", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-004", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        # Create an active program-level grant
        AccessGrant.objects.create(
            user=self.pm,
            program=self.program,
            reason=self.reason,
            justification="Supervision",
            expires_at=timezone.now() + timedelta(days=7),
        )

        resp = self.http_client.get(f"/notes/participant/{client.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_tier_3_denies_pm_with_expired_grant(self):
        """At Tier 3, an expired grant does not provide access."""
        _setup_tier3()
        self.http_client.login(username="pm", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-005", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        AccessGrant.objects.create(
            user=self.pm,
            program=self.program,
            reason=self.reason,
            justification="Supervision",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        resp = self.http_client.get(f"/notes/participant/{client.pk}/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("access-grant/request", resp.url)

    def test_tier_3_denies_pm_with_revoked_grant(self):
        """At Tier 3, a revoked (is_active=False) grant does not provide access."""
        _setup_tier3()
        self.http_client.login(username="pm", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-006", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        AccessGrant.objects.create(
            user=self.pm,
            program=self.program,
            reason=self.reason,
            justification="Supervision",
            expires_at=timezone.now() + timedelta(days=7),
            is_active=False,
        )

        resp = self.http_client.get(f"/notes/participant/{client.pk}/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("access-grant/request", resp.url)

    def test_staff_unaffected_by_gated(self):
        """Staff role has PROGRAM (not GATED) for note.view — unaffected."""
        _setup_tier3()
        staff = User.objects.create_user(
            username="staff_user", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=staff, program=self.program, role="staff",
        )
        self.http_client.login(username="staff_user", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-007", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        resp = self.http_client.get(f"/notes/participant/{client.pk}/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessGrantFormTest(TestCase):
    """Tests for the justification (grant request) form submission."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.pm = User.objects.create_user(
            username="pm", password="testpass123",
        )
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role="program_manager",
        )
        self.reason = _create_reason()
        _setup_tier3()

    def test_grant_request_form_renders(self):
        """GET to the grant request page returns 200 with form."""
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/auth/access-grant/request/?next=/clients/1/notes/&permission=note.view")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Request Clinical Access")

    def test_grant_request_creates_grant(self):
        """POST with valid data creates an AccessGrant."""
        self.http_client.login(username="pm", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-010", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        resp = self.http_client.post("/auth/access-grant/request/", {
            "next": f"/notes/participant/{client.pk}/",
            "permission": "note.view",
            "reason": self.reason.pk,
            "justification": "Need to review supervision notes",
            "duration_days": "7",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AccessGrant.objects.count(), 1)

        grant = AccessGrant.objects.first()
        self.assertEqual(grant.user, self.pm)
        self.assertEqual(grant.program, self.program)
        self.assertTrue(grant.is_valid)

    def test_grant_request_creates_audit_log(self):
        """Creating a grant writes an audit log entry."""
        from apps.audit.models import AuditLog

        self.http_client.login(username="pm", password="testpass123")

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        client = ClientFile.objects.create(
            _first_name_encrypted=b"", _last_name_encrypted=b"",
            record_id="T-011", status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=client, program=self.program,
        )

        self.http_client.post("/auth/access-grant/request/", {
            "next": f"/notes/participant/{client.pk}/",
            "permission": "note.view",
            "reason": self.reason.pk,
            "justification": "Need to review supervision notes",
            "duration_days": "7",
        })

        logs = AuditLog.objects.using("audit").filter(
            resource_type="access_grant",
            action="create",
        )
        self.assertEqual(logs.count(), 1)
        self.assertIn("note.view", logs.first().new_values["permission_key"])

    def test_grant_request_blocked_at_tier_1(self):
        """The grant request page returns 403 at Tier 1."""
        InstanceSetting.objects.update_or_create(
            setting_key="access_tier",
            defaults={"setting_value": "1"},
        )
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/auth/access-grant/request/")
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessGrantListViewTest(TestCase):
    """Tests for the user's grant list and revocation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.pm = User.objects.create_user(
            username="pm", password="testpass123",
        )
        self.program = Program.objects.create(name="Test Program")
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role="program_manager",
        )
        self.reason = _create_reason()

    def test_grant_list_shows_active_grants(self):
        """Active grants appear in the list."""
        AccessGrant.objects.create(
            user=self.pm,
            program=self.program,
            reason=self.reason,
            justification="Supervision",
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/auth/access-grants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Program")
        self.assertContains(resp, "Revoke")

    def test_revoke_deactivates_grant(self):
        """Revoking a grant sets is_active=False."""
        grant = AccessGrant.objects.create(
            user=self.pm,
            program=self.program,
            reason=self.reason,
            justification="Supervision",
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.post(f"/auth/access-grants/{grant.pk}/revoke/")
        self.assertEqual(resp.status_code, 302)

        grant.refresh_from_db()
        self.assertFalse(grant.is_active)

    def test_revoke_creates_audit_log(self):
        """Revoking a grant writes an audit log entry."""
        from apps.audit.models import AuditLog

        grant = AccessGrant.objects.create(
            user=self.pm,
            program=self.program,
            reason=self.reason,
            justification="Supervision",
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.http_client.login(username="pm", password="testpass123")
        self.http_client.post(f"/auth/access-grants/{grant.pk}/revoke/")

        logs = AuditLog.objects.using("audit").filter(
            resource_type="access_grant",
            action="update",
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().new_values["action"], "revoked")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AccessGrantAdminViewTest(TestCase):
    """Tests for the admin grant list and reasons management."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.pm = User.objects.create_user(
            username="pm", password="testpass123",
        )
        self.program = Program.objects.create(name="Test Program")
        self.reason = _create_reason()
        _setup_tier3()

    def test_admin_grant_list_shows_all_grants(self):
        """Admin can see grants from all users."""
        AccessGrant.objects.create(
            user=self.pm,
            program=self.program,
            reason=self.reason,
            justification="Supervision",
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/admin/settings/access-grants/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Program")

    def test_admin_grant_list_blocked_at_tier_1(self):
        """Admin grant list returns 403 at lower tiers."""
        InstanceSetting.objects.update_or_create(
            setting_key="access_tier",
            defaults={"setting_value": "1"},
        )
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/admin/settings/access-grants/")
        self.assertEqual(resp.status_code, 403)

    def test_non_admin_cannot_access_admin_views(self):
        """Non-admin users get 403 on admin grant views."""
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role="program_manager",
        )
        self.http_client.login(username="pm", password="testpass123")
        resp = self.http_client.get("/admin/settings/access-grants/")
        self.assertEqual(resp.status_code, 403)

    def test_reasons_page_renders(self):
        """Reasons admin page shows the default reason."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/admin/settings/access-grant-reasons/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Clinical supervision")

    def test_add_reason(self):
        """Admin can add a new reason."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post("/admin/settings/access-grant-reasons/", {
            "action": "add",
            "label": "Program audit",
            "label_fr": "Audit de programme",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            AccessGrantReason.objects.filter(label="Program audit").exists()
        )

    def test_toggle_reason(self):
        """Admin can deactivate a reason."""
        self.http_client.login(username="admin", password="testpass123")
        self.http_client.post("/admin/settings/access-grant-reasons/", {
            "action": "toggle",
            "reason_id": str(self.reason.pk),
        })
        self.reason.refresh_from_db()
        self.assertFalse(self.reason.is_active)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DashboardGrantCardsTest(TestCase):
    """Tests that dashboard shows grant cards at Tier 3."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

    def test_no_grant_cards_at_tier_1(self):
        """Grant cards are not shown at Tier 1."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/admin/settings/")
        self.assertNotContains(resp, "Clinical Access Grants")
        self.assertNotContains(resp, "Access Grant Reasons")

    def test_grant_cards_at_tier_3(self):
        """Grant cards appear on dashboard at Tier 3."""
        _setup_tier3()
        _create_reason()
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/admin/settings/")
        self.assertContains(resp, "Clinical Access Grants")
        self.assertContains(resp, "Access Grant Reasons")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConfigurableDurationTest(TestCase):
    """Tests for configurable grant duration settings."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.reason = _create_reason()

    def test_default_duration_is_7(self):
        """Without any InstanceSetting, default duration is 7 days."""
        from apps.auth_app.forms import AccessGrantForm
        form = AccessGrantForm()
        self.assertEqual(form.fields["duration_days"].initial, 7)

    def test_custom_default_duration(self):
        """Custom default_days setting changes the initial value."""
        InstanceSetting.objects.create(
            setting_key="access_grant_default_days",
            setting_value="14",
        )
        from apps.auth_app.forms import AccessGrantForm
        form = AccessGrantForm()
        self.assertEqual(form.fields["duration_days"].initial, 14)

    def test_custom_max_days_filters_choices(self):
        """Max days setting removes choices that exceed the maximum."""
        InstanceSetting.objects.create(
            setting_key="access_grant_max_days",
            setting_value="7",
        )
        from apps.auth_app.forms import AccessGrantForm
        form = AccessGrantForm()
        choice_values = [val for val, _ in form.fields["duration_days"].choices]
        self.assertNotIn(14, choice_values)
        self.assertNotIn(30, choice_values)
        self.assertIn(7, choice_values)

    def test_validation_rejects_over_max(self):
        """Submitting a duration over max_days is rejected."""
        InstanceSetting.objects.create(
            setting_key="access_grant_max_days",
            setting_value="7",
        )
        from apps.auth_app.forms import AccessGrantForm
        form = AccessGrantForm(data={
            "reason": self.reason.pk,
            "justification": "Testing",
            "duration_days": "30",
        })
        self.assertFalse(form.is_valid())
