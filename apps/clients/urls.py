from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import path
from django.utils import timezone

from apps.portal.staff_views import create_staff_portal_note

from . import erasure_views, views


@login_required
def executive_dashboard(request):
    """
    Executive dashboard with aggregate statistics only.

    Executives see high-level program metrics without access to individual
    client records. This protects client confidentiality while giving
    leadership the oversight they need.
    """
    from apps.clients.models import ClientFile, ClientProgramEnrolment
    from apps.notes.models import ProgressNote
    from apps.programs.models import Program, UserProgramRole

    # Get programs the executive is assigned to
    user_program_ids = list(
        UserProgramRole.objects.filter(
            user=request.user, status="active"
        ).values_list("program_id", flat=True)
    )
    programs = Program.objects.filter(pk__in=user_program_ids, status="active")

    # Base client queryset (respects demo/real separation)
    from apps.clients.views import get_client_queryset
    base_clients = get_client_queryset(request.user)

    # Calculate time boundaries
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())

    # Build program statistics
    program_stats = []
    total_clients = 0
    total_active = 0
    total_with_consent = 0

    for program in programs:
        # Clients enrolled in this program
        enrolled_client_ids = ClientProgramEnrolment.objects.filter(
            program=program, status="enrolled"
        ).values_list("client_file_id", flat=True)

        # Filter to accessible clients
        program_clients = base_clients.filter(pk__in=enrolled_client_ids)

        active = program_clients.filter(status="active").count()
        inactive = program_clients.filter(status="inactive").count()
        discharged = program_clients.filter(status="discharged").count()
        total = active + inactive + discharged

        # New this month
        new_this_month = program_clients.filter(created_at__gte=month_start).count()

        # Notes this week
        notes_this_week = ProgressNote.objects.filter(
            client_file_id__in=enrolled_client_ids,
            created_at__gte=week_start,
        ).count()

        # Consent compliance
        with_consent = program_clients.exclude(consent_given_at__isnull=True).count()

        program_stats.append({
            "program": program,
            "total": total,
            "active": active,
            "inactive": inactive,
            "discharged": discharged,
            "new_this_month": new_this_month,
            "notes_this_week": notes_this_week,
            "consent_count": with_consent,
            "consent_pct": round(with_consent / total * 100) if total > 0 else 0,
        })

        total_clients += total
        total_active += active
        total_with_consent += with_consent

    # Overall statistics
    overall_consent_pct = round(total_with_consent / total_clients * 100) if total_clients > 0 else 0

    return render(request, "clients/executive_dashboard.html", {
        "program_stats": program_stats,
        "total_clients": total_clients,
        "total_active": total_active,
        "overall_consent_pct": overall_consent_pct,
        "data_refreshed_at": now,
        "nav_active": "executive",
    })


app_name = "clients"

urlpatterns = [
    path("executive/", executive_dashboard, name="executive_dashboard"),
    path("", views.client_list, name="client_list"),
    path("create/", views.client_create, name="client_create"),
    path("check-duplicate/", views.check_duplicate, name="check_duplicate"),
    path("search/", views.client_search, name="client_search"),
    path("<int:client_id>/", views.client_detail, name="client_detail"),
    path("<int:client_id>/edit/", views.client_edit, name="client_edit"),
    path("<int:client_id>/edit-contact/", views.client_contact_edit, name="client_contact_edit"),
    path("<int:client_id>/custom-fields/", views.client_save_custom_fields, name="client_save_custom_fields"),
    path("<int:client_id>/custom-fields/display/", views.client_custom_fields_display, name="client_custom_fields_display"),
    path("<int:client_id>/custom-fields/edit/", views.client_custom_fields_edit, name="client_custom_fields_edit"),
    # Consent recording (PRIV1)
    path("<int:client_id>/consent/display/", views.client_consent_display, name="client_consent_display"),
    path("<int:client_id>/consent/edit/", views.client_consent_edit, name="client_consent_edit"),
    path("<int:client_id>/consent/", views.client_consent_save, name="client_consent_save"),
    # Custom field admin (FIELD1)
    path("admin/fields/", views.custom_field_admin, name="custom_field_admin"),
    path("admin/fields/groups/create/", views.custom_field_group_create, name="custom_field_group_create"),
    path("admin/fields/groups/<int:group_id>/edit/", views.custom_field_group_edit, name="custom_field_group_edit"),
    path("admin/fields/create/", views.custom_field_def_create, name="custom_field_def_create"),
    path("admin/fields/<int:field_id>/edit/", views.custom_field_def_edit, name="custom_field_def_edit"),
    # Erasure request (ERASE4)
    path("<int:client_id>/erase/", erasure_views.erasure_request_create, name="client_erasure_request"),
    # Portal staff note
    path("<int:client_id>/portal-note/", create_staff_portal_note, name="create_staff_portal_note"),
]
