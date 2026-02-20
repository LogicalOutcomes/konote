"""Tests for the surveys app.

Run with:
    pytest tests/test_surveys.py -v
"""
from datetime import timedelta

from cryptography.fernet import Fernet
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Event, EventType
from apps.portal.models import ParticipantUser
from apps.programs.models import Program
from apps.surveys.models import (
    Survey, SurveySection, SurveyQuestion, SurveyTriggerRule,
    SurveyAssignment, SurveyResponse, SurveyAnswer, PartialAnswer,
    SurveyLink,
)
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SurveyModelTests(TestCase):
    """Test Survey, SurveySection, and SurveyQuestion creation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="survey_staff",
            password="testpass123",
            display_name="Survey Staff",
        )

    def test_create_survey_with_sections_and_questions(self):
        survey = Survey.objects.create(
            name="Test Survey",
            name_fr="Sondage test",
            created_by=self.staff,
        )
        section = SurveySection.objects.create(
            survey=survey,
            title="About You",
            title_fr="À propos de vous",
            sort_order=1,
        )
        q1 = SurveyQuestion.objects.create(
            section=section,
            question_text="How are you?",
            question_text_fr="Comment allez-vous?",
            question_type="single_choice",
            sort_order=1,
            required=True,
            options_json=[
                {"value": "good", "label": "Good", "label_fr": "Bien", "score": 2},
                {"value": "ok", "label": "OK", "label_fr": "Correct", "score": 1},
                {"value": "bad", "label": "Bad", "label_fr": "Mal", "score": 0},
            ],
        )
        self.assertEqual(survey.sections.count(), 1)
        self.assertEqual(section.questions.count(), 1)
        self.assertEqual(q1.question_type, "single_choice")
        self.assertEqual(str(survey), "Test Survey")

    def test_survey_defaults(self):
        survey = Survey.objects.create(
            name="Defaults Test",
            created_by=self.staff,
        )
        self.assertEqual(survey.status, "draft")
        self.assertFalse(survey.is_anonymous)
        self.assertFalse(survey.show_scores_to_participant)
        self.assertTrue(survey.portal_visible)

    def test_section_with_scoring(self):
        survey = Survey.objects.create(name="Scored", created_by=self.staff)
        section = SurveySection.objects.create(
            survey=survey,
            title="Health",
            sort_order=1,
            scoring_method="sum",
            max_score=20,
        )
        self.assertEqual(section.scoring_method, "sum")
        self.assertEqual(section.max_score, 20)

    def test_section_with_page_break(self):
        survey = Survey.objects.create(name="Paged", created_by=self.staff)
        s1 = SurveySection.objects.create(
            survey=survey, title="Page 1", sort_order=1, page_break=False,
        )
        s2 = SurveySection.objects.create(
            survey=survey, title="Page 2", sort_order=2, page_break=True,
        )
        self.assertFalse(s1.page_break)
        self.assertTrue(s2.page_break)

    def test_conditional_section(self):
        survey = Survey.objects.create(name="Conditional", created_by=self.staff)
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1,
            question_text="Do you have children?",
            question_type="yes_no",
            sort_order=1,
            required=True,
        )
        s2 = SurveySection.objects.create(
            survey=survey,
            title="Childcare",
            sort_order=2,
            condition_question=trigger_q,
            condition_value="yes",
        )
        self.assertEqual(s2.condition_question, trigger_q)
        self.assertEqual(s2.condition_value, "yes")

    def test_question_types(self):
        survey = Survey.objects.create(name="Types", created_by=self.staff)
        section = SurveySection.objects.create(
            survey=survey, title="All Types", sort_order=1,
        )
        for qt in ["single_choice", "multiple_choice", "rating_scale",
                    "short_text", "long_text", "yes_no"]:
            q = SurveyQuestion.objects.create(
                section=section,
                question_text=f"Test {qt}",
                question_type=qt,
                sort_order=1,
            )
            self.assertEqual(q.question_type, qt)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TriggerRuleModelTests(TestCase):
    """Test SurveyTriggerRule creation and constraints."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="trigger_staff", password="testpass123",
            display_name="Trigger Staff",
        )
        self.survey = Survey.objects.create(name="Trigger Test", created_by=self.staff)
        self.program = Program.objects.create(name="Youth Program")

    def test_create_enrolment_trigger(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="enrolment",
            program=self.program,
            repeat_policy="once_per_enrolment",
            auto_assign=True,
            created_by=self.staff,
        )
        self.assertEqual(rule.trigger_type, "enrolment")
        self.assertTrue(rule.auto_assign)
        self.assertTrue(rule.is_active)

    def test_create_time_trigger(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="time",
            program=self.program,
            recurrence_days=30,
            anchor="enrolment_date",
            repeat_policy="recurring",
            auto_assign=True,
            created_by=self.staff,
        )
        self.assertEqual(rule.recurrence_days, 30)
        self.assertEqual(rule.anchor, "enrolment_date")

    def test_create_event_trigger(self):
        et = EventType.objects.create(name="Crisis")
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=et,
            repeat_policy="once_per_participant",
            auto_assign=False,
            created_by=self.staff,
        )
        self.assertEqual(rule.event_type, et)
        self.assertFalse(rule.auto_assign)

    def test_create_characteristic_trigger(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            include_existing=True,
            created_by=self.staff,
        )
        self.assertTrue(rule.include_existing)

    def test_trigger_with_due_days(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="enrolment",
            program=self.program,
            repeat_policy="once_per_enrolment",
            auto_assign=True,
            due_days=7,
            created_by=self.staff,
        )
        self.assertEqual(rule.due_days, 7)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-surveys",
)
class AssignmentResponseModelTests(TestCase):
    """Test SurveyAssignment, SurveyResponse, SurveyAnswer, PartialAnswer."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="assign_staff", password="testpass123",
            display_name="Assign Staff",
        )
        self.survey = Survey.objects.create(name="Assignment Test", created_by=self.staff)
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Section 1", sort_order=1,
        )
        self.question = SurveyQuestion.objects.create(
            section=self.section, question_text="Rate this",
            question_type="rating_scale", sort_order=1, min_value=1, max_value=5,
        )
        self.client_file = ClientFile.objects.create(
            record_id="SURV-001", status="active",
        )
        self.client_file.first_name = "Survey"
        self.client_file.last_name = "Participant"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="survey@example.com",
            client_file=self.client_file,
            display_name="Survey P",
            password="testpass123",
        )

    def test_create_assignment(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="pending",
        )
        self.assertEqual(assignment.status, "pending")
        self.assertIsNone(assignment.triggered_by_rule)

    def test_assignment_status_flow(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="awaiting_approval",
        )
        assignment.status = "pending"
        assignment.save()
        assignment.status = "in_progress"
        assignment.save()
        assignment.status = "completed"
        assignment.save()
        self.assertEqual(assignment.status, "completed")

    def test_create_response_and_answer(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="completed",
        )
        response = SurveyResponse.objects.create(
            survey=self.survey,
            assignment=assignment,
            client_file=self.client_file,
            channel="portal",
        )
        answer = SurveyAnswer.objects.create(
            response=response,
            question=self.question,
            value="4",
            numeric_value=4,
        )
        self.assertEqual(response.answers.count(), 1)
        self.assertEqual(answer.numeric_value, 4)

    def test_partial_answer_upsert(self):
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )
        pa, created = PartialAnswer.objects.update_or_create(
            assignment=assignment,
            question=self.question,
            defaults={"value_encrypted": b"test-encrypted-value"},
        )
        self.assertTrue(created)
        pa2, created2 = PartialAnswer.objects.update_or_create(
            assignment=assignment,
            question=self.question,
            defaults={"value_encrypted": b"updated-value"},
        )
        self.assertFalse(created2)
        self.assertEqual(pa.pk, pa2.pk)

    def test_anonymous_response(self):
        """Anonymous survey responses have no client_file or assignment."""
        anon_survey = Survey.objects.create(
            name="Anon Survey", created_by=self.staff, is_anonymous=True,
        )
        response = SurveyResponse.objects.create(
            survey=anon_survey,
            channel="link",
            respondent_name_display="Anonymous Person",
        )
        self.assertIsNone(response.client_file)
        self.assertIsNone(response.assignment)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-engine",
)
class EvaluationEngineTests(TestCase):
    """Test the survey trigger evaluation engine."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="engine_staff", password="testpass123",
            display_name="Engine Staff",
        )
        self.program = Program.objects.create(name="Engine Program")
        self.survey = Survey.objects.create(
            name="Engine Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.client_file = ClientFile.objects.create(
            record_id="ENG-001", status="active",
        )
        self.client_file.first_name = "Engine"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="engine@example.com",
            client_file=self.client_file,
            display_name="Engine P",
            password="testpass123",
        )
        self.enrolment = ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
        )

    def test_characteristic_rule_creates_assignment(self):
        from apps.surveys.engine import evaluate_survey_rules

        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 1)
        self.assertEqual(new_assignments[0].status, "pending")

    def test_characteristic_rule_no_duplicate(self):
        from apps.surveys.engine import evaluate_survey_rules

        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        evaluate_survey_rules(self.client_file, self.participant)
        # Run again — should not create duplicate
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)
        self.assertEqual(SurveyAssignment.objects.count(), 1)

    def test_time_rule_not_due_yet(self):
        from apps.surveys.engine import evaluate_survey_rules

        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="time",
            program=self.program,
            recurrence_days=30,
            anchor="enrolment_date",
            repeat_policy="recurring",
            auto_assign=True,
            created_by=self.staff,
        )
        # Enrolment was just now — 30 days haven't passed
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)

    def test_time_rule_due(self):
        from apps.surveys.engine import evaluate_survey_rules

        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="time",
            program=self.program,
            recurrence_days=30,
            anchor="enrolment_date",
            repeat_policy="recurring",
            auto_assign=True,
            created_by=self.staff,
        )
        # Backdate enrolment to 31 days ago
        ClientProgramEnrolment.objects.filter(pk=self.enrolment.pk).update(
            enrolled_at=timezone.now() - timedelta(days=31),
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 1)

    def test_staff_confirms_creates_awaiting_approval(self):
        from apps.surveys.engine import evaluate_survey_rules

        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=False,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(new_assignments[0].status, "awaiting_approval")

    def test_skips_discharged_client(self):
        from apps.surveys.engine import evaluate_survey_rules

        self.client_file.status = "discharged"
        self.client_file.save()
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)

    def test_skips_inactive_survey(self):
        from apps.surveys.engine import evaluate_survey_rules

        self.survey.status = "draft"
        self.survey.save()
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)

    def test_overload_protection(self):
        """Don't assign if participant has 5+ pending surveys."""
        from apps.surveys.engine import evaluate_survey_rules

        for i in range(5):
            s = Survey.objects.create(
                name=f"Overload {i}", status="active", created_by=self.staff,
            )
            SurveySection.objects.create(survey=s, title="S", sort_order=1)
            SurveyAssignment.objects.create(
                survey=s,
                participant_user=self.participant,
                client_file=self.client_file,
                status="pending",
            )
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        new_assignments = evaluate_survey_rules(self.client_file, self.participant)
        self.assertEqual(len(new_assignments), 0)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-signals",
)
class SignalTriggerTests(TransactionTestCase):
    """Test that event/enrolment creation triggers survey assignment.

    Uses TransactionTestCase so transaction.on_commit() fires.
    """

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        # Enable the surveys feature toggle
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        self.staff = User.objects.create_user(
            username="signal_staff", password="testpass123",
            display_name="Signal Staff",
        )
        self.program = Program.objects.create(name="Signal Program")
        self.event_type = EventType.objects.create(name="Intake")
        self.survey = Survey.objects.create(
            name="Signal Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.client_file = ClientFile.objects.create(
            record_id="SIG-001", status="active",
        )
        self.client_file.first_name = "Signal"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="signal@example.com",
            client_file=self.client_file,
            display_name="Signal P",
            password="testpass123",
        )

    def test_event_signal_creates_assignment(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=self.event_type,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        # Creating an event with matching type should trigger assignment
        Event.objects.create(
            client_file=self.client_file,
            event_type=self.event_type,
            start_timestamp=timezone.now(),
        )
        self.assertEqual(
            SurveyAssignment.objects.filter(
                survey=self.survey,
                participant_user=self.participant,
            ).count(),
            1,
        )

    def test_enrolment_signal_creates_assignment(self):
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="enrolment",
            program=self.program,
            repeat_policy="once_per_enrolment",
            auto_assign=True,
            created_by=self.staff,
        )
        # Creating an enrolment should trigger assignment
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        self.assertEqual(
            SurveyAssignment.objects.filter(
                survey=self.survey,
                participant_user=self.participant,
            ).count(),
            1,
        )

    def test_signal_skips_when_feature_disabled(self):
        """Signals should not create assignments when surveys feature is off."""
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": False},
        )
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=self.event_type,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        Event.objects.create(
            client_file=self.client_file,
            event_type=self.event_type,
            start_timestamp=timezone.now(),
        )
        self.assertEqual(
            SurveyAssignment.objects.filter(
                survey=self.survey,
                participant_user=self.participant,
            ).count(),
            0,
        )


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-engine-direct",
)
class EventEnrolmentEngineTests(TestCase):
    """Direct unit tests for evaluate_event_rules and evaluate_enrolment_rules."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="direct_staff", password="testpass123",
            display_name="Direct Staff",
        )
        self.program = Program.objects.create(name="Direct Program")
        self.event_type = EventType.objects.create(name="Session")
        self.survey = Survey.objects.create(
            name="Direct Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.client_file = ClientFile.objects.create(
            record_id="DIR-001", status="active",
        )
        self.client_file.first_name = "Direct"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="direct@example.com",
            client_file=self.client_file,
            display_name="Direct P",
            password="testpass123",
        )

    def test_evaluate_event_rules_creates_assignment(self):
        from apps.surveys.engine import evaluate_event_rules

        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=self.event_type,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        event = Event.objects.create(
            client_file=self.client_file,
            event_type=self.event_type,
            start_timestamp=timezone.now(),
        )
        assignments = evaluate_event_rules(
            self.client_file, self.participant, event,
        )
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].survey, self.survey)

    def test_evaluate_event_rules_no_match(self):
        from apps.surveys.engine import evaluate_event_rules

        other_type = EventType.objects.create(name="Other")
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=other_type,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        event = Event.objects.create(
            client_file=self.client_file,
            event_type=self.event_type,
            start_timestamp=timezone.now(),
        )
        assignments = evaluate_event_rules(
            self.client_file, self.participant, event,
        )
        self.assertEqual(len(assignments), 0)

    def test_evaluate_enrolment_rules_creates_assignment(self):
        from apps.surveys.engine import evaluate_enrolment_rules

        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="enrolment",
            program=self.program,
            repeat_policy="once_per_enrolment",
            auto_assign=True,
            created_by=self.staff,
        )
        enrolment = ClientProgramEnrolment.objects.create(
            client_file=self.client_file,
            program=self.program,
        )
        assignments = evaluate_enrolment_rules(
            self.client_file, self.participant, enrolment,
        )
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].survey, self.survey)

    def test_evaluate_event_rules_overload_protection(self):
        """Event rules should respect overload limit."""
        from apps.surveys.engine import evaluate_event_rules

        for i in range(5):
            s = Survey.objects.create(
                name=f"Overload {i}", status="active", created_by=self.staff,
            )
            SurveyAssignment.objects.create(
                survey=s,
                participant_user=self.participant,
                client_file=self.client_file,
                status="pending",
            )
        SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="event",
            event_type=self.event_type,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        event = Event.objects.create(
            client_file=self.client_file,
            event_type=self.event_type,
            start_timestamp=timezone.now(),
        )
        assignments = evaluate_event_rules(
            self.client_file, self.participant, event,
        )
        self.assertEqual(len(assignments), 0)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-autosave",
)
class PortalAutoSaveTests(TestCase):
    """Test auto-save of partial answers in the portal."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )
        self.staff = User.objects.create_user(
            username="autosave_staff", password="testpass123",
            display_name="Autosave Staff",
        )
        self.survey = Survey.objects.create(
            name="Autosave Survey", status="active", created_by=self.staff,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Section 1", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="Your name?",
            question_type="short_text", sort_order=1,
        )
        self.q2 = SurveyQuestion.objects.create(
            section=self.section, question_text="Rate us",
            question_type="rating_scale", sort_order=2,
            min_value=1, max_value=5,
        )
        self.client_file = ClientFile.objects.create(
            record_id="AUTO-001", status="active",
        )
        self.client_file.first_name = "Auto"
        self.client_file.last_name = "Save"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="autosave@example.com",
            client_file=self.client_file,
            display_name="Auto S",
            password="testpass123",
        )
        self.assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )

    def _portal_session(self):
        """Set up a portal session for the participant."""
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.pk)
        session.save()

    def test_autosave_creates_partial_answer(self):
        self._portal_session()
        resp = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Alice"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PartialAnswer.objects.count(), 1)
        pa = PartialAnswer.objects.first()
        self.assertEqual(pa.question, self.q1)

    def test_autosave_updates_existing_partial(self):
        self._portal_session()
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Alice"},
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Bob"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(PartialAnswer.objects.count(), 1)

    def test_autosave_requires_htmx(self):
        self._portal_session()
        resp = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Alice"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_form_loads_partial_answers(self):
        """When opening a form with partial answers, values are pre-filled."""
        from konote.encryption import encrypt_field
        PartialAnswer.objects.create(
            assignment=self.assignment,
            question=self.q1,
            value_encrypted=encrypt_field("Alice"),
        )
        self._portal_session()
        resp = self.client.get(
            f"/my/surveys/{self.assignment.pk}/fill/",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Alice", resp.content.decode())

    def test_submit_cleans_up_partial_answers(self):
        """After submit, partial answers are deleted."""
        PartialAnswer.objects.create(
            assignment=self.assignment,
            question=self.q1,
            value_encrypted=b"dummy",
        )
        self._portal_session()
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/fill/",
            {f"q_{self.q1.pk}": "Final Answer", f"q_{self.q2.pk}": "3"},
        )
        self.assertEqual(PartialAnswer.objects.count(), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SurveyLinkModelTests(TestCase):
    """Test SurveyLink model for shareable URLs."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="link_staff", password="testpass123",
            display_name="Link Staff",
        )
        self.survey = Survey.objects.create(
            name="Link Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_create_link(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey,
            created_by=self.staff,
        )
        self.assertTrue(len(link.token) >= 32)
        self.assertTrue(link.is_active)

    def test_link_token_unique(self):
        from apps.surveys.models import SurveyLink
        link1 = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )
        link2 = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )
        self.assertNotEqual(link1.token, link2.token)

    def test_link_with_expiry(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey,
            created_by=self.staff,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertFalse(link.is_expired)

    def test_expired_link(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey,
            created_by=self.staff,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(link.is_expired)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PublicSurveyViewTests(TestCase):
    """Test public survey form accessible via shareable link."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="pub_staff", password="testpass123",
            display_name="Public Staff",
        )
        self.survey = Survey.objects.create(
            name="Public Survey", status="active", created_by=self.staff,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Feedback", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="How was your experience?",
            question_type="short_text", sort_order=1, required=True,
        )
        self.link = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )

    def test_public_form_renders(self):
        resp = self.client.get(f"/s/{self.link.token}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Public Survey")

    def test_public_form_submit_creates_response(self):
        resp = self.client.post(
            f"/s/{self.link.token}/",
            {f"q_{self.q1.pk}": "Great!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(SurveyResponse.objects.filter(channel="link").count(), 1)

    def test_expired_link_returns_gone(self):
        expired = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = self.client.get(f"/s/{expired.token}/")
        self.assertEqual(resp.status_code, 410)

    def test_inactive_link_returns_gone(self):
        self.link.is_active = False
        self.link.save()
        resp = self.client.get(f"/s/{self.link.token}/")
        self.assertEqual(resp.status_code, 410)

    def test_invalid_token_returns_404(self):
        resp = self.client.get("/s/nonexistent-token/")
        self.assertEqual(resp.status_code, 404)

    def test_closed_survey_returns_gone(self):
        self.survey.status = "closed"
        self.survey.save()
        resp = self.client.get(f"/s/{self.link.token}/")
        self.assertEqual(resp.status_code, 410)
