"""Views for Outcome Insights — program-level and client-level qualitative analysis."""
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils.translation import gettext as _

from django.db.models import Count

from apps.auth_app.decorators import requires_permission
from apps.programs.access import get_accessible_programs, get_client_or_403
from apps.programs.models import UserProgramRole
from apps.notes.models import (
    ProgressNote, SuggestionLink, SuggestionTheme,
    THEME_PRIORITY_RANK, deduplicate_themes,
)
from .insights import get_structured_insights, collect_quotes, MIN_PARTICIPANTS_FOR_QUOTES
from .insights_forms import InsightsFilterForm
from .metric_insights import (
    get_metric_distributions,
    get_achievement_rates,
    get_metric_trends,
    get_two_lenses,
    get_data_completeness,
    get_trend_direction,
)
from .interpretations import (
    interpret_progress_trend,
    interpret_engagement,
    interpret_descriptor_snapshot,
    interpret_suggestions,
    interpret_client_trend,
)

# Map DB values to human-readable labels for suggestion priorities
_PRIORITY_LABELS = dict(ProgressNote.SUGGESTION_PRIORITY_CHOICES)

logger = logging.getLogger(__name__)


def _get_data_tier(note_count, month_count):
    """Determine which features to show based on data volume.

    Returns:
        "sparse"   — <20 notes: snapshot only, no trend, no AI
        "limited"  — 20-49 notes or <3 months: trend + quotes + AI with caveat
        "full"     — 50+ notes, 3+ months: everything
    """
    if note_count < 20:
        return "sparse"
    if note_count < 50 or month_count < 3:
        return "limited"
    return "full"


