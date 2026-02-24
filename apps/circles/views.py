"""Circle views: list, create, detail, edit, archive, membership management."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.decorators import requires_permission_global
from apps.clients.models import ClientFile
from apps.clients.views import get_client_queryset
from apps.programs.access import get_user_program_ids

from .forms import CircleForm, CircleMembershipForm
from .helpers import get_accessible_notes_for_circle, get_visible_circles
from .models import Circle, CircleMembership


# ---------------------------------------------------------------------------
# Feature toggle decorator
# ---------------------------------------------------------------------------

def requires_feature(feature_key):
    """Decorator: return 404 if the feature toggle is off."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            flags = FeatureToggle.get_all_flags()
            if not flags.get(feature_key, False):
                raise Http404
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_accessible_clients_for_search(user):
    """Return list of (pk, display_name) for participant search.

    Excludes clients blocked via ClientAccessBlock (DV safety).
    """
    from apps.clients.models import ClientAccessBlock, ClientProgramEnrolment

    qs = get_client_queryset(user).filter(status="active")
    program_ids = get_user_program_ids(user)
    enrolled_ids = set(
        ClientProgramEnrolment.objects.filter(
            program_id__in=program_ids, status="enrolled"
        ).values_list("client_file_id", flat=True)
    )
    # DV safety: exclude blocked clients
    blocked_ids = set(
        ClientAccessBlock.objects.filter(user=user, is_active=True)
        .values_list("client_file_id", flat=True)
    )
    enrolled_ids -= blocked_ids

    results = []
    for client in qs.filter(pk__in=enrolled_ids):
        name = f"{client.display_name} {client.last_name}".strip()
        results.append((client.pk, name or f"#{client.pk}"))
    results.sort(key=lambda x: x[1].lower())
    return results


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@login_required
@requires_feature("circles")
@requires_permission_global("circle.view")
def circle_list(request):
    """List visible circles with member count and search."""
    circles_qs = get_visible_circles(request.user)
    circles_qs = circles_qs.prefetch_related("memberships__client_file")

    # Build display data (decrypt names in Python)
    search = request.GET.get("q", "").strip().lower()
    circle_data = []
    for circle in circles_qs:
        active_members = [
            m for m in circle.memberships.all() if m.status == "active"
        ]
        name = circle.name or ""
        primary = next((m for m in active_members if m.is_primary_contact), None)

        if search and search not in name.lower():
            continue

        circle_data.append({
            "circle": circle,
            "name": name,
            "member_count": len(active_members),
            "primary_contact": primary.display_name if primary else "",
        })

    circle_data.sort(key=lambda x: x["name"].lower())

    return render(request, "circles/circle_list.html", {
        "circles": circle_data,
        "search_query": request.GET.get("q", ""),
        "nav_active": "circles",
    })


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@login_required
@requires_feature("circles")
@requires_permission_global("circle.create")
def circle_create(request):
    """Create a new circle."""
    if request.method == "POST":
        form = CircleForm(request.POST)
        if form.is_valid():
            circle = Circle(is_demo=request.user.is_demo)
            circle.name = form.cleaned_data["name"]
            circle.status = form.cleaned_data["status"]
            circle.created_by = request.user
            circle.save()
            messages.success(request, _("Circle created."))
            return redirect("circles:circle_detail", circle_id=circle.pk)
    else:
        form = CircleForm()

    return render(request, "circles/circle_form.html", {
        "form": form,
        "is_edit": False,
        "nav_active": "circles",
    })


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@login_required
@requires_feature("circles")
@requires_permission_global("circle.view")
def circle_detail(request, circle_id):
    """Show circle with members and tagged notes timeline."""
    visible_circles = get_visible_circles(request.user)
    circle = get_object_or_404(visible_circles, pk=circle_id)

    active_members = CircleMembership.objects.filter(
        circle=circle, status="active"
    ).select_related("client_file").order_by("-is_primary_contact", "created_at")

    accessible_notes, total_note_count = get_accessible_notes_for_circle(
        circle, request.user
    )
    hidden_note_count = total_note_count - len(accessible_notes)

    return render(request, "circles/circle_detail.html", {
        "circle": circle,
        "members": active_members,
        "notes": accessible_notes,
        "total_note_count": total_note_count,
        "hidden_note_count": hidden_note_count,
        "nav_active": "circles",
    })


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

