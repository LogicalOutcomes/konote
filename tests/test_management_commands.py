"""Smoke tests for management commands not covered by other test files.

Already tested elsewhere (skip here):
  - rotate_encryption_key  (tests/test_rotate_encryption_key.py)
  - cleanup_expired_exports (tests/test_secure_export.py)
"""
import io
import os
import unittest

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import TestCase, override_settings

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# =========================================================================
# Seed Commands
# =========================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SeedEventTypesTest(TestCase):
    """Tests for the seed_event_types command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_creates_event_types(self):
        """Running seed_event_types creates the default event types."""
        from apps.events.models import EventType

        out = io.StringIO()
        call_command("seed_event_types", stdout=out)

        self.assertTrue(EventType.objects.filter(name="Intake").exists())
        self.assertTrue(EventType.objects.filter(name="Discharge").exists())
        self.assertTrue(EventType.objects.filter(name="Crisis").exists())
        self.assertTrue(EventType.objects.filter(name="Referral").exists())
        self.assertTrue(EventType.objects.filter(name="Follow-up").exists())
        self.assertEqual(EventType.objects.count(), 5)

    def test_idempotent(self):
        """Running seed_event_types twice does not duplicate records."""
        from apps.events.models import EventType

        out = io.StringIO()
        call_command("seed_event_types", stdout=out)
        call_command("seed_event_types", stdout=out)

        self.assertEqual(EventType.objects.count(), 5)
        self.assertIn("Already exists", out.getvalue())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SeedNoteTemplatesTest(TestCase):
    """Tests for the seed_note_templates command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_creates_templates(self):
        """Running seed_note_templates creates the default templates."""
        from apps.notes.models import ProgressNoteTemplate, ProgressNoteTemplateSection

        out = io.StringIO()
        call_command("seed_note_templates", stdout=out)

        self.assertTrue(
            ProgressNoteTemplate.objects.filter(name="Standard session").exists()
        )
        self.assertTrue(
            ProgressNoteTemplate.objects.filter(name="Brief check-in").exists()
        )
        self.assertEqual(ProgressNoteTemplate.objects.count(), 6)
        # Each template has sections
        self.assertGreater(ProgressNoteTemplateSection.objects.count(), 0)

    def test_idempotent(self):
        """Running seed_note_templates twice does not duplicate records."""
        from apps.notes.models import ProgressNoteTemplate

        out = io.StringIO()
        call_command("seed_note_templates", stdout=out)
        call_command("seed_note_templates", stdout=out)

        self.assertEqual(ProgressNoteTemplate.objects.count(), 6)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SeedIntakeFieldsTest(TestCase):
    """Tests for the seed_intake_fields command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_creates_field_groups_and_definitions(self):
        """Running seed_intake_fields creates groups and field definitions."""
        from apps.clients.models import CustomFieldDefinition, CustomFieldGroup

        out = io.StringIO()
        call_command("seed_intake_fields", stdout=out)

        # Should create multiple groups
        self.assertGreater(CustomFieldGroup.objects.count(), 0)
        self.assertTrue(
            CustomFieldGroup.objects.filter(title="Contact Information").exists()
        )
        self.assertTrue(
            CustomFieldGroup.objects.filter(title="Emergency Contact").exists()
        )

        # Should create field definitions
        self.assertGreater(CustomFieldDefinition.objects.count(), 0)
        self.assertTrue(
            CustomFieldDefinition.objects.filter(name="Primary Phone").exists()
        )

    def test_idempotent(self):
        """Running seed_intake_fields twice does not duplicate records."""
        from apps.clients.models import CustomFieldDefinition, CustomFieldGroup

        out = io.StringIO()
        call_command("seed_intake_fields", stdout=out)
        group_count = CustomFieldGroup.objects.count()
        field_count = CustomFieldDefinition.objects.count()

        call_command("seed_intake_fields", stdout=out)
        self.assertEqual(CustomFieldGroup.objects.count(), group_count)
        self.assertEqual(CustomFieldDefinition.objects.count(), field_count)

    def test_youth_groups_archived_by_default(self):
        """Youth/recreation field groups are archived by default."""
        from apps.clients.models import CustomFieldGroup

        out = io.StringIO()
        call_command("seed_intake_fields", stdout=out)

        parent_group = CustomFieldGroup.objects.filter(
            title="Parent/Guardian Information"
        ).first()
        self.assertIsNotNone(parent_group)
        self.assertEqual(parent_group.status, "archived")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=False)
class SeedOrchestratorTest(TestCase):
    """Tests for the seed (orchestrator) command with DEMO_MODE=False."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_seed_creates_metrics_and_toggles(self):
        """Running seed creates metrics, feature toggles, and instance settings."""
        from apps.admin_settings.models import FeatureToggle, InstanceSetting
        from apps.plans.models import MetricDefinition

        out = io.StringIO()
        call_command("seed", stdout=out)

        # Metrics from the JSON seed file
        self.assertGreater(MetricDefinition.objects.count(), 0)

        # Feature toggles
        self.assertGreater(FeatureToggle.objects.count(), 0)
        self.assertTrue(
            FeatureToggle.objects.filter(feature_key="programs").exists()
        )

        # Instance settings
        self.assertGreater(InstanceSetting.objects.count(), 0)

        self.assertIn("Seed complete", out.getvalue())

    def test_seed_idempotent(self):
        """Running seed twice does not duplicate records."""
        from apps.plans.models import MetricDefinition

        out = io.StringIO()
        call_command("seed", stdout=out)
        metric_count = MetricDefinition.objects.count()

        call_command("seed", stdout=out)
        self.assertEqual(MetricDefinition.objects.count(), metric_count)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=True)
