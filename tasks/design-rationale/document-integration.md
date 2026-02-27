# Design Rationale: Dual Document Integration (SharePoint + Google Drive)

**Status:** Proposed — awaiting PB and SG approval
**Date:** 2026-02-27
**Expert panel:** 5 perspectives (Nonprofit IT Administrator, Health Information Privacy Specialist, Social Services Program Manager, Information Architecture Specialist, Participant Experience Researcher)

## Summary

KoNote needs two separate document integrations for two different audiences and purposes:

1. **SharePoint** — internal staff documents on the participant record (assessments, consent forms, case correspondence)
2. **Google Drive** — participant-owned working documents in the portal (budgets, spreadsheets, job search tools)

KoNote acts as a **link broker** in both cases — it stores folder URLs and generates links, but never touches, stores, or transmits document contents.

## Design Decisions

### 1. Dual-provider architecture

| | SharePoint (Staff) | Google Drive (Portal) |
|---|---|---|
| **Who sees it** | Staff only, on client record | Participant + their worker, in portal |
| **Purpose** | Internal case documents | Participant's own working files |
| **Ownership** | Agency owns the folder | Participant owns the folder |
| **Access** | Staff with access to that program | Participant + assigned worker |
| **At discharge** | Folder retained per retention policy | Worker removes access; participant keeps everything |

**Why two providers:** SharePoint stays within the Microsoft tenant (where staff already authenticate via Azure AD SSO). Google Drive is accessible to participants who almost universally have Google accounts but not Microsoft accounts. The separation also enforces a clean boundary: staff documents never mix with participant documents.

### 2. Program-centric SharePoint folder structure (not client-centric)

**Decided:** One SharePoint document library per program, one subfolder per client.

```
SharePoint Site: KoNote Documents
└── Document Libraries (one per program):
    ├── Youth Employment/
    │   ├── REC-2024-001/
    │   ├── REC-2024-015/
    │   └── ...
    ├── Housing Support/
    │   ├── REC-2024-001/
    │   └── ...
    └── Financial Literacy/
        └── ...
```

**Why program-centric:**

- **Permissions map to programs.** SharePoint permissions are set at the library level. All Youth Employment staff get access to the Youth Employment library. No per-folder permission management needed.
- **Transfers are clean.** When a client transfers from Program A to Program B, Program B creates a new folder. Program A's folder stays put — those are historical records. No folder moving, no broken links.
- **Multi-program is clean.** If a client is in two programs, each has its own folder. Program A staff don't see Program B's documents. This aligns with PHIPA consent boundaries.
- **Staff changes are simple.** When a worker changes, you update SharePoint group membership. Folders don't move.

**Rejected alternative — client-centric folders:**
A single folder per client with program subfolders would require per-folder permissions (expensive to manage) and would tempt staff to browse other programs' documents, breaking PHIPA consent boundaries.

### 3. Folder naming: Record ID only (not client name)

**Decided:** SharePoint folders are named by Record ID only (e.g., `REC-2024-001`), not `REC-2024-001 - Smith, Jane`.

**Why:** Including client name in the folder path puts PII in SharePoint URLs, browser history, and SharePoint activity logs. Record ID alone is a pseudonymous identifier.

**For discoverability:** Add client name as a SharePoint metadata column on the folder so it's searchable without being in the path. This is a SharePoint configuration, not a KoNote change.

### 4. Google Drive link stored per program enrolment (not per client)

**Decided:** The Google Drive folder URL is stored on the program enrolment record, not on the client record globally.

**Why:** If a client is in two programs (Employment Readiness and Financial Literacy), they may have two different Google Drive folders with different resource kits. One link per enrolment keeps it clean. The portal shows the link for each active program, labelled by program name.

### 5. Google Drive URL is not encrypted

**Decided:** The Google Drive folder URL is stored as a plain `URLField`, not an encrypted BinaryField. GK approved 2026-02-27.

