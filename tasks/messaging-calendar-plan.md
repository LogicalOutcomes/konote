# Messaging, Meetings & Calendar Integration — Implementation Plan

> **Reviewed by two expert panels (2026-02-13).** This version incorporates all findings.
>
> **Design principle:** This is a *workflow improvement*, not a technology implementation. Every feature must be evaluated by: "Does this make it easier for a case worker with 35 clients and 5 minutes of training to remind Maria about tomorrow's appointment and keep a record of it?"

## Overview

Add meeting scheduling, communication logging, outbound email/SMS reminders, iCal calendar feeds, and a communication log to KoNote. Staff can schedule meetings, send or log reminders, and see their schedule in Google Calendar (or Outlook).

### Who uses this

| Role | What they do with this feature | Technical skill |
|------|-------------------------------|-----------------|
| Case worker | Creates meetings, sends/logs reminders, views schedule | None — learns by watching a colleague |
| Program manager | Same as above + views team meetings, pulls funder stats | None |
| Office manager / ED | Reads monthly stats for funder reports | None |
| Semi-technical maintainer | Checks in every few months, fixes problems with AI assistance | Decent but not expert |
| Consultant | Initial setup, Twilio account, handoff | Professional |

### Core constraint

**Between consultant visits, the system must either work or clearly tell non-technical staff what's wrong in language they understand.** There is no IT department. There is no sysadmin. Failures must be visible where staff already look — not in admin dashboards nobody checks.

---

## Phase 0: Consultant Setup & Handoff

**Goal:** Everything the consultant does at setup that the org can't do themselves, plus the document that keeps the system alive after the consultant leaves.

### 0A. External account setup (consultant responsibility)

| Account | What to configure | Survival notes |
|---------|-------------------|----------------|
| **Twilio** | Create account, buy Canadian phone number, complete A2P 10DLC campaign registration, set up auto-recharge on org credit card, forward account alerts to org's shared inbox (e.g. `info@orgname.ca`) | A2P registration is mandatory for business SMS in Canada. Must be completed at setup — Twilio will suspend sending if deferred. |
| **Google Workspace SMTP** | Create app password for `reminders@orgname.ca` (or shared mailbox), configure Django SMTP settings | Use the org's existing Google Workspace. No new email provider account needed. |
| **Railway** | Set up cron job for `send_reminders`, verify it runs | Document how to check cron status |

### 0B. App configuration (consultant responsibility)

| Setting | Where | What |
|---------|-------|------|
| SMS sender display name | Admin settings | Configure Twilio alphanumeric sender ID — use something neutral (e.g. "Appt Reminder"), NOT the org name if the org provides sensitive services (mental health, addiction, DV, immigration) |
| Message templates | Admin settings | Review and customize default reminder templates for the org's context. Set English and French versions. |
| Feature toggles | Admin settings | Enable `messaging_email` and `messaging_sms` |
| Support contact | Admin settings | Name and phone number of the person to call when something breaks — displayed in error messages |
| Org mailing address | Admin settings | Required in email footers for CASL compliance |

### 0C. Consultant handoff document

**File:** `docs/operations-runbook.md` (also print a copy for the office)

Contents:
1. **Account inventory** — Twilio login, Google app password location, Railway dashboard URL. Who holds each credential.
2. **What each cron job does** — plain language. "Every morning at 6 AM, the system checks for meetings happening in the next 36 hours and sends text/email reminders to clients who have consented."
3. **What to do when...** troubleshooting for the 5 most likely failures:
   - "Text reminders stopped working" → Check Twilio balance / check for compliance email in shared inbox
   - "Email reminders stopped working" → Check if Google app password was revoked
   - "The system shows a yellow/red banner" → Read the banner, it tells you what to do
   - "A staff member can't log in" → [existing auth troubleshooting]
   - "Twilio sent a scary email" → Forward to consultant, here's their contact info
4. **How to use Claude Code** to diagnose and fix common issues (for the semi-technical maintainer)
5. **Annual checklist** — CASL consent basis review, Twilio compliance re-verification, Google app password rotation

### 0D. CASL & PIPEDA compliance documentation

The consultant documents (and the org reviews):

- **CASL consent basis:** For nonprofits serving active clients, appointment reminders are *transactional* (not commercial electronic messages) and may not strictly require CASL CEM consent. However, KoNote enforces consent for all outbound messages as best practice and PIPEDA compliance. This distinction matters if the org ever sends newsletters or event invitations — different rules apply.
- **PIPEDA cross-border transfer:** Sending phone numbers to Twilio (a US company) constitutes cross-border transfer of personal information. The org should execute Twilio's Data Processing Agreement (DPA). Email via Google Workspace stays in Canadian datacentres for Canadian tenants.
- **CASL sender identification:** Messages must identify the sending organization and the responsible person (CASL s.6(2)(b)). Templates include org name and mailing address.
- **AODA (Ontario):** HTML email templates must be screen-reader compatible. SMS is plain text and inherently accessible.

---

## Phase 1: Meetings + iCal Feeds

**Goal:** Staff can schedule meetings and see them in Google Calendar. Immediate daily value, zero external dependencies.

