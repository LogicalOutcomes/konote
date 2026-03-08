"""Helpers for assigning safe default CIDS metadata.

These defaults are registration metadata, not full taxonomy classification.
They ensure KoNote can generate stable local identifiers and basic provenance
for targets and metrics even when no external mapping has been reviewed yet.
"""

from apps.admin_settings.models import OrganizationProfile


GIIN_URI = "https://iris.thegiin.org"


def build_local_cids_uri(kind, object_id):
    """Return a stable local URI for a KoNote-managed CIDS entity."""
    return f"urn:konote:{kind}:{object_id}"


def is_local_konote_cids_uri(value):
    """Return True when a URI is KoNote's local fallback identifier."""
    return str(value or "").startswith("urn:konote:")


def _local_org_uri():
    org = OrganizationProfile.get_solo()
    return build_local_cids_uri("organization", org.pk or 1)


def apply_metric_cids_defaults(metric):
    """Populate deterministic registration defaults for a MetricDefinition.

    This helper intentionally limits itself to immediate, low-burden metadata:
    a stable local identifier, a plain-language unit carry-through, and basic
    provenance. It does not infer IRIS+, SDG, Common Approach theme, or other
    report-time classifications.

    External mappings remain optional. If an IRIS+ code exists because a human
    explicitly selected it, the metric is marked as defined by GIIN. Otherwise,
    it is defined locally by the current organisation.
    """
    changed_fields = []

    if metric.pk and not metric.cids_indicator_uri:
        metric.cids_indicator_uri = build_local_cids_uri("indicator-definition", metric.pk)
        changed_fields.append("cids_indicator_uri")

    if not metric.cids_unit_description and metric.unit:
        metric.cids_unit_description = metric.unit.strip()
        changed_fields.append("cids_unit_description")

    if not metric.cids_defined_by:
        metric.cids_defined_by = GIIN_URI if metric.iris_metric_code else _local_org_uri()
        changed_fields.append("cids_defined_by")

    return changed_fields


def apply_target_cids_defaults(target):
    """Populate deterministic registration metadata for a PlanTarget.

    This helper assigns only a stable local outcome identifier. Any later
    taxonomy classification belongs in the admin reporting workflow.
    """
    changed_fields = []

    if target.pk and not target.cids_outcome_uri:
        target.cids_outcome_uri = build_local_cids_uri("outcome-definition", target.pk)
        changed_fields.append("cids_outcome_uri")

    return changed_fields