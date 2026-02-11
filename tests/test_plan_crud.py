"""Tests for Plan CRUD — sections, targets, metrics, and RBAC enforcement."""
from cryptography.fernet import Fernet
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
    PlanTargetRevision,
)
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PlanCRUDBaseTest(TestCase):
    """Base class with shared setUp for plan CRUD tests."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        # Users
        self.admin = User.objects.create_user(
            username="admin", password="pass", display_name="Admin", is_admin=True,
        )
        self.manager = User.objects.create_user(
            username="manager", password="pass", display_name="Manager"
        )
        self.counsellor = User.objects.create_user(
            username="counsellor", password="pass", display_name="Direct Service"
        )
        self.other_manager = User.objects.create_user(
            username="other_mgr", password="pass", display_name="Other Manager"
        )

        # Programs
        self.program = Program.objects.create(name="Housing Support")
        self.other_program = Program.objects.create(name="Youth Services")

        # Roles
        UserProgramRole.objects.create(
            user=self.manager, program=self.program, role="program_manager", status="active"
        )
        UserProgramRole.objects.create(
            user=self.counsellor, program=self.program, role="staff", status="active"
        )
        UserProgramRole.objects.create(
            user=self.other_manager, program=self.other_program, role="program_manager", status="active"
        )

        # Client enrolled in program
        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )

    def tearDown(self):
        enc_module._fernet = None


class SectionCreateTest(PlanCRUDBaseTest):
    """Test creating plan sections with RBAC checks.

    Per the permissions matrix: staff has plan.edit: SCOPED (can create sections),
    program_manager has plan.edit: DENY (cannot create sections).
    """

    def test_counsellor_can_create_section(self):
        """Staff has plan.edit: SCOPED per permissions matrix — can create sections."""
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:section_create", args=[self.client_file.pk])
        resp = self.http.post(url, {
            "name": "Employment Goals",
            "sort_order": 0,
        })
        # Should redirect on success
        self.assertIn(resp.status_code, [200, 302])
        self.assertTrue(PlanSection.objects.filter(name="Employment Goals").exists())

    def test_manager_cannot_create_section(self):
        """Program manager has plan.edit: DENY per permissions matrix."""
        self.http.login(username="manager", password="pass")
        url = reverse("plans:section_create", args=[self.client_file.pk])
        resp = self.http.post(url, {
            "name": "Should Not Work",
            "sort_order": 0,
        })
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(PlanSection.objects.filter(name="Should Not Work").exists())

    def test_other_program_manager_cannot_create_section(self):
        """Manager of a different program cannot edit this client's plan."""
        self.http.login(username="other_mgr", password="pass")
        url = reverse("plans:section_create", args=[self.client_file.pk])
        resp = self.http.post(url, {
            "name": "Should Not Work",
            "sort_order": 0,
        })
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_redirected(self):
        url = reverse("plans:section_create", args=[self.client_file.pk])
        resp = self.http.post(url, {"name": "Test", "sort_order": 0})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)


class SectionEditTest(PlanCRUDBaseTest):
    """Test editing plan sections.

    Per the permissions matrix: staff has plan.edit: SCOPED (can edit sections),
    program_manager has plan.edit: DENY (cannot edit sections).
    """

    def setUp(self):
        super().setUp()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Original Section",
            program=self.program, sort_order=0,
        )

    def test_counsellor_can_edit_section(self):
        """Staff has plan.edit: SCOPED per permissions matrix — can edit sections."""
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:section_edit", args=[self.section.pk])
        resp = self.http.post(url, {
            "name": "Updated Section",
            "sort_order": 1,
        })
        self.assertEqual(resp.status_code, 200)  # Returns partial HTML
        self.section.refresh_from_db()
        self.assertEqual(self.section.name, "Updated Section")

    def test_manager_cannot_edit_section(self):
        """Program manager has plan.edit: DENY per permissions matrix."""
        self.http.login(username="manager", password="pass")
        url = reverse("plans:section_edit", args=[self.section.pk])
        resp = self.http.post(url, {
            "name": "Hacked Section",
            "sort_order": 0,
        })
        self.assertEqual(resp.status_code, 403)
        self.section.refresh_from_db()
        self.assertEqual(self.section.name, "Original Section")


