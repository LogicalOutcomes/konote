"""Central permissions matrix — single source of truth for all role-based access.

This file defines what each role can do with each resource type.
Every permission check in the codebase should reference this file.

Enforcement layers:
- @requires_permission("key") decorator reads from can_access()
- {% has_permission "key" %} template tag reads from can_access()
- @admin_required is a SEPARATE system — admin keys here are documentation only
"""

from apps.auth_app.constants import ROLE_RANK

# Permission levels
DENY = "deny"          # Never allowed
ALLOW = "allow"        # Always allowed (within program scope)
SCOPED = "scoped"      # Allowed if assigned to specific group/client
GATED = "gated"        # Allowed with documented reason (just-in-time access)
PER_FIELD = "per_field"  # Check field-level configuration

# --- Permissions matrix (single source of truth) ---

PERMISSIONS = {
    "receptionist": {
        # Tier 1: Operational only — can check people in, see names, safety info only
        "client.view_name": ALLOW,  # Enforced by get_visible_fields() via can_access()
        "client.view_contact": ALLOW,  # Enforced by get_visible_fields() via can_access()
        "client.view_safety": ALLOW,  # Allergies, medical alert CONDITIONS (not treatments),
                                      # emergency contacts, staff alerts. Does NOT include
                                      # medications — medications reveal diagnosis and are
                                      # clinical data (use client.view_medications).
                                      # Enforced by get_visible_fields() via can_access()
        "client.view_medications": DENY,  # Medications reveal diagnosis (clinical data)
        "client.view_clinical": DENY,  # Enforced by get_visible_fields() via can_access(). No diagnosis, treatment plans, notes
        "client.edit": DENY,  # Enforced by @requires_permission
        "client.create": ALLOW,  # Front desk does intake. Enforced by @requires_permission
        "client.edit_contact": ALLOW,  # Phone + email ONLY — not address or emergency contact
                                       # (safety implications for DV). Replace with PER_FIELD in Phase 2.
                                       # Enforced by @requires_permission

        "attendance.check_in": ALLOW,  # Primary function. Enforced by view-level check
        "attendance.view_report": DENY,

        "group.view_roster": DENY,  # Confirmed correct (expert review): group type reveals diagnosis
        "group.view_detail": DENY,
        "group.log_session": DENY,
        "group.edit": DENY,
        "group.manage_members": DENY,
        "group.create": DENY,
        "group.manage_content": DENY,
        "group.view_report": DENY,

        "note.view": DENY,  # Enforced by @requires_permission
        "note.create": DENY,  # Confirmed correct: front desk don't write clinical notes
        "note.edit": DENY,

        "plan.view": DENY,  # Enforced by @requires_permission
        "plan.edit": DENY,

        "metric.view_individual": DENY,
        "metric.view_aggregate": DENY,

        "report.program_report": DENY,  # Managers generate, not front desk
        "report.funder_report": DENY,  # Managers/executives generate funder reports
        "report.data_extract": DENY,

        "insights.view": DENY,  # Outcome insights — staff+ only

        "event.view": DENY,
        "event.create": DENY,

        "meeting.view": DENY,    # Front desk don't manage meetings
        "meeting.create": DENY,
        "meeting.edit": DENY,

        "communication.view": DENY,  # Front desk don't see communication logs
        "communication.log": DENY,

        "alert.view": DENY,
        "alert.create": DENY,
        "alert.cancel": DENY,
        "alert.recommend_cancel": DENY,  # Front desk have no alert access
        "alert.review_cancel_recommendation": DENY,

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
        "erasure.manage": DENY,  # PM-only via erasure workflow

        # System administration (admin-only via @admin_required — separate system)
        "user.manage": DENY,  # Enforced by @admin_required (not matrix-driven)
        "settings.manage": DENY,  # Enforced by @admin_required (not matrix-driven)
        "program.manage": DENY,  # Enforced by @admin_required (not matrix-driven)
        "audit.view": DENY,  # Enforced by @admin_required (not matrix-driven)
    },

    "staff": {
        # Tier 2: Clinical access — scoped to assigned groups/clients (Phase 2)
        # Phase 1: scoped to program (existing behaviour preserved)
        "client.view_name": ALLOW,
        "client.view_contact": ALLOW,
        "client.view_safety": ALLOW,  # Allergies, medical alert CONDITIONS (not treatments),
                                      # emergency contacts, staff alerts. NOT medications.
        "client.view_medications": SCOPED,  # Same access pattern as clinical data
        "client.view_clinical": SCOPED,  # Phase 1: program. Phase 2: assigned groups/clients
        "client.edit": SCOPED,  # Enforced by @requires_permission
        "client.create": SCOPED,  # Creates in own program, especially outreach. Enforced by @requires_permission
        "client.edit_contact": SCOPED,  # Phone + email within own program. Enforced by @requires_permission

        "attendance.check_in": SCOPED,
        "attendance.view_report": SCOPED,

        "group.view_roster": SCOPED,  # Phase 1: program. Phase 2: assigned groups only
        "group.view_detail": SCOPED,
        "group.log_session": SCOPED,
        "group.edit": DENY,  # Can't change group config
        "group.manage_members": SCOPED,  # Facilitators manage own group rosters.
                                         # All changes must create audit entry (PHIPA — group type reveals diagnosis).
                                         # Enforced by @requires_permission
        "group.create": SCOPED,  # Staff can create groups in their program. Enforced by @requires_permission
        "group.manage_content": SCOPED,  # Milestones + outcomes for project groups. Enforced by @requires_permission
        "group.view_report": SCOPED,  # Attendance reports for groups in their program. Enforced by @requires_permission

        "note.view": SCOPED,  # Enforced by @requires_permission. Migrate from @program_role_required
        "note.create": SCOPED,  # Enforced by @requires_permission
        "note.edit": SCOPED,  # Own notes only. Enforced by @requires_permission

        "plan.view": SCOPED,  # Enforced by @requires_permission
        "plan.edit": SCOPED,  # Enforced by @requires_permission

        "metric.view_individual": SCOPED,
        "metric.view_aggregate": SCOPED,

        "report.program_report": DENY,
        "report.funder_report": DENY,  # Managers/executives generate funder reports
        "report.data_extract": DENY,

        "insights.view": SCOPED,  # Program-level outcome insights. Enforced by @requires_permission

        "event.view": SCOPED,  # Enforced by @requires_permission
        "event.create": SCOPED,

        "meeting.view": SCOPED,    # Staff see their own meetings. Enforced by @requires_permission
        "meeting.create": SCOPED,  # Staff schedule meetings with clients. Enforced by @requires_permission
        "meeting.edit": SCOPED,    # Staff edit their own meetings. Enforced by @requires_permission

        "communication.view": SCOPED,  # View logs for clients in their program
        "communication.log": SCOPED,   # Log calls, texts, emails. Enforced by @requires_permission

        "alert.view": SCOPED,
        "alert.create": SCOPED,
        "alert.cancel": DENY,  # Two-person safety rule. Staff posts "recommend cancellation"
                                # with assessment; PM reviews and cancels.
                                # See alert recommendation workflow.
        "alert.recommend_cancel": SCOPED,  # Staff proposes cancellation; PM approves (two-person rule).
                                           # Enforced by @requires_permission
        "alert.review_cancel_recommendation": DENY,  # Only PMs review recommendations

        "custom_field.view": SCOPED,
        "custom_field.edit": SCOPED,

        # Clinical records
        "consent.view": SCOPED,
        "consent.manage": SCOPED,  # Enforced by @requires_permission
        "intake.view": SCOPED,
        "intake.edit": SCOPED,

        # Delete permissions (destructive actions — almost always admin-only)
        "note.delete": DENY,   # Notes are clinical records — cancel, don't delete
        "client.delete": DENY,  # Handled by admin erasure workflow
        "plan.delete": DENY,   # Plans should be archived, not deleted
        "erasure.manage": DENY,  # PM-only via erasure workflow

        # System administration (admin-only via @admin_required — separate system)
        "user.manage": DENY,  # Enforced by @admin_required (not matrix-driven)
        "settings.manage": DENY,  # Enforced by @admin_required (not matrix-driven)
        "program.manage": DENY,  # Enforced by @admin_required (not matrix-driven)
        "audit.view": DENY,  # Enforced by @admin_required (not matrix-driven)
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
        "client.create": SCOPED,  # Intake in smaller programs. Enforced by @requires_permission
        "client.edit_contact": DENY,  # PMs don't edit individual contact info

        "attendance.check_in": DENY,
        "attendance.view_report": ALLOW,  # Aggregate attendance

        "group.view_roster": ALLOW,
        "group.view_detail": ALLOW,  # Phase 3: GATED for session content
        "group.log_session": DENY,
        "group.edit": ALLOW,  # Can configure groups
        "group.manage_members": ALLOW,  # Can add/remove members. Enforced by @requires_permission
        "group.create": ALLOW,  # Managers configure program groups. Enforced by @requires_permission
        "group.manage_content": ALLOW,  # Managers oversee project milestones/outcomes. Enforced by @requires_permission
        "group.view_report": ALLOW,  # Attendance reports. Enforced by @requires_permission

        "note.view": ALLOW,  # Phase 3: GATED with documented reason. Enforced by @requires_permission
        "note.create": SCOPED,  # Lead workers / team leads carry caseloads and write notes
        "note.edit": SCOPED,  # Own notes only. Enforced by @requires_permission

        "plan.view": ALLOW,  # Phase 3: GATED. Enforced by @requires_permission
        "plan.edit": DENY,

        "metric.view_individual": ALLOW,  # Phase 3: GATED
        "metric.view_aggregate": ALLOW,

        "report.program_report": ALLOW,  # Individual with friction (elevated delay + admin
                                        # notification). Enforced by is_aggregate_only_user()
                                        # + _save_export_and_create_link()
        "report.funder_report": ALLOW,  # Managers generate funder reports for their programs.
                                        # Enforced by @requires_permission
        "report.data_extract": ALLOW,  # PM handles PIPEDA data portability requests

        "insights.view": ALLOW,  # Program-level outcome insights. Enforced by @requires_permission

        "event.view": ALLOW,  # Phase 3: GATED. Enforced by @requires_permission
        "event.create": DENY,

        "meeting.view": ALLOW,    # PMs see team meetings for oversight
        "meeting.create": SCOPED,  # PMs can schedule in smaller programs
        "meeting.edit": DENY,     # PMs don't edit individual meetings

        "communication.view": ALLOW,  # PMs view communication logs for oversight + funder stats
        "communication.log": SCOPED,  # PMs log in smaller programs

        "alert.view": ALLOW,
        "alert.create": ALLOW,  # Supervisors should flag safety concerns when reviewing
                                # case files. No barriers to creating safety alerts.
                                # Enforced by @requires_permission
        "alert.cancel": ALLOW,  # Can cancel any alert in their program
        "alert.recommend_cancel": DENY,  # PMs cancel directly, they don't need to recommend
        "alert.review_cancel_recommendation": ALLOW,  # PMs review staff recommendations.
                                                       # Enforced by @requires_permission

        "custom_field.view": ALLOW,  # Phase 3: GATED
        "custom_field.edit": DENY,

        # Clinical records
        "consent.view": ALLOW,
        "consent.manage": SCOPED,  # PMs do intake in smaller programs. Consent records
                                   # immutable after creation — can only withdraw and re-record.
                                   # Enforced by @requires_permission
        "intake.view": ALLOW,
        "intake.edit": DENY,

        # Delete permissions (destructive actions — almost always admin-only)
        "note.delete": DENY,   # Notes are clinical records — cancel, don't delete
        "client.delete": DENY,  # Handled by admin erasure workflow
        "plan.delete": DENY,   # Plans should be archived, not deleted
        "erasure.manage": SCOPED,  # PMs manage erasure requests for their own programs.
                                   # Enforced by @requires_permission_global + internal scoping

        # System administration — SCOPED for program managers (own program only)
        "user.manage": SCOPED,  # Own program team. CANNOT elevate roles
                                # (front desk->staff) or create PM/executive accounts.
                                # Requires custom enforcement — see no-elevation constraint.
                                # Enforced by @requires_permission + custom view logic
        "settings.manage": DENY,  # Enforced by @admin_required (not matrix-driven)
        "program.manage": SCOPED,  # Own program only. Enforced by @requires_permission
        "audit.view": SCOPED,  # QA oversight for own program. Enforced by @requires_permission
    },

    "executive": {
        # Tier 4: Org-wide aggregate only — no individual client data
        "client.view_name": DENY,
        "client.view_contact": DENY,
        "client.view_safety": DENY,  # Executives see aggregate data only, no individual safety info
        "client.view_medications": DENY,  # No individual clinical data
        "client.view_clinical": DENY,
        "client.edit": DENY,
        "client.create": DENY,  # Executives don't do intake
        "client.edit_contact": DENY,

        "attendance.check_in": DENY,
        "attendance.view_report": ALLOW,  # Aggregate only, org-wide

        "group.view_roster": DENY,
        "group.view_detail": DENY,
        "group.log_session": DENY,
        "group.edit": DENY,
        "group.manage_members": DENY,
        "group.create": DENY,
        "group.manage_content": DENY,
        "group.view_report": DENY,

        "note.view": DENY,  # Enforced by @requires_permission
        "note.create": DENY,
        "note.edit": DENY,

        "plan.view": DENY,  # Enforced by @requires_permission
        "plan.edit": DENY,

        "metric.view_individual": DENY,
        "metric.view_aggregate": ALLOW,  # Org-wide

        "report.program_report": ALLOW,  # View only (managers generate). Enforced by @requires_permission
        "report.funder_report": ALLOW,  # Executives can generate aggregate funder reports.
                                        # Enforced by @requires_permission
        "report.data_extract": DENY,

        "insights.view": ALLOW,  # Aggregate outcome insights only (quotes suppressed).
                                 # Enforced by @requires_permission

        "event.view": DENY,
        "event.create": DENY,

        "meeting.view": DENY,    # Executives see aggregate data only
        "meeting.create": DENY,
        "meeting.edit": DENY,

        "communication.view": DENY,  # Executives see aggregate stats via reports, not individual logs
        "communication.log": DENY,

        "alert.view": DENY,
        "alert.create": DENY,
        "alert.cancel": DENY,
        "alert.recommend_cancel": DENY,
        "alert.review_cancel_recommendation": DENY,

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
        "erasure.manage": DENY,

        # System administration — DENY by default for executives.
        # Override to ALLOW for agencies where executive is operational ED (not board member).
        "user.manage": DENY,  # Override to ALLOW if executive is operational ED
        "settings.manage": DENY,  # Override to ALLOW if executive is operational ED
        "program.manage": DENY,  # Override to ALLOW if executive is operational ED
        "audit.view": ALLOW,   # Board oversight — executives can review audit trail
    },
}

