"""Bulk operation wizard views — Transfer and Discharge.

Each operation follows a 3-step wizard:
  Step 1 (GET):  Filter participants by program/status
  Step 2 (POST): Select participants from filtered list, confirm
  Step 3 (POST): Execute the operation

Session stores selected IDs between steps (30-minute expiry).
"""
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.audit.models import AuditLog
from apps.auth_app.decorators import requires_permission
from apps.programs.access import get_accessible_programs

from .bulk_forms import BulkDischargeConfirmForm, BulkFilterForm, BulkTransferConfirmForm
from .models import ClientFile, ClientProgramEnrolment, ServiceEpisodeStatusChange
from .views import _get_accessible_clients, get_client_queryset


SESSION_EXPIRY_SECONDS = 30 * 60  # 30 minutes


def _get_session_key(operation):
    return f"bulk_{operation}"


def _store_selection(request, operation, client_ids, source_program_id=None):
    """Store selected client IDs in session with timestamp."""
    request.session[_get_session_key(operation)] = {
        "client_ids": client_ids,
        "source_program_id": source_program_id,
        "timestamp": time.time(),
    }


def _load_selection(request, operation):
    """Load selected client IDs from session, checking expiry."""
    data = request.session.get(_get_session_key(operation))
    if not data:
        return None
    elapsed = time.time() - data.get("timestamp", 0)
    if elapsed > SESSION_EXPIRY_SECONDS:
        del request.session[_get_session_key(operation)]
        return None
    return data


def _clear_selection(request, operation):
    """Remove selection from session."""
    key = _get_session_key(operation)
    if key in request.session:
        del request.session[key]


def _get_filtered_clients(request, source_program_id=None, status_filter="active"):
    """Return accessible clients filtered by program and status."""
    active_ids = getattr(request, "active_program_ids", None)
    clients = _get_accessible_clients(request.user, active_program_ids=active_ids)

    if source_program_id:
        enrolled_ids = ClientProgramEnrolment.objects.filter(
            program_id=source_program_id,
            status__in=["active", "on_hold"] if status_filter == "all" else [status_filter],
        ).values_list("client_file_id", flat=True)
        clients = clients.filter(pk__in=enrolled_ids)
    elif status_filter != "all":
        enrolled_ids = ClientProgramEnrolment.objects.filter(
            status=status_filter,
        ).values_list("client_file_id", flat=True)
        clients = clients.filter(pk__in=enrolled_ids)

    return clients


# ---------------------------------------------------------------------------
# Bulk Transfer Wizard
# ---------------------------------------------------------------------------

@login_required
@requires_permission("client.transfer")
def bulk_transfer(request):
    """Bulk transfer wizard — filter, select, confirm, execute."""
    active_ids = getattr(request, "active_program_ids", None)
    available_programs = get_accessible_programs(request.user, active_program_ids=active_ids)

    # Step 3: Execute transfer (POST with 'execute')
    if request.method == "POST" and "execute" in request.POST:
        return _bulk_transfer_execute(request, available_programs)

    # Step 2: Show confirm page (POST with selected client IDs)
    if request.method == "POST" and "confirm" in request.POST:
        return _bulk_transfer_confirm(request, available_programs)

    # Step 1: Filter page (GET)
    filter_form = BulkFilterForm(
        request.GET or None,
        available_programs=available_programs,
    )

    source_program_id = None
    status_filter = "active"
    clients = None
    count = 0

    if filter_form.is_valid():
        source_program = filter_form.cleaned_data.get("source_program")
        source_program_id = source_program.pk if source_program else None
        status_filter = filter_form.cleaned_data.get("status_filter") or "active"
        clients = _get_filtered_clients(request, source_program_id, status_filter)
        count = clients.count()

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": "", "label": _("Bulk Transfer")},
    ]

    context = {
        "filter_form": filter_form,
        "clients": clients,
        "client_count": count,
        "breadcrumbs": breadcrumbs,
        "available_programs": available_programs,
        "nav_active": "admin",
    }

    # HTMX: return just the participant table partial
    if request.headers.get("HX-Request") and "filter" in request.GET:
        return render(request, "clients/bulk/_participant_table.html", context)

    return render(request, "clients/bulk/transfer.html", context)


