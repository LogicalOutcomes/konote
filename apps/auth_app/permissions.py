"""Central permissions matrix — single source of truth for all role-based access.

This file defines what each role can do with each resource type.
Every permission check in the codebase should reference this file.
"""

from apps.auth_app.constants import ROLE_RANK

# Permission levels
DENY = "deny"          # Never allowed
ALLOW = "allow"        # Always allowed (within programme scope)
SCOPED = "scoped"      # Allowed if assigned to specific group/client
GATED = "gated"        # Allowed with documented reason (just-in-time access)
PER_FIELD = "per_field"  # Check field-level configuration

# --- Phase 1: Current permissions (what the system enforces now) ---

PERMISSIONS = {
    "receptionist": {
        # Tier 1: Operational only — can check people in, see names, safety info only
        "client.view_name": ALLOW,
        "client.view_contact": ALLOW,
        "client.view_safety": ALLOW,  # Allergies, medical alert CONDITIONS (not treatments),
                                      # emergency contacts, staff alerts. Does NOT include
                                      # medications — medications reveal diagnosis and are
                                      # clinical data (use client.view_medications).
        "client.view_medications": DENY,  # Medications reveal diagnosis (clinical data)
        "client.view_clinical": DENY,  # No diagnosis, treatment plans, notes
        "client.edit": DENY,

        "attendance.check_in": ALLOW,  # Primary function
        "attendance.view_report": DENY,

        "group.view_roster": DENY,  # Group type reveals diagnosis
        "group.view_detail": DENY,
        "group.log_session": DENY,
        "group.edit": DENY,
        "group.manage_members": DENY,

        "note.view": DENY,
        "note.create": DENY,
        "note.edit": DENY,

        "plan.view": DENY,
        "plan.edit": DENY,

        "metric.view_individual": DENY,
        "metric.view_aggregate": DENY,

        "report.programme_report": DENY,  # Managers generate, not front desk
        "report.data_extract": DENY,

        "event.view": DENY,
        "event.create": DENY,

        "alert.view": DENY,
        "alert.create": DENY,
        "alert.cancel": DENY,

        "custom_field.view": PER_FIELD,  # Uses field.front_desk_access setting
        "custom_field.edit": PER_FIELD,

        # Clinical records
        "consent.view": DENY,
        "consent.manage": DENY,
        "intake.view": DENY,
        "intake.edit": DENY,

        # Delete permissions (destructive actions — almost always admin-only)
        "note.delete": DENY,   # Notes are clinical records — cancel, don't delete
        "client.delete": DENY,  # Handled by admin erasure workflow
        "plan.delete": DENY,   # Plans should be archived, not deleted

        # System administration (admin-only via @admin_required)
        "user.manage": DENY,
        "settings.manage": DENY,
        "programme.manage": DENY,
        "audit.view": DENY,
    },

    "staff": {
        # Tier 2: Clinical access — scoped to assigned groups/clients (Phase 2)
        # Phase 1: scoped to programme (existing behaviour preserved)
        "client.view_name": ALLOW,
        "client.view_contact": ALLOW,
        "client.view_safety": ALLOW,  # Allergies, medical alert CONDITIONS (not treatments),
                                      # emergency contacts, staff alerts. NOT medications.
        "client.view_medications": SCOPED,  # Same access pattern as clinical data
        "client.view_clinical": SCOPED,  # Phase 1: programme. Phase 2: assigned groups/clients
        "client.edit": SCOPED,

        "attendance.check_in": SCOPED,
        "attendance.view_report": SCOPED,

        "group.view_roster": SCOPED,  # Phase 1: programme. Phase 2: assigned groups only
        "group.view_detail": SCOPED,
        "group.log_session": SCOPED,
        "group.edit": DENY,  # Can't change group config
        "group.manage_members": DENY,  # PM adds/removes members

        "note.view": SCOPED,
        "note.create": SCOPED,
        "note.edit": SCOPED,  # Own notes only

        "plan.view": SCOPED,
        "plan.edit": SCOPED,

        "metric.view_individual": SCOPED,
        "metric.view_aggregate": SCOPED,

        "report.programme_report": DENY,
        "report.data_extract": DENY,

        "event.view": SCOPED,
        "event.create": SCOPED,

        "alert.view": SCOPED,
        "alert.create": SCOPED,
        "alert.cancel": SCOPED,  # Own alerts only (or admin)

        "custom_field.view": SCOPED,
        "custom_field.edit": SCOPED,

        # Clinical records
        "consent.view": SCOPED,
        "consent.manage": SCOPED,
        "intake.view": SCOPED,
        "intake.edit": SCOPED,

        # Delete permissions (destructive actions — almost always admin-only)
        "note.delete": DENY,   # Notes are clinical records — cancel, don't delete
        "client.delete": DENY,  # Handled by admin erasure workflow
        "plan.delete": DENY,   # Plans should be archived, not deleted

        # System administration (admin-only via @admin_required)
        "user.manage": DENY,
        "settings.manage": DENY,
        "programme.manage": DENY,
        "audit.view": DENY,
    },

    "program_manager": {
        # Tier 3: Administrative + aggregate data
        # Phase 1: same as staff (existing behaviour)
        # Phase 3: aggregate-only default with gated individual access
        "client.view_name": ALLOW,
        "client.view_contact": ALLOW,
        "client.view_safety": ALLOW,  # Allergies, medical alert CONDITIONS (not treatments),
                                      # emergency contacts, staff alerts. NOT medications.
        "client.view_medications": ALLOW,  # Same access pattern as clinical data
        "client.view_clinical": ALLOW,  # Phase 3: GATED (just-in-time with reason)
        "client.edit": DENY,  # Phase 3: managers don't edit client records

        "attendance.check_in": DENY,
        "attendance.view_report": ALLOW,  # Aggregate attendance

        "group.view_roster": ALLOW,
        "group.view_detail": ALLOW,  # Phase 3: GATED for session content
        "group.log_session": DENY,
        "group.edit": ALLOW,  # Can configure groups
        "group.manage_members": ALLOW,  # Can add/remove members

        "note.view": ALLOW,  # Phase 3: GATED with documented reason
        "note.create": DENY,
        "note.edit": DENY,

        "plan.view": ALLOW,  # Phase 3: GATED
        "plan.edit": DENY,

        "metric.view_individual": ALLOW,  # Phase 3: GATED
        "metric.view_aggregate": ALLOW,

        "report.programme_report": ALLOW,  # Primary use case
        "report.data_extract": DENY,  # Phase 3: request-only (requires admin approval)

        "event.view": ALLOW,  # Phase 3: GATED
        "event.create": DENY,

        "alert.view": ALLOW,
        "alert.create": DENY,
        "alert.cancel": ALLOW,  # Can cancel any alert in their programme

        "custom_field.view": ALLOW,  # Phase 3: GATED
        "custom_field.edit": DENY,

        # Clinical records
        "consent.view": ALLOW,
        "consent.manage": ALLOW,
        "intake.view": ALLOW,
        "intake.edit": DENY,

        # Delete permissions (destructive actions — almost always admin-only)
        "note.delete": DENY,   # Notes are clinical records — cancel, don't delete
        "client.delete": DENY,  # Handled by admin erasure workflow
        "plan.delete": DENY,   # Plans should be archived, not deleted

        # System administration (admin-only via @admin_required)
        "user.manage": DENY,
        "settings.manage": DENY,
        "programme.manage": DENY,
        "audit.view": DENY,
    },

    "executive": {
        # Tier 4: Org-wide aggregate only — no individual client data
        "client.view_name": DENY,
        "client.view_contact": DENY,
        "client.view_safety": DENY,  # Executives see aggregate data only, no individual safety info
        "client.view_medications": DENY,  # No individual clinical data
        "client.view_clinical": DENY,
        "client.edit": DENY,

        "attendance.check_in": DENY,
        "attendance.view_report": ALLOW,  # Aggregate only, org-wide

        "group.view_roster": DENY,
        "group.view_detail": DENY,
        "group.log_session": DENY,
        "group.edit": DENY,
        "group.manage_members": DENY,

        "note.view": DENY,
        "note.create": DENY,
        "note.edit": DENY,

        "plan.view": DENY,
        "plan.edit": DENY,

        "metric.view_individual": DENY,
        "metric.view_aggregate": ALLOW,  # Org-wide

        "report.programme_report": ALLOW,  # View only (managers generate)
        "report.data_extract": DENY,

        "event.view": DENY,
        "event.create": DENY,

        "alert.view": DENY,
        "alert.create": DENY,
        "alert.cancel": DENY,

        "custom_field.view": DENY,
        "custom_field.edit": DENY,

        # Clinical records
        "consent.view": DENY,
        "consent.manage": DENY,
        "intake.view": DENY,
        "intake.edit": DENY,

        # Delete permissions (destructive actions — almost always admin-only)
        "note.delete": DENY,   # Notes are clinical records — cancel, don't delete
        "client.delete": DENY,  # Handled by admin erasure workflow
        "plan.delete": DENY,   # Plans should be archived, not deleted

        # System administration (admin-only via @admin_required)
        "user.manage": DENY,
        "settings.manage": DENY,
        "programme.manage": DENY,
        "audit.view": ALLOW,   # Board oversight — executives can review audit trail
    },
}


