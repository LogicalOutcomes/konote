"""Shared-schema models for multi-tenancy.

These models live in the public PostgreSQL schema (shared across all tenants):
- Agency: the tenant model (one per agency)
- AgencyDomain: domain routing for each agency
- TenantKey: per-agency Fernet encryption key (encrypted by master key)
- Consortium: cross-agency groups for funder reporting
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.models import DomainMixin, TenantMixin


class Agency(TenantMixin):
    """An agency (tenant). Each agency gets its own PostgreSQL schema.

    The schema_name field is inherited from TenantMixin and determines
    the PostgreSQL schema used for this agency's data.
    """

    name = models.CharField(max_length=255)
    short_code = models.SlugField(
        max_length=63, unique=True,
        help_text=_("URL-safe identifier, e.g. 'youth-services'. Used as schema name."),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # django-tenants auto-creates the schema on save
    auto_create_schema = True

    class Meta:
        app_label = "tenants"
        db_table = "agencies"
        verbose_name_plural = "agencies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Use short_code as the schema name (e.g. "youth_services")
        if not self.schema_name:
            self.schema_name = self.short_code.replace("-", "_")
        super().save(*args, **kwargs)


class AgencyDomain(DomainMixin):
    """Domain (subdomain) routing for an agency.

    Each agency has at least one domain entry, e.g.:
    - youth-services.konote.ca (production)
    - youth-services.localhost (local dev)
    """

    class Meta:
        app_label = "tenants"
        db_table = "agency_domains"

    def __str__(self):
        return f"{self.domain} → {self.tenant.name}"


class TenantKey(models.Model):
    """Per-agency Fernet encryption key, encrypted by the master key.

    The encrypted_key field stores the agency's Fernet key, itself encrypted
    using the master FIELD_ENCRYPTION_KEY (from env var). This is a proper
    key encryption key (KEK) pattern:

    1. Master key (env var) encrypts/decrypts tenant keys
    2. Tenant key encrypts/decrypts tenant PII

    Benefits:
    - Adding a new agency doesn't require restarting the app
    - Key rotation is per-agency (no cross-agency impact)
    - Deleting a tenant's key makes their PII permanently unrecoverable
    """

    tenant = models.OneToOneField(
        Agency, on_delete=models.CASCADE, related_name="encryption_key",
    )
    encrypted_key = models.BinaryField(
        help_text="Agency's Fernet key, encrypted by the master FIELD_ENCRYPTION_KEY.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "tenants"
        db_table = "tenant_keys"

    def __str__(self):
        return f"Key for {self.tenant.name} (created {self.created_at})"


class Consortium(models.Model):
    """A funder or network that multiple agencies report to.

    Lives in the shared schema because it's cross-tenant by definition.
    DO NOT move this to the consortia app — see DRR anti-pattern.

    Consortium members (ConsortiumMembership) live in tenant schemas
    because each agency manages its own membership status.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tenants"
        db_table = "consortia"
        verbose_name_plural = "consortia"

    def __str__(self):
        return self.name
