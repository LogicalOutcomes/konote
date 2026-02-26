"""Small-cell suppression for confidential program reports.

Prevents inference attacks by replacing exact counts with "< 5" when
a confidential program has fewer than 5 participants in a cell.
Threshold of 5 aligns with the Pan-Canadian De-Identification Guidelines
(CIHI, 2010) and is the standard cited in the multi-tenancy DRR.
"""

SMALL_CELL_THRESHOLD = 5


def suppress_small_cell(count, program, threshold=SMALL_CELL_THRESHOLD, *,
                        is_confidential=None):
    """Apply small-cell suppression to protect confidential program data.

    Args:
        count: The raw count (int).
        program: Program instance — suppression only applies if is_confidential.
            May be None for All Programs mode; use ``is_confidential`` override.
        threshold: Minimum count to display exactly (default 5).
        is_confidential: Optional bool override. When True, suppression is
            applied regardless of ``program``. Useful for All Programs mode
            where program is None but at least one accessible program is
            confidential.

    Returns:
        int if no suppression needed, str "< {threshold}" if suppressed.

    Examples:
        suppress_small_cell(25, confidential_prog) -> 25
        suppress_small_cell(3, confidential_prog)  -> "< 5"
        suppress_small_cell(3, standard_prog)      -> 3
        suppress_small_cell(3, None, is_confidential=True) -> "< 5"
    """
    confidential = (
        is_confidential if is_confidential is not None
        else getattr(program, "is_confidential", False)
    )
    if not confidential:
        return count
    if count < threshold:
        return f"< {threshold}"
    return count
