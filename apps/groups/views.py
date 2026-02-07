"""Group views: list, detail, session logging, membership, milestones, outcomes, reports."""
import csv
import io
from collections import OrderedDict
from datetime import date as dt_date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.reports.csv_utils import sanitise_csv_row, sanitise_filename

from django.urls import reverse

from apps.auth_app.decorators import minimum_role
from apps.clients.models import ClientFile
from apps.clients.views import _get_user_program_ids, get_client_queryset
from apps.programs.models import UserProgramRole

from .forms import (
    GroupForm,
    HighlightForm,
    ProjectMilestoneForm,
    ProjectOutcomeForm,
    SessionLogForm,
)
from .models import (
    Group,
    GroupMembership,
    GroupSession,
    GroupSessionAttendance,
    GroupSessionHighlight,
    ProjectMilestone,
    ProjectOutcome,
)


def _get_user_role_for_group(request, group):
    """Return the display name of the user's role in the group's program.

    Uses request-level caching so repeated calls in the same request
    don't issue extra DB queries.
    """
    if not group.program_id:
        return None
    if not hasattr(request, "_user_role_cache"):
        roles = UserProgramRole.objects.filter(
            user=request.user, status="active",
        ).only("program_id", "role")
        request._user_role_cache = {r.program_id: r for r in roles}
    role_obj = request._user_role_cache.get(group.program_id)
    return role_obj.get_role_display() if role_obj else None


# ---------------------------------------------------------------------------
# 1. Group list
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def group_list(request):
    """List active groups the user has program access to."""
    user_program_ids = _get_user_program_ids(request.user)
    groups = Group.objects.filter(
        status="active",
        program_id__in=user_program_ids,
        program__service_model__in=["group", "both"],
    ).select_related("program")
    return render(request, "groups/group_list.html", {
        "groups": groups,
        "active_groups": groups,
    })


# ---------------------------------------------------------------------------
# 2. Group detail
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def group_detail(request, group_id):
    """Detail view: roster, recent sessions, and project extras."""
    group = get_object_or_404(Group, pk=group_id)

    # Block access if user has no role in the group's program
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))

    # Active members
    memberships = GroupMembership.objects.filter(
        group=group, status="active",
    ).select_related("client_file")

    # Recent 10 sessions with present/total counts for session cards
    sessions = (
        GroupSession.objects.filter(group=group)
        .annotate(
            total_count=Count("attendance_records"),
            present_count=Count(
                "attendance_records",
                filter=models.Q(attendance_records__present=True),
            ),
        )
        .order_by("-session_date")[:10]
    )

    context = {
        "group": group,
        "memberships": memberships,
        "sessions": sessions,
        "breadcrumbs": [
            {"url": reverse("groups:group_list"), "label": _("Groups")},
            {"url": "", "label": group.name},
        ],
        "user_role_for_program": _get_user_role_for_group(request, group),
    }

    # Project-type extras: milestones and outcomes
    if group.group_type == "project":
        context["milestones"] = ProjectMilestone.objects.filter(group=group)
        context["outcomes"] = ProjectOutcome.objects.filter(group=group)

    return render(request, "groups/group_detail.html", context)


# ---------------------------------------------------------------------------
# 3. Group create
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def group_create(request):
    """Create a new group."""
    user_program_ids = _get_user_program_ids(request.user)
    if request.method == "POST":
        form = GroupForm(request.POST, user_program_ids=user_program_ids)
        if form.is_valid():
            group = form.save()
            messages.success(request, _("Group created."))
            return redirect("groups:group_detail", group_id=group.pk)
    else:
        form = GroupForm(user_program_ids=user_program_ids)
    return render(request, "groups/group_form.html", {
        "form": form,
        "editing": False,
    })


# ---------------------------------------------------------------------------
# 4. Group edit
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def group_edit(request, group_id):
    """Edit an existing group."""
    group = get_object_or_404(Group, pk=group_id)
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))
    if request.method == "POST":
        form = GroupForm(request.POST, instance=group, user_program_ids=user_program_ids)
        if form.is_valid():
            form.save()
            messages.success(request, _("Group updated."))
            return redirect("groups:group_detail", group_id=group.pk)
    else:
        form = GroupForm(instance=group, user_program_ids=user_program_ids)
    return render(request, "groups/group_form.html", {
        "form": form,
        "editing": True,
        "group": group,
    })


