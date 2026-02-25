"""Tests for DV-safe mode (PERM-P5).

Covers:
- Setting and removing the DV flag
- Field hiding for receptionists when DV flag is set
- Two-person-rule for flag removal
- Front desk invisibility of the flag itself
- Tier gating (DV-safe only available at Tier 2+)
- Fail-closed behaviour
- Admin form includes is_dv_sensitive checkbox
"""
from django.test import TestCase, Client as HttpClient, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.admin_settings.models import InstanceSetting
from apps.auth_app.models import User
from apps.clients.models import (
    ClientFile,
    CustomFieldDefinition,
    CustomFieldGroup,
    ClientDetailValue,
    ClientProgramEnrolment,
    DvFlagRemovalRequest,
)
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _setup_tier(level):
    """Set the access tier InstanceSetting."""
    InstanceSetting.objects.update_or_create(
        setting_key="access_tier",
        defaults={"setting_value": str(level)},
    )


def _create_client(record_id="DV-001"):
    """Create a minimal client for testing."""
    return ClientFile.objects.create(
        _first_name_encrypted=b"", _last_name_encrypted=b"",
        record_id=record_id, status="active",
    )


def _create_custom_field(name, front_desk_access="view", is_dv_sensitive=False, group=None):
    """Create a custom field definition."""
    if group is None:
        group, _ = CustomFieldGroup.objects.get_or_create(
            title="Test Group", defaults={"sort_order": 0, "status": "active"},
        )
    return CustomFieldDefinition.objects.create(
        group=group,
        name=name,
        input_type="text",
        front_desk_access=front_desk_access,
        is_dv_sensitive=is_dv_sensitive,
        sort_order=0,
        status="active",
    )


def _create_staff_user(username="staff_user"):
    """Create a user with staff role."""
    user = User.objects.create_user(username=username, password="testpass123")
    program = Program.objects.get_or_create(name="Test Program")[0]
    UserProgramRole.objects.create(user=user, program=program, role="staff")
    return user, program


def _create_pm_user(username="pm_user"):
    """Create a user with program_manager role."""
    user = User.objects.create_user(username=username, password="testpass123")
    program = Program.objects.get_or_create(name="Test Program")[0]
    UserProgramRole.objects.create(user=user, program=program, role="program_manager")
    return user, program


def _create_receptionist_user(username="reception_user"):
    """Create a user with receptionist role."""
    user = User.objects.create_user(username=username, password="testpass123")
    program = Program.objects.get_or_create(name="Test Program")[0]
    UserProgramRole.objects.create(user=user, program=program, role="receptionist")
    return user, program


