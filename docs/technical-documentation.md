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
14. [Configuration Reference](#configuration-reference)
15. [Testing](#testing)
16. [Development Guidelines](#development-guidelines)
17. [Extensions & Customization](#extensions--customization)

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
│   ├── clients/               # ClientFile, custom fields
│   ├── plans/                 # PlanSection, PlanTarget, Metrics
│   ├── notes/                 # ProgressNote, MetricValue
│   ├── events/                # Event, EventType, Alert
│   ├── admin_settings/        # Terminology, Features, Settings
│   ├── audit/                 # AuditLog (separate DB)
│   └── reports/               # CSV export, charts, PDFs
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
/clients/                       GET         Client list
/clients/create/                GET, POST   New client
/clients/<id>/                  GET         Client detail
/clients/<id>/edit/             GET, POST   Edit client
/clients/<id>/delete/           POST        Mark inactive
/clients/custom-fields/         GET         Custom field management
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
/admin/settings/                GET         Settings dashboard
/admin/settings/terminology/    GET, POST   Terminology overrides
/admin/settings/features/       GET, POST   Feature toggles
/admin/settings/instance/       GET, POST   Instance settings
/programs/                      GET         Program list
/programs/create/               GET, POST   New program
/programs/<id>/                 GET         Program detail
/audit/log/                     GET         Audit log viewer
```

### Reports

```
/reports/export/                GET, POST   Metric CSV export
/reports/funder-report/         GET, POST   Funder report export
/reports/client-data-export/    GET, POST   Client data CSV export (admin)
/reports/client/<id>/analysis/  GET         Client analysis charts
/reports/client/<id>/pdf/       GET         Client progress PDF
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

## Configuration Reference

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (50+ random characters) |
| `FIELD_ENCRYPTION_KEY` | Fernet key for PII encryption |
| `DATABASE_URL` | Main PostgreSQL connection string |
| `AUDIT_DATABASE_URL` | Audit PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
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

**Design Decision:** Out of scope. KoNote is an outcome tracking system, not a scheduling system.

**Rationale:**
- Calendar features (recurring events, conflicts, reminders, timezone handling) represent a separate product category
- Competitors with calendars (Apricot, ETO, Penelope) have dedicated teams for this feature alone
- Adding scheduling would dilute focus and increase maintenance burden significantly

**Recommended Integrations:**

| Need | Recommended Tool | Integration |
|------|------------------|-------------|
| Client appointments | Calendly (free tier), Acuity, Microsoft Bookings | Link in notes |
| Group sessions | Google Calendar, Outlook | Link in events |
| Program scheduling | When2Meet, Doodle | External |

**Documentation:** Create a "Recommended Tools" page listing scheduling options that complement KoNote.

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

**Version 1.3** — KoNote Web Technical Documentation
Last updated: 2026-02-05
