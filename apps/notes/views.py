# Phase 4: Progress note views
"""Views for progress notes — quick notes, full notes, timeline, cancellation."""
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.plans.models import PlanTarget, PlanTargetMetric
from apps.programs.models import UserProgramRole

from .forms import FullNoteForm, MetricValueForm, NoteCancelForm, QuickNoteForm, TargetNoteForm
from .models import MetricValue, ProgressNote, ProgressNoteTarget


def _get_client_or_403(request, client_id):
    """Return client if user has access, otherwise 403."""
    client = get_object_or_404(ClientFile, pk=client_id)
    user = request.user
    if user.is_admin:
        return client
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
def note_list(request, client_id):
    """Notes timeline for a client with filtering and pagination."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    notes = ProgressNote.objects.filter(client_file=client).select_related("author", "author_program")

    # Filters
    note_type = request.GET.get("type", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    author_filter = request.GET.get("author", "")

    if note_type in ("quick", "full"):
        notes = notes.filter(note_type=note_type)
    if date_from:
        try:
            notes = notes.filter(effective_date__gte=datetime.date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            notes = notes.filter(effective_date__lte=datetime.date.fromisoformat(date_to))
        except ValueError:
            pass
    if author_filter == "mine":
        notes = notes.filter(author=request.user)

    notes = notes.order_by("-effective_date", "-created_at")
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
    }
    if request.headers.get("HX-Request"):
        return render(request, "notes/_tab_notes.html", context)
    return render(request, "notes/note_list.html", context)


@login_required
def quick_note_create(request, client_id):
    """Create a quick note for a client."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    if request.method == "POST":
        form = QuickNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.client_file = client
            note.note_type = "quick"
            note.author = request.user
            note.author_program = _get_author_program(request.user, client)
            note.save()
            messages.success(request, "Quick note saved.")
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = QuickNoteForm()

    return render(request, "notes/quick_note_form.html", {
        "form": form,
        "client": client,
    })


@login_required
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
                )
                if form.cleaned_data.get("backdate"):
                    note.backdate = timezone.make_aware(
                        timezone.datetime.combine(
                            form.cleaned_data["backdate"],
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

            messages.success(request, "Progress note saved.")
            return redirect("notes:note_list", client_id=client.pk)
    else:
        form = FullNoteForm()
        target_forms = _build_target_forms(client)

    return render(request, "notes/note_form.html", {
        "form": form,
        "target_forms": target_forms,
        "client": client,
    })


@login_required
def note_detail(request, note_id):
    """HTMX partial: expanded view of a single note."""
    note = get_object_or_404(
        ProgressNote.objects.select_related("author", "author_program", "template"),
        pk=note_id,
    )
    client = _get_client_or_403(request, note.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    target_entries = (
        ProgressNoteTarget.objects.filter(progress_note=note)
        .select_related("plan_target")
        .prefetch_related("metric_values__metric_def")
    )
    return render(request, "notes/_note_detail.html", {
        "note": note,
        "client": client,
        "target_entries": target_entries,
    })


@login_required
def note_summary(request, note_id):
    """HTMX partial: collapsed summary of a single note (reverses note_detail expand)."""
    note = get_object_or_404(
        ProgressNote.objects.select_related("author", "author_program"),
        pk=note_id,
    )
    client = _get_client_or_403(request, note.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")
    return render(request, "notes/_note_summary.html", {"note": note, "client": client})


@login_required
def note_cancel(request, note_id):
    """Cancel a progress note (staff: own notes within 24h, admin: any)."""
    note = get_object_or_404(ProgressNote, pk=note_id)
    client = _get_client_or_403(request, note.client_file_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    user = request.user
    # Permission check
    if not user.is_admin:
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