def _bulk_transfer_confirm(request, available_programs):
    """Step 2: Show confirmation page with selected participants."""
    selected_ids = request.POST.getlist("selected_clients")
    try:
        client_ids = [int(x) for x in selected_ids if x.strip()]
    except (ValueError, TypeError):
        messages.error(request, _("Invalid selection."))
        return redirect("clients:bulk_transfer_wizard")

    if not client_ids:
        messages.error(request, _("No participants selected."))
        return redirect("clients:bulk_transfer_wizard")

    source_program_id = request.POST.get("source_program_id")
    source_program_id = int(source_program_id) if source_program_id else None

    # Store in session for the execute step
    _store_selection(request, "transfer", client_ids, source_program_id)

    # Load actual client objects (security: filter to accessible)
    active_ids = getattr(request, "active_program_ids", None)
    accessible = _get_accessible_clients(request.user, active_program_ids=active_ids)
    selected_clients = list(accessible.filter(pk__in=client_ids))

    if not selected_clients:
        messages.error(request, _("None of the selected participants are accessible."))
        return redirect("clients:bulk_transfer_wizard")

    confirm_form = BulkTransferConfirmForm(
        initial={"client_ids": ",".join(str(c.pk) for c in selected_clients)},
        available_programs=available_programs,
    )

    # Check for consent warnings
    consent_warnings = []
    for client in selected_clients:
        if getattr(client, "cross_program_sharing", "default") == "restrict":
            consent_warnings.append(client)

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:bulk_transfer_wizard"), "label": _("Bulk Transfer")},
        {"url": "", "label": _("Confirm")},
    ]

    return render(request, "clients/bulk/transfer_confirm.html", {
        "confirm_form": confirm_form,
        "selected_clients": selected_clients,
        "consent_warnings": consent_warnings,
        "breadcrumbs": breadcrumbs,
        "nav_active": "admin",
    })


