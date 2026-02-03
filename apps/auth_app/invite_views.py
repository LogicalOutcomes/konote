"""Invite management views — create, list, and accept invites."""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.programs.models import UserProgramRole

from .admin_views import admin_required
from .forms import InviteAcceptForm, InviteCreateForm
from .models import Invite


@login_required
@admin_required
def invite_list(request):
    """Show all invites — pending and used."""
    invites = Invite.objects.select_related("created_by", "used_by").order_by("-created_at")
    return render(request, "auth_app/invite_list.html", {"invites": invites})


@login_required
@admin_required
def invite_create(request):
    """Create a new invite link."""
    if request.method == "POST":
        form = InviteCreateForm(request.POST)
        if form.is_valid():
            invite = Invite(
                role=form.cleaned_data["role"],
                created_by=request.user,
                expires_at=timezone.now() + timedelta(days=form.cleaned_data["expires_days"]),
            )
            invite.save()
            # Add program assignments (M2M requires save first)
            if form.cleaned_data["role"] != "admin":
                invite.programs.set(form.cleaned_data["programs"])
            invite_url = request.build_absolute_uri(f"/auth/join/{invite.code}/")
            messages.success(request, f"Invite created. Share this link: {invite_url}")
            return redirect("auth_app:invite_list")
    else:
        form = InviteCreateForm()
    return render(request, "auth_app/invite_form.html", {"form": form})


def invite_accept(request, code):
    """Public view — new user registers via invite link."""
    invite = get_object_or_404(Invite, code=code)

    if not invite.is_valid:
        if invite.is_used:
            error = "This invite has already been used."
        else:
            error = "This invite has expired. Please ask your administrator for a new one."
        return render(request, "auth_app/invite_expired.html", {"error": error})

    if request.method == "POST":
        form = InviteAcceptForm(request.POST)
        if form.is_valid():
            from .models import User

            # Create the user
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                display_name=form.cleaned_data["display_name"],
                is_admin=(invite.role == "admin"),
            )
            if form.cleaned_data.get("email"):
                user.email = form.cleaned_data["email"]
                user.save(update_fields=["_email_encrypted"])

            # Assign program roles (non-admin roles)
            if invite.role != "admin":
                for program in invite.programs.all():
                    UserProgramRole.objects.create(
                        user=user, program=program, role=invite.role,
                    )

            # Mark invite as used
            invite.used_by = user
            invite.used_at = timezone.now()
            invite.save()

            # Log the user in
            login(request, user)
            messages.success(request, f"Welcome, {user.display_name}! Your account has been created.")
            return redirect("/")
    else:
        form = InviteAcceptForm()

    return render(request, "auth_app/invite_accept.html", {
        "form": form,
        "invite": invite,
    })
