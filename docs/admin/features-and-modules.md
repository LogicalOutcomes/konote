# Features & Modules

KoNote is modular. Enable only the features your agency needs, and disable the rest to keep the interface clean.

---

## Enable/Disable Features

1. Click **gear icon** -> **Features**
2. Enable or disable modules as needed
3. Click the toggle button to see what will change before confirming

### Feature Reference

| Feature | What it does | Default |
|---------|--------------|---------|
| **Programs** | Organise services into separate programs with their own staff, templates, and metrics | On |
| **Custom Participant Fields** | Extra data fields on participant files (funding source, referral date, etc.) | Off |
| **Metric Alerts** | Notify staff when outcome metrics hit thresholds | Off |
| **Event Tracking** | Record intake, discharge, crisis, and other significant events | On |
| **Program Reports** | Generate formatted outcome reports for funders | Off |
| **Consent Requirement** | Require participant consent before notes (PIPEDA/PHIPA) | On |
| **Email Messaging** | Send email reminders and messages to participants (requires SMTP) | Off |
| **SMS Messaging** | Send text message reminders to participants (requires Twilio) | Off |
| **Portal Journal** | Participant portal -- private journal feature | On |
| **Portal Messaging** | Participant portal -- messages to worker feature | On |
| **Surveys** | Structured feedback forms with trigger rules and shareable links | Off |
| **Participant Portal** | Secure portal where participants view goals, progress, and journal | Off |
| **AI Assist** | AI-powered features like goal builder and narrative generation | Off |
| **Groups** | Group sessions and attendance tracking | On |
| **Quick Notes** | Lightweight contact logging (phone, text, email) | On |
| **Analysis Charts** | Progress visualisation charts on participant files | On |

Features can be toggled at any time without losing data. Disabling a feature hides it from the interface but preserves all associated records.

### Feature Dependency Map

Some features depend on or enhance others:

```
participant_portal
  +-- portal_journal
  +-- portal_messaging
  +-- surveys (portal survey section)

messaging_sms
  requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER

messaging_email
  requires: EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

surveys
  enhanced_by: participant_portal (portal survey fill)

program_reports
  enhanced_by: ai_assist (AI narrative generation)
```

---

## Create Programs

A program is a distinct service line your agency offers.

1. Click **gear icon** -> **Programs**
2. Click **+ New Program**
3. Enter name and description
4. Click **Create**

**Assign staff to programs:**
1. Click the program name
2. Select a user from the dropdown
3. Choose role: "Coordinator" (manages) or "Staff" (delivers services)
4. Click **Add**

---

## Set Up Plan Templates

Plan templates are reusable blueprints for participant outcome plans.

**Key concepts:**
- **Section** -- Broad category (Housing, Employment, Health)
- **Target** -- Specific goal within a section
- **Template** -- Collection of sections and targets

**Create a template:**
1. Click **gear icon** -> **Plan Templates**
2. Click **+ New Template**
3. Add sections and targets

**Example template:**
- **Housing**
  - Maintain stable housing for 3+ months
  - Develop independent living skills
- **Employment**
  - Enroll in or maintain employment/education
  - Achieve 80% attendance rate

Changes to templates don't affect existing participant plans.

---

## Manage Outcome Metrics

Metrics are standardised measurements attached to plan targets (e.g., "PHQ-9 Score", "Housing Stability"). KoNote ships with a built-in library, and you can add your own.

**Browse the metric library:**
1. Click **gear icon** -> **Metric Library**
2. Metrics are grouped by category (Mental Health, Housing, Employment, etc.)
3. Toggle the **Enabled** switch to make a metric available or unavailable for staff

**Review and customise metrics using CSV (recommended for initial setup):**

This workflow lets you review all metrics in Excel, decide which to enable, edit definitions, and push changes back -- without creating duplicates.

1. Go to **gear icon** -> **Metric Library**
2. Click **Export to CSV** -- this downloads a spreadsheet with every metric
3. Open the file in Excel. Each row has:

| Column | What it means |
|--------|---------------|
| **id** | System identifier -- don't change this (it's how KoNote matches rows back) |
| **name** | What staff see when recording outcomes |
| **definition** | How to score/measure it -- guides staff on consistent data entry |
| **category** | Grouping: mental_health, housing, employment, substance_use, youth, general, custom |
| **min_value / max_value** | Valid range (e.g., 0-27 for PHQ-9) |
| **unit** | Label for the value (score, days, %) |
| **is_enabled** | **yes** = available for use, **no** = hidden from staff |
| **status** | **active** or **deactivated** |

