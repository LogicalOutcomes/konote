"""Tests for Serious Reportable Events (SRE) system.

Covers:
1. SRECategory creation
2. Event with is_sre=True requires sre_category
3. Event with is_sre=False doesn't require sre_category
4. SRE flagging sets flagged_by and flagged_at
5. SRE flagging creates audit log entry
6. Un-flagging requires Admin role (PM gets 403)
7. SRE report accessible to Admin/Executive, not Staff
8. Seed command creates 12 categories
9. Seed command is idempotent
"""
import io
from datetime import timedelta

from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.forms import EventForm
from apps.events.models import Event, EventType, SRECategory
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module
from apps.auth_app.constants import ROLE_EXECUTIVE, ROLE_PROGRAM_MANAGER, ROLE_STAFF

TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SRECategoryModelTest(TestCase):
    """Test SRECategory creation and string representation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_create_sre_category(self):
        """SRECategory can be created with required fields."""
        cat = SRECategory.objects.create(
            name="Death of a participant",
            name_fr="Décès d'un participant",
            severity=1,
        )
        self.assertEqual(cat.name, "Death of a participant")
        self.assertEqual(cat.severity, 1)
        self.assertTrue(cat.is_active)

    def test_sre_category_str(self):
        """SRECategory __str__ returns the name."""
        cat = SRECategory.objects.create(name="Test Category", severity=2)
        self.assertEqual(str(cat), "Test Category")

    def test_sre_category_ordering(self):
        """SRECategory ordering is by display_order, then name."""
        cat_b = SRECategory.objects.create(name="Beta", severity=2, display_order=2)
        cat_a = SRECategory.objects.create(name="Alpha", severity=1, display_order=1)
        cats = list(SRECategory.objects.all())
        self.assertEqual(cats[0].name, "Alpha")
        self.assertEqual(cats[1].name, "Beta")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EventSREValidationTest(TestCase):
    """Test Event model SRE validation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(is_demo=False, status="active")
        self.event_type = EventType.objects.create(name="Crisis", status="active")
        self.sre_category = SRECategory.objects.create(
            name="Serious injury",
            severity=1,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_sre_true_requires_category(self):
        """Event with is_sre=True and no sre_category raises ValidationError."""
        event = Event(
            client_file=self.client_file,
            title="Test SRE",
            start_timestamp=timezone.now(),
            is_sre=True,
            sre_category=None,
        )
        with self.assertRaises(ValidationError) as ctx:
            event.clean()
        self.assertIn("sre_category", ctx.exception.message_dict)

    def test_sre_true_with_category_valid(self):
        """Event with is_sre=True and sre_category is valid."""
        event = Event(
            client_file=self.client_file,
            title="Test SRE",
            start_timestamp=timezone.now(),
            is_sre=True,
            sre_category=self.sre_category,
        )
        # Should not raise
        event.clean()

    def test_sre_false_no_category_required(self):
        """Event with is_sre=False doesn't require sre_category."""
        event = Event(
            client_file=self.client_file,
            title="Normal event",
            start_timestamp=timezone.now(),
            is_sre=False,
            sre_category=None,
        )
        # Should not raise
        event.clean()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EventFormSRETest(TestCase):
    """Test EventForm SRE validation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.sre_category = SRECategory.objects.create(
            name="Serious injury", severity=1,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_form_sre_true_requires_category(self):
        """Form with is_sre=True and no category is invalid."""
        form = EventForm(
            data={
                "title": "Test",
                "all_day": False,
                "start_timestamp": "2026-03-01T14:00",
                "is_sre": True,
                # no sre_category
            },
            can_flag_sre=True,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("sre_category", form.errors)

    def test_form_sre_true_with_category_valid(self):
        """Form with is_sre=True and category is valid."""
        form = EventForm(
            data={
                "title": "Test",
                "all_day": False,
                "start_timestamp": "2026-03-01T14:00",
                "is_sre": True,
                "sre_category": self.sre_category.pk,
            },
            can_flag_sre=True,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_sre_false_no_category_valid(self):
        """Form with is_sre=False and no category is valid."""
        form = EventForm(
            data={
                "title": "Test",
                "all_day": False,
                "start_timestamp": "2026-03-01T14:00",
                "is_sre": False,
            },
            can_flag_sre=True,
        )
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SREFlaggingViewTest(TestCase):
    """Test SRE flagging in event_create view."""

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None
        cls.program = Program.objects.create(name="Housing", status="active")
        cls.staff = User.objects.create_user(
            username="sre_staff", password="testpass123", display_name="Staff SRE",
        )
        UserProgramRole.objects.create(
            user=cls.staff, program=cls.program, role=ROLE_STAFF,
        )
        cls.client_file = ClientFile.objects.create(is_demo=False, status="active")
        ClientProgramEnrolment.objects.create(
            client_file=cls.client_file, program=cls.program,
        )
        cls.sre_category = SRECategory.objects.create(
            name="Serious injury", severity=1,
        )

    def setUp(self):
        enc_module._fernet = None
        self.client.login(username="sre_staff", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def test_sre_flagging_sets_flagged_by_and_at(self):
        """Creating an SRE event sets sre_flagged_by and sre_flagged_at."""
        before = timezone.now()
        resp = self.client.post(
            reverse("events:event_create", kwargs={"client_id": self.client_file.pk}),
            data={
                "title": "Serious Incident",
                "all_day": False,
                "start_timestamp": "2026-03-01T14:00",
                "is_sre": True,
                "sre_category": self.sre_category.pk,
            },
        )
        self.assertEqual(resp.status_code, 302)

        event = Event.objects.filter(is_sre=True).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.sre_flagged_by, self.staff)
        self.assertIsNotNone(event.sre_flagged_at)
        self.assertGreaterEqual(event.sre_flagged_at, before)

    def test_sre_flagging_creates_audit_log(self):
        """Creating an SRE event creates an audit log entry."""
        from apps.audit.models import AuditLog

        resp = self.client.post(
            reverse("events:event_create", kwargs={"client_id": self.client_file.pk}),
            data={
                "title": "Serious Incident",
                "all_day": False,
                "start_timestamp": "2026-03-01T14:00",
                "is_sre": True,
                "sre_category": self.sre_category.pk,
            },
        )
        self.assertEqual(resp.status_code, 302)

        audit_entries = AuditLog.objects.using("audit").filter(
            resource_type="sre_event",
            action="create",
        )
        self.assertEqual(audit_entries.count(), 1)
        entry = audit_entries.first()
        self.assertEqual(entry.user_id, self.staff.pk)
        self.assertEqual(entry.metadata["sre_category_name"], "Serious injury")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SREUnflagViewTest(TestCase):
    """Test SRE un-flagging requires Admin role."""

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None
        cls.program = Program.objects.create(name="Youth Services", status="active")

        cls.admin = User.objects.create_user(
            username="sre_admin", password="testpass123", display_name="Admin SRE",
            is_admin=True,
        )
        cls.pm = User.objects.create_user(
            username="sre_pm", password="testpass123", display_name="PM SRE",
        )
        UserProgramRole.objects.create(
            user=cls.pm, program=cls.program, role=ROLE_PROGRAM_MANAGER,
        )
        cls.staff = User.objects.create_user(
            username="sre_staff2", password="testpass123", display_name="Staff SRE 2",
        )
        UserProgramRole.objects.create(
            user=cls.staff, program=cls.program, role=ROLE_STAFF,
        )

        cls.client_file = ClientFile.objects.create(is_demo=False, status="active")
        ClientProgramEnrolment.objects.create(
            client_file=cls.client_file, program=cls.program,
        )
        cls.sre_category = SRECategory.objects.create(
            name="Missing person", severity=1,
        )
        cls.sre_event = Event.objects.create(
            client_file=cls.client_file,
            title="Missing youth",
            start_timestamp=timezone.now(),
            author_program=cls.program,
            is_sre=True,
            sre_category=cls.sre_category,
            sre_flagged_by=cls.staff,
            sre_flagged_at=timezone.now(),
        )

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_unflag(self):
        """Admin can un-flag an SRE event."""
        self.client.login(username="sre_admin", password="testpass123")
        resp = self.client.post(
            reverse("events:sre_unflag", kwargs={"event_id": self.sre_event.pk}),
        )
        self.assertEqual(resp.status_code, 302)
        self.sre_event.refresh_from_db()
        self.assertFalse(self.sre_event.is_sre)

    def test_pm_cannot_unflag(self):
        """PM gets 403 when trying to un-flag an SRE event."""
        self.client.login(username="sre_pm", password="testpass123")
        resp = self.client.post(
            reverse("events:sre_unflag", kwargs={"event_id": self.sre_event.pk}),
        )
        self.assertEqual(resp.status_code, 403)
        self.sre_event.refresh_from_db()
        self.assertTrue(self.sre_event.is_sre)

    def test_staff_cannot_unflag(self):
        """Staff gets 403 when trying to un-flag an SRE event."""
        self.client.login(username="sre_staff2", password="testpass123")
        resp = self.client.post(
            reverse("events:sre_unflag", kwargs={"event_id": self.sre_event.pk}),
        )
        self.assertEqual(resp.status_code, 403)
        self.sre_event.refresh_from_db()
        self.assertTrue(self.sre_event.is_sre)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SREReportViewTest(TestCase):
    """Test SRE report access control."""

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None
        cls.program = Program.objects.create(name="Mental Health", status="active")

        cls.admin = User.objects.create_user(
            username="report_admin", password="testpass123", display_name="Admin Report",
            is_admin=True,
        )
        cls.executive = User.objects.create_user(
            username="report_exec", password="testpass123", display_name="Exec Report",
        )
        UserProgramRole.objects.create(
            user=cls.executive, program=cls.program, role=ROLE_EXECUTIVE,
        )
        cls.staff = User.objects.create_user(
            username="report_staff", password="testpass123", display_name="Staff Report",
        )
        UserProgramRole.objects.create(
            user=cls.staff, program=cls.program, role=ROLE_STAFF,
        )
        cls.pm = User.objects.create_user(
            username="report_pm", password="testpass123", display_name="PM Report",
        )
        UserProgramRole.objects.create(
            user=cls.pm, program=cls.program, role=ROLE_PROGRAM_MANAGER,
        )

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_can_access_report(self):
        """Admin can access the SRE report."""
        self.client.login(username="report_admin", password="testpass123")
        resp = self.client.get(reverse("events:sre_report"))
        self.assertEqual(resp.status_code, 200)

    def test_executive_can_access_report(self):
        """Executive can access the SRE report."""
        self.client.login(username="report_exec", password="testpass123")
        resp = self.client.get(reverse("events:sre_report"))
        self.assertEqual(resp.status_code, 200)

    def test_pm_can_access_report(self):
        """PM can access the SRE report."""
        self.client.login(username="report_pm", password="testpass123")
        resp = self.client.get(reverse("events:sre_report"))
        self.assertEqual(resp.status_code, 200)

    def test_staff_cannot_access_report(self):
        """Staff gets 403 when trying to access the SRE report."""
        self.client.login(username="report_staff", password="testpass123")
        resp = self.client.get(reverse("events:sre_report"))
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Seed command tests
# ---------------------------------------------------------------------------


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SeedSRECategoriesTest(TestCase):
    """Tests for the seed_sre_categories management command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_creates_12_categories(self):
        """Running seed_sre_categories creates 12 default categories."""
        out = io.StringIO()
        call_command("seed_sre_categories", stdout=out)
        self.assertEqual(SRECategory.objects.count(), 12)

    def test_idempotent(self):
        """Running seed_sre_categories twice does not duplicate records."""
        out = io.StringIO()
        call_command("seed_sre_categories", stdout=out)
        call_command("seed_sre_categories", stdout=out)
        self.assertEqual(SRECategory.objects.count(), 12)
        self.assertIn("Already exists", out.getvalue())

    def test_severity_levels_correct(self):
        """Seed categories have correct severity levels."""
        out = io.StringIO()
        call_command("seed_sre_categories", stdout=out)

        # Level 1 categories
        death = SRECategory.objects.get(name="Death of a participant")
        self.assertEqual(death.severity, 1)

        # Level 2 categories
        restraint = SRECategory.objects.get(name="Use of physical restraint or seclusion")
        self.assertEqual(restraint.severity, 2)

        # Level 3 categories
        rights = SRECategory.objects.get(name="Client rights violation")
        self.assertEqual(rights.severity, 3)

    def test_french_names_populated(self):
        """Seed categories have French translations."""
        out = io.StringIO()
        call_command("seed_sre_categories", stdout=out)

        death = SRECategory.objects.get(name="Death of a participant")
        self.assertEqual(death.name_fr, "Décès d'un participant")
