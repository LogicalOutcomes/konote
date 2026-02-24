"""Views for Outcome Insights — program-level and client-level qualitative analysis."""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils.translation import gettext as _

from django.db.models import Count

from apps.auth_app.decorators import requires_permission
from apps.programs.access import get_client_or_403
from apps.programs.models import UserProgramRole
from apps.notes.models import (
    ProgressNote, SuggestionLink, SuggestionTheme,
    THEME_PRIORITY_RANK, deduplicate_themes,
)
from .insights import get_structured_insights, collect_quotes, MIN_PARTICIPANTS_FOR_QUOTES
from .insights_forms import InsightsFilterForm
from .interpretations import (
    interpret_progress_trend,
    interpret_engagement,
    interpret_descriptor_snapshot,
    interpret_suggestions,
    interpret_client_trend,
)
from .metric_insights import (
    get_metric_distributions,
    get_achievement_rates,
    get_metric_trends,
    get_two_lenses,
    get_data_completeness,
)
from .models import ReportTemplate, ReportSchedule

# Map DB values to human-readable labels for suggestion priorities
_PRIORITY_LABELS = dict(ProgressNote.SUGGESTION_PRIORITY_CHOICES)

logger = logging.getLogger(__name__)


def _compute_auto_expand(active_themes, metric_distributions, achievement_rates,
                         structured, data_tier):
    """Determine which <details> sections should be open by default.

    Priority:
    1. Urgent signals (urgent themes, large negative trend) → open
    2. Freshest data → open
    3. Tie → Participant Voice opens (client-centred tiebreaker)
    4. If only quantitative would open, also open Participant Voice
    """
    flags = {
        "expand_participant_voice": False,
        "expand_distributions": False,
        "expand_outcomes": False,
        "expand_staff_assessments": False,
        "expand_engagement": False,
    }

    if data_tier == "sparse":
        return flags

    has_urgent_themes = any(
        t.get("priority") == "urgent" for t in active_themes
    )

    # Default: Participant Voice always opens (client-centred tiebreaker)
    if active_themes or structured.get("suggestion_total", 0) > 0:
        flags["expand_participant_voice"] = True

    # Urgent themes → Participant Voice opens
    if has_urgent_themes:
        flags["expand_participant_voice"] = True

    # If we have distribution data, open that section
    if metric_distributions:
        flags["expand_distributions"] = True

    # If we have achievement data, open outcomes
    if achievement_rates:
        flags["expand_outcomes"] = True

    # If only quantitative sections would open but not Participant Voice,
    # also open Participant Voice
    quantitative_open = (
        flags["expand_distributions"]
        or flags["expand_outcomes"]
        or flags["expand_staff_assessments"]
    )
    if quantitative_open and not flags["expand_participant_voice"]:
        flags["expand_participant_voice"] = True

    # Staff assessments open by default if we have trend data
    if structured.get("descriptor_trend"):
        flags["expand_staff_assessments"] = True

    return flags


def _compute_trend_direction(descriptor_trend):
    """Determine overall trend direction from descriptor trend data."""
    if not descriptor_trend or len(descriptor_trend) < 2:
        return ""

    first = descriptor_trend[0]
    last = descriptor_trend[-1]

    first_good = first.get("good_place", 0) + first.get("shifting", 0)
    last_good = last.get("good_place", 0) + last.get("shifting", 0)

    diff = last_good - first_good
    if diff > 5:
        return _("improving")
    elif diff < -5:
        return _("declining")
    return _("stable")


def _build_distributions_summary(metric_distributions):
    """Build a summary string for the distributions <summary> line."""
    if not metric_distributions:
        return ""
    total_scored = sum(d["total"] for d in metric_distributions.values())
    # Weighted average of band_low_pct across metrics
    if total_scored > 0:
        weighted_low = sum(
            d["band_low_pct"] * d["total"] for d in metric_distributions.values()
        ) / total_scored
        return _("%(scored)d scored · %(low_pct).0f%% need more support") % {
            "scored": total_scored, "low_pct": weighted_low,
        }
    return ""


