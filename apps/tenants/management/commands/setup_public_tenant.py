"""Bootstrap a single-agency deployment that stores data in the 'public' schema.

Used when upgrading an existing single-tenant (flat) deployment to the
django-tenants architecture.  All data is already in PostgreSQL's default
'public' schema; this command creates the Agency and AgencyDomain records
that TenantMainMiddleware needs to route web requests correctly, without
moving any data.

Running this command on an already-provisioned deployment is safe: it exits
immediately if an AgencyDomain for the given domain already exists.

Usage:
    python manage.py setup_public_tenant --domain konote.logicaloutcomes.net
    python manage.py setup_public_tenant --domain konote.logicaloutcomes.net \\
        --name "My Agency" --short-code my-agency
"""
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Bootstrap single-agency deployments: create an Agency + AgencyDomain "
        "that points to the existing 'public' PostgreSQL schema. Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            default=os.environ.get("ALLOWED_HOSTS", "").split(",")[0].strip(),
            help="Primary domain for this agency (e.g. konote.logicaloutcomes.net). "
                 "Defaults to the first value in ALLOWED_HOSTS.",
        )
        parser.add_argument(
            "--name",
            default="KoNote",
            help="Agency display name (default: KoNote)",
        )
        parser.add_argument(
            "--short-code",
            default="public",
            help="URL-safe slug — used as the PostgreSQL schema name. "
                 "Must be 'public' for this bootstrap command (default: public).",
        )

    def handle(self, *args, **options):
        from apps.tenants.models import Agency, AgencyDomain

        domain = options["domain"]
        name = options["name"]
        short_code = options["short_code"]
        schema_name = "public"  # always target the existing public schema

        if not domain:
            self.stderr.write(
                self.style.ERROR(
                    "No domain specified and ALLOWED_HOSTS is not set. "
                    "Re-run with --domain <your-domain>."
                )
            )
            return

        # Idempotent: skip if this domain is already registered.
        if AgencyDomain.objects.filter(domain=domain).exists():
            self.stdout.write(
                f"Domain '{domain}' is already registered — nothing to do."
            )
            return

        # Check whether a 'public' agency already exists (rare edge case where
        # the agency was created but the domain insert failed).
        agency = Agency.objects.filter(schema_name=schema_name).first()
        if not agency:
            self.stdout.write(
                f"Creating agency '{name}' (schema: {schema_name})..."
            )
            agency = Agency(
                name=name,
                short_code=short_code,
                schema_name=schema_name,
            )
            # Disable auto-create: the 'public' schema already exists.
            agency.auto_create_schema = False
            agency.save()
            self.stdout.write(self.style.SUCCESS(f"  Agency '{name}' created."))
        else:
            self.stdout.write(
                f"Reusing existing agency '{agency.name}' (schema: {schema_name})."
            )

        AgencyDomain.objects.create(
            domain=domain,
            tenant=agency,
            is_primary=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"  Domain '{domain}' registered.")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Setup complete. Site is accessible at https://{domain}/"
            )
        )
