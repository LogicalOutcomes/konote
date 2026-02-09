# Phase 4: Progress note views
"""Views for progress notes — quick notes, full notes, timeline, cancellation."""
import datetime

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DateTimeField
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

from django.db.models import Q

from apps.auth_app.decorators import programme_role_required
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import PlanTarget, PlanTargetMetric
from apps.programs.access import (
    build_program_display_context,
    get_author_program,
    get_client_or_403,
    get_user_program_ids,
)
from apps.programs.models import UserProgramRole

from .forms import FullNoteForm, MetricValueForm, NoteCancelForm, QuickNoteForm, TargetNoteForm
from .models import MetricValue, ProgressNote, ProgressNoteTarget, ProgressNoteTemplate


# Use shared access helpers from apps.programs.access
_get_client_or_403 = get_client_or_403
_get_author_program = get_author_program


# ---------------------------------------------------------------------------
# Helper functions for programme_role_required decorator
# ---------------------------------------------------------------------------


def _get_programme_from_client(request, client_id, **kwargs):
    """Extract programme from client_id in URL kwargs.

    A client can be enrolled in multiple programmes. We return the first
    programme the requesting user shares with the client (same logic as
    get_author_program). If no shared programme exists, raises ValueError
    which the decorator converts to a 403.
    """
    from apps.programs.models import Program
    client = get_object_or_404(ClientFile, pk=client_id)
    user_program_ids = set(
        UserProgramRole.objects.filter(user=request.user, status="active")
        .values_list("program_id", flat=True)
    )
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled"
        ).values_list("program_id", flat=True)
    )
    shared = user_program_ids & client_program_ids
    if shared:
        return Program.objects.filter(pk__in=shared).first()
    # Admin bypass -- admins may not share a programme but should still have access
    if request.user.is_admin:
        # Return the client's first programme so the decorator has something to check
        first_enrolment = ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled"
        ).first()
        if first_enrolment:
            return first_enrolment.program
    raise ValueError(f"User has no shared programme with client {client_id}")


def _get_programme_from_note(request, note_id, **kwargs):
    """Extract programme from note_id in URL kwargs.

    Looks up the note's client_file, then delegates to _get_programme_from_client.
    """
    note = get_object_or_404(ProgressNote, pk=note_id)
    return _get_programme_from_client(request, note.client_file_id)


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


