"""Duplicate client matching for Standard programs.

Compares phone numbers in memory (encrypted fields can't be SQL-searched).
Only matches against clients in Standard (non-confidential) programs.
Respects demo/real data separation.
"""
from .models import ClientFile, ClientProgramEnrolment
from .validators import normalize_phone_number


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

    # Get base queryset respecting demo/real separation
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

    # Load clients into memory and compare normalised phone numbers.
    # Acceptable performance up to ~2,000 clients (encrypted field ceiling).
    matches = []
    for client in base_qs.iterator():
        if client.pk in confidential_client_ids:
            continue
        client_phone = normalize_phone_number(client.phone or "")
        if client_phone and client_phone == normalised:
            # Get the Standard program names this client is enrolled in
            program_names = list(
                ClientProgramEnrolment.objects.filter(
                    client_file=client,
                    status="enrolled",
                    program__is_confidential=False,
                ).select_related("program")
                .values_list("program__name", flat=True)
            )
            matches.append({
                "client_id": client.pk,
                "first_name": client.first_name,
                "last_name": client.last_name,
                "program_names": program_names,
            })

    return matches
