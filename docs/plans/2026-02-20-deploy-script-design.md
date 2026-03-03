# Deploy Script Design: Automated KoNote Agency Provisioning

**Date:** 2026-02-20
**Status:** Draft
**Author:** Claude (DOC-MA5)
**Reference:** [deploy-ovhcloud.md](../deploy-ovhcloud.md), [deploy-fullhost.ps1](../../deploy-fullhost.ps1)

---

## Goal

Reduce new agency provisioning time from **45–90 minutes (manual)** to **under 30 minutes (scripted)** by automating the repeatable steps in `docs/deploy-ovhcloud.md`.

A single operator runs one command from their local machine. The script SSHes into the target VPS and configures everything needed for a running KoNote instance with HTTPS.

---

## Target Platform

| Property | Value |
|----------|-------|
| Provider | OVHcloud VPS |
| Data centre | Beauharnois, QC (Canadian data residency) |
| OS | Ubuntu 24.04 LTS or newer |
| Prerequisites | Fresh VPS with SSH access, domain name pointed at VPS IP |

---

## Scope Boundary

**In scope:** App-level provisioning on an **existing** VPS — everything from securing the OS through verifying the running instance.

**Out of scope:**
- VPS creation (done via OVHcloud console/API — no programmatic provisioning yet)
- DNS record creation (varies by registrar — must be done manually before running the script)
- SSH key setup on the operator's local machine (one-time per operator)
- Email relay configuration (requires third-party account setup)
- UptimeRobot monitoring (web UI)

---

## Approach

A single Bash script (`scripts/deploy-konote-vps.sh`) that:

1. Accepts configuration via command-line flags (VPS IP, domain, org name, etc.)
2. Generates all credentials locally (never transmitted unencrypted)
3. SSHes into the target VPS using ControlMaster for connection reuse
4. Executes setup steps in order, with error handling at each step
5. Prints a final summary with the URL and credentials

This follows the same pattern as `deploy-fullhost.ps1` (Jelastic automation) but targets OVHcloud VPS via SSH instead of a PaaS API.

---

## Step Mapping

The table below maps each step in `deploy-ovhcloud.md` to its automation status.

| # | Manual Step | Automated? | Script Action |
|---|-------------|------------|---------------|
| 1 | Connect via SSH / set up SSH key | **No** — prerequisite | Operator must have SSH access before running the script |
| 2 | Secure the VPS (ufw, unattended-upgrades) | **Yes** | `apt update && upgrade`, configure `ufw` (SSH + 80 + 443), install `unattended-upgrades` |
| 3 | Install Docker | **Yes** | Run official Docker convenience script (`get.docker.com`), skip if Docker is already installed |
| 4 | Clone KoNote | **Yes** | `git clone` to `/opt/konote`, skip if directory already contains a git repo |
| 5 | Generate credentials | **Yes** | Generate locally using Python `secrets` + `cryptography.fernet` |
| 6 | Create .env file | **Yes** | Write `.env` via SSH heredoc with generated credentials and user-provided domain/org values |
| 7 | Point domain to VPS (DNS) | **No** — varies by registrar | Pre-check: script verifies DNS resolves to VPS IP before proceeding to deploy |
| 8 | Deploy (docker compose up) | **Yes** | `docker compose up -d --build` |
| 9 | Verify deployment | **Yes** | Wait for health check, curl HTTPS endpoint |
| 10 | Create admin user | **Yes** | `docker compose exec web python manage.py createsuperuser --noinput` |
| 11 | Set up backups (cron) | **Yes** | `chmod +x` backup/disk scripts, `mkdir backups`, install crontab entries |
| 12 | Set up monitoring (UptimeRobot) | **No** — web UI | Printed as a post-deploy reminder |
| 13 | Set up email relay | **No** — third-party account | Printed as a post-deploy reminder |
| 14 | Run a second instance | **No** — optional/advanced | Out of scope for v1 |
| 15 | Update process | **Yes** (partial) | Script includes `--update` flag documentation in help text; initial deploy sets up the git remote |

