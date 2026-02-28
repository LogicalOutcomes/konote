"""Tests for portal Phase B views: dashboard, goals, goal detail, progress, my words.

Verifies the view-template data contracts for B2-B6 are correct.

Run with:
    pytest apps/portal/tests/test_views_b2_b6.py -v
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.models import User
from apps.clients.models import ClientFile
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
)
from apps.portal.models import ParticipantUser, StaffPortalNote
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-b2-b6",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class PortalViewsB2B6Base(TestCase):
    """Base class with shared setup for B2-B6 portal view tests."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        # Staff user (required as ProgressNote.author)
        self.staff_user = User.objects.create_user(
            username="b2b6staff",
            password="staffpass123",
            display_name="Staff User",
        )

        # Client file
        self.client_file = ClientFile.objects.create(
            record_id="B2B6-001", status="active",
        )
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Participant"
        self.client_file.save()

        # Participant user
        self.participant = ParticipantUser.objects.create_participant(
            email="b2b6@example.com",
            client_file=self.client_file,
            display_name="Test P",
            password="TestPass123!",
        )
        self.participant.mfa_method = "exempt"
        self.participant.save()

        # Feature toggle
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

        # Plan section + target
        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Employment",
            status="default",
            sort_order=1,
        )
        self.target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
            status="default",
            sort_order=1,
        )
        self.target.name = "Find stable housing"
        self.target.description = "A place to call home"
        self.target.client_goal = "I want a safe place to live"
        self.target.save()

        # Metric definition (portal-visible)
        self.metric_def = MetricDefinition.objects.create(
            name="Confidence",
            unit="score",
            min_value=0,
            max_value=10,
            portal_visibility="yes",
        )
        PlanTargetMetric.objects.create(
            plan_target=self.target,
            metric_def=self.metric_def,
        )

        # Progress note with participant reflection + descriptor
        self.note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            status="default",
            author=self.staff_user,
        )
        self.note.participant_reflection = "I feel better about my options"
        self.note.save()

        # Progress note target with descriptor and client_words
        self.note_target = ProgressNoteTarget(
            progress_note=self.note,
            plan_target=self.target,
            progress_descriptor="shifting",
        )
        self.note_target.client_words = "I found a few leads"
        self.note_target.save()

        # Metric value
        MetricValue.objects.create(
            progress_note_target=self.note_target,
            metric_def=self.metric_def,
            value="7",
        )

    def tearDown(self):
        enc_module._fernet = None

    def _login(self):
        """Set portal session to simulate a logged-in participant."""
        session = self.client.session
        session["_portal_participant_id"] = str(self.participant.id)
        session.save()


class DashboardViewTests(PortalViewsB2B6Base):
    """B2: Dashboard with progressive disclosure."""

    def test_dashboard_renders(self):
        self._login()
        response = self.client.get("/my/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test P")

    def test_dashboard_has_highlight_message(self):
        """Dashboard should show highlight_message from latest note date."""
        self._login()
        response = self.client.get("/my/")
        self.assertEqual(response.status_code, 200)
        # The highlight message is based on latest progress note
        self.assertContains(response, "last session was recorded")

    def test_dashboard_nav_cards(self):
        """Dashboard should contain navigation cards to goals, progress, milestones."""
        self._login()
        response = self.client.get("/my/")
        self.assertContains(response, "My Goals")
        self.assertContains(response, "My Progress")
        self.assertContains(response, "Milestones")

    def test_dashboard_new_since_banner(self):
        """Dashboard should show new-since-last-visit banner when there are updates."""
        from django.utils import timezone
        from datetime import timedelta
        # Set last_login to yesterday so the note counts as "new"
        self.participant.last_login = timezone.now() - timedelta(days=1)
        self.participant.save(update_fields=["last_login"])
        self._login()
        response = self.client.get("/my/")
        self.assertContains(response, "new update")

    def test_dashboard_staff_notes(self):
        """Dashboard should show staff portal notes."""
        note = StaffPortalNote(
            client_file=self.client_file,
            is_active=True,
        )
        note.content = "Keep up the great work!"
        note.save()
        self._login()
        response = self.client.get("/my/")
        self.assertContains(response, "Keep up the great work!")


class GoalsListViewTests(PortalViewsB2B6Base):
    """B3: My Goals page."""

    def test_goals_list_renders(self):
        self._login()
        response = self.client.get("/my/goals/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employment")
        self.assertContains(response, "Find stable housing")

    def test_goals_shows_client_goal(self):
        """Each goal card should show the participant's own words."""
        self._login()
        response = self.client.get("/my/goals/")
        self.assertContains(response, "I want a safe place to live")

    def test_goals_shows_latest_descriptor(self):
        """Each goal card should show the latest progress descriptor."""
        self._login()
        response = self.client.get("/my/goals/")
        # "shifting" maps to "Something's shifting"
        self.assertContains(response, "shifting")

    def test_goals_empty_state(self):
        """No goals should show empty state message."""
        self.target.status = "completed"
        self.target.save()
        self._login()
        response = self.client.get("/my/goals/")
        self.assertContains(response, "No goals have been added yet")

    def test_goals_correction_link(self):
        """Goals page should have the correction request link."""
        self._login()
        response = self.client.get("/my/goals/")
        self.assertContains(response, "Something doesn")


