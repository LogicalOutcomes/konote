"""Tests for alert cancellation recommendation workflow (Wave 5A).

Covers:
- Staff can recommend cancellation (200), cannot cancel directly (403)
- PM can cancel directly (200), cannot recommend (403)
- PM approve: alert cancelled + audit log
- PM reject: alert stays active, review_note required
- Duplicate pending recommendation blocked
- Receptionist / executive get 403 on all recommendation views
- Already-reviewed recommendation redirects
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert, AlertCancellationRecommendation
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AlertRecommendationWorkflowTest(TestCase):
    """Test the two-person safety rule for alert cancellation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        self.program = Program.objects.create(name="DV Support", colour_hex="#EF4444")

        # Staff user — can recommend, cannot cancel
        self.staff_user = User.objects.create_user(
            username="staff1", password="testpass123", display_name="Staff One",
        )
        UserProgramRole.objects.create(
            user=self.staff_user, program=self.program, role="staff", status="active",
        )

        # PM user — can cancel directly, can review recommendations
        self.pm_user = User.objects.create_user(
            username="pm1", password="testpass123", display_name="PM One",
        )
        UserProgramRole.objects.create(
            user=self.pm_user, program=self.program, role="program_manager", status="active",
        )

        # Receptionist — should be denied everything
        self.receptionist = User.objects.create_user(
            username="recep1", password="testpass123", display_name="Receptionist",
        )
        UserProgramRole.objects.create(
            user=self.receptionist, program=self.program, role="receptionist", status="active",
        )

        # Executive — should be denied everything
        self.executive = User.objects.create_user(
            username="exec1", password="testpass123", display_name="Exec One",
        )
        UserProgramRole.objects.create(
            user=self.executive, program=self.program, role="executive", status="active",
        )

        # Client enrolled in the program
        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

        # Active alert for this client
        self.alert = Alert.objects.create(
            client_file=self.client_file,
            content="Safety concern documented.",
            author=self.staff_user,
            author_program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    # ------------------------------------------------------------------
    # Staff: recommend cancellation
    # ------------------------------------------------------------------

    def test_staff_can_access_recommend_form(self):
        """Staff sees the recommendation form (GET 200)."""
        self.client.login(username="staff1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/recommend-cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_staff_can_submit_recommendation(self):
        """Staff can POST a recommendation successfully."""
        self.client.login(username="staff1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/recommend-cancel/"
        response = self.client.post(url, {"assessment": "Client is stable, alert no longer needed."})
        self.assertEqual(response.status_code, 302)  # redirect on success
        self.assertTrue(
            AlertCancellationRecommendation.objects.filter(
                alert=self.alert, status="pending",
            ).exists()
        )

    def test_staff_cannot_cancel_alert_directly(self):
        """Staff gets 403 trying to cancel an alert directly."""
        self.client.login(username="staff1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_duplicate_pending_recommendation_blocked(self):
        """Submitting a second recommendation while one is pending redirects."""
        AlertCancellationRecommendation.objects.create(
            alert=self.alert,
            recommended_by=self.staff_user,
            assessment="First recommendation.",
        )
        self.client.login(username="staff1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/recommend-cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # redirected with info message

    # ------------------------------------------------------------------
    # PM: direct cancellation
    # ------------------------------------------------------------------

    def test_pm_can_cancel_directly(self):
        """PM can access alert cancel form (GET 200)."""
        self.client.login(username="pm1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_pm_cannot_recommend(self):
        """PM gets 403 trying to recommend cancellation (PMs cancel directly)."""
        self.client.login(username="pm1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/recommend-cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # PM: review recommendations
    # ------------------------------------------------------------------

    def test_pm_can_access_queue(self):
        """PM can access the recommendation queue (GET 200)."""
        self.client.login(username="pm1", password="testpass123")
        response = self.client.get("/events/alerts/recommendations/")
        self.assertEqual(response.status_code, 200)

    def test_pm_queue_explains_page_purpose(self):
        """Queue explains that this page is for reviewing alert cancellation recommendations."""
        self.client.login(username="pm1", password="testpass123")
        response = self.client.get("/events/alerts/recommendations/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "When a staff member believes a safety alert is no longer needed",
        )

    def test_pm_approve_cancels_alert(self):
        """PM approving a recommendation cancels the alert."""
        rec = AlertCancellationRecommendation.objects.create(
            alert=self.alert,
            recommended_by=self.staff_user,
            assessment="Client is stable.",
        )
        self.client.login(username="pm1", password="testpass123")
        url = f"/events/alerts/recommendations/{rec.pk}/review/"
        response = self.client.post(url, {"action": "approve", "review_note": ""})
        self.assertEqual(response.status_code, 302)

        rec.refresh_from_db()
        self.assertEqual(rec.status, "approved")
        self.assertIsNotNone(rec.reviewed_by)
        self.assertIsNotNone(rec.reviewed_at)

        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, "cancelled")

    def test_pm_approve_creates_audit_log(self):
        """Approving a recommendation creates an audit log entry."""
        from apps.audit.models import AuditLog

        rec = AlertCancellationRecommendation.objects.create(
            alert=self.alert,
            recommended_by=self.staff_user,
            assessment="Client stable.",
        )
        self.client.login(username="pm1", password="testpass123")
        url = f"/events/alerts/recommendations/{rec.pk}/review/"
        self.client.post(url, {"action": "approve", "review_note": ""})

        log = AuditLog.objects.using("audit").filter(
            resource_type="alert", resource_id=self.alert.pk, action="cancel",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.metadata["review_action"], "approved")

    def test_pm_reject_keeps_alert_active(self):
        """PM rejecting a recommendation keeps the alert active."""
        rec = AlertCancellationRecommendation.objects.create(
            alert=self.alert,
            recommended_by=self.staff_user,
            assessment="Should be cancelled.",
        )
        self.client.login(username="pm1", password="testpass123")
        url = f"/events/alerts/recommendations/{rec.pk}/review/"
        response = self.client.post(url, {
            "action": "reject",
            "review_note": "Alert still relevant.",
        })
        self.assertEqual(response.status_code, 302)

        rec.refresh_from_db()
        self.assertEqual(rec.status, "rejected")

        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, "default")  # still active

    def test_reject_requires_review_note(self):
        """Rejection without a review_note fails validation."""
        rec = AlertCancellationRecommendation.objects.create(
            alert=self.alert,
            recommended_by=self.staff_user,
            assessment="Cancel please.",
        )
        self.client.login(username="pm1", password="testpass123")
        url = f"/events/alerts/recommendations/{rec.pk}/review/"
        response = self.client.post(url, {"action": "reject", "review_note": ""})
        # Should re-render the form (200) with validation error, not redirect
        self.assertEqual(response.status_code, 200)
        rec.refresh_from_db()
        self.assertEqual(rec.status, "pending")  # still pending

    def test_already_reviewed_recommendation_redirects(self):
        """Trying to review an already-reviewed recommendation redirects."""
        rec = AlertCancellationRecommendation.objects.create(
            alert=self.alert,
            recommended_by=self.staff_user,
            assessment="Cancel it.",
            status="approved",
        )
        self.client.login(username="pm1", password="testpass123")
        url = f"/events/alerts/recommendations/{rec.pk}/review/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    # ------------------------------------------------------------------
    # Receptionist: denied on everything
    # ------------------------------------------------------------------

    def test_receptionist_cannot_recommend(self):
        self.client.login(username="recep1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/recommend-cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_receptionist_cannot_cancel(self):
        self.client.login(username="recep1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_receptionist_cannot_access_queue(self):
        self.client.login(username="recep1", password="testpass123")
        response = self.client.get("/events/alerts/recommendations/")
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Executive: denied on everything
    # ------------------------------------------------------------------

    def test_executive_cannot_recommend(self):
        self.client.login(username="exec1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/recommend-cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_executive_cannot_cancel(self):
        self.client.login(username="exec1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/cancel/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_executive_cannot_access_queue(self):
        self.client.login(username="exec1", password="testpass123")
        response = self.client.get("/events/alerts/recommendations/")
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Re-recommend after rejection
    # ------------------------------------------------------------------

    def test_staff_can_re_recommend_after_rejection(self):
        """After rejection, staff can submit a new recommendation."""
        AlertCancellationRecommendation.objects.create(
            alert=self.alert,
            recommended_by=self.staff_user,
            assessment="Old recommendation.",
            status="rejected",
        )
        self.client.login(username="staff1", password="testpass123")
        url = f"/events/alerts/{self.alert.pk}/recommend-cancel/"
        response = self.client.post(url, {"assessment": "Revised assessment."})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            AlertCancellationRecommendation.objects.filter(
                alert=self.alert, status="pending",
            ).count(),
            1,
        )
