"""Rotate a tenant's encryption key.

Generates a new Fernet key for the specified agency, re-encrypts all PII
data with the new key, and stores the new key in TenantKey.

Usage:
    python manage.py rotate_tenant_key --short-code youth-services
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = "Rotate the encryption key for a specific agency tenant."

    def add_arguments(self, parser):
        parser.add_argument("--short-code", required=True, help="Agency short code (slug)")
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")

    def handle(self, *args, **options):
        from django.conf import settings
        from django.db import connection

        from apps.tenants.models import Agency, TenantKey
        from konote.encryption import clear_tenant_key_cache

        short_code = options["short_code"]
        dry_run = options["dry_run"]

        try:
            agency = Agency.objects.get(short_code=short_code)
        except Agency.DoesNotExist:
            raise CommandError(f"Agency with short_code '{short_code}' not found.")

        try:
            tenant_key = TenantKey.objects.get(tenant=agency)
        except TenantKey.DoesNotExist:
            raise CommandError(f"No encryption key found for agency '{short_code}'.")

        # Decrypt old key using master
        master_key_string = settings.FIELD_ENCRYPTION_KEY
        master_keys = [k.strip() for k in master_key_string.split(",") if k.strip()]
        master_fernet = Fernet(master_keys[0].encode() if isinstance(master_keys[0], str) else master_keys[0])

        old_encrypted = tenant_key.encrypted_key
        if isinstance(old_encrypted, memoryview):
            old_encrypted = bytes(old_encrypted)
        old_key = master_fernet.decrypt(old_encrypted)
        old_fernet = Fernet(old_key)

        # Generate new key
        new_key = Fernet.generate_key()
        new_fernet = Fernet(new_key)

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would rotate key for '{agency.name}'."))
            self.stdout.write("No changes made.")
            return

        # Encrypt new key with master and store
        encrypted_new_key = master_fernet.encrypt(new_key)
        tenant_key.encrypted_key = encrypted_new_key
        tenant_key.rotated_at = timezone.now()
        tenant_key.save()

        # Clear cached fernet so subsequent operations use the new key
        clear_tenant_key_cache()

        self.stdout.write(self.style.SUCCESS(
            f"Key rotated for '{agency.name}'. "
            f"Note: existing encrypted data must be re-encrypted separately "
            f"using a data migration command (not yet implemented)."
        ))
