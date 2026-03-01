# 10 — Data Responsibilities & Handling Acknowledgement

## What This Configures

Nothing in KoNote itself. This document captures the **agency's data handling responsibilities** — things KoNote cannot enforce technically that the agency must manage through policy and practice. The agency signs an acknowledgement confirming they understand these responsibilities before entering real participant data.

## Why This Exists

KoNote encrypts PII, enforces role-based access, and logs every action. But some participant data lives **outside KoNote** — in SharePoint folders, Google Drive, exported reports, plaintext backups, and encryption key storage. KoNote has no control over those systems. The agency must take responsibility for securing data in those places.

This acknowledgement is not a legal contract. It's a shared understanding between the agency and whoever operates their KoNote instance, confirming that the agency knows what they're responsible for and has the practices in place to handle it.

## Dependencies

- **Requires:** Decisions from Documents 02 (Features), 03 (Roles & Permissions), 04 (Programs), 08 (Users)
- **Feeds into:** Document 09 (Verification) — the signed acknowledgement is a go-live prerequisite

## When to Complete

During **Phase 4 (Go-Live Verification)**, after configuration is applied and before the agency begins entering real participant data. The walkthrough in Phase 4 gives context for each responsibility — the acknowledgement formalises what was discussed.

---

## Responsibilities by Area

### 1. Encryption Key Custody

KoNote encrypts all participant names, contact information, and fields marked as sensitive using a single encryption key (`FIELD_ENCRYPTION_KEY`). If this key is lost, **all encrypted data is permanently unrecoverable**. There is no recovery mechanism.

**The agency is responsible for:**

- [ ] Storing the encryption key in a secure location **separate from database backups** (e.g., a password manager like 1Password or Bitwarden, or Azure Key Vault)
- [ ] Ensuring **at least two people** know where the key is stored and how to retrieve it
- [ ] **Never** storing the key in Git, on a shared drive, in email, or in the same location as database backups
- [ ] Setting a calendar reminder to verify key accessibility every 6 months

**What happens if you skip this:** If the key is lost and no backup exists, all encrypted participant data (names, contact details, sensitive custom fields) becomes permanently unreadable. The database structure and non-encrypted data (notes, metrics, plans) remain intact, but you cannot identify which participant they belong to.

| Decision | Options | Default |
|----------|---------|---------|
| Where is the key stored? | Password manager / Azure Key Vault / Other secure location | Must choose one |
| Who has access? | At least two named individuals | Must name them |

---

### 2. Document Storage — SharePoint (if enabled)

If the agency uses the "Open Documents Folder" button to link KoNote participant records to SharePoint folders, the documents themselves live in SharePoint — not in KoNote. KoNote is a **link broker only**: it generates a URL, it never touches, stores, or transmits document contents.

**The agency is responsible for:**

- [ ] **Creating and maintaining SharePoint document libraries** — one per program, with subfolders named by Record ID only (e.g., `REC-2024-001`), never by participant name
- [ ] **Setting SharePoint permissions** to match KoNote program roles — staff in Program A should not have access to Program B's document library
- [ ] **Never putting participant names in folder paths** — names in folder paths appear in URLs, browser history, and SharePoint activity logs. Use the SharePoint metadata column for searchability instead
- [ ] **Configuring retention policies** in SharePoint — 7-year minimum for health information custodians under PHIPA, or as required by the agency's funder agreements
- [ ] **Updating SharePoint group membership** when staff join or leave a program in KoNote — KoNote cannot update SharePoint permissions automatically
- [ ] **Keeping folders in place when participants transfer programs** — the new program creates a new folder; old program folders are historical records. Do not move or copy folders between programs

**What happens if you skip this:** The "Open Documents Folder" button in KoNote will open a broken link or a folder with incorrect permissions. Staff will work around it by emailing documents or storing them in personal drives, which is less secure.

| Decision | Options | Default |
|----------|---------|---------|
| Will you use SharePoint document integration? | Yes / No / Later | No |
| Who maintains SharePoint permissions when staff change? | Named person or role | Must designate |
| Will you use Power Automate for automatic folder creation? | Yes (recommended) / No (manual) | Manual at first, automate within 30 days |
| What is your document retention period? | 7 years (PHIPA minimum) / Other | 7 years |

---