class SectionStatusTest(PlanCRUDBaseTest):
    """Test changing section status.

    Per the permissions matrix: staff has plan.edit: SCOPED (can change status),
    program_manager has plan.edit: DENY (cannot change status).
    """

    def setUp(self):
        super().setUp()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Active Section",
            program=self.program,
        )

    def test_counsellor_can_change_section_status(self):
        """Staff has plan.edit: SCOPED per permissions matrix — can change section status."""
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:section_status", args=[self.section.pk])
        resp = self.http.post(url, {
            "status": "completed",
            "status_reason": "All targets met",
        })
        self.assertEqual(resp.status_code, 200)
        self.section.refresh_from_db()
        self.assertEqual(self.section.status, "completed")

    def test_manager_cannot_change_section_status(self):
        """Program manager has plan.edit: DENY per permissions matrix."""
        self.http.login(username="manager", password="pass")
        url = reverse("plans:section_status", args=[self.section.pk])
        resp = self.http.post(url, {
            "status": "deactivated",
            "status_reason": "Should fail",
        })
        self.assertEqual(resp.status_code, 403)
        self.section.refresh_from_db()
        self.assertEqual(self.section.status, "default")


class TargetCreateTest(PlanCRUDBaseTest):
    """Test creating plan targets.

    Per the permissions matrix: staff has plan.edit: SCOPED (can create targets),
    program_manager has plan.edit: DENY (cannot create targets).
    """
    databases = ("default", "audit")

    def setUp(self):
        super().setUp()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Section", program=self.program,
        )

    def test_counsellor_can_create_target(self):
        """Staff has plan.edit: SCOPED per permissions matrix — can create targets."""
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:target_create", args=[self.section.pk])
        resp = self.http.post(url, {
            "name": "Find stable housing",
            "description": "Client will find stable housing within 3 months",
        })
        self.assertEqual(resp.status_code, 302)
        # name is an encrypted property — can't query by it, so fetch by section
        target = PlanTarget.objects.get(plan_section=self.section)
        self.assertEqual(target.name, "Find stable housing")
        self.assertEqual(target.plan_section, self.section)
        self.assertEqual(target.client_file, self.client_file)
        # Should create an initial revision
        self.assertEqual(
            PlanTargetRevision.objects.filter(plan_target=target).count(), 1
        )

    def test_manager_cannot_create_target(self):
        """Program manager has plan.edit: DENY per permissions matrix."""
        self.http.login(username="manager", password="pass")
        url = reverse("plans:target_create", args=[self.section.pk])
        resp = self.http.post(url, {
            "name": "Should fail",
            "description": "",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(PlanTarget.objects.count(), 0)


class TargetEditTest(PlanCRUDBaseTest):
    """Test editing targets and revision creation.

    Per the permissions matrix: staff has plan.edit: SCOPED (can edit targets),
    program_manager has plan.edit: DENY (cannot edit targets).
    """

    def setUp(self):
        super().setUp()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Section", program=self.program,
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section, client_file=self.client_file,
            name="Original Target", description="Original description",
        )

    def test_edit_creates_revision_with_old_values(self):
        """Staff has plan.edit: SCOPED — editing a target creates a revision with old values."""
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:target_edit", args=[self.target.pk])
        resp = self.http.post(url, {
            "name": "Updated Target",
            "description": "New description",
        })
        self.assertEqual(resp.status_code, 302)
        # Revision should have the OLD values
        rev = PlanTargetRevision.objects.filter(plan_target=self.target).first()
        self.assertIsNotNone(rev)
        self.assertEqual(rev.name, "Original Target")
        self.assertEqual(rev.description, "Original description")
        # Target itself should be updated
        self.target.refresh_from_db()
        self.assertEqual(self.target.name, "Updated Target")

    def test_manager_cannot_edit_target(self):
        """Program manager has plan.edit: DENY per permissions matrix."""
        self.http.login(username="manager", password="pass")
        url = reverse("plans:target_edit", args=[self.target.pk])
        resp = self.http.post(url, {
            "name": "Hacked",
            "description": "",
        })
        self.assertEqual(resp.status_code, 403)
        self.target.refresh_from_db()
        self.assertEqual(self.target.name, "Original Target")

    def test_other_program_manager_cannot_edit_target(self):
        """Manager of a different program also has plan.edit: DENY."""
        self.http.login(username="other_mgr", password="pass")
        url = reverse("plans:target_edit", args=[self.target.pk])
        resp = self.http.post(url, {
            "name": "Hacked",
            "description": "",
        })
        self.assertEqual(resp.status_code, 403)


class TargetStatusTest(PlanCRUDBaseTest):
    """Test changing target status.

    Per the permissions matrix: staff has plan.edit: SCOPED (can change status),
    program_manager has plan.edit: DENY (cannot change status).
    """

    def setUp(self):
        super().setUp()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Section", program=self.program,
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section, client_file=self.client_file,
            name="Target", description="",
        )

    def test_counsellor_can_change_target_status(self):
        """Staff has plan.edit: SCOPED per permissions matrix — can change target status."""
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:target_status", args=[self.target.pk])
        resp = self.http.post(url, {
            "status": "completed",
            "status_reason": "Target achieved",
        })
        self.assertEqual(resp.status_code, 200)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, "completed")
        # Should create a revision
        self.assertTrue(
            PlanTargetRevision.objects.filter(plan_target=self.target).exists()
        )

    def test_manager_cannot_change_target_status(self):
        """Program manager has plan.edit: DENY per permissions matrix."""
        self.http.login(username="manager", password="pass")
        url = reverse("plans:target_status", args=[self.target.pk])
        resp = self.http.post(url, {
            "status": "deactivated",
            "status_reason": "Should fail",
        })
        self.assertEqual(resp.status_code, 403)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, "default")


