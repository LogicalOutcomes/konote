# Phase 4: Progress note views
"""Views for progress notes — quick notes, full notes, timeline, cancellation."""
import datetime
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import DateTimeField
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

logger = logging.getLogger(__name__)

from apps.auth_app.decorators import minimum_role
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import PlanTarget, PlanTargetMetric
from apps.programs.models import UserProgramRole

from .forms import FullNoteForm, MetricValueForm, NoteCancelForm, QuickNoteForm, TargetNoteForm
from .models import MetricValue, ProgressNote, ProgressNoteTarget


def _get_client_or_403(request, client_id):
    """Return client if user has access, otherwise 403.

    Access is based on program roles — admins without program roles cannot access.
    """
    client = get_object_or_404(ClientFile, pk=client_id)
    user = request.user
    user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(client_file=client, status="enrolled")
        .values_list("program_id", flat=True)
    )
    if user_program_ids & client_program_ids:
        return client
    return None


def _get_author_program(user, client):
    """Return the first program the user shares with this client, or None."""
    user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(client_file=client, status="enrolled")
        .values_list("program_id", flat=True)
    )
    shared = user_program_ids & client_program_ids
    if shared:
        from apps.programs.models import Program
        return Program.objects.filter(pk__in=shared).first()
    return None


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


@login_required
@minimum_role("staff")
def note_list(request, client_id):
    """Notes timeline for a client with filtering and pagination."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Annotate with computed effective_date for filtering and ordering
    # (backdate if set, otherwise created_at)
    notes = (
        ProgressNote.objects.filter(client_file=client)
        .select_related("author", "author_program")
        .annotate(
            _effective_date=Coalesce("backdate", "created_at", output_field=DateTimeField())
        )
    )

    # Filters
    note_type = request.GET.get("type", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    author_filter = request.GET.get("author", "")

    if note_type in ("quick", "full"):
        notes = notes.filter(note_type=note_type)
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

    notes = notes.order_by("-_effective_date", "-created_at")
    paginator = Paginator(notes, 25)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "client": client,
        "page": page,
        "filter_type": note_type,
        "filter_date_from": date_from,
        "filter_date_to": date_to,
        "filter_author": author_filter,
        "active_tab": "notes",
        "user_role": getattr(request, "user_program_role", None),
    }
    if request.headers.get("HX-Request"):
        return render(request, "notes/_tab_notes.html", context)
    return render(request, "notes/note_list.html", context)


@login_required
@minimum_role("staff")
def quick_note_create(request, client_id):
    """Create a quick note for a client."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    if request.method == "POST":
        form = QuickNoteForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                note = form.save(commit=False)
                note.client_file = client
                note.note_type = "quick"
                note.author = request.user
                note.author_program = _get_author_program(request.user, client)
                note.save()

                # Auto-complete any pending follow-ups from this author for this client
                ProgressNote.objects.filter(
                    client_file=client,
                    author=request.user,
                    follow_up_date__isnull=False,
                    follow_up_completed_at__isnull=True,
                    status="default",
                ).update(follow_up_completed_at=timezone.now())

            messages.success(request, "Quick note saved.")
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = QuickNoteForm()

    return render(request, "notes/quick_note_form.html", {
        "form": form,
        "client": client,
    })


@login_required
@minimum_role("staff")
def note_create(request, client_id):
    """Create a full structured progress note with target entries and metric values."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

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
                    author=request.user,
                    author_program=_get_author_program(request.user, client),
                    template=form.cleaned_data.get("template"),
                    summary=form.cleaned_data.get("summary", ""),
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
                    # Check if any data was entered for this target
                    has_metrics = any(
                        mf.cleaned_data.get("value", "") for mf in tf["metric_forms"]
                    )
                    if not notes_text and not has_metrics:
                        continue  # Skip targets with no data entered

                    pnt = ProgressNoteTarget.objects.create(
                        progress_note=note,
                        plan_target_id=nf.cleaned_data["target_id"],
                        notes=notes_text,
                    )
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

            messages.success(request, "Progress note saved.")
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = FullNoteForm(initial={"session_date": timezone.localdate()})
        target_forms = _build_target_forms(client)

    return render(request, "notes/note_form.html", {
        "form": form,
        "target_forms": target_forms,
        "client": client,
    })


@login_required
@minimum_role("staff")
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
@minimum_role("staff")
def note_summary(request, note_id):
    """HTMX partial: collapsed summary of a single note (reverses note_detail expand)."""
    try:
        note = get_object_or_404(
            ProgressNote.objects.select_related("author", "author_program"),
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
@minimum_role("staff")
def note_cancel(request, note_id):
    """Cancel a progress note (staff: own notes within 24h, program_manager: any in their program)."""
    note = get_object_or_404(ProgressNote, pk=note_id)
    client = _get_client_or_403(request, note.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    user = request.user
    # Permission check — program managers can cancel any note in their programs
    user_role = getattr(request, "user_program_role", None)
    if user_role != "program_manager":
        if note.author_id != user.pk:
            return HttpResponseForbidden("You can only cancel your own notes.")
        age = timezone.now() - note.created_at
        if age.total_seconds() > 86400:
            return HttpResponseForbidden("Notes can only be cancelled within 24 hours.")

    if note.status == "cancelled":
        messages.info(request, "This note is already cancelled.")
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
                metadata={"reason": form.cleaned_data["status_reason"]},
            )
            messages.success(request, "Note cancelled.")
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = NoteCancelForm()

    return render(request, "notes/cancel_form.html", {
        "form": form,
        "note": note,
        "client": client,
    })
