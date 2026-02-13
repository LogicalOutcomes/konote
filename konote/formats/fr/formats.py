# French (Canadian) date and number formatting.
#
# Human-readable date formats for display; ISO 8601 kept for SHORT_*
# variants (used in machine/export contexts only).
# French Canadian uses comma as decimal separator and space as
# thousands separator: 1 234,56 $.
# Reference: Government of Canada editorial style guide (French).

# Date formats — human-readable for display, ISO for machine contexts
DATE_FORMAT = "j N Y"                   # "10 fév. 2026"
SHORT_DATE_FORMAT = "Y-m-d"             # 2026-02-05 (machine/export)
DATETIME_FORMAT = "j N Y, H\\hi"        # "10 fév. 2026, 14h30"
SHORT_DATETIME_FORMAT = "Y-m-d H:i"    # 2026-02-05 14:30 (machine/export)
DATE_INPUT_FORMATS = [
    "%Y-%m-%d",     # 2026-02-05 (ISO 8601 — primary)
    "%d/%m/%Y",     # 05/02/2026 (EU-style — common in Quebec)
    "%m/%d/%Y",     # 02/05/2026 (US-style fallback)
]

# Number formatting — French Canadian style: 1 234,56 $
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "\N{NARROW NO-BREAK SPACE}"  # Unicode thin space (U+202F)
NUMBER_GROUPING = 3