### 1A. Create Meeting model (separate from Event)

**File:** `apps/events/models.py`

```python
class Meeting(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="meeting")
    location = models.CharField(max_length=255, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("scheduled", "Scheduled"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        default="scheduled",
    )
    attendees = models.ManyToManyField(
        "auth_app.User", blank=True, related_name="meetings"
    )
    reminder_sent = models.BooleanField(default=False)
    reminder_status = models.CharField(
        max_length=15,
        choices=[
            ("not_sent", "Not Sent"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("blocked", "Blocked"),
            ("no_consent", "No Consent"),
            ("no_phone", "No Phone"),
        ],
        default="not_sent",
    )
    reminder_status_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-event__start_timestamp"]
        indexes = [
            models.Index(fields=["status", "reminder_sent"]),
        ]
```

**Why a separate model:** Adding nullable fields to Event for a meeting subtype creates dead weight on every regular event. The OneToOneField keeps Event clean. Use `select_related('meeting')` and `hasattr(event, 'meeting')` in the timeline.

**Why `reminder_status` and `reminder_status_reason`:** These drive the staff-visible indicator on the meeting card. Staff see "Reminder sent" / "Failed — phone not in service" / "No phone on file" without checking a separate screen.

### 1B. Meeting form — 3 fields for creation

**File:** `apps/events/forms.py`

Meeting creation must take **under 60 seconds** or staff will stop using it.

Create form shows 3 required/common fields:
- **Date & time** (required)
- **Location** (optional, free text)
- **Send reminder?** (checkbox, default yes if client has consent + phone/email)

Status defaults to "scheduled." Duration is optional. Attendees defaults to the creating staff member. All other fields are available on the edit form but not required at creation.

### 1C. Meeting views

**File:** `apps/events/views.py`

- `meeting_create(request, client_id)` — quick-create from client page (3 fields)
- `meeting_update(request, client_id, event_id)` — full edit form
- `meeting_list(request)` — staff's upcoming meetings across all clients (dashboard view)
- `meeting_status_update(request, event_id)` — HTMX partial for status changes

**Status auto-transition:** Meetings with a `start_timestamp` more than 24 hours in the past and still "scheduled" are automatically shown as "completed" in the UI (display logic, not a cron job). Staff can override.

### 1D. Meeting card — the thing staff actually see

**File:** `templates/events/_meeting_card.html`

The meeting card on the client page and staff dashboard must show:

```
┌─────────────────────────────────────────────┐
│ Tomorrow, 2:00 PM — Office                  │
│ Maria D. (KN-0042)                          │
│                                             │
│ ✓ Reminder sent by text    [Send Reminder]  │
│                        — or —               │
│ ⚠ No phone on file         [Log a Call]     │
│                        — or —               │
│ ✗ Text failed — phone      [Retry] [Log]    │
│   may not be in service                     │
└─────────────────────────────────────────────┘
```

The reminder status line is **the primary way staff learn about failures.** It uses plain language, not error codes.

### 1E. URLs

**File:** `apps/events/urls.py`

```
meetings/                           → meeting_list (staff dashboard)
client/<client_id>/meetings/create/ → meeting_create
client/<client_id>/meetings/<id>/   → meeting_update
meetings/<id>/status/               → meeting_status_update (HTMX)
```

### 1F. Templates

- `templates/events/meeting_list.html` — staff dashboard with upcoming/past meetings
- `templates/events/meeting_form.html` — create (3 fields) / edit (full) meeting form
- `templates/events/_meeting_card.html` — timeline + dashboard card with reminder status
- `templates/events/_meeting_status.html` — HTMX partial for status toggle

### 1G. iCal feed

**File:** `apps/events/models.py` — add CalendarFeedToken

```python
class CalendarFeedToken(models.Model):
    user = models.OneToOneField("auth_app.User", on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
```

Generate token with `secrets.token_urlsafe(32)`.

Security:
- Auto-disable after 90 days with no access
- Auto-revoke when user is deactivated (signal)
- Rate-limit: max 60 requests/hour per token

**File:** `apps/events/views.py` — add calendar_feed view

```python
def calendar_feed(request, token):
    """Public .ics endpoint — no login required, token is the auth."""
    feed_token = get_object_or_404(CalendarFeedToken, token=token, is_active=True)
    feed_token.last_accessed_at = now()
    feed_token.save(update_fields=["last_accessed_at"])

    user = feed_token.user
    meetings = Meeting.objects.filter(
        status="scheduled",
        attendees=user,
    ).select_related("event", "event__client_file")

    cal = Calendar()
    cal.add("prodid", "-//KoNote//EN")
    cal.add("version", "2.0")
    cal.add("x-published-ttl", "PT30M")  # suggest 30-min refresh

    for meeting in meetings:
        event = ICalEvent()
        # No PII in summary — initials + record ID only
        event.add("summary", f"Meeting — {meeting.event.client_file.initials} ({meeting.event.client_file.record_id})")
        event.add("description", "View details in KoNote")
        event.add("dtstart", meeting.event.start_timestamp)
        if meeting.duration_minutes:
            event.add("dtend", meeting.event.start_timestamp + timedelta(minutes=meeting.duration_minutes))
        if meeting.location:
            event.add("location", meeting.location)
        cal.add_component(event)

    return HttpResponse(cal.to_ical(), content_type="text/calendar")
```