**Why:** The URL (`https://drive.google.com/drive/folders/1aBcDeFg...`) is an opaque identifier that reveals nothing about the client or program. The enrolment record itself is already access-controlled by RBAC. Encryption would prevent useful SQL queries (e.g., "how many enrolments have documents configured?") and add complexity without meaningful security benefit. Anyone who obtains the URL still needs Google Drive permissions to access the folder. Expert panel (4 of 4) agreed encryption is unnecessary.

### 6. Link-broker only — no API/OAuth integration

**Decided:** KoNote stores folder URLs and generates links. It does not authenticate to SharePoint or Google Drive, does not create folders, does not upload or download files.

**Why:**
- Dramatically simpler to build and maintain
- Reduces KoNote's custodian obligations — files remain under whoever manages SharePoint/Drive
- Avoids OAuth token management, API rate limits, Google/Microsoft API quota
- SharePoint and Google Drive handle their own authentication when the link is clicked

**Future path:** If demand justifies it, Microsoft Graph API integration could enable automatic folder creation in SharePoint. But the link-broker approach is correct for launch.

### 6. "Digital toolkit handoff" workflow for Google Drive

**The workflow:**

1. Worker creates a Google Drive folder for the participant
2. Worker populates it with program resources (budget templates, job search tools, etc.)
3. Worker shares the folder with the participant via their email
4. Worker pastes the Google Drive folder link into KoNote
5. Participant sees "Your [Program Name] Documents" link in their portal
6. At program discharge, worker **transfers ownership** to participant, then removes themselves
7. Participant keeps everything — their own space, their own data

**Why this model:** Positions the folder as the participant's property from day one. At discharge, the handoff is an empowerment moment ("these tools are yours"), not a loss moment.

## Technical Requirements

### Data model changes

- Add `document_folder_url` field to the program enrolment model (for Google Drive portal link)
- Existing SharePoint URL template on program settings stays (per-program template with `{record_id}` placeholder)
- Both URL fields must be **encrypted at rest** (Fernet/AES, consistent with other PII fields)
- Both must be **audit-logged** when accessed/displayed

### URL validation on input

- **SharePoint:** Must match `https://*.sharepoint.com/*`
- **Google Drive:** Must match `https://drive.google.com/drive/folders/*` (folder URL, not doc or search URL)
- Domain allowlist already exists in the security audit command — extend it

### Portal UI

- Label as "Your [Program Name] Documents" — not generic "My Documents"
- Include brief onboarding text explaining ownership model
- For multi-program participants, show each folder labelled by program name
- At discharge, display empowerment-framed message about document ownership

### Staff UI

- SharePoint button on client record stays as-is (per current implementation)
- If client is in multiple programs, show buttons per active program enrolment
- Google Drive link field on the program enrolment form (paste-a-link)

## Operational Documentation Required

KoNote should provide the following as part of the feature:

### 1. SharePoint setup guide

- Creating document libraries per program
- **Power Automate flow for automated folder creation** — a SharePoint list with Record ID triggers a flow that creates the folder with the correct name. Eliminates naming errors. This is recommended from day one, not as an optional enhancement.
- SharePoint group configuration to match KoNote program roles

### 2. Google Drive setup guide

- **Shared service account option** — use a shared account (e.g., `clientdocs@agency.org`) for creating folders instead of individual worker accounts. Prevents folder loss when a worker's account is deprovisioned. Recommended for agencies with high staff turnover.
- **Template folder approach** — program manager creates a master folder with standard resources; workers copy it per participant.
- **Starter kit guidance** — start with 4-7 key resources, not 20+. Workers add more based on individual client needs.

### 3. Discharge checklist

- Transfer Google Drive ownership to participant (with micro-tutorial or link to Google support)
- Remove worker access from Google Drive
- Checkbox in KoNote discharge workflow: "I have transferred ownership and removed my access to the participant's Google Drive folder"

### 4. Retention policy template

- Retention period per document type (funder requirements + PHIPA minimums — 7 years for health information custodians)
- Who is responsible for deletion after retention period
- How deletion is documented (audit trail)
- This is a SharePoint administration concern, but KoNote documentation should flag it

### 5. Staff reminders

- When a worker is added/removed from a program in KoNote: reminder to update SharePoint group membership
- When a client is discharged: reminder about Google Drive ownership transfer

