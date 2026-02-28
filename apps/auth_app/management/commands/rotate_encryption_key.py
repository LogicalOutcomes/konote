"""
Rotate the Fernet encryption key used for PII fields.

This command re-encrypts all encrypted data in the database from an old key
to a new key. Use this when you need to rotate your FIELD_ENCRYPTION_KEY.

Full rotation process:
    1. Generate a new Fernet key:
       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    2. Run this command with both keys (dry run first to verify):
       python manage.py rotate_encryption_key --old-key <OLD_KEY> --new-key <NEW_KEY> --dry-run
       python manage.py rotate_encryption_key --old-key <OLD_KEY> --new-key <NEW_KEY>

    3. Update the FIELD_ENCRYPTION_KEY environment variable to the new key.

    4. Restart the application so it picks up the new key.

Models and fields affected:
    - auth_app.User: _email_encrypted
    - clients.ClientFile: _first_name_encrypted, _preferred_name_encrypted,
      _middle_name_encrypted, _last_name_encrypted, _birth_date_encrypted,
      _phone_encrypted, _email_encrypted
    - clients.ClientDetailValue: _value_encrypted (all rows, not just sensitive)
    - notes.ProgressNote: _notes_text_encrypted, _summary_encrypted,
      _participant_reflection_encrypted, _participant_suggestion_encrypted
    - notes.ProgressNoteTarget: _notes_encrypted, _client_words_encrypted
    - registration.RegistrationSubmission: _first_name_encrypted,
      _last_name_encrypted, _email_encrypted, _phone_encrypted
    - portal.ParticipantUser: _email_encrypted, _totp_secret_encrypted
"""

from cryptography.fernet import Fernet, InvalidToken
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# Registry of (model_class, [encrypted_field_names])
def _get_encrypted_models():
    """Import models lazily to avoid app-registry issues."""
    from apps.auth_app.models import User
    from apps.clients.models import ClientDetailValue, ClientFile
    from apps.notes.models import ProgressNote, ProgressNoteTarget

    models = [
        (User, ["_email_encrypted"]),
        (ClientFile, [
            "_first_name_encrypted",
            "_preferred_name_encrypted",
            "_middle_name_encrypted",
            "_last_name_encrypted",
            "_birth_date_encrypted",
            "_phone_encrypted",
            "_email_encrypted",
        ]),
        (ClientDetailValue, ["_value_encrypted"]),
        (ProgressNote, [
            "_notes_text_encrypted",
            "_summary_encrypted",
            "_participant_reflection_encrypted",
            "_participant_suggestion_encrypted",
        ]),
        (ProgressNoteTarget, ["_notes_encrypted", "_client_words_encrypted"]),
    ]

    try:
        from apps.registration.models import RegistrationSubmission
        models.append((RegistrationSubmission, [
            "_first_name_encrypted",
            "_last_name_encrypted",
            "_email_encrypted",
            "_phone_encrypted",
        ]))
    except ImportError:
        pass

    try:
        from apps.portal.models import ParticipantUser
        models.append((ParticipantUser, [
            "_email_encrypted",
            "_totp_secret_encrypted",
        ]))
    except ImportError:
        pass

    return models


def _validate_fernet_key(key_str, label):
    """Validate that a string is a valid Fernet key. Raises CommandError if not."""
    try:
        Fernet(key_str.encode() if isinstance(key_str, str) else key_str)
    except Exception as exc:
        raise CommandError(f"Invalid {label}: {exc}")


def _re_encrypt_bytes(raw_bytes, old_fernet, new_fernet):
    """Decrypt with old key and re-encrypt with new key. Returns new ciphertext bytes."""
    if isinstance(raw_bytes, memoryview):
        raw_bytes = bytes(raw_bytes)
    plaintext = old_fernet.decrypt(raw_bytes)
    return new_fernet.encrypt(plaintext)


class Command(BaseCommand):
    help = "Re-encrypt all PII fields from an old Fernet key to a new one."

    def add_arguments(self, parser):
        parser.add_argument(
            "--old-key", required=True,
            help="The current (old) Fernet key.",
        )
        parser.add_argument(
            "--new-key", required=True,
            help="The new Fernet key to rotate to.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Count records that would be re-encrypted without saving.",
        )

    def handle(self, *args, **options):
        old_key = options["old_key"]
        new_key = options["new_key"]
        dry_run = options["dry_run"]

        # Validate keys before touching any data.
        _validate_fernet_key(old_key, "old key")
        _validate_fernet_key(new_key, "new key")

        if old_key == new_key:
            raise CommandError("Old key and new key are the same — nothing to rotate.")

        old_fernet = Fernet(old_key.encode())
        new_fernet = Fernet(new_key.encode())

        encrypted_models = _get_encrypted_models()

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — no changes will be saved ===\n"))

        with transaction.atomic():
            for model_class, field_names in encrypted_models:
                model_label = model_class._meta.label
                total = model_class.objects.count()
                re_encrypted_count = 0
                skipped_count = 0
                error_count = 0

                for obj in model_class.objects.all().iterator():
                    fields_changed = False

                    for field_name in field_names:
                        raw = getattr(obj, field_name)

                        # Handle memoryview
                        if isinstance(raw, memoryview):
                            raw = bytes(raw)

                        # Skip empty / null fields
                        if not raw or raw == b"":
                            skipped_count += 1
                            continue

                        try:
                            new_value = _re_encrypt_bytes(raw, old_fernet, new_fernet)
                            if not dry_run:
                                setattr(obj, field_name, new_value)
                                fields_changed = True
                        except InvalidToken:
                            error_count += 1
                            self.stderr.write(
                                self.style.ERROR(
                                    f"  Could not decrypt {model_label} pk={obj.pk} "
                                    f"field={field_name} — skipping."
                                )
                            )

                    if fields_changed and not dry_run:
                        # Save only the encrypted columns to avoid triggering
                        # auto_now or other side-effects on unrelated fields.
                        obj.save(update_fields=field_names)
                        re_encrypted_count += 1
                    elif dry_run and not error_count:
                        # In dry-run mode, count rows that have at least one
                        # non-empty encrypted field.
                        has_data = any(
                            _has_encrypted_data(getattr(obj, fn))
                            for fn in field_names
                        )
                        if has_data:
                            re_encrypted_count += 1

                # Summary for this model
                verb = "Would re-encrypt" if dry_run else "Re-encrypted"
                self.stdout.write(
                    f"  {verb} {re_encrypted_count} of {total} {model_label} records."
                )
                if skipped_count:
                    self.stdout.write(f"    (Skipped {skipped_count} empty fields.)")
                if error_count:
                    self.stdout.write(
                        self.style.ERROR(f"    {error_count} decryption errors — those fields were NOT changed.")
                    )

            # Verify record counts are unchanged (sanity check).
            for model_class, _ in encrypted_models:
                post_count = model_class.objects.count()
                self.stdout.write(f"  {model_class._meta.label} count after: {post_count}")

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    "\nDry run complete. No data was modified."
                ))
                # Roll back the transaction (nothing changed, but be explicit).
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS(
                    "\nKey rotation complete. "
                    "Update FIELD_ENCRYPTION_KEY to the new key and restart the application."
                ))


def _has_encrypted_data(raw):
    """Return True if the field contains encrypted data (non-empty bytes)."""
    if isinstance(raw, memoryview):
        raw = bytes(raw)
    return bool(raw and raw != b"")
