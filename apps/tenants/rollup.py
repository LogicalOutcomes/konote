"""Rollup aggregation for consortium reporting.

Reads PublishedReport records from each tenant schema and aggregates
them into a ConsortiumRollup in the shared schema.

Uses django-tenants schema_context() to safely iterate across schemas.
"""
from collections import defaultdict

from django.db import connection
from django_tenants.utils import schema_context

from apps.tenants.models import Agency, Consortium, ConsortiumRollup


def aggregate_consortium(consortium_id, period_start, period_end):
    """Aggregate published reports for a consortium into a rollup.

    Iterates over all active agencies, finds PublishedReport records
    matching the consortium and period, and combines their data.

    Args:
        consortium_id: PK of the Consortium
        period_start: date - start of reporting period
        period_end: date - end of reporting period

    Returns:
        ConsortiumRollup instance (created or updated)
    """
    consortium = Consortium.objects.get(pk=consortium_id)
    agencies = Agency.objects.filter(is_active=True)

    all_reports = []
    for agency in agencies:
        reports = _get_published_reports(
            agency.schema_name, consortium_id, period_start, period_end
        )
        if reports:
            all_reports.extend(reports)

    if not all_reports:
        return None

    # Count distinct agencies that contributed
    agency_schemas = {r["schema"] for r in all_reports}

    # Aggregate
    aggregated = _merge_reports([r["data"] for r in all_reports])
    total_participants = sum(
        r["data"].get("service_stats", {}).get("total_clients", 0)
        for r in all_reports
    )

    rollup, _ = ConsortiumRollup.objects.update_or_create(
        consortium=consortium,
        period_start=period_start,
        period_end=period_end,
        defaults={
            "agency_count": len(agency_schemas),
            "participant_count": total_participants,
            "data_json": aggregated,
        },
    )
    return rollup


def _get_published_reports(schema_name, consortium_id, period_start, period_end):
    """Get PublishedReport records from a tenant schema."""
    # Import here to avoid circular imports
    from apps.consortia.models import ConsortiumMembership, PublishedReport

    results = []
    with schema_context(schema_name):
        memberships = ConsortiumMembership.objects.filter(
            consortium_id=consortium_id, is_active=True
        )
        for membership in memberships:
            reports = PublishedReport.objects.filter(
                membership=membership,
                period_start__gte=period_start,
                period_end__lte=period_end,
            )
            for report in reports:
                results.append({
                    "schema": schema_name,
                    "data": report.data_json,
                })
    return results


def _merge_reports(report_data_list):
    """Merge multiple published report data dicts into one aggregate.

    Service stats: summed
    Demographics: counts summed per label
    Outcomes: weighted average by n
    """
    merged = {
        "service_stats": {},
        "demographics": {},
        "outcomes": {},
    }

    # Service stats — sum across reports
    stat_keys = ["total_clients", "total_sessions", "new_clients", "returning_clients"]
    for key in stat_keys:
        merged["service_stats"][key] = sum(
            r.get("service_stats", {}).get(key, 0)
            for r in report_data_list
            if isinstance(r.get("service_stats", {}).get(key, 0), (int, float))
        )

    # Demographics — sum counts per label per category
    demo_totals = defaultdict(lambda: defaultdict(int))
    for report in report_data_list:
        for category, rows in report.get("demographics", {}).items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                label = row.get("label", "")
                count = row.get("count", 0)
                # Skip suppressed values (strings like "< 5")
                if isinstance(count, (int, float)):
                    demo_totals[category][label] += count

    for category, label_counts in demo_totals.items():
        merged["demographics"][category] = [
            {"label": label, "count": count}
            for label, count in sorted(label_counts.items())
        ]

    # Outcomes — weighted average
    outcome_agg = defaultdict(lambda: {"total_value": 0, "total_n": 0})
    for report in report_data_list:
        for metric_key, metric_data in report.get("outcomes", {}).items():
            if not isinstance(metric_data, dict):
                continue
            n = metric_data.get("n", 0) or 0
            avg = metric_data.get("average") or metric_data.get("change")
            if isinstance(avg, (int, float)) and isinstance(n, (int, float)) and n > 0:
                outcome_agg[metric_key]["total_value"] += avg * n
                outcome_agg[metric_key]["total_n"] += n

    for metric_key, agg in outcome_agg.items():
        if agg["total_n"] > 0:
            merged["outcomes"][metric_key] = {
                "average": round(agg["total_value"] / agg["total_n"], 2),
                "n": agg["total_n"],
            }
        else:
            merged["outcomes"][metric_key] = {"average": None, "n": 0}

    return merged