class MetricAssignmentTest(PlanCRUDBaseTest):
    """Test assigning metrics to a target.

    Per the permissions matrix: staff has plan.edit: SCOPED (can assign metrics),
    program_manager has plan.edit: DENY (cannot assign metrics).
    """

    def setUp(self):
        super().setUp()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Section", program=self.program,
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section, client_file=self.client_file,
            name="Housing", description="",
        )
        self.metric_a = MetricDefinition.objects.create(
            name="PHQ-9", definition="Depression scale", category="mental_health",
            min_value=0, max_value=27, unit="score",
        )
        self.metric_b = MetricDefinition.objects.create(
            name="Housing Stability", definition="Housing score", category="housing",
            min_value=0, max_value=10, unit="score",
        )

    def test_counsellor_can_assign_metrics(self):
        """Staff has plan.edit: SCOPED per permissions matrix — can assign metrics."""
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:target_metrics", args=[self.target.pk])
        resp = self.http.post(url, {
            "metrics": [self.metric_a.pk, self.metric_b.pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(PlanTargetMetric.objects.filter(plan_target=self.target).count(), 2)

    def test_manager_cannot_assign_metrics(self):
        """Program manager has plan.edit: DENY per permissions matrix."""
        self.http.login(username="manager", password="pass")
        url = reverse("plans:target_metrics", args=[self.target.pk])
        resp = self.http.post(url, {
            "metrics": [self.metric_a.pk],
        })
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(PlanTargetMetric.objects.count(), 0)

    def test_reassigning_metrics_replaces_old_ones(self):
        """Staff can reassign metrics — old assignments are replaced."""
        PlanTargetMetric.objects.create(plan_target=self.target, metric_def=self.metric_a)
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:target_metrics", args=[self.target.pk])
        resp = self.http.post(url, {
            "metrics": [self.metric_b.pk],
        })
        self.assertEqual(resp.status_code, 302)
        assigned = PlanTargetMetric.objects.filter(plan_target=self.target)
        self.assertEqual(assigned.count(), 1)
        self.assertEqual(assigned.first().metric_def, self.metric_b)


class MetricLibraryPermissionTest(PlanCRUDBaseTest):
    """Test metric library admin pages require admin role."""

    def test_admin_can_access_metric_library(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.get(reverse("plans:metric_library"))
        self.assertEqual(resp.status_code, 200)

    def test_staff_cannot_access_metric_library(self):
        self.http.login(username="counsellor", password="pass")
        resp = self.http.get(reverse("plans:metric_library"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_metric(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.post(reverse("plans:metric_create"), {
            "name": "New Metric",
            "definition": "A test metric",
            "category": "custom",
            "min_value": 0,
            "max_value": 10,
            "unit": "score",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(MetricDefinition.objects.filter(name="New Metric").exists())

    def test_staff_cannot_create_metric(self):
        self.http.login(username="counsellor", password="pass")
        resp = self.http.post(reverse("plans:metric_create"), {
            "name": "Hacked Metric",
            "definition": "Should fail",
            "category": "custom",
        })
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_toggle_metric(self):
        metric = MetricDefinition.objects.create(
            name="Toggle Me", definition="Test", category="general"
        )
        self.http.login(username="admin", password="pass")
        resp = self.http.post(reverse("plans:metric_toggle", args=[metric.pk]))
        self.assertEqual(resp.status_code, 200)
        metric.refresh_from_db()
        self.assertFalse(metric.is_enabled)

    def test_staff_cannot_toggle_metric(self):
        metric = MetricDefinition.objects.create(
            name="No Toggle", definition="Test", category="general"
        )
        self.http.login(username="counsellor", password="pass")
        resp = self.http.post(reverse("plans:metric_toggle", args=[metric.pk]))
        self.assertEqual(resp.status_code, 403)
        metric.refresh_from_db()
        self.assertTrue(metric.is_enabled)


class PlanViewAccessTest(PlanCRUDBaseTest):
    """Test plan view access."""

    def test_plan_view_requires_login(self):
        url = reverse("plans:plan_view", args=[self.client_file.pk])
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.url)

    def test_logged_in_user_can_view_plan(self):
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:plan_view", args=[self.client_file.pk])
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_target_history_accessible(self):
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file,
            name="Target", description="",
        )
        self.http.login(username="counsellor", password="pass")
        url = reverse("plans:target_history", args=[target.pk])
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 200)