# ─── Model Tests ───────────────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvFlagModelTest(TestCase):
    """Tests for the is_dv_safe field on ClientFile."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def test_default_is_false(self):
        """New clients have is_dv_safe=False by default."""
        client = _create_client()
        self.assertFalse(client.is_dv_safe)

    def test_can_set_true(self):
        """is_dv_safe can be set to True."""
        client = _create_client()
        client.is_dv_safe = True
        client.save(update_fields=["is_dv_safe"])
        client.refresh_from_db()
        self.assertTrue(client.is_dv_safe)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvSensitiveFieldTest(TestCase):
    """Tests for the is_dv_sensitive field on CustomFieldDefinition."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def test_default_is_false(self):
        """New custom fields have is_dv_sensitive=False by default."""
        field = _create_custom_field("Phone Number")
        self.assertFalse(field.is_dv_sensitive)

    def test_can_set_true(self):
        """is_dv_sensitive can be set to True."""
        field = _create_custom_field("Address", is_dv_sensitive=True)
        self.assertTrue(field.is_dv_sensitive)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvFlagRemovalRequestModelTest(TestCase):
    """Tests for the DvFlagRemovalRequest model."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff, _ = _create_staff_user()
        self.client_file = _create_client()
        self.client_file.is_dv_safe = True
        self.client_file.save(update_fields=["is_dv_safe"])

    def test_create_pending_request(self):
        """A new removal request has approved=None (pending)."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.staff,
            reason="Situation resolved",
        )
        self.assertIsNone(req.approved)
        self.assertTrue(req.is_pending)

    def test_approve_request(self):
        """Approving a request sets approved=True."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.staff,
            reason="Situation resolved",
        )
        req.approved = True
        req.save()
        self.assertTrue(req.approved)
        self.assertFalse(req.is_pending)


# ─── Field Hiding Tests ───────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvFieldHidingTest(TestCase):
    """Tests that DV-sensitive custom fields are hidden from receptionists."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.receptionist, self.program = _create_receptionist_user()
        self.staff, _ = _create_staff_user("staff2")
        self.client_file = _create_client()

        # Enrol client in program
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

        # Create custom fields — one DV-sensitive, one not
        self.group = CustomFieldGroup.objects.create(
            title="Contact Info", sort_order=0, status="active",
        )
        self.address_field = _create_custom_field(
            "Address", front_desk_access="view", is_dv_sensitive=True, group=self.group,
        )
        self.phone_field = _create_custom_field(
            "Alt Phone", front_desk_access="view", is_dv_sensitive=False, group=self.group,
        )

        # Set values
        ClientDetailValue.objects.create(
            client_file=self.client_file, field_def=self.address_field, value="123 Main St",
        )
        ClientDetailValue.objects.create(
            client_file=self.client_file, field_def=self.phone_field, value="555-1234",
        )

    def test_receptionist_sees_both_without_dv_flag(self):
        """Without DV flag, receptionist sees all allowed fields."""
        from apps.clients.views import _get_custom_fields_context
        ctx = _get_custom_fields_context(self.client_file, "receptionist", hide_empty=False)
        field_names = [
            f["field_def"].name
            for group_data in ctx["custom_data"]
            for f in group_data["fields"]
        ]
        self.assertIn("Address", field_names)
        self.assertIn("Alt Phone", field_names)

    def test_receptionist_hides_dv_sensitive_with_flag(self):
        """With DV flag, receptionist cannot see DV-sensitive fields."""
        self.client_file.is_dv_safe = True
        self.client_file.save(update_fields=["is_dv_safe"])

        from apps.clients.views import _get_custom_fields_context
        ctx = _get_custom_fields_context(self.client_file, "receptionist", hide_empty=False)
        field_names = [
            f["field_def"].name
            for group_data in ctx["custom_data"]
            for f in group_data["fields"]
        ]
        self.assertNotIn("Address", field_names)
        self.assertIn("Alt Phone", field_names)

    def test_staff_sees_all_with_dv_flag(self):
        """DV flag has no effect on staff visibility — they see everything."""
        self.client_file.is_dv_safe = True
        self.client_file.save(update_fields=["is_dv_safe"])

        from apps.clients.views import _get_custom_fields_context
        ctx = _get_custom_fields_context(self.client_file, "staff", hide_empty=False)
        field_names = [
            f["field_def"].name
            for group_data in ctx["custom_data"]
            for f in group_data["fields"]
        ]
        self.assertIn("Address", field_names)
        self.assertIn("Alt Phone", field_names)