class GoalDetailViewTests(PortalViewsB2B6Base):
    """B4: Goal detail page with timeline and chart."""

    def test_goal_detail_renders(self):
        self._login()
        response = self.client.get(f"/my/goals/{self.target.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find stable housing")

    def test_goal_detail_shows_client_goal(self):
        self._login()
        response = self.client.get(f"/my/goals/{self.target.pk}/")
        self.assertContains(response, "I want a safe place to live")

    def test_goal_detail_shows_descriptors(self):
        """Progress timeline should show descriptor entries."""
        self._login()
        response = self.client.get(f"/my/goals/{self.target.pk}/")
        # "shifting" displayed as "Something's shifting"
        self.assertContains(response, "shifting")

    def test_goal_detail_shows_client_words(self):
        """Goal detail should show 'What I said about this goal'."""
        self._login()
        response = self.client.get(f"/my/goals/{self.target.pk}/")
        self.assertContains(response, "I found a few leads")

    def test_goal_detail_has_chart_data(self):
        """Goal detail should include chart data JSON for Chart.js."""
        self._login()
        response = self.client.get(f"/my/goals/{self.target.pk}/")
        self.assertContains(response, "chart-data")
        self.assertContains(response, "Confidence")

    def test_goal_detail_404_other_client(self):
        """Cannot view another client's goal."""
        other_cf = ClientFile.objects.create(record_id="OTHER-001", status="active")
        other_section = PlanSection.objects.create(
            client_file=other_cf, name="Other", status="default",
        )
        other_target = PlanTarget(
            plan_section=other_section, client_file=other_cf,
            status="default", sort_order=1,
        )
        other_target.name = "Other goal"
        other_target.save()

        self._login()
        response = self.client.get(f"/my/goals/{other_target.pk}/")
        self.assertEqual(response.status_code, 404)


class ProgressViewTests(PortalViewsB2B6Base):
    """B5: My Progress page with Chart.js charts."""

    def test_progress_renders(self):
        self._login()
        response = self.client.get("/my/progress/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How I")

    def test_progress_has_chart_data(self):
        """Progress page should contain chart data JSON."""
        self._login()
        response = self.client.get("/my/progress/")
        self.assertContains(response, "chart-data")

    def test_progress_empty_state(self):
        """No data should show empty state."""
        MetricValue.objects.all().delete()
        self._login()
        response = self.client.get("/my/progress/")
        self.assertContains(response, "No progress data")

    def test_progress_excludes_hidden_metrics(self):
        """Metrics with portal_visibility='no' should not appear."""
        self.metric_def.portal_visibility = "no"
        self.metric_def.save()
        self._login()
        response = self.client.get("/my/progress/")
        self.assertNotContains(response, "chart-data")


class MyWordsViewTests(PortalViewsB2B6Base):
    """B6: What I've been saying page."""

    def test_my_words_renders(self):
        self._login()
        response = self.client.get("/my/my-words/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What I")

    def test_my_words_shows_reflection(self):
        """Page should show participant reflections."""
        self._login()
        response = self.client.get("/my/my-words/")
        self.assertContains(response, "I feel better about my options")

    def test_my_words_shows_client_words(self):
        """Page should show client_words from note targets."""
        self._login()
        response = self.client.get("/my/my-words/")
        self.assertContains(response, "I found a few leads")

    def test_my_words_shows_goal_context(self):
        """Client words entries should show which goal they relate to."""
        self._login()
        response = self.client.get("/my/my-words/")
        self.assertContains(response, "Find stable housing")

    def test_my_words_empty_state(self):
        """No reflections or words should show empty state."""
        self.note.delete()
        self._login()
        response = self.client.get("/my/my-words/")
        self.assertContains(response, "Nothing here yet")


class MilestonesViewTests(PortalViewsB2B6Base):
    """B7: Milestones page (completed goals)."""

    def test_milestones_renders(self):
        self._login()
        response = self.client.get("/my/milestones/")
        self.assertEqual(response.status_code, 200)

    def test_milestones_empty_state(self):
        """No completed targets should show encouraging empty state."""
        self._login()
        response = self.client.get("/my/milestones/")
        self.assertContains(response, "No milestones yet")

    def test_milestones_shows_completed_target(self):
        """Completed targets should appear as milestones."""
        self.target.status = "completed"
        self.target.save()
        self._login()
        response = self.client.get("/my/milestones/")
        self.assertContains(response, "Find stable housing")
        self.assertContains(response, "I want a safe place to live")
        self.assertContains(response, "You did it!")

    def test_milestones_shows_completion_date(self):
        """Milestones should display completion date."""
        self.target.status = "completed"
        self.target.save()
        self._login()
        response = self.client.get("/my/milestones/")
        self.assertContains(response, "Completed:")
