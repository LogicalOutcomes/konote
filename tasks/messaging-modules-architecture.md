# Messaging Modules Architecture — Implementation Plan

> **Companion to:** `tasks/messaging-calendar-plan.md` (the phase-by-phase build plan)
>
> **This document covers:** How organizations choose which messaging features to turn on, the admin settings page, Safety-First mode, and deployment documentation. Reviewed by two expert panels (2026-02-13).

## The Problem

KoNote serves diverse nonprofits — employment programs, housing, DV shelters, substance use, youth services, mental health. They have very different needs:

- An employment program wants staff to send appointment reminders and follow-up emails from KoNote
- A DV shelter must never send anything outbound — a text from "Community Services" could endanger someone
- A small counselling agency wants email reminders but doesn't want to pay for Twilio
- A large multi-program org wants automated reminders for some programs but not others

The system must be usable without any external integrations (no email, no Twilio), and organizations must be able to turn capabilities on and off without technical help.

## Design Principle

> A program director should be able to configure messaging in under 5 minutes. Legal requirements (consent, unsubscribe, sender ID) are handled automatically — the admin never sees them as toggles. Complexity lives in the code, not the settings page.

---

## Two-Layer Architecture

### Layer 1: Capability Modules (infrastructure)

These are configured by the technical consultant at deployment. They answer: "What is this instance *able* to do?"

| Module | Feature Key | Prerequisites | Cost | Who Configures |
|--------|-------------|---------------|------|----------------|
| Meetings & Scheduling | `meetings` | None | Free | Always on |
| Communication Log | `communication_log` | None | Free | Always on |
| Calendar Feeds (iCal) | `calendar_feeds` | None | Free | Admin toggle |
| Email Sending | `email_sending` | SMTP credentials (M365 / Google Workspace) | Usually free with existing email | Consultant at setup |
| SMS Sending | `sms_sending` | Twilio account + phone number | ~$15-25 CAD/month | Consultant at setup |
| Automated Reminders | `automated_reminders` | `email_sending` OR `sms_sending` + Railway cron | Free (infrastructure cost only) | Consultant at setup |

**Implementation:** Each is a `FeatureToggle` row. `email_sending` and `sms_sending` are only marked `is_enabled=True` after the consultant has configured credentials and verified they work.

### Layer 2: Policy Profile (organizational decision)

This is chosen by the program director. It answers: "What do we *want* to happen?"

| Profile | What Staff Can Do | What the System Does Automatically |
|---------|-------------------|------------------------------------|
| **Record-Keeping Only** | Schedule meetings, log communications already made | Nothing outbound |
| **Staff-Sent Messages** | All above + send reminders and messages with one click | Nothing — every message requires a human |
| **Full Automation** | All above | Sends reminders 24h before meetings to consented clients |

**Implementation:** Stored as `InstanceSetting(setting_key="messaging_profile", setting_value="record_keeping")`. Values: `record_keeping`, `staff_sent`, `full_automation`.

### Safety-First Override (sits above both layers)

For programs serving populations where outbound contact could create safety risks (DV shelters, some substance use and mental health programs).

**Implementation:** `InstanceSetting(setting_key="safety_first_mode", setting_value="true")`

When enabled:
- All outbound messaging is disabled regardless of profile
- Calendar feeds are disabled (even initials + record ID could be a risk)
- `safe_to_contact` becomes a mandatory workflow step (see below)
- Exports restricted to aggregate data only
- Enhanced audit logging for data-access events
- Per-client override available: individual clients can opt in to receiving messages after documented safety assessment

---

## What the Admin Sees

### Settings > Messaging

The entire configuration fits on one page with three sections.

**Section 1: Safety-First Mode** (top of page, prominent)

```
+--------------------------------------------------------------+
|  SAFETY-FIRST MODE                                    [OFF]  |
|                                                              |
|  For programs where any outbound contact could create        |
|  safety risks. Disables all outbound messaging and           |
|  calendar feeds. Individual overrides are not available       |
|  in this mode.                                               |
+--------------------------------------------------------------+
```

When ON, everything below is greyed out and locked.

**Section 2: Three profile cards**