**Summary:** 9 of 15 steps automated. The 6 manual steps are either one-time setup, third-party web UIs, or optional.

---

## Inputs

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--host` | Yes | — | VPS IP address or hostname |
| `--domain` | Yes | — | Domain name (e.g., `konote.agency.ca`) |
| `--admin-email` | Yes | — | Email address for the admin user |
| `--org-name` | Yes | — | Organization name (displayed in KoNote UI) |
| `--admin-user` | No | `admin` | Username for the first admin account |
| `--client-term` | No | `client` | What participants are called (terminology setting) |
| `--ssh-key` | No | SSH agent default | Path to SSH private key |
| `--ssh-user` | No | `ubuntu` | SSH username on the VPS |
| `--branch` | No | `main` | Git branch to deploy |
| `--dry-run` | No | off | Print commands without executing them |

---

## Outputs

After a successful run, the operator receives:

1. **Running instance** at `https://<domain>` with valid HTTPS (Let's Encrypt via Caddy)
2. **Admin credentials** printed to terminal (username + generated password)
3. **Encryption key** printed to terminal with a prominent warning to back it up
4. **Automated backups** running via cron (nightly database dumps at 2 AM, hourly disk checks)
5. **Post-deploy checklist** printed to terminal (DNS verification, UptimeRobot, email relay)

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Credential transmission | All secrets (Django secret key, encryption key, DB passwords) are generated on the **local machine** using Python's `secrets` module and `cryptography.fernet`. They are transmitted to the VPS only via the SSH channel (encrypted in transit). |
| Credential storage | The script does **not** store credentials in any file on the local machine. They exist only in memory during execution and are printed once at the end. Operator must save them to a password manager. |
| .env file permissions | Set to `600` (owner read/write only) immediately after creation on the VPS. |
| Encryption key loss | The final summary includes a `WARNING` block emphasising that loss of `FIELD_ENCRYPTION_KEY` means permanent loss of all encrypted participant data. |
| SSH security | Uses `StrictHostKeyChecking=accept-new` (accepts the host key on first connection, rejects changes on subsequent connections — safer than `StrictHostKeyChecking=no`). |
| Idempotency | Safe to re-run: checks for existing Docker installation, existing repo clone, existing `.env` file. Will not overwrite an existing `.env` (operator must pass `--force-env` to regenerate). |
| Admin password | Generated using `secrets.token_urlsafe(16)` — 128 bits of entropy. Never echoed during intermediate steps, only in the final summary. |

---

## Decisions

### 1. Generate credentials locally vs. on the VPS

**Chosen:** Generate locally, send via SSH.

**Alternatives considered:**
- Generate on VPS: Requires Python + cryptography to be pre-installed on the VPS. Adds a dependency and a chicken-and-egg problem (we install Python packages in step 2, but need credentials in step 6).
- Generate locally: The operator's machine already has Python (required to run the script's credential generation). Credentials travel over SSH (encrypted). Simpler and fewer moving parts.

**Trade-off:** Credentials briefly exist in local process memory. Acceptable because the operator's machine is trusted (they have SSH access to the VPS anyway).

### 2. SSH ControlMaster vs. individual connections

**Chosen:** SSH ControlMaster (single TCP connection reused across all SSH commands).

**Rationale:** The script makes 10+ SSH calls. Without ControlMaster, each call requires a new TCP handshake + key exchange (~1-2 seconds each). ControlMaster creates one persistent connection and multiplexes subsequent calls over it, saving 15-20 seconds total and reducing authentication noise in server logs.

### 3. Docker install method

**Chosen:** Official Docker convenience script (`https://get.docker.com`).

**Alternatives considered:**
- Manual apt repository setup: More steps, more things to break, same end result.
- Snap: Docker snap has known issues with volume mounts and AppArmor on Ubuntu.

