"""Encrypt field_values and migrate email hash to HMAC-SHA-256 (PRIV-M2, PRIV-M3).

Step 1: Add _field_values_encrypted column alongside the existing field_values.
Step 2: Data migration encrypts existing field_values and rehashes email_hash.
Step 3: Remove the old plaintext field_values column.
"""
import hashlib
import hmac
import json

from django.conf import settings
from django.db import migrations, models


def encrypt_field_values_and_rehash_emails(apps, schema_editor):
    """Migrate existing data: encrypt field_values, rehash email with HMAC."""
    # Use historical model (no property accessors available)
    RegistrationSubmission = apps.get_model("registration", "RegistrationSubmission")

    # Import encryption helpers directly
    from konote.encryption import decrypt_field, encrypt_field

    for sub in RegistrationSubmission.objects.all().iterator():
        changed = False

        # --- PRIV-M3: Encrypt field_values ---
        if sub.field_values:
            sub._field_values_encrypted = encrypt_field(json.dumps(sub.field_values))
            changed = True

        # --- PRIV-M2: Rehash email with HMAC-SHA-256 ---
        if sub._email_encrypted and sub.email_hash:
            try:
                email = decrypt_field(sub._email_encrypted)
                if email:
                    sub.email_hash = hmac.new(
                        settings.EMAIL_HASH_KEY.encode(),
                        email.lower().strip().encode(),
                        hashlib.sha256,
                    ).hexdigest()
                    changed = True
            except Exception:
                # If decryption fails, leave hash as-is
                pass

        if changed:
            sub.save(
                update_fields=[
                    f
                    for f in ["_field_values_encrypted", "email_hash"]
                    if f in {field.name for field in sub._meta.get_fields()}
                ]
            )


def reverse_encrypt_field_values(apps, schema_editor):
    """Reverse: decrypt field_values back to plaintext JSON field.

    Note: Email hashes cannot be reverted to plain SHA-256 because the
    original plain-SHA-256 values are not stored. This reverse only
    handles field_values.
    """
    RegistrationSubmission = apps.get_model("registration", "RegistrationSubmission")
    from konote.encryption import decrypt_field

    for sub in RegistrationSubmission.objects.all().iterator():
        if sub._field_values_encrypted:
            try:
                raw = decrypt_field(sub._field_values_encrypted)
                sub.field_values = json.loads(raw) if raw else {}
            except Exception:
                sub.field_values = {}
            sub.save(update_fields=["field_values"])


class Migration(migrations.Migration):

    dependencies = [
        ("registration", "0001_initial"),
    ]

    operations = [
        # Step 1: Add the encrypted column (keep old field_values for now)
        migrations.AddField(
            model_name="registrationsubmission",
            name="_field_values_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        # Step 2: Copy + encrypt field_values, rehash email hashes
        migrations.RunPython(
            encrypt_field_values_and_rehash_emails,
            reverse_encrypt_field_values,
        ),
        # Step 3: Remove the old plaintext column
        migrations.RemoveField(
            model_name="registrationsubmission",
            name="field_values",
        ),
    ]
