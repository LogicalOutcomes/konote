"""Tests for the plans app — Phase 3 (PLAN1, PLAN2, PLAN3, PLAN6)."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
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
from .views import _can_edit_plan, _parse_metric_csv


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


class MetricExportTest(TestCase):
    """Test CSV export of metric definitions."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="pass123")
        self.metric = MetricDefinition.objects.create(
            name="PHQ-9", definition="Depression scale", category="mental_health",
            min_value=0, max_value=27, unit="score",
        )

    def test_admin_can_export(self):
        c = TestClient()
        c.login(username="admin", password="pass123")
        response = c.get(reverse("plans:metric_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("metric_definitions.csv", response["Content-Disposition"])
        # Check CSV content includes the metric
        content = response.content.decode("utf-8-sig")
        self.assertIn("PHQ-9", content)
        self.assertIn("Depression scale", content)

    def test_staff_cannot_export(self):
        c = TestClient()
        c.login(username="staff", password="pass123")
        response = c.get(reverse("plans:metric_export"))
        self.assertEqual(response.status_code, 403)

    def test_export_includes_all_columns(self):
        c = TestClient()
        c.login(username="admin", password="pass123")
        response = c.get(reverse("plans:metric_export"))
        content = response.content.decode("utf-8-sig")
        header_line = content.split("\n")[0]
        for col in ["id", "name", "definition", "category", "min_value",
                     "max_value", "unit", "is_enabled", "status"]:
            self.assertIn(col, header_line)


class MetricCsvParseTest(TestCase):
    """Test _parse_metric_csv with update-or-create logic."""

    def setUp(self):
        self.existing = MetricDefinition.objects.create(
            name="PHQ-9", definition="Depression scale", category="mental_health",
            min_value=0, max_value=27, unit="score",
        )

    def _make_csv(self, content):
        """Helper: turn a string into an in-memory file for parsing."""
        return io.BytesIO(content.encode("utf-8"))

    def test_parse_new_rows(self):
        csv_content = "name,definition,category\nGAD-7,Anxiety scale,mental_health\n"
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["action"], "new")
        self.assertIsNone(rows[0]["id"])

    def test_parse_update_row_with_id(self):
        csv_content = f"id,name,definition,category\n{self.existing.pk},PHQ-9 Updated,Depression scale v2,mental_health\n"
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["action"], "update")
        self.assertEqual(rows[0]["id"], self.existing.pk)
        self.assertEqual(rows[0]["name"], "PHQ-9 Updated")

    def test_parse_invalid_id_gives_error(self):
        csv_content = "id,name,definition,category\n99999,GAD-7,Anxiety,mental_health\n"
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(len(errors), 1)
        self.assertIn("does not match", errors[0])

    def test_parse_is_enabled_and_status(self):
        csv_content = "name,definition,category,is_enabled,status\nTest,Desc,custom,no,deactivated\n"
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(errors, [])
        self.assertFalse(rows[0]["is_enabled"])
        self.assertEqual(rows[0]["status"], "deactivated")

    def test_parse_invalid_is_enabled(self):
        csv_content = "name,definition,category,is_enabled\nTest,Desc,custom,maybe\n"
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(len(errors), 1)
        self.assertIn("is_enabled", errors[0])

    def test_parse_invalid_status(self):
        csv_content = "name,definition,category,status\nTest,Desc,custom,archived\n"
        rows, errors = _parse_metric_csv(self._make_csv(csv_content))
        self.assertEqual(len(errors), 1)
        self.assertIn("status", errors[0])


class MetricImportUpdateTest(TestCase):
    """Test that import with id column updates existing metrics."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass123", is_admin=True)
        self.metric = MetricDefinition.objects.create(
            name="PHQ-9", definition="Depression scale", category="mental_health",
            min_value=0, max_value=27, unit="score",
        )

    def test_import_updates_existing_metric(self):
        """Full round-trip: upload CSV with id → preview → confirm → metric updated."""
        c = TestClient()
        c.login(username="admin", password="pass123")
        url = reverse("plans:metric_import")

        # Step 1: Upload CSV with id column
        csv_content = f"id,name,definition,category,min_value,max_value,unit,is_enabled,status\n{self.metric.pk},PHQ-9 Revised,Updated depression scale,mental_health,0,27,score,yes,active\n"
        csv_file = SimpleUploadedFile("metrics.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = c.post(url, {"csv_file": csv_file})
        self.assertEqual(response.status_code, 200)  # Preview page

        # Step 2: Confirm import
        response = c.post(url, {"confirm_import": "1"}, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify the metric was updated
        self.metric.refresh_from_db()
        self.assertEqual(self.metric.name, "PHQ-9 Revised")
        self.assertEqual(self.metric.definition, "Updated depression scale")
