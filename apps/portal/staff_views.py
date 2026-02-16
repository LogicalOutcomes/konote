"""Staff-side views for the participant portal.

These views are used by staff (not participants) to manage portal content,
such as writing notes that appear in a participant's portal dashboard,
creating portal invites, and managing portal access.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.decorators import requires_permission
from apps.clients.models import ClientFile
from apps.portal.forms import StaffPortalInviteForm, StaffPortalNoteForm
from apps.portal.models import (
    CorrectionRequest,
    ParticipantUser,
    PortalInvite,
    StaffPortalNote,
)
from apps.programs.access import get_program_from_client as _get_program_from_client


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
            return render(request, "portal/staff_invite_create.html", {
                "form": form,
                "client_file": client_file,
                "invite": invite,
                "created": True,
            })
    else:
        form = StaffPortalInviteForm()

    return render(request, "portal/staff_invite_create.html", {
        "form": form,
        "client_file": client_file,
        "pending_invite": pending,
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

    return redirect("clients:portal_manage", client_id=client_id)


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
        account.mfa_method = "none"
        account.totp_secret = ""
        account.save(update_fields=["mfa_method", "totp_secret"])

    return redirect("clients:portal_manage", client_id=client_id)
