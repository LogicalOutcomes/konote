"""Format and suppress funder report data for consortium publishing.

Applies cell suppression before data leaves the agency:
- Standard threshold: counts < 5 are suppressed
- Sensitive fields: counts < 10 are suppressed
  (Indigenous Identity, 2SLGBTQIA+ Identity, Disability, Transgender Experience)

All data is de-identified aggregate counts — no individual participant records.
"""

# Fields where small-cell suppression threshold is 10 instead of 5
SENSITIVE_FIELDS = frozenset({
    "Indigenous Identity",
    "2SLGBTQIA+ Identity",
    "Disability",
    "Transgender Experience",
})

DEFAULT_THRESHOLD = 5
SENSITIVE_THRESHOLD = 10


def suppress_value(count, field_name=""):
    """Return the count if above threshold, or a suppressed marker string."""
    threshold = (
        SENSITIVE_THRESHOLD if field_name in SENSITIVE_FIELDS
        else DEFAULT_THRESHOLD
    )
    if isinstance(count, (int, float)) and count < threshold and count > 0:
        return f"< {threshold}"
    return count


def format_published_data(report_data, report_template=None):
    """Format funder report data for consortium publishing.

    Takes the raw report_data dict (from generate_funder_report_data) and
    returns a cleaned, suppressed version suitable for PublishedReport.data_json.

    Args:
        report_data: dict from generate_funder_report_data()
        report_template: optional ReportTemplate for suppression_threshold override

    Returns:
        dict with structure:
        {
            "service_stats": {"total_clients": N, "total_sessions": N, ...},
            "demographics": {
                "age_groups": [{"label": "18-24", "count": N}, ...],
                "gender_identity": [{"label": "Woman", "count": N}, ...],
                ...
            },
            "outcomes": {
                "cfpb_change": {"average": N, "n": N},
                ...
            },
        }
    """
    base_threshold = DEFAULT_THRESHOLD
    if report_template and hasattr(report_template, "suppression_threshold"):
        base_threshold = report_template.suppression_threshold or DEFAULT_THRESHOLD

    published = {
        "service_stats": _format_service_stats(report_data),
        "demographics": _format_demographics(report_data, base_threshold),
        "outcomes": _format_outcomes(report_data),
    }
    return published


def _format_service_stats(report_data):
    """Extract service statistics (no suppression needed — totals only)."""
    stats = report_data.get("service_stats", {})
    return {
        "total_clients": stats.get("total_clients", 0),
        "total_sessions": stats.get("total_sessions", 0),
        "new_clients": stats.get("new_clients", 0),
        "returning_clients": stats.get("returning_clients", 0),
    }


def _format_demographics(report_data, base_threshold):
    """Format demographic breakdowns with cell suppression."""
    demographics = {}

    # Age groups
    age_data = report_data.get("age_demographics", [])
    demographics["age_groups"] = [
        {
            "label": row.get("label", ""),
            "count": suppress_value(row.get("count", 0)),
        }
        for row in age_data
    ]

    # Custom demographic sections (Gender Identity, Racial Identity, etc.)
    for section in report_data.get("custom_demographic_sections", []):
        field_name = section.get("field_name", "")
        key = field_name.lower().replace(" ", "_")
        demographics[key] = [
            {
                "label": row.get("label", ""),
                "count": suppress_value(row.get("count", 0), field_name),
            }
            for row in section.get("rows", [])
        ]

    return demographics


def _format_outcomes(report_data):
    """Format outcome metrics (averages, not counts — no suppression)."""
    outcomes = {}
    for metric in report_data.get("primary_outcomes", []):
        key = metric.get("name", "").lower().replace(" ", "_")
        outcomes[key] = {
            "average": metric.get("average"),
            "change": metric.get("change"),
            "n": metric.get("n", 0),
        }
    return outcomes
