"""Staff-side views for the participant portal.

These views are used by staff (not participants) to manage portal content,
such as writing notes that appear in a participant's portal dashboard,
creating portal invites, and managing portal access.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.admin_settings.models import FeatureToggle
from apps.audit.models import AuditLog
from apps.auth_app.decorators import requires_permission
from apps.clients.models import ClientFile
from apps.auth_app.decorators import admin_required
from apps.portal.forms import ClientResourceForm, ProgramResourceForm, StaffPortalInviteForm, StaffPortalNoteForm
from apps.portal.models import (
    ClientResourceLink,
    CorrectionRequest,
    ParticipantUser,
    PortalInvite,
    PortalResourceLink,
    StaffAssistedLoginToken,
    StaffPortalNote,
)
from apps.programs.access import get_program_from_client as _get_program_from_client
from apps.programs.models import Program


def _portal_enabled_or_404():
    """Raise 404 if the participant_portal feature is disabled."""
    flags = FeatureToggle.get_all_flags()
    if not flags.get("participant_portal"):
        raise Http404


@login_required
@requires_permission("note.create", _get_program_from_client)
def create_staff_portal_note(request, client_id):
    """Create a note visible in the participant's portal."""
    client_file = get_object_or_404(ClientFile, pk=client_id)

    if request.method == "POST":
        form = StaffPortalNoteForm(request.POST)
        if form.is_valid():
            note = StaffPortalNote(
                client_file=client_file,
                from_user=request.user,
            )
            note.content = form.cleaned_data["content"]
            note.save()
            return redirect("clients:client_detail", client_id=client_id)
    else:
        form = StaffPortalNoteForm()

    recent_notes = StaffPortalNote.objects.filter(
        client_file=client_file, is_active=True,
    )[:10]

    return render(request, "portal/staff_create_note.html", {
        "form": form,
        "client_file": client_file,
        "recent_notes": recent_notes,
    })


@login_required
@requires_permission("note.create", _get_program_from_client)
def create_portal_invite(request, client_id):
    """Create a portal invite for a participant."""
    _portal_enabled_or_404()
    client_file = get_object_or_404(ClientFile, pk=client_id)

    # Check for pending invites
    pending = PortalInvite.objects.filter(
        client_file=client_file,
        status="pending",
        expires_at__gt=timezone.now(),
    ).first()

    if request.method == "POST":
        form = StaffPortalInviteForm(request.POST)
        if form.is_valid():
            invite = PortalInvite.objects.create(
                client_file=client_file,
                invited_by=request.user,
                verbal_code=form.cleaned_data.get("verbal_code") or "",
                expires_at=timezone.now() + timedelta(days=7),
            )

            # Build invite URL — use portal domain if configured
            invite_path = reverse("portal:accept_invite", args=[invite.token])
            portal_domain = getattr(settings, "PORTAL_DOMAIN", "")
            if portal_domain:
                scheme = "https" if request.is_secure() else "http"
                invite_url = f"{scheme}://{portal_domain}{invite_path}"
            else:
                invite_url = request.build_absolute_uri(invite_path)

            # Audit log — invite creation is an access-granting event
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.pk,
                user_display=request.user.display_name,
                action="create",
                resource_type="portal_invite",
                resource_id=invite.pk,
                metadata={
                    "client_file_id": client_file.pk,
                    "expires_at": invite.expires_at.isoformat(),
                    "has_verbal_code": bool(invite.verbal_code),
                },
            )

            return render(request, "portal/staff_invite_create.html", {
                "form": form,
                "client_file": client_file,
                "created_invite": invite,
                "invite_url": invite_url,
            })
    else:
        form = StaffPortalInviteForm()

    return render(request, "portal/staff_invite_create.html", {
        "form": form,
        "client_file": client_file,
        "existing_invite": pending,
    })


@login_required
@requires_permission("note.create", _get_program_from_client)
def portal_manage(request, client_id):
    """Manage portal access for a participant."""
    _portal_enabled_or_404()
    client_file = get_object_or_404(ClientFile, pk=client_id)

    portal_account = ParticipantUser.objects.filter(
        client_file=client_file,
    ).first()

    invites = PortalInvite.objects.filter(
        client_file=client_file,
    ).order_by("-created_at")[:10]

    pending_corrections = CorrectionRequest.objects.filter(
        client_file=client_file,
        status="pending",
    ).count()

    return render(request, "portal/staff_manage_portal.html", {
        "client_file": client_file,
        "portal_account": portal_account,
        "invites": invites,
        "pending_corrections": pending_corrections,
    })


@login_required
@requires_permission("note.create", _get_program_from_client)
def portal_revoke_access(request, client_id):
    """Revoke portal access for a participant (POST only)."""
    _portal_enabled_or_404()
    if request.method != "POST":
        raise Http404

    client_file = get_object_or_404(ClientFile, pk=client_id)
    account = ParticipantUser.objects.filter(
        client_file=client_file, is_active=True,
    ).first()

    if account:
        account.is_active = False
        account.save(update_fields=["is_active"])

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.pk,
            user_display=request.user.display_name,
            action="update",
            resource_type="portal_account",
            resource_id=account.pk,
            metadata={
                "client_file_id": client_file.pk,
                "operation": "revoke_access",
            },
        )

    return redirect("clients:portal_manage", client_id=client_id)


