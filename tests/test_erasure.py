"""Tests for client data erasure workflow (ERASE9).

Covers: models, service functions, views, permissions, edge cases.
~40 tests organised into groups matching the implementation plan.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.auth_app.models import User
from apps.clients.erasure import (
    build_data_summary,
    check_all_approved,
    execute_erasure,
    get_available_tiers,
    get_required_programs,
    is_deadlocked,
    record_approval,
)
from apps.clients.models import (
    ClientDetailValue,
    ClientFile,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
    ErasureApproval,
    ErasureRequest,
)
from apps.events.models import Alert, Event, EventType
from apps.notes.models import ProgressNote
from apps.plans.models import PlanSection
from apps.programs.models import Program, UserProgramRole
from konote import encryption as enc_module


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class ErasureModelTests(TestCase):
    """Test ErasureRequest and ErasureApproval model creation."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.record_id = "REC-001"
        self.client_file.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_create_erasure_request(self):
        er = ErasureRequest.objects.create(
            client_file=self.client_file,
            client_pk=self.client_file.pk,
            client_record_id="REC-001",
            requested_by=self.admin,
            requested_by_display="Admin User",
            reason_category="client_requested",
            request_reason="Client asked to have data removed.",
            programs_required=[self.prog.pk],
        )
        self.assertEqual(er.status, "pending")
        self.assertEqual(er.client_pk, self.client_file.pk)
        self.assertTrue(er.erasure_code.startswith("ER-"))
        self.assertIn(f"Client #{self.client_file.pk}", str(er))

    def test_erasure_request_survives_client_deletion(self):
        er = ErasureRequest.objects.create(
            client_file=self.client_file,
            client_pk=self.client_file.pk,
            requested_by=self.admin,
            requested_by_display="Admin",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        saved_pk = self.client_file.pk
        self.client_file.delete()
        er.refresh_from_db()
        self.assertIsNone(er.client_file)
        self.assertEqual(er.client_pk, saved_pk)

    def test_erasure_approval_unique_per_program(self):
        er = ErasureRequest.objects.create(
            client_file=self.client_file,
            client_pk=self.client_file.pk,
            requested_by=self.admin,
            requested_by_display="Admin",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        ErasureApproval.objects.create(
            erasure_request=er,
            program=self.prog,
            approved_by=self.admin,
            approved_by_display="Admin",
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ErasureApproval.objects.create(
                erasure_request=er,
                program=self.prog,
                approved_by=self.admin,
                approved_by_display="Admin",
            )


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class BuildDataSummaryTests(TestCase):
    """Test build_data_summary counts."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_empty_client_returns_zero_counts(self):
        summary = build_data_summary(self.cf)
        self.assertEqual(summary["progress_notes"], 0)
        self.assertEqual(summary["events"], 0)
        self.assertEqual(summary["alerts"], 0)
        self.assertEqual(summary["enrolments"], 0)

    def test_counts_related_records(self):
        # Create some related records
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog)
        et = EventType.objects.create(name="Test Event Type")
        from django.utils import timezone
        Event.objects.create(client_file=self.cf, event_type=et, start_timestamp=timezone.now())
        Alert.objects.create(client_file=self.cf, content="Safety concern")

        summary = build_data_summary(self.cf)
        self.assertEqual(summary["enrolments"], 1)
        self.assertEqual(summary["events"], 1)
        self.assertEqual(summary["alerts"], 1)

    def test_summary_contains_expected_count_keys(self):
        summary = build_data_summary(self.cf)
        count_keys = [
            "progress_notes", "plan_sections", "plan_targets",
            "events", "alerts", "custom_field_values", "enrolments", "metric_values",
        ]
        for key in count_keys:
            self.assertIn(key, summary)
            self.assertIsInstance(summary[key], int, f"{key} should be an integer, got {type(summary[key])}")
        # Non-count fields are optional lists/dicts
        self.assertIsInstance(summary.get("programmes", []), list)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class GetRequiredProgramsTests(TestCase):
    """Test get_required_programs with 3-tier fallback."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6", status="active")
        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_active_enrolments_returned(self):
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog_a, status="enrolled")
        result = get_required_programs(self.cf)
        self.assertEqual(result, [self.prog_a.pk])

    def test_discharged_client_uses_historical(self):
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog_a, status="unenrolled")
        result = get_required_programs(self.cf)
        self.assertIn(self.prog_a.pk, result)

    def test_no_enrolments_falls_back_to_any_program(self):
        # No enrolments at all — should still return at least one program
        result = get_required_programs(self.cf)
        self.assertTrue(len(result) > 0, "Must never return empty list")

    def test_never_returns_empty(self):
        result = get_required_programs(self.cf)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class MultiProgramApprovalTests(TestCase):
    """Test multi-program approval workflow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.pm_a = User.objects.create_user(username="pm_a", password="testpass123")
        self.pm_b = User.objects.create_user(username="pm_b", password="testpass123")

        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6", status="active")

        UserProgramRole.objects.create(user=self.staff, program=self.prog_a, role="staff")
        UserProgramRole.objects.create(user=self.pm_a, program=self.prog_a, role="program_manager")
        UserProgramRole.objects.create(user=self.pm_b, program=self.prog_b, role="program_manager")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog_a, status="enrolled")
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog_b, status="enrolled")

        self.er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            client_record_id="REC-001",
            requested_by=self.staff,
            requested_by_display="Staff User",
            reason_category="client_requested",
            request_reason="Client requested.",
            data_summary=build_data_summary(self.cf),
            programs_required=[self.prog_a.pk, self.prog_b.pk],
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_single_approval_does_not_execute(self):
        approval, executed = record_approval(self.er, self.pm_a, self.prog_a, "127.0.0.1")
        self.assertFalse(executed)
        self.er.refresh_from_db()
        self.assertEqual(self.er.status, "pending")

    def test_all_approvals_triggers_execution(self):
        record_approval(self.er, self.pm_a, self.prog_a, "127.0.0.1")
        approval, executed = record_approval(self.er, self.pm_b, self.prog_b, "127.0.0.1")
        self.assertTrue(executed)
        self.er.refresh_from_db()
        # Default tier is "anonymise", so status becomes "anonymised"
        self.assertEqual(self.er.status, "anonymised")

    def test_check_all_approved_false_when_partial(self):
        ErasureApproval.objects.create(
            erasure_request=self.er,
            program=self.prog_a,
            approved_by=self.pm_a,
            approved_by_display="PM A",
        )
        self.assertFalse(check_all_approved(self.er))

    def test_check_all_approved_true_when_all(self):
        ErasureApproval.objects.create(
            erasure_request=self.er, program=self.prog_a,
            approved_by=self.pm_a, approved_by_display="PM A",
        )
        ErasureApproval.objects.create(
            erasure_request=self.er, program=self.prog_b,
            approved_by=self.pm_b, approved_by_display="PM B",
        )
        self.assertTrue(check_all_approved(self.er))


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class RejectionTests(TestCase):
    """Test rejection after partial approval."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.pm_a = User.objects.create_user(username="pm_a", password="testpass123")
        self.pm_b = User.objects.create_user(username="pm_b", password="testpass123")

        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6", status="active")

        UserProgramRole.objects.create(user=self.pm_a, program=self.prog_a, role="program_manager")
        UserProgramRole.objects.create(user=self.pm_b, program=self.prog_b, role="program_manager")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog_a, status="enrolled")
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog_b, status="enrolled")

        self.er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog_a.pk, self.prog_b.pk],
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_rejection_after_partial_approval_preserves_data(self):
        # PM-A approves, PM-B rejects
        record_approval(self.er, self.pm_a, self.prog_a, "127.0.0.1")

        self.er.status = "rejected"
        self.er.save(update_fields=["status"])

        # Client data should still exist
        self.assertTrue(ClientFile.objects.filter(pk=self.cf.pk).exists())
        # PM-A's approval should still exist for audit trail
        self.assertEqual(self.er.approvals.count(), 1)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class ExecuteErasureTests(TestCase):
    """Test the actual erasure execution logic."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.pm = User.objects.create_user(username="pm", password="testpass123")

        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        UserProgramRole.objects.create(user=self.pm, program=self.prog, role="program_manager")

        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.record_id = "REC-001"
        self.cf.save()

        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")
        Alert.objects.create(client_file=self.cf, content="Test alert")

        # Create a custom field value
        grp = CustomFieldGroup.objects.create(title="Contact")
        fd = CustomFieldDefinition.objects.create(group=grp, name="Phone", input_type="text")
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=fd)
        cdv.set_value("555-1234")
        cdv.save()

        self.er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            client_record_id="REC-001",
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="client_requested",
            request_reason="Client request.",
            data_summary=build_data_summary(self.cf),
            programs_required=[self.prog.pk],
            erasure_tier="full_erasure",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_execute_deletes_client_and_cascades(self):
        cf_pk = self.cf.pk
        execute_erasure(self.er, "127.0.0.1")

        self.assertFalse(ClientFile.objects.filter(pk=cf_pk).exists())
        self.assertFalse(Alert.objects.filter(client_file_id=cf_pk).exists())
        self.assertFalse(ClientProgramEnrolment.objects.filter(client_file_id=cf_pk).exists())
        self.assertFalse(ClientDetailValue.objects.filter(client_file_id=cf_pk).exists())

    def test_execute_updates_erasure_request(self):
        execute_erasure(self.er, "127.0.0.1")
        self.er.refresh_from_db()
        self.assertEqual(self.er.status, "approved")
        self.assertIsNotNone(self.er.completed_at)
        self.assertIsNone(self.er.client_file)

    def test_execute_scrubs_registration_pii(self):
        from apps.registration.models import RegistrationLink, RegistrationSubmission

        link = RegistrationLink.objects.create(
            program=self.prog, title="Test Link",
            created_by=self.staff,
        )
        sub = RegistrationSubmission()
        sub.registration_link = link
        sub.first_name = "Jane"
        sub.last_name = "Doe"
        sub.email = "jane@example.com"
        sub.client_file = self.cf
        sub.save()

        execute_erasure(self.er, "127.0.0.1")

        sub.refresh_from_db()
        # Submission should still exist but PII scrubbed
        self.assertTrue(RegistrationSubmission.objects.filter(pk=sub.pk).exists())
        self.assertEqual(sub._first_name_encrypted, b"")
        self.assertEqual(sub._last_name_encrypted, b"")
        self.assertEqual(sub._email_encrypted, b"")
        self.assertEqual(sub.email_hash, "")

    def test_execute_raises_if_client_already_deleted(self):
        self.cf.delete()
        self.er.refresh_from_db()
        with self.assertRaises(ValueError):
            execute_erasure(self.er, "127.0.0.1")

    def test_audit_log_created_on_erasure(self):
        from apps.audit.models import AuditLog

        execute_erasure(self.er, "127.0.0.1")
        logs = AuditLog.objects.using("audit").filter(resource_type="client_erasure")
        self.assertTrue(logs.exists())

    @patch("apps.clients.erasure._log_audit", side_effect=Exception("Audit DB down"))
    def test_erasure_fails_if_audit_db_unavailable(self, mock_audit):
        """Erasure must not proceed if audit logging fails."""
        cf_pk = self.cf.pk
        with self.assertRaises(Exception):
            execute_erasure(self.er, "127.0.0.1")
        # Client data should still exist
        self.assertTrue(ClientFile.objects.filter(pk=cf_pk).exists())


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class DeadlockTests(TestCase):
    """Test PM-as-requester deadlock detection and admin fallback."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.pm = User.objects.create_user(username="pm", password="testpass123")
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)

        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        UserProgramRole.objects.create(user=self.pm, program=self.prog, role="program_manager")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")

        self.er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.pm,
            requested_by_display="PM",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_is_deadlocked_when_requester_is_only_pm(self):
        self.assertTrue(is_deadlocked(self.er))

    def test_not_deadlocked_when_other_pm_exists(self):
        other_pm = User.objects.create_user(username="other_pm", password="testpass123")
        UserProgramRole.objects.create(user=other_pm, program=self.prog, role="program_manager")
        self.assertFalse(is_deadlocked(self.er))

    def test_admin_can_approve_in_deadlock(self):
        approval, executed = record_approval(self.er, self.admin, self.prog, "127.0.0.1")
        self.assertTrue(executed)
        self.er.refresh_from_db()
        # Default tier is "anonymise", so status becomes "anonymised"
        self.assertEqual(self.er.status, "anonymised")

    def test_requester_cannot_self_approve_without_deadlock(self):
        other_pm = User.objects.create_user(username="other_pm", password="testpass123")
        UserProgramRole.objects.create(user=other_pm, program=self.prog, role="program_manager")
        with self.assertRaises(ValueError):
            record_approval(self.er, self.pm, self.prog, "127.0.0.1")


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class ErasureViewPermissionTests(TestCase):
    """Test view permissions for erasure workflow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.pm = User.objects.create_user(username="pm", password="testpass123")
        self.receptionist = User.objects.create_user(username="recep", password="testpass123")
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)

        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")

        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.pm, program=self.prog, role="program_manager")
        UserProgramRole.objects.create(user=self.receptionist, program=self.prog, role="receptionist")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")

    def tearDown(self):
        enc_module._fernet = None

    def test_staff_cannot_access_request_form(self):
        """Staff role can no longer create erasure requests (PM+ required)."""
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get(f"/clients/{self.cf.pk}/erase/")
        self.assertEqual(resp.status_code, 403)

    def test_pm_can_access_request_form(self):
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get(f"/clients/{self.cf.pk}/erase/")
        self.assertEqual(resp.status_code, 200)

    def test_receptionist_cannot_access_request_form(self):
        self.client.login(username="recep", password="testpass123")
        resp = self.client.get(f"/clients/{self.cf.pk}/erase/")
        self.assertEqual(resp.status_code, 403)

    def test_pm_can_access_pending_list(self):
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get("/erasure/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_access_pending_list(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/erasure/")
        self.assertEqual(resp.status_code, 200)

    def test_staff_cannot_access_pending_list(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/erasure/")
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_redirected(self):
        resp = self.client.get("/erasure/")
        self.assertEqual(resp.status_code, 302)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class ErasureViewWorkflowTests(TestCase):
    """Test the full view-level workflow: request → approve → delete."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.pm = User.objects.create_user(username="pm", password="testpass123")

        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")

        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.pm, program=self.prog, role="program_manager")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.record_id = "REC-099"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")

    def tearDown(self):
        enc_module._fernet = None

    def test_create_request_via_post(self):
        """PM can create an erasure request with tier and acknowledgements."""
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/clients/{self.cf.pk}/erase/", {
            "erasure_tier": "anonymise",
            "reason_category": "client_requested",
            "request_reason": "Client asked for data removal.",
            "ack_permanent": "on",
            "ack_authorised": "on",
            "ack_notify": "on",
        })
        self.assertEqual(resp.status_code, 302)
        er = ErasureRequest.objects.last()
        self.assertIsNotNone(er)
        self.assertEqual(er.status, "pending")
        self.assertEqual(er.erasure_tier, "anonymise")
        self.assertEqual(er.client_file, self.cf)
        self.assertTrue(er.erasure_code.startswith("ER-"))

    def test_full_erasure_rejected_when_retention_not_expired(self):
        """POSTing full_erasure when retention hasn't expired must be rejected."""
        import datetime
        self.cf.retention_expires = datetime.date(2030, 1, 1)
        self.cf.save()

        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/clients/{self.cf.pk}/erase/", {
            "erasure_tier": "full_erasure",
            "reason_category": "retention_expired",
            "request_reason": "Trying to bypass retention.",
            "ack_permanent": "on",
            "ack_authorised": "on",
            "ack_notify": "on",
        })
        # Form should re-render (200) with validation error, not redirect (302)
        self.assertEqual(resp.status_code, 200)
        # No erasure request should have been created
        self.assertFalse(ErasureRequest.objects.filter(client_file=self.cf).exists())

    def test_duplicate_request_redirects(self):
        ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/clients/{self.cf.pk}/erase/", {
            "erasure_tier": "anonymise",
            "reason_category": "client_requested",
            "request_reason": "Another attempt.",
            "ack_permanent": "on",
            "ack_authorised": "on",
            "ack_notify": "on",
        })
        # Should redirect to existing request, not create a new one
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ErasureRequest.objects.filter(client_file=self.cf, status="pending").count(), 1)

    @patch("apps.clients.erasure_views._notify_pms_erasure_request")
    def test_approve_full_erasure_via_post(self, mock_notify):
        """Full erasure tier: approval deletes client data."""
        import datetime
        # Set retention_expires in the past so full_erasure tier is available
        self.cf.retention_expires = datetime.date(2020, 1, 1)
        self.cf.save(update_fields=["retention_expires"])

        # Create a second PM so the first PM isn't approving their own request
        pm2 = User.objects.create_user(username="pm2", password="testpass123")
        UserProgramRole.objects.create(user=pm2, program=self.prog, role="program_manager")

        self.client.login(username="pm", password="testpass123")
        self.client.post(f"/clients/{self.cf.pk}/erase/", {
            "erasure_tier": "full_erasure",
            "reason_category": "client_requested",
            "request_reason": "Client asked.",
            "ack_permanent": "on",
            "ack_authorised": "on",
            "ack_notify": "on",
        })
        er = ErasureRequest.objects.last()

        # PM2 approves
        self.client.login(username="pm2", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/approve/", {
            "program_id": self.prog.pk,
            "review_notes": "Confirmed with client.",
        })
        self.assertEqual(resp.status_code, 302)
        er.refresh_from_db()
        self.assertEqual(er.status, "approved")
        self.assertFalse(ClientFile.objects.filter(pk=self.cf.pk).exists())

    @patch("apps.clients.erasure_views._notify_pms_erasure_request")
    def test_approve_anonymise_via_post(self, mock_notify):
        """Anonymise tier: approval anonymises but keeps client record."""
        pm2 = User.objects.create_user(username="pm2", password="testpass123")
        UserProgramRole.objects.create(user=pm2, program=self.prog, role="program_manager")

        self.client.login(username="pm", password="testpass123")
        self.client.post(f"/clients/{self.cf.pk}/erase/", {
            "erasure_tier": "anonymise",
            "reason_category": "client_requested",
            "request_reason": "Client asked.",
            "ack_permanent": "on",
            "ack_authorised": "on",
            "ack_notify": "on",
        })
        er = ErasureRequest.objects.last()

        # PM2 approves
        self.client.login(username="pm2", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/approve/", {
            "program_id": self.prog.pk,
            "review_notes": "Confirmed.",
        })
        self.assertEqual(resp.status_code, 302)
        er.refresh_from_db()
        self.assertEqual(er.status, "anonymised")
        # Client record should still exist but be anonymised
        cf = ClientFile.objects.get(pk=self.cf.pk)
        self.assertTrue(cf.is_anonymised)

    def test_reject_via_post(self):
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/reject/", {
            "review_notes": "Not appropriate at this time.",
        })
        self.assertEqual(resp.status_code, 302)
        er.refresh_from_db()
        self.assertEqual(er.status, "rejected")
        # Client data should still exist
        self.assertTrue(ClientFile.objects.filter(pk=self.cf.pk).exists())

    def test_reject_requires_notes(self):
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/reject/", {
            "review_notes": "",
        })
        self.assertEqual(resp.status_code, 302)  # Redirects back with error
        er.refresh_from_db()
        self.assertEqual(er.status, "pending")  # Should NOT have been rejected

    @patch("django.core.mail.send_mail")
    def test_rejection_emails_requester(self, mock_send):
        """Rejecting a request sends an email to the requester."""
        self.staff.email = "staff@example.com"
        self.staff.save()
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        self.client.post(f"/erasure/{er.pk}/reject/", {
            "review_notes": "Not appropriate.",
        })
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        self.assertIn("staff@example.com", call_kwargs[1]["recipient_list"])

    def test_cancel_by_requester(self):
        """PM who created the request can cancel it."""
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.pm,
            requested_by_display="PM",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/cancel/")
        self.assertEqual(resp.status_code, 302)
        er.refresh_from_db()
        self.assertEqual(er.status, "cancelled")

    def test_cancel_by_pm(self):
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/cancel/")
        self.assertEqual(resp.status_code, 302)
        er.refresh_from_db()
        self.assertEqual(er.status, "cancelled")

    def test_cancel_by_unrelated_staff_forbidden(self):
        other_staff = User.objects.create_user(username="other_staff", password="testpass123")
        other_prog = Program.objects.create(name="Other Prog", colour_hex="#000000", status="active")
        UserProgramRole.objects.create(user=other_staff, program=other_prog, role="staff")

        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="other_staff", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/cancel/")
        self.assertEqual(resp.status_code, 403)

    def test_approve_non_pending_blocked(self):
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            status="rejected",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/approve/", {
            "program_id": self.prog.pk,
        })
        self.assertEqual(resp.status_code, 302)  # Redirects with error message
        self.assertEqual(ErasureApproval.objects.filter(erasure_request=er).count(), 0)

    def test_requester_cannot_approve_own_request(self):
        # Upgrade staff's existing role to PM for this test
        UserProgramRole.objects.filter(user=self.staff, program=self.prog).update(role="program_manager")
        # Also add another PM so it's not deadlocked
        other_pm = User.objects.create_user(username="other_pm", password="testpass123")
        UserProgramRole.objects.create(user=other_pm, program=self.prog, role="program_manager")

        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post(f"/erasure/{er.pk}/approve/", {
            "program_id": self.prog.pk,
        })
        self.assertEqual(resp.status_code, 302)  # Redirects with error
        self.assertEqual(ErasureApproval.objects.filter(erasure_request=er).count(), 0)

    def test_history_view_accessible(self):
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get("/erasure/history/")
        self.assertEqual(resp.status_code, 200)

    def test_unrelated_pm_cannot_download_receipt(self):
        """PM not involved in the request's programs cannot download the PDF receipt."""
        other_pm = User.objects.create_user(username="other_pm", password="testpass123")
        other_prog = Program.objects.create(name="Other Prog", colour_hex="#000000", status="active")
        UserProgramRole.objects.create(user=other_pm, program=other_prog, role="program_manager")

        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="other_pm", password="testpass123")
        resp = self.client.get(f"/erasure/{er.pk}/receipt/")
        self.assertEqual(resp.status_code, 403)

    @patch("apps.reports.pdf_utils.is_pdf_available", return_value=True)
    @patch("apps.reports.pdf_utils.render_pdf")
    def test_receipt_download_sets_timestamp(self, mock_pdf, mock_avail):
        """First receipt download sets receipt_downloaded_at."""
        from django.http import HttpResponse
        mock_pdf.return_value = HttpResponse(b"fake-pdf", content_type="application/pdf")
        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.staff, requested_by_display="Staff",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.assertIsNone(er.receipt_downloaded_at)
        self.client.login(username="pm", password="testpass123")
        self.client.get(f"/erasure/{er.pk}/receipt/")
        er.refresh_from_db()
        self.assertIsNotNone(er.receipt_downloaded_at)

    def test_detail_warns_if_receipt_not_downloaded(self):
        """Detail page includes warning when receipt hasn't been downloaded."""
        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.staff, requested_by_display="Staff",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get(f"/erasure/{er.pk}/")
        self.assertContains(resp, "PDF receipt has not been downloaded")

    def test_involved_pm_can_download_receipt(self):
        """PM in one of the request's required programs can access the receipt."""
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        # Will redirect or return 200/error depending on PDF availability,
        # but should NOT be 403
        resp = self.client.get(f"/erasure/{er.pk}/receipt/")
        self.assertNotEqual(resp.status_code, 403)

    def test_detail_view_accessible(self):
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get(f"/erasure/{er.pk}/")
        self.assertEqual(resp.status_code, 200)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class DemoDataSeparationTests(TestCase):
    """Test that demo users can only erase demo clients."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.demo_staff = User.objects.create_user(username="demo_staff", password="testpass123", is_demo=True)
        self.real_staff = User.objects.create_user(username="real_staff", password="testpass123", is_demo=False)

        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        UserProgramRole.objects.create(user=self.demo_staff, program=self.prog, role="staff")
        UserProgramRole.objects.create(user=self.real_staff, program=self.prog, role="staff")

        self.demo_client = ClientFile(is_demo=True)
        self.demo_client.first_name = "Demo"
        self.demo_client.last_name = "Client"
        self.demo_client.save()

        self.real_client = ClientFile(is_demo=False)
        self.real_client.first_name = "Real"
        self.real_client.last_name = "Client"
        self.real_client.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_demo_user_cannot_erase_real_client(self):
        self.client.login(username="demo_staff", password="testpass123")
        resp = self.client.get(f"/clients/{self.real_client.pk}/erase/")
        # 403 (middleware blocks — no program overlap) or 404 (queryset filters)
        self.assertIn(resp.status_code, [403, 404])

    def test_real_user_cannot_erase_demo_client(self):
        self.client.login(username="real_staff", password="testpass123")
        resp = self.client.get(f"/clients/{self.demo_client.pk}/erase/")
        self.assertIn(resp.status_code, [403, 404])


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class ContextProcessorTests(TestCase):
    """Test the pending_erasures context processor."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        from django.core.cache import cache
        cache.clear()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.pm_a = User.objects.create_user(username="pm_a", password="testpass123")
        self.pm_b = User.objects.create_user(username="pm_b", password="testpass123")
        self.staff = User.objects.create_user(username="staff", password="testpass123")

        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6", status="active")

        UserProgramRole.objects.create(user=self.pm_a, program=self.prog_a, role="program_manager")
        UserProgramRole.objects.create(user=self.pm_b, program=self.prog_b, role="program_manager")
        UserProgramRole.objects.create(user=self.staff, program=self.prog_a, role="staff")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()

        # Create a pending erasure request for Program A
        self.er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog_a.pk],
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_admin_sees_all_pending(self):
        from django.test import RequestFactory
        from konote.context_processors import pending_erasures

        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.admin

        result = pending_erasures(request)
        self.assertEqual(result.get("pending_erasure_count"), 1)

    def test_pm_a_sees_their_programs(self):
        from django.test import RequestFactory
        from konote.context_processors import pending_erasures

        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.pm_a

        result = pending_erasures(request)
        self.assertEqual(result.get("pending_erasure_count"), 1)

    def test_pm_b_does_not_see_other_programs(self):
        from django.test import RequestFactory
        from konote.context_processors import pending_erasures

        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.pm_b

        result = pending_erasures(request)
        # PM-B has no pending requests in their programs
        self.assertIsNone(result.get("pending_erasure_count"))

    def test_staff_gets_no_count(self):
        from django.test import RequestFactory
        from konote.context_processors import pending_erasures

        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.staff

        result = pending_erasures(request)
        self.assertEqual(result, {})


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class StuckRequestTests(TestCase):
    """Test stuck request detection (no active PM for required program)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        UserProgramRole.objects.create(user=self.staff, program=self.prog, role="staff")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_request_stuck_when_no_pm_exists(self):
        # No PM exists for the required program — deadlocked because no one can approve
        er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="other",
            request_reason="Test",
            programs_required=[self.prog.pk],
        )
        # is_deadlocked returns True — no PM can approve, admin fallback needed
        self.assertTrue(is_deadlocked(er))


# ===========================================================================
# NEW TESTS: Tiered erasure system
# ===========================================================================

@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class TierAvailabilityTests(TestCase):
    """Test get_available_tiers() retention period logic."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_tiers_1_and_2_always_available(self):
        result = get_available_tiers(self.cf)
        self.assertTrue(result["anonymise"]["available"])
        self.assertTrue(result["anonymise_purge"]["available"])

    def test_tier_3_blocked_when_no_retention_set(self):
        result = get_available_tiers(self.cf)
        self.assertFalse(result["full_erasure"]["available"])
        self.assertIn("No retention period", result["full_erasure"]["reason"])

    def test_tier_3_blocked_when_retention_not_expired(self):
        import datetime
        self.cf.retention_expires = datetime.date(2030, 1, 1)
        self.cf.save()
        result = get_available_tiers(self.cf)
        self.assertFalse(result["full_erasure"]["available"])
        self.assertIn("not expired", result["full_erasure"]["reason"])

    def test_tier_3_available_when_retention_expired(self):
        import datetime
        self.cf.retention_expires = datetime.date(2020, 1, 1)
        self.cf.save()
        result = get_available_tiers(self.cf)
        self.assertTrue(result["full_erasure"]["available"])


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class Tier1AnonymiseTests(TestCase):
    """Test Tier 1: PII removed, all records survive."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.pm = User.objects.create_user(username="pm", password="testpass123")
        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")
        UserProgramRole.objects.create(user=self.pm, program=self.prog, role="program_manager")

        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.record_id = "REC-T1"
        self.cf.save()

        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")
        Alert.objects.create(client_file=self.cf, content="Test alert")
        ProgressNote.objects.create(client_file=self.cf, author=self.staff, author_program=self.prog)

        grp = CustomFieldGroup.objects.create(title="Info")
        self.fd = CustomFieldDefinition.objects.create(group=grp, name="Phone", input_type="text", is_sensitive=True)
        cdv = ClientDetailValue.objects.create(client_file=self.cf, field_def=self.fd)
        cdv.set_value("555-1234")
        cdv.save()

        self.er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            client_record_id="REC-T1",
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="client_requested",
            request_reason="Client request.",
            data_summary=build_data_summary(self.cf),
            programs_required=[self.prog.pk],
            erasure_tier="anonymise",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_client_record_survives(self):
        execute_erasure(self.er, "127.0.0.1")
        self.assertTrue(ClientFile.objects.filter(pk=self.cf.pk).exists())

    def test_client_pii_blanked(self):
        execute_erasure(self.er, "127.0.0.1")
        cf = ClientFile.objects.get(pk=self.cf.pk)
        self.assertEqual(cf._first_name_encrypted, b"")
        self.assertEqual(cf._last_name_encrypted, b"")
        self.assertEqual(cf._birth_date_encrypted, b"")

    def test_client_is_anonymised_flag(self):
        execute_erasure(self.er, "127.0.0.1")
        cf = ClientFile.objects.get(pk=self.cf.pk)
        self.assertTrue(cf.is_anonymised)

    def test_client_record_id_replaced(self):
        execute_erasure(self.er, "127.0.0.1")
        cf = ClientFile.objects.get(pk=self.cf.pk)
        self.assertEqual(cf.record_id, self.er.erasure_code)

    def test_related_records_survive(self):
        note_count = ProgressNote.objects.filter(client_file=self.cf).count()
        alert_count = Alert.objects.filter(client_file=self.cf).count()
        enrolment_count = ClientProgramEnrolment.objects.filter(client_file=self.cf).count()

        execute_erasure(self.er, "127.0.0.1")

        self.assertEqual(ProgressNote.objects.filter(client_file=self.cf).count(), note_count)
        self.assertEqual(Alert.objects.filter(client_file=self.cf).count(), alert_count)
        self.assertEqual(ClientProgramEnrolment.objects.filter(client_file=self.cf).count(), enrolment_count)

    def test_sensitive_custom_fields_blanked(self):
        execute_erasure(self.er, "127.0.0.1")
        cdv = ClientDetailValue.objects.get(client_file=self.cf, field_def=self.fd)
        self.assertEqual(cdv._value_encrypted, b"")

    def test_erasure_request_status_anonymised(self):
        execute_erasure(self.er, "127.0.0.1")
        self.er.refresh_from_db()
        self.assertEqual(self.er.status, "anonymised")
        self.assertIsNotNone(self.er.completed_at)

    def test_audit_log_created(self):
        from apps.audit.models import AuditLog
        execute_erasure(self.er, "127.0.0.1")
        logs = AuditLog.objects.using("audit").filter(resource_type="client_erasure")
        self.assertTrue(logs.exists())
        log = logs.first()
        self.assertIn("erasure_code", log.metadata)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class Tier2PurgeTests(TestCase):
    """Test Tier 2: PII removed AND narrative content blanked."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981", status="active")

        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.record_id = "REC-T2"
        self.cf.save()

        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")

        # Create note with content
        self.note = ProgressNote.objects.create(
            client_file=self.cf, author=self.staff, author_program=self.prog,
        )
        self.note._notes_text_encrypted = enc_module.encrypt_field("Session went well.")
        self.note._summary_encrypted = enc_module.encrypt_field("Good progress.")
        self.note.save()

        # Create alert with content
        self.alert = Alert.objects.create(client_file=self.cf, content="Safety concern")

        # Create event with content
        from django.utils import timezone
        self.event = Event.objects.create(
            client_file=self.cf, title="Meeting", description="Discussed goals",
            start_timestamp=timezone.now(),
        )

        self.er = ErasureRequest.objects.create(
            client_file=self.cf,
            client_pk=self.cf.pk,
            client_record_id="REC-T2",
            requested_by=self.staff,
            requested_by_display="Staff",
            reason_category="client_requested",
            request_reason="Client request.",
            data_summary=build_data_summary(self.cf),
            programs_required=[self.prog.pk],
            erasure_tier="anonymise_purge",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_note_content_blanked(self):
        execute_erasure(self.er, "127.0.0.1")
        self.note.refresh_from_db()
        self.assertEqual(self.note._notes_text_encrypted, b"")
        self.assertEqual(self.note._summary_encrypted, b"")

    def test_alert_content_blanked(self):
        execute_erasure(self.er, "127.0.0.1")
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.content, "")

    def test_event_text_blanked(self):
        execute_erasure(self.er, "127.0.0.1")
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "")
        self.assertEqual(self.event.description, "")

    def test_note_record_survives(self):
        execute_erasure(self.er, "127.0.0.1")
        self.assertTrue(ProgressNote.objects.filter(pk=self.note.pk).exists())

    def test_client_anonymised(self):
        execute_erasure(self.er, "127.0.0.1")
        cf = ClientFile.objects.get(pk=self.cf.pk)
        self.assertTrue(cf.is_anonymised)
        self.assertEqual(cf._first_name_encrypted, b"")


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class ErasureCodeTests(TestCase):
    """Test auto-generation of erasure codes."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.prog = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_first_request_gets_001(self):
        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
        )
        from django.utils import timezone
        year = timezone.now().year
        self.assertEqual(er.erasure_code, f"ER-{year}-001")

    def test_sequential_codes(self):
        for i in range(3):
            cf = ClientFile()
            cf.first_name = f"Test{i}"
            cf.last_name = "Client"
            cf.save()
            ErasureRequest.objects.create(
                client_file=cf, client_pk=cf.pk,
                requested_by=self.admin, requested_by_display="Admin",
                reason_category="other", request_reason="Test",
                programs_required=[self.prog.pk],
            )
        codes = list(ErasureRequest.objects.values_list("erasure_code", flat=True).order_by("pk"))
        from django.utils import timezone
        year = timezone.now().year
        self.assertEqual(codes, [f"ER-{year}-001", f"ER-{year}-002", f"ER-{year}-003"])


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class EnhancedDataSummaryTests(TestCase):
    """Test enhanced build_data_summary with programme names and service period."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.prog = Program.objects.create(name="Youth Resilience", colour_hex="#10B981", status="active")
        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")

    def tearDown(self):
        enc_module._fernet = None

    def test_summary_includes_programme_names(self):
        summary = build_data_summary(self.cf)
        self.assertIn("programmes", summary)
        self.assertIn("Youth Resilience", summary["programmes"])

    def test_summary_includes_counts(self):
        summary = build_data_summary(self.cf)
        self.assertEqual(summary["progress_notes"], 0)
        self.assertEqual(summary["enrolments"], 1)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class EmailNotificationWarningTests(TestCase):
    """Test REV-W3: user-visible warning when email notification fails."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.pm = User.objects.create_user(
            username="pm", password="testpass123", email="pm@example.com",
        )
        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981", status="active")
        UserProgramRole.objects.create(user=self.pm, program=self.prog, role="program_manager", status="active")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.record_id = "REC-W3"
        self.cf.save()
        ClientProgramEnrolment.objects.create(client_file=self.cf, program=self.prog, status="enrolled")

    def tearDown(self):
        enc_module._fernet = None

    @patch("django.core.mail.send_mail", side_effect=Exception("SMTP down"))
    def test_notify_pms_returns_false_on_failure(self, mock_send):
        from apps.clients.erasure_views import _notify_pms_erasure_request

        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            client_record_id="REC-W3",
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
        )
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        result = _notify_pms_erasure_request(er, request)
        self.assertFalse(result)

    @patch("django.core.mail.send_mail")
    def test_notify_pms_returns_true_on_success(self, mock_send):
        from apps.clients.erasure_views import _notify_pms_erasure_request

        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            client_record_id="REC-W3",
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
        )
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        result = _notify_pms_erasure_request(er, request)
        self.assertTrue(result)

    @patch("django.core.mail.send_mail", side_effect=Exception("SMTP down"))
    def test_create_view_shows_warning_on_email_failure(self, mock_send):
        self.client.login(username="pm", password="testpass123")
        self.admin.email = "admin@example.com"
        self.admin.save()
        UserProgramRole.objects.create(
            user=self.admin, program=self.prog,
            role="program_manager", status="active",
        )
        resp = self.client.post(
            f"/clients/{self.cf.pk}/erase/",
            {
                "erasure_tier": "anonymise",
                "reason_category": "client_requested",
                "request_reason": "Client asked to be forgotten.",
                "ack_permanent": "on",
                "ack_authorised": "on",
                "ack_notify": "on",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        msgs = [str(m) for m in resp.context["messages"]]
        self.assertTrue(
            any("notify the programme managers manually" in m.lower() for m in msgs),
            f"Expected email failure warning in messages: {msgs}",
        )


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class SQLFilteredVisibilityTests(TestCase):
    """Test REV-W1: SQL-level PM filtering for erasure visibility."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.pm1 = User.objects.create_user(username="pm1", password="testpass123")
        self.pm2 = User.objects.create_user(username="pm2", password="testpass123")

        self.prog_a = Program.objects.create(name="Prog A", colour_hex="#10B981", status="active")
        self.prog_b = Program.objects.create(name="Prog B", colour_hex="#3B82F6", status="active")

        UserProgramRole.objects.create(user=self.pm1, program=self.prog_a, role="program_manager", status="active")
        UserProgramRole.objects.create(user=self.pm2, program=self.prog_b, role="program_manager", status="active")

        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()

        # Request requiring prog_a only
        self.er_a = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test A",
            programs_required=[self.prog_a.pk],
        )
        # Request requiring prog_b only
        self.er_b = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test B",
            programs_required=[self.prog_b.pk],
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_pm_sees_only_their_program_requests(self):
        from apps.clients.erasure_views import _get_visible_requests
        visible = _get_visible_requests(self.pm1)
        pks = list(visible.values_list("pk", flat=True))
        self.assertIn(self.er_a.pk, pks)
        self.assertNotIn(self.er_b.pk, pks)

    def test_admin_sees_all_requests(self):
        from apps.clients.erasure_views import _get_visible_requests
        visible = _get_visible_requests(self.admin)
        pks = list(visible.values_list("pk", flat=True))
        self.assertIn(self.er_a.pk, pks)
        self.assertIn(self.er_b.pk, pks)

    def test_pm_with_no_programs_sees_nothing(self):
        from apps.clients.erasure_views import _get_visible_requests
        staff = User.objects.create_user(username="staff", password="testpass123")
        visible = _get_visible_requests(staff)
        self.assertEqual(visible.count(), 0)


