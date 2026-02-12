"""Demographic grouping utilities for report aggregation.

Provides functions to group clients by demographics:
- Age range (calculated from encrypted birth_date)
- Custom field values (from EAV system)

These functions work with encrypted data by loading records into Python
and filtering in memory. This approach is acceptable for up to ~2,000 clients.
"""
from collections import defaultdict
from datetime import date
from typing import Any

from django.db.models import QuerySet

from apps.clients.models import ClientDetailValue, ClientFile, CustomFieldDefinition
from apps.notes.models import MetricValue


# Age range buckets (standard demographic groupings)
AGE_RANGES = [
    (0, 17, "0-17"),
    (18, 24, "18-24"),
    (25, 34, "25-34"),
    (35, 44, "35-44"),
    (45, 54, "45-54"),
    (55, 64, "55-64"),
    (65, 999, "65+"),
]


def get_age_range(birth_date: date | str | None, as_of_date: date | None = None) -> str:
    """
    Calculate age range bucket from a birth date.

    Args:
        birth_date: Date of birth (as date object or string YYYY-MM-DD).
        as_of_date: Calculate age as of this date (default: today).

    Returns:
        Age range string (e.g., "25-34") or "Unknown" if birth_date is missing/invalid.
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

    # Find matching range
    for min_age, max_age, label in AGE_RANGES:
        if min_age <= age <= max_age:
            return label

    return "Unknown"


def group_clients_by_age(
    client_ids: list[int] | QuerySet,
    as_of_date: date | None = None,
    custom_bins: list[dict] | None = None,
) -> dict[str, list[int]]:
    """
    Group client IDs by their age range.

    Args:
        client_ids: List or queryset of client IDs to group.
        as_of_date: Calculate ages as of this date (default: today).
        custom_bins: Optional list of {"min": int, "max": int, "label": str}
                     dicts defining funder-specific age buckets.

    Returns:
        Dict mapping age range labels to lists of client IDs.
        Example: {"25-34": [1, 2], "35-44": [3], "Unknown": [4]}
    """
    groups: dict[str, list[int]] = defaultdict(list)

    # Convert queryset to list if needed
    if hasattr(client_ids, "values_list"):
        client_ids = list(client_ids)

    # Use custom bins if provided, otherwise default
    if custom_bins:
        bins = [(b["min"], b["max"], b["label"]) for b in custom_bins]
    else:
        bins = AGE_RANGES

    # Load clients — encrypted birth_date requires Python access
    clients = ClientFile.objects.filter(pk__in=client_ids)

    for client in clients:
        age_range = _find_age_bin(client.birth_date, as_of_date, bins)
        groups[age_range].append(client.pk)

    return dict(groups)


def _find_age_bin(
    birth_date: date | str | None,
    as_of_date: date | None,
    bins: list[tuple[int, int, str]],
) -> str:
    """Find the matching age bin label for a birth date."""
    if not birth_date:
        return "Unknown"

    if isinstance(birth_date, str):
        try:
            birth_date = date.fromisoformat(birth_date)
        except (ValueError, TypeError):
            return "Unknown"

    if as_of_date is None:
        as_of_date = date.today()

    age = as_of_date.year - birth_date.year
    if (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    for min_age, max_age, label in bins:
        if min_age <= age <= max_age:
            return label

    return "Unknown"


def group_clients_by_custom_field(
    client_ids: list[int] | QuerySet,
    field_definition: CustomFieldDefinition,
    merge_categories: dict[str, list[str]] | None = None,
) -> dict[str, list[int]]:
    """
    Group client IDs by values of a custom field.

    Args:
        client_ids: List or queryset of client IDs to group.
        field_definition: The CustomFieldDefinition to group by.
        merge_categories: Optional dict mapping target labels to lists of
                          source labels. E.g., {"Employed": ["Full-time", "Part-time"]}.
                          Values not in any merge group go to "Other".

    Returns:
        Dict mapping field values to lists of client IDs.
        For dropdown fields, uses option labels (not raw values).
        Clients without a value are grouped under "Unknown".
    """
    groups: dict[str, list[int]] = defaultdict(list)

    # Convert queryset to list if needed
    if hasattr(client_ids, "values_list"):
        client_ids = list(client_ids)

    # Build lookup for dropdown options (value -> label)
    option_labels = {}
    if field_definition.input_type == "select" and field_definition.options_json:
        for option in field_definition.options_json:
            if isinstance(option, dict):
                option_labels[option.get("value", "")] = option.get("label", option.get("value", ""))
            else:
                # Simple list of strings
                option_labels[option] = option

    # Get all values for this field for the given clients
    values = ClientDetailValue.objects.filter(
        client_file_id__in=client_ids,
        field_def=field_definition,
    ).select_related("field_def")

    # Track which clients have values
    clients_with_values = set()

    for cv in values:
        client_id = cv.client_file_id
        raw_value = cv.get_value()  # Handles decryption if sensitive

        if not raw_value:
            groups["Unknown"].append(client_id)
        else:
            # Use option label for dropdowns, raw value otherwise
            display_value = option_labels.get(raw_value, raw_value)
            groups[display_value].append(client_id)

        clients_with_values.add(client_id)

    # Add clients without any value for this field to "Unknown"
    for client_id in client_ids:
        if client_id not in clients_with_values:
            groups["Unknown"].append(client_id)

    raw_groups = dict(groups)

    # Apply category merging if provided
    if merge_categories:
        return _apply_category_merge(raw_groups, merge_categories)

    return raw_groups


def _apply_category_merge(
    raw_groups: dict[str, list[int]],
    merge_map: dict[str, list[str]],
) -> dict[str, list[int]]:
    """
    Merge raw grouping results into funder-defined categories.

    Args:
        raw_groups: Dict mapping raw labels to client ID lists.
        merge_map: Dict mapping target labels to lists of source labels.

    Returns:
        Dict with merged categories. Source labels consumed by the map
        are removed; unmatched labels go to "Other" unless "Unknown".
    """
    merged: dict[str, list[int]] = defaultdict(list)

    # Build reverse map: source_label -> target_label
    reverse_map: dict[str, str] = {}
    for target_label, source_labels in merge_map.items():
        for source in source_labels:
            reverse_map[source] = target_label

    for raw_label, ids in raw_groups.items():
        if raw_label == "Unknown":
            merged["Unknown"].extend(ids)
        elif raw_label in reverse_map:
            merged[reverse_map[raw_label]].extend(ids)
        else:
            merged["Other"].extend(ids)

    # Remove empty "Other" and "Unknown" groups
    result = {}
    for label, ids in merged.items():
        if ids:
            result[label] = ids

    return result


def aggregate_by_demographic(
    metric_values_qs: QuerySet[MetricValue],
    grouping_type: str,
    grouping_field: CustomFieldDefinition | None = None,
    as_of_date: date | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Aggregate metric values by demographic grouping.

    Args:
        metric_values_qs: QuerySet of MetricValue objects to aggregate.
        grouping_type: One of "age_range", "custom_field", or "none".
        grouping_field: Required if grouping_type is "custom_field".
        as_of_date: For age calculations, use this date (default: today).

    Returns:
        Dict mapping demographic group labels to stats dicts.
        Each stats dict contains: count, valid_count, avg, min, max, sum
        Also includes client_ids set for each group.
    """
    from .aggregations import _stats_from_list

    if grouping_type == "none" or not grouping_type:
        # No grouping — aggregate everything together
        stats = _stats_from_list(list(metric_values_qs))
        client_ids = set(
            mv.progress_note_target.progress_note.client_file_id
            for mv in metric_values_qs
        )
        stats["client_ids"] = client_ids
        return {"All": stats}

    # Get all unique client IDs from the metric values
    all_client_ids = set()
    client_metric_map: dict[int, list[MetricValue]] = defaultdict(list)

    for mv in metric_values_qs.select_related(
        "progress_note_target__progress_note__client_file"
    ):
        client_id = mv.progress_note_target.progress_note.client_file_id
        all_client_ids.add(client_id)
        client_metric_map[client_id].append(mv)

    # Group clients by demographic
    if grouping_type == "age_range":
        client_groups = group_clients_by_age(list(all_client_ids), as_of_date)
    elif grouping_type == "custom_field" and grouping_field:
        client_groups = group_clients_by_custom_field(list(all_client_ids), grouping_field)
    else:
        # Invalid grouping — return ungrouped
        stats = _stats_from_list(list(metric_values_qs))
        stats["client_ids"] = all_client_ids
        return {"All": stats}

    # Aggregate metric values for each demographic group
    results: dict[str, dict[str, Any]] = {}

    for group_label, client_ids in client_groups.items():
        # Collect all metric values for clients in this group
        group_values = []
        for client_id in client_ids:
            group_values.extend(client_metric_map.get(client_id, []))

        if group_values:
            stats = _stats_from_list(group_values)
        else:
            stats = {
                "count": 0,
                "valid_count": 0,
                "avg": None,
                "min": None,
                "max": None,
                "sum": None,
            }
        stats["client_ids"] = set(client_ids)
        results[group_label] = stats

    return results


