# English (Canadian) date and number formatting.
#
# Human-readable date formats for display; ISO 8601 kept for SHORT_*
# variants (used in machine/export contexts only).
# Reference: Government of Canada editorial style guide.

# Date formats — human-readable for display, ISO for machine contexts
DATE_FORMAT = "N j, Y"                  # "Feb. 10, 2026"
SHORT_DATE_FORMAT = "Y-m-d"             # 2026-02-05 (machine/export)
DATETIME_FORMAT = "N j, Y, P"           # "Feb. 10, 2026, 2:30 p.m."
SHORT_DATETIME_FORMAT = "Y-m-d H:i"    # 2026-02-05 14:30 (machine/export)
DATE_INPUT_FORMATS = [
    "%Y-%m-%d",     # 2026-02-05 (ISO 8601 — primary)
    "%m/%d/%Y",     # 02/05/2026 (US-style fallback)
    "%d/%m/%Y",     # 05/02/2026 (EU-style fallback)
]

# Number formatting — English Canadian style: $1,234.56
DECIMAL_SEPARATOR = "."
THOUSAND_SEPARATOR = ","
NUMBER_GROUPING = 3
