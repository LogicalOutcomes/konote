"""CSV parser for funder profile uploads.

Parses a structured CSV file into a FunderProfile with DemographicBreakdowns.

CSV format (each row starts with a type prefix):
    profile_name,United Way Greater Toronto
    profile_description,Annual Community Impact Report

    breakdown,Age Group,age,,
    bin,Age Group,0,14,Child (0-14)
    bin,Age Group,15,29,Youth (15-29)

    breakdown,Employment Status,custom_field,Employment Status,
    merge,Employment Status,Employed,"Employed full-time,Employed part-time,Self-employed"
    merge,Employment Status,Unemployed,"Unemployed - looking for work,Unemployed - not looking"

    breakdown,Gender Identity,custom_field,Gender Identity,
    keep_all,Gender Identity

Row types:
    profile_name      — Profile name (required, exactly once)
    profile_description — Description (optional)
    breakdown         — Declares a demographic dimension
    bin               — Age range bin within a breakdown
    merge             — Category merge within a breakdown
    keep_all          — Use original field categories as-is
"""
import csv
import io
from dataclasses import dataclass, field


@dataclass
class ParsedBreakdown:
    """Intermediate representation of a single demographic breakdown."""
    label: str
    source_type: str                     # "age" or "custom_field"
    source_field_name: str = ""          # Name of the CustomFieldDefinition
    bins: list[dict] = field(default_factory=list)     # [{"min": int, "max": int, "label": str}]
    merge_map: dict[str, list[str]] = field(default_factory=dict)  # {target: [sources]}
    keep_all: bool = False


@dataclass
class ParsedProfile:
    """Intermediate representation of a complete funder profile."""
    name: str = ""
    description: str = ""
    breakdowns: list[ParsedBreakdown] = field(default_factory=list)
    raw_csv: str = ""


def parse_funder_profile_csv(csv_content: str) -> tuple[ParsedProfile | None, list[str]]:
    """
    Parse a funder profile CSV string into a ParsedProfile.

    Args:
        csv_content: The raw CSV text content.

    Returns:
        Tuple of (ParsedProfile or None, list of error messages).
        If errors is non-empty, the profile may be incomplete.
    """
    errors: list[str] = []
    profile = ParsedProfile(raw_csv=csv_content)

    # Parse CSV rows
    reader = csv.reader(io.StringIO(csv_content))
    breakdowns_by_label: dict[str, ParsedBreakdown] = {}
    line_num = 0

    for row in reader:
        line_num += 1

        # Skip empty rows and comments
        if not row or not row[0].strip() or row[0].strip().startswith("#"):
            continue

        row_type = row[0].strip().lower()
        cells = [c.strip() for c in row]

        try:
            if row_type == "profile_name":
                if len(cells) < 2 or not cells[1]:
                    errors.append(f"Line {line_num}: profile_name requires a value.")
                else:
                    profile.name = cells[1]

            elif row_type == "profile_description":
                if len(cells) >= 2:
                    profile.description = cells[1]

            elif row_type == "breakdown":
                _parse_breakdown_row(cells, line_num, breakdowns_by_label, errors)

            elif row_type == "bin":
                _parse_bin_row(cells, line_num, breakdowns_by_label, errors)

            elif row_type == "merge":
                _parse_merge_row(cells, line_num, breakdowns_by_label, errors)

            elif row_type == "keep_all":
                _parse_keep_all_row(cells, line_num, breakdowns_by_label, errors)

            else:
                errors.append(
                    f"Line {line_num}: Unknown row type '{row_type}'. "
                    f"Expected: profile_name, profile_description, breakdown, bin, merge, keep_all."
                )

        except Exception as exc:
            errors.append(f"Line {line_num}: {exc}")

    # Validation
    if not profile.name:
        errors.append("Missing required profile_name row.")

    if not breakdowns_by_label:
        errors.append("No breakdown rows found. At least one breakdown is required.")

    # Validate each breakdown
    for label, bd in breakdowns_by_label.items():
        if bd.source_type == "age" and not bd.bins:
            errors.append(f"Breakdown '{label}': Age breakdown requires at least one bin row.")
        if bd.source_type == "custom_field" and not bd.source_field_name:
            errors.append(f"Breakdown '{label}': Custom field breakdown requires a field name.")
        if bd.source_type == "custom_field" and not bd.merge_map and not bd.keep_all:
            errors.append(
                f"Breakdown '{label}': Custom field breakdown needs either "
                f"merge rows or a keep_all row."
            )

    # Assign sort order and collect
    for i, bd in enumerate(breakdowns_by_label.values()):
        bd_copy = ParsedBreakdown(
            label=bd.label,
            source_type=bd.source_type,
            source_field_name=bd.source_field_name,
            bins=bd.bins,
            merge_map=bd.merge_map,
            keep_all=bd.keep_all,
        )
        profile.breakdowns.append(bd_copy)

    if errors:
        return None, errors

    return profile, []