**Privacy:** Feed contains initials + record ID only. No names, no phone numbers, no addresses. Description links back to KoNote for full details.

**URL:** `konote/urls.py` — `path("calendar/<str:token>/feed.ics", calendar_feed, name="calendar_feed")`

**Settings page:** Add "Calendar Feed" section to user profile. Shows feed URL with "Copy" button and instructions for Google Calendar / Outlook. "Regenerate" button to invalidate old token.

**Feed caching:** Cache generated .ics per user with 5-minute TTL using Django's cache framework. Only regenerate if meetings changed since last generation.

### 1H. RBAC permissions

Add `"meeting.view"`, `"meeting.create"`, `"meeting.edit"` — scoped like existing event permissions. Staff and PM can create; Receptionist can view only.

### 1I. Tests

- Create meeting in under 3 fields
- Edit meeting with full fields
- Meeting status transitions
- RBAC: staff can create, receptionist cannot
- Meeting list filters by user's programs
- Meeting appears on client timeline
- iCal feed returns valid .ics format
- Invalid/inactive token returns 404
- Only assigned meetings appear in feed
- No PII in feed content
- Regenerating token invalidates old one
- `reminder_status` displays correctly on meeting card

### 1J. Dependency

**Adds to `requirements.txt`:** `icalendar>=6.0`

---

## Phase 2: Communication Log

**Goal:** Staff can quickly log any communication they've had with a client. This captures what's already happening (personal texts, phone calls) and gives the org funder-reportable data immediately.

**Why this comes before messaging:** Staff are already communicating with clients. Give them a way to record it now. When system-sent messaging is added later, it writes to the same log — no new concept to learn.

### 2A. Create Communication model (new app)

**File:** `apps/communications/models.py`

```python
class Communication(models.Model):
    client_file = models.ForeignKey("clients.ClientFile", on_delete=models.CASCADE)

    direction = models.CharField(
        max_length=10,
        choices=[("outbound", "Outbound"), ("inbound", "Inbound")],
    )
    channel = models.CharField(
        max_length=15,
        choices=[
            ("email", "Email"),
            ("sms", "SMS"),
            ("phone", "Phone Call"),
            ("in_person", "In Person"),
            ("portal", "Portal Message"),
            ("whatsapp", "WhatsApp"),
        ],
    )
    method = models.CharField(
        max_length=15,
        choices=[
            ("manual_log", "Manual Log"),
            ("system_sent", "System Sent"),
            ("system_received", "System Received"),
        ],
    )

    subject = models.CharField(max_length=255, blank=True)
    _content_encrypted = models.BinaryField(null=True, blank=True)

    # Delivery tracking (for system-sent messages)
    delivery_status = models.CharField(
        max_length=15,
        choices=[
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
            ("bounced", "Bounced"),
            ("blocked", "Blocked"),
        ],
        default="sent",
        blank=True,
    )
    delivery_status_display = models.CharField(
        max_length=255, blank=True,
        help_text="Plain-language description of delivery result for staff display"
    )
    external_id = models.CharField(max_length=255, blank=True)  # Twilio SID, etc.

    logged_by = models.ForeignKey("auth_app.User", on_delete=models.SET_NULL, null=True)
    author_program = models.ForeignKey("programs.Program", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["client_file", "-created_at"]),
            models.Index(fields=["delivery_status"]),
        ]
```

**Why a separate app:** The events app already has Event, EventType, Alert, AlertCancellationRecommendation. Adding Communication with its forms, views, services, and templates would roughly double it. A separate `apps/communications/` keeps the dependency graph clean.

### 2B. Quick-log form — the 2-click workflow

**File:** `apps/communications/forms.py`

Staff need to log a personal text or phone call in under 10 seconds. On the client page, below the meeting list, show quick-action buttons:

```
[Logged a Call]  [Logged a Text]  [Logged an Email]  [Logged a Visit]
```

Each button opens a minimal HTMX form:
- **Notes** (one text field, optional)
- Direction defaults to "outbound," channel pre-filled from the button clicked
- Timestamp auto-fills to now
- One click to save

This is the realistic workflow: staff texts Maria from their personal phone, then taps "Logged a Text" and types "Confirmed for tomorrow."

Full form (`CommunicationLogForm`) is also available for detailed logging with all fields (direction, channel, subject, content).

### 2C. Views

**File:** `apps/communications/views.py`

- `quick_log(request, client_id)` — HTMX endpoint for quick-action buttons
- `communication_log(request, client_id)` — full form for detailed logging
- Communication records appear on the client timeline

### 2D. URLs

```
client/<client_id>/communications/quick-log/ → quick_log (HTMX)
client/<client_id>/communications/log/       → communication_log (full form)
```

### 2E. Templates

- `templates/communications/_quick_log_buttons.html` — the row of quick-action buttons
- `templates/communications/_quick_log_form.html` — HTMX inline form
- `templates/communications/communication_log_form.html` — full form
- `templates/communications/_communication_card.html` — timeline display partial