@login_required
@requires_permission("insights.view")
def program_insights(request):
    """Program-level Outcome Insights page.

    GET: Show form. If program + time period are in query params, show results.

    Access: staff, program_manager, and executive roles. Executives see
    aggregate data only (quotes suppressed because note.view is DENY).
    Enforced by @requires_permission("insights.view").
    """
    # Executive-only users see aggregates but not individual note quotes
    user_roles = set(
        UserProgramRole.objects.filter(user=request.user, status="active")
        .values_list("role", flat=True)
    )
    is_executive_only = user_roles and user_roles <= {"executive"}

    form = InsightsFilterForm(request.GET or None, user=request.user)

    context = {
        "form": form,
        "nav_active": "insights",
        "is_executive_only": is_executive_only,
        "breadcrumbs": [
            {"url": "", "label": "Outcome Insights"},
        ],
    }

    # If form is submitted via GET params, compute insights
    if form.is_bound and form.is_valid():
        program = form.cleaned_data["program"]
        date_from = form.cleaned_data["date_from"]
        date_to = form.cleaned_data["date_to"]

        # Layer 1: SQL aggregation (instant, no ceiling)
        structured = get_structured_insights(
            program=program,
            date_from=date_from,
            date_to=date_to,
        )

        data_tier = _get_data_tier(structured["note_count"], structured["month_count"])

        # Quotes: privacy-gated, no dates at program level.
        # Always collect so executives can see suggestion text (program
        # feedback, not personal data). Other quotes are suppressed for
        # executive-only users because note.view is DENY for them.
        quotes = []
        if data_tier != "sparse":
            quotes = collect_quotes(
                program=program,
                date_from=date_from,
                date_to=date_to,
                include_dates=False,  # Privacy: no dates at program level
            )

        # Separate suggestions from other quotes so they display under their own heading
        suggestions = []
        other_quotes = []
        for q in quotes:
            if q.get("source") == "suggestion":
                q["priority_label"] = _PRIORITY_LABELS.get(q.get("priority", ""), "")
                suggestions.append(q)
            elif not is_executive_only:
                other_quotes.append(q)

        # Active suggestion themes for this program (deduplicated by name)
        active_themes = deduplicate_themes(list(
            SuggestionTheme.objects.active()
            .filter(program=program)
            .annotate(link_count=Count("links"))
            .values("pk", "name", "status", "priority", "program_id",
                    "updated_at", "link_count")
        ))
        active_themes.sort(key=lambda t: (
            -THEME_PRIORITY_RANK.get(t["priority"], 0),
            -t["updated_at"].timestamp(),
        ))

        # Responsiveness summary: "X of Y themes addressed"
        addressed_themes = deduplicate_themes(list(
            SuggestionTheme.objects.filter(program=program, status="addressed")
            .annotate(link_count=Count("links"))
            .values("pk", "name", "status", "priority", "program_id",
                    "updated_at", "link_count")
        ))
        addressed_themes.sort(key=lambda t: -t["updated_at"].timestamp())
        addressed_themes_count = len(addressed_themes)
        total_theme_count = len(active_themes) + addressed_themes_count

        # Split suggestions into linked vs unlinked (ungrouped)
        linked_note_ids = set(
            SuggestionLink.objects.filter(theme__program=program)
            .values_list("progress_note_id", flat=True)
        )
        unlinked_suggestions = [s for s in suggestions if s["note_id"] not in linked_note_ids]

        # Plain-language interpretations (only when enough data)
        interp = {}
        if data_tier != "sparse":
            interp = {
                "interp_trend": interpret_progress_trend(structured["descriptor_trend"]),
                "interp_engagement": interpret_engagement(structured["engagement_raw"]),
                "interp_snapshot": interpret_descriptor_snapshot(structured["descriptor_trend"]),
                "interp_suggestions": interpret_suggestions(
                    structured["suggestion_total"],
                    structured["suggestion_important_count"],
                ),
            }

        # ── Metric distributions and achievements (Phase 2) ──
        metric_distributions = {}
        achievement_rates = {}
        metric_trends = {}
        two_lenses = None
        data_completeness = {}
        trend_directions = {}
        lead_outcome = None
        lead_metric = None
        lead_trend_direction = None
        distributions_summary_pct = None
        distributions_trend_direction = None
        total_new_participants = 0
        has_urgent_themes = False

        if data_tier != "sparse":
            metric_distributions = get_metric_distributions(program, date_from, date_to)
            achievement_rates = get_achievement_rates(program, date_from, date_to)
            metric_trends = get_metric_trends(program, date_from, date_to)
            two_lenses = get_two_lenses(program, date_from, date_to, distributions=metric_distributions)
            data_completeness = get_data_completeness(program, date_from, date_to)

            # Compute trend directions per metric
            for mid in metric_distributions:
                trend_directions[mid] = get_trend_direction(metric_trends, mid)

            # Total new participants across all metrics
            total_new_participants = sum(
                d.get("n_new_participants", 0) for d in metric_distributions.values()
            )

            # Lead outcome (first achievement metric for summary card)
            if achievement_rates:
                lead_outcome = next(iter(achievement_rates.values()))

            # Lead metric (first scale metric for summary card, when no achievement)
            if metric_distributions and not lead_outcome:
                lead_metric = next(iter(metric_distributions.values()))

            # Distributions summary for section preview
            if metric_distributions:
                first_dist = next(iter(metric_distributions.values()))
                distributions_summary_pct = first_dist["band_high_pct"]
                first_mid = next(iter(metric_distributions))
                distributions_trend_direction = trend_directions.get(first_mid)

            # Lead trend direction for summary card
            if lead_outcome and achievement_rates:
                lead_trend_direction = None  # No trend for achievement yet
            elif metric_distributions:
                first_mid = next(iter(metric_distributions))
                lead_trend_direction = trend_directions.get(first_mid)

            # Check for urgent themes
            has_urgent_themes = any(
                t.get("priority") == "urgent" for t in active_themes
            )

        # ── Auto-expand logic (DRR §5) ──
        expand_participant_voice = True  # Default: always open
        expand_distributions = bool(metric_distributions)
        expand_outcomes = bool(achievement_rates)
        expand_staff_assessments = bool(structured.get("descriptor_trend"))
        expand_engagement = False  # Default: collapsed

        if has_urgent_themes:
            # Urgent feedback → Participant Voice always open
            expand_participant_voice = True
        elif metric_distributions or achievement_rates:
            # Quantitative data exists → open those, Participant Voice stays open too
            expand_participant_voice = True

        context.update({
            "program": program,
            "date_from": date_from,
            "date_to": date_to,
            "structured": structured,
            "quotes": other_quotes,
            "suggestions": suggestions,
            "unlinked_suggestions": unlinked_suggestions,
            "active_themes": active_themes,
            "addressed_themes": addressed_themes,
            "addressed_themes_count": addressed_themes_count,
            "total_theme_count": total_theme_count,
            "can_manage_themes": UserProgramRole.objects.filter(
                user=request.user, program=program,
                role="program_manager", status="active",
            ).exists() or request.user.is_superuser,
            "data_tier": data_tier,
            "min_participants": MIN_PARTICIPANTS_FOR_QUOTES,
            "chart_data_json": structured["descriptor_trend"],
            "show_results": True,
            # Metric distributions (Phase 2)
            "metric_distributions": metric_distributions,
            "achievement_rates": achievement_rates,
            "metric_trends": metric_trends,
            "two_lenses": two_lenses,
            "data_completeness": data_completeness,
            "trend_directions": trend_directions,
            "lead_outcome": lead_outcome,
            "lead_metric": lead_metric,
            "lead_trend_direction": lead_trend_direction,
            "distributions_summary_pct": distributions_summary_pct,
            "distributions_trend_direction": distributions_trend_direction,
            "total_new_participants": total_new_participants,
            "has_urgent_themes": has_urgent_themes,
            # Auto-expand flags
            "expand_participant_voice": expand_participant_voice,
            "expand_distributions": expand_distributions,
            "expand_outcomes": expand_outcomes,
            "expand_staff_assessments": expand_staff_assessments,
            "expand_engagement": expand_engagement,
            **interp,
        })

    # Check if AI is available for the template
    from konote.ai import is_ai_available
    from apps.admin_settings.models import FeatureToggle
    ai_enabled = is_ai_available() and FeatureToggle.get_all_flags().get("ai_assist", False)
    context["ai_enabled"] = ai_enabled

    if request.headers.get("HX-Request"):
        return render(request, "reports/_insights_basic.html", context)
    return render(request, "reports/insights.html", context)