# ---------------------------------------------------------------------------
# 5. Session log -- THE CRITICAL 60-SECOND WORKFLOW
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def session_log(request, group_id):
    """Log a group session with attendance and optional highlights.

    All active members are pre-checked (Rec #9) -- the facilitator unchecks
    anyone who was absent rather than checking everyone present.
    """
    group = get_object_or_404(Group, pk=group_id)
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))
    members = GroupMembership.objects.filter(
        group=group, status="active",
    ).select_related("client_file")

    if request.method == "POST":
        form = SessionLogForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # 1. Create the session
                session = GroupSession(
                    group=group,
                    session_date=form.cleaned_data["session_date"],
                    facilitator=request.user,
                    group_vibe=form.cleaned_data["group_vibe"],
                )
                session.notes = form.cleaned_data["notes"]
                session.save()

                # 2. Record attendance for each member
                for member in members:
                    present = request.POST.get(f"present_{member.pk}") == "on"
                    GroupSessionAttendance.objects.create(
                        group_session=session,
                        membership=member,
                        present=present,
                    )

                # 3. Save any non-empty highlights
                for member in members:
                    highlight_notes = request.POST.get(
                        f"highlight_{member.pk}", "",
                    ).strip()
                    if highlight_notes:
                        highlight = GroupSessionHighlight(
                            group_session=session,
                            membership=member,
                        )
                        highlight.notes = highlight_notes
                        highlight.save()

            messages.success(request, _("Session logged."))
            return redirect("groups:group_detail", group_id=group.pk)
    else:
        form = SessionLogForm(initial={"session_date": timezone.now().date()})

    # Build attendance data -- all checked by default (Rec #9)
    attendance_data = [
        {"membership": m, "present": True} for m in members
    ]

    return render(request, "groups/session_log.html", {
        "group": group,
        "form": form,
        "attendance_data": attendance_data,
        "members": members,
        "breadcrumbs": [
            {"url": reverse("groups:group_list"), "label": _("Groups")},
            {"url": reverse("groups:group_detail", args=[group.pk]), "label": group.name},
            {"url": "", "label": _("Log Session")},
        ],
        "user_role_for_program": _get_user_role_for_group(request, group),
    })


# ---------------------------------------------------------------------------
# 6. Membership add
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def membership_add(request, group_id):
    """Add a member to a group (existing client or named non-client)."""
    group = get_object_or_404(Group, pk=group_id)
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))

    if request.method == "POST":
        client_file_id = request.POST.get("client_file", "").strip()
        member_name = request.POST.get("member_name", "").strip()
        role = request.POST.get("role", "member")
        if role not in ("member", "leader"):
            role = "member"

        if client_file_id:
            # Security: only allow adding clients the user can see
            base_qs = get_client_queryset(request.user)
            client = get_object_or_404(base_qs, pk=client_file_id)
            # Check for duplicate membership
            if GroupMembership.objects.filter(
                group=group, client_file=client, status="active",
            ).exists():
                messages.warning(request, _("This client is already a member."))
            else:
                GroupMembership.objects.create(
                    group=group,
                    client_file=client,
                    role=role,
                )
                messages.success(request, _("Member added."))
        elif member_name:
            GroupMembership.objects.create(
                group=group,
                member_name=member_name,
                role=role,
            )
            messages.success(request, _("Member added."))
        else:
            messages.error(request, _("Please select a client or enter a name."))

        return redirect("groups:group_detail", group_id=group.pk)

    # GET -- show the add-member form (filtered by demo/real separation)
    clients = get_client_queryset(request.user).filter(status="active").order_by("pk")
    return render(request, "groups/membership_add.html", {
        "group": group,
        "clients": clients,
        "breadcrumbs": [
            {"url": reverse("groups:group_list"), "label": _("Groups")},
            {"url": reverse("groups:group_detail", args=[group.pk]), "label": group.name},
            {"url": "", "label": _("Add Member")},
        ],
    })


