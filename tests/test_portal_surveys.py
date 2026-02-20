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


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-portal",
)
class AutoSaveViewTests(TestCase):
    """Test the HTMX auto-save endpoint."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(
            username="auto_staff", password="testpass123",
            display_name="Auto Staff",
        )
        self.survey = Survey.objects.create(
            name="Auto Survey", status="active", created_by=self.staff,
        )
        self.section = SurveySection.objects.create(
            survey=self.survey, title="S1", sort_order=1,
        )
        self.q1 = SurveyQuestion.objects.create(
            section=self.section, question_text="Name?",
            question_type="short_text", sort_order=1,
        )
        self.q2 = SurveyQuestion.objects.create(
            section=self.section, question_text="How?",
            question_type="rating_scale", sort_order=2,
            options_json=[
                {"value": "1", "label": "Bad", "score": 1},
                {"value": "2", "label": "OK", "score": 2},
                {"value": "3", "label": "Good", "score": 3},
            ],
        )
        self.client_file = ClientFile.objects.create(
            record_id="AUTO-001", status="active",
        )
        self.client_file.first_name = "Auto"
        self.client_file.last_name = "Test"
        self.client_file.save()
        self.participant = ParticipantUser.objects.create_participant(
            email="auto@example.com",
            client_file=self.client_file,
            display_name="Auto P",
            password="testpass123",
        )
        from apps.admin_settings.models import FeatureToggle
        FeatureToggle.objects.update_or_create(
            feature_key="surveys",
            defaults={"is_enabled": True},
        )
        FeatureToggle.objects.update_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )
        self.assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=self.participant,
            client_file=self.client_file,
            status="in_progress",
        )

    def _portal_login(self):
        """Set up portal session for the test client."""
        # Force a session to exist by making any request first
        self.client.get("/my/login/")
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.pk)
        session.save()

    def test_autosave_creates_partial_answer(self):
        self._portal_login()
        response = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane Doe"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        pa = PartialAnswer.objects.get(
            assignment=self.assignment, question=self.q1,
        )
        self.assertEqual(pa.value, "Jane Doe")

    def test_autosave_updates_existing(self):
        self._portal_login()
        # First save
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane"},
            HTTP_HX_REQUEST="true",
        )
        # Update
        self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane Doe"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(PartialAnswer.objects.filter(
            assignment=self.assignment, question=self.q1,
        ).count(), 1)
        pa = PartialAnswer.objects.get(
            assignment=self.assignment, question=self.q1,
        )
        self.assertEqual(pa.value, "Jane Doe")

    def test_autosave_rejects_non_htmx(self):
        self._portal_login()
        response = self.client.post(
            f"/my/surveys/{self.assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "Jane"},
        )
        self.assertEqual(response.status_code, 400)

    def test_autosave_wrong_assignment(self):
        """Cannot save to someone else's assignment."""
        other_cf = ClientFile.objects.create(
            record_id="OTHER-001", status="active",
        )
        other_cf.first_name = "Other"
        other_cf.last_name = "Person"
        other_cf.save()
        other_p = ParticipantUser.objects.create_participant(
            email="other@example.com",
            client_file=other_cf,
            display_name="Other P",
            password="testpass123",
        )
        other_assignment = SurveyAssignment.objects.create(
            survey=self.survey,
            participant_user=other_p,
            client_file=other_cf,
            status="in_progress",
        )
        self._portal_login()
        response = self.client.post(
            f"/my/surveys/{other_assignment.pk}/save/",
            {"question_id": self.q1.pk, "value": "hacked"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 404)
