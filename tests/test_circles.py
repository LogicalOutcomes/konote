"""Tests for Circles Lite (Phase 1).

Covers:
- Model tests: encrypted name, membership, queryset helpers, unique constraint
- Form tests: CircleForm, CircleMembershipForm validation
- View tests: permissions, feature toggle gating, CRUD
- Privacy tests: PHIPA-compliant timeline, DV small-circle hiding
- Intake tests: link to existing circle, create new circle
- Note form tests: circle dropdown, auto-select single circle
"""
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.circles.forms import CircleForm, CircleMembershipForm
from apps.circles.models import Circle, CircleMembership
from apps.clients.models import ClientAccessBlock, ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _enable_circles():
    """Enable the circles feature toggle."""
    FeatureToggle.objects.update_or_create(
        feature_key="circles", defaults={"is_enabled": True},
    )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CircleModelTest(TestCase):
    """Test Circle and CircleMembership models."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_encrypted_name_roundtrip(self):
        """Encrypted name property stores and retrieves correctly."""
        circle = Circle(is_demo=False, created_by=self.admin)
        circle.name = "Garcia Family"
        circle.save()
        circle.refresh_from_db()
        self.assertEqual(circle.name, "Garcia Family")

    def test_encrypted_name_not_stored_plaintext(self):
        """Raw encrypted field should not contain plaintext."""
        circle = Circle(is_demo=False)
        circle.name = "Garcia Family"
        circle.save()
        circle.refresh_from_db()
        self.assertNotEqual(circle._name_encrypted, b"Garcia Family")

    def test_queryset_real_and_demo(self):
        """`.real()` and `.demo()` queryset methods work."""
        c1 = Circle(is_demo=False)
        c1.name = "Real Circle"
        c1.save()
        c2 = Circle(is_demo=True)
        c2.name = "Demo Circle"
        c2.save()
        self.assertEqual(Circle.objects.real().count(), 1)
        self.assertEqual(Circle.objects.demo().count(), 1)

    def test_membership_with_client_file(self):
        """Membership can link to a ClientFile."""
        circle = Circle(is_demo=False)
        circle.name = "Test"
        circle.save()
        client = ClientFile(is_demo=False)
        client.first_name = "Jane"
        client.last_name = "Doe"
        client.save()
        m = CircleMembership.objects.create(
            circle=circle, client_file=client, relationship_label="parent",
        )
        self.assertIn("Jane", m.display_name)

    def test_membership_without_client_file(self):
        """Membership can use member_name instead of client_file."""
        circle = Circle(is_demo=False)
        circle.name = "Test"
        circle.save()
        m = CircleMembership.objects.create(
            circle=circle, member_name="External Person",
        )
        self.assertEqual(m.display_name, "External Person")

    def test_unique_constraint_prevents_duplicate_active(self):
        """Cannot add same client to same circle twice when both active."""
        circle = Circle(is_demo=False)
        circle.name = "Test"
        circle.save()
        client = ClientFile(is_demo=False)
        client.first_name = "A"
        client.last_name = "B"
        client.save()
        CircleMembership.objects.create(
            circle=circle, client_file=client, status="active",
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CircleMembership.objects.create(
                circle=circle, client_file=client, status="active",
            )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CircleFormTest(TestCase):
    """Test CircleForm and CircleMembershipForm validation."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_circle_form_valid(self):
        form = CircleForm(data={"name": "Garcia Family", "status": "active"})
        self.assertTrue(form.is_valid())

    def test_circle_form_name_required(self):
        form = CircleForm(data={"name": "", "status": "active"})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_membership_form_requires_one_of_client_or_name(self):
        """Must provide either client_file or member_name."""
        form = CircleMembershipForm(data={})
        self.assertFalse(form.is_valid())

    def test_membership_form_rejects_both(self):
        """Cannot provide both client_file and member_name."""
        form = CircleMembershipForm(data={
            "client_file": 1,
            "member_name": "External Person",
        })
        self.assertFalse(form.is_valid())

    def test_membership_form_accepts_client_file_only(self):
        form = CircleMembershipForm(data={
            "client_file": 1,
            "member_name": "",
        })
        self.assertTrue(form.is_valid())

    def test_membership_form_accepts_member_name_only(self):
        form = CircleMembershipForm(data={
            "member_name": "External Person",
        })
        self.assertTrue(form.is_valid())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CircleViewPermissionTest(TestCase):
    """Test circle view access control and feature gating."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(name="Test Program")

    def tearDown(self):
        enc_module._fernet = None

    def _make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass123")
        UserProgramRole.objects.create(user=user, program=self.program, role=role)
        return user

    def test_feature_toggle_off_returns_404(self):
        """All circle views return 404 when feature toggle is off."""
        FeatureToggle.objects.update_or_create(
            feature_key="circles", defaults={"is_enabled": False},
        )
        staff = self._make_user("staff1", "staff")
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 404)

    def test_feature_toggle_on_staff_can_list(self):
        """Staff with circle.view can access the list."""
        _enable_circles()
        staff = self._make_user("staff1", "staff")
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 200)

    def test_receptionist_denied(self):
        """Receptionists should be denied access (circle.view = DENY)."""
        _enable_circles()
        receptionist = self._make_user("rec1", "receptionist")
        self.http.login(username="rec1", password="testpass123")
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 403)

    def test_executive_denied(self):
        """Executives should be denied access (circle.view = DENY)."""
        _enable_circles()
        executive = self._make_user("exec1", "executive")
        self.http.login(username="exec1", password="testpass123")
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 403)

    def test_program_manager_can_access(self):
        """Program managers should have full access."""
        _enable_circles()
        pm = self._make_user("pm1", "program_manager")
        self.http.login(username="pm1", password="testpass123")
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CircleCRUDTest(TestCase):
    """Test circle create, detail, edit, archive, membership flows."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        _enable_circles()
        self.program = Program.objects.create(name="Test Program")
        self.staff = User.objects.create_user(
            username="staff1", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff",
        )
        # Create a client enrolled in the program
        self.client_file = ClientFile(is_demo=False)
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="active",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_create_circle(self):
        """Staff can create a circle."""
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.post("/circles/create/", {
            "name": "Doe Family",
            "status": "active",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Circle.objects.count(), 1)
        circle = Circle.objects.first()
        self.assertEqual(circle.name, "Doe Family")
        self.assertEqual(circle.created_by, self.staff)

    def test_circle_detail(self):
        """Circle detail page shows members and notes sections."""
        self.http.login(username="staff1", password="testpass123")
        circle = Circle(is_demo=False, created_by=self.staff)
        circle.name = "Doe Family"
        circle.save()
        CircleMembership.objects.create(
            circle=circle, client_file=self.client_file, relationship_label="parent",
        )
        resp = self.http.get(f"/circles/{circle.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Doe Family")
        self.assertContains(resp, "Jane")

    def test_edit_circle(self):
        """Staff can edit a circle's name."""
        self.http.login(username="staff1", password="testpass123")
        circle = Circle(is_demo=False, created_by=self.staff)
        circle.name = "Old Name"
        circle.save()
        CircleMembership.objects.create(
            circle=circle, client_file=self.client_file,
        )
        resp = self.http.post(f"/circles/{circle.pk}/edit/", {
            "name": "New Name",
            "status": "active",
        })
        self.assertEqual(resp.status_code, 302)
        circle.refresh_from_db()
        self.assertEqual(circle.name, "New Name")

    def test_archive_circle(self):
        """Archiving a circle sets status to archived."""
        self.http.login(username="staff1", password="testpass123")
        circle = Circle(is_demo=False, created_by=self.staff)
        circle.name = "Doe Family"
        circle.save()
        CircleMembership.objects.create(
            circle=circle, client_file=self.client_file,
        )
        resp = self.http.post(f"/circles/{circle.pk}/archive/")
        self.assertEqual(resp.status_code, 302)
        circle.refresh_from_db()
        self.assertEqual(circle.status, "archived")

    def test_add_member(self):
        """Adding a participant member works."""
        self.http.login(username="staff1", password="testpass123")
        circle = Circle(is_demo=False, created_by=self.staff)
        circle.name = "Doe Family"
        circle.save()
        CircleMembership.objects.create(
            circle=circle, client_file=self.client_file,
        )
        # Create another client
        client2 = ClientFile(is_demo=False)
        client2.first_name = "John"
        client2.last_name = "Doe"
        client2.save()
        ClientProgramEnrolment.objects.create(
            client_file=client2, program=self.program, status="active",
        )
        resp = self.http.post(f"/circles/{circle.pk}/member/add/", {
            "client_file": client2.pk,
            "relationship_label": "spouse",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CircleMembership.objects.filter(circle=circle).count(), 2)

    def test_remove_member(self):
        """Removing a member sets status to inactive."""
        self.http.login(username="staff1", password="testpass123")
        circle = Circle(is_demo=False, created_by=self.staff)
        circle.name = "Doe Family"
        circle.save()
        m = CircleMembership.objects.create(
            circle=circle, client_file=self.client_file,
        )
        resp = self.http.post(f"/circles/{circle.pk}/member/{m.pk}/remove/")
        self.assertEqual(resp.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.status, "inactive")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CirclePrivacyTest(TestCase):
    """Test PHIPA-compliant note timeline and DV small-circle hiding."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        _enable_circles()
        self.program1 = Program.objects.create(name="Program 1")
        self.program2 = Program.objects.create(name="Program 2")
        # Staff user with access to program1 only
        self.staff = User.objects.create_user(
            username="staff1", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program1, role="staff",
        )
        # Client A in program1 (accessible)
        self.client_a = ClientFile(is_demo=False)
        self.client_a.first_name = "Alice"
        self.client_a.last_name = "A"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_a, program=self.program1, status="active",
        )
        # Client B in program2 only (NOT accessible to staff1)
        self.client_b = ClientFile(is_demo=False)
        self.client_b.first_name = "Bob"
        self.client_b.last_name = "B"
        self.client_b.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.program2, status="active",
        )
        # Circle with both clients
        self.circle = Circle(is_demo=False, created_by=self.staff)
        self.circle.name = "AB Family"
        self.circle.save()
        CircleMembership.objects.create(
            circle=self.circle, client_file=self.client_a,
        )
        CircleMembership.objects.create(
            circle=self.circle, client_file=self.client_b,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_timeline_filters_notes_by_client_access(self):
        """Circle detail only shows notes where user can access the client."""
        # Create note for client_a (accessible) and client_b (not accessible)
        admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        note_a = ProgressNote.objects.create(
            client_file=self.client_a,
            circle=self.circle,
            author=admin,
            note_type="quick",
            interaction_type="session",
            notes_text="Note about Alice",
            author_program=self.program1,
        )
        note_b = ProgressNote.objects.create(
            client_file=self.client_b,
            circle=self.circle,
            author=admin,
            note_type="quick",
            interaction_type="session",
            notes_text="Note about Bob",
            author_program=self.program2,
        )
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.get(f"/circles/{self.circle.pk}/")
        self.assertEqual(resp.status_code, 200)
        # Should see note_a but not note_b
        self.assertContains(resp, "Alice")
        # Should show hidden count
        self.assertContains(resp, "1 on records you don")

    def test_dv_hiding_small_circle(self):
        """Circle with <2 visible enrolled participants after block is hidden."""
        # Block staff from seeing client_b
        ClientAccessBlock.objects.create(
            user=self.staff,
            client_file=self.client_b,
            reason="DV safety",
            created_by=self.staff,
        )
        self.http.login(username="staff1", password="testpass123")
        # Circle has 2 enrolled members, 1 blocked = 1 visible < 2 → hidden
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "AB Family")

    def test_dv_hiding_ignores_non_participants(self):
        """Non-participant members don't count toward DV visibility threshold."""
        # Add 3 non-participant members (typed names, no client_file)
        for name in ["Uncle Bob", "Aunt Carol", "Cousin Dave"]:
            m = CircleMembership(circle=self.circle)
            m.member_name = name
            m.save()
        # Block client_b
        ClientAccessBlock.objects.create(
            user=self.staff,
            client_file=self.client_b,
            reason="DV safety",
            created_by=self.staff,
        )
        self.http.login(username="staff1", password="testpass123")
        # Circle has 1 visible enrolled participant + 3 non-participants
        # Non-participants don't count → 1 visible < 2 → still hidden
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "AB Family")

    def test_circle_visible_with_enough_members(self):
        """Circle with >= 2 visible enrolled participants shown even with blocks."""
        # Add one more enrolled client to reach threshold
        c = ClientFile(is_demo=False)
        c.first_name = "Extra"
        c.last_name = "X"
        c.save()
        ClientProgramEnrolment.objects.create(
            client_file=c, program=self.program1, status="active",
        )
        CircleMembership.objects.create(
            circle=self.circle, client_file=c,
        )
        # Block client_b (still 2 visible enrolled participants → ok)
        ClientAccessBlock.objects.create(
            user=self.staff,
            client_file=self.client_b,
            reason="DV safety",
            created_by=self.staff,
        )
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.get("/circles/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AB Family")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CircleIntakeTest(TestCase):
    """Test circle integration in intake form."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        _enable_circles()
        self.program = Program.objects.create(name="Test Program")
        self.staff = User.objects.create_user(
            username="staff1", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff",
        )
        # Pre-existing circle
        self.circle = Circle(is_demo=False, created_by=self.staff)
        self.circle.name = "Existing Family"
        self.circle.save()
        # Need a member so the circle is visible
        c = ClientFile(is_demo=False)
        c.first_name = "Existing"
        c.last_name = "Member"
        c.save()
        ClientProgramEnrolment.objects.create(
            client_file=c, program=self.program, status="active",
        )
        CircleMembership.objects.create(circle=self.circle, client_file=c)

    def tearDown(self):
        enc_module._fernet = None

    def test_link_to_existing_circle(self):
        """Intake can link a new participant to an existing circle."""
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.post("/participants/create/", {
            "first_name": "New",
            "last_name": "Person",
            "status": "active",
            "preferred_language": "en",
            "programs": [self.program.pk],
            "existing_circle": self.circle.pk,
            "new_circle_name": "",
        })
        self.assertEqual(resp.status_code, 302)
        # Should have a new membership in the existing circle
        new_client = ClientFile.objects.order_by("-pk").first()
        self.assertTrue(
            CircleMembership.objects.filter(
                circle=self.circle, client_file=new_client, status="active",
            ).exists()
        )

    def test_create_new_circle_at_intake(self):
        """Intake can create a new circle for a participant."""
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.post("/participants/create/", {
            "first_name": "New",
            "last_name": "Person",
            "status": "active",
            "preferred_language": "en",
            "programs": [self.program.pk],
            "existing_circle": "",
            "new_circle_name": "New Family",
        })
        self.assertEqual(resp.status_code, 302)
        new_circle = Circle.objects.filter().order_by("-pk").first()
        self.assertEqual(new_circle.name, "New Family")
        new_client = ClientFile.objects.order_by("-pk").first()
        self.assertTrue(
            CircleMembership.objects.filter(
                circle=new_circle, client_file=new_client, status="active",
            ).exists()
        )

    def test_intake_rejects_both_existing_and_new(self):
        """Cannot select existing circle AND provide a new name."""
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.post("/participants/create/", {
            "first_name": "New",
            "last_name": "Person",
            "status": "active",
            "preferred_language": "en",
            "programs": [self.program.pk],
            "existing_circle": self.circle.pk,
            "new_circle_name": "Conflicting Name",
        })
        # Should re-render the form with errors (200 not 302)
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CircleNoteFormTest(TestCase):
    """Test circle dropdown on note forms."""

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        _enable_circles()
        FeatureToggle.objects.update_or_create(
            feature_key="require_client_consent", defaults={"is_enabled": False},
        )
        self.program = Program.objects.create(name="Test Program")
        self.staff = User.objects.create_user(
            username="staff1", password="testpass123",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff",
        )
        self.client_file = ClientFile(is_demo=False)
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="active",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_no_dropdown_when_no_circles(self):
        """When participant has no circles, form doesn't include circle field."""
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/quick/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'name="circle"')

    def test_dropdown_shown_when_has_circle(self):
        """When participant belongs to a circle, form includes circle field."""
        circle = Circle(is_demo=False)
        circle.name = "Doe Family"
        circle.save()
        CircleMembership.objects.create(
            circle=circle, client_file=self.client_file,
        )
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/quick/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="circle"')

    def test_quick_note_saves_circle_tag(self):
        """Quick note saves the circle FK when selected."""
        circle = Circle(is_demo=False)
        circle.name = "Doe Family"
        circle.save()
        CircleMembership.objects.create(
            circle=circle, client_file=self.client_file,
        )
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.post(f"/notes/participant/{self.client_file.pk}/quick/", {
            "interaction_type": "session",
            "notes_text": "Family session",
            "circle": circle.pk,
        })
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.first()
        self.assertEqual(note.circle_id, circle.pk)

    def test_note_without_circle_tag(self):
        """Quick note without circle tag saves circle as None."""
        circle = Circle(is_demo=False)
        circle.name = "Doe Family"
        circle.save()
        CircleMembership.objects.create(
            circle=circle, client_file=self.client_file,
        )
        self.http.login(username="staff1", password="testpass123")
        resp = self.http.post(f"/notes/participant/{self.client_file.pk}/quick/", {
            "interaction_type": "session",
            "notes_text": "Individual session",
            "circle": "",
        })
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.first()
        self.assertIsNone(note.circle_id)
