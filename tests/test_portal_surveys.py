"""Tests for portal survey helpers and views.

Run with:
    pytest tests/test_portal_surveys.py -v
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.auth_app.models import User
from apps.clients.models import ClientFile
from apps.portal.models import ParticipantUser
from apps.surveys.models import (
    Survey, SurveySection, SurveyQuestion,
    SurveyAssignment, PartialAnswer,
)
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PageGroupingTests(TestCase):
    """Test grouping sections into pages."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="pg_staff", password="testpass123",
            display_name="PG Staff",
        )

    def test_single_page_no_breaks(self):
        """Survey with no page_break sections = 1 page."""
        from apps.portal.survey_helpers import group_sections_into_pages

        survey = Survey.objects.create(name="No Breaks", created_by=self.staff)
        s1 = SurveySection.objects.create(
            survey=survey, title="S1", sort_order=1, page_break=False,
        )
        s2 = SurveySection.objects.create(
            survey=survey, title="S2", sort_order=2, page_break=False,
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        pages = group_sections_into_pages(sections)
        self.assertEqual(len(pages), 1)
        self.assertEqual(len(pages[0]), 2)

    def test_multi_page_with_breaks(self):
        """page_break=True starts a new page."""
        from apps.portal.survey_helpers import group_sections_into_pages

        survey = Survey.objects.create(name="Paged", created_by=self.staff)
        SurveySection.objects.create(
            survey=survey, title="Page 1A", sort_order=1, page_break=False,
        )
        SurveySection.objects.create(
            survey=survey, title="Page 1B", sort_order=2, page_break=False,
        )
        SurveySection.objects.create(
            survey=survey, title="Page 2", sort_order=3, page_break=True,
        )
        SurveySection.objects.create(
            survey=survey, title="Page 3", sort_order=4, page_break=True,
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        pages = group_sections_into_pages(sections)
        self.assertEqual(len(pages), 3)
        self.assertEqual(len(pages[0]), 2)  # Page 1A + 1B
        self.assertEqual(len(pages[1]), 1)  # Page 2
        self.assertEqual(len(pages[2]), 1)  # Page 3

    def test_conditional_section_hidden(self):
        """Conditional section hidden when condition not met."""
        from apps.portal.survey_helpers import filter_visible_sections

        survey = Survey.objects.create(
            name="Conditional", created_by=self.staff, status="active",
        )
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1, question_text="Has children?",
            question_type="yes_no", sort_order=1, required=True,
        )
        SurveySection.objects.create(
            survey=survey, title="Childcare", sort_order=2,
            condition_question=trigger_q, condition_value="1",
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        # No partial answers — condition not met
        visible = filter_visible_sections(sections, partial_answers={})
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].title, "Main")

    def test_conditional_section_visible(self):
        """Conditional section visible when condition is met."""
        from apps.portal.survey_helpers import filter_visible_sections

        survey = Survey.objects.create(
            name="Conditional2", created_by=self.staff, status="active",
        )
        s1 = SurveySection.objects.create(
            survey=survey, title="Main", sort_order=1,
        )
        trigger_q = SurveyQuestion.objects.create(
            section=s1, question_text="Has children?",
            question_type="yes_no", sort_order=1, required=True,
        )
        SurveySection.objects.create(
            survey=survey, title="Childcare", sort_order=2,
            condition_question=trigger_q, condition_value="1",
        )
        sections = list(survey.sections.filter(is_active=True).order_by("sort_order"))
        # Partial answer matches condition
        visible = filter_visible_sections(
            sections, partial_answers={trigger_q.pk: "1"},
        )
        self.assertEqual(len(visible), 2)