def _parse_breakdown_row(
    cells: list[str],
    line_num: int,
    breakdowns: dict[str, ParsedBreakdown],
    errors: list[str],
) -> None:
    """Parse a 'breakdown' row: breakdown,Label,source_type,field_name,"""
    if len(cells) < 3:
        errors.append(f"Line {line_num}: breakdown row needs at least: breakdown,label,source_type")
        return

    label = cells[1]
    source_type = cells[2].lower()

    if not label:
        errors.append(f"Line {line_num}: breakdown label is empty.")
        return

    if source_type not in ("age", "custom_field"):
        errors.append(
            f"Line {line_num}: Invalid source type '{source_type}'. "
            f"Expected 'age' or 'custom_field'."
        )
        return

    if label in breakdowns:
        errors.append(f"Line {line_num}: Duplicate breakdown label '{label}'.")
        return

    field_name = cells[3] if len(cells) > 3 else ""

    breakdowns[label] = ParsedBreakdown(
        label=label,
        source_type=source_type,
        source_field_name=field_name,
    )


def _parse_bin_row(
    cells: list[str],
    line_num: int,
    breakdowns: dict[str, ParsedBreakdown],
    errors: list[str],
) -> None:
    """Parse a 'bin' row: bin,breakdown_label,min_age,max_age,display_label"""
    if len(cells) < 5:
        errors.append(f"Line {line_num}: bin row needs: bin,breakdown_label,min,max,label")
        return

    bd_label = cells[1]
    if bd_label not in breakdowns:
        errors.append(f"Line {line_num}: No breakdown named '{bd_label}' declared yet.")
        return

    bd = breakdowns[bd_label]
    if bd.source_type != "age":
        errors.append(f"Line {line_num}: bin rows are only valid for age breakdowns.")
        return

    try:
        min_age = int(cells[2])
        max_age = int(cells[3])
    except ValueError:
        errors.append(f"Line {line_num}: min and max age must be integers.")
        return

    bin_label = cells[4]
    if not bin_label:
        errors.append(f"Line {line_num}: bin label is empty.")
        return

    if min_age > max_age:
        errors.append(f"Line {line_num}: min age ({min_age}) > max age ({max_age}).")
        return

    bd.bins.append({"min": min_age, "max": max_age, "label": bin_label})


def _parse_merge_row(
    cells: list[str],
    line_num: int,
    breakdowns: dict[str, ParsedBreakdown],
    errors: list[str],
) -> None:
    """Parse a 'merge' row: merge,breakdown_label,target_label,"source1,source2,..." """
    if len(cells) < 4:
        errors.append(f"Line {line_num}: merge row needs: merge,breakdown_label,target,sources")
        return

    bd_label = cells[1]
    if bd_label not in breakdowns:
        errors.append(f"Line {line_num}: No breakdown named '{bd_label}' declared yet.")
        return

    bd = breakdowns[bd_label]
    if bd.source_type != "custom_field":
        errors.append(f"Line {line_num}: merge rows are only valid for custom_field breakdowns.")
        return

    target_label = cells[2]
    # Sources may be a single value or comma-separated within the cell
    source_str = cells[3]
    sources = [s.strip() for s in source_str.split(",") if s.strip()]

    if not target_label:
        errors.append(f"Line {line_num}: merge target label is empty.")
        return
    if not sources:
        errors.append(f"Line {line_num}: merge sources list is empty.")
        return

    if target_label in bd.merge_map:
        # Append to existing merge group
        bd.merge_map[target_label].extend(sources)
    else:
        bd.merge_map[target_label] = sources


def _parse_keep_all_row(
    cells: list[str],
    line_num: int,
    breakdowns: dict[str, ParsedBreakdown],
    errors: list[str],
) -> None:
    """Parse a 'keep_all' row: keep_all,breakdown_label"""
    if len(cells) < 2:
        errors.append(f"Line {line_num}: keep_all row needs: keep_all,breakdown_label")
        return

    bd_label = cells[1]
    if bd_label not in breakdowns:
        errors.append(f"Line {line_num}: No breakdown named '{bd_label}' declared yet.")
        return

    bd = breakdowns[bd_label]
    if bd.source_type != "custom_field":
        errors.append(f"Line {line_num}: keep_all is only valid for custom_field breakdowns.")
        return

    bd.keep_all = True


