"""XLSForm definitions for ODK Collect field forms.

These structures define the forms that get deployed to ODK Central.
Each definition follows the XLSForm specification:
https://xlsform.org/en/

The sync_odk command can convert these to XLSForm .xlsx files
for upload to ODK Central.

Form design principles (from DRR):
- Form titles are always generic (never reveal program type)
- Entity list names are generic ("Participants", "Groups")
- Engagement and alliance scales match KoNote exactly
- Field notes are always "quick" type (no structured templates)
"""

# ------------------------------------------------------------------
# Form 1: Session Attendance
# ------------------------------------------------------------------
SESSION_ATTENDANCE = {
    "settings": {
        "form_title": "Session Attendance",
        "form_id": "session_attendance",
        "version": "2026022401",
        "instance_name": "concat('Session ', ${session_date})",
    },
    "survey": [
        {
            "type": "select_one_from_file groups.csv",
            "name": "group",
            "label": "Group",
            "required": "yes",
        },
        {
            "type": "hidden",
            "name": "group_konote_id",
            "label": "Group KoNote ID",
            "calculation": "instance('groups')/root/item[name=${group}]/konote_group_id",
        },
        {
            "type": "date",
            "name": "session_date",
            "label": "Session date",
            "required": "yes",
            "default": "today()",
        },
        {
            "type": "text",
            "name": "location",
            "label": "Location (optional)",
            "required": "no",
        },
        {
            "type": "note",
            "name": "attendance_header",
            "label": "## Members Present\nCheck the box for each member who attended.",
        },
        # Members present is a select_multiple from the group's member entity list.
        # The actual implementation uses a repeat group with member entities filtered
        # by the selected group. This is a simplified representation.
        {
            "type": "select_multiple_from_file group_members.csv",
            "name": "members_present",
            "label": "Members present",
            "choice_filter": "group_id=${group_konote_id}",
        },
        {
            "type": "text",
            "name": "session_notes",
            "label": "Session notes (optional)",
            "required": "no",
            "appearance": "multiline",
        },
    ],
}


# ------------------------------------------------------------------
# Form 2: Visit Note
# ------------------------------------------------------------------
VISIT_NOTE = {
    "settings": {
        "form_title": "Visit Note",
        "form_id": "visit_note",
        "version": "2026022401",
        "instance_name": "concat('Visit ', ${visit_date})",
    },
    "survey": [
        {
            "type": "select_one_from_file participants.csv",
            "name": "participant",
            "label": "Participant",
            "required": "yes",
        },
        {
            "type": "hidden",
            "name": "participant_konote_id",
            "label": "Participant KoNote ID",
            "calculation": "instance('participants')/root/item[name=${participant}]/konote_id",
        },
        {
            "type": "date",
            "name": "visit_date",
            "label": "Visit date",
            "required": "yes",
            "default": "today()",
        },
        {
            "type": "select_one visit_types",
            "name": "visit_type",
            "label": "Visit type",
            "required": "yes",
        },
        {
            "type": "text",
            "name": "observations",
            "label": "Observations",
            "hint": "What did you observe during this visit?",
            "required": "yes",
            "appearance": "multiline",
        },
        {
            "type": "select_one engagement_scale",
            "name": "engagement",
            "label": "Engagement observation",
            "hint": "How engaged was the participant during the visit?",
            "required": "no",
        },
        {
            "type": "select_one alliance_scale",
            "name": "alliance_rating",
            "label": "Alliance rating (optional)",
            "hint": "How would you rate the working relationship?",
            "required": "no",
        },
    ],
    "choices": [
        # Visit types — match KoNote interaction types
        {"list_name": "visit_types", "name": "home_visit", "label": "Home visit"},
        {"list_name": "visit_types", "name": "community", "label": "Community meeting"},
        {"list_name": "visit_types", "name": "phone", "label": "Phone call"},
        {"list_name": "visit_types", "name": "virtual", "label": "Virtual / video call"},

        # Engagement scale — matches KoNote's 6-point scale
        {"list_name": "engagement_scale", "name": "1", "label": "1 — Disengaged"},
        {"list_name": "engagement_scale", "name": "2", "label": "2 — Reluctant"},
        {"list_name": "engagement_scale", "name": "3", "label": "3 — Going through motions"},
        {"list_name": "engagement_scale", "name": "4", "label": "4 — Participating"},
        {"list_name": "engagement_scale", "name": "5", "label": "5 — Actively engaged"},
        {"list_name": "engagement_scale", "name": "6", "label": "6 — Fully invested"},

        # Alliance scale — matches KoNote's 1-5 Likert
        {"list_name": "alliance_scale", "name": "1", "label": "1 — Poor"},
        {"list_name": "alliance_scale", "name": "2", "label": "2 — Fair"},
        {"list_name": "alliance_scale", "name": "3", "label": "3 — Adequate"},
        {"list_name": "alliance_scale", "name": "4", "label": "4 — Good"},
        {"list_name": "alliance_scale", "name": "5", "label": "5 — Excellent"},
    ],
}


# ------------------------------------------------------------------
# Form 3: Circle Observation (Phase 3 — requires Circles Lite)
# ------------------------------------------------------------------
CIRCLE_OBSERVATION = {
    "settings": {
        "form_title": "Circle Observation",
        "form_id": "circle_observation",
        "version": "2026022401",
        "instance_name": "concat('Circle ', ${visit_date})",
    },
    "survey": [
        {
            "type": "select_one_from_file circles.csv",
            "name": "circle",
            "label": "Circle",
            "required": "yes",
        },
        {
            "type": "hidden",
            "name": "circle_konote_id",
            "label": "Circle KoNote ID",
            "calculation": "instance('circles')/root/item[name=${circle}]/konote_circle_id",
        },
        {
            "type": "date",
            "name": "visit_date",
            "label": "Visit date",
            "required": "yes",
            "default": "today()",
        },
        {
            "type": "select_multiple_from_file circle_members.csv",
            "name": "members_present",
            "label": "Members present",
            "choice_filter": "circle_id=${circle_konote_id}",
        },
        {
            "type": "text",
            "name": "observations",
            "label": "Observations",
            "hint": "What did you observe about the circle/family?",
            "required": "yes",
            "appearance": "multiline",
        },
        # Optional: record a new relationship
        {
            "type": "begin_group",
            "name": "new_relationship",
            "label": "New relationship observed (optional)",
            "appearance": "field-list",
        },
        {
            "type": "text",
            "name": "member_name",
            "label": "Person's name",
            "required": "no",
        },
        {
            "type": "text",
            "name": "relationship_label",
            "label": "Relationship (e.g., parent, uncle, caregiver)",
            "required": "no",
        },
        {
            "type": "end_group",
            "name": "new_relationship",
        },
    ],
}


# Registry of all forms
FORM_REGISTRY = {
    "session_attendance": SESSION_ATTENDANCE,
    "visit_note": VISIT_NOTE,
    "circle_observation": CIRCLE_OBSERVATION,
}
