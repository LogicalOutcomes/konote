"""Views for client data erasure workflow."""
import logging
from smtplib import SMTPException

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from django.template.exceptions import TemplateDoesNotExist

from apps.auth_app.decorators import minimum_role
from apps.events.models import Alert
from apps.programs.models import UserProgramRole

from .erasure import (
    build_data_summary,
    get_available_tiers,
    get_required_programs,
    is_deadlocked,
    record_approval,
)
from .forms import ErasureApprovalForm, ErasureRejectForm, ErasureRequestForm
from .models import ErasureRequest
from .views import get_client_queryset

logger = logging.getLogger(__name__)


from konote.utils import get_client_ip as _get_client_ip


def _user_is_pm_or_admin(user):
    """Check if user is a PM in any program or a system admin."""
    if user.is_admin:
        return True
    return UserProgramRole.objects.filter(
        user=user, role="program_manager", status="active",
    ).exists()


def _get_user_pm_program_ids(user):
    """Get program IDs where user is an active program manager."""
    return list(
        UserProgramRole.objects.filter(
            user=user, role="program_manager", status="active",
        ).values_list("program_id", flat=True)
    )


def _get_visible_requests(user, status_filter=None):
    """Get erasure requests visible to this user (PM-scoped or admin-all).

    Filters in Python since erasure requests are a small dataset and
    JSONField __contains is not supported on all backends (e.g. SQLite).
    """
    qs = ErasureRequest.objects.all().order_by("-requested_at")
    if status_filter:
        qs = qs.filter(status=status_filter)

    if user.is_admin:
        return qs  # Admins see all

    # PMs see requests for clients in their programs
    pm_program_ids = _get_user_pm_program_ids(user)
    if not pm_program_ids:
        return qs.none()

    # Filter in Python — works on all DB backends
    pids_set = set(pm_program_ids)
    matching_pks = [
        r.pk for r in qs
        if pids_set & set(r.programs_required or [])
    ]
    return qs.filter(pk__in=matching_pks)


# --- Request creation (PM+ only) ---

@login_required
@minimum_role("program_manager")
def erasure_request_create(request, client_id):
    """Create an erasure request for a client."""
    base_qs = get_client_queryset(request.user)
    client = get_object_or_404(base_qs, pk=client_id)

    # Block if client is already anonymised
    if client.is_anonymised:
        messages.info(request, _("This %(term)s's data has already been anonymised.") % {"term": request.get_term("client").lower()})
        return redirect("clients:client_detail", client_id=client.pk)

    # Check for existing pending request
    existing = ErasureRequest.objects.filter(
        client_file=client, status="pending",
    ).first()
    if existing:
        messages.info(request, _("An erasure request already exists for this %(term)s.") % {"term": request.get_term("client").lower()})
        return redirect("erasure_request_detail", pk=existing.pk)

    available_tiers = get_available_tiers(client)
    summary = build_data_summary(client)

    if request.method == "POST":
        form = ErasureRequestForm(request.POST, available_tiers=available_tiers)
        if form.is_valid():
            programs = get_required_programs(client)

            er = ErasureRequest.objects.create(
                client_file=client,
                client_pk=client.pk,
                client_record_id=client.record_id,
                data_summary=summary,
                requested_by=request.user,
                requested_by_display=request.user.get_display_name(),
                reason_category=form.cleaned_data["reason_category"],
                request_reason=form.cleaned_data["request_reason"],
                erasure_tier=form.cleaned_data["erasure_tier"],
                programs_required=programs,
            )

            # Set convenience flag on client
            client.erasure_requested = True
            client.save(update_fields=["erasure_requested"])

            # Send email notification to PMs
            email_sent = _notify_pms_erasure_request(er, request)

            messages.success(request, _("Erasure request created."))
            if email_sent:
                messages.info(request, _("Program managers have been notified by email."))
            else:
                messages.warning(
                    request,
                    _("Email notification failed. Please notify the program managers manually."),
                )
            return redirect("erasure_request_detail", pk=er.pk)
    else:
        form = ErasureRequestForm(available_tiers=available_tiers)

    active_alerts = Alert.objects.filter(client_file=client, status="default")

    return render(request, "clients/erasure/erasure_request_form.html", {
        "client": client,
        "form": form,
        "data_summary": summary,
        "active_alerts": active_alerts,
        "available_tiers": available_tiers,
        "nav_active": "clients",
    })


