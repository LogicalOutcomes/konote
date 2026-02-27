# Data Handling Acknowledgement — Plaintext Export

**Status:** Template — requires legal review before use with a real agency

**When to use:** Before enabling plaintext data exports for an agency. Discussed during Phase 1 (Permissions Setup) of the deployment protocol. Signed during Phase 4 (Go-Live Verification).

**Related:** [tasks/agency-data-offboarding.md](../tasks/agency-data-offboarding.md) — full design for the export system

---

## About This Document

This acknowledgement is between KoNote (the service provider) and your organisation (the agency). It covers how your data is protected inside KoNote, what changes when data is exported as a plaintext file, and what your organisation is responsible for after receiving an export.

**You do not need to sign this to use KoNote.** This acknowledgement is only required if your organisation wants to receive plaintext (unencrypted) data exports — for example, as a backup against encryption key loss. Encrypted exports (for offboarding or migration) and individual client exports (for PIPEDA requests or program transfers) are covered by the standard service agreement.

---

## How KoNote Protects Your Data

Inside KoNote, participant data is protected by multiple layers:

- **Encryption at rest** — names, dates of birth, contact information, clinical notes, and other personal information are encrypted in the database using Fernet (AES-128-CBC) encryption. Even someone with direct database access cannot read these fields without the encryption key.
- **Role-based access control** — staff see only the data relevant to their role and program assignments. Front desk staff, coaches, program managers, and executives all have different access levels.
- **Consent enforcement** — cross-program data sharing follows your agency's PHIPA consent settings. Clinical notes from one program are not visible to staff in another program unless consent is in place.
- **Audit logging** — every access to participant data is logged: who viewed what, when, and from where. These logs are stored in a separate database that cannot be modified.
- **Authentication** — access requires login through Azure AD (single sign-on) or a local account with strong password requirements.

**These protections only work while data stays inside KoNote.**

---

## What Changes When Data Is Exported

A plaintext export produces a file (or set of files) containing **all participant data in your KoNote instance, decrypted and readable.** This includes names, dates of birth, contact information, clinical notes, progress records, metric scores, and all other information your staff have entered.

Once the export file leaves KoNote:

- **Encryption is gone** — the file is readable by anyone who has it
- **Access control is gone** — there are no roles, no program boundaries, no consent filters
- **Audit logging is gone** — KoNote cannot track who opens, copies, or forwards the file
- **Authentication is gone** — there is no login required to read the file

**The file contains everything.** A plaintext export has no access control after handover — whoever has the file has all your participant data.

---

## Why You Might Want a Plaintext Export

Despite the risks above, there is one scenario where a plaintext backup is the responsible choice:

**Key loss insurance.** KoNote uses encryption that is all-or-nothing. If your organisation loses the encryption key — due to a server failure, administrative turnover, or misconfigured migration — every encrypted field in your database becomes permanently unrecoverable. No one, including KoNote, can recover this data.

A plaintext backup stored securely by your organisation ensures that even in a worst-case key loss scenario, your participant data is not permanently lost.

**KoNote provides the export tool and periodic reminders.** Your organisation decides whether and when to act on each reminder.

---

## Your Organisation's Responsibilities

By signing this acknowledgement, your organisation agrees to the following:

### 1. Designated Contact Person

You will designate one person as the **data export contact**. This person:
- Receives backup reminders from KoNote
- Initiates export requests (for SaaS agencies) or runs the export command (for self-hosted agencies)
- Is responsible for the secure handling of exported files
- Notifies KoNote if they leave the organisation, so the designation can be updated

> **Your designated contact:** ____________________________
>
> **Title:** ____________________________
>
> **Email:** ____________________________

### 2. Secure Storage

Exported files must be stored securely. Your organisation is responsible for:

- **Where the file is stored** — we recommend an encrypted USB drive in a locked safe, or agency-managed encrypted cloud storage (e.g., an encrypted SharePoint folder or Tresorit vault)
- **Who has access to it** — limit access to the designated contact and one backup person
- **Physical security** — if stored on removable media, keep it in a locked location with restricted access

**Do not store plaintext exports:**
- On shared network drives without encryption
- In personal cloud storage (Google Drive, Dropbox) without encryption
- On unencrypted USB drives
- In email (not even as a draft)

### 3. Retention and Destruction

- **Keep only the most recent backup.** When a new export supersedes an old one, securely delete the previous file.
- **Secure deletion** means overwriting or destroying the media — not just moving the file to the recycle bin.
- **If your organisation leaves KoNote**, securely delete all plaintext exports within 90 days of receiving your final encrypted offboarding export, unless you have an active legal obligation to retain the data.

### 4. Breach Response

If a plaintext export is lost, stolen, or accessed by an unauthorised person:

- **Notify KoNote immediately** (within 24 hours of discovery)
- **Assess the scope** — what data was in the file, how many participants are affected
- **Follow your organisation's breach response plan** and applicable privacy legislation (PIPEDA mandatory breach notification, s. 10.1)
- **Note:** A properly encrypted export (AES-256-GCM) that is lost or stolen does not require breach notification if the encryption key was not also compromised. A plaintext export that is lost or stolen **does** require breach notification.

### 5. Staff Awareness

- Staff who handle exported files must understand these responsibilities
- Include data export handling in your organisation's privacy training
- The designated contact person should review this acknowledgement annually

---

## KoNote's Responsibilities

KoNote commits to the following:

- **Providing the export tool** and keeping it current as the system evolves
- **Sending periodic reminders** (quarterly by default, configurable) when a backup is due
- **Logging every export** in the audit database — who ran it, when, what format, how many records
- **Supporting your organisation** in running exports or responding to PIPEDA data access requests within the agreed SLA
- **Never accessing your plaintext exports** — once the file is handed to your organisation, KoNote does not retain a copy

---

## What This Acknowledgement Does NOT Cover

This acknowledgement is specifically about **plaintext exports** (decrypted backup files). The following are covered by the standard service agreement and do not require this acknowledgement:

- **Encrypted offboarding exports** — AES-256-GCM encrypted files produced when an agency leaves KoNote
- **Individual client exports** — single-client data produced via the client profile for PIPEDA requests or program transfers (delivered via time-limited secure download link)
- **Aggregate reports** — de-identified funder and partner reports
- **Database backups** — encrypted at rest by the hosting provider; these are ciphertext, not readable data

---

## Signatures

By signing below, you confirm that:

1. You have read and understand this acknowledgement
2. You accept responsibility for the secure handling of plaintext exports
3. You have designated a contact person for data export reminders
4. You understand that a plaintext export has no access control once it leaves KoNote
5. You will notify KoNote within 24 hours if an export is lost, stolen, or accessed by an unauthorised person

> **Organisation:** ____________________________
>
> **Signed by:** ____________________________ (print name)
>
> **Title:** ____________________________
>
> **Signature:** ____________________________
>
> **Date:** ____________________________

> **KoNote representative:** ____________________________
>
> **Signature:** ____________________________
>
> **Date:** ____________________________

---

*This template requires legal review before use with a real agency. It is written in plain language for nonprofit executive directors and board members who may not have technical or legal backgrounds. A lawyer should review it for compliance with PIPEDA, applicable provincial privacy legislation, and your organisation's specific data governance requirements.*
