# Local Database Setup

## Default: SQLite (no setup needed)

Tests and local development use **SQLite in-memory databases** by default. You do not need PostgreSQL installed to run the test suite or develop locally.

- `konote/settings/test.py` sets both `DATABASE_URL` and `AUDIT_DATABASE_URL` to `sqlite://:memory:`
- The test settings override `DATABASES` to use `django.db.backends.sqlite3`
- This means `pytest` works out of the box with no database server running

## Where PostgreSQL is used

PostgreSQL 16 is used in **Docker Compose** and **production** deployments only:

- `docker-compose.yml` runs two PostgreSQL 16 Alpine containers (ports 5432 and 5433)
- `konote/settings/production.py` requires `DATABASE_URL` and `AUDIT_DATABASE_URL` environment variables pointing to PostgreSQL
- `konote/settings/development.py` defaults to `postgresql://konote:konote@localhost:5432/konote` and `postgresql://audit_writer:audit_pass@localhost:5433/konote_audit`, but these are only used if you run with `DJANGO_SETTINGS_MODULE=konote.settings.development`

## connect_timeout in base.py

In `konote/settings/base.py` (lines 136-140), a 10-second `connect_timeout` is conditionally applied **only for PostgreSQL engines**:

```python
for _alias, _conf in DATABASES.items():
    if "postgresql" in _conf.get("ENGINE", ""):
        _conf.setdefault("OPTIONS", {})["connect_timeout"] = 10
```

This prevents Django from hanging indefinitely if a PostgreSQL server is unreachable. SQLite connections skip this check entirely because their engine string doesn't contain "postgresql".

## When you might want local PostgreSQL

Two situations where you'd want PostgreSQL running locally:

1. **`security_audit` management command** — Some checks in `python manage.py security_audit` inspect database connection properties that behave differently on SQLite vs PostgreSQL.

2. **Testing against PostgreSQL** — SQLite has minor behavioural differences (e.g., no `DISTINCT ON`, looser type checking). If you need to verify PostgreSQL-specific behaviour, run tests against a real PostgreSQL instance.

## How to set up local PostgreSQL

1. **Install PostgreSQL 16** from https://www.postgresql.org/download/

2. **Create the databases and users** (open pgAdmin → Query Tool, or run `psql -U postgres` in a terminal):

   ```sql
   -- Main application database
   CREATE USER konote WITH PASSWORD 'konote';
   CREATE DATABASE konote OWNER konote;

   -- Audit database (separate instance or separate database)
   CREATE USER audit_writer WITH PASSWORD 'audit_pass';
   CREATE DATABASE konote_audit OWNER audit_writer;
   ```

3. **Set environment variables** before running Django:

   ```bash
   export DATABASE_URL="postgresql://konote:konote@localhost:5432/konote"
   export AUDIT_DATABASE_URL="postgresql://audit_writer:audit_pass@localhost:5433/konote_audit"
   ```

   On Windows (PowerShell):
   ```powershell
   $env:DATABASE_URL = "postgresql://konote:konote@localhost:5432/konote"
   $env:AUDIT_DATABASE_URL = "postgresql://audit_writer:audit_pass@localhost:5433/konote_audit"
   ```

4. **Run migrations:**

   ```bash
   python manage.py migrate
   python manage.py migrate --database=audit
   ```

5. **Run tests against PostgreSQL** (instead of SQLite):

   ```bash
   DJANGO_SETTINGS_MODULE=konote.settings.development pytest -m "not browser and not scenario_eval"
   ```

   On Windows (PowerShell):
   ```powershell
   $env:DJANGO_SETTINGS_MODULE = "konote.settings.development"
   pytest -m "not browser and not scenario_eval"
   ```

## Alternative: use Docker Compose

If you just want PostgreSQL without installing it locally:

```bash
docker compose up db audit_db
```

This starts both database containers. Then set your environment variables to point to `localhost:5432` and `localhost:5433` as shown in `.env.example`.