### 2F. Timeline integration

Update the existing timeline view to include Communication records alongside Events and ProgressNotes. Add HTMX "Load more" pagination — 25 items per page.

**Implementation note:** Merging three querysets with different timestamp fields for sorted pagination is non-trivial. Options: (a) annotate a common `sort_date` field on each queryset and use `union()`, or (b) use `itertools.merge` with manual slicing. Document the chosen approach in comments for the AI-assisted maintainer.

### 2G. Funder reporting number

On the staff dashboard (or admin page), always show: **"This month: X reminders sent, Y communications logged."** One number, always visible, copy-pasteable for funder reports. Not a report to generate — a number that's always there.

### 2H. Audit logging

Log "communication logged" actions to the audit database (without message content).

### 2I. RBAC

Add `"communication.log"`, `"communication.view"` permissions.

### 2J. Tests

- Quick-log creates record in under 2 clicks
- Full log form creates record with all fields
- Log appears on client timeline
- Encrypted content round-trip
- RBAC: staff can log, receptionist can view
- Timeline pagination works with mixed content types
- Funder stats show correct counts

---

## Phase 3: Consent, Contact Fields & Client Language

**Goal:** Add email, phone confirmation tracking, consent, and language preference to ClientFile so messages can be sent legally and appropriately.

### 3A. Add fields to ClientFile

**File:** `apps/clients/models.py`

```python
# Encrypted email (same pattern as phone)
_email_encrypted = models.BinaryField(null=True, blank=True)

# Quick existence checks without decryption
has_email = models.BooleanField(default=False)
has_phone = models.BooleanField(default=False)

# Phone number staleness tracking
phone_last_confirmed = models.DateField(null=True, blank=True)

# Client's preferred language for messages (not UI language)
preferred_language = models.CharField(
    max_length=5,
    choices=[("en", "English"), ("fr", "French")],
    default="en",
)

# Contact preferences
preferred_contact_method = models.CharField(
    max_length=10,
    choices=[
        ("sms", "Text Message"),
        ("email", "Email"),
        ("both", "Both"),
        ("none", "None"),
    ],
    default="none",
    blank=True,
)

# Consent tracking (CASL compliance — full model in DB, simple UI)
sms_consent = models.BooleanField(default=False)
sms_consent_date = models.DateField(null=True, blank=True)
email_consent = models.BooleanField(default=False)
email_consent_date = models.DateField(null=True, blank=True)
consent_type = models.CharField(
    max_length=10,
    choices=[("express", "Express"), ("implied", "Implied")],
    default="express",
    blank=True,
)

# Consent withdrawal tracking (CASL requires proof)
sms_consent_withdrawn_date = models.DateField(null=True, blank=True)
email_consent_withdrawn_date = models.DateField(null=True, blank=True)
consent_notes = models.TextField(blank=True)
```

Set `has_email` and `has_phone` automatically in `save()`:

```python
def save(self, *args, **kwargs):
    self.has_phone = bool(self._phone_encrypted)
    self.has_email = bool(self._email_encrypted)
    super().save(*args, **kwargs)
```

**Consent audit trail:** Log every consent change to the AuditLog database using the existing `AuditLog.objects.using("audit").create(...)` pattern with `action="consent_changed"`.

### 3B. Consent UI — one question at intake

**The intake form asks ONE question:**

> "Can we text this client appointment reminders?" — Yes / No

That's it. When staff checks "Yes":
- `sms_consent = True`
- `sms_consent_date = today()`
- `consent_type = "express"`
- `preferred_contact_method = "sms"`

All auto-filled. Staff never sees nine consent fields. The full CASL-compliant record exists in the database for compliance evidence, but the UI presents one checkbox.

A second checkbox for email consent appears if the org has `messaging_email` enabled.

**Consent withdrawal:** If staff unchecks the consent box on the client edit form, the system auto-fills `sms_consent_withdrawn_date = today()` and logs to AuditLog. Staff doesn't manage dates.

**Consent notes** (how consent was given) — available on the full client edit form but not required at intake. The system auto-fills: "Express consent recorded by [staff name] on [date]."

### 3C. Phone number staleness indicator

On the client detail page, next to the phone number:

- Phone confirmed in the last 90 days: no indicator
- Phone confirmed 90-180 days ago: "Phone number last confirmed 4 months ago"
- Phone not confirmed or >180 days: "Phone number hasn't been confirmed recently — consider verifying"

**Not a blocker** — just a visual nudge. Staff can update `phone_last_confirmed` by clicking a "Phone verified" button on the client page (sets to today).

This matters because marginalized populations frequently change numbers, lose prepaid service, or share phones.

### 3D. Migration

Create and apply migration.

### 3E. Update client detail view

Show preferred contact method, consent status (simple "Consented to text reminders: Yes / No"), language preference, and phone staleness indicator on the client detail page.

### 3F. Tests

- Email encryption/decryption round-trip
- Consent checkbox auto-fills all CASL fields
- Consent withdrawal auto-fills withdrawal date
- Consent change logged to AuditLog
- Phone staleness indicator shows at correct thresholds
- `preferred_language` defaults to "en"

