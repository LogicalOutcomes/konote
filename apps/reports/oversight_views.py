"""Views for Safety Oversight Reports and Report Scheduling."""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.auth_app.decorators import admin_required

from .forms import OversightApproveForm, OversightReportForm, ReportScheduleForm
from .models import OversightReportSnapshot, ReportSchedule
from .oversight import generate_oversight_report, get_oversight_context, quarter_dates


# ---------------------------------------------------------------------------
# Safety Oversight Reports
# ---------------------------------------------------------------------------

@login_required
@admin_required
def oversight_report_list(request):
    """List all generated oversight reports."""
    reports = OversightReportSnapshot.objects.all()[:20]
    return render(request, "reports/oversight_list.html", {
        "reports": reports,
        "nav_active": "reports",
    })


@login_required
@admin_required
def oversight_report_generate(request):
    """Generate a new oversight report for a selected quarter."""
    if request.method == "POST":
        form = OversightReportForm(request.POST)
        if form.is_valid():
            period_label = form.cleaned_data["period"]
            period_start, period_end = quarter_dates(period_label)
            snapshot = generate_oversight_report(
                period_label, period_start, period_end, request.user,
            )
            return redirect("reports:oversight_detail", report_id=snapshot.pk)
    else:
        form = OversightReportForm()

    return render(request, "reports/oversight_generate.html", {
        "form": form,
        "nav_active": "reports",
    })


@login_required
@admin_required
def oversight_report_detail(request, report_id):
    """View a generated oversight report with approve/file controls."""
    snapshot = get_object_or_404(OversightReportSnapshot, pk=report_id)
    is_external = request.GET.get("external") == "1"
    context = get_oversight_context(snapshot, is_external=is_external)
    context["approve_form"] = OversightApproveForm()
    context["nav_active"] = "reports"
    return render(request, "reports/oversight_detail.html", context)


@login_required
@admin_required
@require_POST
def oversight_report_approve(request, report_id):
    """Approve and file the oversight report (attestation)."""
    snapshot = get_object_or_404(OversightReportSnapshot, pk=report_id)
    form = OversightApproveForm(request.POST)

    if form.is_valid():
        snapshot.narrative = form.cleaned_data.get("narrative", "")
        snapshot.approved_by = request.user
        snapshot.approved_at = timezone.now()
        snapshot.save(update_fields=[
            "narrative", "approved_by", "approved_at",
        ])

        # If this report is linked to a schedule, mark it generated
        schedules = ReportSchedule.objects.filter(
            report_type="oversight", is_active=True,
        )
        for schedule in schedules:
            if (schedule.last_generated_at is None
                    or schedule.last_generated_at < snapshot.created_at):
                schedule.last_generated_at = timezone.now()
                schedule.save(update_fields=["last_generated_at", "updated_at"])
                schedule.advance_due_date()

    return redirect("reports:oversight_detail", report_id=snapshot.pk)


@login_required
@admin_required
def oversight_report_pdf(request, report_id):
    """Generate PDF of the oversight report."""
    from .pdf_utils import is_pdf_available, render_pdf

    snapshot = get_object_or_404(OversightReportSnapshot, pk=report_id)

    if not is_pdf_available():
        from django.contrib import messages
        messages.error(request, "PDF generation is not available on this server.")
        return redirect("reports:oversight_detail", report_id=snapshot.pk)

    is_external = request.GET.get("external") == "1"
    context = get_oversight_context(snapshot, is_external=is_external)

    filename = f"safety-oversight-{snapshot.period_label.replace(' ', '-')}.pdf"
    return render_pdf("reports/pdf_oversight_report.html", context, filename)


# ---------------------------------------------------------------------------
# Report Scheduling
# ---------------------------------------------------------------------------

@login_required
@admin_required
def report_schedule_list(request):
    """List all report schedules."""
    schedules = ReportSchedule.objects.all()
    return render(request, "reports/schedule_list.html", {
        "schedules": schedules,
        "nav_active": "reports",
    })


@login_required
@admin_required
def report_schedule_create(request):
    """Create a new report schedule."""
    if request.method == "POST":
        form = ReportScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            return redirect("reports:schedule_list")
    else:
        form = ReportScheduleForm()

    return render(request, "reports/schedule_form.html", {
        "form": form,
        "is_edit": False,
        "nav_active": "reports",
    })


@login_required
@admin_required
def report_schedule_edit(request, schedule_id):
    """Edit an existing report schedule."""
    schedule = get_object_or_404(ReportSchedule, pk=schedule_id)

    if request.method == "POST":
        form = ReportScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            return redirect("reports:schedule_list")
    else:
        form = ReportScheduleForm(instance=schedule)

    return render(request, "reports/schedule_form.html", {
        "form": form,
        "schedule": schedule,
        "is_edit": True,
        "nav_active": "reports",
    })
