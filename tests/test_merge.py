"""Tests for the duplicate client merge tool (MATCH4).

Covers: candidate finding, comparison, merge execution, security rules,
constraint handling, view permissions, and audit logging.
"""
from django.test import Client as HttpClient
from django.test import TestCase, override_settings
from django.utils import timezone

from cryptography.fernet import Fernet

from apps.audit.models import AuditLog
from apps.auth_app.models import User
from apps.clients.merge import (
    _get_all_confidential_client_ids,
    _validate_merge_preconditions,
    build_comparison,
    execute_merge,
    find_merge_candidates,
)
from apps.clients.models import (
    ClientDetailValue,
    ClientFile,
    ClientMerge,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
    ErasureRequest,
)
from apps.events.models import Alert, Event, EventType
from apps.groups.models import Group, GroupMembership
from apps.notes.models import ProgressNote
from apps.plans.models import PlanSection, PlanTarget
from apps.programs.models import Program, UserProgramRole

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MergeCandidatesTest(TestCase):
    """Test finding merge candidates."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )

        self.prog_a = Program.objects.create(name="Employment", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Youth Services", colour_hex="#3B82F6")
        self.conf_prog = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )
        UserProgramRole.objects.create(
            user=self.admin, program=self.prog_a, role="program_manager",
        )

    def _make_client(self, first_name, last_name, phone="", birth_date="", program=None):
        client = ClientFile()
        client.first_name = first_name
        client.last_name = last_name
        if phone:
            client.phone = phone
        if birth_date:
            client._birth_date_encrypted = enc_module.encrypt_field(birth_date)
        client.save()
        if program:
            ClientProgramEnrolment.objects.create(client_file=client, program=program)
        return client

    def test_finds_phone_match_candidates(self):
        c1 = self._make_client("Jane", "Doe", phone="(613) 555-1234", program=self.prog_a)
        c2 = self._make_client("Janet", "Smith", phone="(613) 555-1234", program=self.prog_b)
        results = find_merge_candidates(self.admin)
        self.assertEqual(results["phone_count"], 1)
        pair = results["phone"][0]
        ids = {pair["client_a"]["client_id"], pair["client_b"]["client_id"]}
        self.assertEqual(ids, {c1.pk, c2.pk})

    def test_finds_name_dob_match_candidates(self):
        self._make_client("Jane", "Doe", birth_date="2000-01-15", program=self.prog_a)
        self._make_client("Jane", "Smith", birth_date="2000-01-15", program=self.prog_b)
        results = find_merge_candidates(self.admin)
        self.assertEqual(results["name_dob_count"], 1)

    def test_excludes_confidential_clients(self):
        """Client currently enrolled in a confidential programme must not appear."""
        self._make_client("Jane", "Doe", phone="(613) 555-9999", program=self.prog_a)
        self._make_client("Janet", "Doe", phone="(613) 555-9999", program=self.conf_prog)
        results = find_merge_candidates(self.admin)
        self.assertEqual(results["phone_count"], 0)
        self.assertEqual(results["name_dob_count"], 0)

    def test_excludes_historically_confidential_clients(self):
        """Client who was unenrolled from a confidential programme must not appear."""
        c1 = self._make_client("Jane", "Doe", phone="(613) 555-8888", program=self.prog_a)
        c2 = self._make_client("Janet", "Doe", phone="(613) 555-8888", program=self.prog_b)
        # Also give c2 a HISTORICAL confidential enrolment (unenrolled)
        ClientProgramEnrolment.objects.create(
            client_file=c2, program=self.conf_prog, status="unenrolled",
        )
        results = find_merge_candidates(self.admin)
        # c2 should be excluded due to historical confidential enrolment
        self.assertEqual(results["phone_count"], 0)

    def test_excludes_anonymised_clients(self):
        self._make_client("Jane", "Doe", phone="(613) 555-7777", program=self.prog_a)
        c2 = self._make_client("Janet", "Doe", phone="(613) 555-7777", program=self.prog_b)
        c2.is_anonymised = True
        c2.save()
        results = find_merge_candidates(self.admin)
        self.assertEqual(results["phone_count"], 0)

    def test_respects_demo_real_separation(self):
        """Demo admin should not see real clients as candidates."""
        self._make_client("Jane", "Doe", phone="(613) 555-6666", program=self.prog_a)
        self._make_client("Janet", "Doe", phone="(613) 555-6666", program=self.prog_b)
        demo_admin = User.objects.create_user(
            username="demo_admin", password="testpass123", is_admin=True, is_demo=True,
        )
        results = find_merge_candidates(demo_admin)
        self.assertEqual(results["phone_count"], 0)

    def test_phone_pairs_before_name_dob(self):
        """Phone matches should be returned separately from name/DOB matches."""
        results = find_merge_candidates(self.admin)
        self.assertIn("phone", results)
        self.assertIn("name_dob", results)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MergeComparisonTest(TestCase):
    """Test building side-by-side comparison data."""

    def setUp(self):
        enc_module._fernet = None
        self.prog = Program.objects.create(name="Employment", colour_hex="#10B981")

        self.client_a = ClientFile()
        self.client_a.first_name = "Jane"
        self.client_a.last_name = "Doe"
        self.client_a.phone = "(613) 555-1111"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_a, program=self.prog)

        self.client_b = ClientFile()
        self.client_b.first_name = "Janet"
        self.client_b.last_name = "Doe"
        self.client_b.phone = "(613) 555-2222"
        self.client_b.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_b, program=self.prog)

    def test_identifies_differing_pii_fields(self):
        comp = build_comparison(self.client_a, self.client_b)
        first_name_field = next(
            f for f in comp["pii_fields"] if f["field_name"] == "first_name"
        )
        self.assertTrue(first_name_field["differs"])
        self.assertEqual(first_name_field["value_a"], "Jane")
        self.assertEqual(first_name_field["value_b"], "Janet")

    def test_shows_record_counts(self):
        # Add some notes to client_a
        ProgressNote.objects.create(client_file=self.client_a, note_type="quick")
        ProgressNote.objects.create(client_file=self.client_a, note_type="quick")
        comp = build_comparison(self.client_a, self.client_b)
        self.assertEqual(comp["counts_a"]["notes"], 2)
        self.assertEqual(comp["counts_b"]["notes"], 0)

    def test_identifies_custom_field_conflicts(self):
        group = CustomFieldGroup.objects.create(name="Test Group")
        field_def = CustomFieldDefinition.objects.create(
            name="Referral Source", input_type="text", group=group,
        )
        ClientDetailValue.objects.create(
            client_file=self.client_a, field_def=field_def, value="Hospital",
        )
        ClientDetailValue.objects.create(
            client_file=self.client_b, field_def=field_def, value="Self-referral",
        )
        comp = build_comparison(self.client_a, self.client_b)
        self.assertEqual(len(comp["field_conflicts"]), 1)
        self.assertEqual(comp["field_conflicts"][0]["value_a"], "Hospital")

    def test_shows_post_merge_programmes(self):
        prog_b = Program.objects.create(name="Youth Services", colour_hex="#3B82F6")
        ClientProgramEnrolment.objects.create(client_file=self.client_b, program=prog_b)
        comp = build_comparison(self.client_a, self.client_b)
        self.assertIn("Employment", comp["post_merge_programs"])
        self.assertIn("Youth Services", comp["post_merge_programs"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MergeExecutionTest(TestCase):
    """Test the merge execution — data transfer, anonymisation, auditing."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.prog = Program.objects.create(name="Employment", colour_hex="#10B981")
        UserProgramRole.objects.create(
            user=self.admin, program=self.prog, role="program_manager",
        )

        # Create two clients
        self.kept = ClientFile()
        self.kept.first_name = "Jane"
        self.kept.last_name = "Doe"
        self.kept.phone = "(613) 555-1111"
        self.kept.save()
        ClientProgramEnrolment.objects.create(client_file=self.kept, program=self.prog)

        self.archived = ClientFile()
        self.archived.first_name = "Janet"
        self.archived.last_name = "Doe"
        self.archived.phone = "(613) 555-2222"
        self.archived.save()
        ClientProgramEnrolment.objects.create(client_file=self.archived, program=self.prog)

    def test_transfers_progress_notes(self):
        ProgressNote.objects.create(client_file=self.archived, note_type="quick")
        ProgressNote.objects.create(client_file=self.archived, note_type="full")
        merge = execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        self.assertEqual(
            ProgressNote.objects.filter(client_file=self.kept).count(), 2,
        )
        self.assertEqual(merge.transfer_summary["notes"], 2)

    def test_transfers_events_and_alerts(self):
        et = EventType.objects.create(name="Meeting")
        Event.objects.create(client_file=self.archived, title="Test", event_type=et)
        Alert.objects.create(client_file=self.archived, content="Alert!")
        execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        self.assertEqual(Event.objects.filter(client_file=self.kept).count(), 1)
        self.assertEqual(Alert.objects.filter(client_file=self.kept).count(), 1)

    def test_transfers_plan_sections_and_targets(self):
        section = PlanSection.objects.create(
            client_file=self.archived, name="Housing", program=self.prog,
        )
        PlanTarget.objects.create(
            client_file=self.archived, plan_section=section,
        )
        execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        self.assertEqual(PlanSection.objects.filter(client_file=self.kept).count(), 1)
        self.assertEqual(PlanTarget.objects.filter(client_file=self.kept).count(), 1)

    def test_handles_enrolment_conflicts_preserves_history(self):
        """Duplicate enrolment in same programme is marked unenrolled, not deleted."""
        execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        enrolments = ClientProgramEnrolment.objects.filter(
            client_file=self.kept, program=self.prog,
        )
        # One enrolled (kept's), one unenrolled (archived's, preserved)
        self.assertEqual(enrolments.count(), 2)
        self.assertEqual(enrolments.filter(status="enrolled").count(), 1)
        self.assertEqual(enrolments.filter(status="unenrolled").count(), 1)

    def test_handles_custom_field_conflicts(self):
        """Admin's choice resolves custom field conflicts without IntegrityError."""
        group = CustomFieldGroup.objects.create(name="Test Group")
        field_def = CustomFieldDefinition.objects.create(
            name="Referral Source", input_type="text", group=group,
        )
        ClientDetailValue.objects.create(
            client_file=self.kept, field_def=field_def, value="Hospital",
        )
        ClientDetailValue.objects.create(
            client_file=self.archived, field_def=field_def, value="Self-referral",
        )
        # Admin chooses archived's value
        execute_merge(
            self.kept, self.archived,
            pii_choices={},
            field_resolutions={str(field_def.pk): "archived"},
            user=self.admin,
            ip_address="127.0.0.1",
        )
        cdv = ClientDetailValue.objects.get(client_file=self.kept, field_def=field_def)
        self.assertEqual(cdv.value, "Self-referral")

    def test_handles_group_membership_conflicts(self):
        """Duplicate active group memberships are deactivated, no constraint violation."""
        group = Group.objects.create(name="Basketball", group_type="activity")
        GroupMembership.objects.create(
            client_file=self.kept, group=group, member_name="Jane", status="active",
        )
        GroupMembership.objects.create(
            client_file=self.archived, group=group, member_name="Janet", status="active",
        )
        execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        kept_memberships = GroupMembership.objects.filter(client_file=self.kept, group=group)
        self.assertEqual(kept_memberships.filter(status="active").count(), 1)
        self.assertEqual(kept_memberships.filter(status="inactive").count(), 1)

    def test_anonymises_archived_client(self):
        execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        self.archived.refresh_from_db()
        self.assertTrue(self.archived.is_anonymised)
        self.assertEqual(self.archived.status, "discharged")
        self.assertIn("Merged into", self.archived.status_reason)
        # PII should be cleared
        self.assertEqual(self.archived.first_name, "")
        self.assertEqual(self.archived.phone, "")

    def test_preserves_kept_client_data(self):
        """Kept client's original PII is preserved when admin doesn't choose archived's."""
        execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        self.kept.refresh_from_db()
        self.assertEqual(self.kept.first_name, "Jane")
        self.assertEqual(self.kept.last_name, "Doe")

    def test_applies_pii_choices(self):
        """When admin chooses archived's PII, it's applied to kept client."""
        execute_merge(
            self.kept, self.archived,
            pii_choices={"first_name": "archived", "phone": "archived"},
            field_resolutions={},
            user=self.admin,
            ip_address="127.0.0.1",
        )
        self.kept.refresh_from_db()
        self.assertEqual(self.kept.first_name, "Janet")
        self.assertEqual(self.kept.phone, "(613) 555-2222")

    def test_creates_client_merge_record(self):
        merge = execute_merge(self.kept, self.archived, {}, {}, self.admin, "127.0.0.1")
        self.assertIsInstance(merge, ClientMerge)
        self.assertEqual(merge.kept_client_pk, self.kept.pk)
        self.assertEqual(merge.archived_client_pk, self.archived.pk)
        self.assertEqual(merge.merged_by, self.admin)

    def test_pii_choices_contains_no_pii(self):
        """The pii_choices JSONField stores field names only, never actual PII."""
        merge = execute_merge(
            self.kept, self.archived,
            pii_choices={"first_name": "archived"},
            field_resolutions={},
            user=self.admin,
            ip_address="127.0.0.1",
        )
        # Values should be "kept" or "archived", never actual names
        for key, val in merge.pii_choices.items():
            self.assertIn(val, ("kept", "archived"))
            self.assertNotIn("Jane", val)
            self.assertNotIn("Janet", val)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MergeSecurityTest(TestCase):
    """Test security rules — confidential exclusion, demo separation, erasure blocking."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.prog = Program.objects.create(name="Employment", colour_hex="#10B981")
        self.conf_prog = Program.objects.create(
            name="Counselling", colour_hex="#EF4444", is_confidential=True,
        )

        self.client_a = ClientFile()
        self.client_a.first_name = "Jane"
        self.client_a.last_name = "Doe"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_a, program=self.prog)

        self.client_b = ClientFile()
        self.client_b.first_name = "Janet"
        self.client_b.last_name = "Doe"
        self.client_b.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_b, program=self.prog)

    def test_rejects_confidential_clients(self):
        """Cannot merge a client with any confidential enrolment."""
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.conf_prog,
        )
        errors = _validate_merge_preconditions(self.client_a, self.client_b)
        self.assertTrue(any("confidential" in e.lower() for e in errors))

    def test_rejects_historically_confidential_clients(self):
        """Cannot merge even if confidential enrolment is historical (unenrolled)."""
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.conf_prog, status="unenrolled",
        )
        errors = _validate_merge_preconditions(self.client_a, self.client_b)
        self.assertTrue(any("confidential" in e.lower() for e in errors))

    def test_rejects_anonymised_clients(self):
        self.client_b.is_anonymised = True
        self.client_b.save()
        errors = _validate_merge_preconditions(self.client_a, self.client_b)
        self.assertTrue(any("anonymised" in e.lower() for e in errors))

    def test_rejects_demo_real_mismatch(self):
        self.client_b.is_demo = True
        self.client_b.save()
        errors = _validate_merge_preconditions(self.client_a, self.client_b)
        self.assertTrue(any("demo" in e.lower() for e in errors))

    def test_rejects_pending_erasure_request(self):
        ErasureRequest.objects.create(
            client_file=self.client_b,
            client_pk=self.client_b.pk,
            requested_by=self.admin,
            requested_by_display="admin",
            request_reason="Test",
            status="pending",
        )
        errors = _validate_merge_preconditions(self.client_a, self.client_b)
        self.assertTrue(any("erasure" in e.lower() for e in errors))


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MergeViewsTest(TestCase):
    """Test merge view permissions and basic rendering."""

    def setUp(self):
        enc_module._fernet = None
        self.http = HttpClient()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.staff = User.objects.create_user(
            username="staff", password="testpass123",
        )
        self.prog = Program.objects.create(name="Employment", colour_hex="#10B981")
        UserProgramRole.objects.create(
            user=self.admin, program=self.prog, role="program_manager",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.prog, role="staff",
        )

    def test_candidates_list_requires_admin(self):
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get("/merge/")
        self.assertEqual(resp.status_code, 403)

    def test_candidates_list_accessible_to_admin(self):
        self.http.login(username="admin", password="testpass123")
        resp = self.http.get("/merge/")
        self.assertEqual(resp.status_code, 200)

    def test_compare_view_requires_admin(self):
        c1 = ClientFile()
        c1.first_name = "Jane"
        c1.last_name = "Doe"
        c1.save()
        c2 = ClientFile()
        c2.first_name = "Janet"
        c2.last_name = "Doe"
        c2.save()
        self.http.login(username="staff", password="testpass123")
        resp = self.http.get(f"/merge/{c1.pk}/{c2.pk}/")
        self.assertEqual(resp.status_code, 403)

    def test_compare_view_returns_200_for_admin(self):
        c1 = ClientFile()
        c1.first_name = "Jane"
        c1.last_name = "Doe"
        c1.save()
        ClientProgramEnrolment.objects.create(client_file=c1, program=self.prog)
        c2 = ClientFile()
        c2.first_name = "Janet"
        c2.last_name = "Doe"
        c2.save()
        ClientProgramEnrolment.objects.create(client_file=c2, program=self.prog)
        self.http.login(username="admin", password="testpass123")
        resp = self.http.get(f"/merge/{c1.pk}/{c2.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_merge_requires_login(self):
        resp = self.http.get("/merge/")
        self.assertEqual(resp.status_code, 302)  # Redirect to login
