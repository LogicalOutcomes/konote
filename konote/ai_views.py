"""AI-powered HTMX endpoints — all POST, all rate-limited, no PII."""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from apps.admin_settings.models import FeatureToggle
from konote import ai
from konote.forms import (
    GenerateNarrativeForm,
    ImproveOutcomeForm,
    SuggestMetricsForm,
    SuggestNoteStructureForm,
)


def _ai_enabled():
    """Check both the feature toggle and the API key."""
    if not ai.is_ai_available():
        return False
    return FeatureToggle.get_all_flags().get("ai_assist", False)


@login_required
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def suggest_metrics_view(request):
    """Suggest metrics for a plan target description."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    form = SuggestMetricsForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "Please enter a target description first."})
    target_description = form.cleaned_data["target_description"]

    # Build catalogue from non-PII metric data
    from apps.plans.models import MetricDefinition

    metrics = list(
        MetricDefinition.objects.filter(is_enabled=True, status="active").values(
            "id", "name", "definition", "category"
        )
    )

    suggestions = ai.suggest_metrics(target_description, metrics)
    if suggestions is None:
        return render(request, "ai/_error.html", {"message": "AI suggestion unavailable. Please try again later."})

    return render(request, "ai/_metric_suggestions.html", {"suggestions": suggestions})


@login_required
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def improve_outcome_view(request):
    """Improve a draft outcome statement."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    form = ImproveOutcomeForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "Please enter a draft outcome first."})
    draft_text = form.cleaned_data["draft_text"]

    improved = ai.improve_outcome(draft_text)
    if improved is None:
        return render(request, "ai/_error.html", {"message": "AI suggestion unavailable. Please try again later."})

    return render(request, "ai/_improved_outcome.html", {"improved_text": improved, "original_text": draft_text})