@override_settings(FIELD_ENCRYPTION_KEY="ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=")
class PIPEDAAgingTests(TestCase):
    """Test REV-PIPEDA1: 30-day aging indicator for pending erasure requests."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.prog = Program.objects.create(name="Prog A", colour_hex="#10B981", status="active")
        UserProgramRole.objects.create(
            user=self.admin, program=self.prog,
            role="program_manager", status="active",
        )
        self.cf = ClientFile()
        self.cf.first_name = "Test"
        self.cf.last_name = "Client"
        self.cf.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_pending_list_shows_days_pending(self):
        """Pending list view includes days_pending on each request."""
        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/erasure/")
        self.assertEqual(resp.status_code, 200)
        pending = list(resp.context["pending_requests"])
        self.assertTrue(len(pending) > 0)
        self.assertTrue(hasattr(pending[0], "days_pending"))
        self.assertEqual(pending[0].days_pending, 0)

    def test_overdue_request_shows_days(self):
        """A request older than 30 days gets correct days_pending value."""
        from datetime import timedelta
        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Old request",
            programs_required=[self.prog.pk],
        )
        # Backdate the request
        from django.utils import timezone as tz
        ErasureRequest.objects.filter(pk=er.pk).update(
            requested_at=tz.now() - timedelta(days=35),
        )

        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/erasure/")
        pending = list(resp.context["pending_requests"])
        self.assertEqual(pending[0].days_pending, 35)

    def test_detail_view_includes_days_pending(self):
        """Detail view passes days_pending for pending requests."""
        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/erasure/{er.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["days_pending"])

    def test_detail_view_no_aging_for_completed(self):
        """Completed requests do not show days_pending."""
        er = ErasureRequest.objects.create(
            client_file=self.cf, client_pk=self.cf.pk,
            requested_by=self.admin, requested_by_display="Admin",
            reason_category="other", request_reason="Test",
            programs_required=[self.prog.pk],
            status="anonymised",
        )
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get(f"/erasure/{er.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["days_pending"])