def save_parsed_profile(parsed: ParsedProfile, created_by) -> "FunderProfile":
    """
    Save a ParsedProfile to the database, creating FunderProfile and
    DemographicBreakdown objects.

    Args:
        parsed: A validated ParsedProfile from parse_funder_profile_csv().
        created_by: The User who uploaded the profile.

    Returns:
        The created FunderProfile instance.
    """
    from apps.clients.models import CustomFieldDefinition
    from .models import DemographicBreakdown, FunderProfile

    profile = FunderProfile.objects.create(
        name=parsed.name,
        description=parsed.description,
        source_csv=parsed.raw_csv,
        created_by=created_by,
    )

    for i, bd in enumerate(parsed.breakdowns):
        custom_field = None
        if bd.source_type == "custom_field" and bd.source_field_name:
            try:
                custom_field = CustomFieldDefinition.objects.get(
                    name=bd.source_field_name,
                    status="active",
                )
            except CustomFieldDefinition.DoesNotExist:
                # Will be caught during validation — store without FK
                pass
            except CustomFieldDefinition.MultipleObjectsReturned:
                # Take the first match
                custom_field = CustomFieldDefinition.objects.filter(
                    name=bd.source_field_name,
                    status="active",
                ).first()

        DemographicBreakdown.objects.create(
            funder_profile=profile,
            label=bd.label,
            source_type=bd.source_type,
            custom_field=custom_field,
            bins_json=bd.bins if bd.source_type == "age" else [],
            merge_categories_json=bd.merge_map if bd.merge_map else {},
            keep_all_categories=bd.keep_all,
            sort_order=i,
        )

    return profile


def validate_parsed_profile(parsed: ParsedProfile) -> list[str]:
    """
    Validate a ParsedProfile against the database — check that
    referenced custom fields exist and referenced option labels match.

    Args:
        parsed: A ParsedProfile from parse_funder_profile_csv().

    Returns:
        List of warning messages (non-fatal). Empty if everything matches.
    """
    from apps.clients.models import CustomFieldDefinition

    warnings: list[str] = []

    for bd in parsed.breakdowns:
        if bd.source_type != "custom_field":
            continue

        # Check field exists
        try:
            field_def = CustomFieldDefinition.objects.get(
                name=bd.source_field_name,
                status="active",
            )
        except CustomFieldDefinition.DoesNotExist:
            warnings.append(
                f"Breakdown '{bd.label}': Field '{bd.source_field_name}' not found "
                f"in active custom fields. The breakdown will be skipped in reports."
            )
            continue
        except CustomFieldDefinition.MultipleObjectsReturned:
            warnings.append(
                f"Breakdown '{bd.label}': Multiple fields named '{bd.source_field_name}' found. "
                f"The first match will be used."
            )
            field_def = CustomFieldDefinition.objects.filter(
                name=bd.source_field_name, status="active",
            ).first()

        # Check merge source labels match field options
        if bd.merge_map and field_def.input_type == "select" and field_def.options_json:
            known_labels = set()
            for opt in field_def.options_json:
                if isinstance(opt, dict):
                    known_labels.add(opt.get("label", opt.get("value", "")))
                    known_labels.add(opt.get("value", ""))
                else:
                    known_labels.add(opt)

            for target, sources in bd.merge_map.items():
                for source in sources:
                    if source not in known_labels:
                        warnings.append(
                            f"Breakdown '{bd.label}': Merge source '{source}' "
                            f"not found in field '{bd.source_field_name}' options. "
                            f"Clients with this value may appear in 'Other'."
                        )

    return warnings


def generate_sample_csv() -> str:
    """
    Generate a sample/template CSV that admins can download and customise.

    Returns:
        A string containing a valid sample CSV.
    """
    lines = [
        "# KoNote Funder Profile CSV Template",
        "# Lines starting with # are comments and will be ignored.",
        "#",
        "# INSTRUCTIONS:",
        "# 1. Replace the profile name and description below",
        "# 2. Define your age breakdowns (bins)",
        "# 3. Define custom field breakdowns (merge or keep_all)",
        "# 4. Upload this file in Admin → Funder Profiles",
        "#",
        "# TIP: Use Claude to generate this CSV from your funder's",
        "#       reporting template (PDF, Excel, or email).",
        "",
        "profile_name,Example Funder Name",
        "profile_description,Annual reporting requirements",
        "",
        "# Age breakdown — adjust ranges to match your funder's requirements",
        "breakdown,Age Group,age,,",
        "bin,Age Group,0,12,Child (0-12)",
        "bin,Age Group,13,17,Youth (13-17)",
        "bin,Age Group,18,24,Young Adult (18-24)",
        "bin,Age Group,25,64,Adult (25-64)",
        "bin,Age Group,65,999,Senior (65+)",
        "",
        "# Custom field breakdown — merge categories into funder's groupings",
        "# breakdown,Employment Status,custom_field,Employment Status,",
        '# merge,Employment Status,Employed,"Employed full-time,Employed part-time,Self-employed"',
        '# merge,Employment Status,Unemployed,"Unemployed - looking for work,Unemployed - not looking"',
        "# merge,Employment Status,Student,Student",
        '# merge,Employment Status,Other,"Retired,Not currently able to work"',
        "# merge,Employment Status,Prefer not to answer,Prefer not to answer",
        "",
        "# Or keep all original field categories unchanged:",
        "# breakdown,Gender Identity,custom_field,Gender Identity,",
        "# keep_all,Gender Identity",
    ]
    return "\n".join(lines) + "\n"
