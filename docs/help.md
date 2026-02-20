# KoNote Help

Welcome to KoNote! This guide helps you find what you need quickly.

---

## Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| Find a client | [Searching for Clients](#searching-for-clients) |
| Write a progress note | [Progress Notes](#progress-notes) |
| Record an event or alert | [Events and Alerts](#events-and-alerts) |
| Leave a message for a case worker | [Staff Messaging](#staff-messaging) |
| Assign or fill in a survey | [Surveys](#surveys) |
| Transfer a client between programs | [Client Transfer](#client-transfer) |
| View or edit a client's plan | [Outcome Plans](#outcome-plans) |
| See progress charts | [Analysis and Reports](#analysis-and-reports) |
| See program patterns | [Outcome Insights](#outcome-insights) |
| Invite a participant to the portal | [Portal Staff Management](#portal-staff-management) |
| Review registration submissions | [Registration Forms](#registration-forms) |
| Change my password | [Account Settings](#account-settings) |
| Get admin help | [Administrator Tasks](#administrator-tasks) |

---

## Getting Started

### First Time Login

**If your agency uses Microsoft (Azure AD):**
1. Go to your KoNote web address
2. Click **Login with Azure AD**
3. Sign in with your work email and password

**If your agency uses local login:**
1. Go to your KoNote web address
2. Enter your username and password
3. Click **Login**

**Forgot your password?** Contact your supervisor or system administrator.

### Understanding the Home Page

After logging in, your home page shows:

| Section | What It Shows |
|---------|---------------|
| **Search bar** | Type a name or ID to find clients |
| **Stats row** | Active clients, alerts, clients needing attention |
| **Priority Items** | Clients with active alerts or no recent notes |
| **Recently Viewed** | Quick links to clients you've looked at recently |

**Priority Items** highlights clients who need attention:
- **Active alerts** — safety concerns or flags you should review
- **Needs attention** — no progress note recorded in 30+ days

---

## Searching for Clients

### Quick Search

1. Type a client's **name** or **record ID** in the search bar
2. Results appear as you type
3. Click a name to open their file

**Tip:** You can search by first name, last name, or the client's record ID.

### Using Filters

Need to narrow your results?

1. Click **Search filters** below the search bar
2. Choose from:
   - **Status** — Active, Inactive, or Discharged
   - **Program** — Filter by specific program
   - **Date range** — Created after/before certain dates
3. Results update automatically

### Viewing All Clients

Click **View All** to see a paginated list of all clients you have access to.

---

## Client Files

When you open a client's file, you'll see several tabs:

| Tab | What You'll Find |
|-----|------------------|
| **Info** | Basic information, program enrolments, custom fields, and staff messaging |
| **Plan** | Outcome plan with sections, targets, and metrics |
| **Notes** | Progress notes timeline |
| **History** | Events, meetings, and alerts |
| **Analysis** | Progress charts over time |

### Editing Client Information

1. Go to the **Info** tab
2. Click **Edit** next to the section you want to change
3. Make your changes
4. Click **Save**

**Note:** Some fields may be view-only depending on your role.

---

## Progress Notes

Progress notes document your interactions with clients. KoNote offers two types:

### Quick Notes

Use quick notes for brief check-ins or short updates.

1. Open the client's file
2. Go to the **Notes** tab
3. Click **+ Quick Note**
4. Type your note
5. Check **We created this note together**
6. Click **Save**

### Full Progress Notes

Use full progress notes for structured sessions where you're working on plan targets.

1. Open the client's file
2. Go to the **Notes** tab
3. Click **+ Progress Note**
4. Fill in:
   - **Session date** — defaults to today (change if documenting a past session)
   - **Target sections** — select which targets you worked on, add notes and metrics
   - **Summary** — optional overview of the session
5. **Capture their reflection** — ask the question shown and record their words
6. Check **We created this note together**
7. Click **Save Note**

**Tip:** You only need to fill in the targets you actually worked on. Leave others blank.

### Participant Reflection

At the end of each full progress note, you'll see a prompt to ask the participant:

> *"What's one thing you're taking away from today?"*

Record their response in their own words — even a short phrase is valuable. This isn't extra paperwork; it's a moment to help them process what you worked on together, and it puts their voice in the record.

**Tips:**
- Keep it brief — a sentence or two is enough
- Use their exact words, not your interpretation
- Make it conversational, not formal

### Recording Metrics

When writing a full progress note, you'll see metric fields under each target. Common types:

- **Scale ratings** (1–10) for things like housing stability or mood
- **Yes/No** checkboxes for milestone achievements
- **Text** for qualitative observations

Enter values for metrics you observed or discussed during the session.

### Backdating Notes

Documenting a session that happened earlier?

1. In the note form, change the **Session date** to the actual date
2. The note will appear in the timeline based on that date

### Cancelling a Note

Made a mistake? You can cancel a note within 24 hours:

1. Find the note in the Notes tab
2. Click **Cancel**
3. Enter a reason (required)
4. Confirm

The note remains visible but is marked as cancelled. After 24 hours, notes cannot be cancelled.

---

## Events and Alerts

### Events

Events record discrete occurrences that don't need a full note — intake, discharge, hospital visits, crises, etc.

**Add an event:**
1. Open the client's file
2. Go to the **Events** tab
3. Click **+ New Event**
4. Choose the **Event type**
5. Enter the **Date**
6. Add any **Notes**
7. Click **Save**

### Alerts

Alerts flag a client as needing attention. Use them for safety concerns or urgent follow-ups.

**Create an alert:**
1. Open the client's file
2. Go to the **Events** tab
3. Click **+ New Alert**
4. Describe the concern
5. Click **Save**

The client will appear in **Priority Items** on the home page until the alert is resolved.

**Resolve an alert:**
1. Find the alert in the History tab
2. Click **Resolve** or **Cancel Alert**
3. Add a resolution note
4. Save

---

## Staff Messaging

Staff messaging is for internal communication between staff members about a client. Clients do not see these messages.

### My Messages Page

Click **Messages** in the main navigation to see all your unread messages. Each message shows who left it, when, and which client it's about. Click **Mark as Read** to clear it.

**Unread badge:** A number badge appears next to **Messages** in the navigation when you have unread messages. It updates automatically as you read messages.

### Leaving a Message

1. Open the client's file
2. On the **Info** tab, click **Leave Message**
3. Choose a specific staff member from the dropdown, or leave blank for all case workers
4. Type your message
5. Click **Leave Message**

### Viewing Messages on a Client File

1. Open the client's file
2. On the **Info** tab, click **View Messages**
3. You'll see messages addressed to you or to "any case worker"

---

## Client Transfer

Transfer moves a client between programs without creating a duplicate record. Use it when someone graduates from one service and starts another, or when you need to adjust enrolments.

### Where to Find It

Open the client's file, click the **Actions** menu, then click **Transfer**.

### Who Can Do It

Only staff with the **client.transfer** permission (typically program managers and administrators).

### What Happens

- Check or uncheck programs to enrol or unenrol the client
- Set cross-program sharing consent if needed
- Add an optional reason (recorded in the audit log)
- You can only change programs you have access to — other enrolments remain untouched

---

## Surveys

If surveys are enabled for your agency, you can assign structured feedback forms to participants and enter responses on their behalf.

### Assigning a Survey

1. Open the participant's file → **Surveys** tab
2. Click **Assign Survey**
3. Choose a survey and optionally set a due date
4. Click **Assign**

Some surveys are assigned automatically through trigger rules — you don't need to assign those manually.

### Entering a Response

1. Open the participant's file → **Surveys** tab
2. Click the survey name under **Enter Survey on Behalf**
3. Fill in the answers (conditional sections show/hide based on your answers)
4. Click **Submit Response**

### Viewing Responses

Go to the participant's **Surveys** tab → **Completed Responses** → click **View**.

For the complete survey guide, see [Surveys](surveys.md).

---

## Portal Staff Management

If the participant portal feature is enabled, staff can invite participants to create a portal account and manage their access.

### Inviting a Participant

1. Open the client's file
2. On the **Info** tab, expand **Participant Portal**
3. Click **Invite to Portal**
4. Optionally set a **verification code** (shared verbally, not in writing)
5. Click **Create invite** — you'll get a link to share with the participant

The invite link expires after 7 days. You can create a new invite at any time.

### Managing Portal Access

From the client's **Info** tab under **Participant Portal**, click **Manage portal access** to:

- View the participant's account status (active or deactivated)
- **Reset MFA** if they're locked out of their authenticator
- **Revoke access** if the participant should no longer have portal access
- See invite history

---

## Meeting Reminders

If SMS or email messaging is enabled for your agency, you can send appointment reminders to participants.

### How Reminders Work

1. When scheduling a meeting, check **Send reminder to client** to send one automatically
2. For existing meetings, find the meeting in the **History** tab and click **Send Reminder**
3. A preview shows the exact message before it's sent — review it and click **Send**
4. The meeting card updates to show "Reminder sent"

### What Staff See

- A **Send Reminder** button appears on scheduled meetings (not on completed, cancelled, or no-show meetings)
- The button is disabled if the client hasn't consented to receiving messages
- Each meeting can have one reminder sent
- The reminder channel (SMS or email) is determined by the client's preferred contact method

---

## Registration Forms

Registration forms let people sign up for your programs through a public web page — no login required. When someone submits a form, their information comes into KoNote for review.

### How Registration Works

1. An administrator creates a **registration link** tied to a program
2. The link is shared or embedded on your agency's website
3. Someone fills out the form (name, email, phone, and any custom fields)
4. The submission appears under **Admin → Submissions** for review
5. Staff approve, reject, waitlist, or merge the submission

When approved, KoNote automatically creates a client record and enrols the person in the program.

**Auto-approve:** If the administrator turned on auto-approve for a link, submissions skip the review step — clients are created immediately.

### Reviewing Submissions

If your role allows you to review submissions:

1. Go to **Admin → Submissions**
2. Click the **Pending** tab to see new submissions
3. Click a submission to view the details

**You can:**

| Action | What it does |
|--------|-------------|
| **Approve** | Creates a new client and enrols them in the program |
| **Merge** | Connects the submission to an existing client instead of creating a duplicate |
| **Waitlist** | Parks the submission for later — you can approve or reject it later |
| **Reject** | Marks the submission as rejected (with a reason). No client is created |

**Duplicate detection:** KoNote highlights submissions that match an existing client's email or name. If a match is found, use **Merge** instead of Approve to avoid creating a duplicate record.

### Creating Registration Links (Administrators)

1. Go to **Admin → Registration**
2. Click **+ New Registration Link**
3. Choose a **program**, add a title and description
4. Optionally: add custom field groups, set a capacity limit, or set a deadline
5. Save — you'll get a shareable URL and an embed code for your website

For full setup details, see [Administering KoNote — Registration Forms](administering-KoNote.md#set-up-registration-forms).

---

## Outcome Plans

The **Plan** tab shows the client's outcome plan — their goals, how they're progressing, and what you're working on together.

### Understanding the Plan Structure

- **Sections** — Broad categories like "Housing", "Employment", "Health"
- **Targets** — Specific goals within each section
- **Metrics** — Measurable indicators attached to targets

### Viewing Target Details

1. Click a target name to expand it
2. View all notes and metric recordings for that target
3. See progress charts (if metrics have been recorded)

### Editing Plans

**Staff** can view plans but typically cannot edit them.

**Program managers** and **coordinators** can:
- Add new sections and targets
- Edit existing targets
- Assign metrics to targets
- View target revision history

If you need something updated in a plan, let your supervisor know.

---

## Analysis and Reports

### Viewing Progress Charts

1. Open the client's file
2. Go to the **Analysis** tab
3. View charts showing metric values over time

Charts automatically update when new metric values are recorded in progress notes.

### Outcome Insights

Outcome Insights helps you see patterns across your program — how participants are doing overall, what's changing, and what their own words reveal.

1. Click **Insights** in the main navigation
2. Choose a **Program** from the dropdown
3. Choose a **Time period** (3 months, 6 months, 12 months, or a custom range)
4. Click **Show Insights**

You'll see:

| Section | What It Shows |
|---------|---------------|
| **Progress Trend** | A chart showing how participant progress descriptors have changed over time (percentages) |
| **Progress Snapshot** | Distribution of current descriptors (e.g., "Good place", "Shifting", "Holding", "Harder") |
| **Engagement** | How participants are engaging in sessions |
| **What participants are saying** | Direct quotes from progress notes (anonymised, with goal context) |

**Data volume matters:** Insights become more reliable with more data. You need at least 20 notes across 3 months for trend analysis, and at least 50 notes for full insights.

**Privacy protection:** At program level, participant quotes only appear when 15 or more participants have notes in the selected period. This prevents anyone from being identified from their words.

#### AI Report Summaries (Optional)

If your administrator has enabled AI assistance, you can click **Draft report summary** to generate a narrative draft. This uses AI to summarise the patterns into a paragraph you can include in reports.

**Important:**
- Always review and edit the draft before using it — AI summaries are starting points, not final text
- The draft is labelled "AI-Generated" so it's clear it needs human review
- No participant names are sent to the AI — all identifying information is removed first

### Client-Level Insights

You can also see insights for an individual participant:

1. Open the participant's file
2. Go to the **Analysis** tab
3. Scroll down to the **Qualitative Insights** section

This shows the same trend chart and quotes, but for that one person. Unlike program-level insights, dates are shown and there's no minimum participant threshold.

### Exporting Data

**Program managers and admins** can export data:

- **Metric Export (CSV)** — Export metric data filtered by program, metrics, and date range
- **Client Data Export** — Download a client's complete data (for GDPR/privacy requests)
- **PDF Reports** — Generate printable progress reports

Find export options under **Reports** in the main navigation.

---

## Account Settings

### Changing Your Password

If your agency uses **local login**:
1. Contact your administrator to reset your password

If your agency uses **Azure AD**:
1. Use your organisation's standard password reset process

### Session Timeout

For security, KoNote automatically logs you out after a period of inactivity. The timer appears in the footer. Activity (clicking, typing) resets the timer.

---

## Keyboard Shortcuts

Speed up your work with these shortcuts:

| Shortcut | Action |
|----------|--------|
| `/` | Focus the search bar |
| `g` then `h` | Go to Home |
| `n` | New quick note (on client page) |
| `Ctrl+S` | Save current form |
| `Esc` | Close modal or cancel action |
| `?` | Show keyboard shortcuts |

---

## Understanding Roles

Your access depends on your assigned role:

| Role | What You Can Do |
|------|-----------------|
| **Front Desk** | View limited client info, update contact details, leave messages |
| **Staff** | Full client access, write notes, record events, leave and view messages |
| **Program Manager** | All staff abilities plus edit plans, manage team, transfer clients |
| **Administrator** | System settings, user management, all configuration |

**Note:** Administrators without a program assignment cannot see client data. This is a security feature.

---

## Administrator Tasks

If you're an administrator, you can configure KoNote through the **Admin** menu:

### Quick Links

| Task | Where to Find It |
|------|------------------|
| Create users | Admin → Invites |
| Manage programs | Admin → Programs |
| Set up metrics | Admin → Metrics |
| Create plan templates | Admin → Templates |
| Customise terminology | Admin → Settings → Terminology |
| Enable/disable features | Admin → Settings → Features |
| View audit logs | Admin → Audit Log |
| Create registration forms | Admin → Registration |
| Review registration submissions | Admin → Submissions |

### Customising Terminology

Change default terms to match your organisation's vocabulary:

1. Go to Admin → Settings → Terminology
2. Edit terms (e.g., "Client" → "Participant")
3. Click Save

Changes apply immediately throughout the app.

### Managing Users

**Invite a new user:**
1. Go to Admin → Invites
2. Click **+ New Invite**
3. Enter their email address
4. Assign programs and roles
5. Click **Send Invite**

**Deactivate a user:**
1. Go to Admin → Users
2. Find the user
3. Uncheck **Is Active**
4. Save

Deactivated users cannot log in, but their historical data is preserved.

### Setting Up Programs

A program is a distinct service line your agency offers.

1. Go to Admin → Programs
2. Click **+ New Program**
3. Enter name and description
4. Add staff members and assign roles
5. Save

### Viewing Audit Logs

Every significant action is logged for compliance.

1. Go to Admin → Audit Log
2. Filter by date, user, or action type
3. Export if needed for reporting

For detailed administrator documentation, see [Administering KoNote](administering-KoNote.md).

---

## Privacy and Security

### Your Data is Protected

KoNote protects sensitive information through:

- **Encryption** — Client names, birthdates, and sensitive fields are encrypted
- **Role-based access** — You only see clients in programs you're assigned to
- **Audit logging** — Every action is recorded for accountability
- **Automatic logout** — Sessions time out after inactivity

### Privacy Best Practices

- **Log out** when leaving your computer
- **Don't share** your login credentials
- **Report** any suspicious activity to your administrator
- **Follow** your agency's privacy policies

---

## Troubleshooting

### I can't log in

**Azure AD:** Check that your work email is registered with KoNote. Contact your administrator.

**Local login:** Confirm your credentials. If forgotten, ask your administrator to reset your password.

### I can't find a client

- Check your spelling
- Try searching by record ID instead of name
- Check filters — you may have a status filter active
- You can only see clients in programs you're assigned to

### I can't edit a client's plan

Only program managers and administrators can edit plans. If you need changes, let your supervisor know.

### I can't see the Admin menu

The Admin menu only appears for administrators. If you need admin access, contact your system administrator.

### My changes aren't saving

- Check for validation errors (red text near fields)
- Ensure you're clicking **Save**, not just closing the form
- Try refreshing the page and attempting again

### Charts aren't showing data

Charts require metric values recorded in progress notes. If no metrics have been recorded for a target, charts will be empty.

### The page timed out

For security, KoNote logs you out after inactivity. Log in again to continue. Your unsaved work may be lost.

---

## Getting More Help

### In-App Resources

- **Quick Reference Card** — See [Using KoNote](using-KoNote.md#quick-reference-card)
- **Keyboard shortcuts** — Press `?` anywhere in the app

### Documentation

- [Staff Training Guide](using-KoNote.md) — Daily tasks in detail
- [Administrator Guide](administering-KoNote.md) — Configuration and maintenance
- [Technical Documentation](technical-documentation.md) — For developers

### Contact Support

- **Password issues** — Contact your supervisor or administrator
- **Bug reports** — Report to your administrator
- **Feature requests** — Talk to your program coordinator

---

## Quick Reference

### Common Tasks

| I want to... | Do this... |
|--------------|------------|
| Find a client | Type name in search bar |
| Write a quick update | Actions menu → Quick Note |
| Document a session | Actions menu → Detailed Note |
| Record intake/discharge | Actions menu → Record Event |
| Flag a safety concern | Actions menu → New Alert |
| Schedule a meeting | Actions menu → Schedule Meeting |
| Leave a message for a case worker | Info tab → Leave Message |
| See my unread messages | Messages (main navigation) |
| Assign a survey | Client file → Surveys tab → Assign Survey |
| Enter a survey response | Client file → Surveys tab → Enter Survey on Behalf |
| Transfer a client | Actions menu → Transfer |
| Invite to the participant portal | Info tab → Participant Portal → Invite to Portal |
| See who needs attention | Check Priority Items on home page |
| View progress charts | Client file → Analysis tab |
| See program patterns | Insights (main navigation) |
| Review registrations | Admin → Submissions |
| Create a registration form | Admin → Registration |
| Create or manage surveys | Admin → Surveys |
| Change terminology | Admin → Settings → Terminology |
| Add a user | Admin → Invites |

### Understanding Status

| Client Status | Meaning |
|---------------|---------|
| **Active** | Currently receiving services |
| **Inactive** | Temporarily not receiving services |
| **Discharged** | Services completed or ended |

| Alert Status | Meaning |
|--------------|---------|
| **Active** | Requires attention |
| **Resolved** | Issue addressed |
| **Cancelled** | Created in error |

---

**KoNote** — Participant Outcome Management

Last updated: 2026-02-20
