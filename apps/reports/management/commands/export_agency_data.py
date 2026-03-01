"""
Management command: export_agency_data

Exports ALL agency data for offboarding, migration, or backup.

Usage:
    # Full agency export — encrypted (for offboarding handover)
    python manage.py export_agency_data --output /path/export.enc

    # Full agency export — plaintext (for backup)
    python manage.py export_agency_data --plaintext --output /path/backup.zip

    # Dry run (shows row counts)
    python manage.py export_agency_data --dry-run

    # Single client
    python manage.py export_agency_data --client-id 42 --plaintext --output /path/client_42.zip

File format (encrypted mode):
    VERSION byte (0x01) + 16-byte salt + 12-byte IV + AES-256-GCM ciphertext

    Key derivation: PBKDF2-SHA256, 600 000 iterations, from a 6-word
    Diceware passphrase generated at export time.
"""

import io
import json
import os
import secrets
import shutil
import tempfile
import zipfile
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.utils import timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from apps.reports.export_registry import get_exportable_models
from konote.encryption import DecryptionError

# ── Constants ─────────────────────────────────────────────────────────

VERSION = 0x01
SALT_LEN = 16
IV_LEN = 12
KDF_ITERATIONS = 600_000
SCHEMA_VERSION = "1.0"

# EFF short wordlist (abridged — 200 common words, diverse starting letters)
EFF_SHORT_WORDLIST = [
    "acid", "acorn", "acre", "aging", "airbag", "aisle", "alarm", "alike",
    "alive", "alpha", "ample", "ankle", "apple", "arena", "argon", "attic",
    "awning", "bacon", "badge", "bagel", "baker", "balmy", "banjo", "basin",
    "batch", "beard", "begin", "being", "bench", "berry", "bison", "blaze",
    "bliss", "booth", "boxer", "bread", "brisk", "budget", "bugle", "bunch",
    "cable", "camel", "candy", "cargo", "cedar", "chain", "chalk", "chase",
    "chess", "chief", "cider", "civic", "clasp", "clerk", "cliff", "cloud",
    "coach", "cobra", "coral", "couch", "crane", "crisp", "crowd", "crush",
    "cubic", "dance", "decoy", "delta", "depot", "diary", "ditch", "dodge",
    "doing", "donor", "dough", "draft", "dried", "dryer", "dunce", "dusty",
    "eagle", "early", "easel", "eight", "elder", "ember", "enamel", "ended",
    "entry", "epoch", "essay", "evade", "exact", "exile", "extra", "facet",
    "fairy", "fancy", "feast", "fiber", "fifth", "finch", "fizzy", "flame",
    "fleet", "flint", "flood", "flora", "floss", "focus", "forge", "found",
    "front", "frost", "fruit", "gavel", "giddy", "given", "gizmo", "globe",
    "gloss", "grain", "grape", "grasp", "green", "grief", "grind", "grove",
    "guide", "gusty", "haven", "hazel", "hedge", "heron", "hoist", "honor",
    "hound", "hydro", "index", "inlet", "ivory", "jewel", "jumbo", "kayak",
    "kinky", "lager", "lance", "latch", "layer", "lemon", "lilac", "linen",
    "llama", "logic", "lotus", "lunar", "major", "mango", "manor", "maple",
    "marsh", "melon", "mercy", "miner", "mocha", "mogul", "molar", "month",
    "moose", "nerve", "noble", "north", "nudge", "nylon", "oasis", "ocean",
    "olive", "onset", "opera", "orbit", "otter", "oxide", "panda", "panic",
    "patch", "peach", "pearl", "penny", "perch", "pilot", "plaza", "plumb",
    "polar", "poppy", "power", "prism", "proxy", "pulse", "query", "quiet",
]


def generate_passphrase(word_count=6):
    """Generate a Diceware passphrase from the EFF short wordlist."""
    return " ".join(secrets.choice(EFF_SHORT_WORDLIST) for _ in range(word_count))


