# Phase 4: Progress note views
"""Views for progress notes — quick notes, full notes, timeline, cancellation."""
import datetime

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DateTimeField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

from django.db.models import Q

from apps.auth_app.constants import ROLE_PROGRAM_MANAGER, ROLE_RANK, ROLE_STAFF
from apps.auth_app.decorators import program_role_required, requires_permission
from apps.clients.models import ClientFile
from apps.plans.models import PlanTarget, PlanTargetMetric
from apps.programs.access import (
    apply_consent_filter,
    build_program_display_context,
    check_note_consent_or_403,
    get_author_program,
    get_client_or_403,
    get_program_from_client,
    get_user_program_ids,
    should_share_across_programs,
    _resolve_viewing_program,
)
from apps.programs.models import UserProgramRole
from .forms import FullNoteForm, MetricValueForm, NoteCancelForm, QuickNoteForm, TargetNoteForm
from .models import (
    ALLIANCE_PROMPT_SETS,
    MetricValue, PlausibilityOverrideLog, ProgressNote, ProgressNoteTarget,
    ProgressNoteTemplate,
)


# Use shared access helpers from apps.programs.access
_get_client_or_403 = get_client_or_403
_get_author_program = get_author_program
_get_program_from_client = get_program_from_client


def _portal_access_reminder(request, client):
    """B14: Remind staff that this participant has portal access."""
    try:
        if hasattr(client, 'portal_account') and client.portal_account.is_active:
            messages.info(
                request,
                _("Reminder: %(name)s has portal access — "
                  "their updated progress will be visible next time they log in.")
                % {"name": client.display_name},
            )
    except Exception:
        logger.warning(
            "Portal reminder check failed for client %s",
            client.pk,
            exc_info=True,
        )


def _get_program_from_note(request, note_id, **kwargs):
    """Extract program from note_id in URL kwargs.

    Looks up the note's client_file, then delegates to _get_program_from_client.
    """
    note = get_object_or_404(ProgressNote, pk=note_id)
    return _get_program_from_client(request, note.client_file_id)


def _check_client_consent(client):
    """Check if client has recorded consent (PRIV1 - PIPEDA/PHIPA compliance).

    Returns True if consent is recorded or if the feature is disabled.
    Returns False if consent is required but missing.
    """
    from apps.admin_settings.models import FeatureToggle
    flags = FeatureToggle.get_all_flags()
    # Default to True (consent required) if toggle doesn't exist
    if not flags.get("require_client_consent", True):
        return True  # Feature disabled, allow notes
    return client.consent_given_at is not None


def _get_next_alliance_prompt(client):
    """Return the next alliance prompt set index for rotation.

    Looks at the client's most recent note with an alliance_prompt_index
    and returns the next index in rotation.
    """
    last_note = ProgressNote.objects.filter(
        client_file=client,
        alliance_prompt_index__isnull=False,
    ).order_by("-pk").first()

    if last_note and last_note.alliance_prompt_index is not None:
        return (last_note.alliance_prompt_index + 1) % len(ALLIANCE_PROMPT_SETS)
    return 0


def _compute_auto_calc_values(client):
    """Compute auto-calculated metric values for a client.

    Returns dict: {computation_type: computed_value}
    """
    computed = {}
    # Use localtime so year/month match how Django evaluates created_at__month
    # (Django converts DateTimeField to the active timezone before comparing).
    local_now = timezone.localtime(timezone.now())
    count = ProgressNote.objects.filter(
        client_file=client,
        status="default",
        created_at__year=local_now.year,
        created_at__month=local_now.month,
    ).count()
    computed["session_count"] = count
    return computed


def _log_plausibility_override(metric_form, final_value, progress_note, user):
    """Create a PlausibilityOverrideLog entry when a plausibility warning was confirmed.

    Determines which threshold was breached and whether the staff corrected the value.
    """
    md = metric_form.metric_def
    original_str = metric_form.cleaned_data.get("plausibility_original_value", "")
    try:
        final_num = float(final_value)
    except (ValueError, TypeError):
        return  # Cannot log non-numeric values

    try:
        original_num = float(original_str) if original_str else final_num
    except (ValueError, TypeError):
        original_num = final_num

    # Determine which threshold was breached (use original value to detect)
    threshold_type = None
    threshold_value = None
    if md.warn_min is not None and original_num < md.warn_min:
        threshold_type = "warn_min"
        threshold_value = md.warn_min
    elif md.warn_max is not None and original_num > md.warn_max:
        threshold_type = "warn_max"
        threshold_value = md.warn_max

    if not threshold_type:
        return  # No threshold breach detected

    # Determine if staff corrected the value
    value_changed = abs(final_num - original_num) > 0.001
    action = "corrected" if value_changed else "confirmed"

    PlausibilityOverrideLog.objects.create(
        metric_definition=md,
        progress_note=progress_note,
        entered_value=original_num,
        threshold_type=threshold_type,
        threshold_value=threshold_value,
        action=action,
        corrected_value=final_num if value_changed else None,
        user=user,
    )


