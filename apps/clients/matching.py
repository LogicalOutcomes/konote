"""Duplicate client matching for Standard programs.

Compares encrypted fields in memory (can't be SQL-searched).
Only matches against clients in Standard (non-confidential) programs.
Respects demo/real data separation.

Phone matching is the primary signal. Name + DOB is a secondary fallback
when phone is unavailable or produces no match.
"""
from datetime import date

from .models import ClientFile, ClientProgramEnrolment
from .validators import normalize_phone_number


def _iter_matchable_clients(user, exclude_client_id=None):
    """Yield clients eligible for duplicate matching.

    Handles demo/real separation, client exclusion (for edit forms),
    and confidential program filtering in one place so every matching
    function applies the same security rules.
    """
    if user.is_demo:
        base_qs = ClientFile.objects.demo()
    else:
        base_qs = ClientFile.objects.real()

    if exclude_client_id:
        base_qs = base_qs.exclude(pk=exclude_client_id)

    # Exclude clients enrolled in ANY confidential program — they must
    # never appear in matching results, even if also in standard programs.
    confidential_client_ids = set(
        ClientProgramEnrolment.objects.filter(
            program__is_confidential=True,
            status="enrolled",
        ).values_list("client_file_id", flat=True)
    )

    for client in base_qs.iterator():
        if client.pk in confidential_client_ids:
            continue
        yield client


def _get_program_names(client):
    """Return list of Standard program names this client is enrolled in."""
    return list(
        ClientProgramEnrolment.objects.filter(
            client_file=client,
            status="enrolled",
            program__is_confidential=False,
        ).select_related("program")
        .values_list("program__name", flat=True)
    )


def _client_match_dict(client):
    """Build the standard match result dict for a client."""
    return {
        "client_id": client.pk,
        "first_name": client.first_name,
        "last_name": client.last_name,
        "program_names": _get_program_names(client),
    }


def _parse_date(val):
    """Parse a date string to a date object, or return None.

    Handles both ISO format strings and date objects.
    Using date.fromisoformat() instead of string comparison prevents
    silent mismatches from format differences (e.g. "2001-3-5" vs "2001-03-05").
    """
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def find_phone_matches(phone, user, exclude_client_id=None):
    """Find existing clients with the same phone number.

    Args:
        phone: Raw or normalised phone string to match against.
        user: The requesting user (for demo/real filtering).
        exclude_client_id: Optional client PK to exclude (for edit forms).

    Returns:
        List of dicts with keys: client_id, first_name, last_name, program_names.
        Empty list if no matches or phone is empty.
    """
    if not phone:
        return []

    normalised = normalize_phone_number(phone)
    if not normalised:
        return []

    matches = []
    for client in _iter_matchable_clients(user, exclude_client_id):
        client_phone = normalize_phone_number(client.phone or "")
        if client_phone and client_phone == normalised:
            matches.append(_client_match_dict(client))

    return matches


def find_name_dob_matches(first_name, birth_date, user, exclude_client_id=None):
    """Find existing clients with similar first name + same date of birth.

    Match logic:
    - First 3 characters of first_name, case-insensitive (casefold for Unicode)
    - Exact date of birth (parsed to date objects to prevent format drift)

    Args:
        first_name: The first name to match (needs 3+ chars after stripping).
        birth_date: Date of birth as string (YYYY-MM-DD) or date object.
        user: The requesting user (for demo/real filtering).
        exclude_client_id: Optional client PK to exclude (for edit forms).

    Returns:
        List of dicts with keys: client_id, first_name, last_name, program_names.
        Empty list if inputs are insufficient or no matches found.
    """
    input_prefix = (first_name or "").strip()[:3].casefold()
    if len(input_prefix) < 3:
        return []

    input_dob = _parse_date(birth_date)
    if input_dob is None:
        return []

    matches = []
    for client in _iter_matchable_clients(user, exclude_client_id):
        client_prefix = (client.first_name or "").strip()[:3].casefold()
        if len(client_prefix) < 3:
            continue
        if client_prefix != input_prefix:
            continue
        client_dob = _parse_date(client.birth_date)
        if client_dob is None:
            continue
        if client_dob == input_dob:
            matches.append(_client_match_dict(client))

    return matches


def find_duplicate_matches(phone, first_name, birth_date, user,
                           exclude_client_id=None):
    """Single-pass duplicate detection: phone first, name+DOB fallback.

    Iterates all matchable clients once, checking phone match on each.
    If no phone matches are found, checks name+DOB as a secondary signal.
    Returns the matches and which type matched so the UI can show
    appropriate wording (phone match = strong signal, name+DOB = weaker).

    Args:
        phone: Raw or normalised phone string (may be empty).
        first_name: First name string (may be empty).
        birth_date: Date of birth as string or date object (may be empty).
        user: The requesting user (for demo/real filtering).
        exclude_client_id: Optional client PK to exclude (for edit forms).

    Returns:
        Tuple of (matches_list, match_type) where match_type is
        "phone", "name_dob", or None if no matches found.
    """
    # Prepare phone comparison values
    normalised_phone = normalize_phone_number(phone) if phone else ""
    check_phone = bool(normalised_phone)

    # Prepare name+DOB comparison values
    input_prefix = (first_name or "").strip()[:3].casefold()
    input_dob = _parse_date(birth_date)
    check_name_dob = len(input_prefix) >= 3 and input_dob is not None

    # Nothing to check — return early
    if not check_phone and not check_name_dob:
        return [], None

    phone_matches = []
    name_dob_matches = []

    for client in _iter_matchable_clients(user, exclude_client_id):
        # Check phone (primary signal)
        if check_phone:
            client_phone = normalize_phone_number(client.phone or "")
            if client_phone and client_phone == normalised_phone:
                phone_matches.append(_client_match_dict(client))
                continue  # Already matched by phone, skip name+DOB

        # Check name+DOB (secondary signal)
        if check_name_dob:
            client_prefix = (client.first_name or "").strip()[:3].casefold()
            if len(client_prefix) >= 3 and client_prefix == input_prefix:
                client_dob = _parse_date(client.birth_date)
                if client_dob is not None and client_dob == input_dob:
                    name_dob_matches.append(_client_match_dict(client))

    # Phone matches take priority — stronger signal
    if phone_matches:
        return phone_matches, "phone"
    if name_dob_matches:
        return name_dob_matches, "name_dob"
    return [], None
