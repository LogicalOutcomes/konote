"""Staff-side views for the participant portal.

These views are used by staff (not participants) to manage portal content,
such as writing notes that appear in a participant's portal dashboard.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import minimum_role
from apps.clients.models import ClientFile
from apps.portal.forms import StaffPortalNoteForm
from apps.portal.models import StaffPortalNote


@login_required
@minimum_role("worker")
def create_staff_portal_note(request, client_id):
    """Create a note visible in the participant's portal.

    Restricted to workers and above — writing a portal note is a
    clinical interaction that should only be done by someone
    working directly with the participant.
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
