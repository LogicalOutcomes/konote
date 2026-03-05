"""Views for suggestion theme management (UX-INSIGHT6 Phase 1)."""
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, DateTimeField
from django.db.models.functions import Coalesce
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.admin_settings.models import FeatureToggle
from apps.audit.models import AuditLog
from apps.auth_app.decorators import requires_permission
from apps.programs.access import get_accessible_programs
from apps.programs.models import Program, UserProgramRole
from apps.utils.dates import parse_date_safely

from .forms import FocusedAnalysisForm, SuggestionThemeForm
from .models import (
    ProgressNote, SuggestionLink, SuggestionTheme, recalculate_theme_priority,
)

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────

def _get_pm_program_ids(user):
    """Return set of program IDs where user is an active program manager."""
    return set(
        UserProgramRole.objects.filter(
            user=user, role="program_manager", status="active",
        ).values_list("program_id", flat=True)
    )


def _can_manage_theme(user, theme):
    """Check if user can manage (edit/link/status) a specific theme."""
    if getattr(user, "is_admin", False):
        return True
    return theme.program_id in _get_pm_program_ids(user)


def _log_audit(request, action, theme, old_values=None, new_values=None):
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=str(request.user),
        ip_address=request.META.get("REMOTE_ADDR", ""),
        action=action,
        resource_type="suggestion_theme",
        resource_id=theme.pk,
        program_id=theme.program_id,
        old_values=old_values or {},
        new_values=new_values or {},
        is_demo_context=getattr(request.user, "is_demo", False),
    )


# ── Views ────────────────────────────────────────────────────────────

@login_required
@requires_permission("suggestion_theme.view", allow_admin=True)
def theme_list(request):
    """List all suggestion themes the user can see, sorted by recently active."""
    accessible_programs = get_accessible_programs(request.user)
    themes = (
        SuggestionTheme.objects.filter(program__in=accessible_programs)
        .select_related("program")
        .annotate(link_count=Count("links"))
        .order_by("-updated_at")
    )

    # GET filters
    status_filter = request.GET.get("status", "")
    program_filter = request.GET.get("program", "")
    if status_filter:
        themes = themes.filter(status=status_filter)
    if program_filter:
        themes = themes.filter(program_id=program_filter)

    can_manage = getattr(request.user, "is_admin", False) or bool(
        _get_pm_program_ids(request.user)
    )

    return render(request, "notes/suggestions/theme_list.html", {
        "themes": themes,
        "accessible_programs": accessible_programs,
        "status_filter": status_filter,
        "program_filter": program_filter,
        "can_manage": can_manage,
        "status_choices": SuggestionTheme.STATUS_CHOICES,
        "breadcrumbs": [{"url": "", "label": _("Suggestion Themes")}],
    })