---

## Phase 4: Outbound Messaging (Email + SMS)

**Goal:** System can send reminders and messages to clients. Staff can preview and personalize before sending. Failures are visible on the meeting card.

### 4A. Dependencies

**File:** `requirements.txt`

```
twilio>=9.0
```

**No django-anymail.** Use Django's built-in SMTP backend with the org's existing Google Workspace. Configuration:

```python
# konote/settings/base.py
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp-relay.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "reminders@orgname.ca")
```

Google Workspace SMTP supports up to 10,000 messages/day on Business Standard. More than sufficient.

### 4B. SMS configuration

**File:** `konote/settings/base.py`

```python
# SMS via Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
SMS_ENABLED = bool(TWILIO_ACCOUNT_SID)
SMS_SENDER_NAME = os.environ.get("SMS_SENDER_NAME", "")  # Alphanumeric sender ID

# Mask sensitive settings from Django error pages
import re
SENSITIVE_VARIABLES_RE = re.compile(
    r"TWILIO|SECRET|TOKEN|PASSWORD|KEY", re.IGNORECASE
)
```

**Realistic cost estimate:** Twilio for a Canadian nonprofit sending ~500 SMS/month: ~$1.50/month number rental + ~$0.0085/segment x 500 = ~$4.25 + platform fees + carrier surcharges. **Budget $15-25 CAD/month**, not $10.

### 4C. Services layer

**File:** `apps/communications/services.py`

This is the core business logic. Views call these functions; they handle consent checking, channel routing, sending, and logging. **Docstrings explain business rules (the "why") for AI-assisted maintainers.**

```python
def send_reminder(meeting, logged_by=None):
    """Send an appointment reminder for a meeting.

    Checks consent, selects channel based on client preference,
    renders template in client's preferred language, sends, and
    records the result on both the Communication log and the
    Meeting.reminder_status field (so staff see it on the meeting card).

    Business rules:
    - CASL requires consent before sending (even though transactional
      messages may be exempt, we enforce as best practice)
    - Implied consent expires after 2 years (CASL standard)
    - SMS must contain no PII — org name may be sensitive
    - Contact info is read at send time, never cached
    """
    client_file = meeting.event.client_file
    channel = client_file.preferred_contact_method

    if channel == "none":
        _record_reminder_status(meeting, "no_consent", "Client has not consented to reminders")
        return False, "No consent"

    if channel in ("sms", "both"):
        ok, reason = _send_sms_reminder(meeting, client_file, logged_by)
        if ok:
            return True, "Sent"

    if channel in ("email", "both"):
        ok, reason = _send_email_reminder(meeting, client_file, logged_by)
        if ok:
            return True, "Sent"

    return False, reason


def _check_consent(client_file, channel):
    """Check consent including implied consent 2-year expiry.

    CASL requires express or implied consent. Implied consent
    (e.g. existing service relationship) expires after 2 years
    from the date of last interaction.
    """
    if channel == "sms":
        if not client_file.sms_consent:
            return False, "Client has not consented to text reminders"
        if not client_file.has_phone:
            return False, "No phone number on file"
    elif channel == "email":
        if not client_file.email_consent:
            return False, "Client has not consented to email"
        if not client_file.has_email:
            return False, "No email address on file"

    if client_file.consent_type == "implied":
        consent_date = (
            client_file.sms_consent_date if channel == "sms"
            else client_file.email_consent_date
        )
        if consent_date and consent_date < date.today() - timedelta(days=730):
            return False, "Consent expired — please re-confirm with client"

    return True, "OK"


def _record_reminder_status(meeting, status, reason):
    """Update the meeting card's reminder indicator.

    This is what staff see. Use plain language.
    """
    meeting.reminder_status = status
    meeting.reminder_status_reason = reason
    # CRITICAL: Only set reminder_sent=True on actual success.
    # Do NOT mark as sent on failure — the cron job must retry.
    if status == "sent":
        meeting.reminder_sent = True
    meeting.save(update_fields=["reminder_status", "reminder_status_reason", "reminder_sent"])


PLAIN_LANGUAGE_ERRORS = {
    "TwilioRestException": "Text messaging service is temporarily unavailable",
    "21211": "This phone number doesn't appear to be valid",
    "21614": "This phone number can't receive text messages",
    "21610": "This number has opted out of text messages",
    "30003": "The phone may be turned off or out of service",
    "30005": "Unknown phone number",
    "30006": "Phone number can't be reached — it may no longer be in service",
}


def _translate_error(error):
    """Turn technical errors into language a case worker understands."""
    error_str = str(error)
    for code, message in PLAIN_LANGUAGE_ERRORS.items():
        if code in error_str:
            return message
    return "Text could not be delivered — try confirming the phone number with the client"
```

### 4D. Message templates — configurable, bilingual, safety-conscious

**Admin-configurable templates** stored in InstanceSettings (not hardcoded in template files). Consultant sets these during setup. Defaults provided.

**SMS default (English):**
> Reminder: You have an appointment tomorrow at {time}. Call {org_phone} if you need to reschedule. Reply STOP to opt out.