# --- Pending list (PM+ or admin) ---

@login_required
def erasure_pending_list(request):
    """List pending erasure requests."""
    if not _user_is_pm_or_admin(request.user):
        return HttpResponseForbidden(_("Access denied."))

    pending = _get_visible_requests(request.user, status_filter="pending")

    # Annotate each request with aging and stuck status
    now = timezone.now()
    for er in pending:
        er.is_stuck = is_deadlocked(er)
        er.days_pending = (now - er.requested_at).days

    return render(request, "clients/erasure/erasure_pending_list.html", {
        "pending_requests": pending,
        "nav_active": "admin",
    })


# --- Request detail (PM+ or admin) ---

@login_required
def erasure_request_detail(request, pk):
    """View details of an erasure request."""
    if not _user_is_pm_or_admin(request.user):
        return HttpResponseForbidden(_("Access denied."))

    er = get_object_or_404(ErasureRequest, pk=pk)

    # Build per-program approval status
    from apps.programs.models import Program
    program_status = []
    approved_program_ids = set(er.approvals.values_list("program_id", flat=True))
    user_pm_ids = set(_get_user_pm_program_ids(request.user))

    for prog_pk in er.programs_required:
        try:
            program = Program.objects.get(pk=prog_pk)
            program_name = program.name
        except Program.DoesNotExist:
            program_name = f"Program #{prog_pk} (deleted)"

        approval = er.approvals.filter(program_id=prog_pk).first()
        can_approve = (
            er.status == "pending"
            and prog_pk not in approved_program_ids
            and prog_pk in user_pm_ids
            and request.user != er.requested_by
        )
        program_status.append({
            "pk": prog_pk,
            "name": program_name,
            "approved": approval is not None,
            "approval": approval,
            "can_approve": can_approve,
        })

    # Current data counts (if client still exists)
    current_summary = None
    active_alerts = []
    if er.client_file:
        current_summary = build_data_summary(er.client_file)
        active_alerts = Alert.objects.filter(client_file=er.client_file, status="default")

    # Deadlock check — admin fallback
    deadlocked = is_deadlocked(er)
    admin_can_approve = deadlocked and request.user.is_admin and er.status == "pending"

    # PIPEDA 30-day aging
    days_pending = (timezone.now() - er.requested_at).days if er.status == "pending" else None

    approval_form = ErasureApprovalForm()
    reject_form = ErasureRejectForm()

    return render(request, "clients/erasure/erasure_request_detail.html", {
        "er": er,
        "program_status": program_status,
        "current_summary": current_summary,
        "active_alerts": active_alerts,
        "deadlocked": deadlocked,
        "admin_can_approve": admin_can_approve,
        "approval_form": approval_form,
        "reject_form": reject_form,
        "can_download_receipt": er.status == "pending" and er.client_file is not None,
        "receipt_not_downloaded": er.status == "pending" and er.receipt_downloaded_at is None,
        "days_pending": days_pending,
        "nav_active": "admin",
    })


# --- Approve (PM+ or admin fallback) ---

