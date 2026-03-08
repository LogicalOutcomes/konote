"""Tests for bulk transfer and discharge wizard views (BULK1)."""
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.constants import ROLE_PROGRAM_MANAGER, ROLE_RECEPTIONIST, ROLE_STAFF
from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BulkTransferWizardTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.pm = User.objects.create_user(username="pm", password="testpass123")
        self.staff = User.objects.create_user(username="staff", password="testpass123")
        self.receptionist = User.objects.create_user(username="receptionist", password="testpass123")
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#3B82F6")
        UserProgramRole.objects.create(user=self.pm, program=self.prog_a, role=ROLE_PROGRAM_MANAGER)
        UserProgramRole.objects.create(user=self.pm, program=self.prog_b, role=ROLE_PROGRAM_MANAGER)
        UserProgramRole.objects.create(user=self.staff, program=self.prog_a, role=ROLE_STAFF)
        UserProgramRole.objects.create(user=self.staff, program=self.prog_b, role=ROLE_STAFF)
        UserProgramRole.objects.create(user=self.receptionist, program=self.prog_a, role=ROLE_RECEPTIONIST)

    def _create_client(self, first="Jane", last="Doe", programs=None):
        cf = ClientFile()
        cf.first_name = first
        cf.last_name = last
        cf.status = "active"
        cf.save()
        if programs:
            for p in programs:
                ClientProgramEnrolment.objects.create(client_file=cf, program=p)
        return cf

    def test_wizard_page_loads_for_pm(self):
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get("/participants/manage/bulk-transfer/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bulk Transfer")

    def test_wizard_page_loads_for_staff(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/participants/manage/bulk-transfer/")
        self.assertEqual(resp.status_code, 200)

    def test_receptionist_denied(self):
        self.client.login(username="receptionist", password="testpass123")
        resp = self.client.get("/participants/manage/bulk-transfer/")
        self.assertEqual(resp.status_code, 403)

    def test_filter_shows_participants(self):
        self._create_client("Alice", "Smith", [self.prog_a])
        self._create_client("Bob", "Jones", [self.prog_b])
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get("/participants/manage/bulk-transfer/", {
            "source_program": self.prog_a.pk,
            "status_filter": "active",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertNotContains(resp, "Bob")

    def test_confirm_step_shows_selected(self):
        c1 = self._create_client("Alice", "Smith", [self.prog_a])
        c2 = self._create_client("Bob", "Jones", [self.prog_a])
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post("/participants/manage/bulk-transfer/", {
            "confirm": "1",
            "selected_clients": [str(c1.pk), str(c2.pk)],
            "source_program_id": str(self.prog_a.pk),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice")
        self.assertContains(resp, "Bob")
        self.assertContains(resp, "Confirm Transfer")

    def test_execute_transfers_participants(self):
        c1 = self._create_client("Alice", "Smith", [self.prog_a])
        c2 = self._create_client("Bob", "Jones", [self.prog_a])
        self.client.login(username="pm", password="testpass123")

        # Step 2: confirm (stores in session)
        self.client.post("/participants/manage/bulk-transfer/", {
            "confirm": "1",
            "selected_clients": [str(c1.pk), str(c2.pk)],
            "source_program_id": str(self.prog_a.pk),
        })

        # Step 3: execute
        resp = self.client.post("/participants/manage/bulk-transfer/", {
            "execute": "1",
            "client_ids": f"{c1.pk},{c2.pk}",
            "destination_program": str(self.prog_b.pk),
            "transfer_reason": "Cohort ended",
        })
        self.assertEqual(resp.status_code, 302)  # redirect to client list

        # Verify: both enrolled in prog_b
        self.assertTrue(
            ClientProgramEnrolment.objects.filter(
                client_file=c1, program=self.prog_b, status="active"
            ).exists()
        )
        self.assertTrue(
            ClientProgramEnrolment.objects.filter(
                client_file=c2, program=self.prog_b, status="active"
            ).exists()
        )

        # Verify: both unenrolled from prog_a
        self.assertFalse(
            ClientProgramEnrolment.objects.filter(
                client_file=c1, program=self.prog_a, status="active"
            ).exists()
        )

    def test_no_selection_redirects(self):
        self.client.login(username="pm", password="testpass123")
        resp = self.client.post("/participants/manage/bulk-transfer/", {
            "confirm": "1",
            "selected_clients": [],
        })
        self.assertEqual(resp.status_code, 302)

    def test_audit_log_created_per_participant(self):
        from apps.audit.models import AuditLog
        c1 = self._create_client("Alice", "Smith", [self.prog_a])
        c2 = self._create_client("Bob", "Jones", [self.prog_a])
        self.client.login(username="pm", password="testpass123")

        self.client.post("/participants/manage/bulk-transfer/", {
            "confirm": "1",
            "selected_clients": [str(c1.pk), str(c2.pk)],
            "source_program_id": str(self.prog_a.pk),
        })
        self.client.post("/participants/manage/bulk-transfer/", {
            "execute": "1",
            "client_ids": f"{c1.pk},{c2.pk}",
            "destination_program": str(self.prog_b.pk),
        })

        # Should have individual audit entries for each participant
        logs = AuditLog.objects.using("audit").filter(
            metadata__bulk_transfer=True
        )
        self.assertEqual(logs.count(), 2)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BulkDischargeWizardTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.pm = User.objects.create_user(username="pm", password="testpass123")
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.pm, program=self.prog_a, role=ROLE_PROGRAM_MANAGER)

    def _create_client(self, first="Jane", last="Doe", programs=None):
        cf = ClientFile()
        cf.first_name = first
        cf.last_name = last
        cf.status = "active"
        cf.save()
        if programs:
            for p in programs:
                ClientProgramEnrolment.objects.create(client_file=cf, program=p)
        return cf

    def test_wizard_page_loads(self):
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get("/participants/manage/bulk-discharge/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bulk Discharge")

    def test_filter_requires_program(self):
        self.client.login(username="pm", password="testpass123")
        resp = self.client.get("/participants/manage/bulk-discharge/", {
            "status_filter": "active",
        })
        self.assertEqual(resp.status_code, 200)
        # Should not show participant table without a program selected
        self.assertNotContains(resp, "participant found")

    def test_execute_discharges_participants(self):
        c1 = self._create_client("Alice", "Smith", [self.prog_a])
        c2 = self._create_client("Bob", "Jones", [self.prog_a])
        self.client.login(username="pm", password="testpass123")

        # Step 2: confirm
        self.client.post("/participants/manage/bulk-discharge/", {
            "confirm": "1",
            "selected_clients": [str(c1.pk), str(c2.pk)],
            "source_program_id": str(self.prog_a.pk),
        })

        # Step 3: execute
        resp = self.client.post("/participants/manage/bulk-discharge/", {
            "execute": "1",
            "client_ids": f"{c1.pk},{c2.pk}",
            "source_program": str(self.prog_a.pk),
            "end_reason": "program_closure",
            "status_reason": "Program ended March 2026",
        })
        self.assertEqual(resp.status_code, 302)

        # Verify: both discharged from prog_a
        self.assertFalse(
            ClientProgramEnrolment.objects.filter(
                client_file=c1, program=self.prog_a, status="active"
            ).exists()
        )
        ep = ClientProgramEnrolment.objects.get(client_file=c1, program=self.prog_a)
        self.assertEqual(ep.status, "finished")
        self.assertEqual(ep.end_reason, "program_closure")

    def test_audit_log_created_per_participant(self):
        from apps.audit.models import AuditLog
        c1 = self._create_client("Alice", "Smith", [self.prog_a])
        c2 = self._create_client("Bob", "Jones", [self.prog_a])
        self.client.login(username="pm", password="testpass123")

        self.client.post("/participants/manage/bulk-discharge/", {
            "confirm": "1",
            "selected_clients": [str(c1.pk), str(c2.pk)],
            "source_program_id": str(self.prog_a.pk),
        })
        self.client.post("/participants/manage/bulk-discharge/", {
            "execute": "1",
            "client_ids": f"{c1.pk},{c2.pk}",
            "source_program": str(self.prog_a.pk),
            "end_reason": "cohort_ended",
        })

        logs = AuditLog.objects.using("audit").filter(
            metadata__bulk_discharge=True
        )
        self.assertEqual(logs.count(), 2)
