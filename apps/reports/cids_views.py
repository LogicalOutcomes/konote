"""CIDS compliance dashboard and Full Tier export views."""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required
from apps.programs.models import EvaluationFramework, Program
from konote.utils import get_client_ip

from .cids_full_tier import (
    build_full_tier_jsonld,
    get_agency_cids_summary,
    get_program_cids_coverage,
    serialize_full_tier_jsonld,
)

logger = logging.getLogger(__name__)


@login_required
@admin_required
def cids_coverage_dashboard(request):
    """Agency-wide CIDS compliance dashboard."""
    summaries = get_agency_cids_summary()
    total_programs = len(summaries)
    programs_with_fw = sum(1 for s in summaries if s["has_framework"])
    programs_attested = sum(1 for s in summaries if s["is_attested"])

    # Overall class coverage across all programs
    all_classes = set()
    for s in summaries:
        for c in s["coverage"]:
            if c["status"] == "present":
                all_classes.add(c["class_uri"])

    return render(request, "reports/cids_coverage_dashboard.html", {
        "summaries": summaries,
        "total_programs": total_programs,
        "programs_with_fw": programs_with_fw,
        "programs_attested": programs_attested,
        "all_classes_count": len(all_classes),
        "total_classes": 14,
    })


@login_required
@admin_required
def cids_export_status(request, program_id):
    """Export status page for a single program."""
    program = get_object_or_404(Program, pk=program_id, status="active")
    coverage = get_program_cids_coverage(program)
    present = sum(1 for c in coverage if c["status"] == "present")

    fw = EvaluationFramework.objects.filter(
        program=program, status__in=["active", "draft"],
    ).first()

    return render(request, "reports/cids_export_status.html", {
        "program": program,
        "coverage": coverage,
        "present": present,
        "total": len(coverage),
        "pct": round(present / len(coverage) * 100) if coverage else 0,
        "framework": fw,
    })


@login_required
@admin_required
def cids_full_tier_export(request):
    """Export Full Tier JSON-LD for selected programs."""
    program_id = request.GET.get("program_id")
    taxonomy_lens = request.GET.get("taxonomy_lens", "common_approach")
    include_layer3 = request.GET.get("layer3") == "1"

    if program_id:
        programs = Program.objects.filter(pk=program_id, status="active")
    else:
        programs = Program.objects.filter(status="active")

    document = build_full_tier_jsonld(
        programs,
        taxonomy_lens=taxonomy_lens,
        include_layer3=include_layer3,
    )

    program_names = ", ".join(p.name for p in programs[:10])
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=str(request.user),
        ip_address=get_client_ip(request),
        action="export",
        resource_type="export",
        metadata={"export_type": "CIDSFullTierExport", "taxonomy_lens": taxonomy_lens, "programs": program_names},
    )

    if request.GET.get("format") == "download":
        output = json.dumps(document, indent=2, ensure_ascii=False)
        response = HttpResponse(output, content_type="application/ld+json")
        timestamp = timezone.now().strftime("%Y%m%d-%H%M")
        response["Content-Disposition"] = f'attachment; filename="cids-full-tier-{timestamp}.jsonld"'
        return response

    return JsonResponse(document, json_dumps_params={"indent": 2, "ensure_ascii": False})
