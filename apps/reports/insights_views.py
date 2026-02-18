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
from apps.notes.models import ProgressNote, SuggestionLink, SuggestionTheme
from .insights import get_structured_insights, collect_quotes, MIN_PARTICIPANTS_FOR_QUOTES
from .insights_forms import InsightsFilterForm
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

        # Quotes: privacy-gated, no dates at program level
        # Executives cannot see quotes (note.view is DENY for executives)
        quotes = []
        if data_tier != "sparse" and not is_executive_only:
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
            else:
                other_quotes.append(q)

        # Active suggestion themes for this program
        active_themes = (
            SuggestionTheme.objects.active()
            .filter(program=program)
            .annotate(link_count=Count("links"))
            .order_by("-updated_at")
        )

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

        context.update({
            "program": program,
            "date_from": date_from,
            "date_to": date_to,
            "structured": structured,
            "quotes": other_quotes,
            "suggestions": suggestions,
            "unlinked_suggestions": unlinked_suggestions,
            "active_themes": active_themes,
            "data_tier": data_tier,
            "min_participants": MIN_PARTICIPANTS_FOR_QUOTES,
            "chart_data_json": structured["descriptor_trend"],
            "show_results": True,
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
