"""Root URL — staff dashboard with search, recent clients, and alerts."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import path
from django.utils import timezone


@login_required
def home(request):
    from apps.clients.models import ClientFile, ClientProgramEnrolment
    from apps.clients.views import _get_accessible_clients, _get_accessible_programs
    from apps.events.models import Alert
    from apps.notes.models import ProgressNote

    # --- Recently viewed clients (stored in session) ---
    recent_ids = request.session.get("recent_clients", [])
    recent_clients = []
    if recent_ids:
        clients_by_id = {c.pk: c for c in ClientFile.objects.filter(pk__in=recent_ids)}
        # Preserve order
        for cid in recent_ids:
            if cid in clients_by_id:
                c = clients_by_id[cid]
                recent_clients.append({
                    "client": c,
                    "name": f"{c.first_name} {c.last_name}",
                })

    # --- Quick stats ---
    accessible = _get_accessible_clients(request.user)
    active_count = accessible.filter(status="active").count()
    total_count = accessible.count()

    # --- Active alerts (across all accessible clients) ---
    accessible_ids = list(accessible.values_list("pk", flat=True))
    active_alerts = Alert.objects.filter(
        client_file_id__in=accessible_ids,
        status="default",
    ).select_related("client_file").order_by("-created_at")[:5]
    alert_count = active_alerts.count()

    # --- Notes recorded today ---
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    notes_today_count = ProgressNote.objects.filter(
        client_file_id__in=accessible_ids,
        created_at__gte=today_start,
    ).count()

    # --- Clients not seen in 30+ days ---
    thirty_days_ago = timezone.now() - timedelta(days=30)
    # Get clients with recent notes
    clients_with_recent_notes = set(
        ProgressNote.objects.filter(
            client_file_id__in=accessible_ids,
            created_at__gte=thirty_days_ago,
        ).values_list("client_file_id", flat=True)
    )
    # Active clients without recent notes
    needs_attention = []
    for c in accessible.filter(status="active")[:200]:
        if c.pk not in clients_with_recent_notes:
            needs_attention.append({
                "client": c,
                "name": f"{c.first_name} {c.last_name}",
            })
        if len(needs_attention) >= 10:
            break
    needs_attention_count = len(needs_attention)

    # --- Organization name (placeholder — will come from settings later) ---
    org_name = "LogicalOutcomes"

    # --- Accessible programs for search filters ---
    accessible_programs = _get_accessible_programs(request.user)

    return render(request, "clients/home.html", {
        "results": [],
        "query": "",
        "recent_clients": recent_clients,
        "active_count": active_count,
        "total_count": total_count,
        "active_alerts": active_alerts,
        "alert_count": alert_count,
        "notes_today_count": notes_today_count,
        "needs_attention": needs_attention,
        "needs_attention_count": needs_attention_count,
        "org_name": org_name,
        "accessible_programs": accessible_programs,
    })


urlpatterns = [
    path("", home, name="home"),
]