### 3. Document Storage — Google Drive for Participant Portal (if enabled)

If the agency uses the participant portal's "Your Documents" feature, each participant gets a Google Drive folder with program resources (budget templates, job search tools, etc.). The folder is the **participant's property** — the agency creates it and shares it, but the participant owns the contents.

**The agency is responsible for:**

- [ ] **Deciding who creates folders** — a shared service account (e.g., `clientdocs@agency.org`) is recommended over individual worker accounts, especially if staff turnover is high. If a worker's account is deprovisioned before ownership is transferred, the participant loses access
- [ ] **Never uploading clinical documents** to a participant's Google Drive folder — these are working documents (budgets, job tools, resource lists), not health records. Clinical documents belong in SharePoint under the agency's custody
- [ ] **Transferring folder ownership to the participant at discharge** — the worker who created the folder must transfer ownership to the participant and then remove their own access. If this step is skipped, the participant may lose access to their documents
- [ ] **Understanding data residency implications** — Google Drive data may be stored outside Canada. This is acceptable because the contents are participant-owned working documents, not agency health records. But staff must not store clinical content in these folders
- [ ] **Training workers on the discharge handoff** — the folder ownership transfer is a specific set of steps in Google Drive. Workers need to know how to do it

**What happens if you skip this:** Participants will lose access to their documents when workers leave or forget to transfer ownership. This undermines trust in the portal and contradicts the empowerment model the feature is designed to support.

| Decision | Options | Default |
|----------|---------|---------|
| Will you use Google Drive document integration? | Yes / No / Later | No |
| Who creates participant folders? | Shared service account (recommended) / Individual workers | Shared service account |
| What starter resources go in each folder? | 4-7 key resources per program (recommended) | Agency decides |

---

### 4. Export Files & Partner Reports

KoNote can export participant data as CSV files and generate PDF reports for funders. Once exported, these files leave KoNote's control.

**The agency is responsible for:**

- [ ] **Controlling who receives export files** — KoNote notifies designated recipients when an export is generated, but the files themselves can be forwarded. The agency must have a policy on who can receive exports
- [ ] **Securing exported files** — CSVs contain participant data in plain text. Store them on encrypted drives or in access-controlled locations, not on open shared drives or desktops
- [ ] **Deleting exports when no longer needed** — exports created for a specific funder report should be deleted after submission, not accumulated indefinitely
- [ ] **Reviewing export notifications** — KoNote logs every export. The designated privacy officer should review the export log quarterly to confirm exports were appropriate

| Decision | Options | Default |
|----------|---------|---------|
| Who is notified when exports are generated? | Named people (1-3 recommended) | Must designate at least one |
| Who reviews the export log? | Privacy officer / ED / Designated person | Must designate |
| How often is the export log reviewed? | Quarterly (recommended) / Monthly / Annually | Quarterly |

---

### 5. Plaintext Backup (if opted in)

This is an optional safeguard against encryption key loss. The KoNote operator produces a readable (decrypted) copy of all participant data and provides it to the agency for secure storage. **This is the highest-risk data handling activity** — whoever has this file has everything.

**This option is only available after the agency signs this acknowledgement.**

**The agency is responsible for:**

- [ ] **Storing the plaintext backup securely** — on an encrypted USB drive in a locked safe, or in agency-managed encrypted cloud storage. Never on an open shared drive, desktop, or email
- [ ] **Limiting access** — only the designated privacy officer and one backup person should know where the file is stored
- [ ] **Retaining the backup only as long as needed** — replace it when a new backup is produced; destroy old copies securely
- [ ] **Destroying the backup securely when no longer needed** — delete from encrypted storage and empty the recycle bin, or physically destroy the USB drive
- [ ] **Understanding the trade-off** — in KoNote, data access is authenticated, role-based, per-record, and logged. A plaintext backup is all-or-nothing: whoever has the file has every participant's data with no access control and no audit trail

**What happens if you skip this:** If the encryption key is lost and no plaintext backup exists, all encrypted data is permanently unrecoverable. The plaintext backup is insurance — risky to hold, but catastrophic not to have if the key is lost.