@login_required
@requires_feature("circles")
@requires_permission_global("circle.edit")
def circle_edit(request, circle_id):
    """Edit circle name and status."""
    visible_circles = get_visible_circles(request.user)
    circle = get_object_or_404(visible_circles, pk=circle_id)

    if request.method == "POST":
        form = CircleForm(request.POST)
        if form.is_valid():
            circle.name = form.cleaned_data["name"]
            circle.status = form.cleaned_data["status"]
            circle.save()
            messages.success(request, _("Circle updated."))
            return redirect("circles:circle_detail", circle_id=circle.pk)
    else:
        form = CircleForm(initial={
            "name": circle.name,
            "status": circle.status,
        })

    return render(request, "circles/circle_form.html", {
        "form": form,
        "circle": circle,
        "is_edit": True,
        "nav_active": "circles",
    })


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

@login_required
@requires_feature("circles")
@requires_permission_global("circle.edit")
def circle_archive(request, circle_id):
    """Archive a circle (POST only)."""
    if request.method != "POST":
        return redirect("circles:circle_detail", circle_id=circle_id)

    visible_circles = get_visible_circles(request.user)
    circle = get_object_or_404(visible_circles, pk=circle_id)
    circle.status = "archived"
    circle.save()
    messages.success(request, _("Circle archived."))
    return redirect("circles:circle_list")


# ---------------------------------------------------------------------------
# Membership: add
# ---------------------------------------------------------------------------

@login_required
@requires_feature("circles")
@requires_permission_global("circle.edit")
def membership_add(request, circle_id):
    """Add a member (participant or non-participant) to a circle."""
    visible_circles = get_visible_circles(request.user)
    circle = get_object_or_404(visible_circles, pk=circle_id)

    if request.method == "POST":
        form = CircleMembershipForm(request.POST)
        if form.is_valid():
            client_file_id = form.cleaned_data.get("client_file")
            member_name = form.cleaned_data.get("member_name", "").strip()

            membership = CircleMembership(
                circle=circle,
                relationship_label=form.cleaned_data.get("relationship_label", ""),
                is_primary_contact=form.cleaned_data.get("is_primary_contact", False),
            )

            if client_file_id:
                # Validate user has access to this client (DV safety + program scope)
                accessible_pks = set(pk for pk, _ in _get_accessible_clients_for_search(request.user))
                if client_file_id not in accessible_pks:
                    messages.error(request, _("You do not have access to this participant."))
                    return redirect("circles:circle_detail", circle_id=circle.pk)
                client = get_object_or_404(ClientFile, pk=client_file_id)
                # Check duplicate
                if CircleMembership.objects.filter(
                    circle=circle, client_file=client, status="active"
                ).exists():
                    messages.warning(request, _("This participant is already in this circle."))
                    return redirect("circles:circle_detail", circle_id=circle.pk)
                membership.client_file = client
            else:
                membership.member_name = member_name

            membership.save()
            messages.success(request, _("Member added."))
            return redirect("circles:circle_detail", circle_id=circle.pk)
    else:
        form = CircleMembershipForm()

    # Accessible participants for the search dropdown
    client_choices = _get_accessible_clients_for_search(request.user)

    return render(request, "circles/membership_add.html", {
        "form": form,
        "circle": circle,
        "client_choices": client_choices,
        "nav_active": "circles",
    })


# ---------------------------------------------------------------------------
# Membership: remove
# ---------------------------------------------------------------------------

@login_required
@requires_feature("circles")
@requires_permission_global("circle.edit")
def membership_remove(request, circle_id, membership_id):
    """Remove a member from a circle (POST only — sets status to inactive)."""
    if request.method != "POST":
        return redirect("circles:circle_detail", circle_id=circle_id)

    visible_circles = get_visible_circles(request.user)
    circle = get_object_or_404(visible_circles, pk=circle_id)
    membership = get_object_or_404(
        CircleMembership, pk=membership_id, circle=circle
    )
    membership.status = "inactive"
    membership.save()
    messages.success(request, _("Member removed."))
    return redirect("circles:circle_detail", circle_id=circle.pk)