**Trade-off:** The convenience script is maintained by Docker Inc. and handles Ubuntu version detection automatically. It's what the manual guide already recommends.

### 4. Admin user creation

**Chosen:** `createsuperuser --noinput` with environment variables (`DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`).

**Rationale:** Django's built-in `--noinput` mode reads credentials from environment variables, avoiding interactive prompts over SSH. The password is generated locally and passed as an environment variable for the single command execution, then discarded.

### 5. No Ansible / no Terraform (yet)

**Chosen:** Plain Bash script.

**Rationale:** The target audience is nonprofit consultants, not DevOps engineers. A single Bash script with clear output is easier to understand, debug, and modify than an Ansible playbook or Terraform configuration. The script is a stepping stone — if multi-tenant provisioning becomes common, wrapping it in Ansible or Terraform is a natural evolution (see Future Enhancements).

### 6. Health check strategy

**Chosen:** Poll `https://<domain>/auth/login/` every 10 seconds for up to 5 minutes after `docker compose up`.

**Rationale:** The web container's health check in `docker-compose.yml` hits `http://localhost:8000/auth/login/` internally. Our external check via HTTPS validates the full stack: Caddy → web → database. The 5-minute timeout accounts for first-time Docker image builds (2-5 minutes) + migrations + Let's Encrypt certificate issuance.

---

## Error Handling

The script uses `set -euo pipefail` and wraps each major step in a function with descriptive error messages:

```
Step 3/9: Installing Docker...
  ✓ Docker 27.5.1 installed

Step 4/9: Cloning KoNote...
  ✗ FAILED: git clone failed (exit code 128)
    Possible cause: repository is private and no GitHub token was provided
    To retry: re-run the script (it will skip completed steps)
```

If a step fails, the script:
1. Prints which step failed and the exit code
2. Suggests a possible cause
3. Exits with a non-zero status
4. Does **not** attempt to roll back completed steps (they are idempotent)

---

## Future Enhancements

| Enhancement | Description | Trigger |
|-------------|-------------|---------|
| OVHcloud API integration | Automate VPS creation via OVHcloud API, eliminating the manual console step | When provisioning volume exceeds 2-3 agencies per month |
| Terraform wrapper | Wrap VPS creation + DNS + script execution in a Terraform module | When infrastructure-as-code is a requirement (e.g., for audits) |
| Multi-tenant support | Deploy multiple agencies on a single VPS (separate Docker Compose stacks sharing Caddy) | After multi-tenancy DRR is resolved |
| Backup verification | Add a post-backup restore test to a throwaway database | After first production backup incident |
| Update command | `--update` flag to pull latest code and redeploy with zero-downtime | After initial deployments stabilise |
| Monitoring integration | Auto-configure UptimeRobot via their API | When UptimeRobot API key management is sorted |

---

## File Location

```
scripts/deploy-konote-vps.sh    # The script itself
docs/plans/2026-02-20-deploy-script-design.md   # This document
```

---

## References

- [docs/deploy-ovhcloud.md](../deploy-ovhcloud.md) — Manual deployment guide (the source of truth for what the script automates)
- [deploy-fullhost.ps1](../../deploy-fullhost.ps1) — Jelastic automation script (analogous approach for a different platform)
- [docker-compose.yml](../../docker-compose.yml) — Container orchestration (web, db, audit_db, caddy, autoheal)
- [entrypoint.sh](../../entrypoint.sh) — Container startup (migrations, seeding, security checks, gunicorn)
- [Caddyfile](../../Caddyfile) — HTTPS reverse proxy configuration
- [scripts/backup-vps.sh](../../scripts/backup-vps.sh) — Nightly database backup script
- [tasks/design-rationale/ovhcloud-deployment.md](../../tasks/design-rationale/ovhcloud-deployment.md) — OVHcloud deployment architecture DRR
