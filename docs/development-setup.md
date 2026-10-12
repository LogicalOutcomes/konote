# Local Development Setup

This is the canonical setup guide for contributors. It describes current
application behaviour; shorter instructions link here to avoid drifting out of
sync.

## Choose One Local Workflow

KoNote has two alternative Compose files:

| Workflow | Compose file | What runs in containers | Use it for |
|----------|--------------|-------------------------|------------|
| Development | `docker-compose.dev.yml` | Main PostgreSQL and audit PostgreSQL only | Editing code and running Django from a virtual environment |
| Demo | `docker-compose.demo.yml` | Django, both databases, and synthetic demo data | Evaluating KoNote without a development environment |

Do not start both stacks together. They use overlapping ports and separate
volumes. Demo credentials and keys are public and must never be used for real
participant data.

## Development Workflow

### 1. Prerequisites and source

Install Git, Python 3.12+, and Docker Desktop or Docker Engine with Compose.

```bash
git clone https://github.com/LogicalOutcomes/konote.git
cd konote
git config core.hooksPath .githooks
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows PowerShell
```

Contributors install development dependencies:

```bash
pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes `requirements-test.txt`, which in turn includes
`requirements.txt`. The runtime file is enough for a deployed application;
the development file adds the complete CI test toolchain, including pytest,
pytest-django, pytest-xdist, and Playwright's Python package.

### 2. Configure the environment

```bash
cp .env.example .env            # macOS/Linux
# copy .env.example .env        # Windows
```

Generate unique values for all three required keys:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put the results in `.env` as `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, and
`EMAIL_HASH_KEY`. Never commit `.env`.

For the development database stack, use the `konote` user for both databases:

```ini
DATABASE_URL=postgresql://konote:konote@localhost:5432/konote
AUDIT_DATABASE_URL=postgresql://konote:konote@localhost:5433/konote_audit
AUTH_MODE=local
ALLOWED_HOSTS=localhost,127.0.0.1
```

The Django alias is named `audit`, the PostgreSQL database is
`konote_audit`, and its development database user is `konote`. Those are three
different concepts.

### 3. Start the databases

```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps
```

The main database listens on port 5432. The audit database listens on host
port 5433. Django continues to run on the host.

### 4. Bootstrap the databases and public tenant

Run these commands in this order:

```bash
python manage.py migrate_default
python manage.py migrate
python manage.py setup_public_tenant --domain localhost
python manage.py migrate_audit
python manage.py lockdown_audit_db
python manage.py seed
python manage.py createsuperuser
```

What each command does:

1. `migrate_default` runs Django's standard migration command against the main
   database's `public` schema. The regular command is replaced by
   django-tenants and would omit tenant-app tables in KoNote's single-agency
   public-schema deployment.
2. `migrate` runs django-tenants' migration workflow for any non-public agency
   schemas. On a new single-agency development instance there may be none.
3. `setup_public_tenant` creates or reuses the `Agency` record for the existing
   `public` schema and registers `localhost` in `AgencyDomain`. It is
   idempotent.
4. `migrate_audit` calls Django's original migration implementation for the
   separate audit database. Do not use `migrate --database=audit`;
   django-tenants expects `set_schema()` and the normal PostgreSQL audit
   connection does not provide it.
5. `lockdown_audit_db` revokes update/delete access from the configured audit
   writer after its tables exist. It is idempotent.
6. `seed` creates or updates the metric library, feature toggles, instance
   settings, event types, serious-event categories, note templates, and intake
   fields. With `DEMO_MODE=true`, it also creates synthetic users, programs,
   and participant records. Run it only after main migrations; its operations
   are designed to be safe to repeat.
7. `createsuperuser` creates the first local account after the `users` table
   exists. KoNote's custom manager sets Django `is_superuser`/`is_staff` and
   KoNote `is_admin`.

### 5. Run and sign in

```bash
python manage.py runserver 8000
```

Open <http://localhost:8000/auth/login/>. With `AUTH_MODE=local`, Azure
credentials are optional. `/auth/login/` is the staff sign-in page;
`/admin/settings/` is KoNote's administration interface. Django's built-in
administration site, for rare framework-level work, is mounted separately at
`/django-admin/`.

KoNote uses django-tenants even for a single agency. The `AgencyDomain` record
maps the request hostname to a PostgreSQL schema. `localhost` and `127.0.0.1`
are different hostnames, so each must have a domain record if both will be
used. `setup_public_tenant --domain localhost` guarantees `localhost`; add
another `AgencyDomain` deliberately if direct `127.0.0.1` requests are needed.

## One-Command Demo Workflow

From the repository root:

```bash
docker compose -f docker-compose.demo.yml up --build
```

The container entrypoint runs the canonical migration sequence, public-tenant
bootstrap, audit lockdown, and seed command. Open <http://localhost:8000> and
use a synthetic demo account such as `demo-admin` with password `demo1234`.

Stop the demo with:

```bash
docker compose -f docker-compose.demo.yml down
```

Add `-v` only when you intentionally want to delete all demo database data.

## Database Architecture

The main PostgreSQL database uses
`django_tenants.postgresql_backend`. PostgreSQL schemas provide logical tenant
separation:

```text
konote database
├── public       single-agency deployment and shared tenant metadata
├── agency_a     optional multi-tenant agency schema
└── agency_b     optional multi-tenant agency schema
```

The audit database is a separate normal PostgreSQL database:

```text
audit alias -> konote_audit database -> standard PostgreSQL backend
```

It is intentionally not tenant-aware. Isolation comes from the separate
database connection, Django's `AuditRouter`, and restricted database
permissions. Audit writes use `AuditLog.objects.using("audit")`.

## Tests and Quality Checks

Tests use `konote.settings.test` and isolated SQLite test databases by default;
they do not use the development PostgreSQL databases.

```bash
# Tests matching CI (excluding browser and scenario evaluation)
pytest -m "not browser and not scenario_eval"

# A targeted file
pytest tests/test_plans.py

# Accessibility checks used by CI
pytest tests/test_a11y_ci.py tests/test_blocker_a11y.py

# Django configuration checks
python manage.py check

# Production-oriented configuration check
python manage.py check --deploy

# Container image build
docker compose build web
```

Browser tests require Playwright and Chromium. Scenario-evaluation tests also
require the separate holdout scenario repository. There is currently no
configured formatter, linter, or static type-checker in CI.

## AI During Development

AI is optional. Without `OPENROUTER_API_KEY`, the application runs normally
and tools-only AI cannot make external requests. Participant-data AI remains
disabled unless an administrator separately enables it. See the
[AI Provider Configuration Guide](ai-provider-guide.md) for provider, privacy,
fallback, and data-residency details.

## Troubleshooting

- `relation "users" does not exist`: run `migrate_default` before creating a
  user.
- `relation "metric_definitions" does not exist`: run `migrate_default` before
  `seed`.
- `DatabaseWrapper has no attribute set_schema`: use `migrate_audit`, not
  `migrate --database=audit`.
- `No tenant for hostname`: run `setup_public_tenant` for the exact hostname in
  the browser address.
- `/auth/login/` returns 404 even though the URL resolves: confirm the hostname
  appears in both `ALLOWED_HOSTS` and `AgencyDomain`. Tenant middleware converts
  an invalid or unmapped hostname into a not-found response.