```
+--------------------+  +--------------------+  +--------------------+
| RECORD-KEEPING     |  | STAFF-SENT         |  | FULL AUTOMATION    |
| ONLY          [*]  |  | MESSAGES           |  |                    |
|                    |  |                    |  |                    |
| Staff can schedule |  | Everything in      |  | Everything in      |
| meetings and log   |  | Record-Keeping,    |  | Staff-Sent, plus   |
| communications     |  | plus staff can     |  | KoNote sends       |
| they've already    |  | send appointment   |  | reminders           |
| made. Nothing is   |  | reminders, follow- |  | automatically      |
| sent from KoNote.  |  | ups, and other     |  | before meetings.   |
|                    |  | messages directly  |  |                    |
| Best for orgs that |  | from KoNote.       |  | Requires email or  |
| handle all client  |  |                    |  | SMS setup.         |
| contact through    |  | Requires email or  |  |                    |
| existing channels. |  | SMS setup.         |  |                    |
+--------------------+  +--------------------+  +--------------------+
```

Card states:
- **Available & Active**: blue border, checkmark
- **Available & Inactive**: default border, clickable
- **Unavailable** (missing prerequisites): grey, muted. Shows "Requires email setup — Configure now" with link. Cannot be selected.

**Section 3: Channel checkboxes** (visible when Staff-Sent or Full Automation is active)

```
Channels:
  [x] Email    (Connected via Microsoft 365)     [Change]
  [ ] Text messages    (Not set up)              [Set up Twilio]
```

Shows connection status. Greyed-out channels show what's needed to enable them.

**Section 4: More Controls** (visible on same page, below the main sections)

```
More Controls
  [ ] Allow messages to groups of clients
      Staff can send one message to all participants in a program.
      The system automatically skips clients without consent.

  [ ] Require supervisor review before sending
      Messages are queued for approval before delivery.
```

### What's NOT on this page (hard-coded in the system)

These are legal requirements handled automatically. The admin never toggles them:

- Consent check before every send
- Unsubscribe/opt-out mechanism in every message
- Organization name + mailing address in message footer
- Implied consent 2-year expiry (auto-flags clients for renewal)
- `safe_to_contact` check when Safety-First mode is on
- All messages logged in communication record
- CASL-compliant footer appended to all outbound messages

---

## Message Types

Staff can send three types of messages through KoNote. These are NOT separate toggles — they're all gated by the single "Staff can send messages" profile choice.

### Templated Messages (low risk)

Appointment reminders, document requests ("please bring X to your next appointment"). Pre-written templates with fill-in fields. Staff clicks one button, previews, sends.

- Gated by: messaging profile (Staff-Sent or Full Automation)
- Consent check: automatic
- PII risk: low (templates are controlled)
- CASL risk: low (predictable content)

### Composed Messages (medium risk)