@login_required
@minimum_role("program_manager")
def erasure_approve(request, pk):
    """Record approval for a program within an erasure request."""
    if request.method != "POST":
        return redirect("erasure_request_detail", pk=pk)

    er = get_object_or_404(ErasureRequest, pk=pk)

    # Determine which program this PM is approving for
    program_id = request.POST.get("program_id")
    if not program_id:
        messages.error(request, _("No program specified."))
        return redirect("erasure_request_detail", pk=pk)

    from apps.programs.models import Program
    program = get_object_or_404(Program, pk=program_id)

    # Permission check: must be PM in this program, or admin fallback
    user_pm_ids = _get_user_pm_program_ids(request.user)
    deadlocked = is_deadlocked(er)
    is_admin_fb = deadlocked and request.user.is_admin

    if program.pk not in user_pm_ids and not is_admin_fb:
        return HttpResponseForbidden(_("You are not a program manager for this program."))

    form = ErasureApprovalForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Invalid form data."))
        return redirect("erasure_request_detail", pk=pk)

    try:
        approval, executed = record_approval(
            erasure_request=er,
            user=request.user,
            program=program,
            ip_address=_get_client_ip(request),
            review_notes=form.cleaned_data.get("review_notes", ""),
        )
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("erasure_request_detail", pk=pk)

    if executed:
        email_sent = _notify_erasure_completed(er, request)
        if er.erasure_tier == "full_erasure":
            messages.success(request, _("All approvals received. %(term)s data has been permanently erased.") % {"term": request.get_term("client")})
        else:
            messages.success(request, _("All approvals received. %(term)s data has been anonymised.") % {"term": request.get_term("client")})
        if not email_sent:
            messages.warning(
                request,
                _("Email notification failed. Please notify involved program managers manually."),
            )
        return redirect("erasure_history")
    else:
        messages.success(request, _("Approval recorded. Waiting for remaining program managers."))
        return redirect("erasure_request_detail", pk=pk)


# --- Reject (PM+) ---

@login_required
@minimum_role("program_manager")
def erasure_reject(request, pk):
    """Reject an erasure request. One rejection = whole request rejected."""
    if request.method != "POST":
        return redirect("erasure_request_detail", pk=pk)

    er = get_object_or_404(ErasureRequest, pk=pk, status="pending")
    form = ErasureRejectForm(request.POST)

    if not form.is_valid() or not form.cleaned_data["review_notes"].strip():
        messages.error(request, _("A reason for rejection is required."))
        return redirect("erasure_request_detail", pk=pk)

    # Must be PM in one of the required programs
    user_pm_ids = set(_get_user_pm_program_ids(request.user))
    if not (set(er.programs_required) & user_pm_ids):
        return HttpResponseForbidden(_("You are not a program manager for this participant's programs."))

    er.status = "rejected"
    er.save(update_fields=["status"])

    # Clear the convenience flag on the client (if still exists)
    if er.client_file:
        er.client_file.erasure_requested = False
        er.client_file.save(update_fields=["erasure_requested"])

    # Audit log
    from .erasure import _log_audit
    _log_audit(
        user=request.user,
        action="update",
        resource_type="erasure_request_rejected",
        resource_id=er.pk,
        ip_address=_get_client_ip(request),
        metadata={
            "client_pk": er.client_pk,
            "record_id": er.client_record_id,
            "review_notes": form.cleaned_data["review_notes"],
            "rejected_by": request.user.get_display_name(),
        },
    )

    # Notify the requester
    email_sent = _notify_requester_rejection(er, request.user, form.cleaned_data["review_notes"])

    messages.success(request, _("Erasure request rejected. %(term)s data has been preserved.") % {"term": request.get_term("client")})
    if not email_sent:
        messages.warning(
            request,
            _("Email notification to the requester failed. Please notify them manually."),
        )
    return redirect("erasure_pending_list")


# --- Cancel (requester or PM) ---

@login_required
@minimum_role("program_manager")
def erasure_cancel(request, pk):
    """Cancel a pending erasure request."""
    if request.method != "POST":
        return redirect("erasure_request_detail", pk=pk)

    er = get_object_or_404(ErasureRequest, pk=pk, status="pending")

    # Permission: requester or PM in one of the required programs
    is_requester = (request.user == er.requested_by)
    user_pm_ids = set(_get_user_pm_program_ids(request.user))
    is_pm_for_client = bool(set(er.programs_required) & user_pm_ids)

    if not is_requester and not is_pm_for_client:
        return HttpResponseForbidden(_("You cannot cancel this request."))

    er.status = "cancelled"
    er.save(update_fields=["status"])

    # Clear the convenience flag on the client (if still exists)
    if er.client_file:
        er.client_file.erasure_requested = False
        er.client_file.save(update_fields=["erasure_requested"])

    messages.success(request, _("Erasure request cancelled."))
    return redirect("erasure_pending_list")