4. Make your changes:
   - Set `is_enabled` to **no** for metrics your organisation won't use
   - Edit `definition` to match your agency's scoring guidelines
   - Change `category` to reorganise how metrics are grouped
   - Add new rows at the bottom (leave the `id` column blank for new metrics)
5. Save the file as CSV
6. Go back to **Metric Library** -> click **Import from CSV**
7. Upload your edited file -- KoNote shows a preview:
   - Rows with an ID are marked **Update** (overwrites the existing metric)
   - Rows without an ID are marked **New** (creates a new metric)
8. Review the preview, then click **Import**

**Tips:**
- Don't delete the `id` column -- it prevents duplicates when re-importing
- You can repeat this workflow any time (export -> edit -> re-import)
- Deactivating a metric doesn't affect historical data already recorded
- All exports and imports are recorded in the audit log

**Add a single metric manually:**
1. Click **gear icon** -> **Metric Library** -> **Add Custom Metric**
2. Fill in name, definition, category, range, and unit
3. Click **Save**

---

## Set Up Progress Note Templates

Note templates define the structure for progress notes. When staff write a note, they see a dropdown labelled **"This note is for..."** with options like "Standard session" or "Crisis intervention." Each option is a template you create here.

**Default templates:** KoNote comes with six templates pre-configured:

| Template | Use case |
|----------|----------|
| **Standard session** | Regular participant meetings |
| **Brief check-in** | Quick touchpoints |
| **Phone/text contact** | Remote contact documentation |
| **Crisis intervention** | Safety concerns, urgent situations |
| **Intake assessment** | First meeting with new participants |
| **Case closing** | Discharge and case closure |

Staff can also select **"Freeform"** for unstructured notes without pre-defined sections.

**Create or edit templates:**

1. Click **Manage** -> **Note Templates** (or go to Settings -> Note Templates)
2. Click **+ New Template**
3. Enter a name (this appears in the "This note is for..." dropdown)
4. Add sections:
   - **Basic Text** -- free-text area for narrative notes
   - **Plan Targets** -- shows the participant's active plan targets with metric inputs
5. Set the sort order for each section
6. Click **Save**

**Example template structure:**

**Standard session**
- Session summary *(Basic Text)*
- Plan progress *(Plan Targets)*
- Next steps *(Basic Text)*

**Tips:**
- Keep template names short and action-oriented (staff see them in a dropdown)
- Include a "Plan progress" section (Plan Targets type) to capture outcome metrics
- Archive templates instead of deleting them to preserve historical data

**Note consent checkbox:** When staff create or edit a progress note, they see a checkbox labelled "We created this note together (this is recommended)." This checkbox is **optional by default** -- staff can save a note without ticking it. The checkbox encourages co-creation with participants but does not block note submission, because a mandatory tick can become a reflexive click that creates a false audit trail. If your agency's internal policy requires documented co-creation confirmation on every note, contact your KoNote administrator to discuss re-enabling this as a required field.

---

## Configure Custom Fields

Capture agency-specific information not in the standard participant form.

**Create a field group:**
1. Click **gear icon** -> **Custom Client Fields**
2. Click **+ New Field Group**
3. Enter title (e.g., "Funding & Referral")

**Add custom fields:**
1. Click **+ New Custom Field**
2. Configure:
   - **Name:** e.g., "Funding Source"
   - **Type:** Text, Number, Date, Dropdown, Checkbox
   - **Required:** Staff must fill in
   - **Sensitive:** Contains private information
   - **Choices:** (for dropdowns) "Government, Private, Foundation"

---

## Set Up Registration Forms

Registration forms let people sign up for your programs through a public web page -- no login required. You create a registration link, share it or embed it on your website, and submissions come into KoNote for your team to review.

### How It Works

1. **You create a registration link** tied to a specific program
2. **You share the link** (or embed it on your website as an iframe)
3. **Someone fills out the form** -- their information is saved and encrypted
4. **Your team reviews the submission** -- and can approve, reject, waitlist, or merge with an existing participant

When a submission is approved, KoNote automatically creates a new participant record and enrols them in the program.

### Create a Registration Link

