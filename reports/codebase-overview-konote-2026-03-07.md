# Project Overview: KoNote

## What This Project Does

KoNote is a secure, web-based **Participant Outcome Management** system built for Canadian nonprofits. It helps social service agencies track client outcomes by letting staff define desired outcomes with participants, write progress notes with built-in metrics, and visualise progress over time using charts. Each agency runs its own isolated instance with full control over terminology, features, and configuration.

The project is a ground-up reimplementation of an older open-source tool by the same name, rebuilt with modern Python/Django and designed so that small nonprofits can deploy and customise it without a development team — using AI-assisted workflows.

## Tech Stack

| Technology | What It Does |
|------------|-------------|
| **Django 5 / Python 3.12** | The web framework — handles all server logic, routing, and database access |
| **PostgreSQL 16** | The database — stores all application data. Two separate databases: one for app data, one for audit logs |
| **django-tenants** | Multi-tenancy — each agency gets its own isolated PostgreSQL schema |
| **HTMX** | Makes the UI interactive without heavy JavaScript — sends partial page updates via AJAX |
| **Pico CSS** | A lightweight CSS framework that provides clean, accessible styling |
| **Chart.js** | Renders progress charts showing participant outcome trends |
| **Fernet (AES)** | Encrypts all personally identifiable information (PII) at the field level |
| **Authlib + Argon2** | Authentication — supports Azure AD single sign-on or local passwords hashed with Argon2 |
| **Caddy** | Reverse proxy that handles HTTPS/TLS automatically |
| **Docker Compose** | Packages the entire application for deployment on a VPS |
| **WhiteNoise** | Serves static files (CSS, JS, images) efficiently from Django |
| **WeasyPrint** | Generates PDF exports of reports |

**No React, no Vue, no webpack, no npm.** The frontend is server-rendered Django templates with minimal vanilla JavaScript.

## Project Structure

```
konote/
├── apps/                    # All Django applications (one folder per feature area)
│   ├── admin_settings/      # Agency configuration (terminology, features, branding)
│   ├── audit/               # Audit logging (separate database)
│   ├── auth_app/            # User authentication, roles, MFA
│   ├── circles/             # Family/network entities (Circles)
│   ├── clients/             # Participant records (encrypted PII)
│   ├── communications/      # Internal messaging between staff
│   ├── consortia/           # Multi-agency consortium management
│   ├── events/              # Meetings, appointments, calendar
│   ├── exports/             # Data export functionality
│   ├── field_collection/    # Offline data collection (ODK Central)
│   ├── groups/              # Group sessions and attendance
│   ├── notes/               # Progress notes (the core feature)
│   ├── plans/               # Outcome plans, metrics, targets
│   ├── portal/              # Participant-facing portal
│   ├── programs/            # Program management and access control
│   ├── registration/        # Public registration forms
│   ├── reports/             # Reporting and analytics
│   ├── surveys/             # Survey builder and responses
│   ├── tenants/             # Multi-tenancy models (Agency, TenantKey)
│   └── utils/               # Shared utilities
│
├── konote/                  # Django project configuration
│   ├── settings/            # Split settings (base, production, development, test)
│   ├── middleware/           # Custom middleware (audit, RBAC, terminology, health check)
│   ├── encryption.py        # Fernet encryption for PII fields
│   ├── context_processors.py # Template context (terminology, features, roles)
│   ├── urls.py              # Root URL routing
│   ├── ai.py / ai_views.py  # AI integration (OpenRouter/Claude)
│   └── db_router.py         # Database routing (app DB vs audit DB)
│
├── templates/               # 2,464 HTML templates organised by app
│   ├── base.html            # Master layout
│   ├── includes/            # Reusable partials (modals, cards, etc.)
│   └── {app_name}/          # One folder per Django app
│
├── static/                  # CSS, JavaScript, images
│   ├── js/app.js            # Main JavaScript (HTMX handlers, UI helpers)
│   ├── js/portal.js         # Participant portal JavaScript
│   └── css/                 # Custom styles layered on Pico CSS
│
├── locale/                  # Bilingual translations (English + French)
│   └── fr/LC_MESSAGES/      # French translation files (.po/.mo)
│
├── tests/                   # Test suite (~480K lines)
│   ├── test_*.py            # Unit and integration tests
│   └── ux_walkthrough/      # Browser-based scenario tests
│
├── tasks/                   # Task details, design rationale records
│   └── design-rationale/    # Architectural decision documents
│
├── docs/                    # Technical documentation
├── scripts/                 # Deployment and maintenance scripts
├── qa/                      # QA reports and fix logs
│
├── Dockerfile               # Container build (Python 3.12-slim, non-root)
├── docker-compose.yml       # Full stack: web + 2x PostgreSQL + Caddy + ops
├── Caddyfile                # TLS reverse proxy configuration
├── requirements.txt         # Python dependencies (pinned by major/minor)
├── entrypoint.sh            # Container startup (migrations, translations)
└── manage.py                # Django management entry point
```

