"""Report views — aggregate metric CSV export, CMT export, client analysis charts, and secure links."""
import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import F, Q
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.auth_app.decorators import admin_required
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.clients.views import get_client_queryset
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import PlanTarget, PlanTargetMetric
from apps.programs.models import UserProgramRole
from .achievements import get_achievement_summary, format_achievement_summary
from .cmt_export import generate_cmt_data, generate_cmt_csv_rows
from .csv_utils import sanitise_csv_row, sanitise_filename
from .demographics import aggregate_by_demographic, get_age_range, parse_grouping_choice
from .suppression import suppress_small_cell
from .forms import CMTExportForm, ClientDataExportForm, MetricExportForm
from .models import SecureExportLink
from .utils import can_create_export, get_manageable_programs

logger = logging.getLogger(__name__)


from konote.utils import get_client_ip as _get_client_ip


def _notify_admins_elevated_export(link, request):
    """
    Send email notification to all active admins about an elevated export.

    Elevated exports (100+ clients or includes notes) have a delay before
    download is available. This notification gives admins time to review
    and revoke if needed.

    Fails gracefully — logs a warning if email sending fails but does not
    block the export creation.
    """
    admins = User.objects.filter(is_admin=True, is_active=True)
    admin_emails = [u.email for u in admins if u.email]
    if not admin_emails:
        logger.warning("No admin email addresses found for elevated export notification (link %s)", link.id)
        return

    manage_url = request.build_absolute_uri(
        reverse("reports:manage_export_links")
    )

    context = {
        "link": link,
        "creator_name": link.created_by.display_name,
        "creator_email": link.created_by.email or "no email on file",
        "manage_url": manage_url,
        "available_at": link.available_at,
        "delay_minutes": getattr(settings, "ELEVATED_EXPORT_DELAY_MINUTES", 10),
    }

    subject = f"Elevated Export Alert — {link.client_count} clients"
    text_body = render_to_string("reports/email/elevated_export_alert.txt", context)
    html_body = render_to_string("reports/email/elevated_export_alert.html", context)

    try:
        send_mail(
            subject=subject,
            message=text_body,
            html_message=html_body,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=admin_emails,
        )
        SecureExportLink.objects.filter(pk=link.pk).update(
            admin_notified_at=timezone.now()
        )
    except Exception:
        logger.warning(
            "Failed to send elevated export notification for link %s",
            link.id,
            exc_info=True,
        )


def _save_export_and_create_link(request, content, filename, export_type,
                                  client_count, includes_notes, recipient,
                                  filters_dict=None):
    """
    Save export content to a temp file and create a SecureExportLink.

    Args:
        request: The HTTP request (for user info).
        content: File content — str for CSV, bytes for PDF.
        filename: Display filename for downloads (e.g., "export_2026-02-05.csv").
        export_type: One of "client_data", "metrics", "cmt".
        client_count: Number of clients in the export.
        includes_notes: Whether clinical note content is included.
        recipient: Who is receiving the data (from ExportRecipientMixin).
        filters_dict: Optional dict of filter parameters for audit.

    Returns:
        SecureExportLink instance.
    """
    export_dir = settings.SECURE_EXPORT_DIR
    os.makedirs(export_dir, exist_ok=True)

    link_id = uuid.uuid4()
    safe_filename = f"{link_id}_{filename}"
    file_path = os.path.join(export_dir, safe_filename)

    # Write content to file
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    with open(file_path, mode, encoding=encoding) as f:
        f.write(content)

    expiry_hours = getattr(settings, "SECURE_EXPORT_LINK_EXPIRY_HOURS", 24)
    is_elevated = client_count >= 100 or includes_notes
    link = SecureExportLink.objects.create(
        id=link_id,
        created_by=request.user,
        expires_at=timezone.now() + timedelta(hours=expiry_hours),
        export_type=export_type,
        filters_json=json.dumps(filters_dict or {}),
        client_count=client_count,
        includes_notes=includes_notes,
        recipient=recipient,
        filename=filename,
        file_path=file_path,
        is_elevated=is_elevated,
    )

    if is_elevated:
        _notify_admins_elevated_export(link, request)

    return link


