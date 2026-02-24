"""Tests for Phase 4: Progress Notes views and forms."""
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.notes.models import ProgressNote, ProgressNoteTarget, MetricValue
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class NoteViewsTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.admin = User.objects.create_user(username="admin", password="pass", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)
        self.other_staff = User.objects.create_user(username="other", password="pass", is_admin=False)

        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.other_staff, program=self.prog, role="staff")

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.consent_given_at = timezone.now()  # Set consent for existing tests
        self.client_file.consent_type = "written"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.prog)

        # Unreachable client (different program)
        self.prog_b = Program.objects.create(name="Prog B", colour_hex="#3B82F6")
        self.other_client = ClientFile()
        self.other_client.first_name = "Bob"
        self.other_client.last_name = "Smith"
        self.other_client.status = "active"
        self.other_client.save()
        ClientProgramEnrolment.objects.create(client_file=self.other_client, program=self.prog_b)

    def tearDown(self):
        enc_module._fernet = None

    # -- Quick Notes --

    def test_quick_note_create_happy_path(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Client seemed well today.", "interaction_type": "session", "consent_confirmed": True},
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(client_file=self.client_file)
        self.assertEqual(note.note_type, "quick")
        self.assertEqual(note.notes_text, "Client seemed well today.")
        self.assertEqual(note.author, self.staff)

    def test_quick_note_empty_text_rejected(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "   ", "interaction_type": "session", "consent_confirmed": True},
        )
        self.assertEqual(resp.status_code, 200)  # Re-renders form with errors
        self.assertEqual(ProgressNote.objects.count(), 0)

    def test_quick_note_without_consent_rejected(self):
        """Notes cannot be saved without confirming consent."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Valid text but no consent."},
        )
        self.assertEqual(resp.status_code, 200)  # Re-renders form with errors
        self.assertEqual(ProgressNote.objects.count(), 0)

    def test_staff_cannot_create_note_for_inaccessible_client(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.other_client.pk}/quick/",
            {"notes_text": "Should not work."},
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_without_program_role_blocked_from_notes(self):
        """Admins without program roles cannot access client data (RBAC restriction)."""
        self.http.login(username="admin", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.other_client.pk}/quick/",
            {"notes_text": "Admin note."},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(ProgressNote.objects.count(), 0)

    def test_admin_with_program_role_can_create_note(self):
        """Admins who also have a program role can create notes."""
        UserProgramRole.objects.create(user=self.admin, program=self.prog_b, role="program_manager")
        # Add consent to other_client so note creation is allowed
        self.other_client.consent_given_at = timezone.now()
        self.other_client.consent_type = "written"
        self.other_client.save()
        self.http.login(username="admin", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.other_client.pk}/quick/",
            {"notes_text": "Admin note.", "interaction_type": "session", "consent_confirmed": True},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ProgressNote.objects.count(), 1)

    def test_quick_note_with_phone_interaction_type(self):
        """Quick note stores the selected interaction type and outcome."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Called about housing.", "interaction_type": "phone", "outcome": "reached"},
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(client_file=self.client_file)
        self.assertEqual(note.interaction_type, "phone")
        self.assertEqual(note.outcome, "reached")

    def test_quick_note_sms_interaction_type(self):
        """SMS is a valid interaction type for quick notes."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Texted about appointment.", "interaction_type": "sms", "outcome": "reached"},
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(client_file=self.client_file)
        self.assertEqual(note.interaction_type, "sms")

    def test_quick_note_email_interaction_type(self):
        """Email is a valid interaction type for quick notes."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Sent intake form.", "interaction_type": "email", "outcome": "reached"},
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(client_file=self.client_file)
        self.assertEqual(note.interaction_type, "email")

    def test_quick_note_phone_requires_outcome(self):
        """Phone interaction type requires an outcome selection."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Called.", "interaction_type": "phone", "outcome": ""},
        )
        self.assertEqual(resp.status_code, 200)  # Re-renders form
        self.assertEqual(ProgressNote.objects.count(), 0)

    def test_quick_note_no_answer_notes_optional(self):
        """When outcome is no_answer, notes_text can be blank (auto-filled)."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "", "interaction_type": "phone", "outcome": "no_answer"},
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(client_file=self.client_file)
        self.assertEqual(note.outcome, "no_answer")
        # notes_text should be auto-filled from the outcome label
        self.assertTrue(note.notes_text)

    def test_quick_note_left_message_notes_optional(self):
        """When outcome is left_message, notes_text can be blank."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "", "interaction_type": "sms", "outcome": "left_message"},
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(client_file=self.client_file)
        self.assertEqual(note.outcome, "left_message")

    def test_quick_note_session_no_outcome_needed(self):
        """Session interaction type does not require outcome."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Good session.", "interaction_type": "session"},
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(client_file=self.client_file)
        self.assertEqual(note.outcome, "")

    def test_inline_quick_note_get(self):
        """HTMX inline quick note endpoint returns form partial."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/inline/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Log Contact")

    def test_inline_quick_note_post(self):
        """HTMX inline quick note creates a note and returns buttons."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/inline/",
            {"notes_text": "Quick phone call.", "interaction_type": "phone", "outcome": "reached"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ProgressNote.objects.count(), 1)
        note = ProgressNote.objects.first()
        self.assertEqual(note.interaction_type, "phone")
        self.assertEqual(note.outcome, "reached")

    def test_inline_quick_note_buttons_mode(self):
        """GET with ?mode=buttons returns the button partial."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/inline/?mode=buttons",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Log Contact")

    def test_quick_note_invalid_interaction_type_rejected(self):
        """Invalid interaction type values are rejected by form validation."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Valid text.", "interaction_type": "hacked", "consent_confirmed": True},
        )
        self.assertEqual(resp.status_code, 200)  # Re-renders form with errors
        self.assertEqual(ProgressNote.objects.count(), 0)

    # -- Note List --

    def test_note_list_filtered_by_interaction_type(self):
        """Interaction type filter only shows matching notes."""
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Phone call note", author=self.staff,
            interaction_type="phone",
        )
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Session note", author=self.staff,
            interaction_type="session",
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/?interaction=phone")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Phone call note")
        self.assertNotContains(resp, "Session note")

    def test_note_list_invalid_filter_ignored(self):
        """Invalid interaction filter values are ignored (shows all notes)."""
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Any note", author=self.staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/?interaction=invalid")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Any note")

    def test_note_list_shows_notes(self):
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Test note", author=self.staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test note")

    def test_note_list_filter_by_target(self):
        """Target filter shows only notes linked to the selected target."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        target_a = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Housing",
        )
        target_b = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Employment",
        )

        note_a = ProgressNote.objects.create(
            client_file=self.client_file, note_type="full",
            author=self.staff, interaction_type="session",
        )
        ProgressNoteTarget.objects.create(progress_note=note_a, plan_target=target_a)

        note_b = ProgressNote.objects.create(
            client_file=self.client_file, note_type="full",
            author=self.staff, interaction_type="session",
        )
        ProgressNoteTarget.objects.create(progress_note=note_b, plan_target=target_b)

        self.http.login(username="staff", password="pass")
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/?target={target_a.pk}"
        )
        self.assertEqual(resp.status_code, 200)
        # note_a is linked to target_a, note_b is not
        self.assertContains(resp, f'id="note-{note_a.pk}"')
        self.assertNotContains(resp, f'id="note-{note_b.pk}"')

    def test_note_list_no_target_filter_shows_all(self):
        """No target filter shows all notes regardless of targets."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Housing",
        )
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="full",
            author=self.staff, interaction_type="session",
        )
        ProgressNoteTarget.objects.create(progress_note=note, plan_target=target)

        note_no_target = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Quick note", author=self.staff,
        )

        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'id="note-{note.pk}"')
        self.assertContains(resp, f'id="note-{note_no_target.pk}"')

    def test_note_list_target_dropdown_shows_active_targets(self):
        """Target filter dropdown appears when participant has active targets."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Housing stability",
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "All targets")
        self.assertContains(resp, "Housing stability")

    def test_target_filter_invalid_id_returns_all_notes(self):
        """Non-existent target ID should show all notes (no crash)."""
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Visible note", author=self.staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/?target=99999")
        self.assertEqual(resp.status_code, 200)

    def test_target_filter_non_numeric_ignored(self):
        """Non-numeric target value should be ignored gracefully."""
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Still visible", author=self.staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/?target=abc")
        self.assertEqual(resp.status_code, 200)

    def test_target_filter_with_foreign_target_id(self):
        """Passing a target ID from another client/programme should not crash or leak data."""
        # Create a target in prog_b (staff has no role in prog_b)
        section_b = PlanSection.objects.create(
            client_file=self.other_client, name="Other Goals", program=self.prog_b,
        )
        target_b = PlanTarget.objects.create(
            plan_section=section_b, client_file=self.other_client, name="Other Target",
        )
        note_b = ProgressNote.objects.create(
            client_file=self.other_client, note_type="full",
            author=self.admin, interaction_type="session",
        )
        ProgressNoteTarget.objects.create(progress_note=note_b, plan_target=target_b)

        # Staff user filters their own client's notes with target from other programme
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Own note", author=self.staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/?target={target_b.pk}"
        )
        self.assertEqual(resp.status_code, 200)
        # Should not expose notes from the other programme's client
        self.assertNotContains(resp, f'id="note-{note_b.pk}"')

    # -- Full Notes --

    def test_full_note_create_with_targets_and_metrics(self):
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Housing",
        )
        metric = MetricDefinition.objects.create(
            name="Stability Score", min_value=0, max_value=10, unit="score",
            definition="Housing stability", category="housing",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                "interaction_type": "session",
                "summary": "Good session",
                "consent_confirmed": True,
                f"target_{target.pk}-target_id": str(target.pk),
                f"target_{target.pk}-notes": "Discussed housing options",
                f"metric_{target.pk}_{metric.pk}-metric_def_id": str(metric.pk),
                f"metric_{target.pk}_{metric.pk}-value": "7",
            },
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(note_type="full")
        self.assertEqual(note.summary, "Good session")
        pnt = ProgressNoteTarget.objects.get(progress_note=note)
        self.assertEqual(pnt.notes, "Discussed housing options")
        mv = MetricValue.objects.get(progress_note_target=pnt)
        self.assertEqual(mv.value, "7")

    def test_full_note_saves_without_consent(self):
        """Consent checkbox is recommended, not required."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                "interaction_type": "session",
                "summary": "Session notes",
                # consent_confirmed omitted
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ProgressNote.objects.filter(note_type="full").exists())

    def test_full_note_with_scale_metric_saves(self):
        """Scale metrics (RadioSelect) save correctly via form POST."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Wellbeing", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Confidence",
        )
        metric = MetricDefinition.objects.create(
            name="Confidence Level", min_value=1, max_value=5, unit="",
            definition="Self-rated confidence", category="general",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                "interaction_type": "session",
                "consent_confirmed": True,
                f"target_{target.pk}-target_id": str(target.pk),
                f"target_{target.pk}-notes": "Feeling better",
                f"metric_{target.pk}_{metric.pk}-metric_def_id": str(metric.pk),
                f"metric_{target.pk}_{metric.pk}-value": "4",
            },
        )
        self.assertEqual(resp.status_code, 302)
        mv = MetricValue.objects.get(metric_def=metric)
        self.assertEqual(mv.value, "4")

    def test_scale_metric_renders_as_radio(self):
        """Metrics with small integer ranges (1-5) should use RadioSelect widget."""
        from apps.notes.forms import MetricValueForm
        metric = MetricDefinition.objects.create(
            name="Confidence", min_value=1, max_value=5, unit="",
            definition="Rate your confidence", category="general",
        )
        form = MetricValueForm(metric_def=metric)
        self.assertEqual(form.fields["value"].widget.__class__.__name__, "RadioSelect")
        choices = form.fields["value"].widget.choices
        self.assertEqual(len(choices), 6)  # empty + 1,2,3,4,5

    def test_wide_range_metric_stays_number_input(self):
        """Metrics with wide ranges (0-100) should stay as NumberInput."""
        from apps.notes.forms import MetricValueForm
        metric = MetricDefinition.objects.create(
            name="Score", min_value=0, max_value=100, unit="score",
            definition="Overall score", category="general",
        )
        form = MetricValueForm(metric_def=metric)
        self.assertEqual(form.fields["value"].widget.__class__.__name__, "NumberInput")

    def test_achievement_metric_renders_as_radio(self):
        """Achievement metrics render as RadioSelect with option labels."""
        from apps.notes.forms import MetricValueForm
        metric = MetricDefinition.objects.create(
            name="Job Placement", metric_type="achievement",
            achievement_options=["Not placed", "Interview stage", "Placed — full-time"],
            achievement_success_values=["Placed — full-time"],
            definition="Employment status", category="employment",
        )
        form = MetricValueForm(metric_def=metric)
        self.assertTrue(form.is_achievement)
        self.assertFalse(form.is_scale)
        self.assertEqual(form.fields["value"].widget.__class__.__name__, "RadioSelect")
        choices = form.fields["value"].widget.choices
        self.assertEqual(len(choices), 4)  # empty + 3 options

    def test_achievement_metric_validates_option(self):
        """Achievement metric rejects values not in achievement_options."""
        from apps.notes.forms import MetricValueForm
        metric = MetricDefinition.objects.create(
            name="Housing Secured", metric_type="achievement",
            achievement_options=["No housing", "Transitional", "Permanent housing"],
            achievement_success_values=["Permanent housing"],
            definition="Housing status", category="housing",
        )
        # Valid option
        form = MetricValueForm(
            data={"metric_def_id": metric.pk, "value": "Permanent housing"},
            metric_def=metric,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["value"], "Permanent housing")

        # Invalid option
        form = MetricValueForm(
            data={"metric_def_id": metric.pk, "value": "Invented option"},
            metric_def=metric,
        )
        self.assertFalse(form.is_valid())

    def test_auto_calc_session_count(self):
        """Auto-calc metric shows session count for current month."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Attendance", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Attendance",
        )
        metric = MetricDefinition.objects.create(
            name="Sessions this month", min_value=0, max_value=20,
            unit="sessions", definition="Sessions attended",
            category="general", computation_type="session_count",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

        # Create 3 notes this month
        for i in range(3):
            ProgressNote.objects.create(
                client_file=self.client_file, note_type="quick",
                notes_text=f"Note {i}", author=self.staff,
            )

        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/new/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "auto-calculated")

    def test_auto_calc_saves_on_post(self):
        """Auto-calc metric values are saved server-side on POST."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Attendance", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Attendance",
        )
        metric = MetricDefinition.objects.create(
            name="Sessions this month", min_value=0, max_value=20,
            unit="sessions", definition="Sessions attended",
            category="general", computation_type="session_count",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

        # Create 2 existing notes
        for i in range(2):
            ProgressNote.objects.create(
                client_file=self.client_file, note_type="quick",
                notes_text=f"Note {i}", author=self.staff,
            )

        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                "interaction_type": "session",
                "consent_confirmed": True,
                f"target_{target.pk}-target_id": str(target.pk),
                f"target_{target.pk}-progress_descriptor": "shifting",
                f"metric_{target.pk}_{metric.pk}-metric_def_id": str(metric.pk),
                # value intentionally omitted — auto-calc fills it server-side
            },
        )
        self.assertEqual(resp.status_code, 302)
        # The auto-calc should have saved the count (2 existing + 1 new = 3)
        mv = MetricValue.objects.get(metric_def=metric)
        self.assertEqual(mv.value, "3")

    def test_metric_computation_type_defaults_to_empty(self):
        """New metrics default to manual entry (empty computation_type)."""
        metric = MetricDefinition.objects.create(
            name="Test", definition="Test", category="general",
        )
        self.assertEqual(metric.computation_type, "")

    def test_metric_computation_type_session_count(self):
        """Metrics can have computation_type='session_count'."""
        metric = MetricDefinition.objects.create(
            name="Sessions", definition="Count", category="general",
            computation_type="session_count",
        )
        metric.refresh_from_db()
        self.assertEqual(metric.computation_type, "session_count")

    def test_metric_value_out_of_range_rejected(self):
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Housing",
        )
        metric = MetricDefinition.objects.create(
            name="Score", min_value=0, max_value=10, unit="score",
            definition="Test", category="general",
        )
        PlanTargetMetric.objects.create(plan_target=target, metric_def=metric)

        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                f"target_{target.pk}-target_id": str(target.pk),
                f"target_{target.pk}-notes": "",
                f"metric_{target.pk}_{metric.pk}-metric_def_id": str(metric.pk),
                f"metric_{target.pk}_{metric.pk}-value": "15",  # Over max
            },
        )
        self.assertEqual(resp.status_code, 200)  # Re-renders with errors
        self.assertEqual(ProgressNote.objects.count(), 0)

    # -- Cancellation --

    def test_staff_can_cancel_own_note(self):
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Cancel me", author=self.staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/{note.pk}/cancel/",
            {"status_reason": "Entered in error"},
        )
        self.assertEqual(resp.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.status, "cancelled")
        self.assertEqual(note.status_reason, "Entered in error")

    def test_staff_cannot_cancel_others_note(self):
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Not yours", author=self.other_staff,
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/{note.pk}/cancel/",
            {"status_reason": "Should fail"},
        )
        self.assertEqual(resp.status_code, 403)
        note.refresh_from_db()
        self.assertEqual(note.status, "default")

    def test_admin_without_program_role_blocked_from_cancel(self):
        """Admins without program roles cannot cancel notes (RBAC restriction)."""
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Admin cancel", author=self.staff,
        )
        self.http.login(username="admin", password="pass")
        resp = self.http.post(
            f"/notes/{note.pk}/cancel/",
            {"status_reason": "Admin override"},
        )
        self.assertEqual(resp.status_code, 403)
        note.refresh_from_db()
        self.assertEqual(note.status, "default")

    def test_admin_with_program_role_can_cancel_note(self):
        """Admins who also have a program role can cancel notes in their programs."""
        UserProgramRole.objects.create(user=self.admin, program=self.prog, role="program_manager")
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Admin cancel", author=self.staff,
        )
        self.http.login(username="admin", password="pass")
        resp = self.http.post(
            f"/notes/{note.pk}/cancel/",
            {"status_reason": "Admin override"},
        )
        self.assertEqual(resp.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.status, "cancelled")

    # -- Template Admin --

    def test_admin_can_access_template_list(self):
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/manage/note-templates/")
        self.assertEqual(resp.status_code, 200)

    def test_staff_cannot_access_template_admin(self):
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/manage/note-templates/")
        self.assertEqual(resp.status_code, 403)

    # -- Consent Workflow (PRIV1) --

    def test_note_blocked_without_client_consent(self):
        """Notes cannot be created when client has no consent recorded."""
        # Create client without consent
        client_no_consent = ClientFile()
        client_no_consent.first_name = "No"
        client_no_consent.last_name = "Consent"
        client_no_consent.status = "active"
        client_no_consent.save()
        ClientProgramEnrolment.objects.create(client_file=client_no_consent, program=self.prog)

        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{client_no_consent.pk}/quick/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Consent Required")
        self.assertContains(resp, "Cannot create notes")

    def test_note_allowed_with_client_consent(self):
        """Notes can be created when client has consent recorded."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/quick/",
            {"notes_text": "Consent is on file.", "interaction_type": "session", "consent_confirmed": True},
        )
        self.assertEqual(resp.status_code, 302)  # Redirect = success
        self.assertEqual(ProgressNote.objects.count(), 1)

    def test_consent_feature_toggle_disables_blocking(self):
        """Disabling the feature toggle allows notes without client consent."""
        # Create client without consent
        client_no_consent = ClientFile()
        client_no_consent.first_name = "Toggle"
        client_no_consent.last_name = "Test"
        client_no_consent.status = "active"
        client_no_consent.save()
        ClientProgramEnrolment.objects.create(client_file=client_no_consent, program=self.prog)

        # Disable consent requirement
        FeatureToggle.objects.create(feature_key="require_client_consent", is_enabled=False)

        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{client_no_consent.pk}/quick/",
            {"notes_text": "No consent needed.", "interaction_type": "session", "consent_confirmed": True},
        )
        self.assertEqual(resp.status_code, 302)  # Redirect = success
        self.assertEqual(ProgressNote.objects.count(), 1)

    def test_full_note_blocked_without_consent(self):
        """Full notes are also blocked without client consent."""
        client_no_consent = ClientFile()
        client_no_consent.first_name = "Full"
        client_no_consent.last_name = "Note"
        client_no_consent.status = "active"
        client_no_consent.save()
        ClientProgramEnrolment.objects.create(client_file=client_no_consent, program=self.prog)

        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{client_no_consent.pk}/new/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Consent Required")

    # -- Alliance Check-In --

    def test_full_note_with_alliance_rating(self):
        """Alliance rating and rater saved on a full note."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                "interaction_type": "session",
                "alliance_rating": "4",
                "alliance_rater": "client",
            },
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(note_type="full")
        self.assertEqual(note.alliance_rating, 4)
        self.assertEqual(note.alliance_rater, "client")

    def test_full_note_alliance_skipped(self):
        """Alliance rating can be skipped (null)."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                "interaction_type": "session",
                "alliance_rating": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(note_type="full")
        self.assertIsNone(note.alliance_rating)

    def test_full_note_alliance_worker_observed(self):
        """Worker-observed alliance rating saves correctly."""
        self.http.login(username="staff", password="pass")
        resp = self.http.post(
            f"/notes/participant/{self.client_file.pk}/new/",
            {
                "interaction_type": "session",
                "alliance_rating": "2",
                "alliance_rater": "worker_observed",
            },
        )
        self.assertEqual(resp.status_code, 302)
        note = ProgressNote.objects.get(note_type="full")
        self.assertEqual(note.alliance_rating, 2)
        self.assertEqual(note.alliance_rater, "worker_observed")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class QualitativeSummaryTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)
        self.receptionist = User.objects.create_user(username="recep", password="pass", is_admin=False)

        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.receptionist, program=self.prog, role="receptionist")

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.consent_given_at = timezone.now()
        self.client_file.consent_type = "written"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.prog)

    def tearDown(self):
        enc_module._fernet = None

    def test_qualitative_summary_permission_denied_no_program(self):
        """Staff user without any program role cannot access qualitative summary."""
        no_role_user = User.objects.create_user(username="norole", password="pass", is_admin=False)
        self.http.login(username="norole", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/qualitative/")
        self.assertEqual(resp.status_code, 403)

    def test_qualitative_summary_happy_path_empty(self):
        """Staff with program role gets 200 even when no plan targets exist."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/qualitative/")
        self.assertEqual(resp.status_code, 200)

    def test_qualitative_summary_shows_descriptor_distribution(self):
        """Descriptor distribution counts appear when progress notes have descriptors."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Housing",
        )
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="full",
            author=self.staff, interaction_type="session",
        )
        ProgressNoteTarget.objects.create(
            progress_note=note, plan_target=target,
            progress_descriptor="shifting",
        )

        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/qualitative/")
        self.assertEqual(resp.status_code, 200)
        # The view renders descriptor labels — "Something's shifting" is the label
        # for the "shifting" value. Check that the page contains descriptor content.
        self.assertContains(resp, "shifting")

    def test_qualitative_summary_shows_client_words(self):
        """Recent client words appear on the qualitative summary page."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Goals", program=self.prog,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file, name="Employment",
        )
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="full",
            author=self.staff, interaction_type="session",
        )
        pnt = ProgressNoteTarget(progress_note=note, plan_target=target)
        pnt.client_words = "I feel more confident about interviews now."
        pnt.save()

        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/qualitative/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "I feel more confident about interviews now.")

    def test_qualitative_summary_receptionist_blocked(self):
        """Receptionist role is blocked by minimum_role('staff') decorator."""
        self.http.login(username="recep", password="pass")
        resp = self.http.get(f"/notes/participant/{self.client_file.pk}/qualitative/")
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CheckNoteDateTest(TestCase):
    """Tests for the duplicate note date warning endpoint (UX-DUPENOTE1)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)
        self.receptionist = User.objects.create_user(username="recep", password="pass", is_admin=False)
        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.receptionist, program=self.prog, role="receptionist")

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.consent_given_at = timezone.now()
        self.client_file.consent_type = "written"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(client_file=self.client_file, program=self.prog)

    def tearDown(self):
        enc_module._fernet = None

    def test_warns_when_note_exists_on_date(self):
        """check_note_date returns existing note info for a date with notes."""
        today = timezone.localdate()
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Existing note", author=self.staff,
            interaction_type="session",
        )
        self.http.login(username="staff", password="pass")
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/check-date/",
            {"session_date": today.isoformat()},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Heads up")
        self.assertContains(resp, "One-on-One Session")

    def test_empty_when_no_notes_on_date(self):
        """check_note_date returns empty when no notes exist for the date."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/check-date/",
            {"session_date": "2020-01-01"},
        )
        self.assertEqual(resp.status_code, 200)
        # Should not contain any note author info
        self.assertNotContains(resp, "staff")

    def test_empty_when_no_date_provided(self):
        """check_note_date returns empty partial when no date is given."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/check-date/",
        )
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_user_redirected(self):
        """Unauthenticated users are redirected to login."""
        resp = self.http.get(
            f"/notes/participant/{self.client_file.pk}/check-date/",
            {"session_date": "2026-01-01"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TemplatePreviewTest(TestCase):
    """Tests for the template preview endpoint (UX-PREVIEW1)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.staff = User.objects.create_user(username="staff", password="pass", is_admin=False)
        self.receptionist = User.objects.create_user(username="recep", password="pass", is_admin=False)
        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.receptionist, program=self.prog, role="receptionist")

        from apps.notes.models import ProgressNoteTemplate, ProgressNoteTemplateSection
        self.template = ProgressNoteTemplate.objects.create(
            name="Session Template", status="active",
            default_interaction_type="session",
        )
        ProgressNoteTemplateSection.objects.create(
            template=self.template, name="Goals Review",
            section_type="plan", sort_order=1,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_staff_can_preview(self):
        """Staff can see template preview."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/template/{self.template.pk}/preview/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Goals Review")

    def test_receptionist_blocked(self):
        """Receptionists cannot preview templates."""
        self.http.login(username="recep", password="pass")
        resp = self.http.get(f"/notes/template/{self.template.pk}/preview/")
        self.assertEqual(resp.status_code, 403)

    def test_inactive_template_404(self):
        """Inactive templates return 404."""
        self.template.status = "archived"
        self.template.save()
        self.http.login(username="staff", password="pass")
        resp = self.http.get(f"/notes/template/{self.template.pk}/preview/")
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_user_redirected(self):
        """Unauthenticated users are redirected to login."""
        resp = self.http.get(f"/notes/template/{self.template.pk}/preview/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)
