# 10 — Data Responsibilities

## What This Configures

Nothing in KoNote itself. This document captures decisions about the agency's **data handling responsibilities** — things KoNote cannot enforce technically that the agency must manage through policy and practice.

The completed decisions feed into the [Data Handling Acknowledgement](../data-handling-acknowledgement.md), which the agency signs during Phase 4 (Go-Live Verification).

## Decisions Needed

### 1. Encryption key storage

Where will the encryption key be stored, and who can access it?

- **Password manager** (1Password, Bitwarden) → accessible, good for small agencies
- **Azure Key Vault** → integrated with Azure infrastructure, good for agencies with IT staff
- **Other secure location** → must be separate from database backups, accessible to at least two people

Default: Must choose one. At least two named individuals must be able to retrieve it.

### 2. Document storage provider

Does the agency want to link KoNote participant records to external document folders?

- **SharePoint** → for staff documents (assessments, consent forms). Requires M365 tenant. IT sets up document libraries per program during Phase 2.
- **Google Drive** → for participant portal documents (resource kits, working files). Requires Google accounts for participants.
- **Both** → SharePoint for staff, Google Drive for portal
- **Neither / Later** → skip document integration for now

Default: No document integration. Can be enabled at any time after go-live.

### 3. SharePoint setup decisions *(if using SharePoint)*

- **Who maintains SharePoint permissions when staff change?** Named person or role. → Must designate.
- **Will you use Power Automate for automatic folder creation?** Yes (recommended) / No (manual). → Manual at first, automate within 30 days.
- **What is your document retention period?** 7 years (PHIPA minimum) / Other. → 7 years.

### 4. Google Drive setup decisions *(if using portal documents)*

- **Who creates participant folders?** Shared service account (recommended) / Individual workers. → Shared service account.
- **What starter resources go in each folder?** 4-7 key resources per program (recommended). → Agency decides per program.

### 5. Export handling

- **Who is notified when exports are generated?** Named people (1-3 recommended). → Must designate at least one.
- **Who reviews the export log?** Privacy officer / ED / Designated person. → Must designate.
- **How often is the export log reviewed?** Quarterly (recommended) / Monthly / Annually. → Quarterly.

### 6. Plaintext backup

- **Do you want plaintext backups?** Yes (recommended) / No. → No (must opt in).
- **If yes — who is the designated custodian?** Named person (privacy officer recommended). → Must designate.
- **How often?** Quarterly (recommended) / After major data entry periods. → Quarterly.
- **Where will it be stored?** Encrypted USB in locked safe / Encrypted cloud / Other. → Must specify.

### 7. Staff departure process

- **Who handles staff departure offboarding?** Named person or role. → Must designate.
- **Is there an existing IT offboarding checklist?** Yes (add KoNote + SharePoint + Google Drive steps) / No (use the acknowledgement as a starting point).

## Common Configurations

### Small agency (5-15 staff), SharePoint, no portal

- Encryption key: shared 1Password vault, ED + one admin
- SharePoint: enabled, one library per program, manual folder creation to start
- Google Drive: not applicable (portal not enabled)
- Exports: ED receives notifications, reviews quarterly
- Plaintext backup: opted in, quarterly, encrypted USB in office safe
- Staff departures: office manager handles

### Medium agency (15-50 staff), SharePoint + portal

- Encryption key: Azure Key Vault, IT lead + ED
- SharePoint: enabled, Power Automate for folder creation, IT maintains permissions
- Google Drive: enabled via shared service account, program managers create folders
- Exports: privacy officer receives notifications, reviews monthly
- Plaintext backup: opted in, quarterly, encrypted cloud storage
- Staff departures: HR + IT follow joint checklist

## Output Format

The completed decisions are recorded in the signed [Data Handling Acknowledgement](../data-handling-acknowledgement.md). No KoNote configuration changes result — this is purely about organisational practice.

## Dependencies

- **Requires:** Decisions from 02 (Features), 03 (Roles & Permissions), 04 (Programs), 08 (Users)
- **Feeds into:** 09 (Verification) — the signed acknowledgement is a go-live prerequisite
