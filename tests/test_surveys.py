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
from apps.programs.models import Program, UserProgramRole
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
class SurveySectionFormTests(TestCase):
    """Test SurveySectionForm includes condition fields."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="form_staff", password="testpass123",
            display_name="Form Staff",
        )
        self.survey = Survey.objects.create(name="Form Test", created_by=self.staff)
        self.s1 = SurveySection.objects.create(
            survey=self.survey, title="Section 1", sort_order=1,
        )
        self.trigger_q = SurveyQuestion.objects.create(
            section=self.s1, question_text="Has children?",
            question_type="yes_no", sort_order=1,
        )

    def test_form_includes_condition_fields(self):
        from apps.surveys.forms import SurveySectionForm
        form = SurveySectionForm()
        self.assertIn("condition_question", form.fields)
        self.assertIn("condition_value", form.fields)

    def test_form_saves_condition(self):
        from apps.surveys.forms import SurveySectionForm
        form = SurveySectionForm(data={
            "title": "Childcare",
            "sort_order": "2",
            "page_break": "",
            "scoring_method": "none",
            "condition_question": str(self.trigger_q.pk),
            "condition_value": "1",
        })
        self.assertTrue(form.is_valid(), form.errors)
        section = form.save(commit=False)
        section.survey = self.survey
        section.save()
        self.assertEqual(section.condition_question_id, self.trigger_q.pk)
        self.assertEqual(section.condition_value, "1")

    def test_form_valid_without_condition(self):
        from apps.surveys.forms import SurveySectionForm
        form = SurveySectionForm(data={
            "title": "No Condition",
            "sort_order": "1",
            "page_break": "",
            "scoring_method": "none",
            "condition_question": "",
            "condition_value": "",
        })
        self.assertTrue(form.is_valid(), form.errors)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConditionValuesEndpointTests(TestCase):
    """Test the HTMX endpoint that returns condition value options."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="cv_staff", password="testpass123",
            display_name="CV Staff", is_admin=True,
        )
        self.client.login(username="cv_staff", password="testpass123")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys", defaults={"is_enabled": True},
        )
        self.survey = Survey.objects.create(name="CV Test", created_by=self.staff)
        self.section = SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_yes_no_returns_two_options(self):
        q = SurveyQuestion.objects.create(
            section=self.section, question_text="Yes or no?",
            question_type="yes_no", sort_order=1,
        )
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('value="1"', content)
        self.assertIn('value="0"', content)

    def test_single_choice_returns_option_values(self):
        q = SurveyQuestion.objects.create(
            section=self.section, question_text="Pick one",
            question_type="single_choice", sort_order=1,
            options_json=[
                {"value": "a", "label": "Alpha"},
                {"value": "b", "label": "Beta"},
            ],
        )
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('value="a"', content)
        self.assertIn("Alpha", content)
        self.assertIn('value="b"', content)

    def test_text_question_returns_text_input(self):
        q = SurveyQuestion.objects.create(
            section=self.section, question_text="Name?",
            question_type="short_text", sort_order=1,
        )
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('type="text"', content)

    def test_rating_scale_returns_option_values(self):
        q = SurveyQuestion.objects.create(
            section=self.section, question_text="Rate 1-3",
            question_type="rating_scale", sort_order=1,
            options_json=[
                {"value": "1", "label": "Low"},
                {"value": "2", "label": "Medium"},
                {"value": "3", "label": "High"},
            ],
        )
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('value="1"', content)
        self.assertIn("Low", content)
        self.assertIn('value="3"', content)

    def test_cross_survey_question_returns_404(self):
        """Question from a different survey should return 404."""
        other_survey = Survey.objects.create(name="Other", created_by=self.staff)
        other_section = SurveySection.objects.create(
            survey=other_survey, title="Other S1", sort_order=1,
        )
        other_q = SurveyQuestion.objects.create(
            section=other_section, question_text="Other Q",
            question_type="yes_no", sort_order=1,
        )
        # Request other_q via self.survey's URL — should 404
        url = f"/manage/surveys/{self.survey.pk}/condition-values/{other_q.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConditionalBadgeRenderTests(TestCase):
    """Test conditional badge appears in admin detail and questions views."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="badge_staff", password="testpass123",
            display_name="Badge Staff", is_admin=True,
        )
        self.client.login(username="badge_staff", password="testpass123")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys", defaults={"is_enabled": True},
        )
        self.survey = Survey.objects.create(
            name="Badge Test", created_by=self.staff,
        )
        self.s1 = SurveySection.objects.create(
            survey=self.survey, title="Main", sort_order=1,
        )
        self.trigger_q = SurveyQuestion.objects.create(
            section=self.s1, question_text="Has children?",
            question_type="yes_no", sort_order=1,
        )
        self.s2 = SurveySection.objects.create(
            survey=self.survey, title="Childcare", sort_order=2,
            condition_question=self.trigger_q, condition_value="1",
        )

    def test_detail_shows_conditional_badge(self):
        url = f"/manage/surveys/{self.survey.pk}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Conditional")
        self.assertContains(resp, "Has children?")

    def test_questions_shows_conditional_badge(self):
        url = f"/manage/surveys/{self.survey.pk}/questions/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Conditional")
        self.assertContains(resp, "Has children?")

    def test_detail_no_badge_for_unconditional(self):
        url = f"/manage/surveys/{self.survey.pk}/"
        resp = self.client.get(url)
        # "Main" section should NOT have a Conditional badge
        content = resp.content.decode()
        # The badge appears once (for Childcare only), not for Main
        self.assertEqual(content.count("Conditional"), 1)


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

    def test_partial_answer_value_property(self):
        """PartialAnswer.value encrypts on set, decrypts on get."""
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )
        pa = PartialAnswer(assignment=assignment, question=self.question)
        pa.value = "test answer"
        pa.save()
        # Load fresh instance to verify roundtrip through DB
        pa_fresh = PartialAnswer.objects.get(pk=pa.pk)
        self.assertEqual(pa_fresh.value, "test answer")
        # Encrypted field should not be plain text or empty
        self.assertNotEqual(pa_fresh.value_encrypted, b"test answer")
        self.assertNotEqual(pa_fresh.value_encrypted, b"")

    def test_partial_answer_value_empty(self):
        """PartialAnswer.value handles empty string."""
        assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )
        pa = PartialAnswer(assignment=assignment, question=self.question)
        pa.value = ""
        pa.save()
        pa_fresh = PartialAnswer.objects.get(pk=pa.pk)
        self.assertEqual(pa_fresh.value, "")

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
        # Second participant for IDOR tests
        self.client_file_b = ClientFile.objects.create(
            record_id="AUTO-002", status="active",
        )
        self.client_file_b.first_name = "Other"
        self.client_file_b.last_name = "Person"
        self.client_file_b.save()
        self.participant_b = ParticipantUser.objects.create_participant(
            email="other@example.com",
            client_file=self.client_file_b,
            display_name="Other P",
            password="testpass123",
        )
        self.assignment_b = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant_b,
            client_file=self.client_file_b,
            status="in_progress",
        )

    def _portal_session(self, participant=None):
        """Set up a portal session for the participant."""
        p = participant or self.participant
        session = self.client.session
        session["_portal_participant_id"] = str(p.pk)
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
        # Verify the decrypted value matches what was saved
        from konote.encryption import decrypt_field
        self.assertEqual(decrypt_field(pa.value_encrypted), "Alice")

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
        # Verify value was actually updated, not just count
        from konote.encryption import decrypt_field
        pa = PartialAnswer.objects.first()
        self.assertEqual(decrypt_field(pa.value_encrypted), "Bob")

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

    def test_autosave_idor_other_participants_assignment(self):
        """Participant A cannot auto-save to participant B's assignment."""
        self._portal_session(self.participant)
        resp = self.client.post(
            f"/my/surveys/{self.assignment_b.pk}/save/",
            {"question_id": self.q1.pk, "value": "Hacked"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(PartialAnswer.objects.count(), 0)

    def test_fill_idor_other_participants_assignment(self):
        """Participant A cannot access participant B's survey form."""
        self._portal_session(self.participant)
        resp = self.client.get(f"/my/surveys/{self.assignment_b.pk}/fill/")
        self.assertEqual(resp.status_code, 404)


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


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StaffLinkGenerationTests(TestCase):
    """Test staff UI for generating shareable survey links."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="linkgen_staff", password="testpass123",
            display_name="LinkGen Staff", is_admin=True,
        )
        self.client.login(username="linkgen_staff", password="testpass123")
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        self.survey = Survey.objects.create(
            name="LinkGen Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_generate_link_page_renders(self):
        resp = self.client.get(
            f"/manage/surveys/{self.survey.pk}/links/",
        )
        self.assertEqual(resp.status_code, 200)

    def test_create_link(self):
        from apps.surveys.models import SurveyLink
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/links/",
            {"action": "create"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(SurveyLink.objects.filter(survey=self.survey).count(), 1)

    def test_deactivate_link(self):
        from apps.surveys.models import SurveyLink
        link = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/links/",
            {"action": "deactivate", "link_id": link.pk},
        )
        link.refresh_from_db()
        self.assertFalse(link.is_active)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SurveyStaffPermissionTests(TestCase):
    """Test that staff survey views require login and correct permissions."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        self.admin = User.objects.create_user(
            username="perm_admin", password="testpass123",
            display_name="Perm Admin", is_admin=True,
        )
        self.survey = Survey.objects.create(
            name="Perm Survey", status="active", created_by=self.admin,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=Program.objects.create(name="Perm Program"),
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.admin,
        )

    def test_survey_links_requires_login(self):
        resp = self.client.get(f"/manage/surveys/{self.survey.pk}/links/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_survey_rules_list_requires_login(self):
        resp = self.client.get(f"/manage/surveys/{self.survey.pk}/rules/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_survey_rule_create_requires_login(self):
        resp = self.client.get(f"/manage/surveys/{self.survey.pk}/rules/new/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_survey_rule_deactivate_requires_login(self):
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/{self.rule.pk}/deactivate/",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_survey_rule_deactivate_rejects_get(self):
        """GET request to POST-only deactivate view returns 405."""
        self.client.login(username="perm_admin", password="testpass123")
        resp = self.client.get(
            f"/manage/surveys/{self.survey.pk}/rules/{self.rule.pk}/deactivate/",
        )
        self.assertEqual(resp.status_code, 405)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PublicSurveySubmissionTests(TestCase):
    """Test public survey form submission creates correct data."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="pubsub_staff", password="testpass123",
            display_name="PubSub Staff",
        )
        self.survey = Survey.objects.create(
            name="PubSub Survey", status="active", created_by=self.staff,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="Feedback", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="How was it?",
            question_type="short_text", sort_order=1, required=True,
        )
        self.link = SurveyLink.objects.create(
            survey=self.survey, created_by=self.staff,
        )

    def test_submit_creates_response_with_correct_values(self):
        """Verify the response and answer values are stored correctly."""
        resp = self.client.post(
            f"/s/{self.link.token}/",
            {f"q_{self.q1.pk}": "Excellent!"},
        )
        self.assertEqual(resp.status_code, 302)
        response = SurveyResponse.objects.get(channel="link")
        self.assertEqual(response.token, self.link.token)
        answer = response.answers.first()
        self.assertEqual(answer.value, "Excellent!")

    def test_honeypot_blocks_bots(self):
        """Submissions with honeypot field filled are silently discarded."""
        resp = self.client.post(
            f"/s/{self.link.token}/",
            {f"q_{self.q1.pk}": "spam", "website": "http://spam.com"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(SurveyResponse.objects.count(), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TriggerRuleManagementTests(TestCase):
    """Test staff UI for managing trigger rules."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="ruleui_staff", password="testpass123",
            display_name="RuleUI Staff", is_admin=True,
        )
        self.client.login(username="ruleui_staff", password="testpass123")
        from django.core.cache import cache
        cache.delete("feature_toggles")
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        self.program = Program.objects.create(name="RuleUI Program")
        self.event_type = EventType.objects.create(name="RuleUI Event")
        self.survey = Survey.objects.create(
            name="RuleUI Survey", status="active", created_by=self.staff,
        )
        SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )

    def test_rule_list_page_renders(self):
        resp = self.client.get(
            f"/manage/surveys/{self.survey.pk}/rules/",
        )
        self.assertEqual(resp.status_code, 200)

    def test_create_characteristic_rule(self):
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/new/",
            {
                "trigger_type": "characteristic",
                "program": self.program.pk,
                "repeat_policy": "once_per_participant",
                "auto_assign": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            SurveyTriggerRule.objects.filter(survey=self.survey).count(), 1,
        )

    def test_create_event_rule(self):
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/new/",
            {
                "trigger_type": "event",
                "event_type": self.event_type.pk,
                "repeat_policy": "once_per_participant",
                "auto_assign": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        rule = SurveyTriggerRule.objects.get(survey=self.survey)
        self.assertEqual(rule.event_type, self.event_type)

    def test_create_time_rule(self):
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/new/",
            {
                "trigger_type": "time",
                "program": self.program.pk,
                "recurrence_days": 30,
                "anchor": "enrolment_date",
                "repeat_policy": "recurring",
                "auto_assign": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        rule = SurveyTriggerRule.objects.get(survey=self.survey)
        self.assertEqual(rule.recurrence_days, 30)

    def test_deactivate_rule(self):
        rule = SurveyTriggerRule.objects.create(
            survey=self.survey,
            trigger_type="characteristic",
            program=self.program,
            repeat_policy="once_per_participant",
            auto_assign=True,
            created_by=self.staff,
        )
        resp = self.client.post(
            f"/manage/surveys/{self.survey.pk}/rules/{rule.pk}/deactivate/",
        )
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-staff",
)
class StaffDataEntryConditionTests(TestCase):
    """Test staff data entry respects conditional sections."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="sde_staff", password="testpass123",
            display_name="SDE Staff", is_admin=True,
        )
        self.client_obj = ClientFile.objects.create(
            record_id="SDE-001", status="active",
        )
        self.client_obj.first_name = "Test"
        self.client_obj.last_name = "Client"
        self.client_obj.save()
        # Ensure staff can access this client via program role
        self.program = Program.objects.create(name="SDE Program")
        ClientProgramEnrolment.objects.create(
            client_file=self.client_obj, program=self.program, status="enrolled",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active",
        )

        self.survey = Survey.objects.create(
            name="Condition Entry", created_by=self.staff, status="active",
        )
        self.s1 = SurveySection.objects.create(
            survey=self.survey, title="Main", sort_order=1,
        )
        self.trigger_q = SurveyQuestion.objects.create(
            section=self.s1, question_text="Has children?",
            question_type="yes_no", sort_order=1, required=True,
        )
        self.s2 = SurveySection.objects.create(
            survey=self.survey, title="Childcare", sort_order=2,
            condition_question=self.trigger_q, condition_value="1",
        )
        self.cond_q = SurveyQuestion.objects.create(
            section=self.s2, question_text="Childcare needed?",
            question_type="yes_no", sort_order=1, required=True,
        )
        FeatureToggle.objects.update_or_create(
            feature_key="surveys", defaults={"is_enabled": True},
        )
        self.client.login(username="sde_staff", password="testpass123")

    def test_hidden_section_required_field_not_enforced(self):
        """When trigger answer hides a section, its required fields don't cause errors."""
        url = f"/surveys/participant/{self.client_obj.pk}/enter/{self.survey.pk}/"
        resp = self.client.post(url, {
            f"q_{self.trigger_q.pk}": "0",  # No — hides childcare section
            # cond_q not submitted (section hidden by JS)
        })
        # Should succeed — childcare section is hidden, required not enforced
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(SurveyResponse.objects.count(), 1)

    def test_visible_section_required_field_enforced(self):
        """When trigger answer shows a section, its required fields are enforced."""
        url = f"/surveys/participant/{self.client_obj.pk}/enter/{self.survey.pk}/"
        resp = self.client.post(url, {
            f"q_{self.trigger_q.pk}": "1",  # Yes — shows childcare section
            # cond_q not submitted — should cause error
        })
        # Should fail — childcare section visible, required field missing
        self.assertEqual(resp.status_code, 200)  # re-renders form with error
        self.assertEqual(SurveyResponse.objects.count(), 0)

    def test_extra_answers_from_hidden_section_saved(self):
        """If JS didn't hide section and staff filled it in, answers are still saved."""
        url = f"/surveys/participant/{self.client_obj.pk}/enter/{self.survey.pk}/"
        resp = self.client.post(url, {
            f"q_{self.trigger_q.pk}": "0",  # No — hides childcare
            f"q_{self.cond_q.pk}": "1",     # But staff submitted anyway (JS failed)
        })
        self.assertEqual(resp.status_code, 302)
        response = SurveyResponse.objects.first()
        # Both answers saved — extra data preserved
        self.assertEqual(response.answers.count(), 2)
