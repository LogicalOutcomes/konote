"""Tests for Phase 5: Events, Alerts, Audit, Charts, Timeline, Reports."""
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import EventType, Event, Alert
from apps.audit.models import AuditLog
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.notes.models import ProgressNote, ProgressNoteTarget, MetricValue
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EventTypeAdminTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.admin = User.objects.create_user(username="admin", password="pass", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_list_event_types(self):
        EventType.objects.create(name="Intake", colour_hex="#10B981")
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/events/admin/types/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Intake")

    def test_staff_cannot_access_event_type_admin(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/events/admin/types/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_event_type(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.post("/events/admin/types/create/", {
            "name": "Crisis",
            "description": "Crisis event",
            "colour_hex": "#EF4444",
            "status": "active",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(EventType.objects.count(), 1)

    def test_admin_can_edit_event_type(self):
        et = EventType.objects.create(name="Old Name", colour_hex="#000000")
        self.http.login(username="admin", password="pass")
        resp = self.http.post(f"/events/admin/types/{et.pk}/edit/", {
            "name": "New Name",
            "description": "",
            "colour_hex": "#FF0000",
            "status": "active",
        })
        self.assertEqual(resp.status_code, 302)
        et.refresh_from_db()
        self.assertEqual(et.name, "New Name")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EventCRUDTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)
        self.admin = User.objects.create_user(username="admin", password="pass", is_admin=True)

        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.prog)

        self.other_client = ClientFile()
        self.other_client.first_name = "Bob"
        self.other_client.last_name = "Smith"
        self.other_client.status = "active"
        self.other_client.save()

        self.event_type = EventType.objects.create(name="Intake", colour_hex="#10B981")

    def tearDown(self):
        enc_module._fernet = None

    def test_event_create_happy_path(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/events/client/{self.client_file.pk}/create/",
            {
                "title": "Initial intake",
                "description": "Client intake meeting",
                "start_timestamp": "2026-01-15 10:00",
                "event_type": self.event_type.pk,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Event.objects.count(), 1)

    def test_staff_cannot_create_event_for_inaccessible_client(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/events/client/{self.other_client.pk}/create/",
            {
                "title": "Should fail",
                "start_timestamp": "2026-01-15 10:00",
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_event_list_shows_timeline(self):
        Event.objects.create(
            client_file=self.client_file,
            title="Test event",
            start_timestamp=timezone.now(),
            event_type=self.event_type,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/events/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test event")

    def test_event_create_all_day(self):
        """All-day events should save with date only (time at midnight)."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/events/client/{self.client_file.pk}/create/",
            {
                "title": "All day workshop",
                "description": "Full day training",
                "all_day": "on",
                "start_date": "2026-03-15",
                "event_type": self.event_type.pk,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertTrue(event.all_day)
        self.assertEqual(event.start_timestamp.date().isoformat(), "2026-03-15")

    def test_event_create_all_day_with_end_date(self):
        """All-day events can have a multi-day span."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/events/client/{self.client_file.pk}/create/",
            {
                "title": "Conference",
                "all_day": "on",
                "start_date": "2026-03-15",
                "end_date": "2026-03-17",
                "event_type": self.event_type.pk,
            },
        )
        self.assertEqual(resp.status_code, 302)
        event = Event.objects.first()
        self.assertTrue(event.all_day)
        self.assertEqual(event.start_timestamp.date().isoformat(), "2026-03-15")
        self.assertEqual(event.end_timestamp.date().isoformat(), "2026-03-17")

    def test_event_list_shows_all_day_badge(self):
        """All-day events should display 'All Day' badge in timeline."""
        Event.objects.create(
            client_file=self.client_file,
            title="All day event",
            start_timestamp=timezone.now(),
            event_type=self.event_type,
            all_day=True,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/events/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "All Day")
        self.assertContains(resp, "All day event")

    def test_all_day_event_requires_start_date(self):
        """All-day events must have a start date."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/events/client/{self.client_file.pk}/create/",
            {
                "title": "Missing date",
                "all_day": "on",
                # No start_date provided
                "event_type": self.event_type.pk,
            },
        )
        # Should re-render the form with errors, not redirect
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Event.objects.count(), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AlertCRUDTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)
        self.admin = User.objects.create_user(username="admin", password="pass", is_admin=True)
        self.other_staff = User.objects.create_user(username="other", password="pass", is_admin=False)
        self.pm = User.objects.create_user(username="pm", password="pass", is_admin=False)

        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.other_staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.pm, program=self.prog, role="program_manager")
        # Admin needs a PM role to cancel alerts (admin alone is not a program role)
        UserProgramRole.objects.create(user=self.admin, program=self.prog, role="program_manager")

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.prog)

    def tearDown(self):
        enc_module._fernet = None

    def test_alert_create(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/events/client/{self.client_file.pk}/alerts/create/",
            {"content": "Safety concern noted"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual(Alert.objects.first().content, "Safety concern noted")

    def test_pm_can_cancel_alert(self):
        """Program managers can cancel alerts directly (two-person rule: staff recommend, PM cancels)."""
        alert = Alert.objects.create(
            client_file=self.client_file,
            content="Test alert",
            author=self.staff,
        )
        self.http.login(username="pm", password="pass")
        resp = self.http.post(
            f"/events/alerts/{alert.pk}/cancel/",
            {"status_reason": "No longer relevant"},
        )
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.status, "cancelled")

    def test_staff_cannot_cancel_alert(self):
        """Staff cannot cancel alerts directly — must use recommend_cancel (two-person safety rule)."""
        alert = Alert.objects.create(
            client_file=self.client_file,
            content="Not yours",
            author=self.other_staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/events/alerts/{alert.pk}/cancel/",
            {"status_reason": "Should fail"},
        )
        self.assertEqual(resp.status_code, 403)
        alert.refresh_from_db()
        self.assertEqual(alert.status, "default")

    def test_admin_with_pm_role_can_cancel_any_alert(self):
        """Admin with PM role can cancel any alert in their program."""
        alert = Alert.objects.create(
            client_file=self.client_file,
            content="Admin cancel",
            author=self.staff,
        )
        self.http.login(username="admin", password="pass")
        resp = self.http.post(
            f"/events/alerts/{alert.pk}/cancel/",
            {"status_reason": "Admin override"},
        )
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.status, "cancelled")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AuditLogViewerTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.admin = User.objects.create_user(username="admin", password="pass", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_view_audit_log(self):
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_display="admin",
            action="login",
            resource_type="session",
        )
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/admin/audit/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "session")

    def test_staff_cannot_access_audit_log(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/admin/audit/")
        self.assertEqual(resp.status_code, 403)

    def test_audit_log_csv_export(self):
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_display="admin",
            action="create",
            resource_type="client",
        )
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/admin/audit/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_audit_log_filter_by_action(self):
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_display="admin",
            action="login",
            resource_type="session",
        )
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_display="admin",
            action="create",
            resource_type="client",
        )
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/admin/audit/?action=login")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "session")
        # Check that the "create" action's "client" resource_type is not in
        # the audit log table rows (it may appear in nav links on the page)
        self.assertContains(resp, "session")
        # The word "client" appears in nav HTML, so check the table body specifically
        table_html = resp.content.decode("utf-8")
        # The filtered results should only contain "login" action rows, not "create" rows
        self.assertNotIn("create", table_html.split("</thead>")[-1] if "</thead>" in table_html else "")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AnalysisChartTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)
        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.prog)

    def tearDown(self):
        enc_module._fernet = None

    def test_analysis_page_loads(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/reports/client/{self.client_file.pk}/analysis/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Analysis")

    def test_analysis_shows_chart_data(self):
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Housing",
        )
        metric = MetricDefinition.objects.create(
            name="PHQ-9", min_value=0, max_value=27, unit="score",
            definition="Depression scale", category="mental_health",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="full", author=self.staff,
        )
        pnt = ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target,
        )
        MetricValue.objects.create(
            progress_note_target=pnt, metric_def=metric, value="12",
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/reports/client/{self.client_file.pk}/analysis/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "PHQ-9")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MetricExportTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.admin = User.objects.create_user(username="admin", password="pass", is_admin=True)
        self.staff_user = User.objects.create_user(username="staff", password="pass", is_admin=False)

        self.prog = Program.objects.create(name="Housing First", colour_hex="#10B981")
        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.record_id = "REC001"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.prog)

        self.metric = MetricDefinition.objects.create(
            name="PHQ-9", min_value=0, max_value=27, unit="score",
            definition="Depression", category="mental_health",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_staff_cannot_access_export(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/reports/export/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_view_export_form(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "export")
