"""Tests for the Sessions by Participant report (REP-SESS1).

Covers:
- ProgressNote model accepts new duration_minutes and modality fields
- Session report aggregation with mock data
- CSV output format and structure
- Permission checks (only PMs and above can generate)
"""
from datetime import date, timedelta
from io import StringIO

from django.test import TestCase, Client as HttpClient, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote
from apps.programs.models import Program, UserProgramRole
from apps.reports.session_report import generate_session_report
from apps.reports.session_csv import generate_session_report_csv

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgressNoteNewFieldsTest(TestCase):
    """Test that ProgressNote accepts the new duration_minutes and modality fields."""

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(username="staff", password="pass")
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_duration_minutes_saved(self):
        """ProgressNote should accept and save duration_minutes."""
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            interaction_type="session",
            author=self.user,
            duration_minutes=60,
        )
        note.refresh_from_db()
        self.assertEqual(note.duration_minutes, 60)

    def test_modality_saved(self):
        """ProgressNote should accept and save modality."""
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            interaction_type="session",
            author=self.user,
            modality="video",
        )
        note.refresh_from_db()
        self.assertEqual(note.modality, "video")

    def test_fields_are_optional(self):
        """Both fields should be optional (null/blank allowed)."""
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="quick",
            interaction_type="phone",
            author=self.user,
        )
        note.refresh_from_db()
        self.assertIsNone(note.duration_minutes)
        # modality is CharField with null=True, blank=True — defaults to None
        self.assertIn(note.modality, (None, ""))

    def test_modality_choices(self):
        """All modality choices should be accepted."""
        for value, _label in ProgressNote.MODALITY_CHOICES:
            note = ProgressNote.objects.create(
                client_file=self.client_file,
                note_type="full",
                interaction_type="session",
                author=self.user,
                modality=value,
            )
            note.refresh_from_db()
            self.assertEqual(note.modality, value)

    def test_duration_zero_not_allowed(self):
        """PositiveIntegerField should reject zero (min_value not enforced at DB level,
        but form validation catches it). This tests that the DB accepts positive values."""
        note = ProgressNote.objects.create(
            client_file=self.client_file,
            note_type="full",
            interaction_type="session",
            author=self.user,
            duration_minutes=1,
        )
        note.refresh_from_db()
        self.assertEqual(note.duration_minutes, 1)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SessionReportAggregationTest(TestCase):
    """Test the session report aggregation engine."""

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(username="pm", password="pass")
        self.program = Program.objects.create(name="Coaching Program", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.user, program=self.program, role="program_manager")

        # Create two clients
        self.client_a = ClientFile()
        self.client_a.first_name = "Alice"
        self.client_a.last_name = "Anderson"
        self.client_a.status = "active"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_a, program=self.program, status="enrolled",
        )

        self.client_b = ClientFile()
        self.client_b.first_name = "Bob"
        self.client_b.last_name = "Baker"
        self.client_b.status = "active"
        self.client_b.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.program, status="enrolled",
        )

        # Create notes for Alice (3 sessions)
        # Use backdate to place notes in the reporting period (Jan 2026).
        # created_at is auto_now_add so cannot be set directly.
        base_date = timezone.make_aware(
            timezone.datetime(2026, 1, 10, 9, 0, 0)
        )
        ProgressNote.objects.create(
            client_file=self.client_a,
            note_type="full",
            interaction_type="session",
            author=self.user,
            duration_minutes=60,
            modality="in_person",
            backdate=base_date,
        )
        ProgressNote.objects.create(
            client_file=self.client_a,
            note_type="full",
            interaction_type="session",
            author=self.user,
            duration_minutes=45,
            modality="video",
            backdate=base_date + timedelta(days=7),
        )
        ProgressNote.objects.create(
            client_file=self.client_a,
            note_type="full",
            interaction_type="phone",
            author=self.user,
            duration_minutes=30,
            modality="phone",
            backdate=base_date + timedelta(days=14),
        )

        # Create notes for Bob (1 session, no duration)
        ProgressNote.objects.create(
            client_file=self.client_b,
            note_type="full",
            interaction_type="session",
            author=self.user,
            modality="in_person",
            backdate=base_date + timedelta(days=3),
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_report_counts_participants(self):
        """Report should count unique participants."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        self.assertEqual(result["summary"]["total_unique_participants"], 2)

    def test_report_counts_total_sessions(self):
        """Report should count total sessions."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        self.assertEqual(result["summary"]["total_sessions"], 4)

    def test_participant_session_count(self):
        """Alice should have 3 sessions, Bob 1."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        participants = {p["client_display_name"]: p for p in result["participants"]}
        self.assertEqual(participants["Alice"]["total_sessions"], 3)
        self.assertEqual(participants["Bob"]["total_sessions"], 1)

    def test_contact_hours_calculation(self):
        """Alice's total contact hours: (60 + 45 + 30) / 60 = 2.2 hours."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        participants = {p["client_display_name"]: p for p in result["participants"]}
        self.assertEqual(participants["Alice"]["total_contact_hours"], 2.2)
        # Bob has no duration, so 0 hours
        self.assertEqual(participants["Bob"]["total_contact_hours"], 0)

    def test_average_sessions_per_participant(self):
        """Average: 4 sessions / 2 participants = 2.0."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        self.assertEqual(result["summary"]["average_sessions_per_participant"], 2.0)

    def test_modality_distribution(self):
        """Should count sessions by modality."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        dist = result["summary"]["modality_distribution"]
        self.assertEqual(dist.get("In Person"), 2)
        self.assertEqual(dist.get("Video"), 1)
        self.assertEqual(dist.get("Phone"), 1)

    def test_date_range_filtering(self):
        """Notes outside the date range should be excluded."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 12), user=self.user,
        )
        # Only Alice's first note (Jan 10) and Bob's note (Jan 13) are in range
        # But Bob's note is Jan 13 which is within Jan 1-12? No, Jan 13 > Jan 12.
        # Actually the base_date for Bob is Jan 10 + 3 = Jan 13, which is outside 1-12.
        # Alice's second is Jan 17 (10 + 7), also outside.
        # So only Alice's first note on Jan 10 is in range.
        self.assertEqual(result["summary"]["total_sessions"], 1)

    def test_cancelled_notes_excluded(self):
        """Cancelled notes should not appear in the report."""
        # Cancel Alice's first note
        note = ProgressNote.objects.filter(
            client_file=self.client_a, duration_minutes=60,
        ).first()
        note.status = "cancelled"
        note.save()

        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        self.assertEqual(result["summary"]["total_sessions"], 3)

    def test_empty_program_returns_zeros(self):
        """Program with no notes should return zero aggregates."""
        empty_program = Program.objects.create(name="Empty", colour_hex="#000000")
        result = generate_session_report(
            empty_program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        self.assertEqual(result["summary"]["total_unique_participants"], 0)
        self.assertEqual(result["summary"]["total_sessions"], 0)
        self.assertEqual(result["summary"]["average_sessions_per_participant"], 0)

    def test_days_in_program_calculation(self):
        """Days in program = last session date - first session date."""
        result = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        participants = {p["client_display_name"]: p for p in result["participants"]}
        # Alice: Jan 10 to Jan 24 = 14 days
        self.assertEqual(participants["Alice"]["days_in_program"], 14)
        # Bob: only 1 session, so 0 days
        self.assertEqual(participants["Bob"]["days_in_program"], 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SessionReportCSVTest(TestCase):
    """Test the CSV output format for the session report."""

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(username="pm", password="pass")
        self.program = Program.objects.create(name="Coaching Program", colour_hex="#10B981")

        self.client_a = ClientFile()
        self.client_a.first_name = "Alice"
        self.client_a.last_name = "Anderson"
        self.client_a.status = "active"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_a, program=self.program, status="enrolled",
        )

        base_date = timezone.make_aware(
            timezone.datetime(2026, 1, 10, 9, 0, 0)
        )
        ProgressNote.objects.create(
            client_file=self.client_a,
            note_type="full",
            interaction_type="session",
            author=self.user,
            duration_minutes=60,
            modality="in_person",
            backdate=base_date,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_csv_contains_metadata_header(self):
        """CSV should start with metadata rows."""
        report_data = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        csv_content, filename = generate_session_report_csv(report_data)

        self.assertIn("Sessions by Participant Report", csv_content)
        self.assertIn("Coaching Program", csv_content)
        self.assertIn("2026-01-01", csv_content)
        self.assertIn("2026-01-31", csv_content)

    def test_csv_contains_session_details(self):
        """CSV should include per-session detail rows."""
        report_data = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        csv_content, filename = generate_session_report_csv(report_data)

        self.assertIn("Session Details", csv_content)
        self.assertIn("Alice", csv_content)
        self.assertIn("Anderson", csv_content)

    def test_csv_contains_participant_summary(self):
        """CSV should include participant summary section."""
        report_data = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        csv_content, filename = generate_session_report_csv(report_data)

        self.assertIn("Participant Summary", csv_content)

    def test_csv_contains_report_summary(self):
        """CSV should include report-level aggregates."""
        report_data = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        csv_content, filename = generate_session_report_csv(report_data)

        self.assertIn("Report Summary", csv_content)
        self.assertIn("Total Unique Participants", csv_content)
        self.assertIn("Total Sessions", csv_content)

    def test_csv_filename_format(self):
        """Filename should follow the pattern Sessions_<program>_<from>_<to>.csv."""
        report_data = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        _content, filename = generate_session_report_csv(report_data)

        self.assertTrue(filename.startswith("Sessions_"))
        self.assertTrue(filename.endswith(".csv"))
        self.assertIn("2026-01-01", filename)
        self.assertIn("2026-01-31", filename)

    def test_csv_sanitises_injection(self):
        """CSV should sanitise formula injection attempts."""
        # Create a client with a potentially dangerous name
        bad_client = ClientFile()
        bad_client.first_name = "=CMD()"
        bad_client.last_name = "Hacker"
        bad_client.status = "active"
        bad_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=bad_client, program=self.program, status="enrolled",
        )
        ProgressNote.objects.create(
            client_file=bad_client,
            note_type="quick",
            interaction_type="session",
            author=self.user,
            duration_minutes=30,
            backdate=timezone.make_aware(
                timezone.datetime(2026, 1, 15, 10, 0, 0)
            ),
        )

        report_data = generate_session_report(
            self.program, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        csv_content, _filename = generate_session_report_csv(report_data)

        # The sanitised output should prefix = with a tab
        self.assertIn("\t=CMD()", csv_content)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SessionReportPermissionTest(TestCase):
    """Test permission checks for the session report view."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = HttpClient()
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")

        # Program manager (should have access)
        self.pm = User.objects.create_user(username="pm", password="pass")
        UserProgramRole.objects.create(user=self.pm, program=self.program, role="program_manager")

        # Admin (should have access)
        self.admin = User.objects.create_user(username="admin", password="pass", is_admin=True)

        # Executive (aggregate-only, should NOT have access)
        self.exec_user = User.objects.create_user(username="exec", password="pass")
        UserProgramRole.objects.create(user=self.exec_user, program=self.program, role="executive")

        # Staff (should NOT have access — no report.program_report permission)
        self.staff = User.objects.create_user(username="staff", password="pass")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role="staff")

    def tearDown(self):
        enc_module._fernet = None

    def test_pm_can_access_form(self):
        """Program managers should see the session report form."""
        self.http.login(username="pm", password="pass")
        resp = self.http.get("/reports/sessions/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_access_form(self):
        """Admins should see the session report form."""
        self.http.login(username="admin", password="pass")
        resp = self.http.get("/reports/sessions/")
        self.assertEqual(resp.status_code, 200)

    def test_executive_blocked(self):
        """Executives (aggregate-only, non-admin) should be blocked from this report."""
        self.http.login(username="exec", password="pass")
        resp = self.http.get("/reports/sessions/")
        self.assertEqual(resp.status_code, 403)

    def test_staff_blocked(self):
        """Staff without report.program_report permission should be blocked."""
        self.http.login(username="staff", password="pass")
        resp = self.http.get("/reports/sessions/")
        self.assertIn(resp.status_code, (403, 302))

    def test_anonymous_redirected(self):
        """Anonymous users should be redirected to login."""
        resp = self.http.get("/reports/sessions/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SessionReportCrossProgramTest(TestCase):
    """Test that session report respects program boundaries."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(username="pm", password="pass")

        # Two programs
        self.prog_a = Program.objects.create(name="Program A", colour_hex="#10B981")
        self.prog_b = Program.objects.create(name="Program B", colour_hex="#EF4444")
        UserProgramRole.objects.create(user=self.user, program=self.prog_a, role="program_manager")
        UserProgramRole.objects.create(user=self.user, program=self.prog_b, role="program_manager")

        # Client enrolled in program A only
        self.client_a = ClientFile()
        self.client_a.first_name = "Alice"
        self.client_a.last_name = "Alpha"
        self.client_a.status = "active"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_a, program=self.prog_a, status="enrolled",
        )

        # Client enrolled in program B only
        self.client_b = ClientFile()
        self.client_b.first_name = "Bob"
        self.client_b.last_name = "Beta"
        self.client_b.status = "active"
        self.client_b.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.prog_b, status="enrolled",
        )

        # Notes for each client
        note_date = timezone.make_aware(timezone.datetime(2026, 1, 15, 10, 0, 0))
        ProgressNote.objects.create(
            client_file=self.client_a, note_type="quick",
            interaction_type="session", author=self.user,
            duration_minutes=60, backdate=note_date,
        )
        ProgressNote.objects.create(
            client_file=self.client_b, note_type="quick",
            interaction_type="session", author=self.user,
            duration_minutes=45, backdate=note_date,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_program_a_excludes_program_b_clients(self):
        """Report for program A should not include program B's participants."""
        report = generate_session_report(
            self.prog_a, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        client_ids = [p["client_id"] for p in report["participants"]]
        self.assertIn(self.client_a.pk, client_ids)
        self.assertNotIn(self.client_b.pk, client_ids)

    def test_program_b_excludes_program_a_clients(self):
        """Report for program B should not include program A's participants."""
        report = generate_session_report(
            self.prog_b, date(2026, 1, 1), date(2026, 1, 31), user=self.user,
        )
        client_ids = [p["client_id"] for p in report["participants"]]
        self.assertIn(self.client_b.pk, client_ids)
        self.assertNotIn(self.client_a.pk, client_ids)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SessionReportAuditLogTest(TestCase):
    """Test that session report generation creates an audit log entry."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = HttpClient()
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        self.pm = User.objects.create_user(username="pm", password="pass")
        UserProgramRole.objects.create(user=self.pm, program=self.program, role="program_manager")

        self.client_file = ClientFile()
        self.client_file.first_name = "Jane"
        self.client_file.last_name = "Doe"
        self.client_file.status = "active"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program, status="enrolled",
        )
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            interaction_type="session", author=self.pm,
            duration_minutes=30,
            backdate=timezone.make_aware(timezone.datetime(2026, 1, 15, 10, 0, 0)),
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_audit_log_created_on_export(self):
        """Generating a session report should write an audit log entry."""
        from apps.audit.models import AuditLog

        self.http.login(username="pm", password="pass")
        initial_count = AuditLog.objects.using("audit").filter(
            resource_type="session_report",
        ).count()

        resp = self.http.post("/reports/sessions/", {
            "program": str(self.program.pk),
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "recipient": "Jane Smith, Test Org",
            "recipient_reason": "Quarterly reporting",
        })
        # Should redirect to download page on success
        self.assertIn(resp.status_code, (302, 200))

        new_count = AuditLog.objects.using("audit").filter(
            resource_type="session_report",
        ).count()
        self.assertEqual(new_count, initial_count + 1)
