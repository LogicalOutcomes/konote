"""PIPEDA data access request views — guided manual checklist process."""
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.auth_app.decorators import requires_permission

from .forms import DataAccessRequestForm, DataAccessCompleteForm
from .models import ClientFile, DataAccessRequest


@login_required
@requires_permission("client.edit")
def data_access_log(request, client_id):
    """Step 1: Log a new data access request for a participant."""
    from apps.programs.access import get_client_or_403
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = DataAccessRequestForm(request.POST)
        if form.is_valid():
            requested_at = form.cleaned_data["requested_at"]
            dar = DataAccessRequest.objects.create(
                client_file=client,
                requested_at=requested_at,
                request_method=form.cleaned_data["request_method"],
                deadline=requested_at + timedelta(days=30),
                created_by=request.user,
            )

            # Audit log
            from apps.audit.models import AuditLog
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=getattr(request.user, "display_name", str(request.user)),
                action="create",
                resource_type="data_access_request",
                resource_id=dar.pk,
                is_demo_context=getattr(request.user, "is_demo", False),
                metadata={
                    "client_pk": client.pk,
                    "requested_at": str(requested_at),
                    "deadline": str(dar.deadline),
                },
            )

            messages.success(request, _("Data access request logged."))
            return redirect("data_access:data_access_checklist", pk=dar.pk)
    else:
        form = DataAccessRequestForm(initial={"requested_at": date.today()})

    return render(request, "clients/data_access_log.html", {
        "client": client,
        "form": form,
    })


@login_required
@requires_permission("client.edit")
def data_access_checklist(request, pk):
    """Step 2: Display the checklist of information to gather."""
    from apps.programs.access import get_client_or_403

    dar = get_object_or_404(DataAccessRequest, pk=pk)
    client = get_client_or_403(request, dar.client_file_id)
    if client is None:
        return HttpResponseForbidden()

    return render(request, "clients/data_access_checklist.html", {
        "dar": dar,
        "client": client,
    })


@login_required
@requires_permission("client.edit")
def data_access_complete(request, pk):
    """Step 3: Mark the data access request as complete (POST only)."""
    from apps.programs.access import get_client_or_403

    dar = get_object_or_404(DataAccessRequest, pk=pk)
    client = get_client_or_403(request, dar.client_file_id)
    if client is None:
        return HttpResponseForbidden()

    if dar.completed_at:
        messages.info(request, _("This request has already been completed."))
        return redirect("data_access:data_access_checklist", pk=dar.pk)

    # POST-only — redirect GET to the checklist page
    if request.method != "POST":
        return redirect("data_access:data_access_checklist", pk=dar.pk)

    form = DataAccessCompleteForm(request.POST)
    if form.is_valid():
        dar.completed_at = form.cleaned_data["completed_at"]
        dar.delivery_method = form.cleaned_data["delivery_method"]
        dar.completed_by = request.user
        dar.save(update_fields=[
            "completed_at", "delivery_method", "completed_by",
        ])

        # Audit log
        from apps.audit.models import AuditLog
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.pk,
            user_display=getattr(request.user, "display_name", str(request.user)),
            action="update",
            resource_type="data_access_request",
            resource_id=dar.pk,
            is_demo_context=getattr(request.user, "is_demo", False),
            metadata={
                "client_pk": dar.client_file_id,
                "completed_at": str(dar.completed_at),
                "delivery_method": dar.delivery_method,
                "days_to_complete": (dar.completed_at - dar.requested_at).days,
            },
        )

        messages.success(request, _("Data access request marked as complete."))
        return redirect("data_access:data_access_checklist", pk=dar.pk)

    # Form invalid — redirect back (errors will surface via messages)
    return redirect("data_access:data_access_checklist", pk=dar.pk)
