# Data Export Acknowledgement

**Status:** Template — requires legal review before use with a real agency

**When to use:** Before enabling plaintext data exports for an agency. Discussed during Phase 1 (Permissions Setup) of the deployment protocol. Signed during Phase 4 (Go-Live Verification).

**Related:** [tasks/agency-data-offboarding.md](../tasks/agency-data-offboarding.md)

---

## Purpose

This document records your organisation's decision to receive plaintext (unencrypted) data exports from KoNote and your acceptance of responsibility for safeguarding those files.

Under the *Personal Information Protection and Electronic Documents Act* (PIPEDA), your organisation is accountable for personal information in its custody or control (Principle 1, s. 4.1). This accountability does not change when data moves from one format to another — it applies equally to information inside software and information in an exported file.

**You do not need to sign this to use KoNote.** This acknowledgement is only relevant if your organisation chooses to produce plaintext exports (e.g., as a backup against encryption key loss). Encrypted exports, individual client exports, and aggregate reports do not require it.

---

## What Plaintext Export Means

Inside KoNote, personal information is protected by encryption, role-based access control, consent enforcement, audit logging, and authentication. These protections are built into the software and operate automatically.

A plaintext export produces a file containing **all personal information in your KoNote instance, decrypted and readable** — including names, dates of birth, contact information, clinical notes, progress records, and metric scores.

Once that file exists outside the software:

- **No encryption** — the file is readable by anyone who possesses it
- **No access control** — there are no roles, program boundaries, or consent filters
- **No audit trail** — no system tracks who opens, copies, or forwards the file
- **No authentication** — no login is required

The file is equivalent to a printed copy of every participant record in your organisation. Whoever has it has everything.

---

## Why You Might Choose This

KoNote uses field-level encryption (Fernet / AES-128-CBC). This encryption is all-or-nothing: if the encryption key is lost, every encrypted field becomes permanently unrecoverable. No one can reverse this.

A plaintext backup stored securely by your organisation protects against this scenario. The trade-off is clear: you accept the risk of possessing a readable copy of all participant data in exchange for insurance against catastrophic key loss.

---

## Your Obligations Under PIPEDA

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

## What This Acknowledgement Does NOT Cover

- **Encrypted exports** — AES-256-GCM encrypted files for offboarding or migration. Protected by encryption; no plaintext handling obligations arise.
- **Individual client exports** — single-client data from the client profile for PIPEDA access requests or program transfers. Delivered via time-limited secure download link. Different risk profile (one person's data, not an entire agency).
- **Aggregate reports** — de-identified funder and partner reports. No personal information.
- **Database backups** — encrypted at rest by the hosting infrastructure. Not readable without the encryption key.
- **The service relationship between your organisation and your hosting provider** — if a third party (such as LogicalOutcomes) hosts and operates KoNote on your behalf, the terms of that relationship (data processing, security commitments, SLAs, breach notification chain) should be documented in a separate service agreement under PIPEDA Principle 1, s. 4.1.3.

---

## Acknowledgement

By signing below, the undersigned confirms on behalf of the organisation that:

1. We understand that a plaintext export removes all software-based protections from participant data
2. We accept accountability for safeguarding exported files in accordance with PIPEDA and applicable provincial legislation
3. We have designated an individual accountable for data export handling
4. We will store plaintext exports using safeguards appropriate to the sensitivity of the information
5. We will retain only the most recent backup and securely destroy superseded copies
6. We understand our mandatory breach notification obligations under PIPEDA s. 10.1 if an export is compromised
7. We understand that KoNote is open-source software provided without warranty, and that responsibility for personal information after export rests entirely with our organisation

> **Organisation:** ____________________________
>
> **Signed by:** ____________________________
>
> **Title:** ____________________________
>
> **Date:** ____________________________

---

## Note on Managed Hosting

If your organisation uses a managed hosting arrangement (a third party operates KoNote on your behalf), PIPEDA Principle 1 (s. 4.1.3) requires that you use contractual or other means to provide a comparable level of protection while your data is being processed by that third party. This acknowledgement does not serve that purpose — you should have a separate data processing or service agreement with your hosting provider that covers security measures, data residency, access controls, breach notification responsibilities, and termination procedures.

---

*This template requires legal review before use with a real agency. It is written in plain language for nonprofit executive directors and board members. A lawyer should review it for compliance with PIPEDA, applicable provincial privacy legislation (including PHIPA if your organisation is a health information custodian), and your organisation's specific governance requirements.*