# --- History (PM+ or admin) ---

@login_required
def erasure_history(request):
    """Show history of all erasure requests."""
    if not _user_is_pm_or_admin(request.user):
        return HttpResponseForbidden(_("Access denied."))

    from django.core.paginator import Paginator

    requests = _get_visible_requests(request.user)
    paginator = Paginator(requests, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "clients/erasure/erasure_history.html", {
        "erasure_requests": page_obj,
        "page_obj": page_obj,
        "nav_active": "admin",
    })


# --- PDF receipt ---

@login_required
@minimum_role("program_manager")
def erasure_receipt_pdf(request, pk):
    """Generate a one-time PDF receipt of the erasure request.

    Includes client PII — this is the document the privacy officer
    keeps outside the system before erasure proceeds. The system
    does NOT retain a copy.
    """
    er = get_object_or_404(ErasureRequest, pk=pk)

    # Scope access: only involved PMs, requester, or admins
    user_pm_ids = set(_get_user_pm_program_ids(request.user))
    is_involved = (
        request.user == er.requested_by
        or bool(set(er.programs_required) & user_pm_ids)
        or request.user.is_admin
    )
    if not is_involved:
        return HttpResponseForbidden(_("You do not have access to this receipt."))

    from apps.reports.pdf_utils import is_pdf_available, render_pdf

    if not is_pdf_available():
        messages.error(request, _("PDF generation is not available on this server."))
        return redirect("erasure_request_detail", pk=pk)

    # Only available while client data still exists
    if er.client_file is None:
        messages.error(request, _("%(term)s data no longer exists. Receipt cannot be generated.") % {"term": request.get_term("client")})
        return redirect("erasure_request_detail", pk=pk)

    client = er.client_file
    from apps.admin_settings.models import InstanceSetting
    org_name = InstanceSetting.get("organisation_name", "")

    context = {
        "er": er,
        "client": client,
        "org_name": org_name,
        "programs": er.data_summary.get("programs", er.data_summary.get("programmes", [])),
        "data_summary": er.data_summary,
        "approvals": er.approvals.select_related("approved_by"),
    }

    # Track first download
    if not er.receipt_downloaded_at:
        from django.utils import timezone as tz
        er.receipt_downloaded_at = tz.now()
        er.save(update_fields=["receipt_downloaded_at"])

    # Audit the download
    from .erasure import _log_audit
    _log_audit(
        user=request.user,
        action="export",
        resource_type="erasure_receipt_pdf",
        resource_id=er.pk,
        ip_address=_get_client_ip(request),
        metadata={
            "erasure_code": er.erasure_code,
            "client_pk": er.client_pk,
        },
    )

    filename = f"erasure-receipt-{er.erasure_code}.pdf"
    return render_pdf("clients/erasure/pdf_erasure_receipt.html", context, filename=filename)


# --- Email notifications ---

def _notify_pms_erasure_request(erasure_request, request):
    """Email all PMs in the client's programs about a new erasure request."""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.urls import reverse

    pm_users = (
        UserProgramRole.objects.filter(
            program_id__in=erasure_request.programs_required,
            role="program_manager",
            status="active",
        )
        .exclude(user=erasure_request.requested_by)
        .select_related("user")
    )
    emails = [upr.user.email for upr in pm_users if upr.user.email]
    if not emails:
        return True  # No one to notify — not a failure

    review_url = request.build_absolute_uri(
        reverse("erasure_request_detail", args=[erasure_request.pk])
    )
    context = {
        "erasure_request": erasure_request,
        "requester_name": erasure_request.requested_by_display,
        "erasure_code": erasure_request.erasure_code,
        "erasure_tier_display": erasure_request.get_erasure_tier_display(),
        "review_url": review_url,
    }

    term = request.get_term("client")
    subject = _("Action Required: %(term)s Erasure Request") % {"term": term}
    try:
        text_body = render_to_string("clients/email/erasure_request_alert.txt", context)
        html_body = render_to_string("clients/email/erasure_request_alert.html", context)
        send_mail(
            subject=subject, message=text_body, html_message=html_body,
            from_email=None, recipient_list=emails,
        )
        return True
    except TemplateDoesNotExist:
        logger.error(
            "Erasure email template not found for request %s — "
            "check templates/clients/email/ directory",
            erasure_request.pk, exc_info=True,
        )
        return False
    except SMTPException:
        logger.warning(
            "SMTP error sending erasure notification for request %s",
            erasure_request.pk, exc_info=True,
        )
        return False
    except Exception:
        logger.warning(
            "Unexpected error sending erasure notification for request %s",
            erasure_request.pk, exc_info=True,
        )
        return False