# ─── Enable View Tests ────────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvSafeEnableViewTest(TestCase):
    """Tests for setting the DV safety flag."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.staff, self.program = _create_staff_user()
        self.pm, _ = _create_pm_user()
        self.receptionist, _ = _create_receptionist_user()
        self.client_file = _create_client()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def test_staff_can_enable_at_tier_2(self):
        """Staff can enable DV flag at Tier 2."""
        _setup_tier(2)
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/enable/",
        )
        self.assertEqual(resp.status_code, 302)
        self.client_file.refresh_from_db()
        self.assertTrue(self.client_file.is_dv_safe)

    def test_pm_can_enable_at_tier_3(self):
        """PM can enable DV flag at Tier 3."""
        _setup_tier(3)
        self.http_client.login(username="pm_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/enable/",
        )
        self.assertEqual(resp.status_code, 302)
        self.client_file.refresh_from_db()
        self.assertTrue(self.client_file.is_dv_safe)

    def test_receptionist_cannot_enable(self):
        """Receptionist cannot enable DV flag."""
        _setup_tier(2)
        self.http_client.login(username="reception_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/enable/",
        )
        self.assertEqual(resp.status_code, 403)
        self.client_file.refresh_from_db()
        self.assertFalse(self.client_file.is_dv_safe)

    def test_blocked_at_tier_1(self):
        """DV enable is blocked at Tier 1."""
        _setup_tier(1)
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/enable/",
        )
        self.assertEqual(resp.status_code, 403)

    def test_get_method_not_allowed(self):
        """GET to the enable URL returns 403."""
        _setup_tier(2)
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.get(
            f"/participants/{self.client_file.pk}/dv-safe/enable/",
        )
        self.assertEqual(resp.status_code, 403)

    def test_enable_creates_audit_log(self):
        """Enabling DV flag creates an audit log entry."""
        from apps.audit.models import AuditLog
        _setup_tier(2)
        self.http_client.login(username="staff_user", password="testpass123")
        self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/enable/",
        )
        logs = AuditLog.objects.using("audit").filter(
            resource_type="dv_safe_flag", action="create",
        )
        self.assertEqual(logs.count(), 1)


# ─── Removal Workflow Tests ───────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvSafeRemovalWorkflowTest(TestCase):
    """Tests for the two-person-rule DV flag removal workflow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.staff, self.program = _create_staff_user()
        self.pm, _ = _create_pm_user()
        self.client_file = _create_client()
        self.client_file.is_dv_safe = True
        self.client_file.save(update_fields=["is_dv_safe"])
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )
        _setup_tier(2)

    def test_staff_can_request_removal(self):
        """Staff can submit a removal request."""
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/request-remove/",
            {"reason": "Situation has been resolved"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(DvFlagRemovalRequest.objects.count(), 1)

        req = DvFlagRemovalRequest.objects.first()
        self.assertTrue(req.is_pending)
        # Flag should still be set until PM approves
        self.client_file.refresh_from_db()
        self.assertTrue(self.client_file.is_dv_safe)

    def test_duplicate_request_blocked(self):
        """Cannot create a second removal request while one is pending."""
        DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.staff,
            reason="First request",
        )
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/request-remove/",
            {"reason": "Second request"},
        )
        self.assertEqual(resp.status_code, 302)
        # Still only one request
        self.assertEqual(DvFlagRemovalRequest.objects.count(), 1)

    def test_pm_can_approve_removal(self):
        """PM approving a request removes the DV flag."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.staff,
            reason="Situation resolved",
        )
        self.http_client.login(username="pm_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/review-remove/{req.pk}/",
            {"action": "approve", "review_note": "Confirmed safe"},
        )
        self.assertEqual(resp.status_code, 302)

        req.refresh_from_db()
        self.assertTrue(req.approved)
        self.client_file.refresh_from_db()
        self.assertFalse(self.client_file.is_dv_safe)

    def test_pm_can_reject_removal(self):
        """PM rejecting a request keeps the DV flag active."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.staff,
            reason="Situation resolved",
        )
        self.http_client.login(username="pm_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/review-remove/{req.pk}/",
            {"action": "reject", "review_note": "Not yet safe"},
        )
        self.assertEqual(resp.status_code, 302)

        req.refresh_from_db()
        self.assertFalse(req.approved)
        self.client_file.refresh_from_db()
        self.assertTrue(self.client_file.is_dv_safe)

    def test_staff_cannot_approve(self):
        """Staff cannot approve removal — only PM+."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.staff,
            reason="Situation resolved",
        )
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/review-remove/{req.pk}/",
            {"action": "approve"},
        )
        self.assertEqual(resp.status_code, 403)
        # Flag still active
        self.client_file.refresh_from_db()
        self.assertTrue(self.client_file.is_dv_safe)

    def test_approval_creates_audit_log(self):
        """Approving removal creates an audit log entry."""
        from apps.audit.models import AuditLog
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.staff,
            reason="Situation resolved",
        )
        self.http_client.login(username="pm_user", password="testpass123")
        self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/review-remove/{req.pk}/",
            {"action": "approve"},
        )
        logs = AuditLog.objects.using("audit").filter(
            resource_type="dv_safe_flag", action="update",
        )
        self.assertEqual(logs.count(), 1)


# ─── Front Desk Invisibility Tests ────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvFrontDeskInvisibilityTest(TestCase):
    """Tests that front desk cannot see any DV-related UI."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.receptionist, self.program = _create_receptionist_user()
        self.client_file = _create_client()
        self.client_file.is_dv_safe = True
        self.client_file.save(update_fields=["is_dv_safe"])
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )
        _setup_tier(2)

    def test_receptionist_cannot_see_dv_section(self):
        """Receptionist does not see the DV Safety section on client detail."""
        self.http_client.login(username="reception_user", password="testpass123")
        resp = self.http_client.get(f"/participants/{self.client_file.pk}/")
        self.assertNotContains(resp, "DV Safety")
        self.assertNotContains(resp, "dv-safe")

    def test_receptionist_cannot_enable_dv_flag(self):
        """Receptionist gets 403 when trying to enable DV flag."""
        self.http_client.login(username="reception_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/enable/",
        )
        self.assertEqual(resp.status_code, 403)


