"""Views for communication logging — quick-log buttons and full log form."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from apps.clients.models import ClientFile
from apps.programs.access import get_author_program, get_client_or_403, get_program_from_client

from apps.auth_app.decorators import requires_permission

from .forms import CommunicationLogForm, QuickLogForm
from .models import Communication


# ---------------------------------------------------------------------------
# Helper for @requires_permission decorator
# ---------------------------------------------------------------------------

_get_program_from_client = get_program_from_client


# ---------------------------------------------------------------------------
# Quick-log — the 2-click workflow
# ---------------------------------------------------------------------------

@login_required
@requires_permission("communication.log", _get_program_from_client)
def quick_log(request, client_id):
    """HTMX endpoint for quick-action buttons — log a call/text/email in under 10 seconds.

    POST creates the record and returns the updated quick-log buttons partial.
    GET with ?channel=xxx returns the mini form for that channel.
    """
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this client."))

    channel = request.GET.get("channel") or request.POST.get("channel", "")

    # Cancel button or no channel specified — return the buttons view
    if request.method == "GET" and not channel:
        recent = (
            Communication.objects.filter(client_file=client)
            .order_by("-created_at")[:5]
        )
        return render(request, "communications/_quick_log_buttons.html", {
            "client": client,
            "recent_communications": recent,
        })

    if request.method == "POST":
        form = QuickLogForm(request.POST)
        if form.is_valid():
            from apps.communications.services import log_communication

            log_communication(
                client_file=client,
                direction=form.cleaned_data["direction"],
                channel=form.cleaned_data["channel"],
                logged_by=request.user,
                content=form.cleaned_data.get("notes", ""),
                author_program=get_author_program(request.user, client),
            )
            messages.success(request, _("Communication logged."))

            # Return updated buttons (HTMX swaps the whole container)
            recent = (
                Communication.objects.filter(client_file=client)
                .order_by("-created_at")[:5]
            )
            return render(request, "communications/_quick_log_buttons.html", {
                "client": client,
                "recent_communications": recent,
            })
    else:
        form = QuickLogForm(initial={"channel": channel, "direction": "outbound"})

    return render(request, "communications/_quick_log_form.html", {
        "form": form,
        "client": client,
        "channel": channel,
    })


# ---------------------------------------------------------------------------
# Full communication log form
# ---------------------------------------------------------------------------

@login_required
@requires_permission("communication.log", _get_program_from_client)
def communication_log(request, client_id):
    """Full form for detailed communication logging — all fields available."""
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden(_("You do not have access to this client."))

    if request.method == "POST":
        form = CommunicationLogForm(request.POST)
        if form.is_valid():
            from apps.communications.services import log_communication

            log_communication(
                client_file=client,
                direction=form.cleaned_data["direction"],
                channel=form.cleaned_data["channel"],
                logged_by=request.user,
                content=form.cleaned_data.get("content", ""),
                subject=form.cleaned_data.get("subject", ""),
                author_program=get_author_program(request.user, client),
            )
            messages.success(request, _("Communication logged."))
            return redirect("events:event_list", client_id=client.pk)
    else:
        form = CommunicationLogForm()

    return render(request, "communications/communication_log_form.html", {
        "form": form,
        "client": client,
    })
