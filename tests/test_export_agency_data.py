"""
Tests for the export_agency_data management command.

Covers:
- Dry run output
- Flat JSON files per exportable model
- Nested clients_complete.json structure
- Config files (agency_settings, metrics, etc.)
- Manifest contents
- AES-256-GCM encryption / decryption round-trip
- Plaintext ZIP output
- --client-id single-client filtering
- Audit log creation
- Encrypted field decryption in output
- File format (version byte + salt + IV + ciphertext)
"""

import io
import json
import os
import tempfile
import zipfile

import pytest
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from apps.reports.management.commands.export_agency_data import (
    VERSION,
    SALT_LEN,
    IV_LEN,
    KDF_ITERATIONS,
    generate_passphrase,
    derive_key,
    encrypt_data,
    serialize_instance,
    ExportEncoder,
)


# ── Helpers ───────────────────────────────────────────────────────────

def _decrypt_export(enc_bytes, passphrase):
    """Mirror the decryptor's logic: VERSION + salt + IV + ciphertext."""
    assert enc_bytes[0] == VERSION
    salt = enc_bytes[1 : 1 + SALT_LEN]
    iv = enc_bytes[1 + SALT_LEN : 1 + SALT_LEN + IV_LEN]
    ciphertext = enc_bytes[1 + SALT_LEN + IV_LEN :]
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ciphertext, None)


def _unzip_bytes(zip_bytes):
    """Return {arc_name: content_bytes} from a ZIP archive."""
    buf = io.BytesIO(zip_bytes)
    result = {}
    with zipfile.ZipFile(buf, "r") as zf:
        for name in zf.namelist():
            result[name] = zf.read(name)
    return result


def _call_export(**kwargs):
    """Call the command and capture stdout."""
    out = io.StringIO()
    call_command("export_agency_data", stdout=out, **kwargs)
    return out.getvalue()


# ── Test Data Setup ───────────────────────────────────────────────────