## Risk Registry

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Google Drive ownership not transferred at discharge | High | Medium — participant loses access to their documents | Discharge checklist in KoNote + shared service account recommendation |
| SharePoint folder naming inconsistency breaks links | Medium | Low — staff can still navigate manually in SharePoint | Power Automate folder creation + URL validation |
| Worker uploads clinical documents to participant's Google Drive | Low | High — PHIPA breach if health info stored outside Canada | Policy documentation + training; KoNote help text warning |
| Worker's Google account deprovisioned before ownership transfer | Medium | Medium — participant loses access | Shared service account recommendation; periodic audit |
| SharePoint folders not deleted after retention period | Medium | Low — storage cost; possible over-retention | Retention policy template; SharePoint retention policies |

## Anti-Patterns

### Do not: Store document contents in KoNote
KoNote is a link broker. It never downloads, caches, previews, or stores document contents. This would increase custodian obligations and attack surface.

### Do not: Use OAuth/API integration at launch
The complexity of OAuth token management, API quota, and error handling is not justified when paste-a-link achieves the same user outcome. Revisit only if a clear operational need emerges (e.g., automatic folder creation is failing manually).

### Do not: Allow cross-program folder URL copying
When a client transfers between programs, the new program should establish its own document folder independently. Copying the old program's folder URL would bypass consent boundaries.

### Do not: Put client names in SharePoint folder paths
Client names in folder paths leak PII into URLs, browser history, and activity logs. Use Record ID only; add client name as SharePoint metadata.

### Do not: Store the Google Drive link on the client record globally
Store it on the program enrolment. Global storage breaks when a client is in multiple programs with different resource folders.

### Do not: Skip the Google Drive ownership transfer at discharge
If the worker created the folder, they are the owner. Removing themselves without transferring ownership may make the folder inaccessible to the participant. This must be in the discharge checklist.

## PHIPA/PIPEDA Compliance Notes

- **Program-centric separation** enforces PHIPA s. 17(1) purpose limitation structurally — staff in Program A cannot access Program B's documents
- **KoNote as link broker** limits custodian obligations — file contents remain under the custodianship of whoever manages SharePoint/Drive
- **Folder URLs are protected metadata** — they encode program membership and must be encrypted, access-controlled, and audit-logged
- **Google Drive and data residency** — Google Drive data may be stored outside Canada. The design mitigates this by framing Google Drive as participant-owned content (personal working documents), not agency health records. Staff must not upload clinical documents to participant Google Drive folders. Document this in training materials.
- **Referral disclosures** — when Program A writes a referral summary for Program B, that's a disclosure under PHIPA requiring participant consent or a permitted purpose under s. 39. KoNote's transfer workflow should prompt for consent confirmation.
- **Retention** — PHIPA s. 13(1) requires a retention policy; s. 13(2) requires secure disposal after the retention period. Agencies must set SharePoint retention policies accordingly (7-year minimum typical for health information custodians).

## Decision Framework (RAPID)

| Role | Who |
|---|---|
| **Recommend** | Expert panel — adopt the dual-provider design with enhancements above |
| **Agree** | PB (technical feasibility), SG (operational fit) |
| **Perform** | Development team (KoNote code) + agency IT admin (SharePoint/Google setup) |
| **Input** | Frontline workers (workflow validation), participants (portal UX feedback) |
| **Decide** | GK as product owner |

## Implementation Sequence

1. **Data model** — Add `document_folder_url` to program enrolment; update program settings for per-program SharePoint URL template
2. **Staff UI** — Update client record to show per-program SharePoint buttons; add Google Drive link field to enrolment form
3. **Portal UI** — Add "Your Documents" link to participant portal, labelled by program
4. **Validation** — URL format validation on input, domain allowlist enforcement
5. **Security** — Encrypt URL fields, add audit logging, extend security audit command
6. **Discharge workflow** — Add Google Drive handoff checklist to discharge process
7. **Documentation** — SharePoint setup guide, Google Drive setup guide, discharge checklist, retention policy template
