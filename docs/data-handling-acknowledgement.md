# Data Handling Acknowledgement

**Status:** Template — requires legal review before use with a real agency

**When to use:** Discussed during Phase 1 (Permissions Setup) of the deployment protocol. Signed during Phase 4 (Go-Live Verification), before the agency begins entering real participant data.

**Related:** [tasks/agency-data-offboarding.md](../tasks/agency-data-offboarding.md), [tasks/design-rationale/document-integration.md](../tasks/design-rationale/document-integration.md)

---

## Purpose

KoNote encrypts personal information, enforces role-based access, and logs every action. But some participant data lives **outside KoNote** — in SharePoint folders, Google Drive, exported reports, plaintext backups, and encryption key storage. KoNote has no control over those external systems.

Under the *Personal Information Protection and Electronic Documents Act* (PIPEDA), your organisation is accountable for personal information in its custody or control (Principle 1, s. 4.1). This accountability does not change when data moves between systems — it applies equally to information inside KoNote and information in an external file, folder, or storage system.

This document records your organisation's understanding of where participant data exists outside KoNote and your acceptance of responsibility for safeguarding it in those places.

**Every agency signs this before entering real participant data.** Sections that apply only to optional features (document storage, plaintext backups) are marked — skip those sections if the feature is not enabled.

---

## 1. Encryption Key Custody

KoNote encrypts all participant names, contact information, and fields marked as sensitive using a single encryption key (`FIELD_ENCRYPTION_KEY`). This encryption is all-or-nothing: if the key is lost, **every encrypted field becomes permanently unrecoverable**. No one — not the hosting provider, not the developer, not Anthropic — can reverse this.

**Your organisation is responsible for:**

- Storing the encryption key in a secure location **separate from database backups** (e.g., a password manager like 1Password or Bitwarden, or Azure Key Vault)
- Ensuring **at least two named individuals** know where the key is stored and can retrieve it
- **Never** storing the key in Git, on a shared drive, in email, or in the same location as database backups
- Verifying key accessibility every 6 months

> **Encryption key custodian (primary):** ____________________________
>
> **Encryption key custodian (backup):** ____________________________
>
> **Storage location:** ____________________________

---

## 2. Document Storage — SharePoint *(skip if not using SharePoint integration)*

If your organisation uses the "Open Documents Folder" button to link KoNote participant records to SharePoint folders, the documents themselves live in SharePoint — not in KoNote. KoNote is a **link broker only**: it generates a URL to the folder, but never touches, stores, or transmits document contents.

Under PIPEDA Principle 7 (s. 4.7), your organisation must protect this information with safeguards appropriate to its sensitivity. Under PHIPA s. 17(1), health information collected for one purpose must not be used for another without consent — which is why KoNote uses program-centric document libraries rather than a single shared folder.

**Your organisation is responsible for:**

- **Creating and maintaining SharePoint document libraries** — one per program, with subfolders named by Record ID only (e.g., `REC-2024-001`), never by participant name
- **Setting SharePoint permissions** to match KoNote program roles — staff in Program A should not have access to Program B's document library
- **Never putting participant names in folder paths** — names in folder paths appear in URLs, browser history, and SharePoint activity logs. Use the SharePoint metadata column for searchability instead
- **Configuring retention policies** in SharePoint — 7-year minimum for health information custodians under PHIPA, or as required by your funder agreements
- **Updating SharePoint group membership** when staff join or leave a program in KoNote — KoNote cannot update SharePoint permissions automatically
- **Keeping folders in place when participants transfer programs** — the new program creates a new folder; old program folders are historical records

> **SharePoint permission manager:** ____________________________

---

## 3. Document Storage — Google Drive for Participant Portal *(skip if not using portal documents)*

If your organisation uses the participant portal's "Your Documents" feature, each participant gets a Google Drive folder with program resources. The folder is the **participant's property** — your organisation creates it and shares it, but the participant owns the contents at discharge.

**Data residency note:** Google Drive data may be stored outside Canada. This is acceptable because the contents are participant-owned working documents (budgets, job tools, resource lists), not agency health records. Staff must not store clinical content in these folders.

**Your organisation is responsible for:**

- **Using a shared service account** (e.g., `clientdocs@agency.org`) rather than individual worker accounts to create folders — this prevents folder loss when a worker's account is deprovisioned
- **Never uploading clinical documents** to a participant's Google Drive folder — clinical documents belong in SharePoint under the agency's custody
- **Transferring folder ownership to the participant at discharge** — the worker (or service account) must transfer ownership to the participant and then remove their own access
- **Training workers on the discharge handoff** — the ownership transfer is a specific set of steps in Google Drive that workers need to know

