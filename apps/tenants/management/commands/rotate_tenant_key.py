"""Rotate a tenant's encryption key.

This command is intentionally disabled until a safe transactional re-encryption
workflow exists for tenant data.

Usage:
    python manage.py rotate_tenant_key --short-code youth-services
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Disabled: tenant key rotation is not safe yet because existing encrypted "
        "data is not re-encrypted automatically."
    )

    def add_arguments(self, parser):
        parser.add_argument("--short-code", required=True, help="Agency short code (slug)")
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")

    def handle(self, *args, **options):
        short_code = options["short_code"]
        dry_run = options["dry_run"]
        mode = "DRY RUN" if dry_run else "LIVE RUN"

        raise CommandError(
            f"rotate_tenant_key is disabled ({mode}) for agency '{short_code}'. "
            "A safe tenant-wide re-encryption workflow has not been implemented yet, "
            "so rotating the stored key would strand existing encrypted data."
        )
