"""CSV and filename sanitisation utilities for export views.

CSV injection (aka formula injection) occurs when a cell value starts with
characters that spreadsheet applications interpret as formulas: = + - @
An attacker could inject malicious payloads via client names, notes, or
custom field values.

Mitigation: prefix dangerous values with a tab character so Excel/LibreOffice
treat them as plain text rather than formulas.

Filename sanitisation strips characters that could be used for path traversal
or header injection in Content-Disposition headers.
"""
import re


# Characters that trigger formula execution in spreadsheet applications
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitise_csv_value(value):
    """Sanitise a single value for safe inclusion in a CSV cell.

    If the string representation starts with =, +, -, or @, prefix it with
    a tab character so spreadsheet applications treat it as text.

    Args:
        value: Any value destined for a CSV cell (str, int, float, None, etc.)

    Returns:
        The sanitised value. Non-string values pass through unchanged.
    """
    if value is None:
        return value
    # Only sanitise strings — numbers, dates, booleans are safe
    if not isinstance(value, str):
        return value
    if value and value[0] in _FORMULA_PREFIXES:
        return "\t" + value
    return value


def sanitise_csv_row(row):
    """Sanitise all values in a CSV row (list of values).

    Args:
        row: List of cell values.

    Returns:
        New list with each value sanitised.
    """
    return [sanitise_csv_value(v) for v in row]


def sanitise_filename(raw_name):
    """Sanitise a string for safe use in Content-Disposition filenames.

    Strips anything that is not alphanumeric, hyphen, underscore, or period.
    This prevents path traversal (../) and header injection attacks.

    Args:
        raw_name: The raw string to use in a filename (e.g. a record_id or
                  program name).

    Returns:
        A sanitised string containing only [A-Za-z0-9_.-] characters.
        Returns 'export' if the result would be empty.
    """
    if not raw_name:
        return "export"
    # Keep only safe characters
    cleaned = re.sub(r"[^A-Za-z0-9_.\-]", "", str(raw_name))
    return cleaned or "export"