@pytest.mark.django_db(databases=["default", "audit"])
class ExportAgencyDataTests(TestCase):
    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        from apps.programs.models import Program
        from apps.clients.models import ClientFile, ServiceEpisode
        from apps.admin_settings.models import InstanceSetting, TerminologyOverride
        from apps.plans.models import MetricDefinition, PlanSection, PlanTarget
        from apps.notes.models import ProgressNote, ProgressNoteTarget, MetricValue
        from apps.events.models import Event, EventType
        from django.contrib.auth import get_user_model

        User = get_user_model()

        cls.user = User.objects.create_user(
            username="exporttester",
            password="testpass123",
            email="export@test.org",
        )

        cls.program = Program.objects.create(name="Housing First")

        cls.client1 = ClientFile.objects.create()
        cls.client1.first_name = "Jane"
        cls.client1.last_name = "Doe"
        cls.client1.save()

        cls.client2 = ClientFile.objects.create()
        cls.client2.first_name = "John"
        cls.client2.last_name = "Smith"
        cls.client2.save()

        cls.enrolment = ServiceEpisode.objects.create(
            client_file=cls.client1,
            program=cls.program,
            status="active",
        )

        cls.setting = InstanceSetting.objects.create(
            setting_key="agency_name",
            setting_value="Test Agency",
        )

        cls.term = TerminologyOverride.objects.create(
            term_key="client",
            display_value="Participant",
        )

        cls.metric_def = MetricDefinition.objects.create(
            name="Housing Stability",
            definition="Measures housing stability",
            category="housing",
        )

        cls.section = PlanSection.objects.create(
            client_file=cls.client1,
            name="Housing Goals",
            program=cls.program,
        )

        cls.target = PlanTarget.objects.create(
            plan_section=cls.section,
            client_file=cls.client1,
        )
        cls.target.name = "Find stable housing"
        cls.target.save()

        cls.note = ProgressNote.objects.create(
            client_file=cls.client1,
            note_type="quick",
            author=cls.user,
            author_program=cls.program,
        )
        cls.note.notes_text = "Client is making progress"
        cls.note.save()

        cls.note_target = ProgressNoteTarget.objects.create(
            progress_note=cls.note,
            plan_target=cls.target,
        )
        cls.note_target.notes = "Good session"
        cls.note_target.save()

        cls.metric_val = MetricValue.objects.create(
            progress_note_target=cls.note_target,
            metric_def=cls.metric_def,
            value="7",
        )

        cls.event_type = EventType.objects.create(name="Intake")
        cls.event = Event.objects.create(
            client_file=cls.client1,
            title="Intake meeting",
            event_type=cls.event_type,
            start_timestamp=timezone.now(),
        )

    # ── 1. Dry run ────────────────────────────────────────────────────

    def test_dry_run_shows_models_and_counts(self):
        output = _call_export(dry_run=True)
        self.assertIn("Summary", output)
        # Should show at least some model names
        self.assertIn("clients.clientfile", output)
        self.assertIn("programs.program", output)
        # Should show row counts (at least 1 for our test data)
        # Don't write files
        self.assertNotIn("written to", output)

    # ── 2. Flat JSON files ────────────────────────────────────────────

    def test_plaintext_creates_flat_json_per_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test_export.zip")
            _call_export(output=out_path, plaintext=True, yes=True)
            self.assertTrue(os.path.exists(out_path))

            files = _unzip_bytes(open(out_path, "rb").read())
            # Should have at least one data JSON
            data_files = [f for f in files if "/data/" in f and f.endswith(".json")]
            self.assertGreater(len(data_files), 0)

            # Check a specific flat file exists
            client_files = [f for f in data_files if "clients_clientfile.json" in f]
            self.assertEqual(len(client_files), 1)

            records = json.loads(files[client_files[0]])
            self.assertIsInstance(records, list)
            self.assertGreaterEqual(len(records), 2)  # Jane + John

    # ── 3. clients_complete.json ──────────────────────────────────────

    def test_clients_complete_has_nested_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

            files = _unzip_bytes(open(out_path, "rb").read())
            cc_files = [f for f in files if "clients_complete.json" in f]
            self.assertEqual(len(cc_files), 1)

            data = json.loads(files[cc_files[0]])
            self.assertIn("export_metadata", data)
            self.assertIn("clients", data)
            self.assertEqual(data["export_metadata"]["format_version"], "1.0")
            self.assertGreaterEqual(data["export_metadata"]["client_count"], 2)

            # Find Jane's record
            jane = next(
                (c for c in data["clients"] if c.get("first_name") == "Jane"),
                None,
            )
            self.assertIsNotNone(jane, "Jane should be in the export")
            self.assertIn("programs", jane)
            self.assertIn("events", jane)
            self.assertIn("custom_fields", jane)

    # ── 4. Config files ───────────────────────────────────────────────

    def test_config_files_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

            files = _unzip_bytes(open(out_path, "rb").read())
            config_names = [os.path.basename(f) for f in files if "/config/" in f]
            self.assertIn("agency_settings.json", config_names)
            self.assertIn("metric_definitions.json", config_names)
            self.assertIn("custom_field_definitions.json", config_names)
            self.assertIn("program_structures.json", config_names)
            self.assertIn("terminology.json", config_names)

            # Verify agency_settings content
            settings_file = [f for f in files if f.endswith("agency_settings.json")][0]
            settings_data = json.loads(files[settings_file])
            self.assertEqual(settings_data.get("agency_name"), "Test Agency")

    # ── 5. Manifest ───────────────────────────────────────────────────

    def test_manifest_includes_models_and_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

            files = _unzip_bytes(open(out_path, "rb").read())
            manifest_files = [f for f in files if "manifest.json" in f]
            self.assertEqual(len(manifest_files), 1)

            manifest = json.loads(files[manifest_files[0]])
            self.assertEqual(manifest["schema_version"], "1.0")
            self.assertIn("exported_at", manifest)
            self.assertIn("models", manifest)
            self.assertIsInstance(manifest["models"], list)

            # Each model entry has required keys
            for entry in manifest["models"]:
                self.assertIn("model", entry)
                self.assertIn("row_count", entry)
                self.assertIn("file", entry)

    # ── 6. AES-256-GCM encrypted export round-trip ────────────────────

    def test_encrypted_export_can_be_decrypted(self):
        """Encrypt, then decrypt and verify we get a valid ZIP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.enc")
            out = io.StringIO()
            call_command(
                "export_agency_data",
                output=out_path,
                yes=True,
                stdout=out,
            )

            # Extract passphrase from stdout
            output_text = out.getvalue()
            # Passphrase is printed between the ═ lines
            lines = output_text.splitlines()
            passphrase = None
            for i, line in enumerate(lines):
                if "DECRYPTION PASSPHRASE" in line:
                    # Next line has the passphrase (indented)
                    passphrase = lines[i + 1].strip()
                    break
            self.assertIsNotNone(passphrase, "Passphrase should be printed to stdout")
            self.assertGreater(len(passphrase.split()), 4, "Should be a multi-word passphrase")

            # Decrypt
            with open(out_path, "rb") as f:
                enc_bytes = f.read()

            zip_bytes = _decrypt_export(enc_bytes, passphrase)

            # The result should be a valid ZIP
            buf = io.BytesIO(zip_bytes)
            with zipfile.ZipFile(buf) as zf:
                names = zf.namelist()
                self.assertTrue(any("manifest.json" in n for n in names))

    # ── 7. Plaintext creates unencrypted ZIP ──────────────────────────

    def test_plaintext_is_valid_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

            with open(out_path, "rb") as f:
                data = f.read()
            # ZIP files start with PK (0x50 0x4B)
            self.assertEqual(data[0:2], b"PK")

            buf = io.BytesIO(data)
            with zipfile.ZipFile(buf) as zf:
                self.assertTrue(zf.testzip() is None, "ZIP should be valid")

    # ── 8. --client-id exports only that client ───────────────────────

    def test_client_id_filters_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(
                output=out_path, plaintext=True, yes=True,
                client_id=self.client1.pk,
            )

            files = _unzip_bytes(open(out_path, "rb").read())
            cc_file = [f for f in files if "clients_complete.json" in f][0]
            data = json.loads(files[cc_file])
            self.assertEqual(data["export_metadata"]["client_count"], 1)
            self.assertEqual(data["clients"][0]["first_name"], "Jane")

    # ── 9. Audit log created before export ────────────────────────────

    def test_audit_log_created(self):
        from apps.audit.models import AuditLog

        before_count = AuditLog.objects.using("audit").filter(
            resource_type="agency_data_export"
        ).count()

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

        after_count = AuditLog.objects.using("audit").filter(
            resource_type="agency_data_export"
        ).count()
        self.assertEqual(after_count, before_count + 1)

        log = AuditLog.objects.using("audit").filter(
            resource_type="agency_data_export"
        ).latest("event_timestamp")
        self.assertEqual(log.action, "export")
        self.assertIn("mode", log.metadata)

    # ── 10. Encrypted fields are decrypted in output ──────────────────

    def test_encrypted_fields_decrypted_in_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

            files = _unzip_bytes(open(out_path, "rb").read())
            cc_file = [f for f in files if "clients_complete.json" in f][0]
            data = json.loads(files[cc_file])

            jane = next(c for c in data["clients"] if c.get("first_name") == "Jane")
            self.assertEqual(jane["first_name"], "Jane")
            self.assertEqual(jane["last_name"], "Doe")

            # No raw encrypted binary should appear
            for key, val in jane.items():
                if isinstance(val, str):
                    self.assertNotIn("\\x", val, f"Field {key} looks like raw bytes")

    # ── 11. File format matches decryptor expectations ────────────────

    def test_encrypted_file_format(self):
        """VERSION byte (0x01) + 16-byte salt + 12-byte IV + ciphertext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.enc")
            out = io.StringIO()
            call_command(
                "export_agency_data",
                output=out_path,
                yes=True,
                stdout=out,
            )

            with open(out_path, "rb") as f:
                data = f.read()

            # First byte is version
            self.assertEqual(data[0], VERSION)

            # Minimum length: 1 + 16 + 12 + 16 (GCM tag) = 45
            self.assertGreater(len(data), 1 + SALT_LEN + IV_LEN + 16)

            # Salt and IV should be present (non-zero, random)
            salt = data[1 : 1 + SALT_LEN]
            iv = data[1 + SALT_LEN : 1 + SALT_LEN + IV_LEN]
            self.assertEqual(len(salt), SALT_LEN)
            self.assertEqual(len(iv), IV_LEN)

    # ── 12. Refuse to overwrite existing file ─────────────────────────

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "existing.zip")
            # Create the file first
            with open(out_path, "w") as f:
                f.write("existing")

            from django.core.management.base import CommandError

            with self.assertRaises(CommandError) as ctx:
                _call_export(output=out_path, plaintext=True, yes=True)
            self.assertIn("already exists", str(ctx.exception))

    # ── 13. Progress note content is decrypted ────────────────────────

    def test_progress_note_decrypted_in_nested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

            files = _unzip_bytes(open(out_path, "rb").read())
            cc_file = [f for f in files if "clients_complete.json" in f][0]
            data = json.loads(files[cc_file])

            jane = next(c for c in data["clients"] if c.get("first_name") == "Jane")
            self.assertGreater(len(jane["programs"]), 0)

            # Find the enrolment and check notes
            ep = jane["programs"][0]
            self.assertIn("progress_notes", ep)
            if ep["progress_notes"]:
                note = ep["progress_notes"][0]
                self.assertEqual(note.get("notes_text"), "Client is making progress")

    # ── 14. Plan target name is decrypted ─────────────────────────────

    def test_plan_target_decrypted_in_nested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "test.zip")
            _call_export(output=out_path, plaintext=True, yes=True)

            files = _unzip_bytes(open(out_path, "rb").read())
            cc_file = [f for f in files if "clients_complete.json" in f][0]
            data = json.loads(files[cc_file])

            jane = next(c for c in data["clients"] if c.get("first_name") == "Jane")
            ep = jane["programs"][0]
            self.assertIn("plan_targets", ep)
            if ep["plan_targets"]:
                target = ep["plan_targets"][0]
                self.assertEqual(target.get("name"), "Find stable housing")