1. Click **Manage** -> **Registration**
2. Click **+ New Registration Link**
3. Fill in:

| Field | What it does |
|-------|--------------|
| **Program** | Which program registrants will be enrolled in (required) |
| **Title** | Heading shown on the form (e.g., "Summer Program Registration") |
| **Description** | Instructions or welcome message shown above the form |
| **Field groups** | Which custom fields to include (optional -- basic name/email/phone are always shown) |
| **Auto-approve** | If checked, submissions create participants immediately without staff review |
| **Max registrations** | Capacity limit -- form closes when reached (leave blank for unlimited) |
| **Closes at** | Deadline -- form closes after this date (leave blank for no deadline) |

4. Click **Save**

You'll get a **public URL** and an **embed code** you can paste into your website.

**Tip:** Confidential programs cannot have registration links -- this is a safety feature.

### Sharing the Registration Link

**Direct link:** Copy the URL and share it by email, social media, or your website.

**Embed on a website:** Copy the iframe embed code and paste it into your website's HTML. The form will appear directly on your page.

### Reviewing Submissions

When someone submits a registration form (and auto-approve is off):

1. Click **Manage** -> **Submissions**
2. You'll see submissions organised by status: **Pending**, **Approved**, **Rejected**, **Waitlisted**
3. Click a submission to see the details

**For each submission, you can:**

| Action | What happens |
|--------|-------------|
| **Approve** | Creates a new participant record and enrols them in the program |
| **Merge** | Links the submission to an existing participant (avoids duplicates) |
| **Waitlist** | Parks the submission -- you can approve or reject it later |
| **Reject** | Marks it as rejected with a reason -- no participant is created |

**Duplicate detection:** KoNote automatically flags submissions that match an existing participant's email or name. This helps you avoid creating duplicates -- use the **Merge** option when a match is found.

### Auto-Approve vs. Manual Review

| Mode | Best for |
|------|----------|
| **Manual review** (default) | Programs where staff need to screen applicants, check eligibility, or manage capacity |
| **Auto-approve** | Open programs where anyone who registers should be enrolled immediately |

With auto-approve on, each submission instantly creates a participant record and enrols them. Staff can still see all submissions under **Admin -> Submissions**.

### Tips

- Each registration link is tied to **one program** -- create separate links for different programs
- Custom field groups let you collect additional information (demographics, referral source, etc.)
- Registration links can be deactivated without deleting them -- toggle **Is Active** off
- All submissions are encrypted -- personal information is protected the same way as participant records
- Every submission gets a unique reference number (e.g., REG-A1B2C3D4) shown on the confirmation page

---

## Suggestion Themes

KoNote automatically identifies recurring themes from participant suggestions captured in progress notes. This helps program managers and executives understand what participants are asking for and track how the agency responds.

### How It Works

1. **Staff capture suggestions** -- Every progress note includes a "Participant Suggestions" field. Staff record what participants suggest or request during sessions.
2. **Automatic theme linking** -- When a note is saved, KoNote checks the suggestion text against existing theme keywords. If a match is found, the note is automatically linked to that theme (Tier 1 automation).
3. **AI-generated themes** -- During Outcome Insights analysis, KoNote can identify new themes from unlinked suggestions using AI (Tier 2 automation, requires OpenRouter API key).
4. **Manual theme management** -- Program managers can also create themes manually and link suggestions to them.

### Managing Themes

1. Click **Manage** -> **Suggestions** to view all suggestion themes
2. Each theme shows: name, description, keywords for auto-linking, status, and linked notes count
3. Create new themes with **Add Theme** -- include keywords that will trigger automatic linking

### Theme Status Workflow

| Status | Meaning |
|--------|---------|
| **Open** | Theme identified but not yet acted on |
| **In Progress** | Agency is actively responding to this feedback |
| **Addressed** | Action has been taken; theme is resolved |
| **Won't Do** | Theme reviewed but agency decided not to act (with reason) |

### Executive Dashboard Integration

The executive dashboard shows the top suggestion themes per program, giving leadership visibility into what participants across the agency are asking for.

---

## Common Questions

### Q: Do staff need to fill all custom fields?
**A:** Only if marked "Required".

### Q: Does editing a template affect existing plans?
**A:** No. Templates only apply to new plans.

### Q: What if I delete a program?
**A:** You can't delete programs with active participants. Deactivate instead.

---

[Back to Admin Guide](index.md)
