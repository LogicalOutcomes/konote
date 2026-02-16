# KoNote Web — Technical Documentation

This document provides a comprehensive technical reference for developers, system administrators, and AI assistants working with the KoNote Web codebase.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Database Architecture](#database-architecture)
4. [Django Apps](#django-apps)
5. [Models Reference](#models-reference)
6. [Security Architecture](#security-architecture)
7. [Authentication](#authentication)
8. [Middleware Pipeline](#middleware-pipeline)
9. [URL Structure](#url-structure)
10. [Context Processors](#context-processors)
11. [Forms & Validation](#forms--validation)
12. [Frontend Stack](#frontend-stack)
13. [AI Integration](#ai-integration)
14. [Management Commands](#management-commands)
15. [Configuration Reference](#configuration-reference)
16. [Testing](#testing)
17. [Development Guidelines](#development-guidelines)
18. [Extensions & Customization](#extensions--customization)

---

## Architecture Overview

KoNote Web is a Django 5.1 application following a server-rendered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Browser                          │
│  (Django Templates + HTMX + Pico CSS + Chart.js)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Reverse Proxy (Caddy)                     │
│              TLS termination, HTTP/2, compression            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Django Application                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   Middleware Stack                      │ │
│  │  Security → Session → CSRF → Auth → Access → Audit     │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   View Layer                            │ │
│  │  Function-based views with form validation             │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   Model Layer                           │ │
│  │  Encrypted fields, audit trails, RBAC                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   Main PostgreSQL DB    │     │   Audit PostgreSQL DB   │
│  (clients, programs,    │     │  (immutable audit log)  │
│   plans, notes, etc.)   │     │  INSERT-only access     │
└─────────────────────────┘     └─────────────────────────┘
```

### Design Principles

1. **Server-rendered first** — No SPA, minimal JavaScript
2. **Encryption at rest** — All PII encrypted before database storage
3. **Audit everything** — Separate, append-only audit database
4. **Role-based access** — Program-scoped permissions
5. **Simple stack** — Django templates, HTMX for interactivity
6. **AI-friendly** — Clear code structure for AI-assisted development

---

## Project Structure

```
KoNote-web/
├── konote/                    # Project configuration
│   ├── settings/
│   │   ├── base.py            # Shared settings
│   │   ├── production.py      # Production overrides
│   │   ├── development.py     # Development overrides
│   │   └── test.py            # Test runner config
│   ├── middleware/
│   │   ├── audit.py           # AuditMiddleware
│   │   ├── program_access.py  # ProgramAccessMiddleware
│   │   └── terminology.py     # TerminologyMiddleware
│   ├── encryption.py          # Fernet encrypt/decrypt helpers
│   ├── db_router.py           # AuditRouter for dual-database
│   ├── context_processors.py  # Template context injection
│   ├── ai.py                  # OpenRouter API integration
│   ├── urls.py                # Root URL configuration
│   └── wsgi.py                # WSGI application
│
├── apps/                      # Django applications
│   ├── auth_app/              # User, Invite, Azure AD SSO
│   ├── programs/              # Program, UserProgramRole
│   ├── clients/               # ClientFile, custom fields, erasure, merge
│   ├── plans/                 # PlanSection, PlanTarget, Metrics
│   ├── notes/                 # ProgressNote, MetricValue
│   ├── events/                # Event, EventType, Alert, Meeting
│   ├── communications/        # Communication logging, reminders, staff messages
│   ├── groups/                # Group sessions, attendance, projects
│   ├── registration/          # Self-service registration links
│   ├── portal/                # Participant-facing portal
│   ├── admin_settings/        # Terminology, Features, Settings
│   ├── audit/                 # AuditLog (separate DB)
│   └── reports/               # CSV export, charts, PDFs, insights
│
├── templates/                 # Django templates (by app)
│   ├── base.html              # Base template with layout
│   ├── auth_app/              # Login, registration
│   ├── clients/               # Client list, detail, forms
│   ├── plans/                 # Plan sections, targets
│   ├── notes/                 # Progress notes
│   └── ...
│
├── static/
│   ├── css/                   # Pico CSS customisations
│   └── js/
│       └── app.js             # HTMX utilities, error handling
│
├── tests/                     # pytest test suite
├── docs/                      # Documentation
├── seeds/                     # Demo/seed data
│
├── Dockerfile                 # Container build
├── docker-compose.yml         # Local development stack
├── railway.json               # Railway deployment config
├── entrypoint.sh              # Container startup script
├── requirements.txt           # Python dependencies
└── manage.py                  # Django CLI
```

---

## Database Architecture

### Dual-Database Strategy

KoNote Web uses two PostgreSQL databases:

| Database | Purpose | Access Pattern |
|----------|---------|----------------|
| **Main** | Application data (clients, programs, notes) | Full CRUD |
| **Audit** | Immutable audit log | INSERT only |

### Database Router

The `AuditRouter` class (`konote/db_router.py`) routes queries:

```python
class AuditRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'audit':
            return 'audit'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'audit':
            return 'audit'
        return 'default'
```

### Running Migrations

```bash
# Main database
python manage.py migrate

# Audit database
python manage.py migrate --database=audit
```

### Backups

Both databases should be backed up regularly. See [Backup & Restore Guide](backup-restore.md) for:
- Manual backup commands for Docker Compose, Railway, and Azure
- Automated backup scripts (Windows Task Scheduler, cron)
- Cloud storage integration (Azure Blob, S3, Google Cloud)
- Monitoring and alerting for backup failures

### PostgreSQL Role Security

For production, the audit database user should have INSERT-only permissions:

```sql
-- Create audit user with limited permissions
CREATE USER konote_audit WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE konote_audit TO konote_audit;
GRANT USAGE ON SCHEMA public TO konote_audit;
GRANT INSERT ON audit_auditlog TO konote_audit;
GRANT USAGE, SELECT ON SEQUENCE audit_auditlog_id_seq TO konote_audit;
-- No UPDATE, DELETE, or TRUNCATE permissions
```

---

## Django Apps

### auth_app
**Purpose:** Authentication and user management

| Model | Description |
|-------|-------------|
| `User` | Custom user with Azure AD support, encrypted email |
| `Invite` | Single-use registration links with role pre-assignment |
| `UserProgramRole` | Links users to programs with roles |

**Key Views:**
- `login_view` — Local username/password login
- `azure_login` / `azure_callback` — Azure AD SSO flow
- `register_from_invite` — Accept invite and create account
- `user_list` / `user_create` / `user_edit` — User management (admin)
- `invite_list` / `invite_create` — Invite management (admin)

### programs
**Purpose:** Organisational units and staff assignment

| Model | Description |
|-------|-------------|
| `Program` | Service line (Housing, Employment, etc.) |
| `UserProgramRole` | Role assignment (front_desk, staff, program_manager) |

### clients
**Purpose:** Client records and custom fields

| Model | Description |
|-------|-------------|
| `ClientFile` | Encrypted PII, status, program enrolments |
| `ClientProgramEnrolment` | Many-to-many: client ↔ program |
| `CustomFieldGroup` | Logical grouping of custom fields |
| `CustomFieldDefinition` | Field schema (type, required, choices) |
| `ClientDetailValue` | EAV pattern for custom field values |

### plans
**Purpose:** Outcome tracking structure

| Model | Description |
|-------|-------------|
| `PlanSection` | Category of goals (Housing, Employment) |
| `PlanTarget` | Individual goal/outcome |
| `PlanTargetRevision` | Immutable revision history |
| `MetricDefinition` | Reusable measurement type |
| `PlanTargetMetric` | Links metrics to targets |
| `PlanTemplate` | Reusable plan structure |

### notes
**Purpose:** Progress documentation

| Model | Description |
|-------|-------------|
| `ProgressNote` | Note record (quick or full) |
| `ProgressNoteTemplate` | Reusable note structure |
| `ProgressNoteTarget` | Note linked to specific target |
| `MetricValue` | Individual metric measurement |

### events
**Purpose:** Client timeline

| Model | Description |
|-------|-------------|
| `Event` | Discrete occurrence (intake, discharge) |
| `EventType` | Category with colour coding |
| `Alert` | Safety/care notes on client file |
| `AlertCancellationRecommendation` | Two-person safety rule for alert cancellation |
| `Meeting` | Scheduled client meeting (OneToOne with Event) |
| `CalendarFeedToken` | Token-based iCal feed authentication |

### communications
**Purpose:** Client interaction logging, messaging, and staff-to-staff messages

| Model | Description |
|-------|-------------|
| `Communication` | Logged interaction (phone, email, SMS, in-person, portal, WhatsApp) with encrypted content. Tracks direction (inbound/outbound), method (manual log, staff sent, system sent), delivery status, and call outcome. |
| `SystemHealthCheck` | Tracks SMS/email delivery health for staff-visible banners. One row per channel, updated on every send attempt. Triggers admin alert emails after 24 hours of sustained failures. |
| `StaffMessage` | Staff-to-staff messages about participants (e.g., "Mike called, wants to reschedule"). Content is encrypted. Can be targeted to a specific staff member or left unassigned for any case worker. Statuses: unread, read, archived. |

**Key Views:**
- `quick_log` — Deprecated redirect; contact logging has moved to Quick Notes
- `communication_log` — Deprecated redirect; contact logging has moved to Quick Notes
- `compose_email` — Compose and send a free-form email to a participant (with preview step)
- `send_reminder_preview` — Preview and send meeting reminder (SMS or email) with personal note
- `email_unsubscribe` — Public token-based consent withdrawal (no login required)
- `leave_message` — Leave a staff-to-staff message about a participant
- `client_messages` — View messages for a specific client (scoped to current user or unassigned)
- `mark_message_read` — Mark a staff message as read (HTMX endpoint)
- `my_messages` — Dashboard showing all unread messages for the current staff member

**Services Layer** (`apps/communications/services.py`):
- `check_consent(client, channel)` — CASL consent verification
- `can_send(client, channel)` — Full pre-send check chain (safety mode → profile → toggle → consent → contact info)
- `send_reminder(meeting, logged_by, personal_note)` — Orchestrates SMS/email delivery
- `send_staff_email(client_file, subject, body_text, logged_by, ...)` — Send a free-form email from staff
- `send_sms(phone, body)` — Twilio integration
- `send_email_message(email, subject, body_text, body_html)` — Django SMTP
- `render_message_template(template_key, client, meeting)` — Render SMS/email templates with participant data
- `check_and_send_health_alert()` — Check messaging channel health and alert admins if channels are failing

### admin_settings
**Purpose:** Instance configuration

| Model | Description |
|-------|-------------|
| `TerminologyOverride` | Custom vocabulary |
| `FeatureToggle` | Enable/disable features |
| `InstanceSetting` | Branding, session timeout, etc. |

### audit
**Purpose:** Compliance logging

| Model | Description |
|-------|-------------|
| `AuditLog` | Append-only log entry |

### reports
**Purpose:** Data export and visualisation

- Metric CSV export with filters
- Client data export (all PII, custom fields, enrolments)
- Funder report export
- Client analysis charts (Chart.js)
- PDF reports (WeasyPrint)
- Outcome Insights dashboard (program-level and client-level)
- Team meeting view (client summary for case conferences)
- Secure export links with time-limited, token-based download URLs

### groups
**Purpose:** Group-based service delivery and project tracking

| Model | Description |
|-------|-------------|
| `Group` | A group or project linked to a program. Types: `group` (attendance and session notes) or `project` (goal-oriented with milestones and outcomes). |
| `GroupMembership` | Links a client (or named non-client) to a group with a role (member or leader). |
| `GroupSession` | A single session for a group — date, facilitator, group vibe rating, encrypted notes. |
| `GroupSessionAttendance` | Per-member attendance for a session (defaults to present — facilitator unchecks absentees). |
| `GroupSessionHighlight` | Individual observation about a member during a session (encrypted). |
| `ProjectMilestone` | A milestone within a project-type group — title, status, due date, completion date. |
| `ProjectOutcome` | A recorded result or outcome for a project — description, evidence, date. |

**Key Views:**
- `group_list` — List all groups the user has access to
- `group_detail` — Group detail with members, sessions, and (for projects) milestones and outcomes
- `group_create` / `group_edit` — Create and edit groups
- `session_log` — Log a group session with attendance, notes, and member highlights
- `membership_add` / `membership_remove` — Manage group membership
- `milestone_create` / `milestone_edit` — Create and edit project milestones
- `outcome_create` — Record project outcomes
- `attendance_report` — Attendance summary for a group

### registration
**Purpose:** Self-service program registration via shareable links

| Model | Description |
|-------|-------------|
| `RegistrationLink` | A shareable URL for public program registration. Configurable with custom field groups, capacity limits, deadlines, and auto-approve option. |
| `RegistrationSubmission` | A submitted registration with encrypted PII, custom field values, and status tracking (pending, approved, rejected, waitlisted). Includes email hash for duplicate detection. |

**Key Views (public, no login required):**
- `public_registration_form` — Renders the registration form for a given link slug
- `registration_submitted` — Confirmation page after submission

**Key Views (admin, login required):**
- `link_list` / `link_create` / `link_edit` / `link_delete` — Manage registration links
- `link_embed` — Get embed code for the registration link
- `submission_list` — View all submissions across links
- `submission_detail` — Review a single submission
- `submission_approve` / `submission_reject` / `submission_waitlist` — Change submission status
- `submission_merge` — Merge a submission with an existing client record

### portal
**Purpose:** Participant-facing portal for viewing goals, progress, and communicating with staff

The portal is a separate interface for participants (clients). It uses its own authentication system (`ParticipantUser`) with a separate session key — participants are not Django `User` objects and do not have access to the staff interface.

| Model | Description |
|-------|-------------|
| `ParticipantUser` | Portal login account linked to a `ClientFile` via OneToOne. Email stored as HMAC-SHA-256 hash (for lookup) and Fernet-encrypted (for display). Supports TOTP-based MFA, account lockout, and preferred language. |
| `PortalInvite` | Single-use invite for a participant to create a portal account. Includes a secure URL token, optional verbal verification code, expiry date, and consent screen tracking. |
| `ParticipantJournalEntry` | Private journal entry written by a participant (encrypted). Optionally linked to a plan target. |
| `ParticipantMessage` | Message from a participant to staff. Types: `general` or `pre_session` (what the participant wants to discuss next time). Encrypted at rest. |
| `StaffPortalNote` | Note from staff visible in the participant's portal dashboard (encrypted). |
| `CorrectionRequest` | Participant request to correct data in their record (PHIPA/PIPEDA right of correction). Data types: goal, metric, reflection. Staff review and record outcome. |

**Portal Views (participant-facing, at `/my/`):**
- `portal_login` / `portal_logout` / `emergency_logout` — Authentication (including panic/safety button)
- `accept_invite` — Accept a portal invite and create an account
- `consent_flow` — Multi-screen privacy consent after registration
- `mfa_setup` / `mfa_verify` — TOTP multi-factor authentication
- `dashboard` — Participant home page with greeting, highlights, and new-since-last-visit count
- `goals_list` / `goal_detail` — View plan sections and targets with progress charts
- `progress_view` — Overall progress charts for all portal-visible metrics
- `my_words` — Participant reflections and client words from progress notes
- `milestones` — Completed goals
- `journal_list` / `journal_create` / `journal_disclosure` — Private journal with one-time privacy notice
- `message_create` — Send a message to staff
- `discuss_next` — Pre-session prompt ("What I want to discuss next time")
- `correction_request_create` — Request a correction to recorded information
- `settings_view` / `password_change` — Account settings
- `password_reset_request` / `password_reset_confirm` — Password recovery flow
- `safety_help` — Pre-auth safety page (private browsing guidance, emergency logout info)

**Staff-Side Portal Views (at `/clients/<id>/portal*`):**
- `portal_manage` — View portal access status, invites, and pending corrections for a participant
- `create_portal_invite` — Generate a portal invite with optional verbal verification code
- `create_staff_portal_note` — Write a note visible in the participant's portal
- `portal_revoke_access` — Deactivate a participant's portal account
- `portal_reset_mfa` — Reset MFA for a participant's account

**Security Architecture:**
- Separate session key (`_portal_participant_id`) — participant sessions do not overlap with staff sessions
- Every view scopes queries to `request.participant_user.client_file` — no cross-client data access
- MFA challenge expires after 5 minutes with a maximum of 5 attempts
- Account lockout after 5 failed login attempts (15-minute lockout)
- All portal actions are audit-logged with `[portal]` user_display prefix
- Feature-gated: the entire `/my/` URL namespace returns 404 if the `participant_portal` toggle is disabled

---

## Models Reference

### User Model

```python
class User(AbstractUser):
    # Azure AD integration
    external_id = models.CharField(max_length=255, unique=True, null=True)

    # Encrypted fields
    _email_encrypted = models.BinaryField(null=True)

    # Roles
    is_admin = models.BooleanField(default=False)

    @property
    def email(self):
        return decrypt_field(self._email_encrypted)

    @email.setter
    def email(self, value):
        self._email_encrypted = encrypt_field(value)
```

### ClientFile Model

```python
class ClientFile(models.Model):
    record_id = models.CharField(max_length=50, unique=True)

    # Encrypted PII
    _first_name_encrypted = models.BinaryField()
    _last_name_encrypted = models.BinaryField()
    _date_of_birth_encrypted = models.BinaryField(null=True)

    # Status
    status = models.CharField(choices=STATUS_CHOICES, default='active')

    # Relationships
    programs = models.ManyToManyField(Program, through='ClientProgramEnrolment')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
```

**Consent & Contact Fields (added for messaging):**
- `phone`, `email` — Encrypted PII (property accessors)
- `has_phone`, `has_email` — Boolean flags for quick existence checks without decryption
- `sms_consent`, `email_consent` — CASL consent booleans
- `sms_consent_date`, `email_consent_date` — When consent was given
- `consent_messaging_type` — `"express"` or `"implied"` (implied expires after 2 years per CASL)
- `sms_consent_withdrawn_date`, `email_consent_withdrawn_date` — Proof of withdrawal
- `preferred_language` — `"en"` or `"fr"` for message templates
- `preferred_contact_method` — `"sms"`, `"email"`, `"both"`, `"none"`

### AuditLog Model

```python
class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField(null=True)
    user_email = models.CharField(max_length=255)
    action = models.CharField(max_length=50)  # CREATE, READ, UPDATE, DELETE
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, null=True)
    ip_address = models.GenericIPAddressField(null=True)
    changes = models.JSONField(null=True)  # {field: {old: x, new: y}}
    metadata = models.JSONField(null=True)

    class Meta:
        app_label = 'audit'
        managed = True
```

---

## Security Architecture

### Encryption

All personally identifiable information (PII) is encrypted at the application level using Fernet (AES-128-CBC + HMAC-SHA256).

**Encrypted fields include:**
- Client first/last name
- Client date of birth
- User email
- Custom field values marked as sensitive

**Implementation:**

```python
# konote/encryption.py
from cryptography.fernet import Fernet
from django.conf import settings

_fernet = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())

def encrypt_field(value):
    if value is None:
        return None
    return _fernet.encrypt(value.encode())

def decrypt_field(encrypted_value):
    if encrypted_value is None:
        return None
    return _fernet.decrypt(encrypted_value).decode()
```

**Important limitation:** Encrypted fields cannot be searched in SQL. Client search loads accessible records into Python and filters in-memory. This works well up to ~2,000 clients.

### Role-Based Access Control (RBAC)

| Role | Scope | Permissions |
|------|-------|-------------|
| **Admin** | Instance-wide | Manage settings, users, programs; no client data access without program role |
| **Program Manager** | Assigned programs | Full client access, manage program staff |
| **Staff** | Assigned programs | Full client records in assigned programs |
| **Front Desk** | Assigned programs | Limited client info (name, status) |

**Enforcement:** `ProgramAccessMiddleware` checks every request:

```python
class ProgramAccessMiddleware:
    def __call__(self, request):
        # Admin-only routes
        if request.path.startswith('/admin/'):
            if not request.user.is_admin:
                return HttpResponseForbidden()

        # Client routes require program access
        if '/clients/' in request.path:
            client_id = extract_client_id(request.path)
            if client_id:
                if not user_can_access_client(request.user, client_id):
                    return HttpResponseForbidden()

        return self.get_response(request)
```

**New Permission Keys:**

| Key | Receptionist | Staff | PM | Executive | Description |
|-----|-------------|-------|-----|-----------|-------------|
| `meeting.view` | DENY | SCOPED | ALLOW | DENY | View meetings |
| `meeting.create` | DENY | SCOPED | SCOPED | DENY | Schedule meetings |
| `meeting.edit` | DENY | SCOPED | DENY | DENY | Edit meeting details |
| `communication.log` | DENY | SCOPED | SCOPED | DENY | Log communications |
| `communication.view` | DENY | SCOPED | ALLOW | DENY | View communication history |
| `alert.recommend_cancel` | DENY | SCOPED | SCOPED | DENY | Recommend alert cancellation |
| `alert.review_cancel_recommendation` | DENY | DENY | SCOPED | DENY | Review cancellation recommendations |

### Audit Logging

Every state-changing request is logged to the separate audit database:

| Logged Events | Details Captured |
|---------------|------------------|
| All POST/PUT/PATCH/DELETE | User, timestamp, IP, resource, changes |
| Client record views (GET) | User, timestamp, IP, client ID |
| Login/logout | User, timestamp, IP, success/failure |
| Admin actions | Full change details |

**AuditMiddleware implementation:**

```python
class AuditMiddleware:
    def __call__(self, request):
        response = self.get_response(request)

        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            self.log_request(request, response)
        elif self.is_client_view(request):
            self.log_client_access(request)

        return response

    def log_request(self, request, response):
        AuditLog.objects.using('audit').create(
            user_id=request.user.id,
            user_email=request.user.email,
            action=self.get_action(request.method),
            resource_type=self.get_resource_type(request),
            resource_id=self.get_resource_id(request),
            ip_address=self.get_client_ip(request),
            changes=getattr(request, '_audit_changes', None),
            metadata=getattr(request, '_audit_metadata', None),
        )
```

### HTTP Security Headers

Configured in `settings/production.py`:

```python
# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "unpkg.com")  # HTMX
CSP_STYLE_SRC = ("'self'", "cdn.jsdelivr.net")  # Pico CSS
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_FORM_ACTION = ("'self'",)

# Other headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
```

---

## Authentication

### Local Authentication

Username/password authentication with Argon2 password hashing:

```python
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # Fallback
]
```

### Azure AD SSO

OAuth 2.0 / OpenID Connect flow:

1. User clicks "Login with Azure AD"
2. Redirect to Azure AD authorization endpoint
3. User authenticates with Microsoft
4. Azure AD redirects back with authorization code
5. Server exchanges code for tokens
6. Server validates ID token, extracts user info
7. Create/update local user, establish session

**Configuration:**

```python
# Environment variables
AZURE_CLIENT_ID = 'your-app-client-id'
AZURE_CLIENT_SECRET = 'your-app-secret'
AZURE_TENANT_ID = 'your-tenant-id'
AZURE_REDIRECT_URI = 'https://your-app/auth/callback/'
```

**First-time login:** Azure AD users are auto-created on first login with `is_admin=False`. An admin must grant program roles.

### Invites

Admins create invites with pre-assigned roles:

```python
class Invite(models.Model):
    code = models.CharField(max_length=64, unique=True)
    email = models.EmailField()
    is_admin = models.BooleanField(default=False)
    program_roles = models.JSONField(default=list)  # [{program_id, role}]
    created_by = models.ForeignKey(User)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
```

---

## Middleware Pipeline

Order matters — middleware executes top-to-bottom on request, bottom-to-top on response:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',      # HTTPS headers
    'whitenoise.middleware.WhiteNoiseMiddleware',         # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'konote.middleware.program_access.ProgramAccessMiddleware',  # RBAC
    'konote.middleware.terminology.TerminologyMiddleware',       # Terms
    'konote.middleware.audit.AuditMiddleware',                   # Logging
    'csp.middleware.CSPMiddleware',                              # CSP headers
    'django.contrib.messages.middleware.MessageMiddleware',
]
```

### Custom Middleware

**ProgramAccessMiddleware:**
- Enforces admin-only routes (`/admin/*`)
- Validates client access based on program roles
- Returns 403 Forbidden for unauthorized access

**TerminologyMiddleware:**
- Loads terminology overrides from cache
- Attaches `request.terminology` dict
- Refreshes cache every 5 minutes

**AuditMiddleware:**
- Logs all state-changing requests
- Logs client record views
- Captures IP address, user, changes

---

## URL Structure

### Authentication

```
/auth/login/                    GET, POST   Login form
/auth/logout/                   POST        Logout
/auth/azure/login/              GET         Initiate Azure SSO
/auth/callback/                 GET         Azure callback
/auth/register/invite/<code>/   GET, POST   Accept invite
/auth/users/                    GET         User list (admin)
/auth/users/create/             GET, POST   Create user (admin)
/auth/users/<id>/edit/          GET, POST   Edit user (admin)
/auth/invites/                  GET         Invite list (admin)
/auth/invites/create/           GET, POST   Create invite (admin)
```

### Clients

```
/clients/executive/                             GET         Executive dashboard
/clients/                                       GET         Client list
/clients/create/                                GET, POST   New client
/clients/check-duplicate/                       POST        Duplicate detection (HTMX)
/clients/search/                                GET         Client search (partial)
/clients/<id>/                                  GET         Client detail
/clients/<id>/edit/                             GET, POST   Edit client
/clients/<id>/transfer/                         GET, POST   Transfer client between programs
/clients/<id>/edit-contact/                     GET, POST   Edit contact information
/clients/<id>/confirm-phone/                    POST        Confirm phone number
/clients/<id>/custom-fields/                    POST        Save custom fields
/clients/<id>/custom-fields/display/            GET         Custom fields display partial
/clients/<id>/custom-fields/edit/               GET         Custom fields edit partial
/clients/<id>/consent/display/                  GET         Consent display partial
/clients/<id>/consent/edit/                     GET         Consent edit partial
/clients/<id>/consent/                          POST        Save consent settings
/clients/<id>/erase/                            GET, POST   Create erasure request
/clients/<id>/portal-note/                      GET, POST   Create staff portal note
/clients/<id>/portal-invite/                    GET, POST   Create portal invite
/clients/<id>/portal/                           GET         Manage portal access
/clients/<id>/portal/revoke/                    POST        Revoke portal access
/clients/<id>/portal/reset-mfa/                 POST        Reset portal MFA
/clients/admin/fields/                          GET         Custom field admin
/clients/admin/fields/groups/create/            GET, POST   Create field group
/clients/admin/fields/groups/<id>/edit/         GET, POST   Edit field group
/clients/admin/fields/create/                   GET, POST   Create field definition
/clients/admin/fields/<id>/edit/                GET, POST   Edit field definition
```

### Plans

```
/plans/<section_id>/            GET         Plan section detail
/plans/<id>/targets/            GET         Target list
/plans/<id>/targets/create/     GET, POST   New target
/plans/templates/               GET         Plan templates (admin)
```

### Notes

```
/notes/client/<client_id>/      GET         Notes for client
/notes/create/                  GET, POST   Quick note
/notes/<id>/full/               GET, POST   Full note
/notes/<id>/                    GET         View note
/notes/<id>/cancel/             POST        Cancel note
/notes/templates/               GET         Note templates (admin)
```

### Admin

```
/admin/settings/                                    GET         Settings dashboard
/admin/settings/terminology/                        GET, POST   Terminology overrides
/admin/settings/terminology/reset/<key>/            POST        Reset terminology override
/admin/settings/features/                           GET, POST   Feature toggles
/admin/settings/instance/                           GET, POST   Instance settings
/admin/settings/messaging/                          GET, POST   Messaging settings (SMS/email)
/admin/settings/diagnose-charts/                    GET         Chart diagnostics
/admin/settings/demo-directory/                     GET         Demo user directory
/admin/settings/report-templates/                   GET         Funder report templates
/admin/settings/report-templates/upload/            GET, POST   Upload report template
/admin/settings/report-templates/confirm/           POST        Confirm template upload
/admin/settings/report-templates/sample.csv         GET         Download sample CSV
/admin/settings/report-templates/<id>/              GET         Template detail
/admin/settings/report-templates/<id>/programs/     GET, POST   Edit template programs
/admin/settings/report-templates/<id>/delete/       POST        Delete template
/admin/settings/report-templates/<id>/download/     GET         Download template CSV
/admin/settings/note-templates/                     ...         Note template management
/admin/templates/                                   ...         Plan template management
/admin/users/                                       ...         User management
/admin/audit/                                       GET         Audit log viewer
/admin/audit/export/                                GET         Audit log CSV export
/audit/program/<id>/                                GET         Per-program audit log (PM)
/programs/                                          GET         Program list
/programs/create/                                   GET, POST   New program
/programs/<id>/                                     GET         Program detail
```

### Reports

```
/reports/insights/                                  GET         Program outcome insights
/reports/client/<id>/insights/                      GET         Client insights partial
/reports/export/                                    GET, POST   Metric CSV export
/reports/funder-report/                             GET, POST   Funder report export
/reports/client/<id>/analysis/                      GET         Client analysis charts
/reports/client/<id>/pdf/                           GET         Client progress PDF
/reports/client/<id>/export/                        GET         Client data export
/reports/team-meeting/                              GET         Team meeting view
/reports/download/<uuid>/                           GET         Download secure export link
/reports/export-links/                              GET         Manage export links
/reports/export-links/<uuid>/revoke/                POST        Revoke export link
```

### Communications

```
/communications/client/<id>/quick-log/                          GET         Quick-log (deprecated, redirects)
/communications/client/<id>/log/                                GET         Full log (deprecated, redirects)
/communications/client/<id>/compose-email/                      GET, POST   Compose and send email
/communications/client/<id>/meeting/<event_id>/send-reminder/   GET, POST   Send meeting reminder
/communications/unsubscribe/<token>/                            GET, POST   Unsubscribe (public)
/communications/my-messages/                                    GET         Staff message dashboard
/communications/client/<id>/leave-message/                      GET, POST   Leave staff message
/communications/client/<id>/messages/                           GET         Client messages
/communications/client/<id>/message/<msg_id>/read/              POST        Mark message read (HTMX)
```

### Meetings & Calendar

```
/events/meetings/                                       GET         Staff meeting dashboard
/events/client/<id>/meetings/create/                    GET, POST   Schedule meeting
/events/client/<id>/meetings/<event_id>/                GET, POST   Edit meeting
/events/meetings/<event_id>/status/                     POST        Update status (HTMX)
/events/calendar/settings/                              GET, POST   Calendar feed settings
/calendar/<token>/feed.ics                              GET         iCal feed (public, token auth)
```

### Groups

```
/groups/                                            GET         Group list
/groups/create/                                     GET, POST   Create group
/groups/<id>/                                       GET         Group detail
/groups/<id>/edit/                                  GET, POST   Edit group
/groups/<id>/session/                               GET, POST   Log group session
/groups/<id>/member/add/                            GET, POST   Add group member
/groups/member/<membership_id>/remove/              POST        Remove group member
/groups/<id>/milestone/                             GET, POST   Create milestone (projects)
/groups/milestone/<milestone_id>/edit/              GET, POST   Edit milestone
/groups/<id>/outcome/                               GET, POST   Record outcome (projects)
/groups/<id>/attendance/                            GET         Attendance report
```

### Self-Service Registration

```
/register/<slug>/                                   GET, POST   Public registration form
/register/<slug>/submitted/                         GET         Submission confirmation
/admin/registration/                                GET         Registration link list
/admin/registration/create/                         GET, POST   Create registration link
/admin/registration/<id>/edit/                      GET, POST   Edit registration link
/admin/registration/<id>/delete/                    POST        Delete registration link
/admin/registration/<id>/embed/                     GET         Embed code for link
/admin/submissions/                                 GET         Submission list
/admin/submissions/<id>/                            GET         Submission detail
/admin/submissions/<id>/approve/                    POST        Approve submission
/admin/submissions/<id>/reject/                     POST        Reject submission
/admin/submissions/<id>/waitlist/                   POST        Waitlist submission
/admin/submissions/<id>/merge/                      POST        Merge with existing client
```

### Erasure & Merge

```
/erasure/                                           GET         Pending erasure requests
/erasure/history/                                   GET         Erasure history
/erasure/<id>/                                      GET         Erasure request detail
/erasure/<id>/approve/                              POST        Approve erasure
/erasure/<id>/reject/                               POST        Reject erasure
/erasure/<id>/cancel/                               POST        Cancel erasure
/erasure/<id>/receipt/                              GET         Erasure receipt PDF
/merge/                                             GET         Duplicate merge candidates
/merge/<client_a_id>/<client_b_id>/                 GET, POST   Compare and merge clients
```

### Participant Portal (at `/my/`)

```
/my/login/                                          GET, POST   Participant login
/my/logout/                                         POST        Participant logout
/my/emergency-logout/                               POST        Panic/safety button (sendBeacon)
/my/invite/<token>/                                 GET, POST   Accept portal invite
/my/consent/                                        GET, POST   Consent flow
/my/mfa/setup/                                      GET, POST   TOTP MFA setup
/my/mfa/verify/                                     GET, POST   MFA verification
/my/safety/                                         GET         Safety help page (pre-auth)
/my/password/change/                                GET, POST   Change password
/my/password/reset/                                 GET, POST   Request password reset
/my/password/reset/confirm/                         GET, POST   Confirm password reset
/my/                                                GET         Participant dashboard
/my/settings/                                       GET         Portal settings
/my/goals/                                          GET         Goals list
/my/goals/<target_id>/                              GET         Goal detail with charts
/my/progress/                                       GET         Overall progress charts
/my/milestones/                                     GET         Completed goals
/my/correction/new/                                 GET, POST   Request data correction
/my/journal/                                        GET         Journal entries
/my/journal/new/                                    GET, POST   New journal entry
/my/journal/disclosure/                             GET, POST   Journal privacy notice
/my/message/                                        GET, POST   Message to worker
/my/discuss-next/                                   GET, POST   Pre-session discussion topics
```

### HTMX Endpoints

```
/ai/suggest-metrics/            POST        Metric suggestions
/ai/improve-outcome/            POST        Outcome improvement
/clients/search/                GET         Client search (partial)
/notes/<id>/preview/            GET         Note preview (partial)
```

---

## Context Processors

Every template receives these variables:

```python
# konote/context_processors.py

def terminology(request):
    return {'term': get_cached_terminology()}

def features(request):
    return {'features': get_cached_features()}

def site_settings(request):
    return {'site': get_cached_settings()}

def user_roles(request):
    if request.user.is_authenticated:
        return {
            'has_program_roles': request.user.program_roles.exists(),
            'is_admin_only': request.user.is_admin and not request.user.program_roles.exists(),
        }
    return {}
```

**Usage in templates:**

```html
<h1>{{ term.client }} List</h1>

{% if features.custom_fields %}
  <a href="{% url 'custom_fields' %}">Custom Fields</a>
{% endif %}

<title>{{ site.product_name }}</title>
```

---

## Forms & Validation

All views use Django forms — never raw `request.POST.get()`:

```python
# apps/clients/forms.py

class ClientFileForm(forms.ModelForm):
    class Meta:
        model = ClientFile
        fields = ['record_id', 'first_name', 'last_name', 'date_of_birth']

    def clean_record_id(self):
        record_id = self.cleaned_data['record_id']
        if ClientFile.objects.filter(record_id=record_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('A client with this record ID already exists.')
        return record_id
```

**Form rendering with accessibility:**

```html
<form method="post">
    {% csrf_token %}
    {% for field in form %}
    <label for="{{ field.id_for_label }}">{{ field.label }}</label>
    {{ field }}
    {% if field.errors %}
    <small role="alert" class="error">{{ field.errors.0 }}</small>
    {% endif %}
    {% endfor %}
    <button type="submit">Save</button>
</form>
```

---

## Frontend Stack

### Pico CSS

Classless CSS framework for semantic HTML:

```html
<!-- No classes needed for basic styling -->
<article>
    <header>
        <h2>Client: {{ client.full_name }}</h2>
    </header>
    <p>Status: {{ client.status }}</p>
    <footer>
        <a href="{% url 'client_edit' client.id %}" role="button">Edit</a>
    </footer>
</article>
```

### HTMX

Partial page updates without full reload:

```html
<!-- Load notes without page refresh -->
<div hx-get="{% url 'client_notes' client.id %}"
     hx-trigger="load"
     hx-swap="innerHTML">
    Loading...
</div>

<!-- Submit form via HTMX -->
<form hx-post="{% url 'quick_note' %}"
      hx-target="#notes-list"
      hx-swap="afterbegin">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Add Note</button>
</form>
```

### Chart.js

Progress visualisation:

```html
<canvas id="progress-chart"></canvas>
<script>
const ctx = document.getElementById('progress-chart');
new Chart(ctx, {
    type: 'line',
    data: {
        labels: {{ metric_dates|safe }},
        datasets: [{
            label: '{{ metric_name }}',
            data: {{ metric_values|safe }},
        }]
    }
});
</script>
```

### app.js

Global HTMX error handling:

```javascript
// static/js/app.js
document.body.addEventListener('htmx:responseError', function(event) {
    const target = event.detail.target;
    target.innerHTML = '<div role="alert" class="error">' +
        'An error occurred. Please try again.' +
        '</div>';
});

document.body.addEventListener('htmx:sendError', function(event) {
    alert('Network error. Please check your connection.');
});
```

---

## AI Integration

Optional AI features via OpenRouter API:

### Configuration

```python
# Environment variable
OPENROUTER_API_KEY = 'your-api-key'  # Leave empty to disable
```

### Available Features

| Feature | Endpoint | Purpose |
|---------|----------|---------|
| Metric suggestions | `/ai/suggest-metrics/` | Given a target, suggest relevant metrics |
| Outcome improvement | `/ai/improve-outcome/` | Analyse progress, suggest improvements |
| Note structure | `/ai/note-hints/` | Help structure progress notes |

### Privacy Protection

AI endpoints only receive **metadata**, never client PII:

```python
# konote/ai.py
def suggest_metrics(target_description, program_name):
    # Send only: target text, program name, existing metric names
    # Never send: client names, dates of birth, notes content

    prompt = f"""
    Target: {target_description}
    Program: {program_name}

    Suggest 3-5 measurable metrics for this outcome target.
    """

    return call_openrouter(prompt)
```

---

## Management Commands

KoNote includes several custom management commands for scheduled tasks, maintenance, and deployment. All commands support `--help` for full usage details.

### Scheduled Commands

These commands are intended to run on a schedule (cron, Railway cron, Azure scheduled task, etc.).

#### `send_reminders` — Automated Appointment Reminders

Finds upcoming meetings that have not yet received a reminder and sends SMS or email notifications via the client's preferred contact channel.

```bash
python manage.py send_reminders              # Send reminders for meetings in next 36 hours
python manage.py send_reminders --dry-run    # Preview without sending
python manage.py send_reminders --hours 24   # Custom lookahead window
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dry-run` | off | Show which meetings would get reminders without actually sending |
| `--hours` | 36 | How far ahead to look for upcoming meetings (in hours) |

**Behaviour:**
- Finds meetings with status `scheduled`, `reminder_sent=False`, and start time within the lookahead window
- Sends via the client's preferred contact method (SMS or email) using the `send_reminder()` service
- Skips clients without consent or contact information (logged as "skipped", not counted as failures)
- Failed sends are retried on subsequent runs (the `reminder_sent` flag stays `False`)
- After processing, triggers a system health check and alerts admins if a messaging channel is persistently failing

**Recommended schedule:** Hourly.

**Location:** `apps/communications/management/commands/send_reminders.py`

#### `send_export_summary` — Weekly Export Activity Report

Emails admins a summary of data export activity for compliance monitoring. Shows how many exports were created, who exported what, and whether any exports are pending download or have been revoked.

```bash
python manage.py send_export_summary              # Send email to admins
python manage.py send_export_summary --dry-run     # Preview without sending
python manage.py send_export_summary --days 14     # Custom lookback window
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dry-run` | off | Show the summary without sending the email |
| `--days` | 7 | Number of days to look back for export activity |

**Behaviour:**
- Queries `SecureExportLink` records created within the lookback period
- Breaks down exports by type, counts elevated exports, downloaded vs. pending, and revoked links
- Lists the top 5 exporters by display name
- Sends the summary via email to addresses in `EXPORT_NOTIFICATION_EMAILS` (setting), or falls back to all active admin users
- Uses both plain text and HTML email templates (`reports/email/weekly_export_summary.txt` and `.html`)
- Stateless and idempotent — safe to run multiple times

**Recommended schedule:** Weekly (e.g., Monday morning).

**Location:** `apps/reports/management/commands/send_export_summary.py`

#### `cleanup_expired_exports` — Export File Cleanup

Removes expired secure export links and their associated files from disk. Also cleans up orphan files that have no matching database record.

```bash
python manage.py cleanup_expired_exports          # Delete expired links + orphan files
python manage.py cleanup_expired_exports --dry-run # Preview what would be deleted
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dry-run` | off | Show what would be deleted without actually deleting |

**Behaviour:**
- Deletes `SecureExportLink` records that expired more than 1 day ago (grace period to avoid deleting mid-download)
- Removes the associated file on disk for each deleted record
- Scans the `SECURE_EXPORT_DIR` directory for orphan files with no matching database record and removes them
- Deletes the database record first, then the file — if the file delete fails, the orphan is caught on the next run

**Recommended schedule:** Daily.

**Location:** `apps/reports/management/commands/cleanup_expired_exports.py`

### Utility Commands

These commands are run manually during deployment, maintenance, or development.

| Command | App | Description |
|---------|-----|-------------|
| `security_audit` | `audit` | Run a comprehensive security check (encryption, RBAC, audit log, configuration). See [Security Operations](security-operations.md) for details. |
| `rotate_encryption_key` | `auth_app` | Re-encrypt all PII fields with a new Fernet key. See [Security Operations](security-operations.md#rotating-the-encryption-key). |
| `validate_permissions` | `auth_app` | Verify the permission matrix is consistent and all views reference valid permission keys. |
| `lockdown_audit_db` | `audit` | Generate SQL statements to configure INSERT-only permissions on the audit database. |
| `startup_check` | `audit` | Run at container startup to verify database connectivity and configuration. |
| `check_translations` | `admin_settings` | Verify that all template translation strings have corresponding entries in `.po` files. |
| `translate_strings` | `admin_settings` | Extract translatable strings from templates and compile `.po` → `.mo` files. |
| `preflight` | `admin_settings` | Shared pre-flight checks used by QA skills (database, settings, test data). |
| `seed_demo_data` | `admin_settings` | Populate the database with realistic demo data for presentations and testing. |
| `seed` | `admin_settings` | Lightweight seed command for development setup. |
| `seed_event_types` | `events` | Create default event types (intake, discharge, etc.). |
| `seed_note_templates` | `notes` | Create default progress note templates. |
| `seed_default_funder_profile` | `reports` | Create a default funder report profile. |
| `seed_intake_fields` | `clients` | Create default custom field groups and fields for client intake. |
| `alert_expired_retention` | `clients` | Check for client records past their retention period and flag them for review. |
| `migrate_phone_field` | `clients` | One-time migration helper for phone field encryption changes. |
| `update_demo_client_fields` | `clients` | Update demo client records with fresh test data. |
| `check_document_url` | `admin_settings` | Verify that the document storage URL template is correctly configured. |
| `diagnose_charts` | `admin_settings` | Debug helper for Chart.js metric visualisation issues. |

---

## Configuration Reference

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (50+ random characters) |
| `FIELD_ENCRYPTION_KEY` | Fernet key for PII encryption |
| `DATABASE_URL` | Main PostgreSQL connection string |
| `AUDIT_DATABASE_URL` | Audit PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins for CSRF validation |
| `AUTH_MODE` | `local` or `azure` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode (never in production) |
| `AZURE_CLIENT_ID` | — | Azure AD application ID |
| `AZURE_CLIENT_SECRET` | — | Azure AD client secret |
| `AZURE_TENANT_ID` | — | Azure AD tenant ID |
| `AZURE_REDIRECT_URI` | — | Azure AD callback URL |
| `OPENROUTER_API_KEY` | — | Enable AI features |
| `DEMO_MODE` | `False` | Show quick-login buttons |

### Instance Settings (via admin UI)

| Setting | Description |
|---------|-------------|
| Product Name | Shown in header and page titles |
| Support Email | Contact for user support |
| Logo URL | Organisation logo |
| Date Format | ISO, US, or custom |
| Session Timeout | Inactivity timeout in minutes |

---

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_clients.py

# With coverage
pytest --cov=apps --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py              # Fixtures (users, clients, programs)
├── test_auth_views.py       # Login, registration, SSO
├── test_rbac.py             # Access control enforcement
├── test_clients.py          # Client CRUD, custom fields
├── test_plan_crud.py        # Plan/target/metric management
├── test_notes.py            # Progress notes, metric recording
├── test_programs.py         # Program management
├── test_admin_settings.py   # Terminology, features, settings
├── test_ai_endpoints.py     # AI suggestion endpoints
├── test_encryption.py       # Fernet encryption/decryption
└── test_phase5.py           # Integration scenarios
```

### Key Fixtures

```python
# tests/conftest.py

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin',
        password='testpass',
        is_admin=True
    )

@pytest.fixture
def staff_user(db, program):
    user = User.objects.create_user(username='staff', password='testpass')
    UserProgramRole.objects.create(user=user, program=program, role='staff')
    return user

@pytest.fixture
def client_file(db, program, staff_user):
    client = ClientFile.objects.create(
        record_id='TEST-001',
        first_name='Jane',
        last_name='Doe',
        created_by=staff_user
    )
    ClientProgramEnrolment.objects.create(client=client, program=program)
    return client
```

---

## Development Guidelines

### Code Standards

1. **Always use forms** — Never `request.POST.get()` directly in views
2. **Write tests** — Add tests when building new views
3. **Run migrations** — After model changes: makemigrations, migrate, commit
4. **Encrypted fields** — Use property accessors, not direct field access
5. **Cache invalidation** — Clear cache after saving terminology/features/settings

### Adding a New Feature

1. Create or update models in the appropriate app
2. Create a form in `forms.py`
3. Create views in `views.py`
4. Add URL patterns in `urls.py`
5. Create templates in `templates/<app>/`
6. Add tests in `tests/`
7. Run migrations if models changed

### HTMX Patterns

For partial page updates:

```python
# views.py
def client_search(request):
    query = request.GET.get('q', '')
    clients = search_clients(request.user, query)

    if request.headers.get('HX-Request'):
        return render(request, 'clients/_search_results.html', {'clients': clients})
    return render(request, 'clients/list.html', {'clients': clients})
```

```html
<!-- templates/clients/list.html -->
<input type="search"
       name="q"
       hx-get="{% url 'client_search' %}"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#results">

<div id="results">
    {% include "clients/_search_results.html" %}
</div>
```

### Security Checklist

Before deploying changes:

- [ ] No PII in log messages
- [ ] Forms validate all input
- [ ] Views check user permissions
- [ ] CSRF token on all POST forms
- [ ] No raw SQL (use ORM)
- [ ] Sensitive fields encrypted

---

## Extensions & Customization

KoNote Web is designed as a lightweight, focused outcome tracking system for small-to-medium nonprofit programs (up to ~2,000 clients). This section covers common extension scenarios and guidance for organizations with needs beyond the core feature set.

### Target Use Cases

KoNote is **well-suited for:**
- Youth services (group homes, shelters, drop-ins)
- Mental health counselling programs
- Housing first / supportive housing
- Employment services
- Small-to-medium agencies (10–50 staff, up to 2,000 clients)

KoNote is **not designed for:**
- Large-scale agencies (2,000+ active clients)
- Multi-organization coalitions (without forking)
- Document-heavy services (legal clinics, medical records)
- Scheduling-centric programs (use dedicated scheduling tools)

---

### Field Data Collection (Offline Access)

**The Problem:** Staff working in the field — coaches at sports programs, outreach workers, youth workers at community drop-ins — need to record attendance and quick notes without reliable internet.

**Design Decision:** KoNote does not include a full Progressive Web App (PWA) with offline sync. The complexity of offline-first architecture (service workers, conflict resolution, data merging) is significant and outside the core scope.

**Recommended Approaches:**

#### Option 1: KoBoToolbox + Import API (Recommended for Most)

[KoBoToolbox](https://www.kobotoolbox.org/) is free, open-source, and purpose-built for field data collection in low-connectivity environments.

**Architecture:**
```
┌─────────────────────────┐     ┌─────────────────────────┐
│   ODK Collect (Android) │     │   KoBoToolbox Server    │
│   - Works fully offline │────▶│   - Free hosted option  │
│   - Queues submissions  │     │   - REST API available  │
└─────────────────────────┘     └───────────┬─────────────┘
                                            │
                                            ▼
                                ┌─────────────────────────┐
                                │   KoNote Import Job     │
                                │   - Scheduled or manual │
                                │   - Maps to Quick Notes │
                                └─────────────────────────┘
```

**Integration Points:**
- KoBoToolbox REST API: `GET /api/v2/assets/{uid}/data/`
- KoNote would need: `/api/field-import/` endpoint accepting standardized JSON
- Mapping: KoBoToolbox submission → KoNote Quick Note with metrics

**Implementation Effort:** Medium (2–3 weeks for import endpoint + documentation)

#### Option 2: SharePoint Lists (Microsoft 365 Organizations)

For organizations already using Microsoft 365, SharePoint Lists now supports offline sync.

**Architecture:**
```
┌─────────────────────────┐     ┌─────────────────────────┐
│   Microsoft Lists App   │     │   SharePoint Online     │
│   - Native offline sync │────▶│   - Lists sync enabled  │
│   - iOS and Android     │     │   - Power Automate      │
└─────────────────────────┘     └───────────┬─────────────┘
                                            │ Webhook
                                            ▼
                                ┌─────────────────────────┐
                                │   KoNote Import API     │
                                │   - Webhook receiver    │
                                │   - Maps list → notes   │
                                └─────────────────────────┘
```

**Pros:** Free if org has Microsoft 365; familiar interface; Microsoft handles sync complexity

**Cons:** Requires Microsoft 365; Power Automate configuration needed

#### Option 3: Google AppSheet (Google Workspace Organizations)

[AppSheet](https://about.appsheet.com/) is Google's no-code app builder with native offline support (~$5/user/month).

**Architecture:**
- Create AppSheet form: Select Client → Record Metric → Add Note
- AppSheet works offline, syncs to Google Sheet when online
- KoNote imports from Google Sheet via Apps Script webhook

**Pros:** Low cost; excellent offline; drag-and-drop form builder

**Cons:** Requires Google Workspace; bidirectional sync is manual

#### Option 4: Bounded "Field Mode" (Future Enhancement)

If demand warrants, KoNote could add a minimal field entry mode:

**Scope Boundaries:**
- Cache client list for user's assigned programs only (read-only)
- Simple form: Select Client → Quick metric → Brief note
- Queue submissions in localStorage when offline
- Manual "Sync Now" button when connectivity returns
- No client creation, no plan editing, no historical data access

**Technical Approach:**
```javascript
// Minimal service worker for field mode only
const FIELD_CACHE = 'KoNote-field-v1';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(FIELD_CACHE).then((cache) => {
      return cache.addAll([
        '/field/',
        '/field/form/',
        '/static/css/field.css',
        '/static/js/field.js',
      ]);
    })
  );
});
```

**Implementation Effort:** Medium-High (3–4 weeks)

**Status:** Not currently planned. Organizations needing offline access should use Option 1 (KoBoToolbox) or Option 2 (SharePoint Lists).

---

### Internationalization (Adding Languages)

**Current State:** French is live with 748 translated strings covering the full UI — menus, buttons, form labels, validation messages, and system notifications. Terminology customisation allows changing specific terms (Client → Participant) independently of language selection.

**Why This Matters:**
- Quebec organizations legally required to operate in French
- Franco-Ontarian agencies throughout Ontario
- Ontario's AODA has French language service requirements for many funded programs
- ~25% of Canadian nonprofit market requires French

#### How Internationalisation Works

KoNote uses Django's built-in internationalisation support:

**Settings (konote/settings/base.py)**

```python
USE_I18N = True
USE_L10N = True

LANGUAGES = [
    ('en', 'English'),
    ('fr', 'Français'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

MIDDLEWARE = [
    ...
    'konote.middleware.safe_locale.SafeLocaleMiddleware',  # After SessionMiddleware
    ...
]
```

**Marking Strings for Translation**

```python
# views.py
from django.utils.translation import gettext as _

def client_list(request):
    messages.success(request, _('Client created successfully.'))
```

```html
<!-- templates/clients/list.html -->
{% load i18n %}

<h1>{% trans "Client List" %}</h1>
<button>{% trans "New Client" %}</button>
```

**Extracting and Compiling Translations**

```bash
# Extract all translatable strings (run locally, not in Docker)
python manage.py makemessages -l fr

# This creates: locale/fr/LC_MESSAGES/django.po
# Translate strings in the .po file

# Compile translations (run locally, commit the .mo files)
python manage.py compilemessages
```

**Language Switching**

The header includes a language switcher following the Canada.ca convention:

```html
<!-- templates/base.html -->
<form action="{% url 'set_language' %}" method="post">
    {% csrf_token %}
    <select name="language" onchange="this.form.submit()">
        {% for lang_code, lang_name in LANGUAGES %}
        <option value="{{ lang_code }}" {% if lang_code == LANGUAGE_CODE %}selected{% endif %}>
            {{ lang_name }}
        </option>
        {% endfor %}
    </select>
</form>
```

#### Implementation Details

| Component | Description |
|-----------|-------------|
| **SafeLocaleMiddleware** (`konote/middleware/safe_locale.py`) | Tests French translations on each request; falls back to English if translations fail (corrupted `.mo` files, missing catalogues) |
| **Cookie-based persistence** | `LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60` (1 year), `LANGUAGE_COOKIE_SECURE = True`, `LANGUAGE_COOKIE_HTTPONLY = True` |
| **User.preferred_language** | Field synced on login for multi-device roaming — language follows the user, not the browser |
| **Pre-compiled `.mo` files** | Committed to the repository. No `gettext` system dependency required in production |
| **Pre-commit hook** (`.githooks/pre-commit`) | Blocks commits if `.po` is staged without a matching `.mo` file |

**Translation scope:** 748 strings translated, covering menus, buttons, form labels, validation messages, error pages, email templates, and system notifications.

**Ongoing maintenance:** Translation updates with each feature addition.

**Interaction with Terminology Customization:**

Terminology overrides should remain in the default language but could be extended:

```python
class TerminologyOverride(models.Model):
    term_key = models.CharField(max_length=100)
    language = models.CharField(max_length=10, default='en')  # NEW
    display_value = models.CharField(max_length=255)

    class Meta:
        unique_together = ['term_key', 'language']
```

**Status:** **Implemented.** French translations are live with 748 strings. Pre-compiled `.mo` files are committed to the repository.

---

### Customizing for Coalitions / Networks

**KoNote's Architecture:** Single-organization. Each deployment serves one agency with shared users, programs, and clients.

**Coalition Requirements Typically Include:**
- Multiple member organizations sharing some data
- Organization-level data isolation (Org A can't see Org B's clients)
- Network-level reporting (aggregate across all members)
- Centralized user management or federated identity
- Shared outcome frameworks with local customization

**Why This Requires a Fork:**

True multi-tenancy fundamentally changes the data model:

```python
# Current: No tenant isolation
class ClientFile(models.Model):
    record_id = models.CharField(unique=True)  # Global uniqueness
    programs = models.ManyToManyField(Program)

# Multi-tenant: Organization scoping required everywhere
class ClientFile(models.Model):
    organization = models.ForeignKey(Organization)  # NEW: Required
    record_id = models.CharField()  # Unique per org only
    programs = models.ManyToManyField(Program)

    class Meta:
        unique_together = ['organization', 'record_id']
```

Every query must filter by organization:
```python
# Current
clients = ClientFile.objects.filter(programs__in=user_programs)

# Multi-tenant: Must ALWAYS include org filter
clients = ClientFile.objects.filter(
    organization=request.user.organization,  # CRITICAL
    programs__in=user_programs
)
```

**Fork Guidance for Coalition Implementations:**

1. **Add Organization Model**
   ```python
   class Organization(models.Model):
       name = models.CharField(max_length=255)
       slug = models.SlugField(unique=True)
       settings = models.JSONField(default=dict)
       parent = models.ForeignKey('self', null=True)  # For hierarchies
   ```

2. **Add Organization FK to All Tenant-Scoped Models**
   - User (or separate OrganizationMembership)
   - Program
   - ClientFile
   - PlanTemplate
   - ProgressNoteTemplate
   - CustomFieldDefinition
   - TerminologyOverride
   - FeatureToggle
   - InstanceSetting

3. **Implement Tenant Middleware**
   ```python
   class TenantMiddleware:
       def __call__(self, request):
           # Determine tenant from subdomain, header, or user
           request.organization = get_tenant_from_request(request)
           return self.get_response(request)
   ```

4. **Create Tenant-Aware QuerySet Manager**
   ```python
   class TenantManager(models.Manager):
       def get_queryset(self):
           return super().get_queryset().filter(
               organization=get_current_organization()
           )
   ```

5. **Network-Level Reporting**
   - Create separate reporting database/views
   - Aggregate anonymized metrics across organizations
   - Respect data sharing agreements

**Estimated Effort:** 3–6 months for full multi-tenancy

**Alternative: Separate Instances with Shared Reporting**

For coalitions that don't need shared client records:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Org A KoNote  │  │   Org B KoNote  │  │   Org C KoNote  │
│   (separate)    │  │   (separate)    │  │   (separate)    │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         │    Anonymized metric exports            │
         └────────────────────┼────────────────────┘
                              ▼
                 ┌─────────────────────────┐
                 │   Coalition Dashboard   │
                 │   (separate app)        │
                 │   - Aggregate metrics   │
                 │   - Cross-org reports   │
                 └─────────────────────────┘
```

**Pros:** Much simpler; maintains data isolation; organizations control their own instances

**Cons:** No shared client records; duplicate setup effort; coordination overhead

---

### Funder Reporting Enhancements

**Current State:** CSV export with flat data: Record ID, Metric Name, Value, Date, Author.

**Common Funder Requirements:**

| Funder Type | Requirements |
|-------------|--------------|
| Community Foundation | Demographic breakdowns, outcome achievement rates, funder report format |
| Provincial (MCSS, MCCSS) | Specific templates, fiscal year grouping, service hours |
| Federal grants | Logic model alignment, indicator tracking |
| Foundations | Custom KPIs, narrative + quantitative |

**Enhancement Opportunities:**

#### 1. Aggregation Functions

```python
# apps/reports/aggregations.py

def aggregate_metrics(queryset, group_by=None):
    """
    Aggregate metric values with optional grouping.

    group_by options: 'program', 'month', 'quarter', 'fiscal_year', 'demographic'
    """
    aggregations = queryset.aggregate(
        count=Count('id'),
        avg_value=Avg('numeric_value'),
        min_value=Min('numeric_value'),
        max_value=Max('numeric_value'),
    )

    if group_by:
        return queryset.values(group_by).annotate(**aggregations)
    return aggregations
```

#### 2. Demographic Grouping

Requires adding demographic fields to ClientFile or CustomFieldDefinition:

```python
# Standard demographic categories
DEMOGRAPHIC_FIELDS = [
    'age_range',      # 0-17, 18-24, 25-44, 45-64, 65+
    'gender',         # Female, Male, Non-binary, Prefer not to say
    'geography',      # Postal code prefix or region
    'referral_source',
]

def report_by_demographics(metrics_qs, demographic_field):
    return metrics_qs.values(
        f'progress_note__client__{demographic_field}'
    ).annotate(
        count=Count('id'),
        avg=Avg('numeric_value'),
    )
```

#### 3. Pre-Built Report Templates

```python
# apps/reports/templates_config.py

REPORT_TEMPLATES = {
    'funder_outcome_report': {
        'name': 'Funder Outcome Report',
        'columns': ['outcome_indicator', 'baseline', 'target', 'actual', 'variance'],
        'grouping': 'outcome',
        'demographics': True,
        'format': 'xlsx',
    },
    'quarterly_summary': {
        'name': 'Quarterly Outcome Summary',
        'columns': ['metric', 'q1', 'q2', 'q3', 'q4', 'ytd'],
        'grouping': 'quarter',
        'format': 'pdf',
    },
    'program_comparison': {
        'name': 'Cross-Program Comparison',
        'columns': ['metric', 'program', 'count', 'avg', 'achievement_rate'],
        'grouping': 'program',
        'format': 'xlsx',
    },
}
```

#### 4. Outcome Achievement Rates

```python
def calculate_achievement_rate(metric_def, client_metrics):
    """
    Calculate % of clients who achieved target for this metric.

    Achievement = final value meets or exceeds target threshold.
    """
    if not metric_def.target_value:
        return None

    achieved = 0
    total = 0

    for client_id, values in client_metrics.items():
        if values:
            final_value = values[-1]  # Most recent
            total += 1
            if metric_def.higher_is_better:
                if final_value >= metric_def.target_value:
                    achieved += 1
            else:
                if final_value <= metric_def.target_value:
                    achieved += 1

    return (achieved / total * 100) if total > 0 else None
```

**Implementation Priority:** High — directly supports the core job of demonstrating program impact to funders.

---

### Document Access

**Current State:** No document integration.

**Design Decision:** Folder-level access, not per-document linking.

**Rationale (from expert panel review):**

Per-document linking was evaluated and rejected:
- Workflow requires 10 steps across 3 systems to link one document
- SharePoint's "Copy link" permission dialog confuses non-technical staff
- Predicted adoption: <5% sustained use after 3 months
- Staff will abandon the feature and keep documents in SharePoint/Drive anyway

**Recommended Approach:** Single "Open Documents Folder" button on client records.

See `tasks/document-access-plan.md` for full design rationale.

**Implementation:**

```python
# apps/admin_settings/models.py

class InstanceSetting(models.Model):
    # Document storage configuration
    document_storage_provider = models.CharField(
        max_length=20,
        choices=[
            ('none', 'Not configured'),
            ('sharepoint', 'SharePoint / OneDrive'),
            ('google_drive', 'Google Drive'),
        ],
        default='none'
    )
    document_storage_url_template = models.CharField(
        max_length=500,
        blank=True,
        help_text='URL template with {record_id} placeholder'
    )
```

**URL Templates by Provider:**

| Provider | Template | Button Label |
|----------|----------|--------------|
| SharePoint | `https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/` | Open Documents Folder |
| Google Drive | `https://drive.google.com/drive/search?q={record_id}` | Search Documents |

**SharePoint:** URLs are path-based; folder opens directly.

**Google Drive:** URLs use opaque IDs; search by Record ID instead. Requires folder naming convention: `REC-2024-042 - Smith, Jane`

```html
<!-- templates/clients/_client_header.html -->
{% if settings.document_storage_provider != 'none' %}
<a href="{{ document_folder_url }}"
   target="_blank"
   rel="noopener noreferrer"
   class="button outline">
    {% if settings.document_storage_provider == 'google_drive' %}
        🔍 Search Documents
    {% else %}
        📁 Open Documents Folder
    {% endif %}
</a>
{% endif %}
```

**What We're NOT Building:**
- Per-document link storage
- Document upload/storage
- SharePoint/Google Drive API integration
- Document preview or iframe embedding

**Why:** Documents live in SharePoint/Google Drive. KoNote provides a doorway, not a replacement.

---

### Scheduling & Calendar

**Design Decision:** Basic meeting scheduling and iCal calendar feeds are now built in. Complex scheduling features (recurring events, conflicts, timezone handling, external booking) remain out of scope.

**Built-In Features:**
- One-off client meeting scheduling (linked to Events via `Meeting` model)
- Meeting status tracking (scheduled → confirmed → completed / cancelled / no-show)
- SMS and email meeting reminders (via `communications` app)
- Personal iCal calendar feed with token-based authentication (`CalendarFeedToken`)
- Staff meeting dashboard with filtering and HTMX status updates

**Recommended for Advanced Needs:**

| Need | Recommended Tool | Integration |
|------|------------------|-------------|
| Recurring appointments | Calendly (free tier), Acuity, Microsoft Bookings | Link in notes |
| Group sessions | Google Calendar, Outlook | Link in events |
| Program scheduling | When2Meet, Doodle | External |

---

### API for External Integrations

**Current State:** No REST API. All functionality is through the web interface.

**Future Enhancement:** Read-only API for reporting integrations.

```python
# Potential API structure (not yet implemented)

# Authentication
POST /api/token/          # Obtain JWT token

# Read-only endpoints
GET /api/v1/programs/                    # List programs
GET /api/v1/programs/{id}/clients/       # Clients in program
GET /api/v1/clients/{id}/metrics/        # Metric values for client
GET /api/v1/reports/metrics/             # Aggregated metrics export

# Write endpoints (for field data import)
POST /api/v1/field-entry/                # Submit field observation
POST /api/v1/import/kobotoolbox/         # Import from KoBoToolbox
```

**Authentication Options:**
- API tokens (simple, per-user)
- OAuth 2.0 (if Azure AD integration desired)
- Webhook signatures (for incoming data)

**Status:** Not currently implemented. Priority depends on integration demand.

---

### Extension Checklist

When considering a new feature or extension:

| Question | If Yes | If No |
|----------|--------|-------|
| Does it serve the core job (demonstrate outcomes to funders)? | Consider building | Probably skip |
| Can it be solved with an external tool + link? | Use external tool | Consider building |
| Does it affect >50% of target users? | Higher priority | Lower priority |
| Is complexity bounded and maintainable? | Proceed carefully | Find simpler approach |
| Does it require multi-tenancy changes? | Fork required | May fit core product |

**Guiding Principle:** KoNote should do one thing extremely well — track outcomes and generate funder reports — rather than becoming a bloated "do everything" platform.

---

## Further Reading

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Internationalization](https://docs.djangoproject.com/en/5.1/topics/i18n/)
- [HTMX Documentation](https://htmx.org/docs/)
- [Pico CSS Documentation](https://picocss.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [KoBoToolbox Documentation](https://support.kobotoolbox.org/)
- [Original KoNote Repository](https://github.com/LogicalOutcomes/KoNote)

---

**Version 1.5** — KoNote Web Technical Documentation
Last updated: 2026-02-16