@login_required
@requires_permission("metric.view_individual")
def client_insights_partial(request, client_id):
    """Client-level insights — HTMX partial for the Analysis tab."""
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this participant.")

    # Default to last 12 months
    from datetime import date, timedelta
    date_to = date.today()
    date_from = date_to - timedelta(days=365)

    # Allow date override from query params
    if request.GET.get("date_from"):
        try:
            date_from = date.fromisoformat(request.GET["date_from"])
        except ValueError:
            pass
    if request.GET.get("date_to"):
        try:
            date_to = date.fromisoformat(request.GET["date_to"])
        except ValueError:
            pass

    structured = get_structured_insights(
        client_file=client,
        date_from=date_from,
        date_to=date_to,
    )

    data_tier = _get_data_tier(structured["note_count"], structured["month_count"])

    # Client-level: no participant threshold, dates included
    quotes = collect_quotes(
        client_file=client,
        date_from=date_from,
        date_to=date_to,
        include_dates=True,
    )

    # Check AI availability
    from konote.ai import is_ai_available
    from apps.admin_settings.models import FeatureToggle
    ai_enabled = is_ai_available() and FeatureToggle.get_all_flags().get("ai_assist", False)

    # Separate suggestions from other quotes
    suggestions = []
    other_quotes = []
    for q in quotes:
        if q.get("source") == "suggestion":
            q["priority_label"] = _PRIORITY_LABELS.get(q.get("priority", ""), "")
            suggestions.append(q)
        else:
            other_quotes.append(q)

    # Plain-language interpretations (only when enough data)
    interp = {}
    if data_tier != "sparse":
        interp = {
            "interp_trend": interpret_client_trend(structured["descriptor_trend"]),
            "interp_suggestions": interpret_suggestions(
                structured["suggestion_total"],
                structured["suggestion_important_count"],
            ),
        }

    context = {
        "client": client,
        "date_from": date_from,
        "date_to": date_to,
        "structured": structured,
        "quotes": other_quotes,
        "suggestions": suggestions,
        "data_tier": data_tier,
        "chart_data_json": structured["descriptor_trend"],
        "ai_enabled": ai_enabled,
        "scope": "client",
        **interp,
    }

    return render(request, "reports/_insights_client.html", context)
