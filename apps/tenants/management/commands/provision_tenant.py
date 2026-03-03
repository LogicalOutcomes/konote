"""Provision a new agency tenant end-to-end.

Creates: PostgreSQL schema, runs migrations, generates encryption key,
creates admin user, loads default config, sets up domain routing.

Usage:
    python manage.py provision_tenant \\
        --name "Youth Services Agency" \\
        --short-code youth-services \\
        --domain youth-services.konote.ca \\
        --admin-username admin \\
        --admin-password <secure-password>
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = "Provision a new agency tenant with schema, encryption key, admin user, and domain."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Agency display name")
        parser.add_argument("--short-code", required=True, help="URL-safe slug (e.g. youth-services)")
        parser.add_argument("--domain", required=True, help="Domain for this agency (e.g. youth-services.konote.ca)")
        parser.add_argument("--admin-username", default="admin", help="Admin username (default: admin)")
        parser.add_argument("--admin-password", help="Admin password (prompted if not given)")
        parser.add_argument("--no-demo-data", action="store_true", help="Skip loading demo/seed data")

    def handle(self, *args, **options):
        import getpass

        from django.conf import settings
        from django.db import connection

        from apps.tenants.models import Agency, AgencyDomain, TenantKey
        from konote.encryption import encrypt_field

        name = options["name"]
        short_code = options["short_code"]
        domain = options["domain"]
        admin_username = options["admin_username"]
        admin_password = options.get("admin_password")

        if not admin_password:
            admin_password = getpass.getpass("Admin password: ")
            if not admin_password:
                raise CommandError("Admin password is required.")

        # Step 1: Create agency (this also creates the schema via django-tenants)
        self.stdout.write(f"Creating agency '{name}' (schema: {short_code.replace('-', '_')})...")
        agency = Agency(
            name=name,
            short_code=short_code,
            schema_name=short_code.replace("-", "_"),
        )
        agency.save()
        self.stdout.write(self.style.SUCCESS(f"  Schema '{agency.schema_name}' created."))

        # Step 2: Set up domain routing
        AgencyDomain.objects.create(
            domain=domain,
            tenant=agency,
            is_primary=True,
        )
        self.stdout.write(self.style.SUCCESS(f"  Domain '{domain}' configured."))

        # Step 3: Generate per-tenant encryption key
        tenant_fernet_key = Fernet.generate_key()
        # Encrypt the tenant key with the master key
        master_key_string = settings.FIELD_ENCRYPTION_KEY
        master_keys = [k.strip() for k in master_key_string.split(",") if k.strip()]
        master_fernet = Fernet(master_keys[0].encode() if isinstance(master_keys[0], str) else master_keys[0])
        encrypted_tenant_key = master_fernet.encrypt(tenant_fernet_key)

        TenantKey.objects.create(
            tenant=agency,
            encrypted_key=encrypted_tenant_key,
        )
        self.stdout.write(self.style.SUCCESS("  Encryption key generated and stored."))

        # Step 4: Create admin user within the tenant schema
        connection.set_tenant(agency)
        try:
            from apps.auth_app.models import User
            admin_user = User.objects.create_superuser(
                username=admin_username,
                password=admin_password,
                display_name=f"{name} Admin",
            )
            self.stdout.write(self.style.SUCCESS(f"  Admin user '{admin_username}' created."))
        finally:
            # Reset to public schema
            connection.set_schema_to_public()

        # Step 5: Load default configuration
        connection.set_tenant(agency)
        try:
            self._load_defaults(agency)
        finally:
            connection.set_schema_to_public()

        # Output summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Agency provisioned successfully!"))
        self.stdout.write(f"  Name:    {name}")
        self.stdout.write(f"  Schema:  {agency.schema_name}")
        self.stdout.write(f"  Domain:  {domain}")
        self.stdout.write(f"  Admin:   {admin_username}")
        self.stdout.write(f"  URL:     https://{domain}/")

    def _load_defaults(self, agency):
        """Load default terminology, feature toggles, and settings."""
        from apps.admin_settings.models import (
            FeatureToggle,
            InstanceSetting,
            TerminologyOverride,
        )

        # Default terminology (use KoNote defaults)
        defaults = [
            ("client", "Participant", "Participant·e"),
            ("clients", "Participants", "Participant·e·s"),
            ("worker", "Worker", "Intervenant·e"),
            ("workers", "Workers", "Intervenant·e·s"),
            ("program", "Program", "Programme"),
            ("programs", "Programs", "Programmes"),
        ]
        for term, en, fr in defaults:
            TerminologyOverride.objects.get_or_create(
                term=term, defaults={"custom_value": en, "custom_value_fr": fr},
            )

        # Default feature toggles
        FeatureToggle.objects.get_or_create(
            name="programs", defaults={"is_enabled": True},
        )
        FeatureToggle.objects.get_or_create(
            name="portal", defaults={"is_enabled": False},
        )

        self.stdout.write(self.style.SUCCESS("  Default configuration loaded."))
