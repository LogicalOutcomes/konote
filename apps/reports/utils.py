"""Utility functions for the reports app — fiscal year calculations and permissions."""
import calendar
from datetime import date
from typing import List, Tuple

from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _


def is_aggregate_only_user(user):
    """Check if this user should only receive aggregate (non-individual) export data.

    Only program managers can access individual client data in report
    exports (with friction — elevated delay + admin notification).
    Admins without PM roles, executives, and all other roles receive
    aggregate summaries only — no record IDs, no author names, no
    per-client rows.

    The admin role is for system configuration (metrics, templates,
    settings) — not for routine access to client data. An admin who
    also holds a PM role gets individual access via the PM role.

    This is a PHIPA/privacy safeguard: report downloads are high-risk
    because files leave the system. Individual data access for clinical
    purposes is handled separately by per-client views with RBAC.

    Returns:
        True if user should only see aggregate data in exports.
    """
    from apps.programs.models import UserProgramRole

    has_pm_role = UserProgramRole.objects.filter(
        user=user, role="program_manager", status="active"
    ).exists()
    return not has_pm_role


def can_download_pii_export(user):
    """Check if this user can download exports containing individual client data.

    Used as defense-in-depth at download time. Admins retain download
    ability for oversight (they manage/revoke export links and may need
    to verify contents). Program managers can download their own PII
    exports.

    Returns:
        True if the user can download PII-containing exports.
    """
    if user.is_admin:
        return True

    from apps.programs.models import UserProgramRole

    return UserProgramRole.objects.filter(
        user=user, role="program_manager", status="active"
    ).exists()


def can_create_export(user, export_type, program=None):
    """
    Check if a user can create an export of the given type.

    Permission rules:
    - metrics / funder_report: admin (any program), program_manager or executive (their programs)
    - All other roles (staff, front desk): no export access

    Args:
        user: The User instance.
        export_type: One of "metrics", "funder_report".
        program: Optional Program instance — when provided, checks whether
                 the user manages that specific program.

    Returns:
        True if the user is allowed to create the export, False otherwise.
    """
    from apps.programs.models import UserProgramRole

    if user.is_admin:
        return True

    if export_type in ("metrics", "funder_report", "session_report"):
        qs = UserProgramRole.objects.filter(
            user=user, role__in=["program_manager", "executive"], status="active"
        )
        if program:
            return qs.filter(program=program).exists()
        return qs.exists()

    return False


def get_manageable_programs(user):
    """
    Return programs the user can export from.

    Admins see all active programs. Program managers and executives
    see the programs they are assigned to.

    Returns:
        QuerySet of Program objects.
    """
    from apps.programs.models import Program, UserProgramRole

    if user.is_admin:
        return Program.objects.filter(status="active")

    managed_ids = UserProgramRole.objects.filter(
        user=user, role__in=["program_manager", "executive"], status="active"
    ).values_list("program_id", flat=True)
    return Program.objects.filter(pk__in=managed_ids, status="active")


def get_fiscal_year_range(year: int) -> Tuple[date, date]:
    """
    Return the date range for a Canadian fiscal year.

    Canadian nonprofits typically use April 1 to March 31 fiscal years.
    For example, FY 2025-26 runs from April 1, 2025 to March 31, 2026.

    Args:
        year: The starting year of the fiscal year (e.g., 2025 for FY 2025-26)

    Returns:
        Tuple of (date_from, date_to) representing the fiscal year bounds
    """
    date_from = date(year, 4, 1)  # April 1 of starting year
    date_to = date(year + 1, 3, 31)  # March 31 of following year
    return (date_from, date_to)


def get_current_fiscal_year() -> int:
    """
    Return the starting year of the current fiscal year based on today's date.

    If today is between January and March, we're still in the previous
    calendar year's fiscal year. Otherwise, we're in the current calendar
    year's fiscal year.

    Returns:
        The starting year of the current fiscal year (e.g., 2025 for FY 2025-26)
    """
    today = date.today()
    # If we're in January-March, fiscal year started the previous calendar year
    if today.month < 4:
        return today.year - 1
    return today.year


def get_fiscal_year_choices(num_years: int = 5) -> List[Tuple[str, str]]:
    """
    Return a list of fiscal year choices for a dropdown field.

    Generates choices for the current fiscal year plus previous years,
    going back the specified number of years.

    Args:
        num_years: Number of fiscal years to include (default 5)

    Returns:
        List of tuples (value, label) for use in a Django ChoiceField.
        The value is the starting year as a string (e.g., "2025").
        The label is formatted as "FY 2025-26".
    """
    current_fy = get_current_fiscal_year()
    choices = []
    for i in range(num_years):
        fy_start = current_fy - i
        fy_end_short = str(fy_start + 1)[-2:]  # Last two digits of end year
        # Translators: FY = Fiscal Year, e.g. "FY 2025-26" / "AF 2025-26"
        label = _("FY %(start)s-%(end)s") % {"start": fy_start, "end": fy_end_short}
        choices.append((str(fy_start), label))
    return choices


# Quarter boundaries within a Canadian fiscal year (April start):
#   Q1 = Apr–Jun,  Q2 = Jul–Sep,  Q3 = Oct–Dec,  Q4 = Jan–Mar
# Keep in sync with qStarts in templates/reports/export_form.html
_QUARTER_STARTS = {
    1: (0, 4),   # same calendar year, April
    2: (0, 7),   # same calendar year, July
    3: (0, 10),  # same calendar year, October
    4: (1, 1),   # next calendar year, January
}


def get_quarter_range(quarter: int, fy_start_year: int) -> Tuple[date, date]:
    """
    Return the date range for a fiscal quarter.

    Args:
        quarter: 1-4 (Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar)
        fy_start_year: The starting year of the fiscal year (e.g. 2025 for FY 2025-26)
    """
    year_offset, month = _QUARTER_STARTS[quarter]
    year = fy_start_year + year_offset
    date_from = date(year, month, 1)
    end_month = month + 2
    end_year = year
    if end_month > 12:
        end_month -= 12
        end_year += 1
    last_day = calendar.monthrange(end_year, end_month)[1]
    date_to = date(end_year, end_month, last_day)
    return (date_from, date_to)


def get_quarter_choices(num_quarters: int = 8) -> List[Tuple[str, str]]:
    """
    Return quarterly choices working backwards from the current quarter.

    Values are formatted as "Q{n}-{fy_start_year}" (e.g. "Q1-2025").
    Labels include month abbreviations for clarity.
    """
    today = date.today()
    current_fy = get_current_fiscal_year()

    # Which fiscal quarter are we in?
    fiscal_month = (today.month - 4) % 12 + 1  # Apr=1 … Mar=12
    current_q = (fiscal_month - 1) // 3 + 1    # 1-4

    choices = []
    fy = current_fy
    q = current_q

    for _i in range(num_quarters):
        fy_end_short = str(fy + 1)[-2:]
        q_from, q_to = get_quarter_range(q, fy)
        m_start = date_format(q_from, "M")
        m_end = date_format(q_to, "M")
        # Translators: e.g. "Q1 FY 2025-26 (Apr–Jun)"
        label = _("Q%(q)s FY %(start)s-%(end)s (%(m1)s\u2013%(m2)s)") % {
            "q": q, "start": fy, "end": fy_end_short,
            "m1": m_start, "m2": m_end,
        }
        choices.append((f"Q{q}-{fy}", label))

        q -= 1
        if q < 1:
            q = 4
            fy -= 1

    return choices