## Scale

| Metric | Count |
|--------|-------|
| Python files (excl. migrations) | ~3,500 |
| Python lines of code | ~892,000 |
| HTML templates | ~2,464 |
| Django apps | 18 |
| Database models | ~50+ |
| Git commits | ~3,170+ |

## Key Files to Know

### [konote/urls.py](konote/urls.py)
- **What it does**: Maps every URL to a view. The master routing table.
- **When you'd look here**: Finding where a page lives, adding new routes.

### [konote/settings/base.py](konote/settings/base.py)
- **What it does**: Core Django settings shared across all environments — database, auth, security headers, CSP, session config.
- **When you'd look here**: Changing configuration, understanding security settings.

### [konote/encryption.py](konote/encryption.py)
- **What it does**: Fernet encryption/decryption for PII fields. Supports per-tenant keys and key rotation.
- **When you'd look here**: Understanding how client data is protected.

### [konote/middleware/](konote/middleware/)
- **What it does**: Custom middleware for audit logging, RBAC program access, terminology injection, health checks.
- **When you'd look here**: Understanding request processing pipeline.

### [apps/clients/models.py](apps/clients/models.py)
- **What it does**: The Client (participant) model with encrypted PII fields. Core data entity.
- **When you'd look here**: Understanding how participant data is stored.

### [apps/notes/](apps/notes/)
- **What it does**: Progress notes — the heart of the application. Two-lens design (staff perspective + participant voice).
- **When you'd look here**: The main workflow feature.

### [apps/plans/](apps/plans/)
- **What it does**: Outcome plans, metric definitions, and progress targets. Links metrics to notes for tracking.
- **When you'd look here**: Understanding outcome measurement.

### [apps/auth_app/](apps/auth_app/)
- **What it does**: Custom user model, Azure AD SSO, local auth, role management, MFA.
- **When you'd look here**: Authentication, authorization, user management.

### [templates/base.html](templates/base.html)
- **What it does**: The master HTML template — nav bar, program switcher, messages, footer. Every page extends this.
- **When you'd look here**: Changing the overall page layout.

## How Things Connect

```
                    ┌─────────────────┐
                    │   Caddy (TLS)   │  ← HTTPS termination
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Django Web    │  ← Gunicorn (WSGI)
                    │                 │
                    │  Middleware:     │
                    │  1. Health check │
                    │  2. Security    │
                    │  3. Tenant      │  ← Sets PostgreSQL schema per agency
                    │  4. Session     │
                    │  5. CSRF        │
                    │  6. Auth        │
                    │  7. Portal      │
                    │  8. Locale      │
                    │  9. Audit       │  ← Logs actions to audit DB
                    │  10. RBAC       │  ← Program-level access control
                    │  11. Terminology│  ← Injects agency-specific terms
                    │  12. CSP        │
                    └───┬─────────┬───┘
                        │         │
            ┌───────────▼─┐  ┌───▼───────────┐
            │  App DB     │  │  Audit DB     │
            │ (PostgreSQL)│  │ (PostgreSQL)  │
            │             │  │               │
            │ Per-tenant  │  │ Cross-tenant  │
            │ schemas     │  │ single schema │
            └─────────────┘  └───────────────┘
```