def _bulk_transfer_execute(request, available_programs):
    """Step 3: Execute the bulk transfer."""
    # Load selection from session
    selection = _load_selection(request, "transfer")
    if not selection:
        messages.error(request, _("Your selection has expired. Please start again."))
        return redirect("clients:bulk_transfer_wizard")

    confirm_form = BulkTransferConfirmForm(request.POST, available_programs=available_programs)
    if not confirm_form.is_valid():
        # Re-render confirm page with errors
        active_ids = getattr(request, "active_program_ids", None)
        accessible = _get_accessible_clients(request.user, active_program_ids=active_ids)
        selected_clients = list(accessible.filter(pk__in=selection["client_ids"]))
        breadcrumbs = [
            {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
            {"url": reverse("clients:bulk_transfer_wizard"), "label": _("Bulk Transfer")},
            {"url": "", "label": _("Confirm")},
        ]
        return render(request, "clients/bulk/transfer_confirm.html", {
            "confirm_form": confirm_form,
            "selected_clients": selected_clients,
            "consent_warnings": [],
            "breadcrumbs": breadcrumbs,
            "nav_active": "admin",
        })

    client_ids = confirm_form.cleaned_data["client_ids"]
    destination = confirm_form.cleaned_data["destination_program"]
    reason = confirm_form.cleaned_data.get("transfer_reason", "")
    source_program_id = selection.get("source_program_id")

    # Security: filter to accessible clients only
    active_ids = getattr(request, "active_program_ids", None)
    accessible = _get_accessible_clients(request.user, active_program_ids=active_ids)
    clients_to_transfer = list(accessible.filter(pk__in=client_ids))

    now = timezone.now()
    transferred_count = 0

    with transaction.atomic():
        for client_obj in clients_to_transfer:
            added = False
            removed = False

            # Remove from source program (if specified)
            if source_program_id:
                episodes = list(ClientProgramEnrolment.objects.filter(
                    client_file=client_obj,
                    program_id=source_program_id,
                    status="active",
                ))
                for ep in episodes:
                    ep.status = "finished"
                    ep.ended_at = now
                    ep.unenrolled_at = now
                    ep.end_reason = "transferred"
                    ep.save()
                    ServiceEpisodeStatusChange.objects.create(
                        episode=ep,
                        status="finished",
                        reason="Bulk transfer to another program",
                        changed_by=request.user,
                    )
                    removed = True

            # Add to destination program (idempotent)
            enrolment, created = ClientProgramEnrolment.objects.get_or_create(
                client_file=client_obj, program=destination,
                defaults={"status": "active", "started_at": now},
            )
            if created:
                ServiceEpisodeStatusChange.objects.create(
                    episode=enrolment,
                    status="active",
                    reason="Enrolled via bulk transfer",
                    changed_by=request.user,
                )
                added = True
            elif enrolment.status != "active":
                enrolment.status = "active"
                enrolment.unenrolled_at = None
                enrolment.save()
                added = True

            if added or removed:
                transferred_count += 1

            # Individual audit log entry per participant
            AuditLog.objects.using("audit").create(
                event_timestamp=now,
                user_id=request.user.pk,
                user_display=getattr(request.user, "display_name", str(request.user)),
                action="update",
                resource_type="enrolment",
                resource_id=client_obj.pk,
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={
                    "bulk_transfer": True,
                    "source_program_id": source_program_id,
                    "destination_program_id": destination.pk,
                    "reason": reason,
                },
            )

    _clear_selection(request, "transfer")

    messages.success(
        request,
        _("%(count)d %(term)s transferred to %(program)s.") % {
            "count": transferred_count,
            "term": request.get_term("client_plural") if transferred_count != 1 else request.get_term("client"),
            "program": destination.translated_name,
        },
    )
    return redirect("clients:client_list")


# ---------------------------------------------------------------------------
# Bulk Discharge Wizard
# ---------------------------------------------------------------------------

@login_required
@requires_permission("client.transfer")
def bulk_discharge(request):
    """Bulk discharge wizard — filter, select, confirm, execute."""
    active_ids = getattr(request, "active_program_ids", None)
    available_programs = get_accessible_programs(request.user, active_program_ids=active_ids)

    # Step 3: Execute discharge (POST with 'execute')
    if request.method == "POST" and "execute" in request.POST:
        return _bulk_discharge_execute(request, available_programs)

    # Step 2: Show confirm page (POST with selected client IDs)
    if request.method == "POST" and "confirm" in request.POST:
        return _bulk_discharge_confirm(request, available_programs)

    # Step 1: Filter page (GET) — discharge requires a source program
    filter_form = BulkFilterForm(
        request.GET or None,
        available_programs=available_programs,
    )
    # Make source_program required for discharge
    filter_form.fields["source_program"].required = True
    filter_form.fields["source_program"].empty_label = _("— Select program —")

    source_program_id = None
    status_filter = "active"
    clients = None
    count = 0

    if filter_form.is_valid():
        source_program = filter_form.cleaned_data.get("source_program")
        source_program_id = source_program.pk if source_program else None
        status_filter = filter_form.cleaned_data.get("status_filter") or "active"
        if source_program_id:
            clients = _get_filtered_clients(request, source_program_id, status_filter)
            count = clients.count()

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": "", "label": _("Bulk Discharge")},
    ]

    context = {
        "filter_form": filter_form,
        "clients": clients,
        "client_count": count,
        "breadcrumbs": breadcrumbs,
        "available_programs": available_programs,
        "nav_active": "admin",
    }

    if request.headers.get("HX-Request") and "filter" in request.GET:
        return render(request, "clients/bulk/_participant_table.html", context)

    return render(request, "clients/bulk/discharge.html", context)


