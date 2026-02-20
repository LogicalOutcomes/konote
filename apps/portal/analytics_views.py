"""Portal usage analytics — aggregate stats for staff (D11).

Shows only aggregate counts. NEVER per-participant data (per design decision D13).
"""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.decorators import admin_required


@login_required
@admin_required
def portal_analytics(request):
    """Aggregate portal usage statistics."""
    flags = FeatureToggle.get_all_flags()
    if not flags.get("participant_portal"):
        raise Http404

    from apps.portal.models import (
        CorrectionRequest,
        ParticipantJournalEntry,
        ParticipantMessage,
        ParticipantUser,
    )

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "total_accounts": ParticipantUser.objects.filter(is_active=True).count(),
        "accounts_created_this_month": ParticipantUser.objects.filter(
            created_at__gte=month_start,
        ).count(),
        "total_journal_entries": ParticipantJournalEntry.objects.count(),
        "journal_entries_this_month": ParticipantJournalEntry.objects.filter(
            created_at__gte=month_start,
        ).count(),
        "total_messages": ParticipantMessage.objects.count(),
        "messages_this_month": ParticipantMessage.objects.filter(
            created_at__gte=month_start,
        ).count(),
        "corrections_pending": CorrectionRequest.objects.filter(status="pending").count(),
        "corrections_total": CorrectionRequest.objects.count(),
    }

    # Login count from audit log (this month)
    try:
        from apps.audit.models import AuditLog
        stats["logins_this_month"] = AuditLog.objects.using("audit").filter(
            action="portal_login",
            event_timestamp__gte=month_start,
        ).count()
    except Exception:
        stats["logins_this_month"] = 0

    # Survey stats if surveys feature is enabled
    try:
        from apps.surveys.engine import is_surveys_enabled
        from apps.surveys.models import SurveyAssignment
        if is_surveys_enabled():
            stats["surveys_completed_this_month"] = SurveyAssignment.objects.filter(
                status="completed",
                completed_at__gte=month_start,
            ).count()
            stats["surveys_pending"] = SurveyAssignment.objects.filter(
                status__in=("pending", "in_progress"),
            ).count()
    except Exception:
        pass

    return render(request, "portal/analytics.html", {"stats": stats})
