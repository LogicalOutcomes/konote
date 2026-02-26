"""Admin views for managing registration links and submissions.

Admins: full access to all registration links and submissions.
PMs with registration.manage: PROGRAM: manage links/submissions for their own programs.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.auth_app.decorators import requires_permission
from apps.clients.models import ClientFile, CustomFieldDefinition
from apps.clients.views import get_client_queryset
from apps.programs.models import UserProgramRole

from .forms import RegistrationLinkForm
from .models import RegistrationLink, RegistrationSubmission
from .utils import approve_submission, find_duplicate_clients, merge_with_existing


def _get_pm_program_ids(user):
    """Return set of program IDs where the user is an active PM."""
    return set(
        UserProgramRole.objects.filter(
            user=user, role="program_manager", status="active",
        ).values_list("program_id", flat=True)
    )


def _can_manage_link(user, link):
    """Check if the user can manage a registration link."""
    if user.is_admin:
        return True
    return link.program_id in _get_pm_program_ids(user)


def _get_embed_code(request, link, height=600):
    """Generate iframe embed code for a registration link."""
    embed_url = request.build_absolute_uri(f"/register/{link.slug}/?embed=1")
    embed_code = f'''<!-- {link.title} Registration Form -->
<iframe
    src="{embed_url}"
    width="100%"
    height="{height}"
    frameborder="0"
    title="{link.title}"
    allow="forms"
    style="border: none; max-width: 100%;">
</iframe>'''
    return embed_code


# --- Registration Link Management ---

@login_required
@requires_permission("registration.manage", allow_admin=True)
def link_list(request):
    """List registration links visible to the user."""
    if request.user.is_admin:
        links = RegistrationLink.objects.select_related("program", "created_by").all()
    else:
        pm_program_ids = _get_pm_program_ids(request.user)
        links = RegistrationLink.objects.select_related("program", "created_by").filter(
            program_id__in=pm_program_ids,
        )

    for link in links:
        link.submission_count = link.submissions.count()
        link.pending_count = link.submissions.filter(status="pending").count()

    return render(request, "registration/admin/link_list.html", {
        "links": links,
        "nav_active": "admin",
    })


@login_required
@requires_permission("registration.manage", allow_admin=True)
def link_create(request):
    """Create a new registration link."""
    if request.method == "POST":
        form = RegistrationLinkForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            link = form.save(commit=False)
            link.created_by = request.user
            link.save()
            form.save_m2m()
            messages.success(request, _("Registration link '%(title)s' created.") % {"title": link.title})
            return redirect("registration:registration_link_list")
    else:
        form = RegistrationLinkForm(requesting_user=request.user)

    return render(request, "registration/admin/link_form.html", {
        "form": form,
        "editing": False,
        "nav_active": "admin",
    })


@login_required
@requires_permission("registration.manage", allow_admin=True)
def link_edit(request, pk):
    """Edit an existing registration link."""
    link = get_object_or_404(RegistrationLink, pk=pk)

    if not _can_manage_link(request.user, link):
        return HttpResponseForbidden(_("Access denied. You can only manage registration links in your programs."))

    if request.method == "POST":
        form = RegistrationLinkForm(request.POST, instance=link, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Registration link '%(title)s' updated.") % {"title": link.title})
            return redirect("registration:registration_link_list")
    else:
        form = RegistrationLinkForm(instance=link, requesting_user=request.user)

    return render(request, "registration/admin/link_form.html", {
        "form": form,
        "link": link,
        "editing": True,
        "nav_active": "admin",
    })


@login_required
@requires_permission("registration.manage", allow_admin=True)
def link_embed(request, pk):
    """Display embed code for a registration link."""
    link = get_object_or_404(RegistrationLink, pk=pk)

    if not _can_manage_link(request.user, link):
        return HttpResponseForbidden(_("Access denied."))

    embed_code = _get_embed_code(request, link)
    direct_url = request.build_absolute_uri(f"/register/{link.slug}/")
    embed_url = request.build_absolute_uri(f"/register/{link.slug}/?embed=1")

    return render(request, "registration/admin/link_embed.html", {
        "link": link,
        "embed_code": embed_code,
        "direct_url": direct_url,
        "embed_url": embed_url,
        "nav_active": "admin",
    })


@login_required
@requires_permission("registration.manage", allow_admin=True)
def link_delete(request, pk):
    """Delete a registration link."""
    link = get_object_or_404(RegistrationLink, pk=pk)

    if not _can_manage_link(request.user, link):
        return HttpResponseForbidden(_("Access denied."))

    if request.method == "POST":
        title = link.title
        link.delete()
        messages.success(request, _("Registration link '%(title)s' deleted.") % {"title": title})
        return redirect("registration:registration_link_list")

    return render(request, "registration/admin/link_confirm_delete.html", {
        "link": link,
        "nav_active": "admin",
    })


# --- Submission Management ---

@login_required
@requires_permission("registration.manage", allow_admin=True)
def submission_list(request):
    """List registration submissions with filtering."""
    status_filter = request.GET.get("status", "")

    submissions = RegistrationSubmission.objects.select_related(
        "registration_link",
        "registration_link__program",
        "reviewed_by",
        "client_file",
    )

    # PMs only see submissions for their programs
    if not request.user.is_admin:
        pm_program_ids = _get_pm_program_ids(request.user)
        submissions = submissions.filter(
            registration_link__program_id__in=pm_program_ids,
        )

    if status_filter:
        submissions = submissions.filter(status=status_filter)

    # Check for potential duplicates
    for sub in submissions:
        sub.is_duplicate = _check_duplicate(sub)

    # Count by status (scoped to same visibility)
    base_qs = RegistrationSubmission.objects.all()
    if not request.user.is_admin:
        base_qs = base_qs.filter(registration_link__program_id__in=pm_program_ids)

    status_counts = {
        "all": base_qs.count(),
        "pending": base_qs.filter(status="pending").count(),
        "approved": base_qs.filter(status="approved").count(),
        "rejected": base_qs.filter(status="rejected").count(),
        "waitlist": base_qs.filter(status="waitlist").count(),
    }

    return render(request, "registration/admin/submission_list.html", {
        "submissions": submissions,
        "status_filter": status_filter,
        "status_counts": status_counts,
        "nav_active": "admin",
    })


@login_required
@requires_permission("registration.manage", allow_admin=True)
def submission_detail(request, pk):
    """View details of a registration submission."""
    submission = get_object_or_404(
        RegistrationSubmission.objects.select_related(
            "registration_link",
            "registration_link__program",
            "reviewed_by",
            "client_file",
        ),
        pk=pk,
    )

    if not request.user.is_admin:
        pm_program_ids = _get_pm_program_ids(request.user)
        if submission.registration_link.program_id not in pm_program_ids:
            return HttpResponseForbidden(_("Access denied."))

    duplicate_matches = []
    if submission.status == "pending":
        duplicate_matches = find_duplicate_clients(submission)

    custom_fields = []
    for field_id, value in submission.field_values.items():
        try:
            field_def = CustomFieldDefinition.objects.get(pk=field_id)
            custom_fields.append({"name": field_def.name, "value": value})
        except CustomFieldDefinition.DoesNotExist:
            custom_fields.append({"name": f"Field {field_id}", "value": value})

    return render(request, "registration/admin/submission_detail.html", {
        "submission": submission,
        "duplicate_matches": duplicate_matches,
        "custom_fields": custom_fields,
        "nav_active": "admin",
    })


@login_required
@requires_permission("registration.manage", allow_admin=True)
def submission_approve(request, pk):
    """Approve a registration submission and create client record."""
    submission = get_object_or_404(RegistrationSubmission, pk=pk)

    if not request.user.is_admin:
        pm_program_ids = _get_pm_program_ids(request.user)
        if submission.registration_link.program_id not in pm_program_ids:
            return HttpResponseForbidden(_("Access denied."))

    if request.method == "POST":
        if submission.status not in ("pending", "waitlist"):
            messages.error(request, _("This submission has already been reviewed."))
            return redirect("registration:submission_detail", pk=pk)

        client = approve_submission(submission, reviewed_by=request.user)
        messages.success(
            request,
            _("Approved! Participant record created for %(first)s %(last)s.") % {
                "first": client.first_name,
                "last": client.last_name,
            },
        )
        return redirect("registration:submission_list")

    return redirect("registration:submission_detail", pk=pk)


@login_required
@requires_permission("registration.manage", allow_admin=True)
def submission_reject(request, pk):
    """Reject a registration submission."""
    submission = get_object_or_404(RegistrationSubmission, pk=pk)

    if not request.user.is_admin:
        pm_program_ids = _get_pm_program_ids(request.user)
        if submission.registration_link.program_id not in pm_program_ids:
            return HttpResponseForbidden(_("Access denied."))

    if request.method == "POST":
        if submission.status not in ("pending", "waitlist"):
            messages.error(request, _("This submission has already been reviewed."))
            return redirect("registration:submission_detail", pk=pk)

        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, _("A rejection reason is required."))
            return redirect("registration:submission_detail", pk=pk)

        submission.status = "rejected"
        submission.review_notes = reason
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save()

        messages.success(request, _("Submission rejected."))
        return redirect("registration:submission_list")

    return redirect("registration:submission_detail", pk=pk)


@login_required
@requires_permission("registration.manage", allow_admin=True)
def submission_waitlist(request, pk):
    """Move a submission to waitlist."""
    submission = get_object_or_404(RegistrationSubmission, pk=pk)

    if not request.user.is_admin:
        pm_program_ids = _get_pm_program_ids(request.user)
        if submission.registration_link.program_id not in pm_program_ids:
            return HttpResponseForbidden(_("Access denied."))

    if request.method == "POST":
        if submission.status not in ("pending", "waitlist"):
            messages.error(request, _("This submission cannot be waitlisted."))
            return redirect("registration:submission_detail", pk=pk)

        submission.status = "waitlist"
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save()

        messages.success(request, _("Submission moved to waitlist."))
        return redirect("registration:submission_list")

    return redirect("registration:submission_detail", pk=pk)


@login_required
@requires_permission("registration.manage", allow_admin=True)
def submission_merge(request, pk):
    """Merge a submission with an existing client instead of creating a new one."""
    submission = get_object_or_404(RegistrationSubmission, pk=pk)

    if not request.user.is_admin:
        pm_program_ids = _get_pm_program_ids(request.user)
        if submission.registration_link.program_id not in pm_program_ids:
            return HttpResponseForbidden(_("Access denied."))

    if request.method == "POST":
        if submission.status != "pending":
            messages.error(request, _("This submission has already been reviewed."))
            return redirect("registration:submission_detail", pk=pk)

        client_id = request.POST.get("client_id")
        if not client_id:
            messages.error(request, _("No participant selected for merge."))
            return redirect("registration:submission_detail", pk=pk)

        try:
            existing_client = get_client_queryset(request.user).get(pk=client_id)
        except ClientFile.DoesNotExist:
            messages.error(request, _("Selected participant not found."))
            return redirect("registration:submission_detail", pk=pk)

        client = merge_with_existing(submission, existing_client, request.user)
        messages.success(
            request,
            _("Merged with existing participant %(first)s %(last)s.") % {
                "first": client.first_name,
                "last": client.last_name,
            },
        )
        return redirect("registration:submission_list")

    return redirect("registration:submission_detail", pk=pk)


# --- Helper Functions ---

def _check_duplicate(submission):
    """Check if a submission might be a duplicate (by email hash)."""
    if not submission.email_hash:
        return False
    return RegistrationSubmission.objects.filter(
        email_hash=submission.email_hash,
        status="approved",
    ).exclude(pk=submission.pk).exists()


def _find_duplicate_client(submission):
    """Find an existing client that matches this submission."""
    if not submission.email_hash:
        return None
    duplicate_submission = RegistrationSubmission.objects.filter(
        email_hash=submission.email_hash,
        status="approved",
        client_file__isnull=False,
    ).exclude(pk=submission.pk).first()
    if duplicate_submission:
        return duplicate_submission.client_file
    return None