@login_required
@requires_permission("suggestion_theme.manage", allow_admin=True)
def theme_form(request, pk=None):
    """Create or edit a suggestion theme."""
    if pk:
        theme = get_object_or_404(SuggestionTheme, pk=pk)
        if not _can_manage_theme(request.user, theme):
            return HttpResponseForbidden()
        editing = True
    else:
        theme = None
        editing = False

    if request.method == "POST":
        form = SuggestionThemeForm(
            request.POST, instance=theme, requesting_user=request.user,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            if not editing:
                obj.created_by = request.user
            obj.save()
            _log_audit(
                request,
                "update" if editing else "create",
                obj,
                new_values={"name": obj.name, "status": obj.status},
            )
            messages.success(
                request,
                _("Theme updated.") if editing else _("Theme created."),
            )
            return redirect("suggestion_themes:theme_detail", pk=obj.pk)
    else:
        initial = {}
        if not editing:
            # Support prefill from focused analysis "Create Theme from This"
            if request.GET.get("prefill_name"):
                initial["name"] = request.GET["prefill_name"][:200]
            if request.GET.get("prefill_description"):
                initial["description"] = request.GET["prefill_description"][:500]
            if request.GET.get("prefill_program"):
                initial["program"] = request.GET["prefill_program"]
        form = SuggestionThemeForm(
            instance=theme, requesting_user=request.user, initial=initial,
        )

    breadcrumbs = [
        {"url": reverse("suggestion_themes:theme_list"), "label": _("Suggestion Themes")},
        {"url": "", "label": _("Edit Theme") if editing else _("New Theme")},
    ]
    return render(request, "notes/suggestions/theme_form.html", {
        "form": form,
        "editing": editing,
        "theme": theme,
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("suggestion_theme.view", allow_admin=True)
def theme_detail(request, pk):
    """View a theme. PMs/admins can update status, link, and unlink."""
    theme = get_object_or_404(SuggestionTheme, pk=pk)

    # Check program access
    accessible_program_ids = set(
        get_accessible_programs(request.user).values_list("pk", flat=True)
    )
    if theme.program_id not in accessible_program_ids:
        return HttpResponseForbidden()

    can_manage = _can_manage_theme(request.user, theme)

    # ── Handle POST actions ──
    if request.method == "POST" and can_manage:
        action = request.POST.get("action", "")

        if action == "status_update":
            return _handle_status_update(request, theme)

        if action == "link_notes":
            return _handle_link_notes(request, theme)

        if action == "unlink":
            return _handle_unlink(request, theme)

    # ── GET: render detail page ──

    # Optional date filtering (passed from Insights page)
    date_from = parse_date_safely(request.GET.get("date_from", ""))
    date_to = parse_date_safely(request.GET.get("date_to", ""))
    is_filtered = bool(date_from and date_to and date_from <= date_to)

    linked_links = (
        theme.links.select_related("progress_note", "linked_by")
        .order_by("-linked_at")
    )
    if is_filtered:
        linked_links = linked_links.annotate(
            _effective_date=Coalesce(
                "progress_note__backdate",
                "progress_note__created_at",
                output_field=DateTimeField(),
            ),
        ).filter(
            _effective_date__date__gte=date_from,
            _effective_date__date__lte=date_to,
        )

    linked_notes = []
    for link in linked_links:
        note = link.progress_note
        linked_notes.append({
            "link_id": link.pk,
            "note_id": note.pk,
            "text": note.participant_suggestion,
            "priority": note.suggestion_priority,
            "priority_label": dict(ProgressNote.SUGGESTION_PRIORITY_CHOICES).get(
                note.suggestion_priority, ""
            ),
            "linked_by": link.linked_by,
            "linked_at": link.linked_at,
            "date": note.effective_date,
        })

    # Determine if verbatim text should be suppressed (5–14 participant programs)
    from apps.notes.theme_engine import get_participant_count
    from apps.reports.insights import MIN_PARTICIPANTS_FOR_QUOTES
    participant_count = get_participant_count(theme.program)
    suppress_verbatim = participant_count < MIN_PARTICIPANTS_FOR_QUOTES

    breadcrumbs = [
        {"url": reverse("suggestion_themes:theme_list"), "label": _("Suggestion Themes")},
        {"url": "", "label": theme.name},
    ]
    return render(request, "notes/suggestions/theme_detail.html", {
        "theme": theme,
        "linked_notes": linked_notes,
        "can_manage": can_manage,
        "status_choices": SuggestionTheme.STATUS_CHOICES,
        "breadcrumbs": breadcrumbs,
        "is_filtered": is_filtered,
        "date_from": date_from,
        "date_to": date_to,
        "suppress_verbatim": suppress_verbatim,
        "participant_count": participant_count,
    })


@login_required
@requires_permission("suggestion_theme.manage", allow_admin=True)
def unlinked_partial(request, pk):
    """HTMX endpoint: lazy-load unlinked suggestions for the Link More tab."""
    theme = get_object_or_404(SuggestionTheme, pk=pk)
    if not _can_manage_theme(request.user, theme):
        return HttpResponseForbidden()

    try:
        offset = max(0, int(request.GET.get("offset", 0)))
    except (ValueError, TypeError):
        offset = 0
    page_size = 25

    # Find notes with suggestions in this program that aren't linked to a theme in this program
    already_linked_ids = set(
        SuggestionLink.objects.filter(theme__program=theme.program)
        .values_list("progress_note_id", flat=True)
    )
    unlinked_qs = (
        ProgressNote.objects.filter(author_program=theme.program)
        .exclude(suggestion_priority="")
        .exclude(pk__in=already_linked_ids)
        .order_by("-created_at")
    )

    total_unlinked = unlinked_qs.count()
    unlinked_notes_page = unlinked_qs[offset:offset + page_size]

    # Decrypt in Python
    unlinked = []
    for note in unlinked_notes_page:
        text = note.participant_suggestion
        unlinked.append({
            "note_id": note.pk,
            "text": text,
            "preview": (text[:50] + "...") if len(text) > 50 else text,
            "priority": note.suggestion_priority,
            "priority_label": dict(ProgressNote.SUGGESTION_PRIORITY_CHOICES).get(
                note.suggestion_priority, ""
            ),
            "date": note.effective_date,
        })

    # Also get suggestions linked to OTHER themes (for reference) — single query
    linked_to_other = []
    other_links = (
        SuggestionLink.objects.filter(theme__program=theme.program)
        .exclude(theme=theme)
        .select_related("progress_note", "theme")
        .order_by("progress_note_id")[:25]
    )
    # Group theme names by note
    note_theme_map = {}  # note_id -> {"note": ..., "themes": set()}
    for link in other_links:
        nid = link.progress_note_id
        if nid not in note_theme_map:
            note_theme_map[nid] = {"note": link.progress_note, "themes": set()}
        note_theme_map[nid]["themes"].add(link.theme.name)
    for entry in note_theme_map.values():
        note = entry["note"]
        text = note.participant_suggestion
        linked_to_other.append({
            "note_id": note.pk,
            "text": text,
            "preview": (text[:50] + "...") if len(text) > 50 else text,
            "priority": note.suggestion_priority,
            "themes": list(entry["themes"]),
        })

    has_more = (offset + page_size) < total_unlinked
    next_offset = offset + page_size

    return render(request, "notes/suggestions/_unlinked_list.html", {
        "theme": theme,
        "unlinked": unlinked,
        "linked_to_other": linked_to_other,
        "has_more": has_more,
        "next_offset": next_offset,
        "total_unlinked": total_unlinked,
    })


# ── POST action handlers ────────────────────────────────────────────

def _handle_status_update(request, theme):
    """Handle status transition via action buttons."""
    new_status = request.POST.get("new_status", "")
    valid_statuses = dict(SuggestionTheme.STATUS_CHOICES)
    if new_status not in valid_statuses:
        messages.error(request, _("Invalid status."))
        return redirect("suggestion_themes:theme_detail", pk=theme.pk)

    old_status = theme.status
    theme.status = new_status
    if new_status == "addressed":
        theme.addressed_note = request.POST.get("addressed_note", "")
    theme.save()

    _log_audit(
        request, "update", theme,
        old_values={"status": old_status},
        new_values={"status": new_status},
    )
    messages.success(request, _("Status updated to %(status)s.") % {
        "status": valid_statuses[new_status],
    })
    return redirect("suggestion_themes:theme_detail", pk=theme.pk)


def _handle_link_notes(request, theme):
    """Handle linking selected suggestions to this theme."""
    note_ids = request.POST.getlist("note_ids")

    # Validate notes in one query: must exist and belong to this program
    valid_notes = ProgressNote.objects.filter(
        pk__in=note_ids, author_program=theme.program,
    )
    # Exclude notes already linked to this theme
    already_linked = set(
        SuggestionLink.objects.filter(theme=theme, progress_note__in=valid_notes)
        .values_list("progress_note_id", flat=True)
    )
    new_links = [
        SuggestionLink(
            theme=theme, progress_note=note,
            linked_by=request.user, auto_linked=False,
        )
        for note in valid_notes if note.pk not in already_linked
    ]
    SuggestionLink.objects.bulk_create(new_links, ignore_conflicts=True)
    linked_count = len(new_links)

    if linked_count:
        recalculate_theme_priority(theme)
        _log_audit(
            request, "update", theme,
            new_values={"action": "linked", "count": linked_count},
        )
    messages.success(
        request,
        _("%(count)d suggestion(s) linked.") % {"count": linked_count},
    )
    return redirect("suggestion_themes:theme_detail", pk=theme.pk)


def _handle_unlink(request, theme):
    """Handle unlinking a single suggestion from this theme."""
    link_id = request.POST.get("link_id", "")
    link = get_object_or_404(SuggestionLink, pk=link_id, theme=theme)
    link.delete()
    # post_delete signal handles priority recalculation
    _log_audit(
        request, "update", theme,
        new_values={"action": "unlinked", "link_id": int(link_id)},
    )
    messages.success(request, _("Suggestion removed from theme."))
    return redirect("suggestion_themes:theme_detail", pk=theme.pk)


# ── HTMX inline status update (from Insights page) ──────────────────

@login_required
@requires_permission("suggestion_theme.manage", allow_admin=True)
def theme_status_update(request, pk):
    """HTMX POST: Update theme status inline, return updated card partial."""
    if request.method != "POST":
        return HttpResponseForbidden()

    theme = get_object_or_404(SuggestionTheme, pk=pk)
    if not _can_manage_theme(request.user, theme):
        return HttpResponseForbidden()

    new_status = request.POST.get("new_status", "")
    valid_statuses = dict(SuggestionTheme.STATUS_CHOICES)
    if new_status not in valid_statuses:
        return HttpResponseForbidden()

    old_status = theme.status
    theme.status = new_status
    if new_status == "addressed":
        theme.addressed_note = request.POST.get("addressed_note", "")
    theme.save()

    _log_audit(
        request, "update", theme,
        old_values={"status": old_status},
        new_values={"status": new_status},
    )

    # Return updated theme row for HTMX swap (table-based layout).
    theme = (
        SuggestionTheme.objects.filter(pk=pk)
        .annotate(link_count=Count("links"))
        .first()
    )
    return render(request, "reports/_theme_row.html", {
        "theme": theme,
        "can_manage_themes": True,
    })


# ── Focused Theme Analysis (AI-FOCUSED-THEME1) ──────────────────────

FOCUSED_ANALYSIS_RATE_KEY = "focused_analysis:{user_id}"
FOCUSED_ANALYSIS_RATE_LIMIT = 10  # per hour
FOCUSED_ANALYSIS_RATE_WINDOW = 3600  # seconds


def _check_focused_rate_limit(user_id):
    """Return True if the user is within the rate limit."""
    key = FOCUSED_ANALYSIS_RATE_KEY.format(user_id=user_id)
    count = cache.get(key, 0)
    return count < FOCUSED_ANALYSIS_RATE_LIMIT


def _increment_focused_rate_limit(user_id):
    key = FOCUSED_ANALYSIS_RATE_KEY.format(user_id=user_id)
    count = cache.get(key, 0)
    cache.set(key, count + 1, FOCUSED_ANALYSIS_RATE_WINDOW)


@login_required
@require_POST
@requires_permission("suggestion_theme.view", allow_admin=True)
def focused_analysis_view(request):
    """HTMX POST: Run focused theme analysis on a program's suggestions."""
    # Check feature toggle
    flags = FeatureToggle.get_all_flags()
    if not flags.get("ai_assist_participant_data", False):
        return HttpResponseForbidden(_("AI participant data features are not enabled."))

    form = FocusedAnalysisForm(request.POST)
    if not form.is_valid():
        return render(request, "notes/suggestions/_focused_results.html", {
            "error": _("Please enter a question (max 500 characters)."),
        })

    question = form.cleaned_data["question"]
    program_id = form.cleaned_data["program_id"]

    # Verify program access
    program = get_object_or_404(Program, pk=program_id)
    accessible_ids = set(
        get_accessible_programs(request.user).values_list("pk", flat=True)
    )
    if program.pk not in accessible_ids:
        return HttpResponseForbidden()

    # Check privacy gate
    from apps.notes.theme_engine import get_participant_count, _check_privacy_gate
    if not _check_privacy_gate(program):
        participant_count = get_participant_count(program)
        return render(request, "notes/suggestions/_focused_results.html", {
            "error": _("This program has %(count)d participants. A minimum of 5 is required for AI analysis.") % {"count": participant_count},
        })

    # Rate limit
    if not _check_focused_rate_limit(request.user.pk):
        return render(request, "notes/suggestions/_focused_results.html", {
            "error": _("Rate limit reached (10 per hour). Please try again later."),
        })

    # Collect suggestions (PII-scrubbed) using the same pipeline as insights
    from apps.reports.insights import collect_quotes
    suggestions = collect_quotes(
        program=program,
        include_dates=False,
    )
    # Filter to only suggestion-source items
    suggestion_items = [q for q in suggestions if q.get("source") == "suggestion"]
    if not suggestion_items:
        # Fall back to all quotes if no dedicated suggestions exist
        suggestion_items = suggestions

    if not suggestion_items:
        return render(request, "notes/suggestions/_focused_results.html", {
            "error": _("No suggestions found for this program."),
        })

    # Call AI
    from konote.ai import generate_focused_analysis
    result = generate_focused_analysis(question, suggestion_items, program.name)

    _increment_focused_rate_limit(request.user.pk)

    # Audit log
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=str(request.user),
        ip_address=request.META.get("REMOTE_ADDR", ""),
        action="focused_analysis",
        resource_type="suggestion_theme",
        resource_id=0,
        program_id=program.pk,
        old_values={},
        new_values={
            "question": question,
            "participant_count": get_participant_count(program),
        },
        is_demo_context=getattr(request.user, "is_demo", False),
    )

    if result is None:
        return render(request, "notes/suggestions/_focused_results.html", {
            "error": _("AI analysis could not be completed. Please try again."),
        })

    return render(request, "notes/suggestions/_focused_results.html", {
        "result": result,
        "question": question,
        "program": program,
    })
