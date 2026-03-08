# Contributing to KoNote

Thank you for your interest in contributing to KoNote! Whether you're fixing a bug, adding a feature, or improving documentation, this guide will help you get started.

---

## Before You Start

KoNote is designed for **nonprofit agencies managing sensitive client data**. All contributions must prioritise:

- **Security** -- encryption, access control, and audit logging are non-negotiable
- **Simplicity** -- no JavaScript frameworks, no build tools, no npm
- **Accessibility** -- WCAG 2.2 AA compliance (semantic HTML, colour contrast, keyboard navigation)
- **Privacy** -- PIPEDA and PHIPA compliance considerations for Canadian nonprofits

For significant changes, please [open an issue](https://github.com/LogicalOutcomes/konote/issues) first to discuss the approach.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5, Python 3.12 |
| Database | PostgreSQL 16 (dual: app + audit) |
| Frontend | Django Templates + HTMX + Pico CSS |
| Charts | Chart.js |
| Auth | Azure AD SSO or local (Argon2) |
| Encryption | Fernet (AES) for PII fields |

**No React. No Vue. No webpack. No npm.** Keep it simple.

---

## Branch Model

KoNote uses a three-branch model:

- **`main`** -- production branch (deploy-ready). Never commit directly to `main`.
- **`develop`** -- integration branch. All feature PRs target `develop`.
- **`staging`** -- testing branch for pre-release validation.

### Creating a Branch

Always branch from `develop`:

```bash
git checkout develop
git pull origin develop
git checkout -b feat/short-description   # new feature
git checkout -b fix/short-description    # bug fix
git checkout -b chore/short-description  # cleanup, config, docs
```

### Pull Requests

1. Push your branch and create a PR targeting `develop` (not `main`).
2. Use regular merge commits -- **never squash merge**.
3. Keep PRs focused. One feature or fix per PR.

---

## Development Setup

See [Deploying KoNote](docs/deploying-KoNote.md) for full setup instructions. The quick version:

```bash
git clone https://github.com/LogicalOutcomes/konote.git
cd konote
cp .env.example .env
# Edit .env with your keys (see docs for key generation)
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py migrate --database=audit
docker-compose exec web python manage.py seed
```

---

## Code Conventions

### Python / Django

- **Always use `forms.py`** -- use Django `ModelForm` for validation. Never use raw `request.POST.get()` in views.
- **Always run migrations** -- after any model change, run `makemigrations` and `migrate`, and commit the migration files.
- **Use terminology helpers** -- use `{{ term.client }}` in templates, never hardcode terms like "client" or "participant."
- **Use feature toggles** -- use `{{ features.programs }}` to check feature flags in templates.
- **PII fields use property accessors** -- `client.first_name = "Jane"` (not `_first_name_encrypted`).
- **Audit logs go to the audit database** -- `AuditLog.objects.using("audit")`.

### Frontend

- Django Templates + HTMX for interactivity
- Pico CSS for styling
- Vanilla JavaScript only where needed (no frameworks)
- Chart.js for data visualisation

### Spelling

Canadian English throughout: colour, centre, behaviour, organisation. The word "program" (not "programme") in English; French translations correctly use "programme."

---

## Testing

Run **only the tests related to what you changed**, not the full suite:

| Changed | Run |
|---------|-----|
| `apps/plans/` | `pytest tests/test_plans.py` |
| `apps/clients/` | `pytest tests/test_clients.py` |
| `apps/reports/` | `pytest tests/test_exports.py` |
| Templates only (no Python) | No tests needed unless it has logic |
| Multiple apps | Run each relevant test file |

Full suite (for major changes only): `pytest -m "not browser and not scenario_eval"`

### Writing Tests

When adding new views or features, add corresponding tests covering:

- Permission checks (correct role can access, wrong role is denied)
- Form validation (happy path and invalid input)
- Happy path (the feature works as expected)

---

## Translations

KoNote supports English and French. After creating or modifying any template that uses `{% trans %}` or `{% blocktrans %}` tags:

1. Run `python manage.py translate_strings` -- extracts new strings and compiles
2. Fill in empty French translations in `locale/fr/LC_MESSAGES/django.po`
3. Run `python manage.py translate_strings` again to recompile
4. Commit both `django.po` and `django.mo`

For `{% blocktrans %}` blocks (strings with variables), you must add the `msgid` to the `.po` file manually.

---

## Security Guidelines

- Never commit secrets (`.env`, API keys, encryption keys)
- All PII fields must be encrypted using the existing Fernet pattern
- New views that display progress notes must enforce PHIPA consent filtering -- see `apps/programs/access.py`
- Audit log all data access and administrative actions
- Follow OWASP top 10 -- no SQL injection, XSS, CSRF bypasses, or command injection

---

## Reporting Security Vulnerabilities

Please report security issues privately. See [SECURITY.md](SECURITY.md) for instructions.

---

## Questions?

- **Documentation issues:** [Open an issue](https://github.com/LogicalOutcomes/konote/issues)
- **General questions:** See the [Admin Guide](docs/admin/index.md)
