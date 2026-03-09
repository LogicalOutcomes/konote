"""Contextual page help content.

Maps URL names to plain-language help tips shown in the ? modal.
Each entry has:
- title: short label for the page
- description: one sentence explaining what this page is for
- tips: list of practical tips (what you can do here)
- help_section: anchor on /help/ for more detail (optional)

Terminology placeholders ({client}, {client_plural}, {file}, {plan},
{progress_note}, etc.) are substituted at request time with the agency's
configured terms. This keeps help text consistent with the rest of the UI.
"""
from collections import defaultdict

from django.utils.translation import gettext_lazy as _


# Keys are Django URL names (from urls.py).
# Use {client}, {client_plural}, {file}, {plan}, {progress_note}, etc.
# for any term the agency can customise. These are replaced at request time.
PAGE_HELP = {
    # --- Home / Client list ---
    "client_list": {
        "title": _("Home"),
        "description": _("Your dashboard showing active {client_plural}, alerts, and recent activity."),
        "tips": [
            _("Use the search bar to find a {client} by name or record ID."),
            _("Priority items show {client_plural} who need attention — overdue notes or active alerts."),
            _("Recently viewed gives you quick links to {client_plural} you've been working with."),
        ],
        "help_section": "getting-started",
    },
    # --- Client detail ---
    "client_detail": {
        "title": _("{client} {file}"),
        "description": _("Everything about this {client} in one place — their {plan}, notes, events, and documents."),
        "tips": [
            _("Use the tabs to switch between notes, {plan}s, events, and documents."),
            _("Click 'Quick note' to add a short {progress_note} without leaving this page."),
            _("The status banner shows their current program enrolment and any active alerts."),
        ],
        "help_section": "files",
    },
    # --- Progress notes ---
    "note_list": {
        "title": _("{progress_note_plural}"),
        "description": _("All {progress_note_plural} for this {client}, newest first."),
        "tips": [
            _("Click 'New note' to record a session or interaction."),
            _("Each note has two parts — your clinical observations and the {client}'s perspective."),
            _("Notes are linked to program enrolments, so they stay with the right program."),
        ],
        "help_section": "notes",
    },
    "note_create": {
        "title": _("New {progress_note}"),
        "description": _("Record a session or interaction with this {client}."),
        "tips": [
            _("Fill in the practitioner lens (your observations) and the {client} lens (their perspective)."),
            _("Rate the working alliance if your agency uses alliance tracking."),
            _("You can record {metric} scores at the bottom to update outcome tracking."),
            _("Ctrl+S saves the form."),
        ],
        "help_section": "notes",
    },
    "note_detail": {
        "title": _("{progress_note}"),
        "description": _("Viewing a completed {progress_note}."),
        "tips": [
            _("If AI summaries are enabled, you can generate a summary of this note."),
            _("You can cancel (retract) a note if it was entered in error."),
        ],
        "help_section": "notes",
    },
    "quick_note_create": {
        "title": _("{quick_note}"),
        "description": _("A short note for brief interactions — phone calls, check-ins, or quick updates."),
        "tips": [
            _("{quick_note_plural} are shorter than full {progress_note_plural} — just a description and optional {metric_plural}."),
            _("Ctrl+S saves the form."),
        ],
        "help_section": "notes",
    },
    # --- Plans ---
    "plan_view": {
        "title": _("Outcome {plan}"),
        "description": _("This {client}'s goals and the {metric_plural} tracking their progress."),
        "tips": [
            _("Goals are grouped into {section_plural} (life areas or themes)."),
            _("Click a {metric} to see the progress chart over time."),
            _("Add new goals using the button at the top — AI suggestions are available if enabled."),
        ],
        "help_section": "plans",
    },
    "goal_create": {
        "title": _("New Goal"),
        "description": _("Add a new goal to this {client}'s outcome {plan}."),
        "tips": [
            _("If AI suggestions are enabled, start typing and suggestions will appear."),
            _("Each goal gets one or more {metric_plural} to track progress over time."),
        ],
        "help_section": "plans",
    },
    "target_create": {
        "title": _("New {metric}"),
        "description": _("Add a {metric} to track progress on a goal."),
        "tips": [
            _("Choose from your agency's {metric} library, or create a custom one."),
            _("{metric_plural} are scored during {progress_note_plural} — you don't need to enter scores separately."),
        ],
        "help_section": "plans",
    },
    # --- Events ---
    "event_list": {
        "title": _("{event_plural}"),
        "description": _("Significant {event_plural} and alerts for this {client}."),
        "tips": [
            _("{event_plural} record things that happened — incidents, milestones, referrals."),
            _("Alerts flag things that need follow-up — they stay visible until resolved."),
        ],
        "help_section": "events",
    },
    "event_create": {
        "title": _("New {event}"),
        "description": _("Record a significant {event} for this {client}."),
        "tips": [
            _("Choose a category that best describes what happened."),
            _("Add details in the description — this becomes part of the {client}'s record."),
        ],
        "help_section": "events",
    },
    "meeting_list": {
        "title": _("Meetings"),
        "description": _("Upcoming and past meetings across all your {client_plural}."),
        "tips": [
            _("Meetings can be linked to {client_plural} or stand alone (like team meetings)."),
            _("Overdue meetings (past date, not completed) appear at the top."),
        ],
        "help_section": "events",
    },
    "alert_create": {
        "title": _("New Alert"),
        "description": _("Create an alert that flags something needing follow-up for this {client}."),
        "tips": [
            _("Alerts stay visible on the {client}'s {file} and in priority lists until resolved."),
            _("Choose a severity level — high-severity alerts appear in the executive dashboard."),
        ],
        "help_section": "events",
    },
    # --- Reports ---
    "client_analysis": {
        "title": _("Progress Analysis"),
        "description": _("Charts and summaries showing how this {client}'s {metric_plural} have changed over time."),
        "tips": [
            _("Each chart shows one {metric} — look for trends, not single data points."),
            _("You can export this as a PDF to share with the {client} or their team."),
        ],
        "help_section": "reports",
    },
    "program_insights": {
        "title": _("Outcome Insights"),
        "description": _("Program-level view of how outcomes are tracking across all {client_plural}."),
        "tips": [
            _("Use the program filter to compare outcomes across different programs."),
            _("Distribution charts show how {client_plural} are spread across score ranges."),
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
        "description": _("High-level summary of agency activity — {client} counts, note volumes, and alerts."),
        "tips": [
            _("Use the date range and program filters to focus on specific time periods or programs."),
            _("You can export the dashboard data for board reports or funder updates."),
        ],
        "help_section": "reports",
    },
    "session_report": {
        "title": _("Sessions Report"),
        "description": _("See session counts and dates by {client} across your programs."),
        "tips": [
            _("Filter by program and date range to focus on a specific period."),
            _("Use this to check which {client_plural} haven't had recent sessions."),
        ],
        "help_section": "reports",
    },
    # --- Communications ---
    "communication_log": {
        "title": _("Communication Log"),
        "description": _("Email and communication history for this {client}."),
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
            _("You can leave messages for other staff on any {client}'s {file}."),
        ],
        "help_section": "files",
    },
    # --- Client management ---
    "client_create": {
        "title": _("New {client}"),
        "description": _("Register a new {client} in the system."),
        "tips": [
            _("Required fields are marked with an asterisk (*)."),
            _("After creating, you'll be taken to their {file} to set up their {plan}."),
        ],
        "help_section": "files",
    },
    "client_edit": {
        "title": _("Edit {client}"),
        "description": _("Update this {client}'s personal information."),
        "tips": [
            _("Changes are logged in the audit trail."),
            _("Ctrl+S saves the form."),
        ],
        "help_section": "files",
    },
    "client_discharge": {
        "title": _("Discharge"),
        "description": _("End this {client}'s active enrolment."),
        "tips": [
            _("You can add a discharge reason and closing notes."),
            _("Discharged {client_plural} can be re-enrolled later if needed."),
        ],
        "help_section": "files",
    },
    "client_transfer": {
        "title": _("Transfer"),
        "description": _("Move this {client} to a different program."),
        "tips": [
            _("Select the destination program — the {client}'s {file} and history stay intact."),
            _("The {client}'s {worker} assignment will be updated to match the new program."),
        ],
        "help_section": "files",
    },
    # --- Groups ---
    "group_list": {
        "title": _("{group_plural}"),
        "description": _("All active {group_plural} in your programs."),
        "tips": [
            _("Click a {group} to see its {member_plural}, {session_plural}, and attendance."),
            _("Use the program filter to see {group_plural} for a specific program."),
        ],
        "help_section": "groups-circles",
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
            _("Each user needs at least one program role to access {client} {file_plural}."),
            _("Admins can see all programs; other roles only see their assigned programs."),
        ],
        "help_section": "admin",
    },
    "audit_log_list": {
        "title": _("Audit Log"),
        "description": _("Record of all significant actions taken in the system."),
        "tips": [
            _("Use the filters to narrow by user, action type, or date range."),
            _("Audit logs are stored in a separate database and cannot be edited."),
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

# Default fallback tips shown on pages without specific help content.
DEFAULT_TIPS = [
    _("Use the search bar at the top to find a {client} by name or ID."),
    _("Press the Help link in the footer to open the full Help Guide."),
    _("Use your browser's back button or the navigation menu to return to the home page."),
]


def get_page_help(request, terms=None):
    """Return help content for the current page, with terminology substituted.

    Args:
        request: The current HttpRequest.
        terms: A dict-like object with terminology keys (client, plan, etc.).
               If None, no substitution is performed.

    Returns:
        A dict with title, description, tips, help_section — or a default
        fallback dict if no page-specific help exists.
    """
    match = getattr(request, "resolver_match", None)
    url_name = match.url_name if match else ""

    entry = PAGE_HELP.get(url_name)

    # Build substitution dict from terminology, with safe fallback
    subs = defaultdict(lambda: "???")
    if terms:
        # terms is a dict-like (AttrDict from terminology context processor)
        for key in (
            "client", "client_plural", "file", "file_plural",
            "plan", "plan_plural", "worker", "worker_plural",
            "section", "section_plural", "target", "target_plural",
            "metric", "metric_plural",
            "progress_note", "progress_note_plural",
            "quick_note", "quick_note_plural",
            "event", "event_plural",
            "group", "group_plural", "member", "member_plural",
            "session", "session_plural",
            "circle", "circle_plural",
            "resource", "resource_plural",
        ):
            val = terms.get(key) if hasattr(terms, "get") else getattr(terms, key, None)
            if val:
                subs[key] = str(val)

    def sub(text):
        """Apply terminology substitution to a translated string."""
        return str(text).format_map(subs)

    if entry:
        return {
            "title": sub(entry["title"]),
            "description": sub(entry["description"]),
            "tips": [sub(t) for t in entry["tips"]],
            "help_section": entry.get("help_section", ""),
        }

    # Default fallback for pages without specific help
    return {
        "title": "",
        "description": "",
        "tips": [sub(t) for t in DEFAULT_TIPS],
        "help_section": "",
        "is_default": True,
    }