**SMS default (French):**
> Rappel : Vous avez un rendez-vous demain a {time}. Appelez le {org_phone} pour reporter. Repondez STOP pour vous desinscrire.

**Safety rules for SMS:**
- No PII — no client name, no staff name, no service details
- Org display name is configurable — sensitive services use a neutral name
- 160 chars max per segment (cost control)
- CASL opt-out instruction included

**Email templates** can be more detailed (include org name, mailing address, unsubscribe link) but still no sensitive service details in the subject line.

Template selection uses `client_file.preferred_language`.

### 4E. Unsubscribe mechanism

**Email:** Use Django's `signing` module to create a token-based unsubscribe URL. `django.core.signing.dumps({"client_id": ..., "channel": "email"}, salt="unsubscribe")` with `max_age=60*60*24*60` (60 days). When clicked, sets `email_consent=False` and `email_consent_withdrawn_date=today()`. No extra model needed.

**SMS:** Include "Reply STOP to opt out" in messages. Twilio handles STOP/START automatically at the carrier level. Also include "Call {org_phone} to unsubscribe" as a fallback.

### 4F. Send Reminder view — preview before sending

**File:** `apps/communications/views.py`

- `send_reminder(request, meeting_id)` — shows a preview of the message that will be sent, with an optional personal note field
- Staff sees: "This will send a text to Maria's phone (***-**42): [preview of message]. Add a personal note (optional): [___________]"
- Staff clicks "Send" → immediate feedback: "Reminder sent" or "Could not send — [plain language reason]"
- Result updates the meeting card's reminder status

**Personal note:** If staff adds a note, it's appended to the template: "Reminder: You have an appointment tomorrow at 2 PM. — Looking forward to seeing you, Sarah." This preserves the relationship touchpoint.

### 4G. Feature toggles

**File:** `apps/admin_settings/models.py` (via FeatureToggle)

- `messaging_email` — enables outbound email
- `messaging_sms` — enables outbound SMS

UI behaviour:
- Both off: hide "Send Reminder" button, only show "Log Communication"
- One on: show only that channel option
- Both on: show channel selector defaulting to client's preference

### 4H. System health visibility — failures where staff look

**This is the most important operational feature in the entire plan.**

#### On the meeting card (staff sees every day):

| Reminder status | What staff sees |
|-----------------|-----------------|
| `not_sent` | "No reminder sent yet" + [Send Reminder] button |
| `sent` | "Reminder sent by text" (or email) + date |
| `failed` | "Text couldn't be delivered — phone may not be in service. Try confirming the number with the client." |
| `blocked` | "Reminder not sent — no consent on file" or "No phone number on file" |
| `no_consent` | "Client hasn't consented to text reminders" |
| `no_phone` | "No phone number on file for this client" |

#### On the staff meeting dashboard (seen daily):

A banner appears **only when something is wrong:**

- **Yellow banner** (failures in last 24 hours): "{N} appointment reminders couldn't be sent yesterday. [View details]" — links to a filtered list of meetings with failed reminders.
- **Red banner** (SMS broken for 3+ days): "Text message reminders haven't been working since {date}. Email reminders are still going through. Please contact {support_contact_name} at {support_contact_phone}."
- **No banner** when everything is working. Silence means healthy.

#### Automated alert email (nobody needs to check anything):

If SMS has been failing for 24+ hours, the system sends an email to the admin contact (ED or office manager) via Google Workspace SMTP: "KoNote text message reminders have not been working since [date]. [N] reminders could not be sent. Email reminders are still working. Please contact [support person] at [phone]."

This email uses the same SMTP that's already configured — no extra infrastructure.

#### How the system tracks health:

A lightweight `SystemHealthCheck` model or cache entry:
- `last_sms_success_at` — updated on every successful SMS send
- `last_sms_failure_at` — updated on every failed SMS send
- `consecutive_sms_failures` — counter, reset on success
- Same for email

The dashboard queries this to decide which banner to show. The daily cron checks it to decide whether to send the alert email.

### 4I. CASL compliance in the send flow

Before every outbound message, the services layer checks:
1. Client has consent for this channel
2. Consent is not expired (implied consent: 2 years)
3. Message template includes org identifier and opt-out
4. If any check fails, message is blocked and staff sees why (on the meeting card)

### 4J. Admin settings page

Consultant configures during setup:
- SMS sender display name (alphanumeric sender ID)
- Default reminder templates (English + French)
- Organisation mailing address (for email CASL footer)
- Default "from" name and reply-to email
- Support contact name and phone (displayed in error messages)
- How far in advance to send reminders (default: 24 hours)

### 4K. Tests

- Send SMS with consent: succeeds, Communication created, meeting card shows "sent"
- Send SMS without consent: blocked, meeting card shows "no consent"
- Send SMS with bad number: failed, meeting card shows plain-language error
- Send email with consent: succeeds
- Send email without consent: blocked
- Consent expiry blocks sending + shows reason
- Feature toggle disabled: Send Reminder button hidden
- System health banner appears after consecutive failures
- Alert email sent after 24h of SMS failure
- Personal note appended to template correctly
- French template used for francophone client
- Unsubscribe URL works and withdraws consent

