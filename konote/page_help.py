"""Contextual page help content.

Maps URL names to plain-language help tips shown in the ? modal.
Each entry has:
- title: short label for the page
- description: one sentence explaining what this page is for
- tips: list of practical tips (what you can do here)
- help_section: anchor on /help/ for more detail (optional)
"""
from django.utils.translation import gettext_lazy as _


# Keys are Django URL names (from urls.py).
# Use tuples for tips so they're immutable and translatable.
PAGE_HELP = {
    # --- Home / Client list ---
    "client_list": {
        "title": _("Home"),
        "description": _("Your dashboard showing active participants, alerts, and recent activity."),
        "tips": [
            _("Use the search bar to find a participant by name or record ID."),
            _("Priority items show participants who need attention — overdue notes or active alerts."),
            _("Recently viewed gives you quick links to participants you've been working with."),
        ],
        "help_section": "getting-started",
    },
    # --- Client detail ---
    "client_detail": {
        "title": _("Participant File"),
        "description": _("Everything about this participant in one place — their plan, notes, events, and documents."),
        "tips": [
            _("Use the tabs to switch between notes, plans, events, and documents."),
            _("Click 'Quick note' to add a short progress note without leaving this page."),
            _("The status banner shows their current program enrolment and any active alerts."),
        ],
        "help_section": "files",
    },
    # --- Progress notes ---
    "note_list": {
        "title": _("Progress Notes"),
        "description": _("All progress notes for this participant, newest first."),
        "tips": [
            _("Click 'New note' to record a session or interaction."),
            _("Each note has two parts — your clinical observations and the participant's perspective."),
            _("Notes are linked to program enrolments, so they stay with the right program."),
        ],
        "help_section": "notes",
    },
    "note_create": {
        "title": _("New Progress Note"),
        "description": _("Record a session or interaction with this participant."),
        "tips": [
            _("Fill in the practitioner lens (your observations) and the participant lens (their perspective)."),
            _("Rate the working alliance if your agency uses alliance tracking."),
            _("You can record metric scores at the bottom to update outcome tracking."),
            _("Ctrl+S saves the form."),
        ],
        "help_section": "notes",
    },
    "note_detail": {
        "title": _("Progress Note"),
        "description": _("Viewing a completed progress note."),
        "tips": [
            _("If AI summaries are enabled, you can generate a summary of this note."),
            _("You can cancel (retract) a note if it was entered in error."),
        ],
        "help_section": "notes",
    },
    "quick_note_create": {
        "title": _("Quick Note"),
        "description": _("A short note for brief interactions — phone calls, check-ins, or quick updates."),
        "tips": [
            _("Quick notes are shorter than full progress notes — just a description and optional metrics."),
            _("Ctrl+S saves the form."),
        ],
        "help_section": "notes",
    },
    # --- Plans ---
    "plan_view": {
        "title": _("Outcome Plan"),
        "description": _("This participant's goals and the metrics tracking their progress."),
        "tips": [
            _("Goals are grouped into sections (life areas or themes)."),
            _("Click a metric to see the progress chart over time."),
            _("Add new goals using the button at the top — AI suggestions are available if enabled."),
        ],
        "help_section": "plans",
    },
    "goal_create": {
        "title": _("New Goal"),
        "description": _("Add a new goal to this participant's outcome plan."),
        "tips": [
            _("If AI suggestions are enabled, start typing and suggestions will appear."),
            _("Each goal gets one or more metrics to track progress over time."),
        ],
        "help_section": "plans",
    },
    "target_create": {
        "title": _("New Metric"),
        "description": _("Add a metric to track progress on a goal."),
        "tips": [
            _("Choose from your agency's metric library, or create a custom one."),
            _("Metrics are scored during progress notes — you don't need to enter scores separately."),
        ],
        "help_section": "plans",
    },
    # --- Events ---
    "event_list": {
        "title": _("Events"),
        "description": _("Significant events and alerts for this participant."),
        "tips": [
            _("Events record things that happened — incidents, milestones, referrals."),
            _("Alerts flag things that need follow-up — they stay visible until resolved."),
        ],
        "help_section": "events",
    },
    "meeting_list": {
        "title": _("Meetings"),
        "description": _("Upcoming and past meetings across all your participants."),
        "tips": [
            _("Meetings can be linked to participants or stand alone (like team meetings)."),
            _("Overdue meetings (past date, not completed) appear at the top."),
        ],
        "help_section": "events",
    },
    # --- Reports ---
    "client_analysis": {
        "title": _("Progress Analysis"),
        "description": _("Charts and summaries showing how this participant's metrics have changed over time."),
        "tips": [
            _("Each chart shows one metric — look for trends, not single data points."),
            _("You can export this as a PDF to share with the participant or their team."),
        ],
        "help_section": "reports",
    },
    "program_insights": {
        "title": _("Outcome Insights"),
        "description": _("Program-level view of how outcomes are tracking across all participants."),
        "tips": [
            _("Use the program filter to compare outcomes across different programs."),
            _("Distribution charts show how participants are spread across score ranges."),
        ],
        "help_section": "insights",
    },
    "generate_report": {
        "title": _("Generate Report"),
        "description": _("Create a formatted report using one of your agency's report templates."),
        "tips": [
            _("Choose a template, select the date range and programs, then preview before exporting."),
            _("Reports can be exported as Word documents or PDFs."),
        ],
        "help_section": "reports",
    },
    "executive_dashboard": {
        "title": _("Executive Dashboard"),
        "description": _("High-level summary of agency activity — participant counts, note volumes, and alerts."),
        "tips": [
            _("Use the date range and program filters to focus on specific time periods or programs."),
            _("You can export the dashboard data for board reports or funder updates."),
        ],
        "help_section": "reports",
    },
    # --- Communications ---
    "communication_log": {
        "title": _("Communication Log"),
        "description": _("Email and communication history for this participant."),
        "tips": [
            _("Use 'Quick log' to record a phone call or in-person conversation."),
            _("Emails sent through KoNote are automatically logged here."),
        ],
        "help_section": "files",
    },
    "my_messages": {
        "title": _("Messages"),
        "description": _("Staff messages assigned to you or your team."),
        "tips": [
            _("Unread messages show a badge in the navigation bar."),
            _("You can leave messages for other staff on any participant's file."),
        ],
        "help_section": "files",
    },
    # --- Client management ---
    "client_create": {
        "title": _("New Participant"),
        "description": _("Register a new participant in the system."),
        "tips": [
            _("Required fields are marked with an asterisk (*)."),
            _("After creating, you'll be taken to their file to set up their plan."),
        ],
        "help_section": "files",
    },
    "client_edit": {
        "title": _("Edit Participant"),
        "description": _("Update this participant's personal information."),
        "tips": [
            _("Changes are logged in the audit trail."),
            _("Ctrl+S saves the form."),
        ],
        "help_section": "files",
    },
    "client_discharge": {
        "title": _("Discharge"),
        "description": _("End this participant's active enrolment."),
        "tips": [
            _("You can add a discharge reason and closing notes."),
            _("Discharged participants can be re-enrolled later if needed."),
        ],
        "help_section": "files",
    },
    # --- Admin pages ---
    "settings_view": {
        "title": _("Settings"),
        "description": _("Agency-wide settings — terminology, features, branding, and system configuration."),
        "tips": [
            _("Changes to terminology update labels across the entire system."),
            _("Feature toggles let you enable or disable optional features like AI suggestions."),
        ],
        "help_section": "admin-settings-guide",
    },
    "user_list": {
        "title": _("User Management"),
        "description": _("Manage staff accounts, roles, and program assignments."),
        "tips": [
            _("Each user needs at least one program role to access participant files."),
            _("Admins can see all programs; other roles only see their assigned programs."),
        ],
        "help_section": "admin",
    },
    # --- CIDS ---
    "cids_dashboard": {
        "title": _("CIDS Dashboard"),
        "description": _("Common Impact Data Standard compliance — see how your data maps to CIDS fields."),
        "tips": [
            _("Green items are complete; yellow items need attention."),
            _("Click a section to see which fields need to be filled in."),
        ],
        "help_section": "reports",
    },
}


def get_page_help(request):
    """Return help content for the current page, or None."""
    match = getattr(request, "resolver_match", None)
    if not match:
        return None

    url_name = match.url_name or ""
    return PAGE_HELP.get(url_name)
