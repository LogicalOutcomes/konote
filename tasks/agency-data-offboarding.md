# Agency Data Offboarding & Secure Export (SEC3)

## Problem

The bulk "Export All Client Data" web feature was removed for privacy reasons — it created a downloadable file containing decrypted PII accessible through the browser. However, legitimate needs remain:

- **Agency offboarding** — an agency leaves KoNote and needs their data
- **Data migration** — moving to a new instance or a different system
- **Privacy access requests** — PIPEDA s. 8 requires producing a copy of personal information on request
- **Key loss insurance** — agencies need a readable backup in case the encryption key is lost

Currently, the only path to access encrypted data is a raw `pg_dump` + the `FIELD_ENCRYPTION_KEY`, which requires database-level access and returns ciphertext that needs a Python script to read.

**Key loss risk:** If an agency loses their `FIELD_ENCRYPTION_KEY`, all encrypted data is permanently unrecoverable. A database backup alone is useless — it's just ciphertext blobs. Agencies need a way to maintain a readable backup as insurance, using their own secure storage process.

## Why Not a Web Endpoint

Downloadable exports of individual PII are the highest-risk data surface:
- Files leave the system and can be forwarded, stored insecurely, or leaked
- A web endpoint can be discovered and exploited
- Browser download history and OS file caches create uncontrolled copies

The application-level export was removed precisely because of this risk. The replacement must not reintroduce it.

## Recommended Approach: Management Command

A Django management command (`manage.py export_agency_data`) that:

1. **Runs only from the server CLI** — not exposed as a web endpoint
2. **Requires explicit confirmation** — interactive prompt to confirm before proceeding
3. **Decrypts and exports** — produces a structured archive of all agency data (encrypted and non-encrypted)
4. **Two output modes** — encrypted (for handover) or plaintext (for agency-managed backup)
5. **Logs to audit database** — records who ran it, when, what was exported, and which format
6. **Supports scoping** — can export a single client (for PIPEDA requests) or all data

### Command Interface (Draft)

```bash
# Full agency export — encrypted (for offboarding handover)
python manage.py export_agency_data \
    --encrypted \
    --output /secure/path/export.zip

# Full agency export — plaintext (for agency-managed backup)
python manage.py export_agency_data \
    --plaintext \
    --output /secure/path/backup.zip

# Single client export (PIPEDA access request)
python manage.py export_agency_data \
    --client-id 42 \
    --plaintext \
    --output /secure/path/client_42.zip

# Dry run (shows row counts, no file written)
python manage.py export_agency_data --dry-run
```

**Mutual exclusivity:** `--encrypted` and `--plaintext` cannot be used together. If neither is provided, the command prompts for which mode to use.

**Confirmation flow:** Before writing any data, the command displays a summary (row counts per model, output path, format) and requires the operator to type `CONFIRM` to proceed. For `--plaintext`, the confirmation also includes a PII warning.

### What Gets Exported

The export must include **all agency data**, not just encrypted fields. An offboarding agency owns everything in their database.

| Model | Fields | Encrypted? |
|---|---|---|
| ClientFile | Names, DOB, phone, record ID | Yes |
| ClientDetailValue | Custom field values | Yes |
| ProgressNote | Notes text, summary, reflection, suggestion | Yes |
| ProgressNoteTarget | Notes, client words | Yes |
| PlanTarget | Name, description, status reason, client goal | Yes |
| PlanTargetRevision | Same as PlanTarget (immutable history) | Yes |
| User | Email | Yes |
| Program | Name, description, settings | No |
| Group | Name, membership | No |
| MetricValue | Scores, dates | No |
| MetricDefinition | Metric names, scales, thresholds | No |
| Alert | Alert records | No |
| Consent | Consent records | No |
| CustomFieldDefinition | Field names, types | No |
| AgencySettings | Terminology, feature toggles | No |

### Export Format

**JSON, not CSV.** Clinical notes contain newlines, commas, quotes, and long narrative text. CSV is fragile for this content — one encoding error and rows misalign. JSON handles arbitrary text safely and preserves data relationships.

The export is a ZIP archive containing:
- One JSON file per model (e.g., `clients.json`, `progress_notes.json`)
- A `README.txt` explaining the file structure and how records relate (foreign keys)
- A `manifest.json` with row counts, export date, and format version

Foreign keys are preserved as IDs. The README explains joins (e.g., "Each progress note has a `client_id` that corresponds to a record in `clients.json`"). For single-client exports, all related records are included automatically.

### Security Controls (built into the tool)

| Control | Detail |
|---|---|
| **No web access** | CLI-only; no URL, no view, no endpoint |
| **Interactive confirmation** | Operator must type `CONFIRM` after reviewing the summary |
| **Encrypted mode** | Output is password-protected ZIP; password communicated separately |
| **Plaintext mode** | PII warning displayed; operator must acknowledge before proceeding |
| **Audit trail** | `AuditLog` entry in audit database before export begins |
| **Scoping** | Can limit to single client for PIPEDA requests |
| **Dry run** | Preview mode shows row counts without writing data |

