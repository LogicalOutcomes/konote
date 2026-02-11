"""Staff-side views for the participant portal.

These views are used by staff (not participants) to manage portal content,
such as writing notes that appear in a participant's portal dashboard.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.constants import ROLE_RANK
from apps.auth_app.decorators import requires_permission
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.portal.forms import StaffPortalNoteForm
from apps.portal.models import StaffPortalNote


def _get_program_from_client(request, client_id, **kwargs):
    """Find the shared program where user has the highest role for a client."""
    from apps.programs.models import UserProgramRole, Program
    client = get_object_or_404(ClientFile, pk=client_id)
    user_roles = UserProgramRole.objects.filter(
        user=request.user, status="active"
    ).values_list("program_id", "role")
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled"
        ).values_list("program_id", flat=True)
    )
    best_program_id = None
    best_rank = -1
    for program_id, role in user_roles:
        if program_id in client_program_ids:
            rank = ROLE_RANK.get(role, 0)
            if rank > best_rank:
                best_rank = rank
                best_program_id = program_id
    if best_program_id is None:
        raise ValueError(f"User has no shared program with client {client_id}")
    return Program.objects.get(pk=best_program_id)


@login_required
@requires_permission("note.create", _get_program_from_client)
def create_staff_portal_note(request, client_id):
    """Create a note visible in the participant's portal.

    Restricted to staff — writing a portal note is a clinical
    interaction that should only be done by someone working
    directly with the participant.
    """
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
            return redirect("client_detail", pk=client_id)
    else:
        form = StaffPortalNoteForm()

    # Recent notes for this client
    recent_notes = StaffPortalNote.objects.filter(
        client_file=client_file, is_active=True,
    )[:10]

    return render(request, "portal/staff_create_note.html", {
        "form": form,
        "client_file": client_file,
        "recent_notes": recent_notes,
    })