# All valid permission keys (computed once at import time for validation)
ALL_PERMISSION_KEYS = frozenset(
    key
    for role_perms in PERMISSIONS.values()
    for key in role_perms.keys()
)


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
        "client.create": "Create new client records",
        "client.edit_contact": "Update client phone number and email",

        "attendance.check_in": "Check clients in and out",
        "attendance.view_report": "View attendance reports",

        "group.view_roster": "See who is in each group",
        "group.view_detail": "View group details and session content",
        "group.log_session": "Record group session attendance and notes",
        "group.edit": "Edit group configuration",
        "group.manage_members": "Add or remove group members",
        "group.create": "Create new groups",
        "group.manage_content": "Manage project milestones and outcomes",
        "group.view_report": "View group attendance reports",

        "note.view": "Read progress notes",
        "note.create": "Write new progress notes",
        "note.edit": "Edit progress notes",

        "plan.view": "View client treatment plans",
        "plan.edit": "Edit client treatment plans",

        "metric.view_individual": "See individual client metrics and outcomes",
        "metric.view_aggregate": "See aggregate metrics and reports",

        "report.program_report": "Generate program outcome reports",
        "report.funder_report": "Generate funder demographic reports",
        "report.data_extract": "Export client data extracts",

        "event.view": "View client events and timeline",
        "event.create": "Record new client events",

        "meeting.view": "View scheduled meetings",
        "meeting.create": "Schedule new meetings with clients",
        "meeting.edit": "Edit meeting details (time, location, status)",

        "communication.view": "View communication logs",
        "communication.log": "Log calls, texts, emails, and visits",

        "alert.view": "View client safety alerts",
        "alert.create": "Create client safety alerts",
        "alert.cancel": "Cancel safety alerts",
        "alert.recommend_cancel": "Recommend cancellation of a safety alert (for PM review)",
        "alert.review_cancel_recommendation": "Approve or reject alert cancellation recommendations",

        "custom_field.view": "View custom fields",
        "custom_field.edit": "Edit custom fields",

        "insights.view": "View program outcome insights",

        # Clinical records
        "consent.view": "View client consent records",
        "consent.manage": "Record or withdraw client consent",
        "intake.view": "View intake forms (may contain detailed clinical history)",
        "intake.edit": "Edit intake forms",

        # Delete permissions
        "note.delete": "Delete progress notes (notes should be cancelled, not deleted)",
        "client.delete": "Delete/erase client records (admin-only via erasure workflow)",
        "erasure.manage": "Request, approve, reject, or cancel client data erasure",
        "plan.delete": "Delete treatment plans (plans should be archived, not deleted)",

        # System administration
        "user.manage": "Create, edit, or deactivate user accounts",
        "settings.manage": "Change system configuration, feature toggles, and terminology",
        "program.manage": "Create, edit, or archive programs",
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