def can_access(role, permission):
    """Check if a role has a given permission.

    Args:
        role: role name (receptionist, staff, program_manager, executive)
        permission: permission key like "group.view_roster"

    Returns:
        Permission level: DENY, ALLOW, SCOPED, GATED, or PER_FIELD
    """
    return PERMISSIONS.get(role, {}).get(permission, DENY)


def get_permission_summary(role):
    """Get all permissions for a role as a dictionary.

    Args:
        role: role name (receptionist, staff, program_manager, executive)

    Returns:
        Dictionary of permission keys to permission levels
    """
    return PERMISSIONS.get(role, {})


def validate_permissions():
    """Validate that all roles have all permission keys defined.

    Returns:
        (is_valid, errors) tuple where errors is a list of missing keys
    """
    errors = []

    # Get all permission keys across all roles
    all_keys = set()
    for role_perms in PERMISSIONS.values():
        all_keys.update(role_perms.keys())

    # Check each role has all keys
    for role in ["receptionist", "staff", "program_manager", "executive"]:
        if role not in PERMISSIONS:
            errors.append(f"Role '{role}' missing from PERMISSIONS")
            continue

        role_keys = set(PERMISSIONS[role].keys())
        missing = all_keys - role_keys
        if missing:
            errors.append(f"Role '{role}' missing keys: {', '.join(sorted(missing))}")

    return (len(errors) == 0, errors)


