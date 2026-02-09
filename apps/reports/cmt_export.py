"""Programme Outcome Report Template (CMT format) export functionality.

Generates standardised programme reports with common nonprofit reporting fields:
- Organisation and programme information
- Reporting period (fiscal year)
- Service statistics (unique clients, total contacts)
- Demographic breakdowns (age groups, custom fields)
- Outcome achievement rates

IMPORTANT: This is a draft template. Organisations should verify this format
matches their specific reporting requirements before submission. Different
recipients (United Way chapters, government agencies, foundations) may require
different formats, fields, or calculations.

Canadian spelling conventions used throughout (programme, organisation, colour).
"""
from datetime import date
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.admin_settings.models import InstanceSetting
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import MetricValue, ProgressNote

from .achievements import get_achievement_summary
from .aggregations import count_clients_by_program, count_notes_by_program
from .demographics import get_age_range, group_clients_by_age
from .utils import get_fiscal_year_range


# CMT age group buckets (United Way standard categories)
CMT_AGE_GROUPS = [
    (0, 12, "Child (0-12)"),
    (13, 17, "Youth (13-17)"),
    (18, 24, "Young Adult (18-24)"),
    (25, 64, "Adult (25-64)"),
    (65, 999, "Senior (65+)"),
]


def get_cmt_age_group(birth_date: date | str | None, as_of_date: date | None = None) -> str:
    """
    Calculate CMT-specific age group from a birth date.

    Uses United Way's standard age categories which differ from our internal
    age ranges.

    Args:
        birth_date: Date of birth (as date object or string YYYY-MM-DD).
        as_of_date: Calculate age as of this date (default: today).

    Returns:
        CMT age group string (e.g., "Youth (13-17)") or "Unknown" if birth_date is missing.
    """
    if not birth_date:
        return "Unknown"

    # Handle string dates (from encrypted field)
    if isinstance(birth_date, str):
        try:
            birth_date = date.fromisoformat(birth_date)
        except (ValueError, TypeError):
            return "Unknown"

    if as_of_date is None:
        as_of_date = date.today()

    # Calculate age
    age = as_of_date.year - birth_date.year
    # Adjust if birthday hasn't occurred yet this year
    if (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    # Find matching CMT age group
    for min_age, max_age, label in CMT_AGE_GROUPS:
        if min_age <= age <= max_age:
            return label

    return "Unknown"


def group_clients_by_cmt_age(
    client_ids: list[int],
    as_of_date: date | None = None,
) -> dict[str, int]:
    """
    Group client IDs by CMT age categories and return counts.

    Args:
        client_ids: List of client IDs to group.
        as_of_date: Calculate ages as of this date (default: today).

    Returns:
        Dict mapping CMT age group labels to counts.
        Example: {"Child (0-12)": 5, "Youth (13-17)": 12, ...}
    """
    # Initialize with all CMT age groups
    counts = {label: 0 for _, _, label in CMT_AGE_GROUPS}
    counts["Unknown"] = 0

    if not client_ids:
        return counts

    # Load clients to access encrypted birth_date
    clients = ClientFile.objects.filter(pk__in=client_ids)

    for client in clients:
        age_group = get_cmt_age_group(client.birth_date, as_of_date)
        counts[age_group] = counts.get(age_group, 0) + 1

    return counts


def get_new_clients_count(
    program,
    date_from: date,
    date_to: date,
) -> int:
    """
    Count clients who were enrolled during the reporting period.

    A "new client" is defined as someone whose enrolment date falls within
    the reporting period.

    Args:
        program: The Programme object to filter by.
        date_from: Start of reporting period.
        date_to: End of reporting period.

    Returns:
        Count of new client enrolments in the period.
    """
    return ClientProgramEnrolment.objects.filter(
        program=program,
        status="enrolled",
        enrolled_at__date__gte=date_from,
        enrolled_at__date__lte=date_to,
    ).count()


def format_fiscal_year_label(start_year: int) -> str:
    """
    Format a fiscal year label for CMT reporting.

    Args:
        start_year: The starting year of the fiscal year (e.g., 2025).

    Returns:
        Formatted string like "FY 2025-26".
    """
    end_year_short = str(start_year + 1)[-2:]
    return f"FY {start_year}-{end_year_short}"


def format_number(value: int | float | None) -> str:
    """
    Format a number with thousand separators for readability.

    Args:
        value: Number to format.

    Returns:
        Formatted string with thousand separators (e.g., "1,234").
    """
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return f"{value:,}"


def generate_cmt_data(
    program,
    date_from: date,
    date_to: date,
    fiscal_year_label: str | None = None,
    user=None,
) -> dict[str, Any]:
    """
    Build the complete CMT data structure for a programme.

    This function aggregates all the data needed for a United Way CMT report:
    - Organisation and programme information
    - Service statistics
    - Demographic breakdowns
    - Outcome achievement rates

    Args:
        program: The Programme object to report on.
        date_from: Start of reporting period.
        date_to: End of reporting period.
        fiscal_year_label: Optional label like "FY 2025-26". If not provided,
                          will be calculated from date_from.
        user: Optional user for demo/real filtering. If provided, only clients
              matching the user's demo status will be included.

    Returns:
        Dict with CMT report data structure ready for rendering.
    """
    # Determine fiscal year label if not provided
    if not fiscal_year_label:
        # Infer from date_from (assumes April start)
        if date_from.month == 4 and date_from.day == 1:
            fiscal_year_label = format_fiscal_year_label(date_from.year)
        else:
            # Custom date range - show actual dates
            fiscal_year_label = f"{date_from} to {date_to}"

    # Get organisation name from instance settings
    organisation_name = InstanceSetting.get("organisation_name", "")
    if not organisation_name:
        organisation_name = InstanceSetting.get("agency_name", "Organisation Name")

    # Get enrolled client IDs for the programme
    enrolled_client_ids = list(
        ClientProgramEnrolment.objects.filter(
            program=program,
            status="enrolled",
        ).values_list("client_file_id", flat=True)
    )

    # Security: Filter by user's demo status if user is provided
    # Demo users can only see demo clients; real users only real clients
    if user is not None:
        if user.is_demo:
            accessible_ids = set(ClientFile.objects.demo().values_list("pk", flat=True))
        else:
            accessible_ids = set(ClientFile.objects.real().values_list("pk", flat=True))
        enrolled_client_ids = [cid for cid in enrolled_client_ids if cid in accessible_ids]

    # Count unique clients with activity in the period
    total_individuals_served = count_clients_by_program(
        program,
        date_from=date_from,
        date_to=date_to,
        active_only=True,
    )

    # Count new clients enrolled in the period
    new_clients = get_new_clients_count(program, date_from, date_to)

    # Count total progress notes (contacts) in the period
    total_contacts = count_notes_by_program(
        program,
        date_from=date_from,
        date_to=date_to,
    )

    # Get clients who had activity in the period for demographics
    # (use same logic as count_clients_by_program but get IDs)
    from datetime import datetime, time
    date_from_dt = timezone.make_aware(datetime.combine(date_from, time.min))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, time.max))

    active_client_ids = list(
        ProgressNote.objects.filter(
            client_file_id__in=enrolled_client_ids,
            status="default",
        ).filter(
            Q(backdate__range=(date_from_dt, date_to_dt))
            | Q(backdate__isnull=True, created_at__range=(date_from_dt, date_to_dt))
        ).values_list("client_file_id", flat=True).distinct()
    )

    # Age demographics using CMT categories
    age_demographics = group_clients_by_cmt_age(active_client_ids, date_to)

    # Get achievement summary for all metrics with data
    achievement_summary = get_achievement_summary(
        program,
        date_from=date_from,
        date_to=date_to,
        use_latest=True,
    )

    # Build primary outcome (first metric with a target, if any)
    primary_outcome = None
    secondary_outcomes = []

    for metric_data in achievement_summary.get("by_metric", []):
        if metric_data["has_target"]:
            outcome_data = {
                "name": metric_data["metric_name"],
                "target_value": metric_data["target_value"],
                "clients_measured": metric_data["total_clients"],
                "clients_achieved": metric_data["clients_met_target"],
                "achievement_rate": metric_data["achievement_rate"],
            }
            if primary_outcome is None:
                primary_outcome = outcome_data
            else:
                secondary_outcomes.append(outcome_data)

    return {
        # Report metadata
        "generated_at": timezone.now(),
        "reporting_period": fiscal_year_label,
        "date_from": date_from,
        "date_to": date_to,

        # Organisation information
        "organisation_name": organisation_name,
        "programme_name": program.name,
        "programme_description": program.description or "",

        # Service statistics
        "total_individuals_served": total_individuals_served,
        "new_clients_this_period": new_clients,
        "total_contacts": total_contacts,

        # Demographics
        "age_demographics": age_demographics,
        "age_demographics_total": sum(age_demographics.values()),

        # Outcomes
        "primary_outcome": primary_outcome,
        "secondary_outcomes": secondary_outcomes,
        "achievement_summary": achievement_summary,

        # Raw data for detailed views
        "active_client_count": len(active_client_ids),
        "enrolled_client_count": len(enrolled_client_ids),
    }