# ─── Tier Gating Tests ────────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvTierGatingTest(TestCase):
    """Tests that DV-safe controls are gated by access tier."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.staff, self.program = _create_staff_user()
        self.client_file = _create_client()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def test_dv_section_hidden_at_tier_1(self):
        """DV Safety section not shown at Tier 1."""
        _setup_tier(1)
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.get(f"/participants/{self.client_file.pk}/")
        self.assertNotContains(resp, "DV Safety")

    def test_dv_section_shown_at_tier_2(self):
        """DV Safety section shown at Tier 2 for staff."""
        _setup_tier(2)
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.get(f"/participants/{self.client_file.pk}/")
        self.assertContains(resp, "DV Safety")

    def test_dv_section_shown_at_tier_3(self):
        """DV Safety section shown at Tier 3 for staff."""
        _setup_tier(3)
        self.http_client.login(username="staff_user", password="testpass123")
        resp = self.http_client.get(f"/participants/{self.client_file.pk}/")
        self.assertContains(resp, "DV Safety")


# ─── Admin Form Tests ─────────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvCustomFieldAdminTest(TestCase):
    """Tests that the custom field admin form includes is_dv_sensitive."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

    def test_form_includes_dv_sensitive(self):
        """CustomFieldDefinitionForm includes the is_dv_sensitive field."""
        from apps.clients.forms import CustomFieldDefinitionForm
        form = CustomFieldDefinitionForm()
        self.assertIn("is_dv_sensitive", form.fields)

    def test_create_field_with_dv_sensitive(self):
        """Admin can create a field with is_dv_sensitive=True."""
        group = CustomFieldGroup.objects.create(
            title="Test Group", sort_order=0, status="active",
        )
        from apps.clients.forms import CustomFieldDefinitionForm
        form = CustomFieldDefinitionForm(data={
            "group": group.pk,
            "name": "Emergency Contact",
            "input_type": "text",
            "front_desk_access": "view",
            "is_dv_sensitive": True,
            "sort_order": 0,
            "status": "active",
            "options_json": "[]",
        })
        self.assertTrue(form.is_valid(), form.errors)
        field = form.save()
        self.assertTrue(field.is_dv_sensitive)


