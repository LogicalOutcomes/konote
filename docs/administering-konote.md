# Administering KoNote

This guide covers everything administrators need to configure, maintain, and secure their KoNote instance.

| I want to... | Go to... |
|--------------|----------|
| Set up my agency's instance | [Agency Configuration](#agency-configuration) |
| Choose which outcome metrics to use | [Manage Outcome Metrics](#manage-outcome-metrics) |
| Set up public registration forms | [Registration Forms](#set-up-registration-forms) |
| Create user accounts | [User Management](#user-management) |
| Let program managers manage their own config | [PM Administration](#program-manager-administration) |
| Manage participant portal access | [Staff Portal Management](#staff-portal-management) |
| Set up automated reminders | [Automated Reminders](#automated-reminders) |
| Get weekly export activity reports | [Weekly Export Summary](#weekly-export-summary-email) |
| Understand system health banners | [System Health Monitoring](#system-health-monitoring) |
| Set up a new instance from a config file | [Apply Setup Command](#apply-setup-command) |
| Back up my data | [Backup and Restore](#backup-and-restore) |
| Configure messaging and reminders | [Messaging Settings](#messaging-settings) |
| Set up report templates | [Report Template Setup](#report-template-setup) |
| Run security checks | [Security Operations](#security-operations) |

---

## Agency Configuration

After deployment, configure KoNote to match your organisation's needs. All setup is done through the web interface — no technical knowledge required.

**Time estimate:** 30–45 minutes for basic setup.

### Creating the First Admin Account

Every new KoNote instance starts with no users. You need to create the first admin from the command line before anyone can log in:

```bash
# Docker:
docker-compose exec web python manage.py createsuperuser

# Direct / Railway:
python manage.py createsuperuser
```

You'll be prompted for a **username** and **password**. This creates a user with full admin access (`is_admin=True`).

> **Demo mode shortcut:** If `DEMO_MODE=true`, the seed process automatically creates a `demo-admin` user with password `demo1234`. You can log in with that immediately and skip this step.

### First Login

**Azure AD (Office 365):**
1. Navigate to your KoNote URL
2. Click **Login with Azure AD**
3. Enter your work email and password
4. An admin must then assign your program roles through the web interface

**Local authentication:**
1. Navigate to your KoNote URL
2. Enter the username and password you created above

---

### Instance Settings

Control your organisation's branding and behaviour.

1. Click the **gear icon** (top-right) → **Instance Settings**
2. Configure:

| Field | What it does | Example |
|-------|--------------|---------|
| **Product Name** | Shown in header and titles | "Youth Housing — KoNote" |
| **Support Email** | Displayed in footer | support@agency.ca |
| **Logo URL** | Your organisation's logo | https://example.com/logo.png |
| **Date Format** | How dates appear | 2026-02-03 (ISO) |
| **Session Timeout** | Minutes before auto-logout | 30 |

3. Click **Save**

---

### Customise Terminology

Change default terms to match your organisation's vocabulary.

1. Click **gear icon** → **Terminology**
2. Edit terms as needed:
   - "Client" → "Participant", "Member", "Service User"
   - "Program" → "Service", "Initiative", "Stream"
   - "Target" → "Goal", "Objective", "Milestone"
3. Click **Save**

Changes apply immediately throughout the app.

---

### Enable/Disable Features

Toggle features based on your workflow.

1. Click **gear icon** → **Features**
2. Enable or disable:

| Feature | What it does |
|---------|--------------|
| **Programs** | Multiple service streams. Disable if single program. |
| **Custom Client Fields** | Extra data fields (funding source, referral date) |
| **Metric Alerts** | Notify staff when metrics hit thresholds |
| **Event Tracking** | Record intake, discharge, crisis, etc. |
| **Funder Report Exports** | Generate formatted reports for funders |
| **SMS Messaging** | Send text message reminders to clients (requires Twilio) |
| **Email Messaging** | Send email reminders to clients (requires SMTP) |

3. Click **Save**

Features can be toggled later without losing data.

---

### Create Programs

A program is a distinct service line your agency offers.

1. Click **gear icon** → **Programs**
2. Click **+ New Program**
3. Enter name and description
4. Click **Create**

**Assign staff to programs:**
1. Click the program name
2. Select a user from the dropdown
3. Choose role: "Coordinator" (manages) or "Staff" (delivers services)
4. Click **Add**

---

### Set Up Plan Templates

Plan templates are reusable blueprints for client outcome plans.

**Key concepts:**
- **Section** — Broad category (Housing, Employment, Health)
- **Target** — Specific goal within a section
- **Template** — Collection of sections and targets

**Create a template:**
1. Click **gear icon** → **Plan Templates**
2. Click **+ New Template**
3. Add sections and targets

**Example template:**
- **Housing**
  - Maintain stable housing for 3+ months
  - Develop independent living skills
- **Employment**
  - Enroll in or maintain employment/education
  - Achieve 80% attendance rate

Changes to templates don't affect existing client plans.

---

### Manage Outcome Metrics

Metrics are standardised measurements attached to plan targets (e.g., "PHQ-9 Score", "Housing Stability"). KoNote ships with a built-in library, and you can add your own.

**Browse the metric library:**
1. Click **gear icon** → **Metric Library**
2. Metrics are grouped by category (Mental Health, Housing, Employment, etc.)
3. Toggle the **Enabled** switch to make a metric available or unavailable for staff

**Review and customise metrics using CSV (recommended for initial setup):**

This workflow lets you review all metrics in Excel, decide which to enable, edit definitions, and push changes back — without creating duplicates.

1. Go to **gear icon** → **Metric Library**
2. Click **Export to CSV** — this downloads a spreadsheet with every metric
3. Open the file in Excel. Each row has:

| Column | What it means |
|--------|---------------|
| **id** | System identifier — don't change this (it's how KoNote matches rows back) |
| **name** | What staff see when recording outcomes |
| **definition** | How to score/measure it — guides staff on consistent data entry |
| **category** | Grouping: mental_health, housing, employment, substance_use, youth, general, custom |
| **min_value / max_value** | Valid range (e.g., 0–27 for PHQ-9) |
| **unit** | Label for the value (score, days, %) |
| **is_enabled** | **yes** = available for use, **no** = hidden from staff |
| **status** | **active** or **deactivated** |

4. Make your changes:
   - Set `is_enabled` to **no** for metrics your organisation won't use
   - Edit `definition` to match your agency's scoring guidelines
   - Change `category` to reorganise how metrics are grouped
   - Add new rows at the bottom (leave the `id` column blank for new metrics)
5. Save the file as CSV
6. Go back to **Metric Library** → click **Import from CSV**
7. Upload your edited file — KoNote shows a preview:
   - Rows with an ID are marked **Update** (overwrites the existing metric)
   - Rows without an ID are marked **New** (creates a new metric)
8. Review the preview, then click **Import**

**Tips:**
- Don't delete the `id` column — it prevents duplicates when re-importing
- You can repeat this workflow any time (export → edit → re-import)
- Deactivating a metric doesn't affect historical data already recorded
- All exports and imports are recorded in the audit log

**Add a single metric manually:**
1. Click **gear icon** → **Metric Library** → **Add Custom Metric**
2. Fill in name, definition, category, range, and unit
3. Click **Save**

---

### Set Up Progress Note Templates

Note templates define the structure for progress notes. When staff write a note, they see a dropdown labelled **"This note is for..."** with options like "Standard session" or "Crisis intervention." Each option is a template you create here.

**Default templates:** KoNote comes with six templates pre-configured:

| Template | Use case |
|----------|----------|
| **Standard session** | Regular client meetings |
| **Brief check-in** | Quick touchpoints |
| **Phone/text contact** | Remote contact documentation |
| **Crisis intervention** | Safety concerns, urgent situations |
| **Intake assessment** | First meeting with new clients |
| **Case closing** | Discharge and case closure |

Staff can also select **"Freeform"** for unstructured notes without pre-defined sections.

**Create or edit templates:**

1. Click **Admin** → **Note Templates** (or go to Settings → Note Templates)
2. Click **+ New Template**
3. Enter a name (this appears in the "This note is for..." dropdown)
4. Add sections:
   - **Basic Text** — free-text area for narrative notes
   - **Plan Targets** — shows the client's active plan targets with metric inputs
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

**Note consent checkbox:** When staff create or edit a progress note, they see a checkbox labelled "We created this note together (this is recommended)." This checkbox is **optional by default** — staff can save a note without ticking it. The checkbox encourages co-creation with participants but does not block note submission, because a mandatory tick can become a reflexive click that creates a false audit trail. If your agency's internal policy requires documented co-creation confirmation on every note, contact your KoNote administrator to discuss re-enabling this as a required field.

---

### Configure Custom Fields

Capture agency-specific information not in the standard client form.

**Create a field group:**
1. Click **gear icon** → **Custom Client Fields**
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

### Messaging Settings

KoNote can log communications and optionally send SMS or email reminders to clients.

**Two modes:**

| Mode | What it does |
|------|--------------|
| **Record-keeping only** (default) | Staff log phone calls, emails, and texts manually. No messages are actually sent. |
| **Active messaging** | Staff can send SMS and email reminders to clients who have consented. |

**To configure messaging:**

1. Click **gear icon** → **Features**
2. Enable **SMS Messaging** and/or **Email Messaging**
3. Click **gear icon** → **Instance Settings** → **Messaging**
4. Choose a messaging profile: **Record keeping** or **Active**

**Safety-First mode:** If enabled, this blocks ALL outbound messages regardless of other settings. Use this during setup and testing to make sure no real messages go out while you're configuring things.

**SMS setup:** Requires a Twilio account. Add the following to your environment variables:

| Variable | What it is |
|----------|------------|
| `TWILIO_ACCOUNT_SID` | Your Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | Your Twilio authentication token |
| `TWILIO_FROM_NUMBER` | The phone number messages are sent from |

**Email setup:** Requires SMTP configuration. Add the following to your environment variables:

| Variable | What it is |
|----------|------------|
| `EMAIL_HOST` | Your mail server address |
| `EMAIL_PORT` | Mail server port (typically 587 for TLS) |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |
| `DEFAULT_FROM_EMAIL` | The "from" address on outgoing emails |

See `.env.example` for details and example values.

**Export notification recipients:** When someone exports a report containing individual participant data, KoNote sends a notification email. By default this goes to all system administrators. To send it to specific people instead (e.g. a privacy officer or ED), set:

| Variable | What it is |
|----------|------------|
| `EXPORT_NOTIFICATION_EMAILS` | Comma-separated email addresses (e.g. `privacy@agency.ca,ed@agency.ca`) |

If this variable is not set, notifications fall back to all active admin users.

**Health warnings:** If SMS or email delivery fails repeatedly, staff see a warning banner on the Meetings page. Admins receive an email alert after 3 or more consecutive failures.

---

### Calendar Feed Token Management

Staff can subscribe to their KoNote meetings in external calendar apps such as Outlook, Google Calendar, or Apple Calendar.

**How it works:**
- Each staff member generates their own feed URL from **Meetings** → **Calendar Feed Settings**
- Feed tokens are private — each user's feed only shows meetings where they are an attendee
- **Privacy:** Calendar entries display initials and record ID only (no full names, phone numbers, or email addresses)
- If a staff member leaves, deactivating their user account also invalidates their calendar feed token

**No admin action is needed for day-to-day management** — staff self-serve. You only need to be aware that deactivating a user also cuts off their calendar feed.

---

### Report Template Setup

Report templates let you customise how demographic breakdowns appear in reports.

**To create a report template:**

1. Click **Admin** → **Report Templates**
2. Click **Upload CSV** — download the sample CSV template first if needed
3. The CSV defines demographic dimensions: age bins, custom field categories, and merged categories
4. Preview the profile, then confirm to save
5. Link programs to the report template

When executives export reports, they can select a report template to use custom demographic breakdowns instead of the defaults.

**Small-cell suppression:** If any demographic group has fewer than 5 clients, the count is suppressed (shown as "<5") to prevent identification of individuals. This is standard practice for Canadian funders.

---

### Set Up Registration Forms

Registration forms let people sign up for your programs through a public web page — no login required. You create a registration link, share it or embed it on your website, and submissions come into KoNote for your team to review.

#### How It Works

1. **You create a registration link** tied to a specific program
2. **You share the link** (or embed it on your website as an iframe)
3. **Someone fills out the form** — their information is saved and encrypted
4. **Your team reviews the submission** — and can approve, reject, waitlist, or merge with an existing client

When a submission is approved, KoNote automatically creates a new client record and enrols them in the program.

#### Create a Registration Link

1. Click **Admin** → **Registration**
2. Click **+ New Registration Link**
3. Fill in:

| Field | What it does |
|-------|--------------|
| **Program** | Which program registrants will be enrolled in (required) |
| **Title** | Heading shown on the form (e.g., "Summer Program Registration") |
| **Description** | Instructions or welcome message shown above the form |
| **Field groups** | Which custom fields to include (optional — basic name/email/phone are always shown) |
| **Auto-approve** | If checked, submissions create clients immediately without staff review |
| **Max registrations** | Capacity limit — form closes when reached (leave blank for unlimited) |
| **Closes at** | Deadline — form closes after this date (leave blank for no deadline) |

4. Click **Save**

You'll get a **public URL** (e.g., `https://yoursite.com/register/abc123/`) and an **embed code** you can paste into your website.

**Tip:** Confidential programs cannot have registration links — this is a safety feature.

#### Sharing the Registration Link

**Direct link:** Copy the URL and share it by email, social media, or your website.

**Embed on a website:** Copy the iframe embed code and paste it into your website's HTML. The form will appear directly on your page.

#### Reviewing Submissions

When someone submits a registration form (and auto-approve is off):

1. Click **Admin** → **Submissions**
2. You'll see submissions organised by status: **Pending**, **Approved**, **Rejected**, **Waitlisted**
3. Click a submission to see the details

**For each submission, you can:**

| Action | What happens |
|--------|-------------|
| **Approve** | Creates a new client record and enrols them in the program |
| **Merge** | Links the submission to an existing client (avoids duplicates) |
| **Waitlist** | Parks the submission — you can approve or reject it later |
| **Reject** | Marks it as rejected with a reason — no client is created |

**Duplicate detection:** KoNote automatically flags submissions that match an existing client's email or name. This helps you avoid creating duplicates — use the **Merge** option when a match is found.

#### Auto-Approve vs. Manual Review

| Mode | Best for |
|------|----------|
| **Manual review** (default) | Programs where staff need to screen applicants, check eligibility, or manage capacity |
| **Auto-approve** | Open programs where anyone who registers should be enrolled immediately |

With auto-approve on, each submission instantly creates a client record and enrols them. Staff can still see all submissions under **Admin → Submissions**.

#### Tips

- Each registration link is tied to **one program** — create separate links for different programs
- Custom field groups let you collect additional information (demographics, referral source, etc.)
- Registration links can be deactivated without deleting them — toggle **Is Active** off
- All submissions are encrypted — personal information is protected the same way as client records
- Every submission gets a unique reference number (e.g., REG-A1B2C3D4) shown on the confirmation page

---

## User Management

There are three ways to create user accounts, depending on the situation:

| Method | Best for | How it works |
|--------|----------|-------------|
| **Invite link** (recommended) | Onboarding new staff | Admin creates a link; the new person sets up their own username and password |
| **Direct creation** | Quick setup, temporary accounts | Admin fills in all details including password |
| **Azure AD SSO** | Organisations using Microsoft 365 | Users are created automatically on first login |

### Invite a New User (Recommended)

Invite links are the easiest way to onboard staff. The new person chooses their own username and password.

1. Click **gear icon** → **User Management**
2. Click **Invite User**
3. Choose:
   - **Role** — front desk, staff, program manager, executive, or admin
   - **Programs** — which programs they'll have access to
   - **Link expiry** — how many days the invite is valid (default: 7)
4. Click **Create Invite**
5. Copy the generated link and send it to the new person

When they open the link, they'll set up their display name, username, and password. They're logged in immediately with the correct role and program access.

> **Tip:** Each invite link can only be used once. If it expires or the person needs a new one, create another invite.

### Create a User Directly

For quick setup when you want to control the credentials:

1. Click **gear icon** → **User Management**
2. Click **+ New User**
3. Fill in:
   - **Display Name:** Full name (shown in reports)
   - **Username:** (local auth) Login name
   - **Email:** Work email
   - **Password:** (local auth) Temporary password
   - **Is Admin:** Check for configuration access
4. Click **Create**

### User Roles

| Role | Can do |
|------|--------|
| **Admin** | All settings, user management, templates |
| **Program Manager** | Program-level management |
| **Staff** | Enter data, write notes, view clients in assigned programs |
| **Front Desk** | Limited client info, basic data entry |

### Per-Program Role Assignments

A single user can hold **different roles in different programs**. This is common in small agencies where one person wears multiple hats.

**Examples:**
- Sarah is **Program Manager** in "Youth Housing" but delivers direct services as **Staff** in "Employment Support"
- David works the front desk for Drop-In Centre (**Front Desk**) but does casework in Mental Health (**Staff**)

**When to use this:**
- A senior staff member oversees one program but facilitates groups or sees clients in another
- A front-desk worker also does casework in a specific program
- Someone is covering temporarily in a different capacity

**How it works:**
- Each program assignment has its own role — the system checks the role for the specific program being accessed
- When viewing a client enrolled in multiple programs, the user's **highest** role across those programs applies
- The user's current role is shown as a badge in the navigation bar

**To manage per-program roles:**
1. Go to **User Management**
2. Click **Roles** next to the user's name
3. Use the table to see current program assignments
4. Use the form below the table to add a new program role
5. Click **Remove** to revoke access to a specific program

> **Tip:** When someone manages one program but personally runs groups in another, assign them as Program Manager in the first and Staff in the second. This gives them management tools where they need them and direct-service access where they're delivering services.

### Deactivate Users

When someone leaves:
1. Go to **User Management**
2. Click user → **Edit**
3. Uncheck **Is Active**
4. Click **Save**

They can no longer log in, but historical data is preserved.

---

## Backup and Restore

KoNote stores data in **two PostgreSQL databases**:
- **Main database** — clients, programs, plans, notes
- **Audit database** — immutable log of every change

### Critical: The Encryption Key

**If you lose `FIELD_ENCRYPTION_KEY`, all encrypted client data is permanently unrecoverable.**

Store it separately from database backups:
- Password manager (1Password, Bitwarden)
- Azure Key Vault
- Encrypted file with restricted access

**Never store it:**
- In the same location as database backups
- In version control (Git)
- In plain text on shared drives

---

### Manual Backup

**Docker Compose:**
```bash
# Main database
docker compose exec db pg_dump -U konote konote > backup_main_$(date +%Y-%m-%d).sql

# Audit database
docker compose exec audit_db pg_dump -U audit_writer konote_audit > backup_audit_$(date +%Y-%m-%d).sql
```

**Plain PostgreSQL:**
```bash
pg_dump -h hostname -U konote -d konote > backup_main_$(date +%Y-%m-%d).sql
pg_dump -h hostname -U audit_writer -d konote_audit > backup_audit_$(date +%Y-%m-%d).sql
```

### Automated Backups

**Windows Task Scheduler:**

Save as `C:\KoNote\backup_KoNote.ps1`:

```powershell
$BackupDir = "C:\Backups\KoNote"
$KoNoteDir = "C:\KoNote\KoNote-web"
$Date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir -Force }

Set-Location $KoNoteDir

# Main database
docker compose exec -T db pg_dump -U konote konote | Out-File -FilePath "$BackupDir\backup_main_$Date.sql" -Encoding utf8

# Audit database
docker compose exec -T audit_db pg_dump -U audit_writer konote_audit | Out-File -FilePath "$BackupDir\backup_audit_$Date.sql" -Encoding utf8

# Clean up backups older than 30 days
Get-ChildItem -Path $BackupDir -Filter "backup_*.sql" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force
```

Schedule via Task Scheduler to run daily at 2:00 AM.

**Linux/Mac Cron:**

Save as `/home/user/backup_KoNote.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/KoNote"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p "$BACKUP_DIR"

docker compose -f /path/to/KoNote-web/docker-compose.yml exec -T db pg_dump -U konote konote > "$BACKUP_DIR/backup_main_$DATE.sql"
docker compose -f /path/to/KoNote-web/docker-compose.yml exec -T audit_db pg_dump -U audit_writer konote_audit > "$BACKUP_DIR/backup_audit_$DATE.sql"

# Clean up old backups
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +30 -delete
```

Add to crontab: `0 2 * * * /home/user/backup_KoNote.sh`

### Cloud Provider Backups

- **Railway:** Automatic daily backups (7 days retention). Restore via dashboard.
- **Azure:** Automatic backups. Configure retention in PostgreSQL server settings.
- **Elestio:** Configure via dashboard or use managed PostgreSQL.

### Restore from Backup

**Docker Compose:**
```bash
# Stop containers
docker compose down

# Remove old volumes (WARNING: deletes current data)
docker volume rm KoNote-web_pgdata KoNote-web_audit_pgdata

# Start fresh containers
docker compose up -d

# Wait 10 seconds, then restore
docker compose exec -T db psql -U konote konote < backup_main_2026-02-03.sql
docker compose exec -T audit_db psql -U audit_writer konote_audit < backup_audit_2026-02-03.sql
```

### Backup Retention Policy

| Type | Frequency | Retention |
|------|-----------|-----------|
| Daily | Every night | 30 days |
| Weekly | Every Monday | 90 days |
| Monthly | First of month | 1 year |

---

## Security Operations

### Quick Reference

| Task | Command |
|------|---------|
| Basic check | `python manage.py check` |
| Deployment check | `python manage.py check --deploy` |
| Security audit | `python manage.py security_audit` |
| Run security tests | `pytest tests/test_security.py tests/test_rbac.py -v` |

---

### Security Checks

KoNote runs security checks automatically. You can also run them explicitly:

```bash
python manage.py check --deploy
```

**Check IDs:**

| ID | Severity | What It Checks |
|----|----------|----------------|
| `KoNote.E001` | Error | Encryption key exists and valid |
| `KoNote.E002` | Error | Security middleware loaded |
| `KoNote.W001` | Warning | DEBUG=True in production |
| `KoNote.W002` | Warning | Session cookies not secure |
| `KoNote.W003` | Warning | CSRF cookies not secure |

Errors prevent server start. Warnings indicate security gaps.

---

### Security Audit

For deeper analysis:

```bash
python manage.py security_audit
```

This checks encryption, access controls, audit logging, and configuration.

**Categories:**
- `ENC` — Encryption (key validity, ciphertext verification)
- `RBAC` — Role-based access control
- `AUD` — Audit logging
- `CFG` — Configuration (DEBUG, cookies, middleware)

---

### Audit Logging

Every significant action is logged to a separate audit database.

**What gets logged:**
- Login/Logout (user, timestamp, IP, success/failure)
- Client views (who viewed which client)
- Create/Update/Delete (what changed, old/new values)
- Exports (who exported what)
- Admin actions (settings changes, user management)

**View audit logs:**
1. Log in as Admin
2. Click **Admin** → **Audit Logs**
3. Filter by date, user, or action type

**Query audit database directly:**
```sql
SELECT event_timestamp, user_display, action, resource_type
FROM audit_auditlog
ORDER BY event_timestamp DESC
LIMIT 20;
```

---

### Encryption Key Management

`FIELD_ENCRYPTION_KEY` encrypts all PII:
- Client names (first, middle, last, preferred)
- Email addresses
- Phone numbers
- Dates of birth
- Sensitive custom fields

**Rotating the key:**

```bash
# 1. Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Rotate (re-encrypts all data)
python manage.py rotate_encryption_key --old-key="OLD" --new-key="NEW"

# 3. Update .env with new key
# 4. Restart application
# 5. Verify it works
# 6. Securely delete old key
```

**Rotation schedule:**
- Every 90 days (baseline)
- When staff with key access leave (immediately)
- After suspected security incident (immediately)

---

### Pre-Deployment Checklist

**Required:**
- [ ] `FIELD_ENCRYPTION_KEY` set to unique generated key
- [ ] `SECRET_KEY` set to unique generated key
- [ ] `DEBUG=False`
- [ ] `python manage.py check --deploy` passes

**Strongly recommended:**
- [ ] `SESSION_COOKIE_SECURE=True` (requires HTTPS)
- [ ] `CSRF_COOKIE_SECURE=True` (requires HTTPS)
- [ ] HTTPS configured
- [ ] Encryption key backed up separately from database
- [ ] All test users removed

---

### Incident Response

**Suspected data breach:**
1. Rotate encryption key immediately
2. Rotate SECRET_KEY (invalidates all sessions)
3. Review audit logs for unauthorized access
4. Document timeline
5. Notify affected parties per PIPEDA/GDPR (typically within 72 hours)

**Lost encryption key:**
- Encrypted PII fields are **permanently unrecoverable**
- Non-PII data (notes, metrics) remains accessible
- Consider this a data loss incident for compliance

**Suspicious login activity:**
```sql
SELECT event_timestamp, ip_address, metadata
FROM audit_auditlog
WHERE action = 'login_failed'
ORDER BY event_timestamp DESC;
```

---

## Data Retention

### Why Clients Can't Be Deleted (by Default)

KoNote intentionally **does not allow deleting clients through normal use**. This is a safety feature, not a limitation.

**Why this matters:**

| Concern | How KoNote handles it |
|---------|----------------------|
| Accidental deletion | Not possible — there is no delete button in normal workflows |
| Audit trail | Client history stays intact for compliance |
| Funder reporting | Historical data remains available for reporting |
| Data recovery | No need to restore backups for "oops" moments |

**Instead of deleting, use these approaches:**

| Scenario | What to do |
|----------|------------|
| Client leaves program | **Discharge** them — status changes to "Discharged" |
| Client no longer active | Set status to **"Inactive"** |
| Entered by mistake | Mark as "Inactive" and add a note explaining the error |
| Client requests data deletion (PIPEDA/GDPR) | Use the **Erase Client Data** workflow on the client detail page. Requires multi-PM approval. See `docs/security-operations.md#erasure-workflow-security`. |

Discharged and inactive clients:
- Do not appear in active client lists
- Remain searchable for historical reference
- Keep all notes, plans, and events intact
- Can be reactivated if the client returns

**Exception — legally required erasure:** For PIPEDA/GDPR right-to-erasure requests, KoNote provides a formal erasure workflow. This requires approval from all program managers for the client's enrolled programs, permanently deletes the client's data, and preserves an audit record with record counts only (no PII). See `docs/security-operations.md#erasure-workflow-security` for the full state machine and invariants.

---

### GDPR/PIPEDA Right to Erasure

Some privacy regulations require the ability to permanently delete personal data upon request.

**How it works:** Any staff member can request erasure from a client's detail page. The request then requires approval from a program manager in each of the client's enrolled programs. Once all approvals are received, the client's data is permanently deleted and an audit record is preserved.

**Steps:**
1. Navigate to the client's detail page and click **Erase Client Data**
2. Select a reason category and provide details (do not include client names)
3. Submit the request — program managers are notified by email
4. Each relevant program manager reviews and approves or rejects
5. Once all approvals are received, the data is permanently erased

**Important:** This action cannot be undone. Recovery requires a database backup. All erasure requests, approvals, and deletions are logged in the audit trail for PIPEDA compliance.

---

## Program Manager Administration

Program managers can now manage configuration for their own programs without needing a full system administrator. This reduces the administrative burden on admins and lets PMs customise their program workflows independently.

### What PMs Can Manage

| Area | What they can do | Where to find it |
|------|-----------------|------------------|
| **Plan templates** | Create, edit, and delete plan templates for their program | Admin → Plan Templates |
| **Note templates** | Create, edit, and delete progress note templates for their program | Admin → Note Templates |
| **Event types** | Create, edit, and delete event types for their program | Admin → Event Types |
| **Outcome metrics** | Create, edit, enable/disable metrics for their program | Admin → Metric Library |
| **Registration links** | Create and manage public registration links for their program | Admin → Registration |
| **Team members** | View and manage staff assignments within their program | User Management → Roles |

### How Scoping Works

- PMs see **their own program's items** plus **global items** (created by admins) in read-only mode
- PMs can only **edit or delete items that belong to their program** — global templates and metrics created by administrators are read-only for PMs
- When a PM creates a new template or metric, it is automatically assigned to their program (if they manage only one program)
- If a PM manages multiple programs, they choose which program to assign the new item to
- PMs **cannot** change system-wide settings, terminology, feature toggles, or create other PM/admin accounts

### What Admins Still Control

These tasks remain admin-only:

- Instance settings (product name, logo, support email)
- Terminology customisation
- Feature toggles (enabling/disabling modules)
- Custom client field definitions
- Report templates
- User management (creating admins, executives, or PMs)
- Merging duplicate clients
- Secure export link management

> **Tip:** If a program manager needs a global template modified, they should ask an admin. PMs can create a program-specific copy of a global template and customise that instead.

---

## Staff Portal Management

The participant portal gives clients a secure way to view their goals, progress, and journal entries. Staff manage portal access from the client detail page.

### Inviting a Participant to the Portal

1. Navigate to the participant's client detail page
2. Click **Portal** → **Create Invite**
3. Optionally set a **verbal code** — an extra verification step the participant must enter when accepting the invite (useful when you want to confirm identity in person or by phone)
4. Click **Create Invite**
5. Copy the generated invite link and share it with the participant

The invite link is valid for **7 days** and can only be used once. When the participant opens the link, they create their own email, display name, and password. They are then guided through a consent flow before reaching their dashboard.

> **Tip:** If a verbal code is set, share it separately from the invite link (e.g., tell the participant in person and send the link by email). This adds a layer of identity verification.

### Managing Portal Access

From the client detail page, click **Portal** → **Manage Portal** to see:

- Whether the participant has an active portal account
- A list of all invites (pending, accepted, expired)
- Any pending correction requests from the participant

### Revoking Portal Access

If a participant should no longer have portal access:

1. Go to their client detail page → **Portal** → **Manage Portal**
2. Click **Revoke Access**

This deactivates their account immediately. They will not be able to log in. Historical data (journal entries, messages) is preserved.

### Resetting Multi-Factor Authentication

If a participant is locked out of their MFA (lost their phone, can't access their authenticator app):

1. Go to their client detail page → **Portal** → **Manage Portal**
2. Click **Reset MFA**

This clears their MFA setup. The next time they log in, they can set up MFA again from their portal settings.

All portal management actions (invite creation, access revocation, MFA resets) are recorded in the audit log.

---

## Automated Reminders

KoNote can automatically send SMS or email reminders for upcoming meetings. This requires the `send_reminders` management command to run on a schedule.

### How It Works

1. The command looks for meetings in the next **36 hours** (by default) that are scheduled and haven't been reminded yet
2. For each meeting, it sends a reminder via the participant's preferred contact method (SMS or email)
3. Participants must have **active consent** for the chosen channel — if no consent, the reminder is skipped (not treated as a failure)
4. Failed reminders are **retried automatically** on the next run
5. After each batch, the system checks messaging channel health and sends admin alerts if channels are failing persistently

### Prerequisites

- **SMS Messaging** and/or **Email Messaging** must be enabled in Features
- SMS and/or email service must be configured (see [Messaging Settings](#messaging-settings))
- The participant must have a valid phone number or email address
- The participant must have active consent for the channel

### Running Manually

```bash
# Send reminders for meetings in the next 36 hours
python manage.py send_reminders

# Preview what would be sent without actually sending
python manage.py send_reminders --dry-run

# Use a custom lookahead window (e.g., 24 hours)
python manage.py send_reminders --hours 24
```

### Setting Up as a Scheduled Task

**Linux/Mac (cron) — run hourly:**

```bash
# Add to crontab with: crontab -e
0 * * * * cd /path/to/konote && python manage.py send_reminders >> /var/log/konote-reminders.log 2>&1
```

**Docker Compose — run hourly:**

```bash
0 * * * * docker compose -f /path/to/docker-compose.yml exec -T web python manage.py send_reminders >> /var/log/konote-reminders.log 2>&1
```

**Railway:**

Add a cron job service in your Railway project configuration that runs `python manage.py send_reminders` on an hourly schedule (e.g., `0 * * * *`).

**Windows Task Scheduler:**

Create a scheduled task that runs hourly:

```powershell
$Action = New-ScheduledTaskAction -Execute "python" -Argument "manage.py send_reminders" -WorkingDirectory "C:\KoNote\KoNote-web"
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "KoNote Reminders" -Action $Action -Trigger $Trigger
```

### Output

Each run reports a summary:

- **Sent** — reminder delivered successfully
- **Skipped** — participant has no consent or no contact information (won't change on retry)
- **Failed** — delivery error (will be retried on the next run)

---

## Weekly Export Summary Email

KoNote can email administrators a weekly digest of all data export activity. This helps with privacy oversight and funder compliance.

### What the Summary Includes

- Total number of exports in the period
- Breakdown by export type (program report, funder report, data extract, etc.)
- Count of elevated exports (exports flagged for extra monitoring)
- Download status (downloaded, pending, revoked)
- Top 5 staff members by export volume

### Running Manually

```bash
# Send the weekly summary email to admins
python manage.py send_export_summary

# Preview without sending
python manage.py send_export_summary --dry-run

# Use a custom lookback window (e.g., 14 days)
python manage.py send_export_summary --days 14
```

### Setting Up as a Scheduled Task

Run this command **once per week** (e.g., every Monday morning):

**Linux/Mac (cron):**

```bash
# Run every Monday at 8:00 AM
0 8 * * 1 cd /path/to/konote && python manage.py send_export_summary >> /var/log/konote-export-summary.log 2>&1
```

**Docker Compose:**

```bash
0 8 * * 1 docker compose -f /path/to/docker-compose.yml exec -T web python manage.py send_export_summary >> /var/log/konote-export-summary.log 2>&1
```

**Railway:**

Add a cron job service that runs `python manage.py send_export_summary` on a weekly schedule (e.g., `0 8 * * 1` for Monday at 8:00 AM).

### Who Receives the Email

- If `EXPORT_NOTIFICATION_EMAILS` is set in your environment variables, the summary goes to those addresses
- Otherwise, it goes to all active admin users who have an email address on file

The command is **stateless and idempotent** — running it multiple times in the same week sends duplicate emails, but causes no data changes. If no exports occurred in the period, the email still sends (showing zero counts).

---

## System Health Monitoring

KoNote tracks the health of SMS and email messaging channels and surfaces warnings when something is wrong.

### How It Works

Every time KoNote sends (or attempts to send) an SMS or email reminder, it records the result in a `SystemHealthCheck` record for that channel. The system tracks:

- When the last successful send occurred
- When the last failure occurred
- How many consecutive failures have happened
- The reason for the last failure

### Staff-Visible Banners

When messaging is enabled and a channel has recent failures, staff see warning banners on the **Meetings** page:

| Condition | Banner colour | Message |
|-----------|--------------|---------|
| 1–2 failures in the last 24 hours | Yellow (warning) | "X SMS/Email reminder(s) could not be sent recently." |
| 3 or more consecutive failures | Red (danger) | "SMS/Email reminders have not been working since [date]. Please contact your support person." |

Banners disappear automatically once the channel starts working again (the failure counter resets on success).

### Admin Alert Emails

After **24 hours of sustained failures**, administrators receive an email alert. This gives your support team early warning to investigate connectivity, credentials, or service outages.

### Viewing Health Status

Administrators can also see channel health status on the **Messaging Settings** page (gear icon → Messaging). This shows the current state of each channel, including the last success/failure timestamps and failure count.

### Common Causes of Failures

| Channel | Common issue | What to check |
|---------|-------------|---------------|
| **SMS** | Invalid Twilio credentials | Verify `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` in environment variables |
| **SMS** | Account balance exhausted | Check your Twilio account balance |
| **Email** | SMTP authentication failed | Verify `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` |
| **Email** | Connection timeout | Check `EMAIL_HOST` and `EMAIL_PORT` settings |

---

## Apply Setup Command

> **Status:** The `apply_setup` management command is **planned but not yet built**. It will be created when the first agency requests setup assistance. The design is documented below so you know what to expect.

The `apply_setup` command will create a full agency configuration from a single JSON file. This is intended for consultants setting up new KoNote instances, replacing the need to manually configure each setting through the web interface.

### How It Will Work

```bash
# Apply a configuration file
python manage.py apply_setup config.json

# Preview without making changes
python manage.py apply_setup config.json --dry-run
```

The command will create, in order:

1. **Instance settings** — product name, logo, support email, date format
2. **Terminology overrides** — customised terms (e.g., "Client" → "Participant")
3. **Feature toggles** — which modules to enable or disable
4. **Programs** — service lines with names, descriptions, and colours
5. **Plan templates** — complete templates with sections and targets
6. **Custom field groups and fields** — agency-specific data fields
7. **Metric enable/disable flags** — which metrics from the library to activate

### Configuration File Format

The configuration file is a JSON document. Here is a simplified example:

```json
{
  "instance_settings": {
    "product_name": "Youth Services — KoNote",
    "support_email": "support@agency.ca"
  },
  "terminology": {
    "client": "Participant",
    "target": "Goal"
  },
  "features": {
    "programs": true,
    "events": true,
    "alerts": false
  },
  "programs": [
    {
      "name": "Youth Housing",
      "description": "Transitional housing support for youth aged 16–24",
      "colour_hex": "#6366F1"
    }
  ],
  "metrics_enabled": ["PHQ-9 (Depression)", "GAD-7 (Anxiety)"]
}
```

See `tasks/setup-wizard-design.md` in the codebase for the full configuration file specification.

### Important Notes

- The command is **not idempotent** — running it twice creates duplicates. Clear the database or remove items manually before re-running.
- User accounts, custom metrics, and client data imports are handled separately through their own workflows.
- For now, use the web interface to configure your instance manually (see [Agency Configuration](#agency-configuration)).

---

## Troubleshooting

### Q: I see a login error
**A:** For Azure AD, check your email is registered. For local auth, confirm credentials with an admin.

### Q: Can I change terminology later?
**A:** Yes. Changes apply immediately to all users.

### Q: How do I delete a client?
**A:** You cannot delete clients through normal use — by design. KoNote preserves all client records to maintain audit trails and prevent accidental data loss. Instead, discharge the client or mark them as inactive. **Exception:** If a client requests data deletion under PIPEDA or GDPR, use the **Erase Client Data** workflow on their detail page. This requires approval from all relevant program managers and permanently deletes the client's data. See [Data Retention](#data-retention) and `docs/security-operations.md#erasure-workflow-security` for details.

### Q: What if I delete a program?
**A:** You can't delete programs with active clients. Deactivate instead.

### Q: Do staff need to fill all custom fields?
**A:** Only if marked "Required".

### Q: Does editing a template affect existing plans?
**A:** No. Templates only apply to new plans.

---

## Support

- **Documentation:** Return to [docs/index.md](index.md)
- **Bug reports:** Contact your deployment support team
- **Security vulnerabilities:** See [SECURITY.md](../SECURITY.md)

---

**Version 2.2** — KoNote
Last updated: 2026-02-16
