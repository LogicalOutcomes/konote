# Data Handling Acknowledgement — Plaintext Export

**Status:** Template — requires legal review before use with a real agency

**When to use:** Before enabling plaintext data exports for an agency. Discussed during Phase 1 (Permissions Setup) of the deployment protocol. Signed during Phase 4 (Go-Live Verification).

**Related:** [tasks/agency-data-offboarding.md](../tasks/agency-data-offboarding.md) — full design for the export system

---

## About This Document

This is an internal policy acknowledgement for your organisation. KoNote is open-source software — it is a tool, not a service provider, and it makes no warranties or commitments. This document exists to help your organisation make an informed decision about plaintext data exports and to document that decision for your own records.

**You do not need to sign this to use KoNote.** This acknowledgement is only relevant if your organisation chooses to produce plaintext (unencrypted) data exports — for example, as a backup against encryption key loss.

---

## How KoNote Protects Your Data

While data stays inside KoNote, it is protected by multiple layers:

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
- **Audit logging is gone** — no system can track who opens, copies, or forwards the file
- **Authentication is gone** — there is no login required to read the file

**The file contains everything.** A plaintext export has no access control after it is produced — whoever has the file has all your participant data.

---

## Why You Might Want a Plaintext Export

Despite the risks above, there is one scenario where a plaintext backup is the responsible choice:

**Key loss insurance.** KoNote uses encryption that is all-or-nothing. If your organisation loses the encryption key — due to a server failure, administrative turnover, or misconfigured migration — every encrypted field in your database becomes permanently unrecoverable. No one can recover this data.

A plaintext backup stored securely by your organisation ensures that even in a worst-case key loss scenario, your participant data is not permanently lost.

KoNote includes an export tool and can be configured to send periodic reminders when a backup is due. Your organisation decides whether and when to act on each reminder.

---

## What the Software Provides

KoNote includes the following features related to data export. These are capabilities of the software, not commitments from a service provider:

- **Export tool** (`export_agency_data` management command) that produces structured data files
- **Configurable backup reminders** sent to a designated contact person when a backup is due
- **Audit logging** of every export — who ran it, when, what format, how many records
- **Encrypted export mode** (AES-256-GCM) as the default, with plaintext as an opt-in alternative
- **Dry-run mode** to preview what would be exported without writing data

Your organisation is responsible for operating and maintaining the software, or for arranging with a hosting provider to do so on your behalf. Any service commitments (SLAs, support, managed exports) are between your organisation and your hosting provider — not part of this document.

---

## Your Organisation's Responsibilities

By signing this acknowledgement, your organisation confirms it understands the following and accepts responsibility:

### 1. Designated Contact Person

You will designate one person as the **data export contact**. This person:
- Receives backup reminders from the system
- Initiates or runs exports
- Is responsible for the secure handling of exported files
- Must be replaced promptly if they leave the organisation

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
- **If your organisation stops using KoNote**, securely delete all plaintext exports within 90 days of receiving your final encrypted export, unless you have an active legal obligation to retain the data.

### 4. Breach Response

If a plaintext export is lost, stolen, or accessed by an unauthorised person:

- **Assess the scope** — what data was in the file, how many participants are affected
- **Follow your organisation's breach response plan** and applicable privacy legislation (PIPEDA mandatory breach notification, s. 10.1)
- **Notify your hosting provider** if applicable, so they can assist with the response
- **Note:** A properly encrypted export (AES-256-GCM) that is lost or stolen does not require breach notification if the passphrase was not also compromised. A plaintext export that is lost or stolen **does** require breach notification.

### 5. Staff Awareness

- Staff who handle exported files must understand these responsibilities
- Include data export handling in your organisation's privacy training
- The designated contact person should review this acknowledgement annually

---

## What This Acknowledgement Does NOT Cover

This acknowledgement is specifically about **plaintext exports** (decrypted backup files). The following do not require this acknowledgement:

- **Encrypted exports** — AES-256-GCM encrypted files produced for offboarding or migration
- **Individual client exports** — single-client data produced via the client profile for PIPEDA requests or program transfers (delivered via time-limited secure download link)
- **Aggregate reports** — de-identified funder and partner reports
- **Database backups** — encrypted at rest by the hosting provider; these are ciphertext, not readable data

---

## Signatures

By signing below, your organisation confirms that:

1. You have read and understand this acknowledgement
2. You accept responsibility for the secure handling of plaintext exports
3. You have designated a contact person for data export reminders
4. You understand that a plaintext export has no access control once it is produced
5. You understand that KoNote is open-source software provided as-is, and that responsibility for data security after export rests entirely with your organisation

> **Organisation:** ____________________________
>
> **Signed by:** ____________________________ (print name)
>
> **Title:** ____________________________
>
> **Signature:** ____________________________
>
> **Date:** ____________________________

---

*This template requires legal review before use with a real agency. It is written in plain language for nonprofit executive directors and board members who may not have technical or legal backgrounds. A lawyer should review it for compliance with PIPEDA, applicable provincial privacy legislation, and your organisation's specific data governance requirements.*
