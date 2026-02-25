"""Views for DV-safe mode: setting/removing the DV safety flag.

PERM-P5: When is_dv_safe is True on a ClientFile, DV-sensitive custom
fields are hidden from front desk staff. Any worker on the case can
set the flag (safety first). Removing requires a two-person-rule
workflow: staff recommends, PM approves.

The front desk must NEVER see that the flag is set or any related UI.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.admin_settings.models import get_access_tier
from apps.audit.models import AuditLog
from apps.programs.models import UserProgramRole

from .models import ClientFile, DvFlagRemovalRequest
from .views import get_client_queryset


def _is_staff_or_above(user):
    """Return True if user has staff, PM, or executive role anywhere."""
    if getattr(user, "is_admin", False):
        return True
    return UserProgramRole.objects.filter(
        user=user,
        role__in=["staff", "program_manager", "executive"],
    ).exists()


def _is_pm_or_above(user):
    """Return True if user is PM, executive, or admin."""
    if getattr(user, "is_admin", False):
        return True
    return UserProgramRole.objects.filter(
        user=user,
        role__in=["program_manager", "executive"],
    ).exists()


@login_required
def dv_safe_enable(request, client_id):
    """Set the DV safety flag on a client. Staff+ only, Tier 2+.

    Any worker on the case can set this unilaterally (safety first).
    POST only.
    """
    if request.method != "POST":
        return HttpResponseForbidden()

    # Tier check: DV-safe not available at Tier 1
    tier = get_access_tier()
    if tier < 2:
        return HttpResponseForbidden(_("DV-safe mode is not available at this access tier."))

    # Role check: staff+ only
    if not _is_staff_or_above(request.user):
        return HttpResponseForbidden(_("You do not have permission to set the DV safety flag."))

    client = get_object_or_404(get_client_queryset(request.user), pk=client_id)

    if client.is_dv_safe:
        messages.info(request, _("DV safety flag is already enabled for this participant."))
        return redirect("clients:client_detail", client_id=client.pk)

    client.is_dv_safe = True
    client.save(update_fields=["is_dv_safe"])

    # Audit log
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=str(request.user),
        action="create",
        resource_type="dv_safe_flag",
        resource_id=str(client.pk),
        new_values={
            "client_id": client.pk,
            "is_dv_safe": True,
            "set_by": request.user.username,
        },
    )

    messages.success(request, _("DV safety flag has been enabled. Sensitive fields are now hidden from front desk staff."))
    return redirect("clients:client_detail", client_id=client.pk)


@login_required
def dv_safe_request_remove(request, client_id):
    """Staff recommends removal of the DV safety flag (step 1 of 2).

    GET: show form with reason field.
    POST: create DvFlagRemovalRequest.
    """
    tier = get_access_tier()
    if tier < 2:
        return HttpResponseForbidden(_("DV-safe mode is not available at this access tier."))

    if not _is_staff_or_above(request.user):
        return HttpResponseForbidden()

    client = get_object_or_404(get_client_queryset(request.user), pk=client_id)

    if not client.is_dv_safe:
        messages.info(request, _("DV safety flag is not enabled for this participant."))
        return redirect("clients:client_detail", client_id=client.pk)

    # Check for existing pending request
    pending = DvFlagRemovalRequest.objects.filter(
        client_file=client, approved__isnull=True,
    ).exists()

    if request.method == "POST":
        if pending:
            messages.warning(request, _("A removal request is already pending for this participant."))
            return redirect("clients:client_detail", client_id=client.pk)

        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, _("Please provide a reason for removing the DV safety flag."))
            return render(request, "clients/dv_request_remove.html", {
                "client": client,
                "error": True,
            })

        DvFlagRemovalRequest.objects.create(
            client_file=client,
            requested_by=request.user,
            reason=reason,
        )

        # Audit log
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.pk,
            user_display=str(request.user),
            action="create",
            resource_type="dv_removal_request",
            resource_id=str(client.pk),
            new_values={
                "client_id": client.pk,
                "requested_by": request.user.username,
                "reason": reason,
            },
        )

        messages.success(request, _("Removal request submitted. A program manager must review and approve it."))
        return redirect("clients:client_detail", client_id=client.pk)

    return render(request, "clients/dv_request_remove.html", {
        "client": client,
        "pending": pending,
    })


@login_required
def dv_safe_review_remove(request, client_id, request_id):
    """PM reviews a DV flag removal request (step 2 of 2).

    GET: show the request details with approve/reject buttons.
    POST: approve or reject.
    """
    tier = get_access_tier()
    if tier < 2:
        return HttpResponseForbidden()

    if not _is_pm_or_above(request.user):
        return HttpResponseForbidden(_("Only program managers can review DV flag removal requests."))

    client = get_object_or_404(get_client_queryset(request.user), pk=client_id)
    removal_request = get_object_or_404(
        DvFlagRemovalRequest,
        pk=request_id,
        client_file=client,
        approved__isnull=True,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        review_note = request.POST.get("review_note", "").strip()

        if action == "approve":
            removal_request.approved = True
            removal_request.reviewed_by = request.user
            removal_request.reviewed_at = timezone.now()
            removal_request.review_note = review_note
            removal_request.save()

            # Remove the DV flag
            client.is_dv_safe = False
            client.save(update_fields=["is_dv_safe"])

            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=str(request.user),
                action="update",
                resource_type="dv_safe_flag",
                resource_id=str(client.pk),
                new_values={
                    "client_id": client.pk,
                    "is_dv_safe": False,
                    "approved_by": request.user.username,
                    "removal_request_id": removal_request.pk,
                    "review_note": review_note,
                },
            )

            messages.success(request, _("DV safety flag has been removed."))

        elif action == "reject":
            removal_request.approved = False
            removal_request.reviewed_by = request.user
            removal_request.reviewed_at = timezone.now()
            removal_request.review_note = review_note
            removal_request.save()

            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=str(request.user),
                action="update",
                resource_type="dv_removal_request",
                resource_id=str(client.pk),
                new_values={
                    "client_id": client.pk,
                    "rejected_by": request.user.username,
                    "removal_request_id": removal_request.pk,
                    "review_note": review_note,
                },
            )

            messages.info(request, _("Removal request has been rejected. The DV safety flag remains active."))
        else:
            return HttpResponseForbidden()

        return redirect("clients:client_detail", client_id=client.pk)

    return render(request, "clients/dv_review_remove.html", {
        "client": client,
        "removal_request": removal_request,
    })
