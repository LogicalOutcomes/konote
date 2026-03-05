"""Consortium dashboard views.

Provides the funder/consortium lead view of aggregated data across
partner agencies. Permission tiers:
- is_consortium_lead on ConsortiumMembership: full network view
- Regular staff: agency-only view (their own published data)
"""
import csv
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.consortia.models import ConsortiumMembership, PublishedReport
from apps.tenants.models import Consortium, ConsortiumRollup


@login_required
def dashboard(request, consortium_id):
    """Main consortium dashboard page.

    Shows aggregated data from the most recent rollup, with charts
    and demographic breakdowns.
    """
    consortium = get_object_or_404(Consortium, pk=consortium_id)
    membership = _get_membership(request, consortium_id)
    is_lead = membership and getattr(membership, "is_consortium_lead", False)

    # Get most recent rollup
    rollup = ConsortiumRollup.objects.filter(
        consortium=consortium,
    ).first()

    # Get this agency's own published reports
    own_reports = []
    if membership:
        own_reports = PublishedReport.objects.filter(
            membership=membership,
        ).order_by("-period_start")[:5]

    context = {
        "consortium": consortium,
        "rollup": rollup,
        "rollup_data_json": json.dumps(rollup.data_json) if rollup else "{}",
        "is_consortium_lead": is_lead,
        "own_reports": own_reports,
        "membership": membership,
    }
    return render(request, "consortia/dashboard.html", context)


@login_required
def dashboard_data(request, consortium_id):
    """API endpoint returning rollup data as JSON (for Chart.js)."""
    consortium = get_object_or_404(Consortium, pk=consortium_id)
    membership = _get_membership(request, consortium_id)
    is_lead = membership and getattr(membership, "is_consortium_lead", False)

    rollup = ConsortiumRollup.objects.filter(
        consortium=consortium,
    ).first()

    if not rollup:
        return JsonResponse({"error": "No rollup data available."}, status=404)

    data = rollup.data_json

    # Non-leads only see their own agency's published data
    if not is_lead:
        own_data = _get_own_agency_data(membership)
        if own_data:
            data = own_data

    return JsonResponse(data)


@login_required
def export_csv(request, consortium_id):
    """Export rollup data as CSV."""
    consortium = get_object_or_404(Consortium, pk=consortium_id)
    membership = _get_membership(request, consortium_id)
    is_lead = membership and getattr(membership, "is_consortium_lead", False)

    rollup = ConsortiumRollup.objects.filter(
        consortium=consortium,
    ).first()

    if not rollup:
        return HttpResponse("No data available.", status=404)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{consortium.name} - '
        f'{rollup.period_start} to {rollup.period_end}.csv"'
    )

    writer = csv.writer(response)

    # Service stats
    writer.writerow(["Service Statistics"])
    writer.writerow(["Metric", "Value"])
    stats = rollup.data_json.get("service_stats", {})
    for key, value in stats.items():
        writer.writerow([key.replace("_", " ").title(), value])

    writer.writerow([])

    # Demographics
    writer.writerow(["Demographics"])
    demographics = rollup.data_json.get("demographics", {})
    for category, rows in demographics.items():
        writer.writerow([category.replace("_", " ").title()])
        writer.writerow(["Category", "Count"])
        if isinstance(rows, list):
            for row in rows:
                writer.writerow([row.get("label", ""), row.get("count", "")])
        writer.writerow([])

    # Outcomes
    writer.writerow(["Outcomes"])
    writer.writerow(["Metric", "Average", "N"])
    outcomes = rollup.data_json.get("outcomes", {})
    for key, data in outcomes.items():
        if isinstance(data, dict):
            writer.writerow([
                key.replace("_", " ").title(),
                data.get("average", ""),
                data.get("n", ""),
            ])

    return response


def _get_membership(request, consortium_id):
    """Get the current agency's membership in a consortium."""
    return ConsortiumMembership.objects.filter(
        consortium_id=consortium_id, is_active=True,
    ).first()


def _get_own_agency_data(membership):
    """Get the most recent published report data for this agency."""
    if not membership:
        return None
    report = PublishedReport.objects.filter(
        membership=membership,
    ).order_by("-published_at").first()
    if report:
        return report.data_json
    return None
