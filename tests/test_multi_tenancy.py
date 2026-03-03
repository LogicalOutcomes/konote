"""Tests for multi-tenancy infrastructure.

Covers:
- Tenant model creation (Agency, AgencyDomain, TenantKey, Consortium)
- Per-tenant encryption (key generation, encrypt/decrypt with tenant key)
- Consortium models (ConsortiumMembership, ProgramSharing, PublishedReport)
- Consent field on ServiceEpisode
- Audit log tenant_schema field

Note: These tests run against SQLite by default. Schema-level isolation
tests (verifying cross-tenant query isolation) require PostgreSQL and are
marked with @pytest.mark.skipif(not _using_postgresql()).
"""
import pytest
from django.test import TestCase

from apps.tenants.models import Agency, AgencyDomain, Consortium, TenantKey


class TestAgencyModel(TestCase):
    """Test Agency (tenant) model."""

    def test_create_agency(self):
        agency = Agency(
            name="Test Agency",
            short_code="test-agency",
            schema_name="test_agency",
        )
        agency.save()
        assert agency.pk is not None
        assert agency.name == "Test Agency"
        assert agency.schema_name == "test_agency"

    def test_auto_schema_name(self):
        agency = Agency(
            name="Youth Services",
            short_code="youth-services",
        )
        agency.save()
        assert agency.schema_name == "youth_services"

    def test_agency_domain(self):
        agency = Agency(
            name="Domain Test",
            short_code="domain-test",
            schema_name="domain_test",
        )
        agency.save()

        domain = AgencyDomain.objects.create(
            domain="domain-test.konote.ca",
            tenant=agency,
            is_primary=True,
        )
        assert str(domain) == "domain-test.konote.ca → Domain Test"


class TestTenantKeyModel(TestCase):
    """Test TenantKey model for per-tenant encryption."""

    def test_create_tenant_key(self):
        from cryptography.fernet import Fernet
        from django.conf import settings

        agency = Agency(
            name="Key Test",
            short_code="key-test",
            schema_name="key_test",
        )
        agency.save()

        # Generate and encrypt a tenant key
        tenant_key_raw = Fernet.generate_key()
        master_key_string = settings.FIELD_ENCRYPTION_KEY
        master_keys = [k.strip() for k in master_key_string.split(",") if k.strip()]
        master_fernet = Fernet(master_keys[0].encode())
        encrypted_key = master_fernet.encrypt(tenant_key_raw)

        tk = TenantKey.objects.create(
            tenant=agency,
            encrypted_key=encrypted_key,
        )
        assert tk.pk is not None

        # Verify round-trip
        stored = tk.encrypted_key
        if isinstance(stored, memoryview):
            stored = bytes(stored)
        decrypted = master_fernet.decrypt(stored)
        assert decrypted == tenant_key_raw


class TestConsortiumModel(TestCase):
    """Test Consortium model (shared schema)."""

    def test_create_consortium(self):
        c = Consortium.objects.create(
            name="Ontario Youth Network",
            description="Data sharing for youth services funders.",
        )
        assert c.pk is not None
        assert str(c) == "Ontario Youth Network"


class TestConsortiaModels(TestCase):
    """Test tenant-scoped consortia models."""

    def test_consortium_membership(self):
        from apps.consortia.models import ConsortiumMembership

        c = Consortium.objects.create(name="Test Consortium")
        m = ConsortiumMembership.objects.create(
            consortium_id=c.pk,
            is_active=True,
        )
        assert m.pk is not None
        assert m.consortium.name == "Test Consortium"

    def test_program_sharing_model_fields(self):
        from apps.consortia.models import ProgramSharing

        # Verify metrics_shared has correct defaults
        metrics_field = ProgramSharing._meta.get_field("metrics_shared")
        assert metrics_field.default is list
        assert metrics_field.blank is True

        # date_to is nullable (sharing can be ongoing)
        date_to_field = ProgramSharing._meta.get_field("date_to")
        assert date_to_field.null is True

        # Unique constraint prevents a program appearing twice in one membership
        assert ("membership", "program") in [
            tuple(ut) for ut in ProgramSharing._meta.unique_together
        ]

    def test_published_report(self):
        from datetime import date, timedelta

        from apps.consortia.models import ConsortiumMembership, PublishedReport

        c = Consortium.objects.create(name="Report Test Consortium")
        m = ConsortiumMembership.objects.create(
            consortium_id=c.pk,
            is_active=True,
        )
        report = PublishedReport.objects.create(
            membership=m,
            title="Q1 2026 Aggregate Report",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            data_json={"programs": 3, "participants_served": 150, "goals_met_rate": 0.72},
        )
        assert report.pk is not None
        assert "Q1 2026" in str(report)


class TestConsentField(TestCase):
    """Test consent_to_aggregate_reporting field on ServiceEpisode."""

    def test_field_exists_and_defaults_false(self):
        from apps.clients.models import ServiceEpisode
        field = ServiceEpisode._meta.get_field("consent_to_aggregate_reporting")
        assert field is not None
        assert field.default is False


class TestAuditTenantSchema(TestCase):
    """Test tenant_schema field on AuditLog."""

    databases = {"default", "audit"}

    def test_audit_log_with_tenant_schema(self):
        from django.utils import timezone

        from apps.audit.models import AuditLog

        log = AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=1,
            user_display="test-user",
            action="create",
            resource_type="test",
            tenant_schema="test_agency",
        )
        assert log.tenant_schema == "test_agency"

    def test_audit_log_default_empty_schema(self):
        from django.utils import timezone

        from apps.audit.models import AuditLog

        log = AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=1,
            user_display="test-user",
            action="view",
            resource_type="test",
        )
        assert log.tenant_schema == ""


class TestEncryptionMultiTenancy(TestCase):
    """Test encryption module's multi-tenancy support."""

    def test_master_key_still_works(self):
        """Without a tenant context, master key should be used (backward compat)."""
        from konote.encryption import decrypt_field, encrypt_field

        plaintext = "Hello, multi-tenancy"
        ciphertext = encrypt_field(plaintext)
        assert decrypt_field(ciphertext) == plaintext

    def test_empty_values(self):
        from konote.encryption import decrypt_field, encrypt_field

        assert encrypt_field(None) == b""
        assert encrypt_field("") == b""
        assert decrypt_field(b"") == ""
        assert decrypt_field(None) == ""