# ─── Self-Approval Tests ──────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvSelfApprovalTest(TestCase):
    """Tests that the same person cannot request and approve DV flag removal."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.pm, self.program = _create_pm_user()
        self.other_pm, _ = _create_pm_user("other_pm")
        self.staff, _ = _create_staff_user()
        self.client_file = _create_client()
        self.client_file.is_dv_safe = True
        self.client_file.save(update_fields=["is_dv_safe"])
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )
        _setup_tier(2)

    def test_requester_cannot_approve_own_request(self):
        """PM who requested removal cannot approve their own request."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.pm,
            reason="Situation resolved",
        )
        self.http_client.login(username="pm_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/review-remove/{req.pk}/",
            {"action": "approve", "review_note": "Self-approving"},
        )
        self.assertEqual(resp.status_code, 403)
        # Flag should still be active
        self.client_file.refresh_from_db()
        self.assertTrue(self.client_file.is_dv_safe)

    def test_different_pm_can_approve(self):
        """A different PM can approve a removal request."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.pm,
            reason="Situation resolved",
        )
        self.http_client.login(username="other_pm", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/review-remove/{req.pk}/",
            {"action": "approve", "review_note": "Confirmed safe"},
        )
        self.assertEqual(resp.status_code, 302)
        self.client_file.refresh_from_db()
        self.assertFalse(self.client_file.is_dv_safe)

    def test_requester_cannot_reject_own_request(self):
        """PM who requested removal cannot reject their own request either."""
        req = DvFlagRemovalRequest.objects.create(
            client_file=self.client_file,
            requested_by=self.pm,
            reason="Situation resolved",
        )
        self.http_client.login(username="pm_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/dv-safe/review-remove/{req.pk}/",
            {"action": "reject"},
        )
        self.assertEqual(resp.status_code, 403)
        # Request should still be pending
        req.refresh_from_db()
        self.assertTrue(req.is_pending)


# ─── Save-Side Enforcement Tests ──────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DvSaveSideEnforcementTest(TestCase):
    """Tests that receptionists cannot save DV-sensitive field values for DV-safe clients."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = HttpClient()
        self.receptionist, self.program = _create_receptionist_user()
        self.client_file = _create_client()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

        # Create custom fields — one DV-sensitive editable, one normal editable
        # Use generic names to avoid auto-detected validation_type (phone, postal_code)
        self.group = CustomFieldGroup.objects.create(
            title="Contact Info", sort_order=0, status="active",
        )
        self.sensitive_field = _create_custom_field(
            "Secret Info", front_desk_access="edit", is_dv_sensitive=True, group=self.group,
        )
        self.normal_field = _create_custom_field(
            "Favourite Colour", front_desk_access="edit", is_dv_sensitive=False, group=self.group,
        )
        _setup_tier(2)

    def test_receptionist_cannot_save_dv_sensitive_field(self):
        """Receptionist POST of DV-sensitive field value is silently ignored for DV-safe client."""
        self.client_file.is_dv_safe = True
        self.client_file.save(update_fields=["is_dv_safe"])

        self.http_client.login(username="reception_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/custom-fields/",
            {
                f"custom_{self.sensitive_field.pk}": "Secret value",
                f"custom_{self.normal_field.pk}": "Blue",
            },
        )
        # Should succeed (redirect or 200) but only save the non-sensitive field
        self.assertIn(resp.status_code, [200, 302])

        from apps.clients.models import ClientDetailValue
        # DV-sensitive field should NOT have been saved
        sensitive_val = ClientDetailValue.objects.filter(
            client_file=self.client_file, field_def=self.sensitive_field,
        ).first()
        self.assertIsNone(sensitive_val)

        # Normal field SHOULD have been saved
        normal_val = ClientDetailValue.objects.filter(
            client_file=self.client_file, field_def=self.normal_field,
        ).first()
        self.assertIsNotNone(normal_val)
        self.assertEqual(normal_val.value, "Blue")

    def test_receptionist_can_save_without_dv_flag(self):
        """Without DV flag, receptionist can save both fields normally."""
        self.http_client.login(username="reception_user", password="testpass123")
        resp = self.http_client.post(
            f"/participants/{self.client_file.pk}/custom-fields/",
            {
                f"custom_{self.sensitive_field.pk}": "Some value",
                f"custom_{self.normal_field.pk}": "Red",
            },
        )
        self.assertIn(resp.status_code, [200, 302])

        from apps.clients.models import ClientDetailValue
        # Both fields should be saved
        sensitive_val = ClientDetailValue.objects.filter(
            client_file=self.client_file, field_def=self.sensitive_field,
        ).first()
        self.assertIsNotNone(sensitive_val)
        self.assertEqual(sensitive_val.value, "Some value")

        normal_val = ClientDetailValue.objects.filter(
            client_file=self.client_file, field_def=self.normal_field,
        ).first()
        self.assertIsNotNone(normal_val)
        self.assertEqual(normal_val.value, "Red")