### Procedural controls (not enforced by the tool)

These should be documented in the agency's data agreement and operational runbook:

- **Two-person rule** — a second admin witnesses the export
- **Written authorization** — formal request on file before running
- **Secure transmission** — files sent via secure channel, not email
- **Retention policy** — plaintext backups securely deleted when superseded

---

## Procedures

### Agency Offboarding

When an agency leaves KoNote and needs a copy of their data:

1. Receive formal written request from agency (email or signed letter)
2. Verify requester identity and authority (agency ED or board designate)
3. Second admin witnesses the export (two-person rule)
4. Log the offboarding event in the audit database
5. Run `export_agency_data --encrypted`
6. Transmit the encrypted file via secure channel (not email)
7. Communicate the decryption password via a separate channel
8. Confirm receipt with the agency
9. Decommission the instance (delete database, revoke credentials, remove deployment)

Note: The audit log entry (step 4) must happen **before** decommission (step 9), since decommission destroys the database. For long-term records, also log the offboarding in an external system (e.g., a ticket, a shared document, or a separate internal database).

### PIPEDA Access Request

When an individual requests a copy of their personal information (PIPEDA s. 8):

1. **The agency** receives and validates the request (identity verification is the agency's responsibility — KoNote provides the tool, not the process)
2. Agency requests the export from whoever operates their KoNote instance
3. Operator runs `export_agency_data --client-id <ID> --plaintext`
4. Agency provides the file to the requester within 30 days (PIPEDA requirement)
5. Export event is logged in audit database

### Agency-Managed Plaintext Backup (Optional)

For agencies who want a readable backup as insurance against encryption key loss:

**Why this exists:** Fernet encryption is all-or-nothing. If the `FIELD_ENCRYPTION_KEY` is lost — server crash, admin turnover, misconfigured migration — every encrypted field becomes permanently unreadable. For small nonprofits without dedicated IT, this is a real and reasonable fear.

**How it works:** The operator periodically runs `export_agency_data --plaintext` and provides the output to the agency, who stores it using their own security process.

**Risk acknowledgement:** A plaintext file has no access control after handover. In the application, data access is authenticated, role-based, per-record, and logged. A plaintext backup is all-or-nothing — whoever has the file has everything. The agency must understand and accept this trade-off in writing.

**Agency responsibility** (must be documented in their data agreement):

- **KoNote provides** the tool to produce a readable backup
- **The agency is responsible** for:
  - Where the file is stored (encrypted drive, locked cabinet, etc.)
  - Who has access to it
  - How long it is retained
  - Destroying it when no longer needed
- **Recommended cadence:** quarterly or after major data entry periods
- **Recommended storage:** encrypted USB in a locked safe, or agency-managed encrypted cloud storage

**Why this is acceptable despite the risk:**

- The export runs **server-side, CLI-only** — not through a browser
- It requires **server access** (SSH, Railway CLI, or equivalent)
- It's **logged and auditable** — you know every time it happens
- The alternative (key loss = total data loss) is worse for the agency and creates legal liability under PIPEDA
- The agency must **sign a data handling acknowledgement** before this option is enabled

**Procedure:**

1. Agency designates a **privacy officer** responsible for the backup
2. Privacy officer requests the export
3. Operator runs `export_agency_data --plaintext`
4. File is provided to the agency for storage in their controlled environment
5. Export event is logged in the audit database

---

## Existing Infrastructure

These pieces already exist and can be reused:

- **`konote/encryption.py`** — `decrypt_field()` handles all decryption
- **`rotate_encryption_key` command** — pattern for iterating all encrypted models
- **`AuditLog`** — audit database logging
- **`backup-restore.md`** — documents `pg_dump` procedures for all platforms

---

## Open Questions

### Must resolve before building

- [ ] **Who runs this command?** Agencies on Railway/Azure/Elestio likely don't have SSH access. If only the KoNote team can run it, the "agency-managed backup" flow needs a request/response process (agency requests → KoNote team runs → delivers file). If self-hosted agencies can run it themselves, the command needs to work for both models. This shapes the entire design.
- [ ] **Encryption format:** GPG requires expertise small nonprofits won't have. Password-protected ZIP is more accessible but weaker. What's the right balance for this audience?
- [ ] **Data agreement template:** The plaintext backup option requires a signed acknowledgement. Do we provide the template, or does each agency draft their own?

### Should resolve before building

- [ ] Should the command support CSV as an alternative to JSON? Some agencies may want spreadsheet-compatible output despite the formatting risks with clinical notes.
- [ ] For PIPEDA requests, should we include audit log entries related to that client?
- [ ] Should plaintext backups be schedulable (cron/Task Scheduler), or always manual? Scheduled = less likely to be forgotten, but also less deliberate.

### Can defer

- [ ] Do we need a "right to erasure" companion command, or is the existing client delete sufficient?
- [ ] Should the export include a data dictionary (field descriptions, enum values, metric scales)?
