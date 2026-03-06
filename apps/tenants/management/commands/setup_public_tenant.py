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

from django.core.management.base import BaseCommand, CommandError


def _pick_domain_from_allowed_hosts():
    """Return the best public domain from the ALLOWED_HOSTS env var.

    When multiple hosts are listed (e.g. the Azure Container Apps internal FQDN
    AND the custom public domain), pick the one that looks like a real custom
    domain by skipping *.azurecontainerapps.io, localhost, and bare IPs.
    Falls back to the first value if nothing better is found.
    """
    raw = os.environ.get("ALLOWED_HOSTS", "")
    candidates = [h.strip() for h in raw.split(",") if h.strip()]
    for candidate in candidates:
        if (
            candidate
            and not candidate.endswith(".azurecontainerapps.io")
            and candidate not in ("localhost", "127.0.0.1", "0.0.0.0")
            and not candidate.startswith(".")
        ):
            return candidate
    return candidates[0] if candidates else ""


class Command(BaseCommand):
    help = (
        "Bootstrap single-agency deployments: create an Agency + AgencyDomain "
        "that points to the existing 'public' PostgreSQL schema. Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            default=_pick_domain_from_allowed_hosts(),
            help="Primary domain for this agency (e.g. konote.logicaloutcomes.net). "
                 "Defaults to the best-matching value in ALLOWED_HOSTS (prefers "
                 "custom domains over *.azurecontainerapps.io).",
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
            raise CommandError(
                "No domain specified and ALLOWED_HOSTS is not set. "
                "Re-run with --domain <your-domain>."
            )

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

        # Register 'localhost' as a secondary domain so Docker health checks
        # (curl http://localhost:8000/auth/login/) can resolve to a tenant.
        if domain != "localhost" and not AgencyDomain.objects.filter(
            domain="localhost"
        ).exists():
            AgencyDomain.objects.create(
                domain="localhost",
                tenant=agency,
                is_primary=False,
            )
            self.stdout.write(
                "  Secondary domain 'localhost' registered (for health checks)."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Setup complete. Site is accessible at https://{domain}/"
            )
        )
