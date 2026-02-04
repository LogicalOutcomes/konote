"""Report views — aggregate metric CSV export, CMT export, and client analysis charts."""
import csv
import json
from datetime import datetime, time

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import PlanTarget, PlanTargetMetric
from apps.programs.models import UserProgramRole
from .achievements import get_achievement_summary, format_achievement_summary
from .cmt_export import generate_cmt_data, generate_cmt_csv_rows
from .demographics import aggregate_by_demographic, get_age_range, parse_grouping_choice
from .forms import CMTExportForm, ClientDataExportForm, MetricExportForm


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
    """
    if not request.user.is_admin:
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method != "POST":
        form = MetricExportForm()
        return render(request, "reports/export_form.html", {"form": form})

    form = MetricExportForm(request.POST)
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

    # Find clients enrolled in the selected programme
    client_ids = ClientProgramEnrolment.objects.filter(
        program=program, status="enrolled",
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

    if export_format == "pdf":
        from .pdf_views import generate_funder_pdf
        return generate_funder_pdf(
            request, program, selected_metrics,
            date_from, date_to, rows, unique_clients,
            grouping_type=grouping_type,
            grouping_label=grouping_label,
            achievement_summary=achievement_summary,
        )

    # Build CSV response
    response = HttpResponse(content_type="text/csv")
    filename = f"metric_export_{program.name.replace(' ', '_')}_{date_from}_{date_to}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    # Summary header rows (prefixed with # so spreadsheet apps treat them as comments)
    writer.writerow([f"# Programme: {program.name}"])
    writer.writerow([f"# Date Range: {date_from} to {date_to}"])
    writer.writerow([f"# Total Clients: {len(unique_clients)}"])
    writer.writerow([f"# Total Data Points: {len(rows)}"])
    if grouping_type != "none":
        writer.writerow([f"# Grouped By: {grouping_label}"])

    # Achievement rate summary if requested
    if achievement_summary:
        writer.writerow([])  # blank separator
        writer.writerow(["# ===== ACHIEVEMENT RATE SUMMARY ====="])
        if achievement_summary["total_clients"] > 0:
            writer.writerow([
                f"# Overall: {achievement_summary['clients_met_any_target']} of "
                f"{achievement_summary['total_clients']} clients "
                f"({achievement_summary['overall_rate']}%) met at least one target"
            ])
        else:
            writer.writerow(["# No client data available for achievement calculation"])

        for metric in achievement_summary.get("by_metric", []):
            if metric["has_target"]:
                writer.writerow([
                    f"# {metric['metric_name']}: {metric['clients_met_target']} of "
                    f"{metric['total_clients']} clients ({metric['achievement_rate']}%) "
                    f"met target of {metric['target_value']}"
                ])
            else:
                writer.writerow([
                    f"# {metric['metric_name']}: {metric['total_clients']} clients "
                    "(no target defined)"
                ])

    writer.writerow([])  # blank separator

    # Column headers — include demographic column if grouping enabled
    if grouping_type != "none":
        writer.writerow([grouping_label, "Client Record ID", "Metric Name", "Value", "Date", "Author"])
    else:
        writer.writerow(["Client Record ID", "Metric Name", "Value", "Date", "Author"])

    for row in rows:
        if grouping_type != "none":
            writer.writerow([
                row.get("demographic_group", "Unknown"),
                row["record_id"],
                row["metric_name"],
                row["value"],
                row["date"],
                row["author"],
            ])
        else:
            writer.writerow([
                row["record_id"],
                row["metric_name"],
                row["value"],
                row["date"],
                row["author"],
            ])

    # Audit log
    audit_metadata = {
        "program": program.name,
        "metrics": [m.name for m in selected_metrics],
        "date_from": str(date_from),
        "date_to": str(date_to),
        "total_clients": len(unique_clients),
        "total_data_points": len(rows),
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
        metadata=audit_metadata,
    )

    return response


def _get_client_or_403(request, client_id):
    """Return client if user has access via program roles, otherwise None.

    Admins without program roles cannot access client data — consistent with
    the RBAC model where admin-only users manage system config, not client records.
    """
    client = get_object_or_404(ClientFile, pk=client_id)
    user = request.user
    user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )
    client_program_ids = set(
        ClientProgramEnrolment.objects.filter(client_file=client, status="enrolled")
        .values_list("program_id", flat=True)
    )
    if user_program_ids & client_program_ids:
        return client
    return None


@login_required
def client_analysis(request, client_id):
    """Show progress charts for a client's metric data."""
    client = _get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")

    # Get targets with metrics for this client
    targets = PlanTarget.objects.filter(
        client_file=client, status="default"
    ).prefetch_related("metrics")

    chart_data = []
    for target in targets:
        ptm_links = PlanTargetMetric.objects.filter(
            plan_target=target
        ).select_related("metric_def")

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
                })

    context = {
        "client": client,
        "chart_data": chart_data,
        "active_tab": "analysis",
        "user_role": getattr(request, "user_program_role", None),
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

    CMT reports are structured for United Way Canada's funder reporting
    requirements, including:
    - Organisation and programme information
    - Service statistics (individuals served, contacts)
    - Age demographics (CMT standard categories)
    - Outcome achievement rates
    """
    if not request.user.is_admin:
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method != "POST":
        form = CMTExportForm()
        return render(request, "reports/cmt_export_form.html", {"form": form})

    form = CMTExportForm(request.POST)
    if not form.is_valid():
        return render(request, "reports/cmt_export_form.html", {"form": form})

    program = form.cleaned_data["program"]
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    fiscal_year_label = form.cleaned_data["fiscal_year_label"]
    export_format = form.cleaned_data["format"]

    # Generate CMT data
    cmt_data = generate_cmt_data(
        program,
        date_from=date_from,
        date_to=date_to,
        fiscal_year_label=fiscal_year_label,
    )

    # Audit log
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="cmt_report",
        metadata={
            "program": program.name,
            "fiscal_year": fiscal_year_label,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "format": export_format,
            "total_individuals_served": cmt_data["total_individuals_served"],
        },
    )

    if export_format == "pdf":
        from .pdf_views import generate_cmt_pdf
        return generate_cmt_pdf(request, cmt_data)

    # Generate CSV response
    response = HttpResponse(content_type="text/csv")
    safe_name = program.name.replace(" ", "_").replace("/", "-")
    filename = f"CMT_Report_{safe_name}_{fiscal_year_label.replace(' ', '_')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    csv_rows = generate_cmt_csv_rows(cmt_data)
    for row in csv_rows:
        writer.writerow(row)

    return response


@login_required
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

    if not request.user.is_admin:
        return HttpResponseForbidden("You do not have permission to access this page.")

    if request.method != "POST":
        form = ClientDataExportForm()
        return render(request, "reports/client_data_export_form.html", {"form": form})

    form = ClientDataExportForm(request.POST)
    if not form.is_valid():
        return render(request, "reports/client_data_export_form.html", {"form": form})

    # Get filter options
    program = form.cleaned_data.get("program")
    status_filter = form.cleaned_data.get("status")
    include_custom_fields = form.cleaned_data.get("include_custom_fields", True)
    include_enrolments = form.cleaned_data.get("include_enrolments", True)
    include_consent = form.cleaned_data.get("include_consent", True)

    # Build base queryset
    clients_qs = ClientFile.objects.all()

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

    # Build CSV response
    response = HttpResponse(content_type="text/csv")
    export_date = timezone.now().strftime("%Y-%m-%d")
    filename = f"client_data_export_{export_date}.csv"
    if program:
        safe_name = program.name.replace(" ", "_").replace("/", "-")
        filename = f"client_data_export_{safe_name}_{export_date}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Summary header rows
    writer.writerow([f"# Client Data Export"])
    writer.writerow([f"# Export Date: {export_date}"])
    writer.writerow([f"# Total Clients: {len(clients)}"])
    if program:
        writer.writerow([f"# Programme Filter: {program.name}"])
    if status_filter:
        writer.writerow([f"# Status Filter: {status_filter}"])
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

    writer.writerow(headers)

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

    # Write data rows
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

        writer.writerow(row)

    # Audit log
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="export",
        resource_type="client_data",
        metadata={
            "total_clients": len(clients),
            "program_filter": program.name if program else None,
            "status_filter": status_filter or None,
            "include_custom_fields": include_custom_fields,
            "include_enrolments": include_enrolments,
            "include_consent": include_consent,
        },
    )

    return response