def generate_cmt_csv_rows(cmt_data: dict[str, Any]) -> list[list[str]]:
    """
    Generate CSV rows for CMT export.

    The CSV format follows a structured layout with header sections and data:
    - Organisation and programme info
    - Reporting period
    - Service statistics
    - Demographics
    - Outcome indicators

    Args:
        cmt_data: Dict returned by generate_cmt_data().

    Returns:
        List of rows, where each row is a list of cell values.
    """
    rows = []

    # Header section
    rows.append(["PROGRAMME OUTCOME REPORT TEMPLATE"])
    rows.append(["DRAFT — Verify this format matches reporting requirements before submission"])
    rows.append([f"Generated: {cmt_data['generated_at'].strftime('%Y-%m-%d %H:%M')}"])
    rows.append([])

    # Organisation information
    rows.append(["ORGANISATION INFORMATION"])
    rows.append(["Organisation Name", cmt_data["organisation_name"]])
    rows.append(["Programme/Service Name", cmt_data["programme_name"]])
    if cmt_data["programme_description"]:
        rows.append(["Programme Description", cmt_data["programme_description"]])
    rows.append(["Reporting Period", cmt_data["reporting_period"]])
    rows.append([])

    # Service statistics
    rows.append(["SERVICE STATISTICS"])
    rows.append(["Total Individuals Served", format_number(cmt_data["total_individuals_served"])])
    rows.append(["New Clients This Period", format_number(cmt_data["new_clients_this_period"])])
    rows.append(["Total Service Contacts", format_number(cmt_data["total_contacts"])])
    rows.append([])

    # Age demographics
    rows.append(["AGE DEMOGRAPHICS"])
    rows.append(["Age Group", "Count", "Percentage"])
    total_demo = cmt_data["age_demographics_total"]
    for age_group, count in cmt_data["age_demographics"].items():
        if total_demo > 0:
            pct = f"{(count / total_demo * 100):.1f}%"
        else:
            pct = "N/A"
        rows.append([age_group, format_number(count), pct])
    rows.append(["Total", format_number(total_demo), "100%"])
    rows.append([])

    # Outcome indicators
    rows.append(["OUTCOME INDICATORS"])

    if cmt_data["primary_outcome"]:
        rows.append(["PRIMARY OUTCOME"])
        po = cmt_data["primary_outcome"]
        rows.append(["Indicator Name", po["name"]])
        rows.append(["Target Value", format_number(po["target_value"])])
        rows.append(["Clients Measured", format_number(po["clients_measured"])])
        rows.append(["Clients Achieving Target", format_number(po["clients_achieved"])])
        rows.append(["Achievement Rate", f"{po['achievement_rate']}%"])
        rows.append([])

    if cmt_data["secondary_outcomes"]:
        rows.append(["SECONDARY OUTCOMES"])
        rows.append(["Indicator Name", "Target", "Measured", "Achieved", "Rate"])
        for so in cmt_data["secondary_outcomes"]:
            rows.append([
                so["name"],
                format_number(so["target_value"]),
                format_number(so["clients_measured"]),
                format_number(so["clients_achieved"]),
                f"{so['achievement_rate']}%",
            ])
        rows.append([])

    if not cmt_data["primary_outcome"] and not cmt_data["secondary_outcomes"]:
        rows.append(["No outcome indicators with targets defined for this programme."])
        rows.append([])

    # Overall summary
    summary = cmt_data["achievement_summary"]
    if summary["total_clients"] > 0:
        rows.append(["OVERALL SUMMARY"])
        rows.append(["Total Clients with Outcome Data", format_number(summary["total_clients"])])
        rows.append(["Clients Meeting Any Target", format_number(summary["clients_met_any_target"])])
        rows.append(["Overall Achievement Rate", f"{summary['overall_rate']}%"])

    return rows