Follow-ups after meetings, check-ins, referral information. Staff writes the content in a compose form on the client's page. Message is sent from the org's email address (not the staff member's personal email), and logged in the client file.

- Gated by: messaging profile (Staff-Sent or Full Automation)
- Consent check: automatic
- PII risk: higher (staff writes free text — could include case notes)
- Guardrail: **preview step** before every send. Staff sees exactly what the client will receive. No supervisor approval required by default (optional toggle in More Controls).
- CASL risk: medium (variable content, but still one-to-one)

**Why this is safer than the status quo:** Currently staff send from personal work email with no logging, no audit trail, no consent verification. KoNote adds all three.

### Bulk Messages (higher risk, separate toggle)

Program updates to all participants ("office closed Monday," "group session moved to Thursday"). One message sent to multiple clients.

- Gated by: messaging profile + separate "Allow messages to groups" toggle
- Consent check: automatic per-recipient. System filters the list and shows: "This will be sent to 12 of 15 participants. 3 will not receive it (no consent on file)."
- PII risk: low if done right (program-level info, not individual)
- CASL risk: highest (mass send — but consent-gated per recipient)
- Not included in v1 by default. Available as an opt-in toggle under More Controls.

---

## Safe-to-Contact Fields

Added to ClientFile. Available in all modes, mandatory workflow step in Safety-First mode.

### Structured Fields (not free text)

The first panel's VAW Sector Specialist recommended structured options over free-text notes to avoid recording safety-planning details in the database:

```python
# apps/clients/models.py — new fields

safe_to_contact_phone = models.BooleanField(default=True)
# "Safe to contact by phone" / "Not safe — phone may be monitored"

safe_to_contact_sms = models.BooleanField(default=True)
# "Safe to contact by text" / "Not safe — texts may be seen"

safe_to_contact_email = models.BooleanField(default=True)
# "Safe to contact by email" / "Not safe — email may be monitored"

safe_to_leave_voicemail = models.BooleanField(default=True)
# "Leave voicemail: yes / no"

safe_to_contact_code_name = EncryptedCharField(max_length=100, blank=True)
# "Use this name when calling: [field]"

safe_to_contact_review_date = models.DateField(null=True, blank=True)
# "Check with client again on this date"

safe_to_contact_notes = EncryptedTextField(blank=True)
# Label: "Additional safety context"
# Helper text: "Do not record safety plan details here.
#               Use your organization's safety planning tools."
```

### Behaviour

- **Safety-First mode OFF:** Fields are available on client edit form but not required. The `can_send()` function still checks them before sending.
- **Safety-First mode ON:** Fields are mandatory. Staff must review safe-to-contact status before any outbound action. The system prompts review when `safe_to_contact_review_date` has passed.
- **Review date:** System shows a prompt when the review date passes: "Safety contact preferences for [client] were last reviewed [X months ago]. Please confirm with the client." This is critical — safety situations change.

### Encryption & Privacy

- `safe_to_contact_code_name` and `safe_to_contact_notes` are encrypted at rest (Fernet, same pattern as name/phone)
- Both are excluded from all exports and reports
- Both have separate audit trail entries when viewed or modified
- `safe_to_contact_notes` has a shorter retention period (configurable, default 1 year)

---

## The `can_send()` Service Function

All outbound messaging flows through one function that enforces every check in order:

```python
# apps/communications/services.py

def can_send(client, channel):
    """Check all prerequisites before sending a message.

    Returns (allowed: bool, reason: str).
    Checks are ordered from broadest restriction to narrowest.
    """

    # 1. Safety-First mode — blocks everything
    if get_instance_setting("safety_first_mode") == "true":
        # Unless this specific client has a per-client override
        if not client.messaging_override_enabled:
            return False, "Safety-First mode is enabled"

    # 2. Policy profile — is outbound allowed?
    profile = get_instance_setting("messaging_profile")
    if profile == "record_keeping":
        return False, "Messaging is set to record-keeping only"

    # 3. Capability toggle — is this channel configured?
    if channel in ("sms", "phone") and not feature_enabled("sms_sending"):
        return False, "Text messaging is not set up"
    if channel == "email" and not feature_enabled("email_sending"):
        return False, "Email is not set up"

    # 4. Client consent — has the client agreed?
    if channel == "sms" and not client.sms_consent:
        return False, "Client has not consented to text messages"
    if channel == "email" and not client.email_consent:
        return False, "Client has not consented to email"

    # 5. Consent expiry — implied consent older than 2 years
    consent_date = (
        client.sms_consent_date if channel == "sms"
        else client.email_consent_date
    )
    if client.consent_messaging_type == "implied":
        if consent_date and consent_date < date.today() - timedelta(days=730):
            return False, "Consent expired — please re-confirm with client"

    # 6. Safe to contact — channel-specific safety check
    if channel == "sms" and not client.safe_to_contact_sms:
        return False, "Not currently safe to text this client"
    if channel == "email" and not client.safe_to_contact_email:
        return False, "Not currently safe to email this client"
    if channel == "phone" and not client.safe_to_contact_phone:
        return False, "Not currently safe to call this client"

    # 7. Contact info exists
    if channel == "sms" and not client.has_phone:
        return False, "No phone number on file"
    if channel == "email" and not client.has_email:
        return False, "No email address on file"

    return True, "OK"
```

This single function is called by:
- The "Send Reminder" button (manual)
- The "Send Message" compose form (manual)
- The automated reminders cron job
- The bulk message sender
- Any future messaging feature

---

## Consent Model — Kept Simple

The expert panel confirmed: **one consent boolean per channel is sufficient**, as long as the intake consent statement is drafted broadly enough.

### Intake Consent Statement (set by org, stored in InstanceSettings)

Default English:
> "Can we contact you by email/text about your appointments and program participation?"

Default French:
> "Pouvons-nous vous contacter par courriel ou texto au sujet de vos rendez-vous et de votre participation au programme?"

This covers: reminders, follow-ups, program updates, check-ins, document requests — basically everything a case worker would send. No per-purpose consent needed.

### What's in the Database

Per client (already in ClientFile from Phase 3):
- `sms_consent` (boolean) + `sms_consent_date`
- `email_consent` (boolean) + `email_consent_date`
- `consent_messaging_type` (express/implied)
- Withdrawal tracking fields
- `consent_notes` (auto-filled: "Express consent recorded by [staff] on [date]")

### Implied Consent 2-Year Expiry

CASL requires this. The system automatically flags clients whose implied consent is approaching expiry (23 months) with a "Consent renewal needed" indicator on the client page. At 24 months, `can_send()` blocks sending and shows "Consent expired — please re-confirm with client."

---

## Customizable Organization Footer

Set once during deployment, appended to every outbound message automatically.

### Email Footer (HTML)

Stored in `InstanceSetting(setting_key="email_footer_en")` and `email_footer_fr`:

```
—
[Organization Name]
[Mailing Address]
[Phone Number]

You're receiving this because you consented to messages from [Org Name].
To stop receiving messages, click here: [unsubscribe link]
or call [phone number].
```

### SMS Footer

Appended to every text: `Reply STOP to opt out.` (Twilio handles STOP/START at the carrier level.)

### Admin Configuration

On the admin settings page (consultant configures during setup):
- Organization name (English + French)
- Mailing address
- Phone number
- Custom footer text (optional override)

---

## Setup Wizard (First-Run Experience)

When an admin first visits Settings > Messaging after deployment, they see a guided setup instead of the raw toggles page.

### Step 1: Program Types

> "What kind of programs does your organization run?"
>
> (Multi-select checkboxes)
> - [ ] Employment & job readiness
> - [ ] Housing & shelter
> - [ ] Counselling & mental health
> - [ ] Violence against women / domestic violence
> - [ ] Substance use & harm reduction
> - [ ] Youth services
> - [ ] Newcomer & settlement services
> - [ ] Other: ___________

### Step 2: Recommendation

Based on selection, the wizard recommends a profile:

- If DV, substance use, or shelter selected:
  > "Because your organization serves populations with safety concerns, we recommend **Safety-First Mode**. This disables all outbound messaging from KoNote. Staff can still schedule meetings and log communications. You can enable messaging for specific clients on a case-by-case basis after a safety assessment."

- If other program types only:
  > "We recommend **Staff-Sent Messages**. Staff can send appointment reminders and follow-up messages from KoNote. Every message requires a staff member to click send — nothing goes out automatically."

- The admin can accept the recommendation or choose differently.

### Step 3: Channel Setup (if messaging profile chosen)

> "How do you want to reach clients?"
>
> **Email** — Send from your organization's email address
> Status: Connected via Microsoft 365 / Not set up — [contact your consultant]
>
> **Text messages** — Send texts via Twilio
> Status: Connected / Not set up — [contact your consultant]

If neither channel is configured, the wizard shows the consultant's contact info and a note: "Your consultant will set this up. You can come back to this page after."

### Step 4: Confirmation

Summary of choices. "You can change these settings anytime."

After completing the wizard, the admin sees the normal settings page (profile cards + toggles) pre-configured with their choices.

---

## Deployment Documentation

### For the Technical Consultant

A separate section in `docs/operations-runbook.md` covering:

1. **Pre-deployment checklist:**
   - Which email system does the org use? (M365 / Google Workspace / Neither)
   - Does the org want SMS? (Yes = set up Twilio / No = skip)
   - Does the org serve populations with safety concerns? (Yes = recommend Safety-First)
   - Will they want automated reminders? (Yes = configure Railway cron / No = skip)

2. **Email setup steps** (already in messaging-calendar-plan.md Phase 0A1):
   - Google Workspace: app password, SMTP relay
   - Microsoft 365: SMTP AUTH or app password, Exchange admin config

3. **Twilio setup steps** (already in Phase 0A):
   - Account creation, Canadian phone number, A2P 10DLC registration
   - Auto-recharge on org credit card
   - Forward account alerts to org shared inbox

4. **Verification steps:**
   - Send test email from KoNote admin
   - Send test SMS from KoNote admin
   - Verify cron job fires on schedule (if automated reminders)

5. **Handoff to admin:**
   - Walk admin through Setup Wizard
   - Confirm profile choice
   - Review message templates (customize for org context)
   - Set organization footer (English + French)

### For the Organization Administrator

**In-app documentation** (not a separate PDF). Each profile card and toggle has:
- A plain-language description of what it does
- What you get / what you give up
- Prerequisites shown inline ("Requires email setup")

The Setup Wizard is the primary documentation — it guides the admin through decisions at the moment they need to make them.

### Pros and Cons Table (for the admin, shown during setup or in a help panel)

| Option | What You Get | What to Consider |
|--------|-------------|------------------|
| **Record-Keeping Only** | Meeting scheduling, communication logging for funder reports. No setup needed. | Staff still use personal email/phone for client contact — no logging of those messages. |
| **Staff-Sent Messages (Email)** | Reminders and follow-ups from org email address. Logged automatically. Uses your existing M365 or Google Workspace. | Staff must click send for each message. Uses org's existing email — usually no extra cost. |
| **Staff-Sent Messages (SMS)** | Text reminders to clients. Higher open rates than email (~98% vs ~20%). | Requires Twilio account (~$15-25 CAD/month). Texts are visible on phone lock screens — consider privacy. |
| **Full Automation** | Reminders sent automatically 24h before meetings. Staff don't have to remember. | Requires proven manual sending first (1-2 months). Org must monitor for failures. |
| **Safety-First Mode** | Maximum protection for vulnerable clients. Nothing leaves KoNote. | Staff cannot send messages from the system. Per-client overrides available for clients who request it. |
| **Bulk Messages** | Program-wide announcements (closures, schedule changes) in one step. | Only sends to consented clients. Review recipient list before sending. |

---

## Demo Environment Setup

For demos and development, use lightweight services instead of production M365/Google Workspace and Twilio accounts.

### Email: Resend.com

[Resend](https://resend.com) is a developer-friendly email API with an SMTP interface. It requires **zero code changes** — just different env vars.

| Setting | Value |
|---------|-------|
| `EMAIL_HOST` | `smtp.resend.com` |
| `EMAIL_PORT` | `465` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | `resend` |
| `EMAIL_HOST_PASSWORD` | Resend API key (starts with `re_`) |
| `DEFAULT_FROM_EMAIL` | `demo@yourdomain.com` (must verify domain in Resend dashboard) |

**Free tier:** 100 emails/day, 3,000/month — more than enough for demos.

**Why Resend for demo instead of the console backend:**
- You can actually show a client real emails arriving during a live demo
- Delivery status tracking works (sent/delivered/bounced) — so health banners and meeting card status indicators function realistically
- 2-minute setup: sign up, verify a domain, copy the API key
- No M365 Exchange admin or Google app password configuration needed

**Why NOT Resend for production:**
- US-hosted company — no Canadian data residency guarantee
- Production orgs should use their own M365 or Google Workspace for data sovereignty and so replies go to their real inbox
- The switch from Resend to production SMTP is just changing 4 env vars — no code changes

### SMS: Twilio Test Credentials

Twilio provides free test credentials that simulate SMS without actually sending:

| Setting | Value |
|---------|-------|
| `TWILIO_ACCOUNT_SID` | Test Account SID from [Twilio Console > Test Credentials](https://www.twilio.com/console) |
| `TWILIO_AUTH_TOKEN` | Test Auth Token |
| `TWILIO_FROM_NUMBER` | `+15005550006` (Twilio magic test number — always succeeds) |

**Test magic numbers** (use as recipient for different outcomes):
- `+15005550006` — message succeeds
- `+15005550001` — invalid number (tests error handling)
- `+15005550009` — cannot route (tests failure display)

This lets you demonstrate the full SMS flow — including failure states and plain-language error messages on meeting cards — without sending real texts or spending money.

**For a fully realistic demo** (actual texts arriving on a phone): use a real Twilio trial account ($15 USD free credit). Buy a Canadian number (~$1.50/month) and send to your own phone. Trial accounts add a "Sent from a Twilio trial account" prefix to messages.

### Demo Environment Summary

| Channel | Demo Provider | Cost | Setup Time | Realistic? |
|---------|--------------|------|------------|------------|
| Email | Resend.com (SMTP) | Free | 2 minutes | Yes — real emails arrive |
| SMS (simulated) | Twilio test credentials | Free | 1 minute | Partial — no real texts, but status flow works |
| SMS (real) | Twilio trial account | Free ($15 credit) | 10 minutes | Yes — real texts arrive on your phone |
| Calendar feeds | Built-in (no external service) | Free | 0 minutes | Yes |

### Switching from Demo to Production

All changes are env vars only — no code changes, no migrations, no redeployment of different code:

```
# Demo → Production: just swap these env vars
EMAIL_HOST=smtp.resend.com        → smtp.office365.com (or smtp-relay.gmail.com)
EMAIL_HOST_USER=resend            → reminders@orgname.ca
EMAIL_HOST_PASSWORD=re_xxxxx      → (M365 app password or Google app password)
TWILIO_ACCOUNT_SID=test_xxxxx     → (real Twilio Account SID)
TWILIO_AUTH_TOKEN=test_xxxxx      → (real Twilio Auth Token)
TWILIO_FROM_NUMBER=+15005550006   → (org's Canadian Twilio number)
```

---

## Changes to the Existing Plan

This document adds to `tasks/messaging-calendar-plan.md` — it doesn't replace it. The phase-by-phase build order stays the same. These are the specific additions:

### New Items for Phase 0 (Consultant Setup)

- Add Setup Wizard to the handoff workflow
- Add pros/cons documentation to the in-app help system
- Consultant walks admin through profile selection during handoff

### New Items for Phase 3 (Consent & Contact Fields)

- Add `safe_to_contact_*` structured fields to ClientFile
- Add `safe_to_contact_review_date` with auto-prompt
- Encrypt `safe_to_contact_code_name` and `safe_to_contact_notes`
- Add review-date reminder to client detail page

### New Items for Phase 4 (Outbound Messaging)

- Implement `can_send()` with the full check chain (safety mode > profile > capability > consent > safe-to-contact > contact info)
- Add "Send Message" compose form (not just "Send Reminder") — staff can write follow-ups, check-ins, referral info
- Add preview step for all composed messages
- Add customizable organization footer (English + French)
- Bulk messaging toggle and filtered recipient list (under More Controls)

### New Admin Settings Page

- Build the Settings > Messaging page with profile cards + Safety-First toggle + channel checkboxes + More Controls
- Build the first-run Setup Wizard
- Store profile in `InstanceSetting`, Safety-First in `InstanceSetting`, individual toggles in `FeatureToggle`

### New FeatureToggle / InstanceSetting Keys

| Type | Key | Values | Default |
|------|-----|--------|---------|
| InstanceSetting | `messaging_profile` | `record_keeping`, `staff_sent`, `full_automation` | `record_keeping` |
| InstanceSetting | `safety_first_mode` | `true`, `false` | `false` |
| InstanceSetting | `email_footer_en` | HTML text | (template provided) |
| InstanceSetting | `email_footer_fr` | HTML text | (template provided) |
| InstanceSetting | `intake_consent_statement_en` | text | (default provided) |
| InstanceSetting | `intake_consent_statement_fr` | text | (default provided) |
| FeatureToggle | `email_sending` | enabled/disabled | disabled |
| FeatureToggle | `sms_sending` | enabled/disabled | disabled |
| FeatureToggle | `calendar_feeds` | enabled/disabled | enabled |
| FeatureToggle | `automated_reminders` | enabled/disabled | disabled |
| FeatureToggle | `bulk_messaging` | enabled/disabled | disabled |
| FeatureToggle | `supervisor_review` | enabled/disabled | disabled |
