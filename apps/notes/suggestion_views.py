"""Views for suggestion theme management (UX-INSIGHT6 Phase 1)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.audit.models import AuditLog
from apps.auth_app.decorators import requires_permission
from apps.programs.access import get_accessible_programs
from apps.programs.models import UserProgramRole

from .forms import SuggestionThemeForm
from .models import (
    ProgressNote, SuggestionLink, SuggestionTheme, recalculate_theme_priority,
)


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
        form = SuggestionThemeForm(
            instance=theme, requesting_user=request.user,
        )

    breadcrumbs = [
        {"url": "/admin/suggestions/", "label": _("Suggestion Themes")},
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
    linked_links = (
        theme.links.select_related("progress_note", "linked_by")
        .order_by("-linked_at")
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

    breadcrumbs = [
        {"url": "/admin/suggestions/", "label": _("Suggestion Themes")},
        {"url": "", "label": theme.name},
    ]
    return render(request, "notes/suggestions/theme_detail.html", {
        "theme": theme,
        "linked_notes": linked_notes,
        "can_manage": can_manage,
        "status_choices": SuggestionTheme.STATUS_CHOICES,
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("suggestion_theme.manage", allow_admin=True)
def unlinked_partial(request, pk):
    """HTMX endpoint: lazy-load unlinked suggestions for the Link More tab."""
    theme = get_object_or_404(SuggestionTheme, pk=pk)
    if not _can_manage_theme(request.user, theme):
        return HttpResponseForbidden()

    offset = int(request.GET.get("offset", 0))
    page_size = 25

    # Find notes with suggestions in this program that aren't linked to ANY theme
    already_linked_ids = set(
        SuggestionLink.objects.values_list("progress_note_id", flat=True)
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

    # Also get suggestions linked to OTHER themes (for reference)
    linked_to_other = []
    other_linked_ids = set(
        SuggestionLink.objects.filter(theme__program=theme.program)
        .exclude(theme=theme)
        .values_list("progress_note_id", flat=True)
    )
    if other_linked_ids:
        other_notes = ProgressNote.objects.filter(pk__in=list(other_linked_ids)[:25])
        for note in other_notes:
            text = note.participant_suggestion
            themes_for_note = list(
                SuggestionLink.objects.filter(progress_note=note)
                .values_list("theme__name", flat=True)
            )
            linked_to_other.append({
                "note_id": note.pk,
                "text": text,
                "preview": (text[:50] + "...") if len(text) > 50 else text,
                "priority": note.suggestion_priority,
                "themes": themes_for_note,
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
    linked_count = 0
    for note_id in note_ids:
        try:
            note = ProgressNote.objects.get(pk=note_id)
            if note.author_program_id != theme.program_id:
                continue
            link_obj, created = SuggestionLink.objects.get_or_create(
                theme=theme, progress_note=note,
                defaults={"linked_by": request.user, "auto_linked": False},
            )
            if created:
                linked_count += 1
        except ProgressNote.DoesNotExist:
            continue

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
