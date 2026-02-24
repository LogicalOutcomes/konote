"""Tests for offline field data collection (ODK Central integration).

Covers:
- ProgramFieldConfig model behaviour (tiers, profiles, form toggles)
- ODK Central API client (mocked HTTP responses)
- Admin views for field collection configuration
- Sync command logic (push entities, pull submissions)
"""

from datetime import date
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.field_collection.models import ProgramFieldConfig, SyncRun
from apps.field_collection.odk_client import ODKCentralClient, ODKCentralError
from apps.groups.models import Group, GroupMembership, GroupSession, GroupSessionAttendance
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# ------------------------------------------------------------------
# Model tests
# ------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramFieldConfigTest(TestCase):
    """Test ProgramFieldConfig model behaviour."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Home Visiting")

    def tearDown(self):
        enc_module._fernet = None

    def test_default_tier_is_standard(self):
        config = ProgramFieldConfig.objects.create(program=self.program)
        self.assertEqual(config.data_tier, "standard")

    def test_profile_sets_form_defaults_on_save(self):
        """Saving with a profile should set the correct form toggles."""
        config = ProgramFieldConfig(program=self.program, profile="group")
        config.save()
        self.assertTrue(config.form_session_attendance)
        self.assertFalse(config.form_visit_note)
        self.assertFalse(config.form_circle_observation)

    def test_home_visiting_profile(self):
        config = ProgramFieldConfig(program=self.program, profile="home_visiting")
        config.save()
        self.assertFalse(config.form_session_attendance)
        self.assertTrue(config.form_visit_note)
        self.assertFalse(config.form_circle_observation)

    def test_full_field_profile(self):
        config = ProgramFieldConfig(program=self.program, profile="full_field")
        config.save()
        self.assertTrue(config.form_session_attendance)
        self.assertTrue(config.form_visit_note)
        self.assertTrue(config.form_circle_observation)

    def test_circle_profile(self):
        config = ProgramFieldConfig(program=self.program, profile="circle")
        config.save()
        self.assertFalse(config.form_session_attendance)
        self.assertTrue(config.form_visit_note)
        self.assertTrue(config.form_circle_observation)

    def test_enabled_forms_property(self):
        config = ProgramFieldConfig(program=self.program, profile="full_field")
        config.save()
        self.assertEqual(
            config.enabled_forms,
            ["session_attendance", "visit_note", "circle_observation"],
        )

    def test_entity_fields_restricted(self):
        config = ProgramFieldConfig(program=self.program, data_tier="restricted")
        self.assertEqual(config.entity_fields_for_tier, ["id"])

    def test_entity_fields_standard(self):
        config = ProgramFieldConfig(program=self.program, data_tier="standard")
        self.assertEqual(config.entity_fields_for_tier, ["id", "first_name"])

    def test_entity_fields_field(self):
        config = ProgramFieldConfig(program=self.program, data_tier="field")
        self.assertEqual(config.entity_fields_for_tier, ["id", "first_name", "last_initial"])

    def test_entity_fields_field_contact(self):
        config = ProgramFieldConfig(program=self.program, data_tier="field_contact")
        self.assertEqual(
            config.entity_fields_for_tier,
            ["id", "first_name", "last_initial", "phone"],
        )


# ------------------------------------------------------------------
# ODK Client tests (mocked HTTP)
# ------------------------------------------------------------------

class ODKCentralClientTest(TestCase):
    """Test the ODK Central API client with mocked HTTP responses."""

    def setUp(self):
        self.client = ODKCentralClient(
            base_url="https://odk.example.com",
            email="admin@example.com",
            password="secret",
        )

    @patch("apps.field_collection.odk_client.requests.Session")
    def test_authentication(self, MockSession):
        mock_session = MockSession.return_value
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"token": "test-token-123"}
        mock_session.post.return_value = mock_resp

        self.client._session = mock_session
        self.client._authenticate()

        self.assertEqual(self.client._token, "test-token-123")
        mock_session.post.assert_called_once_with(
            "https://odk.example.com/v1/sessions",
            json={"email": "admin@example.com", "password": "secret"},
            timeout=30,
        )

    @patch("apps.field_collection.odk_client.requests.Session")
    def test_authentication_failure(self, MockSession):
        mock_session = MockSession.return_value
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_session.post.return_value = mock_resp

        self.client._session = mock_session

        with self.assertRaises(ODKCentralError) as ctx:
            self.client._authenticate()
        self.assertIn("401", str(ctx.exception))

    def test_create_project(self):
        """Test project creation with mocked HTTP."""
        self.client._token = "fake-token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 42, "name": "Test Project"}
        self.client._session = MagicMock()
        self.client._session.request.return_value = mock_resp
        self.client._session.headers = {}

        result = self.client.create_project("Test Project")
        self.assertEqual(result["id"], 42)

    def test_create_entity(self):
        """Test entity creation with mocked HTTP."""
        self.client._token = "fake-token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "uuid": "test-uuid",
            "currentVersion": {"label": "Maria", "data": {"first_name": "Maria"}},
        }
        self.client._session = MagicMock()
        self.client._session.request.return_value = mock_resp
        self.client._session.headers = {}

        result = self.client.create_entity(
            project_id=1,
            dataset_name="Participants",
            label="Maria",
            data={"first_name": "Maria", "konote_id": "42"},
            uuid="test-uuid",
        )
        self.assertEqual(result["uuid"], "test-uuid")


# ------------------------------------------------------------------
# Admin view tests
# ------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FieldCollectionAdminViewsTest(TestCase):
    """Test admin views for field collection configuration."""

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False,
        )
        self.program = Program.objects.create(name="Home Visiting")

    def tearDown(self):
        enc_module._fernet = None

    def test_list_view_requires_admin(self):
        """Non-admin users cannot access the field collection list."""
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get("/admin/field-collection/")
        self.assertNotEqual(resp.status_code, 200)

    def test_list_view_shows_programs(self):
        """Admin can see all active programs with their field collection status."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get("/admin/field-collection/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Home Visiting")

    def test_edit_view_shows_form(self):
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.get(f"/admin/field-collection/{self.program.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Field Collection")
        self.assertContains(resp, "Home Visiting")

    def test_edit_view_saves_config(self):
        """POST to edit view creates/updates ProgramFieldConfig."""
        self.http_client.login(username="admin", password="testpass123")
        resp = self.http_client.post(
            f"/admin/field-collection/{self.program.pk}/",
            {
                "enabled": "on",
                "data_tier": "field",
                "profile": "home_visiting",
            },
        )
        self.assertEqual(resp.status_code, 302)  # redirect on success

        config = ProgramFieldConfig.objects.get(program=self.program)
        self.assertTrue(config.enabled)
        self.assertEqual(config.data_tier, "field")
        self.assertEqual(config.profile, "home_visiting")

    def test_edit_view_requires_admin(self):
        self.http_client.login(username="staff", password="testpass123")
        resp = self.http_client.get(f"/admin/field-collection/{self.program.pk}/")
        self.assertNotEqual(resp.status_code, 200)