---

## Phase 5: Automated Reminders

**Goal:** System automatically sends reminders for upcoming meetings. Staff don't have to click "Send Reminder" for every appointment.

**Pre-requisite:** Only implement after Phase 4's manual "Send Reminder" has been used for at least 1-2 months and the org confirms they want automation.

### 5A. Management command

**File:** `apps/communications/management/commands/send_reminders.py`

```python
class Command(BaseCommand):
    help = "Send appointment reminders for meetings in the next 36 hours"

    def handle(self, *args, **options):
        # 36-hour window: if cron misses a run, next run catches up
        cutoff = now() + timedelta(hours=36)
        meetings = Meeting.objects.filter(
            status="scheduled",
            event__start_timestamp__gte=now(),
            event__start_timestamp__lte=cutoff,
            reminder_sent=False,
        ).select_related("event", "event__client_file")

        sent = 0
        failed = 0
        blocked = 0

        for meeting in meetings:
            success, reason = send_reminder(meeting, logged_by=None)
            # CRITICAL: send_reminder() handles reminder_sent flag.
            # Only set True on success. Failed = retry next run.
            if success:
                sent += 1
            elif "consent" in reason.lower() or "no phone" in reason.lower():
                blocked += 1
            else:
                failed += 1

        self.stdout.write(
            f"Reminders: {sent} sent, {failed} failed, {blocked} blocked"
        )

        # Update system health tracking
        if failed > 0:
            _update_health_check("sms", success=False)
        if sent > 0:
            _update_health_check("sms", success=True)

        # Send alert email if SMS has been failing for 24+ hours
        _check_and_send_health_alert()
```

**Key fix from panel review:** `reminder_sent` is ONLY set to `True` on successful send (handled in `_record_reminder_status()`). Failed reminders remain `reminder_sent=False` so the next cron run retries them. This fixes the bug in the original plan where failures were marked as sent.

### 5B. Scheduling

Railway cron job: `python manage.py send_reminders` — runs every 6 hours (catches up if a run is missed thanks to the 36-hour window).

No Celery, no Django-Q, no Redis. A management command on a cron schedule.

### 5C. Tests

- Reminder sent for meeting in next 24h
- Reminder NOT re-sent (reminder_sent flag)
- Failed reminder retried on next run
- Reminder not sent if meeting cancelled
- Reminder not sent if no consent (blocked, not failed)
- System health updated after each batch
- Alert email sent after sustained failure

---

## Phase 6 (Future): Background Task Queue

**Not needed initially.** The management command handles automated reminders without a task queue. Add Django-Q2 only when:
- Sending individual messages becomes too slow (synchronous Twilio calls)
- You need complex retry logic
- You need scheduled tasks beyond daily cron

When that time comes:
- **Django-Q2** (stores tasks in existing database, no Redis needed)
- Wrap `send_reminder()` in `async_task()` calls
- Services layer already supports this — no rewrite needed

---

## Phase 7 (Future): Calendar Push & WhatsApp

### Calendar push

The iCal feed (Phase 1G) covers most needs. Add Microsoft Graph or Google Calendar API push only if orgs report the iCal refresh delay (30min-24hr) is unacceptable.

### WhatsApp

Available through Twilio with minimal code changes. The Communication model already includes `whatsapp` channel choice. However:
- Requires Meta Business Account verification (1-4 weeks)
- Outbound messages require pre-approved templates
- ~40-50% of Canadians use WhatsApp (vs ~100% for SMS)
- Best suited for orgs serving newcomer/immigrant communities
- Build SMS first, add WhatsApp later when there's demand

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Meeting model | Separate `Meeting` with OneToOneField to `Event` | Keeps Event clean, avoids nullable fields |
| Communications app | `apps/communications/` (new app) | Prevents events/ from becoming a god-app |
| Communication model | Single model with direction/channel/method | One timeline, one audit trail, extensible |
| Service layer | `apps/communications/services.py` | Separates business logic from views, docstrings explain rules for AI maintainer |
| Email backend | Django SMTP with Google Workspace | Org already has it, no new account, Canadian data residency |
| SMS provider | Twilio | Industry standard, Python SDK, Canadian numbers, WhatsApp upgrade path |
| Background tasks | Management command first, Django-Q2 later | Simplest approach; clear upgrade path |
| Calendar integration | iCal feed first, API push later | 80% of value for 10% of complexity |
| PII in calendar feeds | Initials + record ID only | Privacy by design |
| PII in SMS | No PII, configurable sender name | SMS stored by carriers, visible on lock screens, org name may be sensitive |
| Consent UI | One checkbox at intake, full CASL model in DB | Staff won't fill in 9 fields during intake |
| Consent enforcement | Check even for transactional messages | Best practice, PIPEDA compliance, future-proofs for promotional messages |
| Error messages | Plain language, on the meeting card | Staff have no IT support; failures must be self-explanatory |
| System health | Banner on dashboard + alert email | Nobody checks admin panels; failures push to where staff already look |
| Message templates | Admin-configurable, bilingual (EN/FR) | Different orgs need different messages; Ontario serves francophone clients |
| Phone staleness | `phone_last_confirmed` date + visual nudge | Marginalized populations change numbers frequently |
| Funder reporting | Always-visible count on dashboard | EDs need this for grant reports without running queries |

