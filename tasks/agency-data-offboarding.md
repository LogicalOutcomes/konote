# Agency Data Offboarding & Secure Export (SEC3)

**Last updated:** 2026-02-27
**Expert panels:** 3 (access model, encryption, brittleness/maintainability)
**Design rationale:** See also `tasks/design-rationale/no-live-api-individual-data.md`

---

## Problem

The bulk "Export All Client Data" web feature was removed for privacy reasons — it created a downloadable file containing decrypted PII accessible through the browser. However, legitimate needs remain:

- **Agency offboarding** — an agency leaves KoNote and needs their data
- **Data migration** — moving to a new instance or a different CMS
- **Privacy access requests** — PIPEDA s. 8 requires producing a copy of personal information on request
- **Program transfers** — a client moves to a program that uses a different system
- **Key loss insurance** — agencies need a readable backup in case the encryption key is lost
- **Client data requests** — giving a client their own data directly

Currently, the only path to access encrypted data is a raw `pg_dump` + the `FIELD_ENCRYPTION_KEY`, which requires database-level access and returns ciphertext that needs a Python script to read.

**Key loss risk:** If an agency loses their `FIELD_ENCRYPTION_KEY`, all encrypted data is permanently unrecoverable. A database backup alone is useless — it's just ciphertext blobs.

## Why Not a Live API or Web Endpoint

**No live API for individual participant data.** This was evaluated and explicitly rejected — see `tasks/design-rationale/no-live-api-individual-data.md` for the full decision record. A live API creates a persistent attack surface, bypasses the consent model, degrades the audit trail, and invites scope creep.

**No bulk PII download via the browser.** The application-level export was removed precisely because downloadable files of individual PII are the highest-risk data surface — files leave the system, can be forwarded, stored insecurely, or leaked. Browser download history and OS file caches create uncontrolled copies.

## Two-Tier Export Model

### Tier 1 — Individual Client Export (via web)

For PIPEDA data access requests, program transfers, or giving a client their own data.

- Staff initiates from the client profile ("Export Client Data" action)
- Delivered via **SecureExportLink** — time-limited HTTPS download (24h expiry, logged, revocable)
- **No file-level encryption** — the secure transport is the protection. One person's data has a limited blast radius compared to an agency-wide export. This is consistent with how healthcare portals deliver patient records (e.g., time-limited HTTPS download links).
- Staff chooses format:
  - **PDF** — human-readable, printable. Covers core stable models: profile, program enrolments, plan goals, progress notes, metric history. Footer states: *"For a complete export including all modules, use the JSON format."*
  - **JSON** — machine-readable, nested client-centric structure. Always complete (automatic model discovery via relationship walking from ClientFile). For importing into another CMS or giving to a service provider.
- JSON includes human-readable labels alongside raw values:
  ```json
  {"progress_descriptor": {"value": 3, "label": "Some progress"}}
  ```
- Audit trail: `AuditLog` entry records who exported, whose data, when, format, and delivery method.

**Note:** The existing PIPEDA guided checklist (already built — `DataAccessRequest` model, 30-day tracking, audit logging) remains the primary workflow for PIPEDA requests. Tier 1 export supplements it when a digital file is needed.

### Tier 2 — Full Agency Export (via management command)

For agency offboarding, CMS migration, or key-loss insurance backup.

- Django management command (`manage.py export_agency_data`) — **CLI only, no web endpoint**
- Requires explicit confirmation (operator types `CONFIRM` after reviewing summary)
- **AES-256-GCM encryption** on the output file (see Encryption section below)
- Exports **everything** — full config + data, everything needed to reconstruct the instance
- Logged to audit database before export begins

## Who Runs It (Tiered Access)

| Hosting model | Who runs the export | How they get the file |
|---|---|---|
| **Self-hosted** (Docker Compose) | Agency's server admin | File on their server |
| **SaaS** (Railway/Azure/Elestio) | KoNote team on request | SecureExportLink (encrypted file via time-limited HTTPS) |

**SLA for SaaS agencies:**
- Routine exports: 5 business days
- PIPEDA requests: 48 hours (gives agency 25+ days of their 30-day window)

