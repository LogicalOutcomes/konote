"""Views for Outcome Insights — programme-level and client-level qualitative analysis."""
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _

from apps.auth_app.decorators import minimum_role, requires_permission
from apps.programs.access import get_accessible_programs, get_client_or_403
from apps.programs.models import UserProgramRole
from .insights import get_structured_insights, collect_quotes, MIN_PARTICIPANTS_FOR_QUOTES
from .insights_forms import InsightsFilterForm

logger = logging.getLogger(__name__)

# Roles that can view programme-level aggregate insights
_INSIGHTS_ROLES = {"staff", "program_manager", "executive"}


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
def program_insights(request):
    """Programme-level Outcome Insights page.

    GET: Show form. If programme + time period are in query params, show results.

    Access: staff, program_manager, and executive roles. Executives see
    aggregate data only (quotes suppressed because note.view is DENY).
    """
    # Check role access — allow staff, PM, and executive (not receptionist)
    user_roles = set(
        UserProgramRole.objects.filter(user=request.user, status="active")
        .values_list("role", flat=True)
    )
    if not (request.user.is_admin or user_roles & _INSIGHTS_ROLES):
        message = _("Access denied. You do not have the required role for this action.")
        response = TemplateResponse(
            request, "403.html", {"exception": message}, status=403,
        )
        response.render()
        return response

    # Executive-only users see aggregates but not individual note quotes
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

        # Quotes: privacy-gated, no dates at programme level
        # Executives cannot see quotes (note.view is DENY for executives)
        quotes = []
        if data_tier != "sparse" and not is_executive_only:
            quotes = collect_quotes(
                program=program,
                date_from=date_from,
                date_to=date_to,
                include_dates=False,  # Privacy: no dates at programme level
            )

        context.update({
            "program": program,
            "date_from": date_from,
            "date_to": date_to,
            "structured": structured,
            "quotes": quotes,
            "data_tier": data_tier,
            "min_participants": MIN_PARTICIPANTS_FOR_QUOTES,
            "chart_data_json": structured["descriptor_trend"],
            "show_results": True,
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

    context = {
        "client": client,
        "date_from": date_from,
        "date_to": date_to,
        "structured": structured,
        "quotes": quotes,
        "data_tier": data_tier,
        "chart_data_json": structured["descriptor_trend"],
        "ai_enabled": ai_enabled,
        "scope": "client",
    }

    return render(request, "reports/_insights_client.html", context)
