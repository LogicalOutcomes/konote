"""PII scrubbing for Outcome Insights — strips identifiable information before AI processing.

This is PII *scrubbing*, not de-identification (which has a specific legal meaning
under PIPEDA implying a higher standard). The goal is to remove names, phone numbers,
emails, postal codes, SIN numbers, and street addresses from free-text notes before
sending them to an external AI service.

Two-pass approach:
  1. Regex patterns for structured PII (phones, emails, postal codes, SINs, addresses)
     — run FIRST so names embedded in emails aren't corrupted
  2. Known names (client + staff) replaced with [NAME] using word-boundary matching
"""
import re


# ── Regex patterns for Canadian PII ──────────────────────────────────────────

# Canadian phone numbers: 613-555-1234, 613.555.1234, 6135551234, (613) 555-1234
_PHONE_RE = re.compile(
    r"\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)

# Email addresses
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Canadian postal codes: K1A 0B1, k1a0b1, K1A-0B1
_POSTAL_RE = re.compile(
    r"\b[A-Za-z]\d[A-Za-z][\s-]?\d[A-Za-z]\d\b"
)

# Social Insurance Numbers: 123-456-789, 123 456 789, 123456789
_SIN_RE = re.compile(
    r"\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b"
)

# Street addresses: "123 Main Street", "45 Elm Ave", etc.
_ADDRESS_RE = re.compile(
    r"\b\d+\s+\w+\s+"
    r"(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|"
    r"crescent|cres|court|ct|way|lane|ln|place|pl|circle|cir|"
    r"terrace|terr|trail|trl)\b",
    re.IGNORECASE,
)


def scrub_pii(text, known_names=None):
    """Remove PII from text before sending to an external AI service.

    Args:
        text: The text to scrub.
        known_names: Optional list/set of names to replace (client first/last/preferred
                     names and staff display names). Names are matched using word
                     boundaries to avoid corrupting common words (Hope, Grace, Faith).

    Returns:
        The scrubbed text with PII replaced by placeholders.
    """
    if not text:
        return text

    result = text

    # Pass 1: Structured PII with specific patterns (run FIRST so names
    # embedded in emails like john@example.com aren't corrupted)
    result = _EMAIL_RE.sub("[EMAIL]", result)
    result = _POSTAL_RE.sub("[POSTAL CODE]", result)
    result = _SIN_RE.sub("[SIN]", result)
    result = _ADDRESS_RE.sub("[ADDRESS]", result)
    result = _PHONE_RE.sub("[PHONE]", result)

    # Pass 2: Replace known names (longest first to avoid partial matches)
    if known_names:
        sorted_names = sorted(
            (n for n in known_names if n and len(n) >= 2),
            key=len,
            reverse=True,
        )
        for name in sorted_names:
            # Word-boundary match including possessives: "Hope" and "Hope's"
            pattern = re.compile(
                r"\b" + re.escape(name) + r"(?:'s)?\b",
                re.IGNORECASE,
            )
            result = pattern.sub("[NAME]", result)

    return result