class SeedDemoDataTest(TestCase):
    """Tests for the seed_demo_data command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_skips_when_demo_mode_off(self):
        """seed_demo_data skips when DEMO_MODE is False."""
        out = io.StringIO()
        with self.settings(DEMO_MODE=False):
            call_command("seed_demo_data", stdout=out)
        self.assertIn("DEMO_MODE is not enabled", out.getvalue())

    def test_smoke_with_demo_mode(self):
        """seed_demo_data runs without crashing when DEMO_MODE is True.

        We run the full seed first to create the prerequisite data
        (metrics, programs, demo users), then seed_demo_data creates
        plans, notes, and events.
        """
        out = io.StringIO()
        # The full seed creates programs, users, and calls seed_demo_data
        call_command("seed", stdout=out)

        # Verify demo clients were created
        from apps.clients.models import ClientFile

        demo_clients = ClientFile.objects.filter(
            record_id__startswith="DEMO-", is_demo=True
        )
        self.assertGreater(demo_clients.count(), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, DEMO_MODE=False)
class UpdateDemoClientFieldsTest(TestCase):
    """Tests for the update_demo_client_fields command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_skips_when_demo_mode_off(self):
        """update_demo_client_fields skips when DEMO_MODE is False."""
        out = io.StringIO()
        call_command("update_demo_client_fields", stdout=out)
        self.assertIn("DEMO_MODE is not enabled", out.getvalue())


# =========================================================================
# Security Commands
# =========================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SecurityAuditTest(TestCase):
    """Tests for the security_audit command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_smoke_single_category(self):
        """security_audit runs with --category=ENC without crashing.

        The command calls exit() on failures, so we catch SystemExit.
        It may exit 0 (pass) or 1 (fail) depending on test environment
        settings -- either is fine for a smoke test.
        """
        out = io.StringIO()
        try:
            call_command("security_audit", category="ENC", stdout=out)
        except SystemExit:
            pass  # Expected -- command uses exit() for pass/fail
        output = out.getvalue()
        self.assertIn("Encryption Checks", output)

    def test_json_output(self):
        """security_audit --json produces valid JSON output."""
        import json

        out = io.StringIO()
        try:
            call_command("security_audit", category="ENC", json=True, stdout=out)
        except SystemExit:
            pass
        output = out.getvalue()
        # Should be valid JSON
        parsed = json.loads(output)
        self.assertIn("results", parsed)
        self.assertIn("summary", parsed)

    def test_cfg_category(self):
        """security_audit runs CFG checks without crashing."""
        out = io.StringIO()
        try:
            call_command("security_audit", category="CFG", stdout=out)
        except SystemExit:
            pass
        self.assertIn("Configuration Checks", out.getvalue())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StartupCheckTest(TestCase):
    """Tests for the startup_check command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_demo_mode_exits_zero(self):
        """startup_check with KONOTE_MODE=demo always exits 0."""
        out = io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"KONOTE_MODE": "demo"}):
            with self.assertRaises(SystemExit) as ctx:
                call_command("startup_check", stdout=out)
            self.assertEqual(ctx.exception.code, 0)
        self.assertIn("demo", out.getvalue().lower())

    def test_invalid_mode_exits_one(self):
        """startup_check with an invalid mode exits 1."""
        err = io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"KONOTE_MODE": "invalid"}):
            with self.assertRaises(SystemExit) as ctx:
                call_command("startup_check", stderr=err)
            self.assertEqual(ctx.exception.code, 1)