def derive_key(passphrase, salt):
    """Derive a 256-bit AES key from passphrase + salt via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_data(plaintext_bytes, passphrase):
    """Encrypt bytes with AES-256-GCM.  Returns VERSION + salt + IV + ciphertext."""
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext_bytes, None)
    return bytes([VERSION]) + salt + iv + ciphertext


# ── JSON encoder ──────────────────────────────────────────────────────

class ExportEncoder(json.JSONEncoder):
    """Handle Django model field types that stdlib json can't serialise."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, bytes):
            return None  # skip raw binary
        if isinstance(obj, memoryview):
            return None
        return super().default(obj)


# ── Model serialisation helpers ───────────────────────────────────────

def _get_encrypted_property_names(model):
    """Return a dict mapping encrypted BinaryField attr → property name.

    e.g. {'_first_name_encrypted': 'first_name'}
    """
    mapping = {}
    for field in model._meta.get_fields():
        if isinstance(field, models.BinaryField) and field.name.startswith("_") and field.name.endswith("_encrypted"):
            prop_name = field.name[1:].replace("_encrypted", "")
            # Verify the model actually has a property accessor
            if hasattr(model, prop_name):
                mapping[field.attname if hasattr(field, "attname") else field.name] = prop_name
    return mapping


def serialize_instance(instance, encrypted_map=None):
    """Serialise a single model instance to a dict.

    - Encrypted fields are accessed via property (decrypted).
    - FK fields stored as ID.
    - M2M fields stored as list of IDs.
    - BinaryField (encrypted raw) skipped.
    """
    if encrypted_map is None:
        encrypted_map = _get_encrypted_property_names(type(instance))

    data = {}
    skip_attrs = set(encrypted_map.keys())

    for field in instance._meta.get_fields():
        # Skip reverse relations
        if field.one_to_many or field.one_to_one and not field.concrete:
            continue
        # Skip M2M for now — handled below
        if field.many_to_many:
            continue

        name = field.name
        attr = field.attname if hasattr(field, "attname") else name

        # Skip encrypted binary fields (use property instead)
        if attr in skip_attrs or name in skip_attrs:
            continue

        # Skip raw BinaryField that isn't in the encrypted map
        if isinstance(field, models.BinaryField):
            continue

        try:
            value = getattr(instance, attr)
        except Exception:
            value = None

        data[name if attr == name else attr] = value

    # Add decrypted property values
    for _attr, prop_name in encrypted_map.items():
        try:
            data[prop_name] = getattr(instance, prop_name)
        except (DecryptionError, Exception):
            data[prop_name] = "[DECRYPTION ERROR]"

    # Add M2M fields
    for field in instance._meta.get_fields():
        if field.many_to_many and not field.related_model:
            continue
        if field.many_to_many:
            try:
                manager = getattr(instance, field.name)
                data[field.name] = list(manager.values_list("pk", flat=True))
            except Exception:
                data[field.name] = []

    return data


def serialize_queryset(queryset):
    """Serialise an entire queryset to a list of dicts."""
    model = queryset.model
    encrypted_map = _get_encrypted_property_names(model)
    return [serialize_instance(obj, encrypted_map) for obj in queryset.iterator()]