@login_required
@requires_permission("note.create", _get_program_from_client)
def generate_staff_login_token(request, client_id):
    """Generate a one-time staff-assisted login token (POST only)."""
    _portal_enabled_or_404()
    if request.method != "POST":
        raise Http404

    client_file = get_object_or_404(ClientFile, pk=client_id)
    account = ParticipantUser.objects.filter(
        client_file=client_file, is_active=True,
    ).first()

    if not account:
        raise Http404

    # Create token (15-minute expiry)
    token_obj = StaffAssistedLoginToken.objects.create(
        participant_user=account,
        created_by=request.user,
        expires_at=timezone.now() + timedelta(minutes=15),
    )

    # Build the URL
    login_path = reverse("portal:staff_assisted_login", args=[token_obj.token])
    portal_domain = getattr(settings, "PORTAL_DOMAIN", "")
    if portal_domain:
        scheme = "https" if request.is_secure() else "http"
        login_url = f"{scheme}://{portal_domain}{login_path}"
    else:
        login_url = request.build_absolute_uri(login_path)

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="create",
        resource_type="staff_assisted_login_token",
        resource_id=token_obj.pk,
        metadata={
            "client_file_id": client_file.pk,
            "participant_id": str(account.pk),
            "expires_at": token_obj.expires_at.isoformat(),
        },
    )

    return render(request, "portal/staff_manage_portal.html", {
        "client_file": client_file,
        "portal_account": account,
        "invites": PortalInvite.objects.filter(client_file=client_file).order_by("-created_at")[:10],
        "pending_corrections": CorrectionRequest.objects.filter(client_file=client_file, status="pending").count(),
        "staff_login_url": login_url,
        "staff_login_expires": token_obj.expires_at,
    })


@login_required
@requires_permission("note.create", _get_program_from_client)
def portal_reset_mfa(request, client_id):
    """Reset MFA for a participant's portal account (POST only)."""
    _portal_enabled_or_404()
    if request.method != "POST":
        raise Http404

    client_file = get_object_or_404(ClientFile, pk=client_id)
    account = ParticipantUser.objects.filter(
        client_file=client_file, is_active=True,
    ).first()

    if account:
        previous_method = account.mfa_method
        account.mfa_method = "none"
        account.totp_secret = ""
        account.save(update_fields=["mfa_method", "totp_secret"])

        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=request.user.pk,
            user_display=request.user.display_name,
            action="update",
            resource_type="portal_account",
            resource_id=account.pk,
            metadata={
                "client_file_id": client_file.pk,
                "operation": "reset_mfa",
                "previous_mfa_method": previous_method,
            },
        )

    return redirect("clients:portal_manage", client_id=client_id)


# ---------------------------------------------------------------------------
# Program resource links (admin-only, per-program)
# ---------------------------------------------------------------------------


@login_required
@admin_required
def program_resources_manage(request, program_id):
    """List and add resource links for a program."""
    _portal_enabled_or_404()
    program = get_object_or_404(Program, pk=program_id)

    if request.method == "POST":
        form = ProgramResourceForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.program = program
            resource.created_by = request.user
            resource.save()
            return redirect("programs:program_resources", program_id=program.pk)
    else:
        form = ProgramResourceForm()

    resources = PortalResourceLink.objects.filter(
        program=program, is_active=True,
    ).order_by("display_order", "title")

    return render(request, "portal/staff_program_resources.html", {
        "form": form,
        "program": program,
        "resources": resources,
    })


@login_required
@admin_required
def program_resource_edit(request, program_id, resource_id):
    """Edit a program resource link."""
    _portal_enabled_or_404()
    program = get_object_or_404(Program, pk=program_id)
    resource = get_object_or_404(
        PortalResourceLink, pk=resource_id, program=program, is_active=True,
    )

    if request.method == "POST":
        form = ProgramResourceForm(request.POST, instance=resource)
        if form.is_valid():
            form.save()
            return redirect("programs:program_resources", program_id=program.pk)
    else:
        form = ProgramResourceForm(instance=resource)

    return render(request, "portal/staff_program_resource_edit.html", {
        "form": form,
        "program": program,
        "resource": resource,
    })


@login_required
@admin_required
def program_resource_deactivate(request, program_id, resource_id):
    """Soft-delete a program resource link (POST only)."""
    _portal_enabled_or_404()
    if request.method != "POST":
        raise Http404

    program = get_object_or_404(Program, pk=program_id)
    resource = get_object_or_404(
        PortalResourceLink, pk=resource_id, program=program, is_active=True,
    )
    resource.is_active = False
    resource.save(update_fields=["is_active", "updated_at"])

    return redirect("programs:program_resources", program_id=program.pk)


# ---------------------------------------------------------------------------
# Client resource links (staff, per-client)
# ---------------------------------------------------------------------------


@login_required
@requires_permission("note.create", _get_program_from_client)
def client_resources_manage(request, client_id):
    """List and add resource links for a specific participant."""
    _portal_enabled_or_404()
    client_file = get_object_or_404(ClientFile, pk=client_id)

    if request.method == "POST":
        form = ClientResourceForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.client_file = client_file
            resource.created_by = request.user
            resource.save()
            return redirect("clients:client_resources", client_id=client_file.pk)
    else:
        form = ClientResourceForm()

    resources = ClientResourceLink.objects.filter(
        client_file=client_file, is_active=True,
    ).order_by("-created_at")

    return render(request, "portal/staff_client_resources.html", {
        "form": form,
        "client_file": client_file,
        "resources": resources,
    })


@login_required
@requires_permission("note.create", _get_program_from_client)
def client_resource_deactivate(request, client_id, resource_id):
    """Soft-delete a client resource link (POST only)."""
    _portal_enabled_or_404()
    if request.method != "POST":
        raise Http404

    client_file = get_object_or_404(ClientFile, pk=client_id)
    resource = get_object_or_404(
        ClientResourceLink, pk=resource_id, client_file=client_file, is_active=True,
    )
    resource.is_active = False
    resource.save(update_fields=["is_active"])

    return redirect("clients:client_resources", client_id=client_file.pk)