def _get_circle_choices_for_client(client, user=None):
    """Return circle choices for the note form dropdown.

    Returns a list of (circle_id, circle_name) tuples for circles the client
    belongs to that the user can see, or an empty list if the circles feature
    is off. Filters by get_visible_circles when user is provided (DV safety).
    """
    from apps.admin_settings.models import FeatureToggle
    if not FeatureToggle.get_all_flags().get("circles", False):
        return []
    from apps.circles.models import CircleMembership
    memberships = CircleMembership.objects.filter(
        client_file=client, status="active",
    ).select_related("circle")
    if user:
        from apps.circles.helpers import get_visible_circles
        visible_ids = set(get_visible_circles(user).values_list("pk", flat=True))
        memberships = memberships.filter(circle_id__in=visible_ids)
    return [(m.circle_id, m.circle.name) for m in memberships]


def _build_target_forms(client, post_data=None, auto_calc=None):
    """Build TargetNoteForm + MetricValueForms for each active plan target.

    Returns a list of dicts:
      [{"target": PlanTarget, "note_form": TargetNoteForm, "metric_forms": [MetricValueForm, ...]}]
    """
    targets = (
        PlanTarget.objects.filter(client_file=client, status="default")
        .select_related("plan_section")
        .order_by("plan_section__sort_order", "sort_order")
    )
    target_forms = []
    for target in targets:
        prefix = f"target_{target.pk}"
        note_form = TargetNoteForm(
            post_data,
            prefix=prefix,
            initial={"target_id": target.pk},
        )
        # Get metrics assigned to this target
        ptm_qs = PlanTargetMetric.objects.filter(plan_target=target).select_related("metric_def").order_by("sort_order")
        metric_forms = []
        skipped_metrics = []

        # Prefetch cadence data: last recorded time per metric_def for this client
        cadenced_defs = [
            ptm.metric_def_id for ptm in ptm_qs
            if ptm.metric_def.cadence_sessions and ptm.metric_def.cadence_sessions > 1
        ]
        last_recorded_map = {}
        if cadenced_defs:
            from django.db.models import Max
            last_recorded_map = dict(
                MetricValue.objects.filter(
                    metric_def_id__in=cadenced_defs,
                    progress_note_target__progress_note__client_file=client,
                    progress_note_target__progress_note__status="default",
                ).values("metric_def_id").annotate(
                    last_at=Max("created_at"),
                ).values_list("metric_def_id", "last_at")
            )

        for ptm in ptm_qs:
            # Cadence check: skip metric if not yet due
            is_due = True
            sessions_until_due = 0
            if ptm.metric_def.cadence_sessions and ptm.metric_def.cadence_sessions > 1:
                last_at = last_recorded_map.get(ptm.metric_def_id)
                if last_at:
                    notes_since = ProgressNote.objects.filter(
                        client_file=client,
                        status="default",
                        note_type="full",
                        created_at__gt=last_at,
                    ).count()
                    if notes_since < ptm.metric_def.cadence_sessions - 1:
                        is_due = False
                        sessions_until_due = ptm.metric_def.cadence_sessions - 1 - notes_since

            if not is_due:
                skipped_metrics.append({
                    "name": ptm.metric_def.translated_name,
                    "sessions_until_due": sessions_until_due,
                })
                continue

            m_prefix = f"metric_{target.pk}_{ptm.metric_def.pk}"
            mf = MetricValueForm(
                post_data,
                prefix=m_prefix,
                metric_def=ptm.metric_def,
                target_name=target.name,
                initial={"metric_def_id": ptm.metric_def.pk},
            )
            # Annotate auto-calc metrics with their computed value
            if auto_calc and ptm.metric_def.computation_type:
                mf.auto_calc_value = auto_calc.get(ptm.metric_def.computation_type)
            else:
                mf.auto_calc_value = None
            # 90-day metric review check
            if ptm.last_reviewed_date:
                days_since_review = (datetime.date.today() - ptm.last_reviewed_date).days
                mf.review_due = days_since_review >= 90
            else:
                days_since_assign = (datetime.date.today() - ptm.assigned_date).days if ptm.assigned_date else 0
                mf.review_due = days_since_assign >= 90
            mf.ptm_pk = ptm.pk  # For the HTMX confirm endpoint
            metric_forms.append(mf)
        target_forms.append({
            "target": target,
            "note_form": note_form,
            "metric_forms": metric_forms,
            "skipped_metrics": skipped_metrics,
        })
    return target_forms


def _search_notes_in_memory(notes_list, query):
    """Search encrypted note content in memory.

    Encrypted fields can't be searched in SQL — we decrypt each note's text
    fields and check for a case-insensitive substring match.

    Returns list of matching notes, each with a ``search_snippet`` attribute
    showing the text surrounding the first match.
    """
    query_lower = query.lower()
    matching = []
    for note in notes_list:
        # Collect all searchable text fields with labels
        fields = [
            (note.notes_text or "", "notes_text"),
            (note.summary or "", "summary"),
            (note.participant_reflection or "", "reflection"),
        ]
        # Include target entry notes (already prefetched)
        for entry in note.target_entries.all():
            fields.append((entry.notes or "", "target"))

        # Check each field for a match
        for text, field_name in fields:
            if query_lower in text.lower():
                note.search_snippet = _get_search_snippet(text, query)
                matching.append(note)
                break  # one match per note is enough
    return matching


def _get_search_snippet(text, query, context_chars=80):
    """Return a snippet of text centred around the first match."""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:160] + ("..." if len(text) > 160 else "")
    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(query) + context_chars)
    snippet = text[start:end]
    if start > 0:
        snippet = "\u2026" + snippet
    if end < len(text):
        snippet = snippet + "\u2026"
    return snippet


