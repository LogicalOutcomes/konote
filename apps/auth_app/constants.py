"""Shared constants for role-based access control."""

# Higher number = more access.
# Executive has highest rank but no client data access.
ROLE_RANK = {
    "receptionist": 1,
    "staff": 2,
    "program_manager": 3,
    "executive": 4,
}