def _build_demographic_map(metric_values, grouping_type, grouping_field, as_of_date):
    """
    Build a mapping of client IDs to their demographic group labels.

    Args:
        metric_values: QuerySet of MetricValue objects.
        grouping_type: "age_range" or "custom_field".
        grouping_field: CustomFieldDefinition for custom_field grouping.
        as_of_date: Date to use for age calculations.

    Returns:
        Dict mapping client_id to demographic group label.
    """
    from apps.clients.models import ClientDetailValue, ClientFile

    client_demographic_map = {}

    # Collect all unique client IDs
    client_ids = set()
    for mv in metric_values:
        client_ids.add(mv.progress_note_target.progress_note.client_file_id)

    if grouping_type == "age_range":
        # Load clients to access encrypted birth_date
        clients = ClientFile.objects.filter(pk__in=client_ids)
        for client in clients:
            client_demographic_map[client.pk] = get_age_range(client.birth_date, as_of_date)

    elif grouping_type == "custom_field" and grouping_field:
        # Build option labels lookup for dropdown fields
        option_labels = {}
        if grouping_field.input_type == "select" and grouping_field.options_json:
            for option in grouping_field.options_json:
                if isinstance(option, dict):
                    option_labels[option.get("value", "")] = option.get("label", option.get("value", ""))
                else:
                    option_labels[option] = option

        # Get custom field values for all clients
        values = ClientDetailValue.objects.filter(
            client_file_id__in=client_ids,
            field_def=grouping_field,
        )

        for cv in values:
            raw_value = cv.get_value()
            if not raw_value:
                client_demographic_map[cv.client_file_id] = "Unknown"
            else:
                display_value = option_labels.get(raw_value, raw_value)
                client_demographic_map[cv.client_file_id] = display_value

        # Mark clients without a value as Unknown
        for client_id in client_ids:
            if client_id not in client_demographic_map:
                client_demographic_map[client_id] = "Unknown"

    return client_demographic_map


def _get_grouping_label(group_by_value, grouping_field):
    """
    Get a human-readable label for the grouping type.

    Args:
        group_by_value: The raw form value (e.g., "age_range", "custom_123").
        grouping_field: The CustomFieldDefinition if applicable.

    Returns:
        String label for the grouping (e.g., "Age Range", "Gender").
    """
    if not group_by_value:
        return None

    if group_by_value == "age_range":
        return "Age Range"

    if grouping_field:
        return grouping_field.name

    return "Demographic Group"