# ---------------------------------------------------------------------------
# 7. Membership remove
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def membership_remove(request, membership_id):
    """Deactivate a membership (POST only)."""
    membership = get_object_or_404(GroupMembership, pk=membership_id)
    user_program_ids = _get_user_program_ids(request.user)
    if membership.group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))
    if request.method == "POST":
        membership.status = "inactive"
        membership.save()
        messages.success(request, _("Member removed."))
    return redirect("groups:group_detail", group_id=membership.group_id)


# ---------------------------------------------------------------------------
# 8. Milestone create (project groups only)
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def milestone_create(request, group_id):
    """Create a milestone for a project-type group."""
    group = get_object_or_404(Group, pk=group_id, group_type="project")
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))
    if request.method == "POST":
        form = ProjectMilestoneForm(request.POST)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.group = group
            milestone.save()
            messages.success(request, _("Milestone created."))
            return redirect("groups:group_detail", group_id=group.pk)
    else:
        form = ProjectMilestoneForm()
    return render(request, "groups/milestone_form.html", {
        "form": form,
        "group": group,
    })


# ---------------------------------------------------------------------------
# 9. Milestone edit
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def milestone_edit(request, milestone_id):
    """Edit an existing project milestone."""
    milestone = get_object_or_404(ProjectMilestone, pk=milestone_id)
    group = milestone.group
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))
    if request.method == "POST":
        form = ProjectMilestoneForm(request.POST, instance=milestone)
        if form.is_valid():
            form.save()
            messages.success(request, _("Milestone updated."))
            return redirect("groups:group_detail", group_id=group.pk)
    else:
        form = ProjectMilestoneForm(instance=milestone)
    return render(request, "groups/milestone_form.html", {
        "form": form,
        "group": group,
        "milestone": milestone,
    })


# ---------------------------------------------------------------------------
# 10. Outcome create (project groups only)
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def outcome_create(request, group_id):
    """Record an outcome for a project-type group."""
    group = get_object_or_404(Group, pk=group_id, group_type="project")
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))
    if request.method == "POST":
        form = ProjectOutcomeForm(request.POST)
        if form.is_valid():
            ProjectOutcome.objects.create(
                group=group,
                outcome_date=form.cleaned_data["outcome_date"],
                description=form.cleaned_data["description"],
                evidence=form.cleaned_data["evidence"],
                created_by=request.user,
            )
            messages.success(request, _("Outcome recorded."))
            return redirect("groups:group_detail", group_id=group.pk)
    else:
        form = ProjectOutcomeForm(initial={
            "outcome_date": timezone.now().date(),
        })
    return render(request, "groups/outcome_form.html", {
        "form": form,
        "group": group,
    })


# ---------------------------------------------------------------------------
# 11. Attendance report
# ---------------------------------------------------------------------------

