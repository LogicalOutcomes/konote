"""Small-cell suppression for confidential program reports.

Prevents inference attacks by replacing exact counts with "< 10" when
a confidential program has fewer than 10 clients. Threshold of 10 aligns
with Statistics Canada small-cell suppression standard and CIHI practice.
"""

SMALL_CELL_THRESHOLD = 10


def suppress_small_cell(count, program, threshold=SMALL_CELL_THRESHOLD):
    """Apply small-cell suppression to protect confidential program data.

    Args:
        count: The raw count (int).
        program: Program instance — suppression only applies if is_confidential.
        threshold: Minimum count to display exactly (default 10).

    Returns:
        int if no suppression needed, str "< {threshold}" if suppressed.

    Examples:
        suppress_small_cell(25, confidential_prog) -> 25
        suppress_small_cell(7, confidential_prog)  -> "< 10"
        suppress_small_cell(7, standard_prog)      -> 7
    """
    if not getattr(program, "is_confidential", False):
        return count
    if count < threshold:
        return f"< {threshold}"
    return count