def _bulk_discharge_confirm(request, available_programs):
    """Step 2: Show confirmation page with selected participants."""
    selected_ids = request.POST.getlist("selected_clients")
    try:
        client_ids = [int(x) for x in selected_ids if x.strip()]
    except (ValueError, TypeError):
        messages.error(request, _("Invalid selection."))
        return redirect("clients:bulk_discharge_wizard")

    if not client_ids:
        messages.error(request, _("No participants selected."))
        return redirect("clients:bulk_discharge_wizard")

    source_program_id = request.POST.get("source_program_id")
    if not source_program_id:
        messages.error(request, _("Please select a program."))
        return redirect("clients:bulk_discharge_wizard")
    source_program_id = int(source_program_id)

    _store_selection(request, "discharge", client_ids, source_program_id)

    active_ids = getattr(request, "active_program_ids", None)
    accessible = _get_accessible_clients(request.user, active_program_ids=active_ids)
    selected_clients = list(accessible.filter(pk__in=client_ids))

    if not selected_clients:
        messages.error(request, _("None of the selected participants are accessible."))
        return redirect("clients:bulk_discharge_wizard")

    from apps.programs.models import Program
    source_program = get_object_or_404(Program, pk=source_program_id)

    confirm_form = BulkDischargeConfirmForm(
        initial={
            "client_ids": ",".join(str(c.pk) for c in selected_clients),
            "source_program": source_program_id,
        },
        available_programs=available_programs,
    )

    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:bulk_discharge_wizard"), "label": _("Bulk Discharge")},
        {"url": "", "label": _("Confirm")},
    ]

    return render(request, "clients/bulk/discharge_confirm.html", {
        "confirm_form": confirm_form,
        "selected_clients": selected_clients,
        "source_program": source_program,
        "breadcrumbs": breadcrumbs,
        "nav_active": "admin",
    })


def _bulk_discharge_execute(request, available_programs):
    """Step 3: Execute the bulk discharge."""
    selection = _load_selection(request, "discharge")
    if not selection:
        messages.error(request, _("Your selection has expired. Please start again."))
        return redirect("clients:bulk_discharge_wizard")

    confirm_form = BulkDischargeConfirmForm(request.POST, available_programs=available_programs)
    if not confirm_form.is_valid():
        active_ids = getattr(request, "active_program_ids", None)
        accessible = _get_accessible_clients(request.user, active_program_ids=active_ids)
        selected_clients = list(accessible.filter(pk__in=selection["client_ids"]))
        from apps.programs.models import Program
        source_program = get_object_or_404(Program, pk=selection["source_program_id"])
        breadcrumbs = [
            {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
            {"url": reverse("clients:bulk_discharge_wizard"), "label": _("Bulk Discharge")},
            {"url": "", "label": _("Confirm")},
        ]
        return render(request, "clients/bulk/discharge_confirm.html", {
            "confirm_form": confirm_form,
            "selected_clients": selected_clients,
            "source_program": source_program,
            "breadcrumbs": breadcrumbs,
            "nav_active": "admin",
        })

    client_ids = confirm_form.cleaned_data["client_ids"]
    source_program = confirm_form.cleaned_data["source_program"]
    end_reason = confirm_form.cleaned_data["end_reason"]
    status_reason = confirm_form.cleaned_data.get("status_reason", "")

    active_ids = getattr(request, "active_program_ids", None)
    accessible = _get_accessible_clients(request.user, active_program_ids=active_ids)
    clients_to_discharge = list(accessible.filter(pk__in=client_ids))

    now = timezone.now()
    discharged_count = 0

    with transaction.atomic():
        for client_obj in clients_to_discharge:
            episodes = list(ClientProgramEnrolment.objects.filter(
                client_file=client_obj,
                program=source_program,
                status="active",
            ))
            for ep in episodes:
                ep.status = "finished"
                ep.ended_at = now
                ep.unenrolled_at = now
                ep.end_reason = end_reason
                ep.status_reason = status_reason
                ep.save()
                ServiceEpisodeStatusChange.objects.create(
                    episode=ep,
                    status="finished",
                    reason=f"Bulk discharge: {ep.get_end_reason_display()}",
                    changed_by=request.user,
                )
                discharged_count += 1

            # Individual audit log entry per participant
            AuditLog.objects.using("audit").create(
                event_timestamp=now,
                user_id=request.user.pk,
                user_display=getattr(request.user, "display_name", str(request.user)),
                action="update",
                resource_type="enrolment",
                resource_id=client_obj.pk,
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={
                    "bulk_discharge": True,
                    "program_id": source_program.pk,
                    "end_reason": end_reason,
                    "status_reason": status_reason,
                },
            )

    _clear_selection(request, "discharge")

    messages.success(
        request,
        _("%(count)d %(term)s discharged from %(program)s.") % {
            "count": discharged_count,
            "term": request.get_term("client_plural") if discharged_count != 1 else request.get_term("client"),
            "program": source_program.translated_name,
        },
    )
    return redirect("clients:client_list")