**What happens if ownership is not transferred:** The participant may lose access to their documents when the worker leaves or the service account changes. This undermines trust in the portal and contradicts the empowerment model the feature is designed to support.

---

## 4. Export Files & Partner Reports

KoNote can export participant data as CSV files and generate PDF reports for funders. Once exported, these files leave KoNote's control.

Under PIPEDA Principle 7 (s. 4.7), exported data requires the same safeguards as data inside the application. Under Principle 5 (s. 4.5), it must be retained only as long as necessary.

**Your organisation is responsible for:**

- **Controlling who receives export files** — KoNote notifies designated recipients when an export is generated, but the files can be forwarded
- **Securing exported files** — CSVs contain participant data in plain text. Store them on encrypted drives or in access-controlled locations, not on open shared drives or desktops
- **Deleting exports when no longer needed** — exports created for a specific funder report should be deleted after submission
- **Reviewing the export log quarterly** — KoNote logs every export. The designated reviewer should confirm exports were appropriate

> **Export notification recipient(s):** ____________________________
>
> **Export log reviewer:** ____________________________

---

## 5. Plaintext Backup *(skip if not opting in)*

### What Plaintext Export Means

Inside KoNote, personal information is protected by encryption, role-based access control, consent enforcement, audit logging, and authentication. These protections are built into the software and operate automatically.

A plaintext export produces a file containing **all personal information in your KoNote instance, decrypted and readable** — including names, dates of birth, contact information, clinical notes, progress records, and metric scores.

Once that file exists outside the software:

- **No encryption** — the file is readable by anyone who possesses it
- **No access control** — there are no roles, program boundaries, or consent filters
- **No audit trail** — no system tracks who opens, copies, or forwards the file
- **No authentication** — no login is required

The file is equivalent to a printed copy of every participant record in your organisation. Whoever has it has everything.

### Why You Might Choose This

A plaintext backup stored securely by your organisation protects against encryption key loss. The trade-off is clear: you accept the risk of possessing a readable copy of all participant data in exchange for insurance against catastrophic key loss.

### Your Obligations Under PIPEDA

