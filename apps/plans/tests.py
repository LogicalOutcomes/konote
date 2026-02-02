"""Tests for the plans app — Phase 3 (PLAN1, PLAN2, PLAN3, PLAN6)."""
from django.test import TestCase, Client as TestClient
from django.urls import reverse

from apps.auth_app.models import User
from apps.clients.models import ClientFile
from apps.programs.models import Program, UserProgramRole

from .models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetRevision,
)
from .views import _can_edit_plan


class PlanPermissionHelperTest(TestCase):
    """Test the _can_edit_plan helper."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass123", is_admin=True)
        self.pm = User.objects.create_user(username="pm", password="pass123")
        self.staff = User.objects.create_user(username="staff", password="pass123")
        self.program = Program.objects.create(name="Housing")
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        # Enrol client in programme
        from apps.clients.models import ClientProgramEnrolment
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled"
        )
        # PM role
        UserProgramRole.objects.create(
            user=self.pm, program=self.program, role="program_manager", status="active"
        )
        # Staff role
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active"
        )

    def test_admin_can_edit(self):
        self.assertTrue(_can_edit_plan(self.admin, self.client_file))

    def test_program_manager_can_edit(self):
        self.assertTrue(_can_edit_plan(self.pm, self.client_file))

    def test_staff_cannot_edit(self):
        self.assertFalse(_can_edit_plan(self.staff, self.client_file))


class PlanViewTest(TestCase):
    """Test plan view requires login."""

    def setUp(self):
        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.save()

    def test_plan_view_requires_login(self):
        c = TestClient()
        url = reverse("plans:plan_view", args=[self.client_file.pk])
        response = c.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)


class SectionCreatePermissionTest(TestCase):
    """Test section create requires admin/PM role."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="pass123")
        self.program = Program.objects.create(name="Youth")
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "User"
        self.client_file.save()
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active"
        )

    def test_admin_can_create_section(self):
        c = TestClient()
        c.login(username="admin", password="pass123")
        url = reverse("plans:section_create", args=[self.client_file.pk])
        response = c.post(url, {"name": "New Section", "sort_order": 0})
        # Should succeed (redirect or re-render)
        self.assertIn(response.status_code, [200, 302])

    def test_staff_cannot_create_section(self):
        c = TestClient()
        c.login(username="staff", password="pass123")
        url = reverse("plans:section_create", args=[self.client_file.pk])
        response = c.post(url, {"name": "New Section", "sort_order": 0})
        self.assertEqual(response.status_code, 403)


class TargetEditRevisionTest(TestCase):
    """Test that editing a target creates a revision."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass123", is_admin=True)
        self.client_file = ClientFile()
        self.client_file.first_name = "Rev"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.section = PlanSection.objects.create(
            client_file=self.client_file, name="Section A"
        )
        self.target = PlanTarget.objects.create(
            plan_section=self.section,
            client_file=self.client_file,
            name="Original Name",
            description="Original description",
        )

    def test_edit_creates_revision(self):
        c = TestClient()
        c.login(username="admin", password="pass123")
        url = reverse("plans:target_edit", args=[self.target.pk])
        c.post(url, {"name": "Updated Name", "description": "Updated description"})
        # Should have one revision with the OLD values
        revisions = PlanTargetRevision.objects.filter(plan_target=self.target)
        self.assertEqual(revisions.count(), 1)
        rev = revisions.first()
        self.assertEqual(rev.name, "Original Name")
        self.assertEqual(rev.description, "Original description")


class MetricTogglePermissionTest(TestCase):
    """Test metric toggle requires admin."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="pass123")
        self.metric = MetricDefinition.objects.create(
            name="PHQ-9", definition="Depression scale", category="mental_health"
        )

    def test_admin_can_toggle(self):
        c = TestClient()
        c.login(username="admin", password="pass123")
        url = reverse("plans:metric_toggle", args=[self.metric.pk])
        response = c.post(url)
        self.assertEqual(response.status_code, 200)
        self.metric.refresh_from_db()
        self.assertFalse(self.metric.is_enabled)

    def test_staff_cannot_toggle(self):
        c = TestClient()
        c.login(username="staff", password="pass123")
        url = reverse("plans:metric_toggle", args=[self.metric.pk])
        response = c.post(url)
        self.assertEqual(response.status_code, 403)