# ── Command ───────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Export all agency data for offboarding, migration, or backup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", "-o",
            type=str,
            default="",
            help="Output file path (.enc for encrypted, .zip for plaintext).",
        )
        parser.add_argument(
            "--plaintext",
            action="store_true",
            help="Write an unencrypted ZIP instead of an encrypted archive.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show model list and row counts without writing files.",
        )
        parser.add_argument(
            "--client-id",
            type=int,
            default=None,
            help="Export only data for a single client (by ID).",
        )
        parser.add_argument(
            "--authorized-by",
            type=str,
            default="",
            help="Name of the person who authorised this export (logged only).",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip interactive confirmation (for automated pipelines).",
        )

    # ── handle ────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        plaintext = options["plaintext"]
        output_path = options["output"]
        client_id = options["client_id"]
        authorized_by = options["authorized_by"]
        skip_confirm = options["yes"]

        exportable = sorted(get_exportable_models(), key=lambda m: f"{m._meta.app_label}.{m._meta.model_name}")

        # ── Dry Run ───────────────────────────────────────────────────
        if dry_run:
            self._print_summary(exportable, client_id)
            return

        # ── Validate output ───────────────────────────────────────────
        if not output_path:
            raise CommandError("--output is required (unless using --dry-run).")

        if os.path.exists(output_path):
            raise CommandError(f"Output file already exists: {output_path}. Refusing to overwrite.")

        # Create parent directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # ── Summary + Confirmation ────────────────────────────────────
        self._print_summary(exportable, client_id)

        if not skip_confirm:
            expected = "CONFIRM PLAINTEXT" if plaintext else "CONFIRM"
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(f'Type "{expected}" to proceed, or anything else to cancel:')
            )
            try:
                answer = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                raise CommandError("Export cancelled.")
            if answer != expected:
                raise CommandError("Export cancelled — confirmation text did not match.")

        # ── Audit log BEFORE export ───────────────────────────────────
        from apps.audit.models import AuditLog

        now = timezone.now()
        audit_metadata = {
            "mode": "plaintext" if plaintext else "encrypted",
            "output": output_path,
            "authorized_by": authorized_by or "(not specified)",
        }
        if client_id:
            audit_metadata["client_id"] = client_id

        AuditLog.objects.using("audit").create(
            event_timestamp=now,
            action="export",
            resource_type="agency_data_export",
            metadata=audit_metadata,
        )

        # ── Build the export ──────────────────────────────────────────
        tmpdir = tempfile.mkdtemp(prefix="konote_export_")
        try:
            self._build_export(tmpdir, exportable, client_id, now)
            zip_bytes = self._zip_directory(tmpdir)

            if plaintext:
                with open(output_path, "wb") as f:
                    f.write(zip_bytes)
                self.stdout.write(self.style.SUCCESS(f"\nPlaintext export written to: {output_path}"))
            else:
                passphrase = generate_passphrase()
                encrypted = encrypt_data(zip_bytes, passphrase)
                with open(output_path, "wb") as f:
                    f.write(encrypted)
                self.stdout.write(self.style.SUCCESS(f"\nEncrypted export written to: {output_path}"))
                self.stdout.write("")
                self.stdout.write(self.style.WARNING("═" * 60))
                self.stdout.write(self.style.WARNING("  DECRYPTION PASSPHRASE (record this NOW):"))
                self.stdout.write(self.style.WARNING(f"  {passphrase}"))
                self.stdout.write(self.style.WARNING("═" * 60))
                self.stdout.write("")
                self.stdout.write(
                    "  Communicate this passphrase by phone or in person.\n"
                    "  Do not send it by email or text message.\n"
                    "  This passphrase will NOT be shown again."
                )
                self.stdout.write("")

        except Exception:
            # Clean up partial output on failure
            if os.path.exists(output_path):
                os.remove(output_path)
            raise
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # ── Summary printer ───────────────────────────────────────────────

    def _print_summary(self, exportable, client_id):
        """Print a table of models and row counts."""
        self.stdout.write(self.style.HTTP_INFO("\n  Agency Data Export — Summary\n"))
        if client_id:
            self.stdout.write(f"  Scope: single client (ID {client_id})\n")
        else:
            self.stdout.write("  Scope: full agency\n")

        self.stdout.write(f"  {'Model':<45} {'Rows':>8}")
        self.stdout.write(f"  {'─' * 45} {'─' * 8}")

        total = 0
        for model in exportable:
            label = f"{model._meta.app_label}.{model._meta.model_name}"
            qs = model.objects.all()
            if client_id:
                qs = self._filter_for_client(qs, model, client_id)
            count = qs.count()
            total += count
            self.stdout.write(f"  {label:<45} {count:>8}")

        self.stdout.write(f"  {'─' * 45} {'─' * 8}")
        self.stdout.write(f"  {'TOTAL':<45} {total:>8}\n")

    # ── Build export directory ────────────────────────────────────────

    def _build_export(self, tmpdir, exportable, client_id, now):
        """Create the full export directory structure."""
        export_name = f"export-{now.strftime('%Y-%m-%d')}"
        base = os.path.join(tmpdir, export_name)
        data_dir = os.path.join(base, "data")
        config_dir = os.path.join(base, "config")
        meta_dir = os.path.join(base, "meta")
        os.makedirs(data_dir)
        os.makedirs(config_dir)
        os.makedirs(meta_dir)

        manifest_models = []

        # ── Flat data files ───────────────────────────────────────────
        for model in exportable:
            qs = model.objects.all()
            if client_id:
                qs = self._filter_for_client(qs, model, client_id)

            label = f"{model._meta.app_label}_{model._meta.model_name}"
            records = serialize_queryset(qs)
            count = len(records)
            manifest_models.append({
                "model": f"{model._meta.app_label}.{model._meta.model_name}",
                "file": f"{label}.json",
                "row_count": count,
            })

            self._write_json(os.path.join(data_dir, f"{label}.json"), records)

        # ── Nested client-centric file ────────────────────────────────
        self._build_clients_complete(data_dir, client_id, now)

        # ── Config files ──────────────────────────────────────────────
        self._build_config_files(config_dir)

        # ── Meta files ────────────────────────────────────────────────
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "exported_at": now.isoformat(),
            "client_id": client_id,
            "models": manifest_models,
        }
        self._write_json(os.path.join(meta_dir, "manifest.json"), manifest)

        with open(os.path.join(meta_dir, "schema_version.txt"), "w") as f:
            f.write(SCHEMA_VERSION)

        readme = (
            "KoNote Agency Data Export\n"
            "========================\n\n"
            f"Exported: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Schema version: {SCHEMA_VERSION}\n\n"
            "Directory structure:\n"
            "  data/     — One JSON file per model (flat records) + clients_complete.json\n"
            "  config/   — Agency configuration (settings, metrics, fields, programs, terminology)\n"
            "  meta/     — Manifest, schema version, this README\n\n"
            "If this file was inside an encrypted archive (.enc), it was\n"
            "decrypted using the companion HTML decryptor tool with a\n"
            "6-word passphrase and AES-256-GCM (PBKDF2, 600 000 iterations).\n"
        )
        with open(os.path.join(meta_dir, "README.txt"), "w") as f:
            f.write(readme)

    # ── Nested client-centric file ────────────────────────────────────

    def _build_clients_complete(self, data_dir, client_id, now):
        """Build clients_complete.json with nested per-client data."""
        from apps.clients.models import ClientFile, ClientDetailValue
        from apps.notes.models import ProgressNote, ProgressNoteTarget, MetricValue
        from apps.plans.models import PlanSection, PlanTarget
        from apps.events.models import Event

        client_qs = ClientFile.objects.all()
        if client_id:
            client_qs = client_qs.filter(pk=client_id)

        clients_data = []
        for client in client_qs.iterator():
            client_dict = serialize_instance(client)

            # Programs (service episodes / enrolments)
            programs_list = []
            for ep in client.enrolments.all():
                ep_data = serialize_instance(ep)
                # Plan targets for this client in this program
                sections = PlanSection.objects.filter(
                    client_file=client, program=ep.program
                )
                plan_targets = []
                for section in sections:
                    for target in section.targets.all():
                        plan_targets.append(serialize_instance(target))

                # Progress notes authored under this program
                notes = ProgressNote.objects.filter(
                    client_file=client, author_program=ep.program
                )
                notes_list = []
                for note in notes:
                    note_data = serialize_instance(note)
                    # Target entries + metric values
                    target_entries = []
                    for te in note.target_entries.all():
                        te_data = serialize_instance(te)
                        te_data["metric_values"] = [
                            serialize_instance(mv) for mv in te.metric_values.all()
                        ]
                        target_entries.append(te_data)
                    note_data["target_entries"] = target_entries
                    notes_list.append(note_data)

                ep_data["plan_targets"] = plan_targets
                ep_data["progress_notes"] = notes_list
                programs_list.append(ep_data)

            client_dict["programs"] = programs_list

            # Events
            client_dict["events"] = [
                serialize_instance(e) for e in Event.objects.filter(client_file=client)
            ]

            # Custom field values
            custom_values = []
            for cv in ClientDetailValue.objects.filter(client_file=client).select_related("field_def"):
                custom_values.append({
                    "field_name": cv.field_def.name,
                    "field_group": cv.field_def.group.title if cv.field_def.group_id else "",
                    "value": cv.get_value(),
                })
            client_dict["custom_fields"] = custom_values

            # Circles
            try:
                from apps.circles.models import CircleMembership
                memberships = CircleMembership.objects.filter(
                    client_file=client
                ).select_related("circle")
                circles_list = []
                for m in memberships:
                    circles_list.append({
                        "circle_id": m.circle_id,
                        "circle_name": m.circle.name,
                        "role": getattr(m, "role", ""),
                        "status": m.status,
                    })
                client_dict["circles"] = circles_list
            except Exception:
                client_dict["circles"] = []

            clients_data.append(client_dict)

        output = {
            "export_metadata": {
                "format_version": SCHEMA_VERSION,
                "exported_at": now.isoformat(),
                "client_count": len(clients_data),
            },
            "clients": clients_data,
        }
        self._write_json(os.path.join(data_dir, "clients_complete.json"), output)

    # ── Config files ──────────────────────────────────────────────────

    def _build_config_files(self, config_dir):
        """Extract agency configuration into dedicated JSON files."""
        from apps.admin_settings.models import InstanceSetting, TerminologyOverride
        from apps.plans.models import MetricDefinition
        from apps.clients.models import CustomFieldDefinition, CustomFieldGroup
        from apps.programs.models import Program

        # agency_settings.json
        settings_data = {s.setting_key: s.setting_value for s in InstanceSetting.objects.all()}
        self._write_json(os.path.join(config_dir, "agency_settings.json"), settings_data)

        # metric_definitions.json
        metrics = serialize_queryset(MetricDefinition.objects.all())
        self._write_json(os.path.join(config_dir, "metric_definitions.json"), metrics)

        # custom_field_definitions.json
        groups_data = []
        for group in CustomFieldGroup.objects.prefetch_related("fields").all():
            group_dict = serialize_instance(group)
            group_dict["fields"] = [serialize_instance(f) for f in group.fields.all()]
            groups_data.append(group_dict)
        self._write_json(os.path.join(config_dir, "custom_field_definitions.json"), groups_data)

        # program_structures.json
        programs = serialize_queryset(Program.objects.all())
        self._write_json(os.path.join(config_dir, "program_structures.json"), programs)

        # terminology.json
        terms = serialize_queryset(TerminologyOverride.objects.all())
        self._write_json(os.path.join(config_dir, "terminology.json"), terms)

    # ── Client filtering ──────────────────────────────────────────────

    def _filter_for_client(self, qs, model, client_id):
        """Narrow a queryset to rows related to a specific client."""
        # Direct FK to ClientFile
        for field in model._meta.get_fields():
            if isinstance(field, models.ForeignKey):
                related = field.related_model
                if related and related._meta.label_lower == "clients.clientfile":
                    return qs.filter(**{field.name: client_id})

        # If the model IS ClientFile, filter by pk
        if model._meta.label_lower == "clients.clientfile":
            return qs.filter(pk=client_id)

        # Models without client FK — return full set (config, metadata)
        return qs

    # ── Helpers ────────────────────────────────────────────────────────

    def _write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, cls=ExportEncoder, ensure_ascii=False, indent=2)

    def _zip_directory(self, tmpdir):
        """Zip the export directory into bytes."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(tmpdir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    arc_name = os.path.relpath(abs_path, tmpdir)
                    zf.write(abs_path, arc_name)
        return buf.getvalue()
