# Getting Started with KoNote2

This guide walks you through setting up KoNote2 for local development. Choose between:

- **[Option A: Docker Setup](#option-a-docker-setup-recommended)** — Faster, fewer dependencies to install manually
- **[Option B: Manual Setup](#option-b-manual-setup)** — More control, better for debugging

---

## Is This Guide for Me?

**Yes.** This guide is written for nonprofit staff who aren't developers.

If you've ever:
- Installed WordPress or another web application
- Used Excel competently (formulas, sorting, multiple sheets)
- Followed step-by-step software instructions

...you have the skills to set up KoNote2. No command-line experience is required — every step shows you exactly what to type and what to expect.

> **Realistic time estimate:** Plan for **up to 2 hours** for your first Docker setup. The technical steps take 30-45 minutes, but you'll also be learning new concepts along the way. That's normal. Take breaks, re-read steps, and don't rush. Once it's running, you won't need to do this again.

---

## Before You Begin: Understanding Your Responsibility

KoNote2 stores sensitive client information. By setting up and running your own instance, you're taking on responsibility for protecting that data. This section helps you understand what that means.

### What KoNote2 Does Automatically

KoNote2 has security protections built in. When configured correctly, it:

- **Encrypts client names, emails, birth dates, and phone numbers** — Even if someone accessed your database directly, they'd see scrambled text, not readable data
- **Blocks most common security mistakes** — The server won't start if critical security settings are missing
- **Logs who accesses what** — Every time someone views or changes a client record, it's recorded in a separate audit database
- **Restricts access by role** — Staff only see clients in their assigned programs; front desk staff can't view clinical notes
- **Runs security checks automatically** — Every time you start the application, it verifies encryption keys and security settings

### What You Need to Do

Software protections only work if you set things up correctly and maintain them. You are responsible for:

| Your Responsibility | Why It Matters | How KoNote2 Helps |
|---------------------|----------------|------------------|
| **Keep the encryption key safe** | If you lose it, all client data becomes unreadable — permanently | Clear warnings in setup; no default key to fall back on |
| **Use HTTPS in production** | Without it, data travels unprotected over the internet | Built-in support for HTTPS; warnings if cookies aren't secure |
| **Remove departed staff promptly** | Former employees shouldn't access client data | User management in admin panel; audit logs show who accessed what |
| **Back up your data regularly** | Hardware fails; mistakes happen | Backup guide provided; encryption key must be stored separately |
| **Keep software updated** | Security fixes are released over time | Simple update process documented |
| **Train staff on privacy** | Software can't stop someone from writing down a name | Role-based access limits exposure |

### How to Verify Your Setup Is Secure

After completing setup, run these commands to verify security is working:

```bash
# Basic check (should show "no issues")
python manage.py check

# Deployment check (should show no errors, may show warnings in development)
python manage.py check --deploy

# Full security audit (should show all PASS, with possible WARN for development settings)
python manage.py security_audit
```

**What you want to see:**
- `FIELD_ENCRYPTION_KEY` is configured and valid
- No `FAIL` results in the security audit
- `WARN` results are acceptable during local testing, but must be fixed before entering real client data

See [Security Operations Guide](security-operations.md) for detailed explanations of each check.

### When to Get Help

Consider engaging IT support or a technical consultant if:

- Your organisation serves **vulnerable populations** (children, mental health clients, survivors of violence)
- You're subject to **specific regulatory requirements** (healthcare privacy laws, government contracts)
- You need to **integrate with other systems** (SSO, external databases)
- You're **not comfortable** with the responsibility after reading this section

There's no shame in deciding this isn't the right approach for your organisation. Managed software-as-a-service options exist for a reason.

---

## What You'll Need (Pre-Flight Checklist)

Before you begin, make sure you have:

### Skills & Knowledge

- [ ] **Comfort opening a terminal** — You'll type commands and see text output. No coding required, just copy-paste.
- [ ] **Ability to edit text files** — You'll create a `.env` file with settings. Any text editor works (Notepad, VS Code, etc.)
- [ ] **Administrator access on your computer** — Installing software requires admin rights.

### Software to Install First

| Software | What It Does | Where to Get It |
|----------|--------------|-----------------|
| **Git** | Downloads the KoNote2 code from the internet | [git-scm.com/download/win](https://git-scm.com/download/win) |
| **Python 3.12+** | Runs the KoNote2 application | [python.org/downloads](https://www.python.org/downloads/) |
| **Docker Desktop** *(Option A only)* | Runs databases and services automatically | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |

### Time Required

- **Docker Setup (Option A):** Approximately 30-45 minutes for download and setup
- **Manual Setup (Option B):** Approximately 1-2 hours, plus PostgreSQL installation

### Which Option Should I Choose?

| Choose Docker (Option A) if... | Choose Manual (Option B) if... |
|--------------------------------|--------------------------------|
| You're new to software setup | You have IT support available |
| You want the fastest path | You need to debug issues closely |
| You're just trying KoNote2 out | You'll deploy to a server later |

> **Recommendation:** Most nonprofits should start with **Option A: Docker Setup**. It handles the complex parts automatically.

---

## Prerequisites

### All Platforms

- **Git** — to clone the repository
- **Python 3.12 or higher** — KoNote2 requires Python 3.12+

### For Docker Setup (Option A)

- **Docker Desktop** — [Download for Windows](https://docs.docker.com/desktop/install/windows-install/)

### For Manual Setup (Option B)

- **PostgreSQL 16** — KoNote2 requires two separate databases

---

## Option A: Docker Setup (Recommended)

Docker handles PostgreSQL, the web server, and all dependencies automatically.

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/KoNote2-web.git
cd KoNote2-web
```

**Expected output:**
```
Cloning into 'KoNote2-web'...
remote: Enumerating objects: 245, done.
remote: Counting objects: 100% (245/245), done.
remote: Compressing objects: 100% (167/167), done.
Receiving objects: 100% (245/245), 156.00 KiB | 2.60 MiB/s, done.
```

> **What just happened?** You downloaded a copy of all the KoNote2 code to your computer. The `cd` command moved you into that folder.

### Step 2: Create Environment File

Copy the example file:

```bash
copy .env.example .env
```

### Step 3: Generate Security Keys

Open a terminal and run these commands to generate the required keys:

```bash
# Generate SECRET_KEY (Django sessions)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate FIELD_ENCRYPTION_KEY (PII encryption)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Expected output:**
```
# SECRET_KEY will look like this (yours will be different):
8&kx!r#p$m2q^w@3zn5h7jf0+c6v9bldy4gt_a%e1

# FIELD_ENCRYPTION_KEY will look like this (yours will be different):
xK7mP2nQ5rT8vW0yB3dF6hJ9kL4sA1cE7gI0jM2nO=
```

Copy each output and paste it into your `.env` file on the appropriate line.

> **What just happened?**
>
> You created two unique passwords that only your KoNote2 installation knows:
>
> - **SECRET_KEY** — Like a master password for your browser sessions. If someone got this, they could impersonate logged-in users.
> - **FIELD_ENCRYPTION_KEY** — The "lock" for client personal information. Names, emails, and birth dates are scrambled in the database using this key. **If you lose this key, that data is gone forever.**
>
> **Important:** Write down or securely store your `FIELD_ENCRYPTION_KEY` somewhere safe (like a password manager) — separate from where you store database backups.

### Step 4: Set Database Passwords

Edit your `.env` file and replace the placeholder passwords:

```ini
POSTGRES_USER=konote
POSTGRES_PASSWORD=MySecurePassword123    # <-- Replace this!
POSTGRES_DB=konote

AUDIT_POSTGRES_USER=audit_writer
AUDIT_POSTGRES_PASSWORD=AnotherPassword456    # <-- Replace this too!
AUDIT_POSTGRES_DB=konote_audit
```

> **Tip:** Use different passwords for each database. A password manager can generate secure random passwords for you.

### Step 5: Start the Containers

```bash
docker-compose up -d
```

**Expected output:**
```
[+] Running 4/4
 ✔ Container KoNote2-db-1        Started
 ✔ Container KoNote2-audit_db-1  Started
 ✔ Container KoNote2-web-1       Started
 ✔ Container KoNote2-caddy-1     Started
```

This starts:
- **web** — The KoNote2 application on port 8000
- **db** — Main PostgreSQL database
- **audit_db** — Audit log database
- **caddy** — Reverse proxy (for production HTTPS)

Wait for the health checks to pass (about 30 seconds).

### Step 6: Run Migrations

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py migrate --database=audit
```

**Expected output:**
```
Operations to perform:
  Apply all migrations: admin, auth, auth_app, clients, contenttypes, events, notes, plans, programs, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  ... (more lines like this)
  Applying sessions.0001_initial... OK
```

> **What just happened?** "Migrations" create the database tables that KoNote2 needs to store data. The first command sets up the main database (for clients, programs, notes). The second sets up the audit database (which records who changed what, for security).

### Step 7: Create Your First Admin User

Every new instance needs an initial admin account. Since there are no users yet, you create one from the command line:

```bash
docker-compose exec web python manage.py createsuperuser
```

You'll be prompted for:
- **Username** — your login name (e.g., `admin` or your name)
- **Password** — minimum 8 characters (you'll be asked to confirm it)

This creates a user with full admin access. Once logged in, you can create additional users through the web interface using **invite links** (Admin → Users → Invite) or direct user creation.

> **Demo mode shortcut:** If `DEMO_MODE=true` in your `.env`, the `seed` command creates a `demo-admin` user with password `demo1234` — you can use that instead.

### Step 8: Access KoNote2

Open your browser to **http://localhost:8000** and log in with the user you just created.

### Docker Commands Reference

| Command | Purpose |
|---------|---------|
| `docker-compose up -d` | Start all containers |
| `docker-compose down` | Stop all containers |
| `docker-compose logs web` | View application logs |
| `docker-compose exec web bash` | Open shell in web container |
| `docker-compose down -v` | Stop and delete all data (fresh start) |

---

## Option B: Manual Setup

For more control over your development environment, or if you prefer not to use Docker.

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/KoNote2-web.git
cd KoNote2-web
```

**Expected output:**
```
Cloning into 'KoNote2-web'...
remote: Enumerating objects: 245, done.
remote: Counting objects: 100% (245/245), done.
remote: Compressing objects: 100% (167/167), done.
Receiving objects: 100% (245/245), 156.00 KiB | 2.60 MiB/s, done.
```

> **What just happened?** You downloaded a copy of all the KoNote2 code to your computer. The `cd` command moved you into that folder.

### Step 2: Install Python 3.12

**Windows:**
1. Download Python 3.12 from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. **Important:** Check "Add Python to PATH" during installation
4. Verify: `python --version` should show 3.12.x

**macOS (using Homebrew):**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
```

### Step 3: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3.12 -m venv venv
source venv/bin/activate
```

**How to know it worked:** Your command prompt changes to show `(venv)` at the beginning:
```
# Before activation:
C:\Users\YourName\KoNote2-web>

# After activation:
(venv) C:\Users\YourName\KoNote2-web>
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Django, PostgreSQL driver, cryptography library, and other dependencies.

### Step 5: Install PostgreSQL 16

**Windows:**
1. Download PostgreSQL 16 from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run the installer
3. Remember the password you set for the `postgres` user
4. The installer includes pgAdmin (a graphical tool)

**macOS (using Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install postgresql-16
sudo systemctl start postgresql
```

### Step 6: Create Databases

KoNote2 uses two databases: one for application data, one for audit logs.

**Using psql (command line):**

```bash
# Connect as postgres superuser
psql -U postgres

# Create main database and user (replace MySecurePassword123 with your own password)
CREATE DATABASE konote;
CREATE USER konote WITH PASSWORD 'MySecurePassword123';
GRANT ALL PRIVILEGES ON DATABASE konote TO konote;

# Create audit database and user (replace AnotherPassword456 with your own password)
CREATE DATABASE konote_audit;
CREATE USER audit_writer WITH PASSWORD 'AnotherPassword456';
GRANT ALL PRIVILEGES ON DATABASE konote_audit TO audit_writer;

# Exit psql
\q
```

> **Remember:** Write down the passwords you choose. You'll need them in Step 8 when configuring your `.env` file.

**Using pgAdmin (graphical):**
1. Open pgAdmin and connect to your local server
2. Right-click "Databases" → Create → Database
3. Name: `konote`, Owner: `postgres`
4. Repeat for `konote_audit`
5. Create users under Login/Group Roles with appropriate passwords

### Step 7: Create Environment File

Copy the example:

```bash
copy .env.example .env
```

### Step 8: Configure Environment Variables

Edit `.env` with your settings. Replace each `REPLACE_THIS_...` placeholder:

```ini
# Django secret key (generate in Step 9)
SECRET_KEY=REPLACE_THIS_run_command_in_step_9

# PII encryption key (generate in Step 9) - CRITICAL
FIELD_ENCRYPTION_KEY=REPLACE_THIS_run_command_in_step_9

# Database connections (use passwords from Step 6)
DATABASE_URL=postgresql://konote:MySecurePassword123@localhost:5432/konote
AUDIT_DATABASE_URL=postgresql://audit_writer:AnotherPassword456@localhost:5432/konote_audit

# Authentication mode
AUTH_MODE=local

# Allowed hosts for local development
ALLOWED_HOSTS=localhost,127.0.0.1
```

> **Important:** The passwords in `DATABASE_URL` must match the passwords you set when creating the databases in Step 6.

### Step 9: Generate Security Keys

Run these commands and paste the output into your `.env` file:

```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate FIELD_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Expected output:**
```
# SECRET_KEY will look like this (yours will be different):
8&kx!r#p$m2q^w@3zn5h7jf0+c6v9bldy4gt_a%e1

# FIELD_ENCRYPTION_KEY will look like this (yours will be different):
xK7mP2nQ5rT8vW0yB3dF6hJ9kL4sA1cE7gI0jM2nO=
```

> **What just happened?**
>
> You created two unique passwords that only your KoNote2 installation knows:
>
> - **SECRET_KEY** — Like a master password for your browser sessions. Keeps user logins secure.
> - **FIELD_ENCRYPTION_KEY** — The "lock" for client personal information. Names, emails, and birth dates are scrambled in the database using this key.
>
> **Critical:** If you lose `FIELD_ENCRYPTION_KEY`, all encrypted client data becomes unreadable. Store a copy in a password manager or secure location — separate from your database backups.

### Step 10: Run Migrations

```bash
python manage.py migrate
python manage.py migrate --database=audit
```

**Expected output:**
```
Operations to perform:
  Apply all migrations: admin, auth, auth_app, clients, contenttypes, events, notes, plans, programs, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ... (more lines like this)
  Applying sessions.0001_initial... OK
```

> **What just happened?** "Migrations" create the database tables that KoNote2 needs to store data. You'll see messages listing each table being created. The first command sets up the main database (for clients, programs, notes). The second sets up the audit database (which records who changed what, for security).

### Step 11: Create Your First Admin User

Every new instance needs an initial admin account:

```bash
python manage.py createsuperuser
```

You'll be prompted for:
- **Username** — your login name (e.g., `admin` or your name)
- **Password** — minimum 8 characters (you'll be asked to confirm it)

This creates a user with full admin access. Once logged in, you can invite additional staff through the web interface (Admin → Users → Invite).

### Step 12: Start the Development Server

```bash
python manage.py runserver
```

**Expected output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
February 03, 2026 - 14:30:00
Django version 5.0.2, using settings 'konote.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Step 13: Verify Your Setup

1. Open **http://localhost:8000** in your browser
2. You should see the KoNote2 login page
3. Log in with the superuser you created
4. You should see the home page with client search

---

## Environment Variable Reference

### Required Variables

These must be set for KoNote2 to start.

| Variable | Purpose | How to Generate |
|----------|---------|-----------------|
| `SECRET_KEY` | Secures sessions and CSRF | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `FIELD_ENCRYPTION_KEY` | Encrypts client PII | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | Main database connection | `postgresql://user:pass@host:port/dbname` |
| `AUDIT_DATABASE_URL` | Audit log database | `postgresql://user:pass@host:port/dbname` |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AUTH_MODE` | `local` or `azure` for SSO | `local` |
| `DEBUG` | Show detailed errors | `True` in development |
| `ALLOWED_HOSTS` | Domains that can access | `localhost,127.0.0.1` |
| `AZURE_CLIENT_ID` | Azure AD app ID | (required if AUTH_MODE=azure) |
| `AZURE_CLIENT_SECRET` | Azure AD secret | (required if AUTH_MODE=azure) |
| `AZURE_TENANT_ID` | Azure AD tenant | (required if AUTH_MODE=azure) |

---

## Running Security Checks

After setup, verify your configuration passes security checks:

```bash
python manage.py check
```

**Expected output:**
```
System check identified no issues (0 silenced).
```

For a more thorough check (recommended before deployment):

```bash
python manage.py check --deploy
```

See [Security Operations Guide](security-operations.md) for details on all security checks.

---

## Running Tests

To verify everything is working:

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_security.py -v
pytest tests/test_rbac.py -v
```

### What Each Test File Covers

| File | Tests | Purpose |
|------|-------|---------|
| `test_security.py` | PII encryption | Verifies client data is encrypted in database |
| `test_rbac.py` | 19 tests | Role permissions, front desk access control |
| `test_htmx_errors.py` | 21 tests | Error responses, form validation, HTMX partials |
| `test_encryption.py` | Key validation | Fernet encrypt/decrypt functions |

### Running Specific Test Categories

```bash
# Security and access control tests
pytest tests/test_security.py tests/test_rbac.py -v

# HTMX and UI error handling tests
pytest tests/test_htmx_errors.py -v

# All tests with verbose output
pytest -v
```

The test suite creates temporary test data (users, programs, clients) that is automatically cleaned up after each test.

---

## Troubleshooting

### KoNote.E001: FIELD_ENCRYPTION_KEY not configured

**Cause:** Your `.env` file is missing or has an empty `FIELD_ENCRYPTION_KEY`.

**Fix:**
1. Generate a key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Add it to your `.env` file (replace the placeholder):
   ```ini
   FIELD_ENCRYPTION_KEY=xK7mP2nQ5rT8vW0yB3dF6hJ9kL4sA1cE7gI0jM2nO=
   ```
   (Use your actual generated key, not this example!)

### KoNote.E001: FIELD_ENCRYPTION_KEY is invalid

**Cause:** The key in your `.env` file is not a valid Fernet key (wrong format or length).

**Fix:** Generate a fresh key using the command above. Fernet keys are base64-encoded and end with `=`.

### Database connection refused

**Cause:** PostgreSQL is not running or credentials are wrong.

**Fix:**
1. Check PostgreSQL is running:
   - Windows: Check Services for "postgresql-x64-16"
   - macOS: `brew services list`
   - Linux: `sudo systemctl status postgresql`
2. Verify your `DATABASE_URL` credentials match what you set in Step 6
3. Test connection: `psql -U konote -d konote -h localhost`

### ModuleNotFoundError: No module named 'django'

**Cause:** Virtual environment not activated or dependencies not installed.

**Fix:**
1. Activate your virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`

### Port 8000 already in use

**Cause:** Another process is using port 8000.

**Fix:** Either stop the other process, or run on a different port:
```bash
python manage.py runserver 8080
```

### Docker: Container keeps restarting

**Cause:** Usually missing or invalid environment variables.

**Fix:**
1. Check logs: `docker-compose logs web`
2. Look for error messages about SECRET_KEY or FIELD_ENCRYPTION_KEY
3. Ensure your `.env` file has all required variables set

---

## Next Steps

Once your local environment is running:

1. **[Before You Enter Real Data](before-real-data.md)** — Verify backups and security before adding client information
2. **[Agency Setup Guide](agency-setup.md)** — Configure terminology, features, and programs
3. **[Security Operations](security-operations.md)** — Understand security checks and audit logs
4. **[Technical Documentation](technical-documentation.md)** — Architecture deep dive

---

## Glossary

Terms you'll encounter during setup, explained in plain language:

| Term | What It Means |
|------|---------------|
| **Terminal** | A text-based window where you type commands. On Windows, this is "Command Prompt" or "PowerShell". You type a command, press Enter, and see the result as text. |
| **Repository (repo)** | A folder containing all the code for a project, stored online (like GitHub). When you "clone" a repo, you download a copy to your computer. |
| **Clone** | To download a copy of code from the internet (GitHub) to your computer. Think of it like downloading a zip file, but it also keeps track of version history. |
| **Migration** | A script that creates or updates database tables. When you "run migrations," you're telling the database what types of data KoNote2 will store. |
| **Container** | A self-contained package that includes an application and everything it needs to run. Docker containers are like mini virtual computers that run inside your computer. |
| **Environment variables** | Settings stored in a file (`.env`) that tell the application how to behave. Like a configuration file with passwords and preferences. |
| **Virtual environment (venv)** | An isolated space on your computer where Python packages are installed, keeping them separate from other projects. |
| **Dependencies** | Other software packages that KoNote2 needs to work. When you run `pip install`, you're downloading these packages. |
| **PostgreSQL** | The database software that stores all your data. Think of it as a very powerful spreadsheet that KoNote2 uses to save client information. |
| **Encryption key** | A password used to scramble data so only you can read it. Like a key to a lockbox — without it, the contents are unreadable. |
| **Django** | The web framework (toolkit) that KoNote2 is built with. You don't need to know Django, but you'll see its name in commands and logs. |
| **HTMX** | A small tool that makes web pages feel snappier by updating only parts of a page instead of reloading everything. |

---

## Getting Help

- **Documentation issues:** Open an issue in the GitHub repository
- **Security concerns:** See [SECURITY.md](../SECURITY.md) for reporting vulnerabilities
