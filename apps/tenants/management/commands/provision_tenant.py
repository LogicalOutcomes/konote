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

        name = options["name"]
        short_code = options["short_code"]
        domain = options["domain"]
        admin_username = options["admin_username"]
        admin_password = options.get("admin_password")
        schema_name = short_code.replace("-", "_")

        if not admin_password:
            admin_password = getpass.getpass("Admin password: ")
            if not admin_password:
                raise CommandError("Admin password is required.")

        self.stdout.write(f"Provisioning agency '{name}' (schema: {schema_name})...")

        # Step 1: Create or reuse the tenant row.
        agency, created = Agency.objects.get_or_create(
            short_code=short_code,
            defaults={"name": name, "schema_name": schema_name},
        )
        if agency.schema_name != schema_name:
            raise CommandError(
                f"Agency '{short_code}' already exists with schema '{agency.schema_name}', "
                f"expected '{schema_name}'. Resolve the mismatch before rerunning.",
            )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  Schema '{agency.schema_name}' created."))
        else:
            updated_fields = []
            if agency.name != name:
                agency.name = name
                updated_fields.append("name")
            if updated_fields:
                agency.save(update_fields=updated_fields)
            self.stdout.write(self.style.WARNING(f"  Schema '{agency.schema_name}' already exists; reusing tenant."))

        # Step 2: Create or reuse domain routing.
        domain_record, domain_created = AgencyDomain.objects.get_or_create(
            domain=domain,
            defaults={"tenant": agency, "is_primary": True},
        )
        if domain_record.tenant_id != agency.pk:
            raise CommandError(
                f"Domain '{domain}' already belongs to tenant '{domain_record.tenant.short_code}'. "
                "Resolve the domain conflict before rerunning.",
            )
        if not domain_record.is_primary:
            domain_record.is_primary = True
            domain_record.save(update_fields=["is_primary"])
        if domain_created:
            self.stdout.write(self.style.SUCCESS(f"  Domain '{domain}' configured."))
        else:
            self.stdout.write(self.style.WARNING(f"  Domain '{domain}' already exists; keeping it attached to this tenant."))

        # Step 3: Create or reuse the tenant encryption key.
        tenant_key, key_created = TenantKey.objects.get_or_create(
            tenant=agency,
            defaults={"encrypted_key": self._generate_encrypted_tenant_key(settings.FIELD_ENCRYPTION_KEY)},
        )
        if key_created:
            self.stdout.write(self.style.SUCCESS("  Encryption key generated and stored."))
        else:
            self.stdout.write(self.style.WARNING("  Encryption key already exists; reusing existing key."))

        # Step 4: Create or update the admin user within the tenant schema.
        self._run_tenant_phase(
            agency,
            "admin user creation",
            lambda: self._ensure_admin_user(admin_username, admin_password, name),
        )

        # Step 5: Load default configuration.
        self._run_tenant_phase(
            agency,
            "default configuration",
            lambda: self._load_defaults(),
        )

        # Output summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Agency provisioned successfully!"))
        self.stdout.write(f"  Name:    {name}")
        self.stdout.write(f"  Schema:  {agency.schema_name}")
        self.stdout.write(f"  Domain:  {domain}")
        self.stdout.write(f"  Admin:   {admin_username}")
        self.stdout.write(f"  URL:     https://{domain}/")

    def _generate_encrypted_tenant_key(self, master_key_string):
        """Generate one tenant key encrypted by the current master key."""
        tenant_fernet_key = Fernet.generate_key()
        master_keys = [key.strip() for key in master_key_string.split(",") if key.strip()]
        master_key = master_keys[0].encode() if isinstance(master_keys[0], str) else master_keys[0]
        master_fernet = Fernet(master_key)
        return master_fernet.encrypt(tenant_fernet_key)

    def _run_tenant_phase(self, agency, phase_name, callback):
        """Run one tenant-scoped phase and always restore the public schema."""
        from django.db import connection

        connection.set_tenant(agency)
        try:
            return callback()
        except Exception as exc:
            raise CommandError(
                f"Provisioning stopped during {phase_name} for tenant '{agency.short_code}'. "
                "Fix the underlying issue and rerun the same command to resume. "
                f"Original error: {exc}",
            ) from exc
        finally:
            connection.set_schema_to_public()

    def _ensure_admin_user(self, admin_username, admin_password, agency_name):
        """Create the tenant admin on first run, or refresh it on rerun."""
        from apps.auth_app.models import User

        admin_defaults = {
            "display_name": f"{agency_name} Admin",
            "is_admin": True,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }
        admin_user, created = User.objects.get_or_create(
            username=admin_username,
            defaults=admin_defaults,
        )
        changed = []
        for field, value in admin_defaults.items():
            if getattr(admin_user, field) != value:
                setattr(admin_user, field, value)
                changed.append(field)
        admin_user.set_password(admin_password)
        changed.append("password")
        admin_user.save(update_fields=changed)
        if created:
            self.stdout.write(self.style.SUCCESS(f"  Admin user '{admin_username}' created."))
        else:
            self.stdout.write(self.style.WARNING(f"  Admin user '{admin_username}' already exists; refreshed privileges and password."))

    def _load_defaults(self):
        """Load default terminology, feature toggles, and settings."""
        from apps.admin_settings.models import (
            FeatureToggle,
            TerminologyOverride,
        )

        # Default terminology (use KoNote defaults)
        defaults = [
            ("client", "Participant", "Participant(e)"),
            ("client_plural", "Participants", "Participant(e)s"),
            ("worker", "Worker", "Intervenant(e)"),
            ("worker_plural", "Workers", "Intervenant(e)s"),
            ("program", "Program", "Programme"),
            ("program_plural", "Programs", "Programmes"),
        ]
        for term_key, en, fr in defaults:
            TerminologyOverride.objects.get_or_create(
                term_key=term_key,
                defaults={"display_value": en, "display_value_fr": fr},
            )

        # Default feature toggles
        FeatureToggle.objects.get_or_create(
            feature_key="programs", defaults={"is_enabled": True},
        )
        FeatureToggle.objects.get_or_create(
            feature_key="portal", defaults={"is_enabled": False},
        )
        FeatureToggle.objects.get_or_create(
            feature_key="portal_alliance_ratings", defaults={"is_enabled": False},
        )

        self.stdout.write(self.style.SUCCESS("  Default configuration loaded."))