**Annual vendor-risk export:** Included in the SaaS service agreement. One full export per year so agencies can demonstrate to their board that they aren't locked in.

## Encryption — AES-256-GCM (Tier 2 Only)

**Password-protected ZIP was explicitly rejected** — ZipCrypto is broken, and even AES-256 ZIP varies by tool support. For data about people experiencing domestic violence, addiction, homelessness, and mental health crises, the encryption must withstand scrutiny from a privacy commissioner's investigation.

### Specification

- **Algorithm:** AES-256-GCM (authenticated encryption)
- **Key derivation:** PBKDF2 with SHA-256, 600,000+ iterations, random salt
- **Implementation:** Python `cryptography` library (already in KoNote's stack — no new dependencies)
- **Passphrase:** 6-word Diceware passphrase, generated by the command, displayed to operator on screen
- **File format:** Salt + IV in header, version byte for future compatibility, then encrypted payload

### Decryptor — Self-Contained HTML/JS

A single HTML file that decrypts the export in the browser. No software installation required.

- Uses **Web Crypto API** (native browser cryptography, hardware-accelerated, available in Chrome/Firefox/Edge/Safari)
- **Fully offline** — no network requests, no CDN dependencies, no analytics
- **Content Security Policy:** `default-src 'self' 'unsafe-inline'; connect-src 'none'` — blocks all outbound connections
- Workflow: agency opens the HTML file in a browser → enters passphrase → selects encrypted file → browser decrypts locally → downloads the decrypted ZIP
- Write-once artifact — does not need per-model updates. The version byte handles format changes.

### Key Exchange

- Diceware passphrase communicated **by phone or in person — never email or text message**
- The management command prints explicit instructions: *"Communicate this passphrase by phone or in person. Do not send it by email or text message."*
- Optional `--authorized-by` flag records who approved the export (logged, not verified — creates a paper trail)
- The passphrase is never logged

### Breach Notification Implication

Under PIPEDA's mandatory breach notification (s. 10.1), if an AES-256-GCM encrypted export is lost or stolen, strong encryption with a proper key means the data is not "accessible" — no breach notification is required. This would not be the case with weak encryption.

## What Gets Exported

### Automatic Model Discovery

The export does **not** use a hardcoded list of models. Instead, it automatically discovers all models in KoNote's apps and exports them by default. A small exclusion list (~10 Django internal models) filters out framework internals (Session, ContentType, LogEntry, Migration, etc.).

**Why this matters:** The previous expert panel rejected automated export because "every model change requires updating the export." Automatic discovery eliminates this problem — new models are included by default. Nobody has to remember to update the export when features are added.

### Three Safety Nets

1. **Django system check (W-level warning):** Runs at app startup. Compares all app models against export coverage. Warns if any model is neither exported nor explicitly excluded. Same pattern as the W010 translation coverage check.

2. **CI test:**
   ```python
   def test_export_covers_all_app_models():
       """Every model in KoNote apps must be exported or explicitly excluded."""
       all_app_models = {m for m in apps.get_models() if m._meta.app_label in KONOTE_APPS}
       exported_models = get_exportable_models()
       excluded_models = set(EXPORT_EXCLUDE)
       uncovered = all_app_models - exported_models - excluded_models
       assert uncovered == set(), f"Models not covered by export: {uncovered}"
   ```
   This test forces a deliberate decision — you can't accidentally forget a model.

3. **Dry-run mode:** `export_agency_data --dry-run` shows row counts per model, encrypted field counts, coverage report, and exclusion list. No data written.

### Export Package Structure

```
export-[agency]-[date]/
  data/
    clients.json              (flat — one record per client)
    progress_notes.json       (flat — one record per note)
    plan_targets.json         (flat — one record per target)
    ...                       (one file per model)
    clients_complete.json     (nested — each client with all related data inline)
  config/
    agency_settings.json      (terminology, feature toggles)
    metric_definitions.json   (metrics, scales, thresholds)
    custom_field_definitions.json
    program_structures.json   (programs, groups, enrolment settings)
    terminology.json
  meta/
    manifest.json             (model list, row counts, schema version, export date, exclusion list)
    README.txt                (how to use the export, relationship explanations)
    schema_version.txt
```

**Flat files** (in `data/`) are for machine import into another database — foreign keys preserved as IDs, joins explained in README.

**Nested client-centric file** (`clients_complete.json`) is for human reading and client-by-client import:
```json
{
  "client": {
    "first_name": "Jane",
    "date_of_birth": "1985-03-15",
    "programs": [
      {
        "name": "Housing First",
        "enrolled": "2025-01-10",
        "plan_targets": [...],
        "progress_notes": [...],
        "metric_values": [...]
      }
    ]
  }
}
```

**Config files** are for setting up a new KoNote instance with the same configuration. Separated from data so a receiving CMS doesn't need to parse KoNote-specific settings.

### Format Decisions

- **JSON, not CSV.** Clinical notes contain newlines, commas, quotes, and long narrative text. CSV is fragile — one encoding error and rows misalign. JSON handles arbitrary text safely.
- **No CSV option.** The risk of data corruption in CSV for clinical notes outweighs the convenience of spreadsheet compatibility.
- **Human-readable labels** included alongside raw values in both flat and nested files.
- **Encoding:** All JSON files are UTF-8 encoded without BOM.

## Command Interface

```bash
# Full agency export — encrypted (for offboarding handover)
python manage.py export_agency_data \
    --output /secure/path/export.enc

# Full agency export — plaintext (for agency-managed backup)
python manage.py export_agency_data \
    --plaintext \
    --output /secure/path/backup.zip

# Single client export — operator convenience for SaaS PIPEDA requests
python manage.py export_agency_data \
    --client-id 42 \
    --plaintext \
    --output /secure/path/client_42.zip

# Dry run (shows row counts, coverage, no file written)
python manage.py export_agency_data --dry-run
```

**Notes:**
- Default mode is encrypted. `--plaintext` must be explicitly specified.
- Plaintext mode shows a PII warning and requires the operator to type `CONFIRM PLAINTEXT`.
- `--client-id` is for SaaS operators handling PIPEDA requests on behalf of agencies that can't access the web UI. Agency staff should use Tier 1 from the client profile when possible.

## Security Controls

### Built into the tool

| Control | Detail |
|---|---|
| **No web access** | CLI-only; no URL, no view, no endpoint |
| **Interactive confirmation** | Operator must type `CONFIRM` (or `CONFIRM PLAINTEXT`) after reviewing summary |
| **AES-256-GCM encryption** | Default mode; PBKDF2-derived key from Diceware passphrase |
| **Guided key exchange** | Command displays passphrase and prints instructions for secure communication |
| **Audit trail** | `AuditLog` entry in audit database before export begins |
| **Dry run** | Preview mode shows row counts and coverage without writing data |
| **Automatic completeness** | Model discovery + CI test ensures nothing is silently missing |

### Procedural controls (not enforced by the tool)

Documented in the agency's data agreement and operational runbook:

- **Two-person rule** — a second admin witnesses the export
- **Written authorisation** — formal request on file before running
- **Secure transmission** — files sent via secure channel, not email
- **Retention policy** — plaintext backups securely deleted when superseded
- **Data handling acknowledgement** — agency signs before plaintext exports are enabled

---

## Procedures

### Agency Offboarding

When an agency leaves KoNote and needs a copy of their data:

1. Receive formal written request from agency (email or signed letter)
2. Verify requester identity and authority (agency ED or board designate)
3. Second admin witnesses the export (two-person rule)
4. Log the offboarding event in the audit database
5. Run `export_agency_data` (default encrypted mode)
6. For SaaS: deliver via SecureExportLink. For self-hosted: file is on their server.
7. Communicate the decryption passphrase by phone or in person
8. Confirm receipt with the agency
9. Decommission the instance (delete database, revoke credentials, remove deployment)

Note: The audit log entry (step 4) must happen **before** decommission (step 9), since decommission destroys the database.

### PIPEDA Access Request

When an individual requests a copy of their personal information (PIPEDA s. 8):

1. **The agency** receives and validates the request (identity verification is the agency's responsibility)
2. Staff uses the **PIPEDA guided checklist** (already built) to track the request and 30-day deadline
3. Staff uses the **Tier 1 individual export** from the client profile to generate a PDF or JSON file
4. File delivered via SecureExportLink (time-limited, logged)
5. Staff marks the PIPEDA request as complete in the checklist

### Program Transfer

When a client moves to a program at another agency that uses a different CMS:

1. Confirm consent for data sharing (PHIPA consent model)
2. Staff uses the **Tier 1 individual export** from the client profile — JSON format for system-to-system transfer
3. Receiving agency downloads via SecureExportLink within 24 hours
4. Export event logged in audit database

### Agency-Managed Backup (Key-Loss Insurance)

**Why this exists:** Fernet encryption is all-or-nothing. If the `FIELD_ENCRYPTION_KEY` is lost — server crash, admin turnover, misconfigured migration — every encrypted field becomes permanently unreadable. For small nonprofits without dedicated IT, this is a real and reasonable fear.

**How it works:** Manual export with automated reminders. The system sends periodic reminders to the agency's designated contact person when a backup is due. A human then initiates the export — the system does not create backups automatically.

**Cadence:** KoNote sends reminders quarterly (configurable). The agency decides whether to act on each reminder.

**For self-hosted agencies:** The agency's admin runs `export_agency_data --plaintext` themselves.

**For SaaS agencies:** The agency requests the export from KoNote. Annual vendor-risk export is included in the service agreement. More frequent backups available on request.

**Agency responsibility** (documented in their data agreement):

- **KoNote provides** the tool and the reminders
- **The agency is responsible** for:
  - Where the file is stored (encrypted drive, locked cabinet, etc.)
  - Who has access to it
  - How long it is retained
  - Destroying it when no longer needed
- **Recommended storage:** encrypted USB in a locked safe, or agency-managed encrypted cloud storage
- **Risk acknowledgement required:** The agency must sign a data handling acknowledgement before plaintext exports are enabled. A plaintext file has no access control after handover — whoever has the file has everything.

---

## Existing Infrastructure

These pieces already exist and can be reused:

- **`konote/encryption.py`** — `decrypt_field()` handles all decryption
- **`rotate_encryption_key` command** — pattern for iterating all encrypted models
- **`AuditLog`** — audit database logging
- **`SecureExportLink`** — time-limited download links (for Tier 1 delivery and SaaS Tier 2 delivery)
- **`backup-restore.md`** — documents `pg_dump` procedures for all platforms
- **Django `_meta` API** — for automatic model discovery and relationship walking

---

## Resolved Questions

All "must resolve" questions have been answered by expert panels (2026-02-27):

| Question | Resolution |
|---|---|
| Who runs this command? | Tiered: self-hosted self-serve, SaaS via KoNote with SLA |
| Encryption format? | AES-256-GCM with PBKDF2 key derivation. HTML/JS browser decryptor. |
| Data agreement template? | KoNote provides the template. Agencies sign before exports enabled. |
| CSV as alternative to JSON? | No. CSV is too fragile for clinical notes. JSON only. |
| Include audit log entries for PIPEDA? | Defer — not required for PIPEDA s. 8 compliance. Can add later. |
| Scheduled or manual backups? | Manual with automated reminders. System nags, human acts. |

### Remaining Questions (can defer)

- [ ] Do we need a "right to erasure" companion command, or is the existing client delete sufficient?
- [ ] Should the export include a data dictionary (field descriptions, enum values, metric scales)?
- [ ] At what scale (number of SaaS agencies) should we build a self-service request portal to replace the manual process?

---

## Maintenance Burden

| Component | Maintenance frequency | Effort |
|---|---|---|
| Export command (automatic discovery) | Only when adding new Django internal models | ~0 |
| CI test (coverage check) | Never — runs automatically | 0 |
| Django system check | Never — runs automatically | 0 |
| HTML decryptor | Only if file format changes | Rare, small |
| Tier 1 PDF | When adding a new core model to PDF layout | Occasional, small |
| Nested JSON structure | Never — relationship walking is automatic | 0 |

**Overall maintenance score: 1/5** (down from 4/5 for the previously rejected PDF-only approach).