def permission_to_plain_english(perm_key, perm_level):
    """Convert permission keys to readable sentences.

    Args:
        perm_key: permission key like "group.view_roster"
        perm_level: permission level (ALLOW, DENY, SCOPED, etc.)

    Returns:
        Human-readable description of what this permission means
    """
    TRANSLATIONS = {
        "client.view_name": "See client names",
        "client.view_contact": "See client contact information",
        "client.view_safety": "See safety information (allergies, medical alert conditions, emergency contacts, staff alerts — NOT medications)",
        "client.view_medications": "See client medications (clinical data — reveals diagnosis)",
        "client.view_clinical": "See clinical information (diagnosis, treatment plans, notes)",
        "client.edit": "Edit client records",

        "attendance.check_in": "Check clients in and out",
        "attendance.view_report": "View attendance reports",

        "group.view_roster": "See who is in each group",
        "group.view_detail": "View group details and session content",
        "group.log_session": "Record group session attendance and notes",
        "group.edit": "Edit group configuration",
        "group.manage_members": "Add or remove group members",

        "note.view": "Read progress notes",
        "note.create": "Write new progress notes",
        "note.edit": "Edit progress notes",

        "plan.view": "View client treatment plans",
        "plan.edit": "Edit client treatment plans",

        "metric.view_individual": "See individual client metrics and outcomes",
        "metric.view_aggregate": "See aggregate metrics and reports",

        "report.programme_report": "Generate programme reports (for funders/board)",
        "report.data_extract": "Export client data extracts",

        "event.view": "View client events and timeline",
        "event.create": "Record new client events",

        "alert.view": "View client safety alerts",
        "alert.create": "Create client safety alerts",
        "alert.cancel": "Cancel safety alerts",

        "custom_field.view": "View custom fields",
        "custom_field.edit": "Edit custom fields",

        # Clinical records
        "consent.view": "View client consent records",
        "consent.manage": "Record or withdraw client consent",
        "intake.view": "View intake forms (may contain detailed clinical history)",
        "intake.edit": "Edit intake forms",

        # Delete permissions
        "note.delete": "Delete progress notes (notes should be cancelled, not deleted)",
        "client.delete": "Delete/erase client records (admin-only via erasure workflow)",
        "plan.delete": "Delete treatment plans (plans should be archived, not deleted)",

        # System administration
        "user.manage": "Create, edit, or deactivate user accounts (admin-only)",
        "settings.manage": "Change system configuration, feature toggles, and terminology (admin-only)",
        "programme.manage": "Create, edit, or archive programmes (admin-only)",
        "audit.view": "View the audit log",
    }

    base = TRANSLATIONS.get(perm_key, perm_key)

    if perm_level == SCOPED:
        base += " (for their assigned clients/groups)"
    elif perm_level == GATED:
        base += " (with documented reason)"
    elif perm_level == PER_FIELD:
        base += " (based on field settings)"
    elif perm_level == DENY:
        return f"CANNOT {base.lower()}"

    return base