---

## Files Created/Modified Summary

### New app: `apps/communications/`
- `apps/communications/__init__.py`
- `apps/communications/apps.py`
- `apps/communications/models.py` — Communication model
- `apps/communications/forms.py` — QuickLogForm, CommunicationLogForm, SendMessageForm
- `apps/communications/views.py` — quick-log, full log, send reminder, timeline integration
- `apps/communications/urls.py`
- `apps/communications/services.py` — send logic with plain-language error translation
- `apps/communications/admin.py`
- `apps/communications/management/commands/send_reminders.py`
- `apps/communications/tests/test_communications.py`
- `apps/communications/tests/test_notifications.py`

### New files (events app)
- `apps/events/tests/test_meetings.py`
- `apps/events/tests/test_ical_feed.py`

### New templates
- `templates/events/meeting_list.html` — staff dashboard with health banner
- `templates/events/meeting_form.html` — quick-create (3 fields) / full edit
- `templates/events/_meeting_card.html` — card with reminder status in plain language
- `templates/events/_meeting_status.html` — HTMX status toggle
- `templates/events/calendar_feed_settings.html` — iCal feed URL + instructions
- `templates/communications/_quick_log_buttons.html` — quick-action button row
- `templates/communications/_quick_log_form.html` — HTMX inline form
- `templates/communications/communication_log_form.html` — full log form
- `templates/communications/_communication_card.html` — timeline partial
- `templates/communications/send_reminder_preview.html` — preview + personal note
- `templates/notifications/unsubscribe.html` — email unsubscribe landing page

### Modified files
- `apps/events/models.py` — Meeting model (with reminder_status), CalendarFeedToken
- `apps/events/forms.py` — MeetingForm (quick-create variant)
- `apps/events/views.py` — meeting CRUD, calendar feed, timeline pagination
- `apps/events/urls.py` — meeting URLs
- `apps/clients/models.py` — email, consent, contact preference, phone_last_confirmed, preferred_language
- `apps/clients/forms.py` — consent checkbox, email field, language preference
- `apps/auth_app/permissions.py` — meeting and communication permissions
- `konote/settings/base.py` — SMTP, Twilio, SMS, sensitive settings filter
- `konote/urls.py` — calendar feed URL, communications app URLs
- `requirements.txt` — icalendar, twilio
- `templates/events/event_list.html` — communications in timeline, pagination
- `templates/clients/client_detail.html` — consent, contact preferences, phone staleness

### New documentation
- `docs/operations-runbook.md` — consultant handoff document

---

## Parallel Execution Schedule

### Wave 1 (no file conflicts)

| Agent | Phase | Files Touched | Depends On |
|-------|-------|---------------|------------|
| **Agent A** | Phase 1A-F: Meetings + iCal | `events/models.py`, `events/forms.py`, `events/views.py`, `events/urls.py`, meeting templates, `requirements.txt` (icalendar) | Nothing |
| **Agent B** | Phase 3: Consent & Contact & Language | `clients/models.py`, `clients/forms.py`, client templates | Nothing |
| **Agent C** | Phase 2A: Communications app scaffold | NEW `communications/` app (models, forms, admin, apps.py) | Nothing |

All three agents touch completely different files.

**Important:** Do NOT parallelize migration creation. After all three agents finish, create and apply migrations sequentially in one step.

### Wave 2 (after Wave 1)

| Agent | Phase | Files Touched | Depends On |
|-------|-------|---------------|------------|
| **Agent D** | Phase 2B-J: Communication log views + quick-log + timeline | `communications/views.py`, `communications/urls.py`, communication templates, `events/views.py` (timeline merge) | Wave 1 Agent C (Communication model) |
| **Agent E** | Phase 4A-C: Settings + services layer | `settings/base.py`, `requirements.txt` (twilio), `communications/services.py`, notification templates | Wave 1 Agents B + C (consent fields + Communication model) |

### Wave 3 (after Wave 2)

| Agent | Phase | Files Touched | Depends On |
|-------|-------|---------------|------------|
| **Agent F** | Phase 4D-K: Send views + feature toggles + health banners + unsubscribe | `communications/views.py`, `admin_settings/`, `auth_app/permissions.py`, send templates, dashboard banner | Wave 2 (services.py must exist) |

### Wave 4 (after org has used manual send for 1-2 months)

| Agent | Phase | Files Touched | Depends On |
|-------|-------|---------------|------------|
| **Agent G** | Phase 5: Automated reminders | `communications/management/commands/send_reminders.py`, tests | Phase 4 proven in production |

### Wave 5 (integration)

| Task | Description |
|------|-------------|
| RBAC permissions | Add all new permission keys (one file, do once) |
| Integration tests | Full test suite across all features |
| Translations | Run `translate_strings` for new template strings |
| Migration consolidation | Verify all migrations apply cleanly in sequence |