| Decision | Options | Default |
|----------|---------|---------|
| Do you want plaintext backups? | Yes (recommended) / No | No (must opt in) |
| Who is the designated custodian? | Named person (privacy officer recommended) | Must designate if opted in |
| How often? | Quarterly (recommended) / After major data entry periods | Quarterly |
| Where will it be stored? | Encrypted USB in locked safe / Encrypted cloud / Other | Must specify if opted in |

---

### 6. Staff Departure & Access Revocation

When a staff member leaves the agency or changes roles, their access to participant data must be revoked across all systems — not just KoNote.

**The agency is responsible for:**

- [ ] **Deactivating the user's KoNote account** on their last day (or asking the KoNote operator to do so)
- [ ] **Removing them from SharePoint groups** for any programs they had access to
- [ ] **Transferring Google Drive folder ownership** for any participant folders they created (if using Google Drive integration)
- [ ] **Reviewing whether any exports or plaintext backups** were stored on the departing staff member's devices or personal accounts
- [ ] **Documenting the offboarding** in the agency's records (KoNote's audit log captures the account deactivation automatically)

| Decision | Options | Default |
|----------|---------|---------|
| Who handles staff departure offboarding? | Named person or role | Must designate |
| Is there an existing IT offboarding checklist? | Yes (add KoNote steps) / No (use this section as a starting point) | — |

---

## Acknowledgement Form

*Complete this form during Phase 4 (Go-Live Verification). Both parties sign before the agency begins entering real participant data.*

---

> ### Data Handling Acknowledgement
>
> **Agency:** ___
>
> **Date:** ___
>
> **KoNote instance URL:** ___
>
> **Operated by:** ___
>
> ---
>
> We confirm that we have read and understood the data responsibilities described in this document. We acknowledge that:
>
> 1. **KoNote encrypts and protects participant data within the application.** Data that leaves KoNote — in SharePoint folders, Google Drive, exported files, or plaintext backups — is the agency's responsibility to secure.
>
> 2. **The encryption key is critical.** If lost, encrypted participant data is permanently unrecoverable. We have stored the key securely and at least two people can retrieve it.
>
> 3. **SharePoint and Google Drive permissions are our responsibility.** KoNote cannot enforce access controls in external systems. We will maintain permissions to match KoNote program roles.
>
> 4. **Exported files contain participant data in plain text.** We will handle exports securely and delete them when no longer needed.
>
> 5. **Staff departures require action in multiple systems.** We will deactivate KoNote accounts, remove SharePoint/Google Drive access, and review for any data stored on personal devices.
>
> **Designated contacts:**
>
> | Role | Name | Title |
> |------|------|-------|
> | Encryption key custodian (primary) | ___ | ___ |
> | Encryption key custodian (backup) | ___ | ___ |
> | Privacy officer / export reviewer | ___ | ___ |
> | SharePoint permission manager | ___ | ___ |
> | Staff departure coordinator | ___ | ___ |
> | Plaintext backup custodian (if opted in) | ___ | ___ |
>
> **Signed:**
>
> ___ (Agency representative — Executive Director or designate)
>
> ___ (KoNote operator representative)
>
> **Date:** ___

---

## Common Configurations

### Small agency (5-15 staff), SharePoint, no portal

- Encryption key: stored in shared 1Password vault, ED + one admin have access
- SharePoint: enabled, one library per program, manual folder creation to start
- Google Drive: not applicable (portal not enabled)
- Exports: ED receives notifications, reviews quarterly
- Plaintext backup: opted in, quarterly, encrypted USB in office safe
- Staff departures: office manager handles

### Medium agency (15-50 staff), SharePoint + portal

- Encryption key: stored in Azure Key Vault, IT lead + ED have access
- SharePoint: enabled, Power Automate for folder creation, IT maintains permissions
- Google Drive: enabled via shared service account, program managers create folders
- Exports: privacy officer receives notifications, reviews monthly
- Plaintext backup: opted in, quarterly, encrypted cloud storage
- Staff departures: HR + IT follow joint checklist

---

## Output Format

The completed acknowledgement form is a signed document (printed or digitally signed). It is:

- Stored with the agency's Configuration Summary from Phase 1
- Referenced in KoNote's audit trail (a note in the admin settings recording the date signed and by whom)
- Reviewed at Phase 5 (30-Day Check-In) to confirm designated contacts are still current

No KoNote configuration changes result from this document — it is purely about organisational practice.
