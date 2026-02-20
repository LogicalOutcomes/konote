"""Tests for the surveys app.

Run with:
    pytest tests/test_surveys.py -v
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.auth_app.models import User
from apps.surveys.models import Survey, SurveySection, SurveyQuestion
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