@login_required
@minimum_role("staff")
def attendance_report(request, group_id):
    """Attendance report: member x session matrix with CSV export.

    Shows attendance for a date range (default: last 3 months).
    Sortable by attendance rate so staff can see who's been missing.
    CSV export for funder reporting.
    """
    group = get_object_or_404(Group, pk=group_id)
    user_program_ids = _get_user_program_ids(request.user)
    if group.program_id not in user_program_ids:
        return HttpResponseForbidden(_("You do not have access to this group."))

    # Date range (default: last 3 months)
    today = timezone.now().date()
    default_from = today - timedelta(days=90)
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    try:
        date_from_parsed = dt_date.fromisoformat(date_from) if date_from else default_from
    except ValueError:
        date_from_parsed = default_from

    try:
        date_to_parsed = dt_date.fromisoformat(date_to) if date_to else today
    except ValueError:
        date_to_parsed = today

    # Get sessions in range
    sessions = (
        GroupSession.objects.filter(
            group=group,
            session_date__gte=date_from_parsed,
            session_date__lte=date_to_parsed,
        )
        .order_by("session_date")
    )

    # Get all attendance records for these sessions
    attendance_qs = (
        GroupSessionAttendance.objects.filter(group_session__in=sessions)
        .select_related("membership", "membership__client_file", "group_session")
    )

    # Build the matrix: {membership_id: {session_id: present_bool}}
    # Also track member info and totals
    members_data = OrderedDict()  # {membership_id: {"name": str, "sessions": {}, "present": 0, "total": 0}}
    session_list = list(sessions)

    # Initialise from all active + any historically-attending members
    all_memberships = GroupMembership.objects.filter(
        group=group,
    ).select_related("client_file")

    for m in all_memberships:
        members_data[m.pk] = {
            "name": m.display_name,
            "sessions": {},
            "present": 0,
            "total": 0,
        }

    # Fill in attendance data
    for att in attendance_qs:
        mid = att.membership_id
        if mid not in members_data:
            members_data[mid] = {
                "name": att.membership.display_name,
                "sessions": {},
                "present": 0,
                "total": 0,
            }
        members_data[mid]["sessions"][att.group_session_id] = att.present
        members_data[mid]["total"] += 1
        if att.present:
            members_data[mid]["present"] += 1

    # Calculate attendance rates and sort by rate (ascending = most absent first)
    for mid, data in members_data.items():
        if data["total"] > 0:
            data["rate"] = round(data["present"] / data["total"] * 100)
        else:
            data["rate"] = None  # No sessions in range

    # Sort: members with attendance data first (by rate ascending), then members with no data
    sorted_members = sorted(
        members_data.items(),
        key=lambda x: (x[1]["rate"] is None, x[1]["rate"] if x[1]["rate"] is not None else 0),
    )

    # Build rows for template/CSV
    rows = []
    for mid, data in sorted_members:
        row_sessions = []
        for s in session_list:
            present = data["sessions"].get(s.pk)
            row_sessions.append(present)  # True, False, or None (not recorded)
        rows.append({
            "name": data["name"],
            "sessions": row_sessions,
            "present": data["present"],
            "total": data["total"],
            "rate": data["rate"],
        })

    # CSV export
    if request.GET.get("format") == "csv":
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)

        # Header comment rows
        writer.writerow(sanitise_csv_row(
            [f"# {_('Attendance Report')}: {group.name}"]
        ))
        writer.writerow(sanitise_csv_row(
            [f"# {_('Date range')}: {date_from_parsed} — {date_to_parsed}"]
        ))
        writer.writerow(sanitise_csv_row(
            [f"# {_('Total sessions')}: {len(session_list)}"]
        ))
        writer.writerow([])

        # Column headers
        header = [_("Member")]
        for s in session_list:
            header.append(str(s.session_date))
        header.extend([_("Present"), _("Total"), _("Rate %")])
        writer.writerow(sanitise_csv_row(header))

        # Data rows
        for row in rows:
            csv_row = [row["name"]]
            for present in row["sessions"]:
                if present is True:
                    csv_row.append(_("Yes"))
                elif present is False:
                    csv_row.append(_("No"))
                else:
                    csv_row.append("—")
            csv_row.extend([
                row["present"],
                row["total"],
                f"{row['rate']}%" if row["rate"] is not None else "—",
            ])
            writer.writerow(sanitise_csv_row(csv_row))

        content = csv_buffer.getvalue()
        safe_name = sanitise_filename(group.name.replace(" ", "_"))
        filename = f"attendance_{safe_name}_{date_from_parsed}_{date_to_parsed}.csv"
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return render(request, "groups/attendance_report.html", {
        "group": group,
        "sessions": session_list,
        "rows": rows,
        "date_from": str(date_from_parsed),
        "date_to": str(date_to_parsed),
        "total_sessions": len(session_list),
        "breadcrumbs": [
            {"url": reverse("groups:group_list"), "label": _("Groups")},
            {"url": reverse("groups:group_detail", args=[group.pk]), "label": group.name},
            {"url": "", "label": _("Attendance Report")},
        ],
    })