def get_demographic_field_choices(program=None) -> list[tuple[str, str]]:
    """
    Get choices for the demographic grouping dropdown.

    Returns a curated list of fields safe for reporting — blocking PII,
    operational fields, and text fields that produce unique groups.

    If a program is confidential or has fewer than 50 enrolled clients,
    only "No grouping" is returned.

    Args:
        program: Optional Program instance to check confidentiality
                 and enrolment count.

    Returns:
        List of (value, label) tuples for form choices.
    """
    from apps.clients.models import ClientProgramEnrolment, CustomFieldDefinition

    choices = [
        ("", "No grouping"),
    ]

    # Confidential programs: no demographic grouping at all
    if program and getattr(program, "is_confidential", False):
        return choices

    # Small programs: grouping is unsafe (k-anonymity)
    if program:
        enrolled_count = ClientProgramEnrolment.objects.filter(
            program=program, status="enrolled",
        ).count()
        if enrolled_count < 50:
            return choices

    choices.append(("age_range", "Age Range"))

    # Groups whose fields should NEVER appear in reports
    BLOCKED_GROUPS = {
        "Contact Information",
        "Emergency Contact",
        "Accessibility & Accommodation",
        "Consent & Permissions",
        "Parent/Guardian Information",
        "Health & Safety",
        "Program Consents",
    }

    # Specific field names blocked regardless of group
    BLOCKED_FIELDS = {
        "Preferred Name",
        "Postal Code",
        "Referring Agency Name",
        "Primary Language Spoken at Home",
        "Goals or Desired Outcomes",
        "Primary Reason for Seeking Services",
        "Accommodation Needs",
        "Immigration/Citizenship Status",
    }

    # Only dropdown fields — text fields produce unique groups
    fields = CustomFieldDefinition.objects.filter(
        status="active",
        input_type="select",
        is_sensitive=False,
    ).exclude(
        group__title__in=BLOCKED_GROUPS,
    ).exclude(
        name__in=BLOCKED_FIELDS,
    ).select_related("group").order_by("group__sort_order", "sort_order")

    for field in fields:
        value = f"custom_{field.pk}"
        label = f"{field.group.title}: {field.name}"
        choices.append((value, label))

    return choices


def parse_grouping_choice(choice_value: str) -> tuple[str, CustomFieldDefinition | None]:
    """
    Parse a grouping dropdown choice value into type and field.

    Args:
        choice_value: Value from the form (e.g., "", "age_range", "custom_123")

    Returns:
        Tuple of (grouping_type, field_definition or None)
    """
    if not choice_value:
        return ("none", None)

    if choice_value == "age_range":
        return ("age_range", None)

    if choice_value.startswith("custom_"):
        try:
            field_id = int(choice_value.replace("custom_", ""))
            field = CustomFieldDefinition.objects.get(pk=field_id, status="active")
            return ("custom_field", field)
        except (ValueError, CustomFieldDefinition.DoesNotExist):
            return ("none", None)

    return ("none", None)