@login_required
def alliance_repair_guide(request):
    """Printable one-pager: Alliance Repair Guide for low alliance ratings (1-2).

    Reference material based on Feedback-Informed Treatment (FIT) principles.
    Any authenticated staff can view — no special permission needed.
    """
    return render(request, "notes/alliance_repair_guide.html")


@login_required
@requires_permission("note.view", _get_program_from_client)
def note_list(request, client_id):
    """Notes timeline for a client with filtering and pagination."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

    # Get user's accessible programs (respects CONF9 context switcher)
    active_ids = getattr(request, "active_program_ids", None)
    user_program_ids = get_user_program_ids(request.user, active_ids)
    program_ctx = build_program_display_context(request.user, active_ids)

    # Annotate with computed effective_date for filtering and ordering
    # (backdate if set, otherwise created_at), plus target count for display.
    # prefetch target_entries→plan_target so cards can show target chips (3 queries total)
    # Filter by user's accessible programs — workers only see notes from their programs
    notes = (
        ProgressNote.objects.filter(client_file=client)
        .filter(Q(author_program_id__in=user_program_ids) | Q(author_program__isnull=True))
        .select_related("author", "author_program", "template")
        .prefetch_related("target_entries__plan_target")
        .annotate(
            _effective_date=Coalesce("backdate", "created_at", output_field=DateTimeField()),
            target_count=Count("target_entries"),
        )
    )

    # PHIPA: consent filter narrows to viewing program if sharing is off
    notes, consent_viewing_program = apply_consent_filter(
        notes, client, request.user, user_program_ids,
        active_program_ids=active_ids,
    )

    # Filters — interaction type replaces the old quick/full type filter
    interaction_filter = request.GET.get("interaction", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    author_filter = request.GET.get("author", "")
    search_query = request.GET.get("q", "").strip()
    program_filter = request.GET.get("program", "")
    target_filter = request.GET.get("target", "")

    valid_interactions = [c[0] for c in ProgressNote.INTERACTION_TYPE_CHOICES]
    if interaction_filter in valid_interactions:
        notes = notes.filter(interaction_type=interaction_filter)
    if date_from:
        try:
            notes = notes.filter(_effective_date__date__gte=datetime.date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            notes = notes.filter(_effective_date__date__lte=datetime.date.fromisoformat(date_to))
        except ValueError:
            pass
    if author_filter == "mine":
        notes = notes.filter(author=request.user)
    if program_filter:
        try:
            notes = notes.filter(author_program_id=int(program_filter))
        except (ValueError, TypeError):
            pass
    if target_filter:
        try:
            notes = notes.filter(target_entries__plan_target_id=int(target_filter)).distinct()
        except (ValueError, TypeError):
            pass

    # Get participant's active plan targets for the filter dropdown
    # Scoped by user's accessible programs so workers only see their targets
    client_targets = PlanTarget.objects.filter(
        client_file=client, status="default"
    ).filter(
        Q(plan_section__program_id__in=user_program_ids) | Q(plan_section__program__isnull=True)
    ).select_related("plan_section").order_by("plan_section__sort_order", "sort_order")

    notes = notes.order_by("-_effective_date", "-created_at")

    # Text search — decrypt and filter in memory (encrypted fields can't be
    # searched in SQL). Only triggered when a search query is present so the
    # default path remains a fast SQL-only query.
    if search_query:
        notes_list = list(notes)
        notes_list = _search_notes_in_memory(notes_list, search_query)
        paginator = Paginator(notes_list, 25)
    else:
        paginator = Paginator(notes, 25)

    page = paginator.get_page(request.GET.get("page"))

    # Count active filters for the filter bar indicator
    active_filter_count = sum([
        bool(interaction_filter),
        bool(date_from),
        bool(date_to),
        bool(author_filter),
        bool(program_filter),
        bool(target_filter),
    ])

    # Breadcrumbs: Clients > [Client Name] > Notes
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": _("Notes")},
    ]
    context = {
        "client": client,
        "page": page,
        "filter_interaction": interaction_filter,
        "interaction_choices": ProgressNote.INTERACTION_TYPE_CHOICES,
        "filter_date_from": date_from,
        "filter_date_to": date_to,
        "filter_author": author_filter,
        "filter_program": program_filter,
        "filter_target": target_filter,
        "client_targets": client_targets,
        "search_query": search_query,
        "active_filter_count": active_filter_count,
        "active_tab": "notes",
        "user_role": getattr(request, "user_program_role", None),
        "breadcrumbs": breadcrumbs,
        "show_program_ui": program_ctx["show_program_ui"],
        "accessible_programs": program_ctx["accessible_programs"],
        "consent_viewing_program": consent_viewing_program,
    }
    if request.headers.get("HX-Request"):
        return render(request, "notes/_tab_notes.html", context)
    return render(request, "notes/note_list.html", context)


@login_required
@requires_permission("note.create", _get_program_from_client)
def quick_note_create(request, client_id):
    """Create a quick note for a client."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

    # PRIV1: Check client consent before allowing note creation
    if not _check_client_consent(client):
        return render(request, "notes/consent_required.html", {"client": client})

    circle_choices = _get_circle_choices_for_client(client, request.user)

    if request.method == "POST":
        form = QuickNoteForm(request.POST, circle_choices=circle_choices or None)
        if form.is_valid():
            with transaction.atomic():
                note = ProgressNote(
                    client_file=client,
                    note_type="quick",
                    interaction_type=form.cleaned_data["interaction_type"],
                    outcome=form.cleaned_data.get("outcome", ""),
                    author=request.user,
                    author_program=_get_author_program(request.user, client),
                    notes_text=form.cleaned_data["notes_text"],
                    follow_up_date=form.cleaned_data.get("follow_up_date"),
                )
                # Circle tagging
                circle_id = form.cleaned_data.get("circle")
                if circle_id:
                    note.circle_id = circle_id
                note.save()

                # Auto-complete any pending follow-ups from this author for this client
                ProgressNote.objects.filter(
                    client_file=client,
                    author=request.user,
                    follow_up_date__isnull=False,
                    follow_up_completed_at__isnull=True,
                    status="default",
                ).update(follow_up_completed_at=timezone.now())

            messages.success(request, _("Quick note saved."))
            _portal_access_reminder(request, client)
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = QuickNoteForm(circle_choices=circle_choices or None)

    # Breadcrumbs: Clients > [Client Name] > Notes > Quick Note
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": reverse("notes:note_list", kwargs={"client_id": client.pk}), "label": _("Notes")},
        {"url": "", "label": _("Quick Note")},
    ]
    return render(request, "notes/quick_note_form.html", {
        "form": form,
        "client": client,
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("note.create", _get_program_from_client)
def quick_note_inline(request, client_id):
    """HTMX inline form for logging contacts on the Timeline tab.

    GET: returns the inline form partial.
    GET ?mode=buttons: returns the buttons partial (for Cancel).
    POST: creates the note and returns the buttons partial.
    """
    client = _get_client_or_403(request, client_id)
    if client is None:
        raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

    # Buttons mode (Cancel action restores the button state)
    if request.method == "GET" and request.GET.get("mode") == "buttons":
        return render(request, "notes/_quick_note_inline_buttons.html", {
            "client": client,
        })

    # PRIV1: Check client consent
    if not _check_client_consent(client):
        return render(request, "notes/_inline_consent_required.html", {"client": client})

    circle_choices = _get_circle_choices_for_client(client, request.user)

    if request.method == "POST":
        form = QuickNoteForm(request.POST, circle_choices=circle_choices or None)
        if form.is_valid():
            with transaction.atomic():
                note = ProgressNote(
                    client_file=client,
                    note_type="quick",
                    interaction_type=form.cleaned_data["interaction_type"],
                    outcome=form.cleaned_data.get("outcome", ""),
                    author=request.user,
                    author_program=_get_author_program(request.user, client),
                    notes_text=form.cleaned_data["notes_text"],
                    follow_up_date=form.cleaned_data.get("follow_up_date"),
                )
                circle_id = form.cleaned_data.get("circle")
                if circle_id:
                    note.circle_id = circle_id
                note.save()

                # Auto-complete pending follow-ups
                ProgressNote.objects.filter(
                    client_file=client,
                    author=request.user,
                    follow_up_date__isnull=False,
                    follow_up_completed_at__isnull=True,
                    status="default",
                ).update(follow_up_completed_at=timezone.now())

            messages.success(request, _("Note saved."))
            return render(request, "notes/_quick_note_inline_buttons.html", {
                "client": client,
            })
    else:
        initial_type = request.GET.get("type", "phone")
        form = QuickNoteForm(initial={"interaction_type": initial_type}, circle_choices=circle_choices or None)

    return render(request, "notes/_quick_note_inline.html", {
        "form": form,
        "client": client,
    })


@login_required
def template_preview(request, template_id):
    """HTMX endpoint: return a preview of the template's sections.

    Requires at least staff-level role (receptionists cannot preview templates).
    """
    from apps.auth_app.decorators import _get_user_highest_role

    user_role = _get_user_highest_role(request.user)
    if ROLE_RANK.get(user_role, 0) < ROLE_RANK.get(ROLE_STAFF, 0):
        raise PermissionDenied(_("Access restricted to clinical staff."))

    template = get_object_or_404(ProgressNoteTemplate, pk=template_id, status="active")
    sections = template.sections.prefetch_related("metrics__metric_def").all()
    return render(request, "notes/_template_preview.html", {
        "template": template,
        "sections": sections,
    })


@login_required
@requires_permission("note.view", _get_program_from_client)
def check_note_date(request, client_id):
    """HTMX endpoint: warn if a note already exists for this client on the given date."""
    date_str = request.GET.get("session_date", "")
    if not date_str:
        return render(request, "notes/_note_date_warning.html", {"existing_notes": []})
    try:
        target_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return render(request, "notes/_note_date_warning.html", {"existing_notes": []})

    existing = (
        ProgressNote.objects.filter(client_file_id=client_id, status="default")
        .annotate(
            eff_date=Coalesce("backdate", "created_at", output_field=DateTimeField()),
        )
        .filter(eff_date__date=target_date)
        .select_related("author")
        .order_by("-created_at")[:5]
    )
    return render(request, "notes/_note_date_warning.html", {"existing_notes": existing})


@login_required
@requires_permission("note.create", _get_program_from_client)
def note_create(request, client_id):
    """Create a full structured progress note with target entries and metric values."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

    # PRIV1: Check client consent before allowing note creation
    if not _check_client_consent(client):
        return render(request, "notes/consent_required.html", {"client": client})

    auto_calc = _compute_auto_calc_values(client)
    circle_choices = _get_circle_choices_for_client(client, request.user)

    # Alliance prompt rotation — determine which prompt set to show
    from django.utils.translation import get_language
    if request.method == "POST":
        prompt_index = int(request.POST.get("alliance_prompt_index", 0))
    else:
        prompt_index = _get_next_alliance_prompt(client)
    lang = get_language()
    prompt_set = ALLIANCE_PROMPT_SETS[prompt_index]
    alliance_prompt = prompt_set["prompt_fr"] if lang == "fr" else prompt_set["prompt"]
    alliance_anchors = prompt_set["anchors_fr"] if lang == "fr" else prompt_set["anchors"]

    if request.method == "POST":
        form = FullNoteForm(request.POST, circle_choices=circle_choices or None, alliance_anchors=alliance_anchors)
        target_forms = _build_target_forms(client, request.POST, auto_calc=auto_calc)

        # Validate all forms
        all_valid = form.is_valid()
        for tf in target_forms:
            if not tf["note_form"].is_valid():
                all_valid = False
            for mf in tf["metric_forms"]:
                if not mf.is_valid():
                    all_valid = False

        if all_valid:
            with transaction.atomic():
                # Create the progress note
                note = ProgressNote(
                    client_file=client,
                    note_type="full",
                    interaction_type=form.cleaned_data["interaction_type"],
                    author=request.user,
                    author_program=_get_author_program(request.user, client),
                    template=form.cleaned_data.get("template"),
                    summary=form.cleaned_data.get("summary", ""),
                    participant_reflection=form.cleaned_data.get("participant_reflection", ""),
                    participant_suggestion=form.cleaned_data.get("participant_suggestion", ""),
                    suggestion_priority=form.cleaned_data.get("suggestion_priority", ""),
                    engagement_observation=form.cleaned_data.get("engagement_observation", ""),
                    alliance_rating=form.cleaned_data.get("alliance_rating") or None,
                    alliance_rater=form.cleaned_data.get("alliance_rater", ""),
                    alliance_prompt_index=prompt_index,
                    follow_up_date=form.cleaned_data.get("follow_up_date"),
                    duration_minutes=form.cleaned_data.get("duration_minutes") or None,
                    modality=form.cleaned_data.get("modality") or "",
                )
                # Circle tagging
                circle_id = form.cleaned_data.get("circle")
                if circle_id:
                    note.circle_id = circle_id
                session_date = form.cleaned_data.get("session_date")
                if session_date and session_date != timezone.localdate():
                    note.backdate = timezone.make_aware(
                        timezone.datetime.combine(
                            session_date,
                            timezone.datetime.min.time(),
                        )
                    )
                note.save()

                # Create target entries and metric values
                # Recompute auto-calc values once (includes the just-saved note)
                fresh_calc = _compute_auto_calc_values(client)

                for tf in target_forms:
                    nf = tf["note_form"]
                    notes_text = nf.cleaned_data.get("notes", "")
                    client_words = nf.cleaned_data.get("client_words", "")
                    progress_descriptor = nf.cleaned_data.get("progress_descriptor", "")
                    # Check if any data was entered for this target
                    has_metrics = any(
                        mf.cleaned_data.get("value", "") for mf in tf["metric_forms"]
                    )
                    has_auto_calc = any(
                        hasattr(mf, "metric_def") and mf.metric_def.computation_type
                        for mf in tf["metric_forms"]
                    )
                    if not notes_text and not has_metrics and not has_auto_calc and not client_words and not progress_descriptor:
                        continue  # Skip targets with no data entered

                    pnt = ProgressNoteTarget(
                        progress_note=note,
                        plan_target_id=nf.cleaned_data["target_id"],
                        notes=notes_text,
                        client_words=client_words,
                        progress_descriptor=progress_descriptor,
                    )
                    pnt.save()
                    for mf in tf["metric_forms"]:
                        # Auto-calc metrics: save computed value server-side
                        if hasattr(mf, "metric_def") and mf.metric_def.computation_type:
                            computed_val = fresh_calc.get(mf.metric_def.computation_type)
                            if computed_val is not None:
                                MetricValue.objects.create(
                                    progress_note_target=pnt,
                                    metric_def_id=mf.metric_def.pk,
                                    value=str(computed_val),
                                )
                        else:
                            val = mf.cleaned_data.get("value", "")
                            if val:
                                plaus_confirmed = mf.cleaned_data.get("plausibility_confirmed", False)
                                MetricValue.objects.create(
                                    progress_note_target=pnt,
                                    metric_def_id=mf.cleaned_data["metric_def_id"],
                                    value=val,
                                    plausibility_confirmed=bool(plaus_confirmed),
                                    plausibility_confirmed_by=request.user if plaus_confirmed else None,
                                )
                                # Log plausibility override if warning was triggered
                                if plaus_confirmed and hasattr(mf, "metric_def"):
                                    _log_plausibility_override(
                                        mf, val, note, request.user,
                                    )

                # Auto-complete any pending follow-ups from this author for this client
                ProgressNote.objects.filter(
                    client_file=client,
                    author=request.user,
                    follow_up_date__isnull=False,
                    follow_up_completed_at__isnull=True,
                    status="default",
                ).exclude(pk=note.pk).update(follow_up_completed_at=timezone.now())

            # Tier 1: Auto-link suggestion to existing themes (non-blocking).
            if note.participant_suggestion and note.suggestion_priority:
                try:
                    from apps.notes.theme_engine import try_auto_link_suggestion
                    try_auto_link_suggestion(note)
                except Exception:
                    logger.exception("Auto-link failed for note %s", note.pk)

            # UX-POSTSAVE1: Enhanced success message with target/metric counts
            saved_targets = ProgressNoteTarget.objects.filter(progress_note=note).count()
            saved_metrics = MetricValue.objects.filter(progress_note_target__progress_note=note).count()
            parts = [_("Progress note saved.")]
            if saved_targets:
                parts.append(
                    _("%(count)d target(s) updated") % {"count": saved_targets}
                )
            if saved_metrics:
                parts.append(
                    _("%(count)d metric(s) recorded") % {"count": saved_metrics}
                )
            messages.success(request, " ".join(parts))

            # Contextual toast when a suggestion was recorded
            if form.cleaned_data.get("suggestion_priority"):
                is_pm = UserProgramRole.objects.filter(
                    user=request.user, role=ROLE_PROGRAM_MANAGER, status="active",
                ).exists()
                if is_pm or getattr(request.user, "is_admin", False):
                    messages.info(
                        request,
                        format_html(
                            '{} <a href="{}">{}</a>',
                            _("Suggestion recorded."),
                            reverse("suggestion_themes:theme_list"),
                            _("View Suggestion Themes"),
                        ),
                    )
                else:
                    messages.info(
                        request,
                        _("This suggestion has been recorded. A Program Manager can group it with similar feedback."),
                    )

            # PORTAL-ALLIANCE1: Create async alliance rating request if applicable
            if not note.alliance_rating:
                try:
                    from apps.admin_settings.models import FeatureToggle
                    flags = FeatureToggle.get_all_flags()
                    if flags.get("portal_alliance_ratings", False):
                        if hasattr(client, "portal_account") and client.portal_account.is_active:
                            from datetime import timedelta
                            from apps.portal.models import PortalAllianceRequest
                            PortalAllianceRequest.objects.create(
                                progress_note=note,
                                client_file=client,
                                prompt_index=prompt_index,
                                expires_at=timezone.now() + timedelta(days=7),
                            )
                except Exception:
                    logger.exception("Portal alliance request creation failed for note %s", note.pk)

            _portal_access_reminder(request, client)
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = FullNoteForm(initial={"session_date": timezone.localdate()}, circle_choices=circle_choices or None, alliance_anchors=alliance_anchors)
        target_forms = _build_target_forms(client, auto_calc=auto_calc)

    # Build template → default_interaction_type mapping for JS auto-fill
    template_defaults = {}
    for tmpl in ProgressNoteTemplate.objects.filter(status="active"):
        template_defaults[str(tmpl.pk)] = tmpl.default_interaction_type

    # Breadcrumbs: Clients > [Client Name] > Notes > New Note
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": reverse("notes:note_list", kwargs={"client_id": client.pk}), "label": _("Notes")},
        {"url": "", "label": _("New Note")},
    ]
    return render(request, "notes/note_form.html", {
        "form": form,
        "target_forms": target_forms,
        "client": client,
        "breadcrumbs": breadcrumbs,
        "template_defaults": template_defaults,
        "alliance_prompt": alliance_prompt,
        "alliance_anchors": alliance_anchors,
        "alliance_prompt_index": prompt_index,
    })


@login_required
@requires_permission("note.view", _get_program_from_note)
def note_detail(request, note_id):
    """HTMX partial: expanded view of a single note."""
    try:
        note = get_object_or_404(
            ProgressNote.objects.select_related("author", "author_program", "template"),
            pk=note_id,
        )

        # Validate that author exists (defensive check for data integrity)
        if not note.author:
            logger.error(
                "Data integrity issue: note %s has no author",
                note_id
            )
            error_context = {
                "note": note,
                "client": None,
                "target_entries": [],
                "error": "This note has a data integrity issue. Please contact support.",
            }
            if request.headers.get("HX-Request"):
                return render(request, "notes/_note_detail.html", error_context)
            return render(request, "notes/note_detail_page.html", error_context)

        # Middleware already verified access; this is a redundant safety check
        client = _get_client_or_403(request, note.client_file_id)
        if client is None:
            logger.warning(
                "Permission denied in note_detail for user=%s note=%s client=%s",
                request.user.pk, note_id, note.client_file_id
            )
            raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

        # PHIPA: verify this note is visible under consent rules
        active_ids = getattr(request, "active_program_ids", None)
        check_note_consent_or_403(note, client, request.user, active_ids)

        # Filter out any orphaned entries (plan_target deleted outside Django)
        target_entries = list(
            ProgressNoteTarget.objects.filter(progress_note=note, plan_target__isnull=False)
            .select_related("plan_target")
            .prefetch_related("metric_values__metric_def")
        )
        context = {
            "note": note,
            "client": client,
            "target_entries": target_entries,
        }
        # HTMX requests get the partial; regular page loads get the full page
        if request.headers.get("HX-Request"):
            return render(request, "notes/_note_detail.html", context)
        client_url = reverse("clients:client_detail", kwargs={"client_id": client.pk})
        context["breadcrumbs"] = [
            {"label": f"{client.display_name} {client.last_name}", "url": client_url},
            {"label": _("Notes"), "url": reverse("notes:note_list", kwargs={"client_id": client.pk})},
            {"label": note.get_interaction_type_display()},
        ]
        return render(request, "notes/note_detail_page.html", context)
    except Exception as e:
        logger.exception(
            "Unexpected error in note_detail for user=%s note_id=%s: %s",
            getattr(request, 'user', None), note_id, e
        )
        raise


@login_required
@requires_permission("note.view", _get_program_from_note)
def note_summary(request, note_id):
    """HTMX partial: collapsed summary of a single note (reverses note_detail expand)."""
    try:
        note = get_object_or_404(
            ProgressNote.objects.select_related("author", "author_program", "template")
            .prefetch_related("target_entries__plan_target")
            .annotate(target_count=Count("target_entries")),
            pk=note_id,
        )
        client = _get_client_or_403(request, note.client_file_id)
        if client is None:
            logger.warning(
                "Permission denied in note_summary for user=%s note=%s client=%s",
                request.user.pk, note_id, note.client_file_id
            )
            raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

        # PHIPA: verify this note is visible under consent rules
        active_ids = getattr(request, "active_program_ids", None)
        check_note_consent_or_403(note, client, request.user, active_ids)

        return render(request, "notes/_note_summary.html", {"note": note, "client": client})
    except Exception as e:
        logger.exception(
            "Unexpected error in note_summary for user=%s note_id=%s: %s",
            getattr(request, 'user', None), note_id, e
        )
        raise


@login_required
@requires_permission("note.edit", _get_program_from_note)
def note_cancel(request, note_id):
    """Cancel a progress note (staff: own notes within 24h, program_manager: any in their program)."""
    note = get_object_or_404(ProgressNote, pk=note_id)
    client = _get_client_or_403(request, note.client_file_id)
    if client is None:
        raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

    user = request.user
    # Permission check — program managers can cancel any note in their programs
    user_role = getattr(request, "user_program_role", None)
    if user_role != ROLE_PROGRAM_MANAGER:
        if note.author_id != user.pk:
            raise PermissionDenied(_("You can only cancel your own notes."))
        age = timezone.now() - note.created_at
        if age.total_seconds() > 86400:
            raise PermissionDenied(_("Notes can only be cancelled within 24 hours."))

    if note.status == "cancelled":
        messages.info(request, _("This note is already cancelled."))
        return redirect("notes:note_list", client_id=client.pk)

    if request.method == "POST":
        form = NoteCancelForm(request.POST)
        if form.is_valid():
            note.status = "cancelled"
            note.status_reason = form.cleaned_data["status_reason"]
            note.save()
            # Create explicit audit entry
            from apps.audit.models import AuditLog
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=user.pk,
                user_display=user.display_name if hasattr(user, "display_name") else str(user),
                action="cancel",
                resource_type="progress_note",
                resource_id=note.pk,
                is_demo_context=getattr(user, "is_demo", False),
                metadata={"reason": form.cleaned_data["status_reason"]},
            )
            # Expire any pending portal alliance request for this note
            try:
                from apps.portal.models import PortalAllianceRequest
                PortalAllianceRequest.objects.filter(
                    progress_note=note,
                    status="pending",
                ).update(status="expired")
            except Exception:
                pass
            messages.success(request, _("Note cancelled."))
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = NoteCancelForm()

    # Breadcrumbs: Clients > [Client Name] > Notes > Cancel Note
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": reverse("notes:note_list", kwargs={"client_id": client.pk}), "label": _("Notes")},
        {"url": "", "label": _("Cancel Note")},
    ]
    return render(request, "notes/cancel_form.html", {
        "form": form,
        "note": note,
        "client": client,
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("note.view", _get_program_from_client)
def qualitative_summary(request, client_id):
    """Show qualitative progress summary — descriptor distribution and recent client words per target.

    PHIPA (PHIPA-QUAL1): Filters ProgressNoteTarget entries by program access
    and consent settings to prevent cross-program disclosure of client words.
    """
    client = _get_client_or_403(request, client_id)
    if client is None:
        raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

    # PHIPA-QUAL1: Get user's accessible programs for consent filtering
    active_ids = getattr(request, "active_program_ids", None)
    user_program_ids = get_user_program_ids(request.user, active_ids)

    # Check consent status for this client
    from apps.clients.dashboard_views import _get_feature_flags
    flags = _get_feature_flags()
    agency_shares = flags.get("cross_program_note_sharing", True)
    shares = should_share_across_programs(client, agency_shares)

    # Determine viewing program if consent restricts cross-program access
    consent_viewing_program = None
    viewing_program = None
    if not shares:
        viewing_program = _resolve_viewing_program(
            request.user, client, active_ids
        )
        if viewing_program:
            consent_viewing_program = viewing_program.name

    # Get all active plan targets for this client
    targets = (
        PlanTarget.objects.filter(client_file=client, status="default")
        .select_related("plan_section")
        .order_by("plan_section__sort_order", "sort_order")
    )

    target_data = []
    for target in targets:
        # Base queryset: filter by user's accessible programs
        entries = (
            ProgressNoteTarget.objects.filter(
                plan_target=target,
                progress_note__status="default",
            )
            .filter(
                Q(progress_note__author_program_id__in=user_program_ids)
                | Q(progress_note__author_program__isnull=True)
            )
            .select_related("progress_note")
            .order_by("-progress_note__created_at")
        )

        # PHIPA consent: further restrict to viewing program if sharing is off
        if not shares:
            if viewing_program:
                entries = entries.filter(
                    Q(progress_note__author_program=viewing_program)
                    | Q(progress_note__author_program__isnull=True)
                )
            else:
                # No viewing program found — fail closed (DRR decision #9)
                entries = entries.none()

        # Descriptor distribution
        descriptor_counts = {}
        for choice_val, choice_label in ProgressNoteTarget.PROGRESS_DESCRIPTOR_CHOICES:
            if choice_val:  # Skip empty choice
                descriptor_counts[choice_label] = 0
        for entry in entries:
            if entry.progress_descriptor:
                label = entry.get_progress_descriptor_display()
                if label in descriptor_counts:
                    descriptor_counts[label] += 1

        # Recent client words (last 5)
        recent_words = []
        for entry in entries[:5]:
            if entry.client_words:
                recent_words.append({
                    "text": entry.client_words,
                    "date": entry.progress_note.effective_date,
                })

        target_data.append({
            "target": target,
            "descriptor_counts": descriptor_counts,
            "total_entries": entries.count(),
            "recent_words": recent_words,
        })

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": _("Qualitative Progress")},
    ]
    return render(request, "notes/qualitative_summary.html", {
        "client": client,
        "target_data": target_data,
        "breadcrumbs": breadcrumbs,
        "consent_viewing_program": consent_viewing_program,
    })


@login_required
@requires_permission("note.create", _get_program_from_client)
def assessment_create(request, client_id, metric_id):
    """Create a simplified assessment note for a standardized instrument."""
    import json as _json
    from apps.plans.models import MetricDefinition

    client = _get_client_or_403(request, client_id)
    if client is None:
        raise PermissionDenied(
            _("You do not have access to this %(client)s.")
            % {"client": request.get_term("client", _("participant"))}
        )

    # PRIV1: Check client consent before allowing note creation
    if not _check_client_consent(client):
        return render(request, "notes/consent_required.html", {"client": client})

    metric_def = get_object_or_404(
        MetricDefinition,
        pk=metric_id,
        is_standardized_instrument=True,
        status="active",
    )

    # Find a plan target that uses this metric (needed for ProgressNoteTarget)
    from apps.plans.models import PlanTargetMetric
    ptm = PlanTargetMetric.objects.filter(
        plan_target__client_file=client,
        plan_target__status="default",
        metric_def=metric_def,
    ).select_related("plan_target").first()

    if not ptm:
        messages.error(
            request,
            _("This assessment is not linked to any active plan target."),
        )
        return redirect("clients:client_detail", client_id=client.pk)

    from .forms import AssessmentNoteForm

    # Prepare scoring bands for JS
    scoring_bands_json = None
    if metric_def.scoring_bands:
        scoring_bands_json = metric_def.scoring_bands

    if request.method == "POST":
        form = AssessmentNoteForm(request.POST)
        metric_form = MetricValueForm(
            request.POST,
            prefix="assessment",
            metric_def=metric_def,
            initial={"metric_def_id": metric_def.pk},
        )

        if form.is_valid() and metric_form.is_valid():
            score_val = metric_form.cleaned_data.get("value", "")
            if not score_val:
                metric_form.add_error("value", _("A score is required for assessments."))
            else:
                with transaction.atomic():
                    note = ProgressNote(
                        client_file=client,
                        note_type="assessment",
                        interaction_type="session",
                        author=request.user,
                        author_program=_get_author_program(request.user, client),
                        notes_text=form.cleaned_data.get("clinical_observation", ""),
                    )
                    session_date = form.cleaned_data.get("session_date")
                    if session_date and session_date != timezone.localdate():
                        note.backdate = timezone.make_aware(
                            timezone.datetime.combine(
                                session_date,
                                timezone.datetime.min.time(),
                            )
                        )
                    note.save()

                    pnt = ProgressNoteTarget(
                        progress_note=note,
                        plan_target=ptm.plan_target,
                    )
                    pnt.save()

                    plaus_confirmed = metric_form.cleaned_data.get("plausibility_confirmed", False)
                    mv = MetricValue.objects.create(
                        progress_note_target=pnt,
                        metric_def=metric_def,
                        value=score_val,
                        plausibility_confirmed=bool(plaus_confirmed),
                        plausibility_confirmed_by=request.user if plaus_confirmed else None,
                    )

                    # Log plausibility override if applicable
                    if plaus_confirmed:
                        _log_plausibility_override(metric_form, score_val, note, request.user)

                # Build success message with severity band
                severity = metric_def.get_severity_band(score_val)
                msg = _("Assessment saved: %(name)s = %(value)s") % {
                    "name": metric_def.translated_name,
                    "value": score_val,
                }
                if severity:
                    msg += f" ({severity})"
                messages.success(request, msg)

                # Reminder about portal access
                _portal_access_reminder(request, client)

                return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = AssessmentNoteForm()
        metric_form = MetricValueForm(
            prefix="assessment",
            metric_def=metric_def,
            initial={"metric_def_id": metric_def.pk},
        )

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}),
         "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": metric_def.translated_name},
    ]

    return render(request, "notes/assessment_form.html", {
        "client": client,
        "metric_def": metric_def,
        "form": form,
        "metric_form": metric_form,
        "scoring_bands_json": scoring_bands_json,
        "breadcrumbs": breadcrumbs,
    })