# =========================================================================
# Translation Commands
# =========================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CheckTranslationsTest(TestCase):
    """Tests for the check_translations command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_smoke(self):
        """check_translations runs without unexpected errors.

        The command calls sys.exit() at the end (0 for pass, 1 for fail).
        Either is acceptable in a smoke test.
        """
        out = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            call_command("check_translations", stdout=out)
        # Should exit 0 or 1 (not crash with an unhandled exception)
        self.assertIn(ctx.exception.code, (0, 1))
        self.assertIn("Translation Check", out.getvalue())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TranslateStringsTest(TestCase):
    """Tests for the translate_strings command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_dry_run_no_translate(self):
        """translate_strings --dry-run --no-translate runs without modifying files."""
        out = io.StringIO()
        # The command may sys.exit(1) if .po file is not found; catch that
        try:
            call_command(
                "translate_strings",
                dry_run=True,
                no_translate=True,
                stdout=out,
            )
        except SystemExit:
            pass
        output = out.getvalue()
        self.assertIn("Translation Sync", output)


# =========================================================================
# Utility Commands
# =========================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CheckDocumentUrlTest(TestCase):
    """Tests for the check_document_url command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_not_configured(self):
        """check_document_url shows warning when document storage is not configured."""
        out = io.StringIO()
        # When no document storage is configured, the command returns normally
        try:
            call_command("check_document_url", stdout=out)
        except SystemExit:
            pass
        self.assertIn("not configured", out.getvalue().lower())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DiagnoseChartsTest(TestCase):
    """Tests for the diagnose_charts command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_client_not_found(self):
        """diagnose_charts shows error when the client does not exist."""
        out = io.StringIO()
        call_command("diagnose_charts", client="NONEXISTENT-999", stdout=out)
        self.assertIn("not found", out.getvalue().lower())

    def test_smoke_default_client(self):
        """diagnose_charts runs without crashing for a missing default client."""
        out = io.StringIO()
        # Default is DEMO-001 which won't exist in test DB -- should report not found
        call_command("diagnose_charts", stdout=out)
        output = out.getvalue()
        # Either "not found" (no demo data) or diagnostic output
        self.assertTrue(len(output) > 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AlertExpiredRetentionTest(TestCase):
    """Tests for the alert_expired_retention command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_no_expired_clients(self):
        """alert_expired_retention reports no action when there are no expired clients."""
        out = io.StringIO()
        call_command("alert_expired_retention", stdout=out)
        self.assertIn("No clients past retention date", out.getvalue())

    def test_dry_run_no_expired(self):
        """alert_expired_retention --dry-run works with no expired clients."""
        out = io.StringIO()
        call_command("alert_expired_retention", dry_run=True, stdout=out)
        self.assertIn("No clients past retention date", out.getvalue())

    def test_dry_run_with_expired_client(self):
        """alert_expired_retention --dry-run finds expired clients and does not email."""
        from datetime import date, timedelta

        from apps.clients.models import ClientFile

        # Create a client with expired retention
        client = ClientFile()
        client.first_name = "Test"
        client.last_name = "Expired"
        client.record_id = "TEST-EXPIRED-001"
        client.status = "active"
        client.retention_expires = date.today() - timedelta(days=30)
        client.save()

        out = io.StringIO()
        call_command("alert_expired_retention", dry_run=True, stdout=out)
        output = out.getvalue()
        self.assertIn("TEST-EXPIRED-001", output)
        self.assertIn("DRY RUN", output)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MigratePhoneFieldTest(TestCase):
    """Tests for the migrate_phone_field command."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_dry_run_no_data(self):
        """migrate_phone_field --dry-run runs without crashing when there is no data."""
        out = io.StringIO()
        call_command("migrate_phone_field", dry_run=True, stdout=out)
        self.assertIn("Phone migration complete", out.getvalue())


@unittest.skipUnless(
    os.environ.get("DATABASE_URL", "").startswith("postgres"),
    "lockdown_audit_db requires PostgreSQL",
)
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LockdownAuditDbTest(TestCase):
    """Tests for the lockdown_audit_db command. Requires PostgreSQL."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_placeholder(self):
        """Placeholder test -- lockdown_audit_db requires a real PostgreSQL audit database."""
        # This test only runs against PostgreSQL and verifies the command
        # completes without error.
        out = io.StringIO()
        call_command("lockdown_audit_db", stdout=out)
        self.assertIn("locked down", out.getvalue().lower())