def _notify_erasure_completed(erasure_request, request):
    """Email all involved parties that erasure has been completed."""
    from django.core.mail import send_mail

    # Collect all involved users: requester + all approvers
    involved_users = set()
    if erasure_request.requested_by and erasure_request.requested_by.email:
        involved_users.add(erasure_request.requested_by.email)
    for approval in erasure_request.approvals.select_related("approved_by"):
        if approval.approved_by and approval.approved_by.email:
            involved_users.add(approval.approved_by.email)

    if not involved_users:
        return True  # No one to notify — not a failure

    code = erasure_request.erasure_code
    term = request.get_term("client")
    record_ref = erasure_request.client_record_id or _("%(term)s #%(pk)s") % {"term": term, "pk": erasure_request.client_pk}
    tier_label = erasure_request.get_erasure_tier_display()

    if erasure_request.erasure_tier == "full_erasure":
        subject = _("%(term)s Data Erased — %(code)s") % {"term": term, "code": code}
        action_desc = _("%(term)s data has been permanently erased.") % {"term": term}
    else:
        subject = _("%(term)s Data Anonymised — %(code)s") % {"term": term, "code": code}
        action_desc = _("%(term)s data has been anonymised.") % {"term": term}

    body = (
        action_desc
        + "\n\n"
        + _("Erasure code: %(code)s") % {"code": code}
        + "\n"
        + _("Erasure level: %(tier)s") % {"tier": tier_label}
        + "\n"
        + _("Reason: %(category)s — %(reason)s") % {
            "category": erasure_request.get_reason_category_display(),
            "reason": erasure_request.request_reason,
        }
        + "\n"
        + _("Requested by: %(name)s") % {"name": erasure_request.requested_by_display}
        + "\n"
        + _("All program manager approvals were received.")
        + "\n\n"
        + _("This action cannot be undone.")
    )

    try:
        send_mail(
            subject=subject, message=body,
            from_email=None, recipient_list=list(involved_users),
        )
        return True
    except SMTPException:
        logger.warning(
            "SMTP error sending erasure completion notification for request %s",
            erasure_request.pk, exc_info=True,
        )
        return False
    except Exception:
        logger.warning(
            "Unexpected error sending erasure completion notification for request %s",
            erasure_request.pk, exc_info=True,
        )
        return False


def _notify_requester_rejection(erasure_request, rejecting_user, review_notes):
    """Email the requester that their erasure request was rejected."""
    from django.core.mail import send_mail

    if not erasure_request.requested_by or not erasure_request.requested_by.email:
        return True  # No one to notify — not a failure

    code = erasure_request.erasure_code
    subject = _("Erasure Request Rejected — %(code)s") % {"code": code}
    body = (
        _("Your erasure request %(code)s has been rejected.") % {"code": code}
        + "\n\n"
        + _("Rejected by: %(name)s") % {"name": rejecting_user.get_display_name()}
        + "\n"
        + _("Reason: %(notes)s") % {"notes": review_notes}
        + "\n\n"
        + _("You may submit a new request if circumstances change.")
    )

    try:
        send_mail(
            subject=subject, message=body,
            from_email=None,
            recipient_list=[erasure_request.requested_by.email],
        )
        return True
    except SMTPException:
        logger.warning(
            "SMTP error sending rejection notification for %s",
            code, exc_info=True,
        )
        return False
    except Exception:
        logger.warning(
            "Unexpected error sending rejection notification for %s",
            code, exc_info=True,
        )
        return False