**Data flow for a typical request:**
1. User visits a page → Caddy forwards to Django
2. Tenant middleware identifies the agency from the subdomain, sets the DB schema
3. Auth middleware checks login, RBAC middleware checks program access
4. View loads data (PII decrypted on access via property accessors)
5. Template renders with agency-specific terminology and feature toggles
6. Audit middleware logs the action to the separate audit database

**Key architectural patterns:**
- **Encrypted PII**: Client names, emails, phone numbers are stored as encrypted binary. Property accessors (`client.first_name`) handle encrypt/decrypt transparently.
- **Multi-tenancy**: Each agency gets its own PostgreSQL schema via django-tenants. Data isolation is automatic.
- **RBAC**: Users have roles per program (Staff, Program Manager, Receptionist). Middleware enforces access.
- **Customisable terminology**: Agencies configure their own words for "client", "program", "note", etc. Templates use `{{ term.client }}` instead of hardcoded text.
- **Feature toggles**: Agencies enable/disable features (programs, groups, circles, portal, AI). Templates check `{{ features.programs }}`.
- **PHIPA consent**: Cross-program clinical note visibility requires explicit consent — enforced at the view level.

## Common Tasks

### To add a new feature
1. Create or modify the Django app in `apps/`
2. Define models in `models.py`, forms in `forms.py`, views in `views.py`
3. Create templates in `templates/{app_name}/`
4. Add URL patterns in `urls.py` and wire them in `konote/urls.py`
5. Run migrations: `makemigrations` then `migrate`
6. Add tests in `tests/`
7. Add `{% trans %}` tags for bilingual support, run `translate_strings`

### To fix a bug
1. Find the relevant app (check `konote/urls.py` to trace the URL)
2. Read the view, form, and template
3. Fix and add a test
4. Run the relevant test file: `pytest tests/test_{app}.py`

### To deploy
1. Push to `develop` branch
2. SSH to VPS: `ssh konote-vps`
3. Run: `sudo /opt/konote-dev/scripts/deploy.sh --dev`
4. Container rebuilds, runs migrations, compiles translations automatically

## Where to Start

- **Understanding the data model**: Start with [apps/clients/models.py](apps/clients/models.py) and [apps/plans/models.py](apps/plans/models.py)
- **Understanding the UI**: Look at [templates/base.html](templates/base.html) and any app's template folder
- **Understanding security**: Read [konote/encryption.py](konote/encryption.py) and [konote/settings/base.py](konote/settings/base.py)
- **Understanding the workflow**: Follow a progress note from creation in [apps/notes/views.py](apps/notes/views.py) through to the chart in [apps/plans/views.py](apps/plans/views.py)
- **Design decisions**: Read the files in [tasks/design-rationale/](tasks/design-rationale/)

## Glossary

| Term | Meaning |
|------|---------|
| **Agency** | A nonprofit organisation running their own KoNote instance (tenant) |
| **Participant/Client** | The person receiving services (terminology is configurable) |
| **Program** | A service stream within an agency (e.g., "Youth Counselling") |
| **Plan/PlanTarget** | An outcome goal set for a participant (e.g., "Improve self-regulation") |
| **MetricDefinition** | A measurable indicator (e.g., "Self-regulation score, 1-5") |
| **ProgressNote** | A session record with metrics — the core data entry point |
| **Circle** | A family/network entity connecting related participants |
| **RBAC** | Role-Based Access Control — who can see/do what per program |
| **Fernet** | AES encryption used for PII fields at rest |
| **Tenant** | A PostgreSQL schema isolating one agency's data from another |
| **Portal** | The participant-facing view where clients see their own progress |
| **PHIPA** | Personal Health Information Protection Act (Ontario privacy law) |
| **PIPEDA** | Personal Information Protection and Electronic Documents Act (federal) |
| **DRR** | Design Rationale Record — documents architectural decisions |
