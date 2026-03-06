"""Shared constants for role-based access control."""

# Role constants - values match database/model choices.
# Display labels (shown in UI) are defined in UserProgramRole.ROLE_CHOICES.
#
#   ROLE_RECEPTIONIST    -> "Front Desk"
#   ROLE_STAFF           -> "Direct Service"
#   ROLE_PROGRAM_MANAGER -> "Program Manager"
#   ROLE_EXECUTIVE       -> "Executive"
#   ROLE_ADMIN           -> "Administrator"

ROLE_RECEPTIONIST = "receptionist"
ROLE_STAFF = "staff"
ROLE_PROGRAM_MANAGER = "program_manager"
ROLE_EXECUTIVE = "executive"
ROLE_ADMIN = "admin"

# Convenience sets
ALL_PROGRAM_ROLES = {ROLE_RECEPTIONIST, ROLE_STAFF, ROLE_PROGRAM_MANAGER, ROLE_EXECUTIVE}
CLIENT_ACCESS_ROLES = {ROLE_RECEPTIONIST, ROLE_STAFF, ROLE_PROGRAM_MANAGER}
MANAGEMENT_ROLES = {ROLE_PROGRAM_MANAGER, ROLE_EXECUTIVE}

# Higher number = more access.
# Executive has highest rank but no client data access.
ROLE_RANK = {
    ROLE_RECEPTIONIST: 1,
    ROLE_STAFF: 2,
    ROLE_PROGRAM_MANAGER: 3,
    ROLE_EXECUTIVE: 4,
}