@login_required
def export_form(request):
    """
    GET  — display the export filter form.
    POST — validate, query metric values, and return a CSV download.

    Access: admin (any program) or program_manager (their programs only).
    """
    if not can_create_export(request.user, "metrics"):
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method != "POST":
        form = MetricExportForm(user=request.user)
        return render(request, "reports/export_form.html", {"form": form})

    form = MetricExportForm(request.POST, user=request.user)
    if not form.is_valid():
        return render(request, "reports/export_form.html", {"form": form})

    program = form.cleaned_data["program"]
    selected_metrics = form.cleaned_data["metrics"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    group_by_value = form.cleaned_data.get("group_by", "")
    include_achievement = form.cleaned_data.get("include_achievement_rate", False)

    # Parse the grouping choice
    grouping_type, grouping_field = parse_grouping_choice(group_by_value)

    # Find clients matching user's demo status enrolled in the selected programme
    # Security: Demo users can only export demo clients; real users only real clients
    accessible_client_ids = get_client_queryset(request.user).values_list("pk", flat=True)
    client_ids = ClientProgramEnrolment.objects.filter(
        program=program, status="enrolled",
        client_file_id__in=accessible_client_ids,
    ).values_list("client_file_id", flat=True)

    # Build date-aware boundaries
    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))

    # Filter progress notes by effective date (backdate when present, else created_at)
    notes = ProgressNote.objects.filter(
        client_file_id__in=client_ids,
        status="default",
    ).filter(
        Q(backdate__range=(date_from_dt, date_to_dt))
        | Q(backdate__isnull=True, created_at__range=(date_from_dt, date_to_dt))
    )

    # Get the actual metric values
    metric_values = (
        MetricValue.objects.filter(
            metric_def__in=selected_metrics,
            progress_note_target__progress_note__in=notes,
        )
        .select_related(
            "metric_def",
            "progress_note_target__progress_note__client_file",
            "progress_note_target__progress_note__author",
        )
    )

    if not metric_values.exists():
        return render(
            request,
            "reports/export_form.html",
            {
                "form": form,
                "no_data": True,
            },
        )

    # Build demographic lookup for each client if grouping is enabled
    client_demographic_map = {}
    if grouping_type != "none":
        client_demographic_map = _build_demographic_map(
            metric_values, grouping_type, grouping_field, date_to
        )

    # Get grouping label for display
    grouping_label = _get_grouping_label(group_by_value, grouping_field)

    # Count unique clients in the result set
    unique_clients = set()
    rows = []
    for mv in metric_values:
        note = mv.progress_note_target.progress_note
        client = note.client_file
        unique_clients.add(client.pk)

        row = {
            "record_id": client.record_id,
            "metric_name": mv.metric_def.name,
            "value": mv.value,
            "date": note.effective_date.strftime("%Y-%m-%d"),
            "author": note.author.display_name,
        }

        # Add demographic group if grouping is enabled
        if grouping_type != "none":
            row["demographic_group"] = client_demographic_map.get(client.pk, "Unknown")

        rows.append(row)

    # Calculate achievement rates if requested
    achievement_summary = None
    if include_achievement:
        achievement_summary = get_achievement_summary(
            program,
            date_from=date_from,
            date_to=date_to,
            metric_defs=list(selected_metrics),
            use_latest=True,
        )

    export_format = form.cleaned_data["format"]
    recipient = form.get_recipient_display()

    filters_dict = {
        "program": program.name,
        "metrics": [m.name for m in selected_metrics],
        "date_from": str(date_from),
        "date_to": str(date_to),
    }
    if grouping_type != "none":
        filters_dict["grouped_by"] = grouping_label

    # Apply small-cell suppression for confidential programs
    total_clients_display = suppress_small_cell(len(unique_clients), program)
    total_data_points_display = suppress_small_cell(len(rows), program)

    if export_format == "pdf":
        from .pdf_views import generate_funder_pdf
        pdf_response = generate_funder_pdf(
            request, program, selected_metrics,
            date_from, date_to, rows, unique_clients,
            grouping_type=grouping_type,
            grouping_label=grouping_label,
            achievement_summary=achievement_summary,
            total_clients_display=total_clients_display,
            total_data_points_display=total_data_points_display,
        )
        safe_name = sanitise_filename(program.name.replace(" ", "_"))
        filename = f"funder_report_{safe_name}_{date_from}_{date_to}.pdf"
        content = pdf_response.content
    else:
        # Build CSV in memory buffer (not directly into HttpResponse)
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        # Summary header rows (prefixed with # so spreadsheet apps treat them as comments)
        writer.writerow(sanitise_csv_row([f"# Programme: {program.name}"]))
        writer.writerow(sanitise_csv_row([f"# Date Range: {date_from} to {date_to}"]))
        writer.writerow(sanitise_csv_row([f"# Total Clients: {total_clients_display}"]))
        writer.writerow(sanitise_csv_row([f"# Total Data Points: {total_data_points_display}"]))
        if grouping_type != "none":
            writer.writerow(sanitise_csv_row([f"# Grouped By: {grouping_label}"]))

        # Achievement rate summary if requested
        if achievement_summary:
            writer.writerow([])  # blank separator
            writer.writerow(sanitise_csv_row(["# ===== ACHIEVEMENT RATE SUMMARY ====="]))
            ach_total = suppress_small_cell(achievement_summary["total_clients"], program)
            ach_met = suppress_small_cell(achievement_summary["clients_met_any_target"], program)
            if isinstance(ach_total, str) or isinstance(ach_met, str):
                writer.writerow(sanitise_csv_row([
                    f"# Overall: {ach_met} of {ach_total} clients met at least one target"
                ]))
            elif achievement_summary["total_clients"] > 0:
                writer.writerow(sanitise_csv_row([
                    f"# Overall: {ach_met} of "
                    f"{ach_total} clients "
                    f"({achievement_summary['overall_rate']}%) met at least one target"
                ]))
            else:
                writer.writerow(sanitise_csv_row(["# No client data available for achievement calculation"]))

            for metric in achievement_summary.get("by_metric", []):
                m_total = suppress_small_cell(metric["total_clients"], program)
                m_met = suppress_small_cell(metric.get("clients_met_target", 0), program)
                if metric["has_target"]:
                    if isinstance(m_total, str) or isinstance(m_met, str):
                        writer.writerow(sanitise_csv_row([
                            f"# {metric['metric_name']}: {m_met} of {m_total} clients "
                            f"met target of {metric['target_value']}"
                        ]))
                    else:
                        writer.writerow(sanitise_csv_row([
                            f"# {metric['metric_name']}: {m_met} of "
                            f"{m_total} clients ({metric['achievement_rate']}%) "
                            f"met target of {metric['target_value']}"
                        ]))
                else:
                    writer.writerow(sanitise_csv_row([
                        f"# {metric['metric_name']}: {m_total} clients "
                        "(no target defined)"
                    ]))

        writer.writerow([])  # blank separator

        # Column headers — include demographic column if grouping enabled
        if grouping_type != "none":
            writer.writerow(sanitise_csv_row([grouping_label, "Client Record ID", "Metric Name", "Value", "Date", "Author"]))
        else:
            writer.writerow(sanitise_csv_row(["Client Record ID", "Metric Name", "Value", "Date", "Author"]))

        for row in rows:
            if grouping_type != "none":
                writer.writerow(sanitise_csv_row([
                    row.get("demographic_group", "Unknown"),
                    row["record_id"],
                    row["metric_name"],
                    row["value"],
                    row["date"],
                    row["author"],
                ]))
            else:
                writer.writerow(sanitise_csv_row([
                    row["record_id"],
                    row["metric_name"],
                    row["value"],
                    row["date"],
                    row["author"],
                ]))

        safe_prog = sanitise_filename(program.name.replace(" ", "_"))
        filename = f"metric_export_{safe_prog}_{date_from}_{date_to}.csv"
        content = csv_buffer.getvalue()

    # Save to file and create secure download link
    link = _save_export_and_create_link(
        request=request,
        content=content,
        filename=filename,
        export_type="metrics",
        client_count=len(unique_clients),
        includes_notes=False,
        recipient=recipient,
        filters_dict=filters_dict,
    )

    # Audit log with recipient tracking
    audit_metadata = {
        "program": program.name,
        "metrics": [m.name for m in selected_metrics],
        "date_from": str(date_from),
        "date_to": str(date_to),
        "total_clients": len(unique_clients),
        "total_data_points": len(rows),
        "recipient": recipient,
        "secure_link_id": str(link.id),
    }
    if grouping_type != "none":
        audit_metadata["grouped_by"] = grouping_label
    if achievement_summary:
        audit_metadata["include_achievement_rate"] = True
        audit_metadata["achievement_rate"] = achievement_summary.get("overall_rate")

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="metric_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata=audit_metadata,
    )

    download_url = request.build_absolute_uri(
        reverse("reports:download_export", args=[link.id])
    )
    return render(request, "reports/export_link_created.html", {
        "link": link,
        "download_url": download_url,
    })


