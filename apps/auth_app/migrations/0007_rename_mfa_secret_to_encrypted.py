"""Rename mfa_secret CharField to _mfa_secret_encrypted BinaryField.

Converts the plaintext MFA secret to Fernet-encrypted storage.
"""
from django.db import migrations, models

from konote.encryption import encrypt_field


def encrypt_existing_secrets(apps, schema_editor):
    """Encrypt any existing plaintext MFA secrets."""
    User = apps.get_model("auth_app", "User")
    for user in User.objects.filter(mfa_enabled=True).exclude(mfa_secret=""):
        # mfa_secret is still a CharField at this point in the migration
        plaintext = user.mfa_secret
        if plaintext:
            user._mfa_secret_encrypted = encrypt_field(plaintext)
            user.save(update_fields=["_mfa_secret_encrypted"])


def decrypt_existing_secrets(apps, schema_editor):
    """Reverse: decrypt secrets back to plaintext CharField."""
    from konote.encryption import decrypt_field
    User = apps.get_model("auth_app", "User")
    for user in User.objects.filter(mfa_enabled=True):
        ciphertext = user._mfa_secret_encrypted
        if ciphertext:
            user.mfa_secret = decrypt_field(ciphertext)
            user.save(update_fields=["mfa_secret"])


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0006_user_mfa_fields"),
    ]

    operations = [
        # 1. Add the new encrypted field
        migrations.AddField(
            model_name="user",
            name="_mfa_secret_encrypted",
            field=models.BinaryField(blank=True, default=b""),
        ),
        # 2. Copy and encrypt existing plaintext secrets
        migrations.RunPython(encrypt_existing_secrets, decrypt_existing_secrets),
        # 3. Remove the old plaintext field
        migrations.RemoveField(
            model_name="user",
            name="mfa_secret",
        ),
    ]
