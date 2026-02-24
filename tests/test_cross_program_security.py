"""Tests for cross-program permission leakage — users must not access data
from programs they aren't assigned to by manipulating URL IDs.

Covers group views (membership_remove, milestone_create/edit, outcome_create)
and plans views (target_history).
"""
from django.test import TestCase, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.groups.models import (
    Group,
    GroupMembership,
    ProjectMilestone,
    ProjectOutcome,
)
from apps.plans.models import PlanSection, PlanTarget, PlanTargetRevision
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CrossProgramSecurityTest(TestCase):
    """Verify that staff in Program A cannot access Program B data."""

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None

        # Programs
        cls.program_a = Program.objects.create(name="Housing Support", status="active")
        cls.program_b = Program.objects.create(name="Youth Services", status="active")

        # Staff user — access to Program A only
        cls.staff = User.objects.create_user(
            username="casey", password="testpass123", display_name="Casey Worker",
        )
        UserProgramRole.objects.create(
            user=cls.staff, program=cls.program_a, role="staff",
        )

        # Group in Program A (accessible)
        cls.group_a = Group.objects.create(
            name="Housing Workshop", program=cls.program_a, group_type="project",
        )

        # Group in Program B (should be blocked)
        cls.group_b = Group.objects.create(
            name="Youth Coding Club", program=cls.program_b, group_type="project",
        )
        cls.membership_b = GroupMembership.objects.create(
            group=cls.group_b, member_name="Test Member",
        )
        cls.milestone_b = ProjectMilestone.objects.create(
            group=cls.group_b, title="Launch Day",
        )

        # Client in Program B with plan data (should be blocked)
        cls.client_b = ClientFile.objects.create(is_demo=False, status="active")
        ClientProgramEnrolment.objects.create(
            client_file=cls.client_b, program=cls.program_b,
        )
        section_b = PlanSection.objects.create(
            client_file=cls.client_b, name="Youth Goals", program=cls.program_b,
        )
        cls.target_b = PlanTarget.objects.create(
            plan_section=section_b, client_file=cls.client_b,
            name="Complete coding course",
        )
        PlanTargetRevision.objects.create(
            plan_target=cls.target_b,
            name="Complete coding course",
            status="active",
            changed_by=cls.staff,
        )

    def setUp(self):
        enc_module._fernet = None
        self.client.login(username="casey", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    # --- Cross-program access should be blocked ---

    def test_membership_remove_blocked_cross_program(self):
        """Staff in Program A cannot remove a member from Program B's group."""
        resp = self.client.post(
            f"/groups/member/{self.membership_b.pk}/remove/",
        )
        self.assertEqual(resp.status_code, 403)
        # Membership should still be active
        self.membership_b.refresh_from_db()
        self.assertEqual(self.membership_b.status, "active")

    def test_milestone_create_blocked_cross_program(self):
        """Staff in Program A cannot create a milestone in Program B's group."""
        resp = self.client.post(
            f"/groups/{self.group_b.pk}/milestone/",
            {"title": "Hacked Milestone", "status": "not_started"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_milestone_edit_blocked_cross_program(self):
        """Staff in Program A cannot edit a milestone in Program B's group."""
        resp = self.client.get(
            f"/groups/milestone/{self.milestone_b.pk}/edit/",
        )
        self.assertEqual(resp.status_code, 403)

    def test_outcome_create_blocked_cross_program(self):
        """Staff in Program A cannot record an outcome in Program B's group."""
        resp = self.client.post(
            f"/groups/{self.group_b.pk}/outcome/",
            {
                "outcome_date": "2026-01-15",
                "description": "Hacked outcome",
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_target_history_blocked_cross_program(self):
        """Staff in Program A cannot view target history for Program B client."""
        resp = self.client.get(
            f"/plans/targets/{self.target_b.pk}/history/",
        )
        self.assertEqual(resp.status_code, 403)

    # --- Own program access still works ---

    def test_own_program_group_accessible(self):
        """Staff in Program A can still access their own program's group."""
        resp = self.client.get(f"/groups/{self.group_a.pk}/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CrossProgramConsentTest(TestCase):
    """Verify PHIPA consent enforcement filters notes correctly."""

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None

        # Two programs
        cls.program_a = Program.objects.create(name="Housing Support", status="active")
        cls.program_b = Program.objects.create(name="Mental Health", status="active")

        # Multi-program staff — access to both programs
        cls.multi_staff = User.objects.create_user(
            username="multi", password="testpass123", display_name="Multi Worker",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_a, role="staff",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_b, role="staff",
        )

        # Client enrolled in both programs
        cls.shared_client = ClientFile.objects.create(
            is_demo=False, status="active",
        )
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_a, status="enrolled",
        )
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_b, status="enrolled",
        )

        # Notes in each program
        from apps.notes.models import ProgressNote
        cls.note_a = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_a, note_type="quick",
            notes_text="Housing note",
        )
        cls.note_b = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_b, note_type="quick",
            notes_text="Mental health note",
        )
        # Legacy note with no program
        cls.note_null = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=None, note_type="quick",
            notes_text="Legacy note",
        )

    def setUp(self):
        enc_module._fernet = None
        self.client.login(username="multi", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def _set_agency_sharing(self, enabled):
        """Set the agency-level cross_program_note_sharing toggle."""
        from django.core.cache import cache
        from apps.admin_settings.models import FeatureToggle
        cache.clear()
        FeatureToggle.objects.update_or_create(
            feature_key="cross_program_note_sharing",
            defaults={"is_enabled": enabled},
        )

    def test_agency_on_client_default_sees_all_notes(self):
        """Agency sharing ON + client default -> all notes visible."""
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_a.pk, note_ids)
        self.assertIn(self.note_b.pk, note_ids)
        self.assertIn(self.note_null.pk, note_ids)

    def test_agency_on_client_restrict_sees_one_program(self):
        """Agency sharing ON + client restrict -> only viewing program notes."""
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        # Should see one program's note + null note, but NOT both programs
        self.assertIn(self.note_null.pk, note_ids)
        # Exactly one of note_a or note_b visible (depends on get_author_program)
        has_a = self.note_a.pk in note_ids
        has_b = self.note_b.pk in note_ids
        self.assertTrue(has_a != has_b, "Should see exactly one program's notes")

    def test_agency_off_client_default_sees_one_program(self):
        """Agency sharing OFF + client default -> only viewing program notes."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_null.pk, note_ids)
        has_a = self.note_a.pk in note_ids
        has_b = self.note_b.pk in note_ids
        self.assertTrue(has_a != has_b, "Should see exactly one program's notes")

    def test_agency_off_client_consent_sees_all_notes(self):
        """Agency sharing OFF + client consent -> all notes visible."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "consent"
        self.shared_client.save()
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_a.pk, note_ids)
        self.assertIn(self.note_b.pk, note_ids)

    def test_single_shared_program_no_op(self):
        """Single shared program -> filter is a no-op regardless of settings."""
        # Create single-program staff
        single_staff = User.objects.create_user(
            username="single", password="testpass123", display_name="Single Worker",
        )
        UserProgramRole.objects.create(
            user=single_staff, program=self.program_a, role="staff",
        )
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        self.client.login(username="single", password="testpass123")
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        # Single-program user always sees their program's notes + null
        self.assertIn(self.note_a.pk, note_ids)
        self.assertIn(self.note_null.pk, note_ids)
        self.assertNotIn(self.note_b.pk, note_ids)

    def test_null_author_program_always_visible(self):
        """Notes with author_program=None always visible regardless of consent."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        note_ids = {n.pk for n in resp.context["page"].object_list}
        self.assertIn(self.note_null.pk, note_ids)

    def test_template_indicator_shown_when_filtering(self):
        """Template shows indicator when consent filtering is active."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context.get("consent_viewing_program"))

    def test_template_indicator_hidden_when_sharing(self):
        """Template does NOT show indicator when sharing is enabled."""
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(f"/notes/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context.get("consent_viewing_program"))

    # ── PHIPA-ENFORCE1: direct URL and timeline consent tests ──────────

    def _get_viewing_and_restricted_notes(self):
        """Determine which note is in the viewing program and which is restricted.

        get_author_program picks the highest-ranked shared program. Since
        both roles are "staff", the result depends on DB ordering. This
        helper makes tests agnostic about which program is chosen.
        """
        from apps.programs.access import get_author_program
        viewing = get_author_program(self.multi_staff, self.shared_client)
        if viewing.pk == self.program_a.pk:
            return self.note_a, self.note_b
        return self.note_b, self.note_a

    def test_direct_url_restricted_note_returns_403(self):
        """Direct URL to a note from another program when restricted -> 403."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        _, restricted_note = self._get_viewing_and_restricted_notes()
        resp = self.client.get(f"/notes/{restricted_note.pk}/")
        self.assertEqual(resp.status_code, 403)

    def test_direct_url_allowed_note_returns_200(self):
        """Direct URL to a note from viewing program when restricted -> 200."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        allowed_note, _ = self._get_viewing_and_restricted_notes()
        resp = self.client.get(f"/notes/{allowed_note.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_null_program_note_accessible_via_direct_url(self):
        """Legacy note (null author_program) always accessible regardless of consent."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(f"/notes/{self.note_null.pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_event_timeline_respects_consent(self):
        """Event timeline only shows notes from viewing program when restricted."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(f"/events/participant/{self.shared_client.pk}/")
        self.assertEqual(resp.status_code, 200)
        note_entries = [e for e in resp.context["timeline"] if e["type"] == "note"]
        note_ids = {e["obj"].pk for e in note_entries}
        # Should see one program's note + null note, but not both programs
        self.assertIn(self.note_null.pk, note_ids)
        has_a = self.note_a.pk in note_ids
        has_b = self.note_b.pk in note_ids
        self.assertTrue(has_a != has_b, "Timeline should show only one program's notes")

    def test_apply_consent_filter_fail_closed_no_viewing_program(self):
        """When sharing is OFF and no viewing program found, return empty queryset.

        DRR decision #9: fail-closed is safer than fail-open for a privacy
        feature. A bug here should result in 'can't see notes' (safe)
        rather than 'can see everything' (unsafe).
        """
        from apps.notes.models import ProgressNote
        from apps.programs.access import apply_consent_filter
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()

        # Create a user with NO shared programs with the client
        no_shared = User.objects.create_user(
            username="noshared", password="testpass123",
            display_name="No Shared Worker",
        )
        program_c = Program.objects.create(name="Program C", status="active")
        UserProgramRole.objects.create(
            user=no_shared, program=program_c, role="staff",
        )

        notes_qs = ProgressNote.objects.filter(client_file=self.shared_client)
        filtered, viewing_name = apply_consent_filter(
            notes_qs, self.shared_client, no_shared,
            user_program_ids={program_c.pk},
        )
        # Fail-closed: empty queryset, not the original notes
        self.assertEqual(filtered.count(), 0)
        self.assertIsNone(viewing_name)

    def test_consent_filter_respects_conf9_context_switcher(self):
        """CONF9: active_program_ids overrides get_author_program for viewing program.

        When the context switcher selects a single program, the consent
        filter should use that program — not whatever get_author_program
        would pick based on role rank.
        """
        from apps.notes.models import ProgressNote
        from apps.programs.access import apply_consent_filter, get_author_program
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()

        # Determine which program get_author_program would normally pick
        default_viewing = get_author_program(self.multi_staff, self.shared_client)
        # Pick the OTHER program via CONF9 switcher
        if default_viewing.pk == self.program_a.pk:
            switched_program = self.program_b
            expected_note = self.note_b
            excluded_note = self.note_a
        else:
            switched_program = self.program_a
            expected_note = self.note_a
            excluded_note = self.note_b

        notes_qs = ProgressNote.objects.filter(client_file=self.shared_client)
        filtered, viewing_name = apply_consent_filter(
            notes_qs, self.shared_client, self.multi_staff,
            user_program_ids={switched_program.pk},
            active_program_ids={switched_program.pk},
        )
        filtered_ids = set(filtered.values_list("pk", flat=True))
        # Should see the switched program's note + null, NOT the default
        self.assertIn(expected_note.pk, filtered_ids)
        self.assertIn(self.note_null.pk, filtered_ids)
        self.assertNotIn(excluded_note.pk, filtered_ids)
        self.assertEqual(viewing_name, switched_program.name)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SearchConsentTest(TestCase):
    """PHIPA-SEARCH1: Verify note search respects consent filtering.

    _find_clients_with_matching_notes() must not reveal that a restricted-
    program note contains a search term (side-channel disclosure).
    """

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None

        # Two programs
        cls.program_a = Program.objects.create(name="Housing Support", status="active")
        cls.program_b = Program.objects.create(name="Substance Use", status="active")

        # Staff user — access to Program A only
        cls.staff_a = User.objects.create_user(
            username="searcher", password="testpass123", display_name="Search Worker",
        )
        UserProgramRole.objects.create(
            user=cls.staff_a, program=cls.program_a, role="staff",
        )

        # Multi-program staff — access to both programs
        cls.multi_staff = User.objects.create_user(
            username="multisearch", password="testpass123", display_name="Multi Search",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_a, role="staff",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_b, role="staff",
        )

        # Client enrolled in both programs
        cls.shared_client = ClientFile.objects.create(is_demo=False, status="active")
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_a, status="enrolled",
        )
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_b, status="enrolled",
        )

        # Note in Program A with searchable term
        from apps.notes.models import ProgressNote
        cls.note_a = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_a, note_type="quick",
            notes_text="Housing intake completed",
        )
        # Note in Program B with a different searchable term
        cls.note_b = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_b, note_type="quick",
            notes_text="Discussed relapse prevention strategies",
        )

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def _set_agency_sharing(self, enabled):
        from django.core.cache import cache
        from apps.admin_settings.models import FeatureToggle
        cache.clear()
        FeatureToggle.objects.update_or_create(
            feature_key="cross_program_note_sharing",
            defaults={"is_enabled": enabled},
        )

    def test_search_does_not_find_restricted_program_notes(self):
        """PHIPA-SEARCH1: User searches a term only in a restricted program
        note — should NOT match (prevents side-channel disclosure)."""
        from apps.clients.views import _find_clients_with_matching_notes
        self._set_agency_sharing(True)
        # Client restricts sharing
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()

        # staff_a only has access to Program A — "relapse" is only in Program B note
        matched = _find_clients_with_matching_notes(
            [self.shared_client.pk], "relapse",
            user=self.staff_a,
        )
        self.assertNotIn(self.shared_client.pk, matched)

    def test_search_finds_accessible_program_notes(self):
        """PHIPA-SEARCH1: User searches a term in their own program's note — should match."""
        from apps.clients.views import _find_clients_with_matching_notes
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()

        # staff_a has access to Program A — "housing" is in Program A note
        matched = _find_clients_with_matching_notes(
            [self.shared_client.pk], "housing",
            user=self.staff_a,
        )
        self.assertIn(self.shared_client.pk, matched)

    def test_search_respects_client_restrict_override(self):
        """PHIPA-SEARCH1: Client with restrict flag — search shouldn't find
        cross-program notes even if agency sharing is on."""
        from apps.clients.views import _find_clients_with_matching_notes
        from apps.programs.access import get_author_program
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()

        # Multi-staff has access to both programs; determine which is viewing
        viewing = get_author_program(self.multi_staff, self.shared_client)
        if viewing.pk == self.program_a.pk:
            restricted_term = "relapse"  # Only in Program B note
        else:
            restricted_term = "housing"  # Only in Program A note

        matched = _find_clients_with_matching_notes(
            [self.shared_client.pk], restricted_term,
            user=self.multi_staff,
        )
        self.assertNotIn(self.shared_client.pk, matched)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class QualitativeSummaryConsentTest(TestCase):
    """PHIPA-QUAL1: Verify qualitative_summary respects consent filtering.

    qualitative_summary shows client words (direct quotes) from note entries
    — must not show cross-program entries when sharing is restricted.
    """

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None

        # Two programs
        cls.program_a = Program.objects.create(name="Housing Support", status="active")
        cls.program_b = Program.objects.create(name="Mental Health", status="active")

        # Multi-program staff
        cls.multi_staff = User.objects.create_user(
            username="qualuser", password="testpass123", display_name="Qual Worker",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_a, role="staff",
        )
        UserProgramRole.objects.create(
            user=cls.multi_staff, program=cls.program_b, role="staff",
        )

        # Client enrolled in both programs
        cls.shared_client = ClientFile.objects.create(is_demo=False, status="active")
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_a, status="enrolled",
        )
        ClientProgramEnrolment.objects.create(
            client_file=cls.shared_client, program=cls.program_b, status="enrolled",
        )

        # Plan target for the client
        from apps.plans.models import PlanSection, PlanTarget
        section = PlanSection.objects.create(
            client_file=cls.shared_client, name="Goals", program=cls.program_a,
        )
        cls.target = PlanTarget.objects.create(
            plan_section=section, client_file=cls.shared_client,
            name="Stable housing",
        )

        # Progress notes + target entries from each program
        from apps.notes.models import ProgressNote, ProgressNoteTarget
        cls.note_a = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_a, note_type="full",
            notes_text="Housing session",
        )
        cls.entry_a = ProgressNoteTarget.objects.create(
            progress_note=cls.note_a, plan_target=cls.target,
            progress_descriptor="shifting",
        )
        cls.entry_a.client_words = "I feel safer now"
        cls.entry_a.save()

        cls.note_b = ProgressNote.objects.create(
            client_file=cls.shared_client, author=cls.multi_staff,
            author_program=cls.program_b, note_type="full",
            notes_text="Mental health session",
        )
        cls.entry_b = ProgressNoteTarget.objects.create(
            progress_note=cls.note_b, plan_target=cls.target,
            progress_descriptor="holding",
        )
        cls.entry_b.client_words = "Still working through anxiety"
        cls.entry_b.save()

    def setUp(self):
        enc_module._fernet = None
        self.client.login(username="qualuser", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    def _set_agency_sharing(self, enabled):
        from django.core.cache import cache
        from apps.admin_settings.models import FeatureToggle
        cache.clear()
        FeatureToggle.objects.update_or_create(
            feature_key="cross_program_note_sharing",
            defaults={"is_enabled": enabled},
        )

    def test_qualitative_summary_filters_by_consent(self):
        """PHIPA-QUAL1: Client with restricted sharing — qualitative summary
        only shows viewing program entries."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(
            f"/notes/participant/{self.shared_client.pk}/qualitative/"
        )
        self.assertEqual(resp.status_code, 200)
        # Should show entries from only one program (viewing program)
        target_data = resp.context["target_data"]
        self.assertEqual(len(target_data), 1)
        # total_entries should be 1 (only viewing program), not 2
        self.assertEqual(target_data[0]["total_entries"], 1)

    def test_qualitative_summary_shows_all_when_sharing_on(self):
        """PHIPA-QUAL1: Sharing on — qualitative summary shows all entries."""
        self._set_agency_sharing(True)
        self.shared_client.cross_program_sharing = "default"
        self.shared_client.save()
        resp = self.client.get(
            f"/notes/participant/{self.shared_client.pk}/qualitative/"
        )
        self.assertEqual(resp.status_code, 200)
        target_data = resp.context["target_data"]
        self.assertEqual(len(target_data), 1)
        # Both entries should be visible
        self.assertEqual(target_data[0]["total_entries"], 2)

    def test_qualitative_summary_shows_consent_banner(self):
        """PHIPA-QUAL1: When filtering is active, template shows the consent banner."""
        self._set_agency_sharing(False)
        self.shared_client.cross_program_sharing = "restrict"
        self.shared_client.save()
        resp = self.client.get(
            f"/notes/participant/{self.shared_client.pk}/qualitative/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context.get("consent_viewing_program"))
        # Banner text should be in the response
        self.assertContains(resp, "Cross-program sharing is not enabled")
