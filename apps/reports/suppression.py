"""Small-cell suppression for aggregate reports.

Prevents re-identification by replacing exact counts with "< N" when
a demographic cell has fewer than N participants.  Threshold of 5
aligns with the Pan-Canadian De-Identification Guidelines (CIHI, 2010)
and is the standard cited in the multi-tenancy DRR.

Secondary (complementary) suppression is applied automatically: when
one cell in a row is suppressed, at least one additional cell is also
suppressed to prevent derivation by subtraction from the row total.
"""

SMALL_CELL_THRESHOLD = 5


def suppress_small_cell(count, program=None, threshold=SMALL_CELL_THRESHOLD, *,
                        is_confidential=None):
    """Apply small-cell suppression to a single count value.

    In funder report context, call with ``program=None`` and no
    ``is_confidential`` flag — suppression applies unconditionally
    when the count is below threshold.  The legacy ``program`` and
    ``is_confidential`` parameters are kept for backward compatibility
    with dashboard and insights views that only suppress confidential
    programs.

    Args:
        count: The raw count (int).
        program: Optional Program instance.  When provided *and*
            ``is_confidential`` is not set, suppression only fires if
            ``program.is_confidential`` is True.  Pass ``None`` to
            suppress unconditionally (funder report path).
        threshold: Minimum count to display exactly (default 5).
        is_confidential: Optional bool override.  ``True`` forces
            suppression; ``False`` skips it; ``None`` defers to
            ``program.is_confidential``.

    Returns:
        int if no suppression needed, str "< {threshold}" if suppressed.
    """
    # Determine whether suppression applies.
    # When program is None and is_confidential is None we suppress
    # unconditionally — this is the funder report path.
    if program is not None or is_confidential is not None:
        confidential = (
            is_confidential if is_confidential is not None
            else getattr(program, "is_confidential", False)
        )
        if not confidential:
            return count

    if isinstance(count, int) and count < threshold:
        return f"< {threshold}"
    return count


def apply_secondary_suppression(row_values, threshold=SMALL_CELL_THRESHOLD):
    """Apply secondary suppression to a row of demographic cell values.

    When one cell is suppressed (count < threshold), a second cell must
    also be suppressed to prevent the suppressed value from being derived
    by subtraction from the total and remaining visible cells.

    The first element in ``row_values`` is assumed to be the "All
    Participants" total and is never secondarily suppressed (suppressing
    the total would make the entire row useless).  If only one non-total
    cell needs primary suppression, the next-smallest non-suppressed
    cell is also suppressed.

    Args:
        row_values: List of (label, count_or_value) tuples for one
            metric row.  The first element is the "All" total; the rest
            are demographic group cells.  ``count_or_value`` is an int
            (raw count) or already a suppression string (``"< N"``).
        threshold: The suppression threshold to use.

    Returns:
        List of (label, display_value) tuples with secondary
        suppression applied.  Original ints are preserved when no
        suppression is needed; suppressed cells become ``"< N"``
        strings.

    Example:
        >>> vals = [("All", 20), ("Age 18-24", 12), ("Age 25-44", 5), ("Age 45+", 3)]
        >>> apply_secondary_suppression(vals, threshold=5)
        [('All', 20), ('Age 18-24', 12), ('Age 25-44', '< 5'), ('Age 45+', '< 5')]
    """
    if len(row_values) <= 2:
        # Only "All" + one group — suppress that group if needed, but
        # secondary suppression is meaningless with one column.
        result = []
        for label, val in row_values:
            if isinstance(val, int) and 0 < val < threshold:
                result.append((label, f"< {threshold}"))
            else:
                result.append((label, val))
        return result

    suppressed_label = f"< {threshold}"

    # Separate the "All" total from demographic cells.
    all_label, all_value = row_values[0]
    demo_cells = list(row_values[1:])

    # Primary suppression pass — mark cells below threshold.
    primary_suppressed_indices = set()
    for i, (label, val) in enumerate(demo_cells):
        if isinstance(val, int) and 0 < val < threshold:
            primary_suppressed_indices.add(i)

    if not primary_suppressed_indices:
        # No suppression needed.
        return list(row_values)

    # Secondary suppression: if only one cell is suppressed,
    # suppress the next-smallest visible cell too.
    if len(primary_suppressed_indices) == 1:
        # Find the smallest non-suppressed cell (by count).
        candidates = []
        for i, (label, val) in enumerate(demo_cells):
            if i not in primary_suppressed_indices and isinstance(val, int):
                candidates.append((val, i))
        if candidates:
            candidates.sort()
            secondary_idx = candidates[0][1]
            primary_suppressed_indices.add(secondary_idx)

    # Build result.
    result = [(all_label, all_value)]
    for i, (label, val) in enumerate(demo_cells):
        if i in primary_suppressed_indices:
            result.append((label, suppressed_label))
        else:
            result.append((label, val))

    return result