# ── Unit tests for helper functions ───────────────────────────────────

class ExportHelperTests(TestCase):

    def test_generate_passphrase_six_words(self):
        pp = generate_passphrase()
        words = pp.split()
        self.assertEqual(len(words), 6)
        # All words should be lowercase alpha
        for w in words:
            self.assertTrue(w.isalpha(), f"Word '{w}' should be alphabetic")

    def test_encrypt_decrypt_roundtrip(self):
        passphrase = "alpha brisk cedar donor easel facet"
        plaintext = b"Hello, KoNote export!"
        encrypted = encrypt_data(plaintext, passphrase)

        # Verify format
        self.assertEqual(encrypted[0], VERSION)
        self.assertEqual(len(encrypted), 1 + SALT_LEN + IV_LEN + len(plaintext) + 16)  # +16 for GCM tag

        decrypted = _decrypt_export(encrypted, passphrase)
        self.assertEqual(decrypted, plaintext)

    def test_wrong_passphrase_fails(self):
        passphrase = "alpha brisk cedar donor easel facet"
        plaintext = b"secret data"
        encrypted = encrypt_data(plaintext, passphrase)

        with self.assertRaises(Exception):
            _decrypt_export(encrypted, "wrong passphrase here please fail")

    def test_export_encoder_handles_types(self):
        from datetime import date, datetime
        from decimal import Decimal
        from uuid import UUID

        data = {
            "dt": datetime(2026, 1, 15, 10, 30, 0),
            "d": date(2026, 1, 15),
            "dec": Decimal("3.14159"),
            "uuid": UUID("12345678-1234-5678-1234-567812345678"),
            "raw": b"\x00\x01",
        }
        result = json.loads(json.dumps(data, cls=ExportEncoder))
        self.assertEqual(result["dt"], "2026-01-15T10:30:00")
        self.assertEqual(result["d"], "2026-01-15")
        self.assertEqual(result["dec"], "3.14159")
        self.assertEqual(result["uuid"], "12345678-1234-5678-1234-567812345678")
        self.assertIsNone(result["raw"])

    def test_derive_key_deterministic(self):
        salt = b"\x00" * 16
        key1 = derive_key("test passphrase", salt)
        key2 = derive_key("test passphrase", salt)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)  # 256 bits

    def test_derive_key_different_salt(self):
        key1 = derive_key("test", b"\x00" * 16)
        key2 = derive_key("test", b"\x01" * 16)
        self.assertNotEqual(key1, key2)
