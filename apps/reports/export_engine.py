"""Template-driven report generation engine.

Orchestrates data collection and output formatting for template-driven
reports.  Delegates to generate_funder_report_data() for the heavy
lifting and applies suppression / formatting on top.

Separation from funder_report.py ensures the template pipeline cannot
accidentally fall back to flat ad-hoc output.

See tasks/design-rationale/reporting-architecture.md for the full spec.
"""
import csv
import io
import logging

from .csv_utils import sanitise_csv_row, sanitise_filename
from .funder_report import generate_funder_report_data, generate_funder_report_csv_rows
from .suppression import suppress_small_cell

logger = logging.getLogger(__name__)


def generate_template_report(template, date_from, date_to, period_label,
                             user, export_format, request):
    """
    Generate a template-driven report.

    Args:
        template: ReportTemplate instance (defines programs, metrics,
                  demographics, aggregation rules via Partner).
        date_from: Start of reporting period (date).
        date_to: End of reporting period (date).
        period_label: Human-readable period (e.g. "Q3 FY2025-26").
        user: Requesting user (for demo/real client filtering).
        export_format: "csv" or "pdf".
        request: HttpRequest (needed by PDF renderer).

    Returns:
        Tuple of (content, filename, client_count):
        - content: str (CSV) or bytes (PDF)
        - filename: suggested download filename
        - client_count: raw integer count for SecureExportLink
    """
    programs = list(template.partner.get_programs())
    total_client_count = 0

    # Generate data per program.  For multi-program partners the funder
    # report is currently rendered for the first program — full multi-
    # program aggregation is deferred to DRR step 6.
    all_report_data = []
    for program in programs:
        report_data = generate_funder_report_data(
            program,
            date_from=date_from,
            date_to=date_to,
            fiscal_year_label=period_label,
            user=user,
            report_template=template,
        )

        raw_count = report_data.get("total_individuals_served", 0)
        if isinstance(raw_count, int):
            total_client_count += raw_count

        # Apply small-cell suppression (same logic as funder_report_form view)
        report_data["total_individuals_served"] = suppress_small_cell(
            report_data["total_individuals_served"], program,
        )
        report_data["new_clients_this_period"] = suppress_small_cell(
            report_data["new_clients_this_period"], program,
        )
        if program.is_confidential and "age_demographics" in report_data:
            for age_group, count in report_data["age_demographics"].items():
                if isinstance(count, int):
                    report_data["age_demographics"][age_group] = suppress_small_cell(
                        count, program
                    )
        if program.is_confidential and "custom_demographic_sections" in report_data:
            for section in report_data["custom_demographic_sections"]:
                any_suppressed = False
                for cat_label, count in section["data"].items():
                    if isinstance(count, int):
                        suppressed = suppress_small_cell(count, program)
                        if suppressed != count:
                            any_suppressed = True
                        section["data"][cat_label] = suppressed
                if any_suppressed:
                    section["total"] = "suppressed"

        all_report_data.append((program, report_data))

    # Format output — use the first program's report data for now.
    # Multi-program merge deferred to DRR step 6.
    _program, report_data = all_report_data[0]

    safe_partner = sanitise_filename(template.partner.name.replace(" ", "_"))
    safe_period = sanitise_filename(period_label.replace(" ", "_"))

    if export_format == "pdf":
        from .pdf_views import generate_funder_report_pdf
        pdf_response = generate_funder_report_pdf(request, report_data)
        filename = f"Report_{safe_partner}_{safe_period}.pdf"
        content = pdf_response.content
    else:
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        csv_rows = generate_funder_report_csv_rows(report_data)
        for row in csv_rows:
            writer.writerow(sanitise_csv_row(row))
        filename = f"Report_{safe_partner}_{safe_period}.csv"
        content = csv_buffer.getvalue()

    return content, filename, total_client_count
