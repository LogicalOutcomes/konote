# Design Rationale: Encryption Key Rotation

**Status:** Decided
**Date:** 2026-03-07
**Context:** KoNote encrypts all PII fields using Fernet (AES-128-CBC + HMAC-SHA256). Key rotation is needed when keys may be compromised, staff with key access depart, or as part of a regular security policy.

---

## Architecture

### Key Hierarchy

```
FIELD_ENCRYPTION_KEY (master, from env var)
    |
    +-- TenantKey per agency (encrypted by master key)
            |
            +-- PII fields encrypted by tenant key (or master if no tenant key)
```

### Multi-Key Support

`FIELD_ENCRYPTION_KEY` accepts comma-separated keys. The first key encrypts new data; all keys can decrypt existing data. This allows a rolling migration period.

---

## When to Rotate

| Trigger | Urgency | Action |
|---------|---------|--------|
| Key compromise suspected | Immediate | Rotate + re-encrypt all records |
| Staff with key access departs | Within 1 week | Rotate master key |
| Periodic policy (recommended: annually) | Planned | Schedule maintenance window |
| Tenant key compromise | Per-tenant | Rotate only that tenant's key |

---

## Rotation Procedure

### Master Key Rotation

**Pre-requisites:**
- Database backup (`pg_dump`) completed and verified
- Maintenance window communicated to users (brief downtime expected)
- New Fernet key generated

**Steps:**

1. **Generate new key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Dry run** (verifies all records can be decrypted with old key):
   ```bash
   docker compose exec web python manage.py rotate_encryption_key \
       --old-key <OLD_KEY> --new-key <NEW_KEY> --dry-run
   ```

3. **Execute rotation** (re-encrypts all PII fields):
   ```bash
   docker compose exec web python manage.py rotate_encryption_key \
       --old-key <OLD_KEY> --new-key <NEW_KEY>
   ```

4. **Update environment:** Set `FIELD_ENCRYPTION_KEY=<NEW_KEY>` in `.env`

5. **Restart application:**
   ```bash
   docker compose up -d web
   ```

6. **Verify:** The entrypoint startup check decrypts sample records automatically. Additionally:
   ```bash
   docker compose exec web python manage.py shell -c "
   from apps.clients.models import ClientFile
   for c in ClientFile.objects.all()[:5]:
       print(c.first_name, c.last_name)
   "
   ```

### Tenant Key Rotation

Tenant keys are encrypted by the master key. To rotate a tenant key:

1. Generate a new Fernet key
2. Decrypt all PII in that tenant's schema with the old tenant key
3. Re-encrypt with the new tenant key
4. Update the `TenantKey` record (encrypted by master key)
5. Clear the tenant key cache: call `clear_tenant_key_cache()` or restart

**Note:** The `rotate_encryption_key` management command currently operates on the master key only. Tenant key rotation requires manual steps or a future enhancement to the command.

---

## Models and Fields Affected

| Model | Encrypted Fields |
|-------|-----------------|
| `auth_app.User` | `_email_encrypted` |
| `clients.ClientFile` | `_first_name_encrypted`, `_preferred_name_encrypted`, `_middle_name_encrypted`, `_last_name_encrypted`, `_birth_date_encrypted`, `_phone_encrypted`, `_email_encrypted` |
| `clients.ClientDetailValue` | `_value_encrypted` |
| `notes.ProgressNote` | `_notes_text_encrypted`, `_summary_encrypted`, `_participant_reflection_encrypted`, `_participant_suggestion_encrypted` |
| `notes.ProgressNoteTarget` | `_notes_encrypted`, `_client_words_encrypted` |
| `registration.RegistrationSubmission` | `_first_name_encrypted`, `_last_name_encrypted`, `_email_encrypted`, `_phone_encrypted` |
| `portal.ParticipantUser` | `_email_encrypted`, `_totp_secret_encrypted` |
| `circles.Circle` | `_name_encrypted` |
| `circles.CircleMembership` | `_member_name_encrypted` |
| `surveys.SurveyResponse` | `_respondent_name_encrypted` |
| `surveys.SurveyAnswer` | `_value_encrypted` |

---

## Failure Modes and Recovery

| Failure | Symptom | Recovery |
|---------|---------|----------|
| Rotation interrupted mid-way | Some records encrypted with new key, some with old | Set `FIELD_ENCRYPTION_KEY=<NEW_KEY>,<OLD_KEY>` (multi-key mode) and re-run rotation |
| Wrong old key provided | `InvalidToken` errors in dry-run output | Verify current key matches `.env` and retry |
| New key lost after rotation | `DecryptionError` on all PII fields after restart | Restore database from pre-rotation backup |
| Key mismatch after deploy | Startup check fails, container won't start | Fix `FIELD_ENCRYPTION_KEY` in `.env` and restart |

### Critical Safety Rule

**Always back up the database before rotating.** If the new key is lost or the rotation fails partway, the only recovery path is restoring from backup.

---

## Anti-Patterns

- **Never delete the old key before verifying rotation succeeded.** Use multi-key mode during the transition period.
- **Never rotate keys without a database backup.** Key loss = permanent data loss.
- **Never share rotation keys via email or chat.** Use a secrets manager or secure out-of-band channel.
- **Never run rotation on production without a dry run first.** The dry run verifies every encrypted field can be decrypted.

---

## Deferred Enhancements

- **Tenant key rotation command**: Extend `rotate_encryption_key` to support `--tenant <schema_name>` for per-agency rotation
- **Automated rotation schedule**: Add an ops cron job that alerts when the key age exceeds a configurable threshold
- **Key age tracking**: Store key creation date in the environment or database to support age-based alerts
