"""Tenant-scoped models for consortium data sharing.

These models live in each tenant's schema. They track an agency's
participation in consortia and what data it shares.

The Consortium model itself lives in the shared schema (tenants app)
because it's cross-tenant. DO NOT move it here — see DRR anti-pattern.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ConsortiumMembership(models.Model):
    """Links this agency to a consortium.

    Each agency manages its own membership records in its own schema.
    The consortium_id is a plain integer FK to the shared Consortium table.
    """

    # Integer FK to shared-schema Consortium (cross-schema FK)
    consortium_id = models.IntegerField(
        help_text="FK to tenants.Consortium in the shared schema.",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "consortia"
        db_table = "consortium_memberships"

    def __str__(self):
        return f"Membership in consortium #{self.consortium_id}"

    @property
    def consortium(self):
        """Lazy-load the Consortium from the shared schema."""
        from apps.tenants.models import Consortium
        try:
            return Consortium.objects.get(pk=self.consortium_id)
        except Consortium.DoesNotExist:
            return None


class ProgramSharing(models.Model):
    """Per-program consent to share data with a consortium.

    Sharing is per-program, not per-agency — one agency may share
    youth program data with Funder A but not addiction services data.
    """

    membership = models.ForeignKey(
        ConsortiumMembership, on_delete=models.CASCADE, related_name="program_shares",
    )
    program = models.ForeignKey(
        "programs.Program", on_delete=models.CASCADE, related_name="consortium_shares",
    )
    # What metrics/data this program shares
    metrics_shared = models.JSONField(
        default=list, blank=True,
        help_text="List of metric definition IDs shared with this consortium.",
    )
    date_from = models.DateField(
        help_text="Data shared from this date onward.",
    )
    date_to = models.DateField(
        null=True, blank=True,
        help_text="Data shared until this date. Null = ongoing.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "consortia"
        db_table = "program_sharing"
        unique_together = ("membership", "program")

    def __str__(self):
        return f"{self.program} → consortium #{self.membership.consortium_id}"


class PublishedReport(models.Model):
    """Aggregate report snapshot published to a consortium.

    Stores de-identified aggregate data only — never individual
    participant records. Cell suppression (n<5) must be applied
    before publishing.
    """

    membership = models.ForeignKey(
        ConsortiumMembership, on_delete=models.CASCADE, related_name="published_reports",
    )
    title = models.CharField(max_length=255)
    period_start = models.DateField()
    period_end = models.DateField()
    data_json = models.JSONField(
        help_text="Aggregate report data (de-identified, n<5 cells suppressed).",
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "consortia"
        db_table = "published_reports"
        ordering = ["-published_at"]

    def __str__(self):
        return f"{self.title} ({self.period_start} – {self.period_end})"