def _build_outcomes_summary(achievement_rates):
    """Build a summary string for the outcomes <summary> line."""
    if not achievement_rates:
        return ""
    parts = []
    for ach in achievement_rates.values():
        part = f"{ach['achieved_pct']}% {ach['name']}"
        if ach.get("target_rate"):
            part += f" (target: {ach['target_rate']}%)"
        parts.append(part)
    return " · ".join(parts)


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

        # ── Metric distribution data (Layers 1 & 2) ──
        metric_distributions = get_metric_distributions(program, date_from, date_to)
        achievement_rates_data = get_achievement_rates(program, date_from, date_to)
        metric_trends = get_metric_trends(program, date_from, date_to)
        data_completeness = get_data_completeness(program, date_from, date_to)
        two_lenses = get_two_lenses(program, date_from, date_to,
                                    structured=structured,
                                    distributions=metric_distributions)

        # Enrich achievement rates with not-achieved count and journey context
        for metric_id, ach in achievement_rates_data.items():
            ach["not_achieved_count"] = ach["total"] - ach["achieved_count"]
            ach["not_achieved_pct"] = round(
                ach["not_achieved_count"] / ach["total"] * 100, 1
            ) if ach["total"] else 0

        # ── Auto-expand logic ──
        expand_flags = _compute_auto_expand(
            active_themes, metric_distributions, achievement_rates_data,
            structured, data_tier,
        )

        # ── Summary card helpers ──
        # Lead distribution = first universal metric, or first metric
        lead_distribution = None
        for mid, dist in metric_distributions.items():
            if dist.get("is_universal"):
                lead_distribution = dist
                break
        if not lead_distribution and metric_distributions:
            lead_distribution = next(iter(metric_distributions.values()))

        # Lead achievement = first achievement metric
        lead_achievement = None
        if achievement_rates_data:
            lead_achievement = next(iter(achievement_rates_data.values()))

        # Trend direction from descriptor trend
        trend_direction = _compute_trend_direction(structured["descriptor_trend"])

        # Urgent theme count
        urgent_theme_count = sum(
            1 for t in active_themes if t.get("priority") == "urgent"
        )

        # Total new participants across distributions
        total_new_participants = sum(
            d.get("n_new_participants", 0) for d in metric_distributions.values()
        )

        # Summary lines for progressive disclosure
        distributions_summary = _build_distributions_summary(metric_distributions)
        outcomes_summary = _build_outcomes_summary(achievement_rates_data)

        # Metric trends as JSON for Chart.js
        metric_trends_json = json.dumps(metric_trends) if metric_trends else ""
        metric_trends_keys = set(str(k) for k in metric_trends.keys()) if metric_trends else set()

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
            # New metric distribution data
            "metric_distributions": metric_distributions,
            "achievement_rates": achievement_rates_data,
            "metric_trends": metric_trends,
            "metric_trends_json": metric_trends_json,
            "metric_trends_keys": metric_trends_keys,
            "data_completeness": data_completeness,
            "two_lenses": two_lenses,
            "lead_distribution": lead_distribution,
            "lead_achievement": lead_achievement,
            "trend_direction": trend_direction,
            "urgent_theme_count": urgent_theme_count,
            "total_new_participants": total_new_participants,
            "distributions_summary": distributions_summary,
            "outcomes_summary": outcomes_summary,
            **expand_flags,
            **interp,
        })

        # ── Workbench-to-report links ──
        # Partner report templates configured for this program
        partner_templates = (
            ReportTemplate.objects.filter(
                is_active=True,
                partner__is_active=True,
                partner__programs=program,
            )
            .select_related("partner")
            .order_by("partner__name", "name")
        )
        # Also include org-wide templates (partners with no programs linked)
        org_wide_templates = (
            ReportTemplate.objects.filter(
                is_active=True,
                partner__is_active=True,
            )
            .exclude(partner__programs__isnull=False)
            .select_related("partner")
            .order_by("partner__name", "name")
        )
        all_partner_templates = list(partner_templates) + list(org_wide_templates)

        # Upcoming report schedules (funder reports due soon).
        # Intentionally org-wide: ReportSchedule has no program FK — deadlines
        # apply across the organisation. The insights view already requires
        # report permissions, and schedule names/dates are not PII.
        upcoming_schedules = list(
            ReportSchedule.objects.filter(
                is_active=True,
                report_type="funder_report",
            ).order_by("due_date")[:5]
        )

        context.update({
            "partner_templates": all_partner_templates,
            "upcoming_schedules": upcoming_schedules,
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