@login_required
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def generate_narrative_view(request):
    """Generate an outcome narrative from aggregate metrics."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.notes.models import MetricValue
    from apps.programs.models import Program, UserProgramRole

    form = GenerateNarrativeForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "Please select a program and date range."})

    program_id = form.cleaned_data["program_id"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]

    try:
        program = Program.objects.get(pk=program_id)
    except Program.DoesNotExist:
        return HttpResponseBadRequest("Program not found.")

    # Verify user has access to this program (admin sees all)
    if not request.user.is_admin:
        has_role = UserProgramRole.objects.filter(
            user=request.user, program=program, status="active",
        ).exists()
        if not has_role:
            return HttpResponseForbidden("You do not have access to this program.")

    # Build aggregate stats from metric values — no PII, just numbers
    values = (
        MetricValue.objects.filter(
            progress_note_target__progress_note__client_file__enrolments__program=program,
            progress_note_target__progress_note__client_file__enrolments__status="enrolled",
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .select_related("metric_def")
    )

    # Aggregate by metric
    from collections import defaultdict

    aggregates = defaultdict(lambda: {"total": 0.0, "count": 0})
    for mv in values:
        try:
            num = float(mv.value)
        except (ValueError, TypeError):
            continue
        key = mv.metric_def.name
        aggregates[key]["total"] += num
        aggregates[key]["count"] += 1
        aggregates[key]["unit"] = mv.metric_def.unit

    aggregate_stats = [
        {
            "metric_name": name,
            "average": round(data["total"] / data["count"], 1) if data["count"] else 0,
            "count": data["count"],
            "unit": data.get("unit", ""),
        }
        for name, data in aggregates.items()
    ]

    if not aggregate_stats:
        return render(request, "ai/_error.html", {"message": "No metric data found for this period."})

    date_range = f"{date_from} to {date_to}"
    narrative = ai.generate_narrative(program.name, date_range, aggregate_stats)
    if narrative is None:
        return render(request, "ai/_error.html", {"message": "AI narrative unavailable. Please try again later."})

    return render(request, "ai/_narrative.html", {"narrative": narrative, "program_name": program.name})


@login_required
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def suggest_note_structure_view(request):
    """Suggest a progress note structure for a plan target."""
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.plans.models import PlanTarget
    from apps.programs.models import UserProgramRole

    form = SuggestNoteStructureForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/_error.html", {"message": "No target selected."})

    try:
        target = PlanTarget.objects.select_related("plan_section__program").get(
            pk=form.cleaned_data["target_id"]
        )
    except PlanTarget.DoesNotExist:
        return HttpResponseBadRequest("Target not found.")

    # Verify user has access to the program that owns this target
    program = target.plan_section.program if target.plan_section else None
    if program and not request.user.is_admin:
        has_role = UserProgramRole.objects.filter(
            user=request.user, program=program, status="active",
        ).exists()
        if not has_role:
            return HttpResponseForbidden("You do not have access to this program.")

    metric_names = list(target.metrics.filter(status="active").values_list("name", flat=True))

    sections = ai.suggest_note_structure(target.name, target.description, metric_names)
    if sections is None:
        return render(request, "ai/_error.html", {"message": "AI suggestion unavailable. Please try again later."})

    return render(request, "ai/_note_structure.html", {"sections": sections, "target_name": target.name})


@login_required
@ratelimit(key="user", rate="10/h", method="POST", block=True)
def outcome_insights_view(request):
    """Generate AI narrative draft from qualitative outcome data. HTMX POST.

    Access control: user must have an active role (staff+) in the requested
    program. Without this check, any authenticated user could POST with an
    arbitrary program_id and receive AI-processed quotes from that program.
    """
    if not _ai_enabled():
        return HttpResponseForbidden("AI features are not enabled.")

    from apps.programs.models import Program, UserProgramRole
    from apps.reports.insights import get_structured_insights, collect_quotes
    from apps.reports.pii_scrub import scrub_pii
    from apps.reports.models import InsightSummary

    program_id = request.POST.get("program_id")
    date_from_str = request.POST.get("date_from")
    date_to_str = request.POST.get("date_to")
    regenerate = request.POST.get("regenerate")

    if not program_id or not date_from_str or not date_to_str:
        return render(request, "reports/_insights_ai.html", {
            "error": "Please select a program and date range first.",
        })

    try:
        program = Program.objects.get(pk=program_id)
    except Program.DoesNotExist:
        return HttpResponseBadRequest("Program not found.")

    # Verify user has access to this program (admin sees all)
    if not request.user.is_admin:
        has_role = UserProgramRole.objects.filter(
            user=request.user, program=program, status="active",
        ).exists()
        if not has_role:
            return HttpResponseForbidden("You do not have access to this program.")

    try:
        dt_from = date.fromisoformat(date_from_str)
        dt_to = date.fromisoformat(date_to_str)
    except ValueError:
        return HttpResponseBadRequest("Invalid date format.")

    # Check cache first (unless regenerating)
    cache_key = f"insights:{program_id}:{dt_from}:{dt_to}"
    if not regenerate:
        try:
            cached = InsightSummary.objects.get(cache_key=cache_key)
            return render(request, "reports/_insights_ai.html", {
                "summary": cached.summary_json,
                "program_id": program_id,
                "date_from": date_from_str,
                "date_to": date_to_str,
                "generated_at": cached.generated_at,
            })
        except InsightSummary.DoesNotExist:
            pass

    # Collect data
    structured = get_structured_insights(program=program, date_from=dt_from, date_to=dt_to)
    quotes = collect_quotes(
        program=program, date_from=dt_from, date_to=dt_to,
        max_quotes=30, include_dates=False,
    )

    if not quotes and structured["note_count"] < 20:
        return render(request, "reports/_insights_ai.html", {
            "error": "Not enough data to generate a meaningful summary.",
        })

    # PII-scrub quotes before sending to AI
    # Collect known names from clients in this program
    from apps.clients.models import ClientFile, ClientProgramEnrolment
    client_ids = (
        ClientProgramEnrolment.objects.filter(program=program, status="enrolled")
        .values_list("client_file_id", flat=True)
    )
    known_names = set()
    for client in ClientFile.objects.filter(pk__in=client_ids):
        for name in [client.first_name, client.last_name, client.preferred_name]:
            if name and len(name) >= 2:
                known_names.add(name)

    # Also scrub staff names
    from apps.auth_app.models import User
    for user in User.objects.filter(is_active=True):
        display = getattr(user, "display_name", "")
        if display and len(display) >= 2:
            known_names.add(display)

    scrubbed_quotes = []
    for q in quotes:
        # Data minimization: only send scrubbed text and target name to AI.
        # note_id is deliberately excluded — internal IDs should not reach
        # external services (prevents correlation if AI provider is breached).
        scrubbed_quotes.append({
            "text": scrub_pii(q["text"], known_names),
            "target_name": q.get("target_name", ""),
        })

    date_range = f"{dt_from} to {dt_to}"
    result = ai.generate_outcome_insights(
        program.name, date_range, structured, scrubbed_quotes,
    )

    if result is None:
        return render(request, "reports/_insights_ai.html", {
            "error": "AI summary could not be verified. Showing data analysis only.",
        })

    # Cache the validated result
    InsightSummary.objects.update_or_create(
        cache_key=cache_key,
        defaults={
            "summary_json": result,
            "generated_by": request.user,
        },
    )

    return render(request, "reports/_insights_ai.html", {
        "summary": result,
        "program_id": program_id,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "generated_at": timezone.now(),
    })
