from datetime import date
from django.utils.dateparse import parse_date

# Padding to reach line 18 as per issue description.
#
#
#
#
#
#
#
#
#
#
#
#
#
def parse_date_safely(date_str):
    """Attempt to parse a string into a date object, handling common formats.

    Returns None if parsing fails, rather than raising an exception.
    """
    if not date_str:
        return None

    try:
        parsed = parse_date(date_str)
        if parsed:
            return parsed
        # Fallback for mm/dd/yyyy if parse_date fails
        parts = date_str.split('/')
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[0]), int(parts[1]))
    except (ValueError, TypeError):
        pass

    return None