def _get_client_or_403(request, client_id):
    """Return client if user has access via program roles, otherwise None.

    Delegates to the shared canonical implementation.
    """
    from apps.programs.access import get_client_or_403
    return get_client_or_403(request, client_id)


@login_required
def client_analysis(request, client_id):
    """Show progress charts for a client's metric data."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Get user's accessible programs (respects CONF9 context switcher)
    from apps.programs.access import build_program_display_context, get_user_program_ids
    active_ids = getattr(request, "active_program_ids", None)
    user_program_ids = get_user_program_ids(request.user, active_ids)
    program_ctx = build_program_display_context(request.user, active_ids)

    # Get targets with metrics — filtered by user's accessible programs
    # PlanTarget doesn't have a direct program FK, so filter through plan_section.program
    targets = PlanTarget.objects.filter(
        client_file=client, status="default"
    ).filter(
        Q(plan_section__program_id__in=user_program_ids) | Q(plan_section__program__isnull=True)
    ).select_related("plan_section__program").prefetch_related("metrics")

    chart_data = []
    for target in targets:
        ptm_links = PlanTargetMetric.objects.filter(
            plan_target=target
        ).select_related("metric_def")

        # Get program info from the section for grouping
        section_program = target.plan_section.program if target.plan_section else None
        program_name = section_program.name if section_program else None
        program_colour = section_program.colour_hex if section_program else None

        for ptm in ptm_links:
            metric_def = ptm.metric_def
            # Get all recorded values for this metric on this target
            values = MetricValue.objects.filter(
                metric_def=metric_def,
                progress_note_target__plan_target=target,
                progress_note_target__progress_note__client_file=client,
                progress_note_target__progress_note__status="default",
            ).select_related(
                "progress_note_target__progress_note"
            ).order_by(
                "progress_note_target__progress_note__created_at"
            )

            if not values:
                continue

            data_points = []
            for mv in values:
                note = mv.progress_note_target.progress_note
                date = note.effective_date.strftime("%Y-%m-%d")
                try:
                    numeric_val = float(mv.value)
                except (ValueError, TypeError):
                    continue
                data_points.append({"date": date, "value": numeric_val})

            if data_points:
                chart_data.append({
                    "target_name": target.name,
                    "metric_name": metric_def.name,
                    "unit": metric_def.unit or "",
                    "min_value": metric_def.min_value,
                    "max_value": metric_def.max_value,
                    "data_points": data_points,
                    "program_name": program_name,
                    "program_colour": program_colour,
                })

    # Sort by program_name for template {% regroup %} tag
    chart_data.sort(key=lambda c: (c["program_name"] or "", c["target_name"]))

    context = {
        "client": client,
        "chart_data": chart_data,
        "active_tab": "analysis",
        "user_role": getattr(request, "user_program_role", None),
        "show_grouping": program_ctx["show_grouping"],
        "show_program_ui": program_ctx["show_program_ui"],
    }
    if request.headers.get("HX-Request"):
        return render(request, "reports/_tab_analysis.html", context)
    return render(request, "reports/analysis.html", context)


@login_required
def cmt_export_form(request):
    """
    United Way CMT (Community Monitoring Tool) export.

    GET  — display the CMT export form.
    POST — generate and return the CMT-formatted report.

    Access: admin (any program) or program_manager (their programs only).

    CMT reports are structured for United Way Canada's funder reporting
    requirements, including:
    - Organisation and programme information
    - Service statistics (individuals served, contacts)
    - Age demographics (CMT standard categories)
    - Outcome achievement rates
    """
    if not can_create_export(request.user, "cmt"):
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method != "POST":
        form = CMTExportForm(user=request.user)
        return render(request, "reports/cmt_export_form.html", {"form": form})

    form = CMTExportForm(request.POST, user=request.user)
    if not form.is_valid():
        return render(request, "reports/cmt_export_form.html", {"form": form})

    program = form.cleaned_data["program"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    fiscal_year_label = form.cleaned_data["fiscal_year_label"]
    export_format = form.cleaned_data["format"]

    # Generate CMT data
    # Security: Pass user for demo/real filtering
    cmt_data = generate_cmt_data(
        program,
        date_from=date_from,
        date_to=date_to,
        fiscal_year_label=fiscal_year_label,
        user=request.user,
    )

    # Apply small-cell suppression for confidential programs
    cmt_data["total_individuals_served"] = suppress_small_cell(
        cmt_data["total_individuals_served"], program,
    )
    cmt_data["new_clients_this_period"] = suppress_small_cell(
        cmt_data["new_clients_this_period"], program,
    )
    # Suppress age demographic counts individually
    if program.is_confidential and "age_demographics" in cmt_data:
        for age_group, count in cmt_data["age_demographics"].items():
            if isinstance(count, int):
                cmt_data["age_demographics"][age_group] = suppress_small_cell(count, program)

    recipient = form.get_recipient_display()
    safe_name = sanitise_filename(program.name.replace(" ", "_"))
    safe_fy = sanitise_filename(fiscal_year_label.replace(" ", "_"))

    if export_format == "pdf":
        from .pdf_views import generate_cmt_pdf
        pdf_response = generate_cmt_pdf(request, cmt_data)
        filename = f"CMT_Report_{safe_name}_{safe_fy}.pdf"
        content = pdf_response.content
    else:
        # Build CSV in memory buffer
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        csv_rows = generate_cmt_csv_rows(cmt_data)
        for row in csv_rows:
            writer.writerow(sanitise_csv_row(row))
        filename = f"CMT_Report_{safe_name}_{safe_fy}.csv"
        content = csv_buffer.getvalue()

    # Save to file and create secure download link
    link = _save_export_and_create_link(
        request=request,
        content=content,
        filename=filename,
        export_type="cmt",
        client_count=cmt_data.get("total_individuals_served", 0),
        includes_notes=False,
        recipient=recipient,
        filters_dict={
            "program": program.name,
            "fiscal_year": fiscal_year_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
        },
    )

    # Audit log with recipient tracking
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="cmt_report",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "program": program.name,
            "fiscal_year": fiscal_year_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "format": export_format,
            "total_individuals_served": cmt_data["total_individuals_served"],
            "recipient": recipient,
            "secure_link_id": str(link.id),
        },
    )

    download_url = request.build_absolute_uri(
        reverse("reports:download_export", args=[link.id])
    )
    return render(request, "reports/export_link_created.html", {
        "link": link,
        "download_url": download_url,
    })


@login_required
@admin_required
def client_data_export(request):
    """
    Export all client data as CSV for data portability and migration.

    GET  — display the export filter form.
    POST — generate and return a CSV with all client data.

    This export includes:
    - Core demographics (record ID, name, birth date, status)
    - Custom field values (optional)
    - Programme enrolments (optional)
    - Consent and retention information (optional)

    Admin-only access. All exports are audit logged.
    """
    from apps.clients.models import (
        ClientDetailValue,
        ClientFile,
        ClientProgramEnrolment,
        CustomFieldDefinition,
    )

    if request.method != "POST":
        form = ClientDataExportForm()
        # Show accessible client count for preview
        accessible_clients = get_client_queryset(request.user)
        total_client_count = accessible_clients.count()
        return render(request, "reports/client_data_export_form.html", {
            "form": form,
            "total_client_count": total_client_count,
        })

    form = ClientDataExportForm(request.POST)
    if not form.is_valid():
        # Preserve client count on validation failure
        accessible_clients = get_client_queryset(request.user)
        total_client_count = accessible_clients.count()
        return render(request, "reports/client_data_export_form.html", {
            "form": form,
            "total_client_count": total_client_count,
        })

    # Get filter options
    program = form.cleaned_data.get("program")
    status_filter = form.cleaned_data.get("status")
    include_custom_fields = form.cleaned_data.get("include_custom_fields", True)
    include_enrolments = form.cleaned_data.get("include_enrolments", True)
    include_consent = form.cleaned_data.get("include_consent", True)

    # Build base queryset — filter by user's demo status for security
    # Security: Demo users can only export demo clients; real users only real clients
    clients_qs = get_client_queryset(request.user)

    # Apply status filter
    if status_filter:
        clients_qs = clients_qs.filter(status=status_filter)

    # Apply programme filter
    if program:
        enrolled_client_ids = ClientProgramEnrolment.objects.filter(
            program=program
        ).values_list("client_file_id", flat=True)
        clients_qs = clients_qs.filter(pk__in=enrolled_client_ids)

    # Load all clients into memory for decryption
    # Note: This is required because encrypted fields cannot be queried in SQL.
    # Acceptable for up to ~2,000 clients per export.
    clients = list(clients_qs)

    if not clients:
        return render(
            request,
            "reports/client_data_export_form.html",
            {"form": form, "no_data": True},
        )

    # Get custom field definitions if needed
    custom_fields = []
    if include_custom_fields:
        custom_fields = list(
            CustomFieldDefinition.objects.filter(status="active")
            .select_related("group")
            .order_by("group__sort_order", "sort_order")
        )

    # Build CSV in memory buffer
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    export_date = timezone.now().strftime("%Y-%m-%d")
    filename = f"client_data_export_{export_date}.csv"
    if program:
        safe_name = sanitise_filename(program.name.replace(" ", "_"))
        filename = f"client_data_export_{safe_name}_{export_date}.csv"

    # Summary header rows
    writer.writerow(sanitise_csv_row([f"# Client Data Export"]))
    writer.writerow(sanitise_csv_row([f"# Export Date: {export_date}"]))
    writer.writerow(sanitise_csv_row([f"# Total Clients: {len(clients)}"]))
    if program:
        writer.writerow(sanitise_csv_row([f"# Programme Filter: {program.name}"]))
    if status_filter:
        writer.writerow(sanitise_csv_row([f"# Status Filter: {status_filter}"]))
    writer.writerow([])

    # Build column headers
    headers = [
        "Record ID",
        "First Name",
        "Middle Name",
        "Last Name",
        "Birth Date",
        "Status",
        "Status Reason",
        "Created",
        "Last Updated",
    ]

    if include_consent:
        headers.extend([
            "Consent Given",
            "Consent Type",
            "Retention Expires",
            "Erasure Requested",
        ])

    if include_enrolments:
        headers.append("Programme Enrolments")

    if include_custom_fields:
        for field in custom_fields:
            headers.append(f"{field.group.title}: {field.name}")

    writer.writerow(sanitise_csv_row(headers))

    # Preload custom field values and enrolments for efficiency
    client_ids = [c.pk for c in clients]

    custom_values_by_client = {}
    if include_custom_fields:
        all_values = ClientDetailValue.objects.filter(
            client_file_id__in=client_ids
        ).select_related("field_def")
        for cv in all_values:
            if cv.client_file_id not in custom_values_by_client:
                custom_values_by_client[cv.client_file_id] = {}
            custom_values_by_client[cv.client_file_id][cv.field_def_id] = cv.get_value()

    enrolments_by_client = {}
    if include_enrolments:
        all_enrolments = ClientProgramEnrolment.objects.filter(
            client_file_id__in=client_ids
        ).select_related("program")
        for enrol in all_enrolments:
            if enrol.client_file_id not in enrolments_by_client:
                enrolments_by_client[enrol.client_file_id] = []
            status_label = "Active" if enrol.status == "enrolled" else "Unenrolled"
            enrolments_by_client[enrol.client_file_id].append(
                f"{enrol.program.name} ({status_label})"
            )

    # Write data rows — sanitise all values to prevent CSV injection
    for client in clients:
        row = [
            client.record_id,
            client.first_name,
            client.middle_name or "",
            client.last_name,
            client.birth_date or "",
            client.status,
            client.status_reason or "",
            client.created_at.strftime("%Y-%m-%d %H:%M") if client.created_at else "",
            client.updated_at.strftime("%Y-%m-%d %H:%M") if client.updated_at else "",
        ]

        if include_consent:
            row.extend([
                client.consent_given_at.strftime("%Y-%m-%d %H:%M") if client.consent_given_at else "",
                client.consent_type or "",
                str(client.retention_expires) if client.retention_expires else "",
                "Yes" if client.erasure_requested else "No",
            ])

        if include_enrolments:
            enrolment_list = enrolments_by_client.get(client.pk, [])
            row.append("; ".join(enrolment_list))

        if include_custom_fields:
            client_values = custom_values_by_client.get(client.pk, {})
            for field in custom_fields:
                row.append(client_values.get(field.pk, ""))

        writer.writerow(sanitise_csv_row(row))

    # Save to file and create secure download link
    recipient = form.get_recipient_display()
    link = _save_export_and_create_link(
        request=request,
        content=csv_buffer.getvalue(),
        filename=filename,
        export_type="client_data",
        client_count=len(clients),
        includes_notes=False,
        recipient=recipient,
        filters_dict={
            "program_filter": program.name if program else None,
            "status_filter": status_filter or None,
            "include_custom_fields": include_custom_fields,
            "include_enrolments": include_enrolments,
            "include_consent": include_consent,
        },
    )

    # Audit log with recipient tracking
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="client_data",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "total_clients": len(clients),
            "program_filter": program.name if program else None,
            "status_filter": status_filter or None,
            "include_custom_fields": include_custom_fields,
            "include_enrolments": include_enrolments,
            "include_consent": include_consent,
            "recipient": recipient,
            "secure_link_id": str(link.id),
        },
    )

    download_url = request.build_absolute_uri(
        reverse("reports:download_export", args=[link.id])
    )
    return render(request, "reports/export_link_created.html", {
        "link": link,
        "download_url": download_url,
    })


# ─── Secure link views ──────────────────────────────────────────────


@login_required
def download_export(request, link_id):
    """
    Serve an export file if the secure link is still valid.

    The export creator can download their own link. Admins can download
    any link (for oversight and client_data_export which only admin creates).
    Every download is logged with who actually downloaded the file.
    """
    link = get_object_or_404(SecureExportLink, id=link_id)

    # Permission: creator can download their own export, admin can download any
    can_download = (request.user == link.created_by) or request.user.is_admin
    if not can_download:
        return HttpResponseForbidden("You do not have permission to download this export.")

    # Check link validity (revoked / expired)
    if not link.is_valid():
        reason = "revoked" if link.revoked else "expired"
        return render(request, "reports/export_link_expired.html", {
            "reason": reason,
        })

    # Elevated exports have a delay before download is available
    if link.is_elevated and not link.is_available:
        return render(request, "reports/export_link_pending.html", {
            "link": link,
            "available_at": link.available_at,
        })

    # Check file exists separately (Railway ephemeral storage may lose files)
    if not link.file_exists:
        return render(request, "reports/export_link_expired.html", {
            "reason": "missing",
        })

    # Path traversal defence — verify file is within SECURE_EXPORT_DIR
    real_path = os.path.realpath(link.file_path)
    real_export_dir = os.path.realpath(settings.SECURE_EXPORT_DIR)
    if not real_path.startswith(real_export_dir + os.sep):
        return HttpResponseForbidden("Invalid file path.")

    # Atomic update to prevent race condition on download_count
    updated = SecureExportLink.objects.filter(pk=link.pk).update(
        download_count=F("download_count") + 1,
        last_downloaded_at=timezone.now(),
        last_downloaded_by=request.user,
    )

    # Audit log the download (separate from creation audit)
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="export_download",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "link_id": str(link.id),
            "created_by": link.created_by.display_name,
            "export_type": link.export_type,
            "client_count": link.client_count,
        },
    )

    # Serve file — FileResponse handles proper streaming and cleanup
    response = FileResponse(
        open(link.file_path, "rb"),
        as_attachment=True,
        filename=link.filename,
    )
    return response


@login_required
@admin_required
def manage_export_links(request):
    """
    Admin view: list all active and recent secure export links.

    Shows link status, download counts, and revocation controls.
    """

    # Show active links + recently expired (last 7 days)
    cutoff = timezone.now() - timedelta(days=7)
    links = SecureExportLink.objects.filter(
        created_at__gte=cutoff,
    ).select_related("created_by", "last_downloaded_by", "revoked_by")

    # Identify pending elevated exports (still in delay window, not revoked/expired)
    pending_elevated = [
        link for link in links
        if link.is_elevated and not link.revoked
        and not link.is_available
        and link.is_valid()
    ]

    return render(request, "reports/manage_export_links.html", {
        "links": links,
        "pending_elevated": pending_elevated,
    })


@login_required
@admin_required
def revoke_export_link(request, link_id):
    """
    Admin action: revoke a secure export link so it can no longer be downloaded.

    POST only. Uses Post/Redirect/Get to avoid resubmit-on-refresh.
    After revocation, the file is also deleted from disk.
    """
    from django.contrib import messages
    from django.http import HttpResponseNotAllowed
    from django.shortcuts import redirect
    from django.utils.translation import gettext as _

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    link = get_object_or_404(SecureExportLink, id=link_id)

    if link.revoked:
        messages.info(request, _("This link was already revoked."))
        return redirect("reports:manage_export_links")

    # Revoke the link
    link.revoked = True
    link.revoked_by = request.user
    link.revoked_at = timezone.now()
    link.save(update_fields=["revoked", "revoked_by", "revoked_at"])

    # Delete the file from disk
    if link.file_path and os.path.exists(link.file_path):
        try:
            os.remove(link.file_path)
        except OSError:
            pass  # File gone is acceptable — link is already revoked

    # Audit log the revocation
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="update",
        resource_type="export_link_revoked",
        ip_address=_get_client_ip(request),
        is_demo_context=getattr(request.user, "is_demo", False),
        metadata={
            "link_id": str(link.id),
            "created_by": link.created_by.display_name,
            "export_type": link.export_type,
            "client_count": link.client_count,
        },
    )

    messages.success(request, _("Export link revoked successfully."))
    return redirect("reports:manage_export_links")