def _build_target_forms(client, post_data=None):
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
        for ptm in ptm_qs:
            m_prefix = f"metric_{target.pk}_{ptm.metric_def.pk}"
            mf = MetricValueForm(
                post_data,
                prefix=m_prefix,
                metric_def=ptm.metric_def,
                initial={"metric_def_id": ptm.metric_def.pk},
            )
            metric_forms.append(mf)
        target_forms.append({
            "target": target,
            "note_form": note_form,
            "metric_forms": metric_forms,
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
@programme_role_required("staff", _get_programme_from_client)
def note_list(request, client_id):
    """Notes timeline for a client with filtering and pagination."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

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

    # Filters — interaction type replaces the old quick/full type filter
    interaction_filter = request.GET.get("interaction", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    author_filter = request.GET.get("author", "")
    search_query = request.GET.get("q", "").strip()
    program_filter = request.GET.get("program", "")

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
        "search_query": search_query,
        "active_filter_count": active_filter_count,
        "active_tab": "notes",
        "user_role": getattr(request, "user_programme_role", None) or getattr(request, "user_program_role", None),
        "breadcrumbs": breadcrumbs,
        "show_program_ui": program_ctx["show_program_ui"],
        "accessible_programs": program_ctx["accessible_programs"],
    }
    if request.headers.get("HX-Request"):
        return render(request, "notes/_tab_notes.html", context)
    return render(request, "notes/note_list.html", context)


@login_required
@programme_role_required("staff", _get_programme_from_client)
def quick_note_create(request, client_id):
    """Create a quick note for a client."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # PRIV1: Check client consent before allowing note creation
    if not _check_client_consent(client):
        return render(request, "notes/consent_required.html", {"client": client})

    if request.method == "POST":
        form = QuickNoteForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                note = ProgressNote(
                    client_file=client,
                    note_type="quick",
                    interaction_type=form.cleaned_data["interaction_type"],
                    author=request.user,
                    author_program=_get_author_program(request.user, client),
                    notes_text=form.cleaned_data["notes_text"],
                    follow_up_date=form.cleaned_data.get("follow_up_date"),
                )
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
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = QuickNoteForm()

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
@programme_role_required("staff", _get_programme_from_client)
def note_create(request, client_id):
    """Create a full structured progress note with target entries and metric values."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # PRIV1: Check client consent before allowing note creation
    if not _check_client_consent(client):
        return render(request, "notes/consent_required.html", {"client": client})

    if request.method == "POST":
        form = FullNoteForm(request.POST)
        target_forms = _build_target_forms(client, request.POST)

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
                    follow_up_date=form.cleaned_data.get("follow_up_date"),
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

                # Create target entries and metric values
                for tf in target_forms:
                    nf = tf["note_form"]
                    notes_text = nf.cleaned_data.get("notes", "")
                    client_words = nf.cleaned_data.get("client_words", "")
                    progress_descriptor = nf.cleaned_data.get("progress_descriptor", "")
                    # Check if any data was entered for this target
                    has_metrics = any(
                        mf.cleaned_data.get("value", "") for mf in tf["metric_forms"]
                    )
                    if not notes_text and not has_metrics and not client_words and not progress_descriptor:
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
                        val = mf.cleaned_data.get("value", "")
                        if val:
                            MetricValue.objects.create(
                                progress_note_target=pnt,
                                metric_def_id=mf.cleaned_data["metric_def_id"],
                                value=val,
                            )

                # Auto-complete any pending follow-ups from this author for this client
                ProgressNote.objects.filter(
                    client_file=client,
                    author=request.user,
                    follow_up_date__isnull=False,
                    follow_up_completed_at__isnull=True,
                    status="default",
                ).exclude(pk=note.pk).update(follow_up_completed_at=timezone.now())

            messages.success(request, _("Progress note saved."))
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = FullNoteForm(initial={"session_date": timezone.localdate()})
        target_forms = _build_target_forms(client)

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
    })


@login_required
@programme_role_required("staff", _get_programme_from_note)
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
            return render(request, "notes/_note_detail.html", {
                "note": note,
                "client": None,
                "target_entries": [],
                "error": "This note has a data integrity issue. Please contact support.",
            })

        # Middleware already verified access; this is a redundant safety check
        client = _get_client_or_403(request, note.client_file_id)
        if client is None:
            logger.warning(
                "Permission denied in note_detail for user=%s note=%s client=%s",
                request.user.pk, note_id, note.client_file_id
            )
            return HttpResponseForbidden("You do not have access to this client.")

        # Filter out any orphaned entries (plan_target deleted outside Django)
        target_entries = list(
            ProgressNoteTarget.objects.filter(progress_note=note, plan_target__isnull=False)
            .select_related("plan_target")
            .prefetch_related("metric_values__metric_def")
        )
        return render(request, "notes/_note_detail.html", {
            "note": note,
            "client": client,
            "target_entries": target_entries,
        })
    except Exception as e:
        logger.exception(
            "Unexpected error in note_detail for user=%s note_id=%s: %s",
            getattr(request, 'user', None), note_id, e
        )
        raise


@login_required
@programme_role_required("staff", _get_programme_from_note)
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
            return HttpResponseForbidden("You do not have access to this client.")
        return render(request, "notes/_note_summary.html", {"note": note, "client": client})
    except Exception as e:
        logger.exception(
            "Unexpected error in note_summary for user=%s note_id=%s: %s",
            getattr(request, 'user', None), note_id, e
        )
        raise


@login_required
@programme_role_required("staff", _get_programme_from_note)
def note_cancel(request, note_id):
    """Cancel a progress note (staff: own notes within 24h, program_manager: any in their program)."""
    note = get_object_or_404(ProgressNote, pk=note_id)
    client = _get_client_or_403(request, note.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    user = request.user
    # Permission check — program managers can cancel any note in their programs
    # Use programme_role_required's attribute first, fall back to middleware's
    user_role = getattr(request, "user_programme_role", None) or getattr(request, "user_program_role", None)
    if user_role != "program_manager":
        if note.author_id != user.pk:
            return HttpResponseForbidden("You can only cancel your own notes.")
        age = timezone.now() - note.created_at
        if age.total_seconds() > 86400:
            return HttpResponseForbidden("Notes can only be cancelled within 24 hours.")

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
@programme_role_required("staff", _get_programme_from_client)
def qualitative_summary(request, client_id):
    """Show qualitative progress summary — descriptor distribution and recent client words per target."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Get all active plan targets for this client
    targets = (
        PlanTarget.objects.filter(client_file=client, status="default")
        .select_related("plan_section")
        .order_by("plan_section__sort_order", "sort_order")
    )

    target_data = []
    for target in targets:
        entries = (
            ProgressNoteTarget.objects.filter(
                plan_target=target,
                progress_note__status="default",
            )
            .select_related("progress_note")
            .order_by("-progress_note__created_at")
        )
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
    })