By producing and retaining a plaintext export, your organisation takes on specific obligations under federal privacy law. Provincial legislation (e.g., Ontario's *Personal Health Information Protection Act* if your organisation is a health information custodian) may impose additional requirements.

### Accountability (Principle 1, s. 4.1)

You must designate an individual accountable for your organisation's compliance with privacy principles, including the handling of exported data.

> **Designated accountability contact for data exports:**
>
> **Name:** ____________________________
>
> **Title:** ____________________________
>
> **Email:** ____________________________

This person is responsible for:
- Deciding when to produce exports
- Ensuring exported files are stored and handled according to this acknowledgement
- Responding to any breach involving exported data
- Transferring this responsibility if they leave the organisation

### Safeguards (Principle 7, s. 4.7)

Personal information must be protected by security safeguards appropriate to its sensitivity (s. 4.7.1). Participant data in a community services context — which may include mental health, addiction, housing, domestic violence, and financial information — is highly sensitive.

**Required safeguards for plaintext exports:**

- **Storage:** Encrypted USB drive in a locked safe, or agency-managed encrypted cloud storage (e.g., encrypted SharePoint, Tresorit). Physical access must be restricted to the designated contact and one backup person.
- **No unprotected copies:** Do not store on shared network drives without encryption, in personal cloud storage without encryption, on unencrypted USB drives, or in email.
- **Access limitation:** Only the designated contact and one backup person should have access to the storage location and any passwords or encryption keys protecting it.

### Retention and Disposal (Principle 5, s. 4.5)

Personal information shall be retained only as long as necessary, and shall be destroyed, erased, or made anonymous when no longer needed (s. 4.5.2–4.5.3).

- **Keep only the most recent backup.** Securely delete the previous file each time a new export is produced.
- **Secure deletion** means overwriting or physically destroying the media — not moving the file to the recycle bin.
- **If your organisation stops using KoNote,** securely delete all plaintext exports within 90 days of receiving your final encrypted offboarding export, unless a specific legal obligation requires longer retention.

### Breach of Security Safeguards (s. 10.1)

If a plaintext export is lost, stolen, or accessed by an unauthorised person, and there is a real risk of significant harm to any individual:

1. **Report to the Privacy Commissioner of Canada** (mandatory under s. 10.1(1))
2. **Notify affected individuals** (mandatory under s. 10.1(3))
3. **Keep a record of the breach** (mandatory under s. 10.3, retained for a minimum of 24 months)
4. **Notify your hosting provider** (if applicable) so they can assist

Given the sensitivity of participant data in community services, a lost or stolen plaintext export will almost always meet the "real risk of significant harm" threshold. Plan accordingly.

**Note:** An encrypted export (AES-256-GCM) that is lost or stolen does *not* require breach notification if the passphrase was not compromised — the data is not accessible. This is one reason encrypted export is the default.

---

## 6. Staff Departure & Access Revocation

When a staff member leaves the organisation or changes roles, their access to participant data must be revoked across **all systems** — not just KoNote.

**Your organisation is responsible for:**

- **Deactivating the user's KoNote account** on their last day (or asking the KoNote operator to do so)
- **Removing them from SharePoint groups** for any programs they had access to (if using SharePoint integration)
- **Transferring Google Drive folder ownership** for any participant folders they created (if using Google Drive integration)
- **Reviewing whether any exports or plaintext backups** were stored on the departing staff member's devices or personal accounts

KoNote's audit log captures account deactivation automatically. SharePoint and Google Drive changes are outside KoNote's control.

> **Staff departure coordinator:** ____________________________

---

## What This Acknowledgement Does NOT Cover

- **Encrypted exports** — AES-256-GCM encrypted files for offboarding or migration. Protected by encryption; no plaintext handling obligations arise.
- **Individual client exports** — single-client data from the client profile for PIPEDA access requests or program transfers. Delivered via time-limited secure download link. Different risk profile (one person's data, not an entire agency).
- **Aggregate reports** — de-identified funder and partner reports. No personal information.
- **Database backups** — encrypted at rest by the hosting infrastructure. Not readable without the encryption key.
- **The service relationship between your organisation and your hosting provider** — if a third party (such as LogicalOutcomes) hosts and operates KoNote on your behalf, the terms of that relationship (data processing, security commitments, SLAs, breach notification chain) should be documented in a separate service agreement under PIPEDA Principle 1, s. 4.1.3.

---

## Acknowledgement

By signing below, the undersigned confirms on behalf of the organisation that:

**All agencies:**

1. We understand that KoNote encrypts and protects participant data within the application, and that data outside KoNote — in SharePoint folders, Google Drive, exported files, or plaintext backups — is our responsibility to secure
2. We have stored the encryption key securely and at least two named individuals can retrieve it
3. We accept accountability for safeguarding exported files in accordance with PIPEDA and applicable provincial legislation
4. We will handle staff departures by revoking access across all connected systems (KoNote, SharePoint, Google Drive)
5. We understand our mandatory breach notification obligations under PIPEDA s. 10.1 if personal information is compromised in any system
6. We understand that KoNote is open-source software provided without warranty, and that responsibility for personal information outside the application rests entirely with our organisation

**If using SharePoint document integration:**

7. We will maintain SharePoint permissions to match KoNote program roles, and update them when staff change
8. We will use Record ID only (not participant names) in SharePoint folder paths
9. We will configure retention policies appropriate to our obligations

**If using Google Drive for participant portal:**

10. We will transfer Google Drive folder ownership to participants at discharge
11. We will not store clinical documents in participant Google Drive folders
12. We understand that Google Drive data may be stored outside Canada and will limit contents to participant-owned working documents

**If opting in to plaintext backups:**

13. We will store plaintext exports using safeguards appropriate to the sensitivity of the information (encrypted storage, restricted access)
14. We will retain only the most recent backup and securely destroy superseded copies

> **Organisation:** ____________________________
>
> **KoNote instance URL:** ____________________________
>
> **Signed by:** ____________________________
>
> **Title:** ____________________________
>
> **Date:** ____________________________
>
> **Features enabled:** *(check all that apply)*
>
> - [ ] SharePoint document integration
> - [ ] Google Drive participant portal documents
> - [ ] Plaintext backups

---

## Note on Managed Hosting

If your organisation uses a managed hosting arrangement (a third party operates KoNote on your behalf), PIPEDA Principle 1 (s. 4.1.3) requires that you use contractual or other means to provide a comparable level of protection while your data is being processed by that third party. This acknowledgement does not serve that purpose — you should have a separate data processing or service agreement with your hosting provider that covers security measures, data residency, access controls, breach notification responsibilities, and termination procedures.

---

*This template requires legal review before use with a real agency. It is written in plain language for nonprofit executive directors and board members. A lawyer should review it for compliance with PIPEDA, applicable provincial privacy legislation (including PHIPA if your organisation is a health information custodian), and your organisation's specific governance requirements.*