# ------------------------------------------------------------------
# Sync run model tests
# ------------------------------------------------------------------

class SyncRunTest(TestCase):
    """Test SyncRun model."""

    def test_create_sync_run(self):
        run = SyncRun.objects.create(
            direction="both",
            programs_synced="1,2,3",
        )
        self.assertEqual(run.status, "running")
        self.assertEqual(run.participants_pushed, 0)

    def test_sync_run_str(self):
        run = SyncRun.objects.create(direction="push")
        self.assertIn("push", str(run))


# ------------------------------------------------------------------
# Push logic tests (unit tests with mocked ODK client)
# ------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PushEntitiesTest(TestCase):
    """Test participant entity generation for push."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")

    def tearDown(self):
        enc_module._fernet = None

    def _create_participant(self, first_name, last_name, phone=""):
        """Helper to create an enrolled participant."""
        client_file = ClientFile.objects.create(status="active")
        client_file.first_name = first_name
        client_file.last_name = last_name
        if phone:
            client_file.phone = phone
        client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=client_file,
            program=self.program,
            status="active",
        )
        return client_file

    def test_standard_tier_entity_fields(self):
        """Standard tier should include ID + first name only."""
        cf = self._create_participant("Maria", "Garcia", "555-1234")

        config = ProgramFieldConfig.objects.create(
            program=self.program, enabled=True, data_tier="standard",
        )

        # Import the sync command to test its helper
        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        entities = cmd._get_participants_for_push(config)

        self.assertEqual(len(entities), 1)
        entity = entities[0]
        self.assertEqual(entity["data"]["first_name"], "Maria")
        self.assertNotIn("last_initial", entity["data"])
        self.assertNotIn("phone", entity["data"])

    def test_field_tier_includes_last_initial(self):
        cf = self._create_participant("Maria", "Garcia")

        config = ProgramFieldConfig.objects.create(
            program=self.program, enabled=True, data_tier="field",
        )

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        entities = cmd._get_participants_for_push(config)

        self.assertEqual(entities[0]["data"]["last_initial"], "G")
        self.assertNotIn("phone", entities[0]["data"])

    def test_field_contact_tier_includes_phone(self):
        cf = self._create_participant("Maria", "Garcia", "555-1234")

        config = ProgramFieldConfig.objects.create(
            program=self.program, enabled=True, data_tier="field_contact",
        )

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        entities = cmd._get_participants_for_push(config)

        self.assertEqual(entities[0]["data"]["phone"], "555-1234")

    def test_restricted_tier_id_only(self):
        cf = self._create_participant("Maria", "Garcia")

        config = ProgramFieldConfig.objects.create(
            program=self.program, enabled=True, data_tier="restricted",
        )

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        entities = cmd._get_participants_for_push(config)

        self.assertNotIn("first_name", entities[0]["data"])
        self.assertNotIn("last_initial", entities[0]["data"])
        self.assertEqual(entities[0]["data"]["konote_id"], str(cf.pk))


# ------------------------------------------------------------------
# Import logic tests
# ------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ImportAttendanceTest(TestCase):
    """Test attendance import from ODK submissions."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Youth Rec")
        self.config = ProgramFieldConfig.objects.create(
            program=self.program, enabled=True, profile="group",
        )
        self.group = Group.objects.create(
            name="Tuesday Circle", program=self.program, group_type="group",
        )
        # Create members
        self.cf1 = ClientFile.objects.create(status="active")
        self.cf1.first_name = "Maria"
        self.cf1.save()
        self.m1 = GroupMembership.objects.create(
            group=self.group, client_file=self.cf1,
        )
        self.cf2 = ClientFile.objects.create(status="active")
        self.cf2.first_name = "James"
        self.cf2.save()
        self.m2 = GroupMembership.objects.create(
            group=self.group, client_file=self.cf2,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_import_attendance_creates_session(self):
        """Importing an attendance submission creates a GroupSession."""
        submissions = [{
            "group_konote_id": str(self.group.pk),
            "session_date": "2026-02-24",
            "members_present": str(self.m1.pk),
            "session_notes": "Good session",
        }]

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        created, skipped = cmd._import_attendance(submissions, self.config)

        self.assertEqual(created, 1)
        self.assertEqual(skipped, 0)

        session = GroupSession.objects.get(group=self.group)
        self.assertEqual(session.session_date, date(2026, 2, 24))

        # Check attendance: m1 present, m2 absent
        att1 = GroupSessionAttendance.objects.get(membership=self.m1)
        self.assertTrue(att1.present)
        att2 = GroupSessionAttendance.objects.get(membership=self.m2)
        self.assertFalse(att2.present)

    def test_import_attendance_dedup(self):
        """Duplicate session for same group+date is skipped."""
        # Create existing session
        GroupSession.objects.create(
            group=self.group, session_date=date(2026, 2, 24),
        )

        submissions = [{
            "group_konote_id": str(self.group.pk),
            "session_date": "2026-02-24",
            "members_present": str(self.m1.pk),
        }]

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        created, skipped = cmd._import_attendance(submissions, self.config)

        self.assertEqual(created, 0)
        self.assertEqual(skipped, 1)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ImportVisitNotesTest(TestCase):
    """Test visit note import from ODK submissions."""

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Home Visiting")
        self.config = ProgramFieldConfig.objects.create(
            program=self.program, enabled=True, profile="home_visiting",
        )
        self.cf = ClientFile.objects.create(status="active")
        self.cf.first_name = "Maria"
        self.cf.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_import_visit_note_creates_progress_note(self):
        """Importing a visit note creates a quick ProgressNote."""
        from apps.notes.models import ProgressNote

        submissions = [{
            "participant_konote_id": str(self.cf.pk),
            "visit_date": "2026-02-24",
            "visit_type": "home_visit",
            "observations": "Maria was in good spirits. Garden project going well.",
            "engagement": "4",
            "alliance_rating": "4",
        }]

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        created, skipped = cmd._import_visit_notes(submissions, self.config)

        self.assertEqual(created, 1)
        note = ProgressNote.objects.get(client_file=self.cf)
        self.assertEqual(note.note_type, "quick")
        self.assertEqual(note.interaction_type, "home_visit")
        self.assertIn("good spirits", note.notes_text)

    def test_import_skip_unknown_participant(self):
        """Submissions with unknown participant IDs are skipped."""
        submissions = [{
            "participant_konote_id": "99999",
            "visit_date": "2026-02-24",
            "visit_type": "home_visit",
            "observations": "Test",
        }]

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        created, skipped = cmd._import_visit_notes(submissions, self.config)

        self.assertEqual(created, 0)
        self.assertEqual(skipped, 1)

    def test_import_skip_empty_observations(self):
        """Submissions with no observations text are skipped."""
        submissions = [{
            "participant_konote_id": str(self.cf.pk),
            "visit_date": "2026-02-24",
            "visit_type": "home_visit",
            "observations": "",
        }]

        from apps.field_collection.management.commands.sync_odk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        created, skipped = cmd._import_visit_notes(submissions, self.config)

        self.assertEqual(created, 0)
        self.assertEqual(skipped, 1)
