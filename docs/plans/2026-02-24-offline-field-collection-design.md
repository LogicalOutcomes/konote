# Offline Field Collection via ODK Central — Design Document

**Date:** 2026-02-24
**Status:** Approved — implementation waiting on Circles Lite completion
**DRR:** `tasks/design-rationale/offline-field-collection.md`
**Depends on:** Circles Lite (FAM-DESIGN1) for Phase 3; Phases 1-2 can start independently

---

## Summary

KoNote integrates with a self-hosted ODK Central instance to enable offline mobile data collection for field staff in rural and remote areas. Staff use ODK Collect (Android) or Enketo web forms (iOS fallback) to record group session attendance, individual visit notes, and circle/family observations while offline for 1-3 days, then sync when back online.

A Django management command (`sync_odk`) handles all communication between KoNote and ODK Central — pushing participant data out and pulling submissions in. Admins configure field collection per-program from KoNote's admin interface. No one needs to log into ODK Central directly.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Canadian Cloud Infrastructure                            │
│                                                          │
│  ┌─────────────────┐     ┌─────────────────────────┐    │
│  │   KoNote         │     │   ODK Central            │    │
│  │   (Django 5)     │────►│   (Node.js + Enketo)     │    │
│  │                  │◄────│                           │    │
│  │  PostgreSQL (app)│     │  PostgreSQL (ODK)         │    │
│  │  PostgreSQL (aud)│     │                           │    │
│  └─────────────────┘     └─────────────────────────┘    │
│         ▲          sync_odk        ▲                     │
│         │ HTTPS    (cron/celery)   │ HTTPS               │
└─────────┼──────────────────────────┼─────────────────────┘
          │                          │
    ┌─────┴─────┐              ┌─────┴──────┐
    │ Office    │              │ Field      │
    │ staff     │              │ staff      │
    │ (browser) │              │ (phone/    │
    └───────────┘              │  tablet)   │
                               └────────────┘
                                ODK Collect (Android)
                                Enketo (iOS/browser)
```

**Two separate systems, one sync bridge.** KoNote and ODK Central each have their own database, Docker stack, and domain. The `sync_odk` management command is the only connection point.

---

## PII Tiers — Per-Program Configuration

Each program has a `field_data_tier` setting controlling what participant data is pushed to ODK Central Entity lists:

| Tier | Fields on Device | Scope | Device Requirements | Use Case |
|------|-----------------|-------|-------------------|----------|
| **Restricted** | KoNote ID only | Full roster | Any | DV, crisis, high-risk populations |
| **Standard** (default) | ID + first name | Full roster | Any | Group attendance, small caseloads |
| **Field** | ID + first name + last initial | Full roster | PIN required | Large caseloads, name collisions |
| **Field+Contact** | ID + first name + last initial + phone | Scheduled visits / assigned caseload only | PIN + device policy | Home visiting, outreach with field scheduling |

**Hard rules (not configurable, all tiers):**
- Program name/type never appears on devices
- No DOB, address, or health information on devices
- Entity list names are always generic ("Participants", "Groups")
- Form titles are always generic ("Visit Note", "Session Attendance")

**Device loss protocol per tier:**
- **Restricted:** No PII exposed. Log incident internally.
- **Standard:** First names exposed. Assess context — small community may warrant breach notification.
- **Field:** Names + initials exposed. Follow agency breach notification protocol. Regenerate sync IDs.
- **Field+Contact:** Names + phone numbers for scheduled participants. Full breach protocol. Regenerate IDs. Notify affected participants.

---

## Program Profiles — Admin Configuration

Admins configure field collection from the Program settings page in KoNote:

```
┌─────────────────────────────────────────┐
│  Field Data Collection                   │
│                                          │
│  ☑ Enable offline field collection       │
│                                          │
│  Profile: [▼ Home Visiting           ]  │
│  Data tier: [▼ Standard (ID + name)  ]  │
│                                          │
│  Forms included:                         │
│  ☑ Visit Note                            │
│  ☐ Session Attendance                    │
│  ☐ Circle Observation                    │
│                                          │
│  [Save]                                  │
└─────────────────────────────────────────┘
```

| Profile | Forms Included | Typical Use |
|---------|---------------|-------------|
| **Group Programs** | Session Attendance | Drop-in, workshops, recreation, classes |
| **Home Visiting** | Visit Note | Individual outreach, coaching, check-ins |
| **Circle Programs** | Visit Note + Circle Observation | Family/care network monitoring |
| **Full Field** | All three forms | Programs doing both group and individual field work |

**Automatic cascading:**
- Circle Observation form hidden when Circles feature toggle is off for a program
- User program roles in KoNote automatically map to ODK Central App User access
- Saving configuration triggers sync on next `sync_odk` run

---

## ODK Forms

### Form 1: Session Attendance

**Purpose:** Record who attended a group session
**Creates in KoNote:** `GroupSession` + `GroupSessionAttendance` records

| Field | Type | Source |
|-------|------|--------|
| Group | select_one from Entity list "Groups" | Pre-populated from KoNote |
| Date | date | Worker enters |
| Location | text (optional) | Worker enters |
| Members present | select_multiple from Entity list "GroupMembers_{group}" | Checkboxes, default all checked |
| Session notes | text (optional) | Worker enters |

### Form 2: Visit Note

**Purpose:** Record observations from an individual visit
**Creates in KoNote:** `ProgressNote` (quick type)

| Field | Type | Source |
|-------|------|--------|
| Participant | select_one from Entity list "Participants" | Pre-populated from KoNote |
| Date | date | Worker enters |
| Visit type | select_one: home visit, community, phone, virtual | Worker selects |
| Observations | text | Worker enters |
| Engagement | select_one: 1-6 scale (matches KoNote) | Worker selects |
| Alliance rating | select_one: 1-5 scale (matches KoNote) | Worker selects (optional) |

### Form 3: Circle Observation (Phase 3 — requires Circles Lite)

**Purpose:** Record observations about a family/circle during a visit
**Creates in KoNote:** `ProgressNote` with `circle` FK + optionally new `CircleMembership` records

| Field | Type | Source |
|-------|------|--------|
| Circle | select_one from Entity list "Circles" | Pre-populated from KoNote |
| Date | date | Worker enters |
| Members present | select_multiple from Entity list "CircleMembers_{circle}" | Checkboxes |
| Observations | text | Worker enters |
| New relationship | repeat group (optional): member name, relationship label | Worker enters |

---

## Data Flow — Sync Command

The `sync_odk` management command handles all data movement:

```
python manage.py sync_odk [--direction=both|push|pull] [--program=ID] [--dry-run]
```

### Push direction (KoNote → ODK Central)

1. For each program with `field_collection_enabled=True`:
   a. Create/update ODK Central Project (one per program)
   b. Deploy form XLSForm files based on program profile
   c. Push participant Entity list with tier-appropriate fields
   d. Push group/circle Entity lists if relevant forms enabled
   e. Create/update App Users from KoNote UserProgramRoles

2. For Field+Contact tier:
   a. Query scheduled visits for upcoming period (configurable: 1-7 days)
   b. Push only scheduled participants with phone numbers
   c. Previous Entity list is overwritten (stale numbers removed)

### Pull direction (ODK Central → KoNote)

1. For each program with field collection enabled:
   a. GET new submissions since last sync timestamp
   b. For each attendance submission:
      - Find or create GroupSession by group + date
      - Create GroupSessionAttendance for each member (match by KoNote ID)
      - Skip if session already exists for that date+group (dedup)
   c. For each visit note submission:
      - Create ProgressNote (quick type) on the participant's record
      - Set engagement, alliance values from form data
      - Set author from ODK App User → KoNote User mapping
   d. For each circle observation (Phase 3):
      - Create ProgressNote with circle FK
      - Create new CircleMembership records for any new relationships
   e. Log all created records to AuditLog (using "audit" database)

3. Record sync timestamp, counts, and any errors

### Error handling

- **Unknown participant ID:** Log warning, skip record, include in sync report
- **Duplicate session:** Skip with info log (likely re-submission)
- **ODK Central unreachable:** Retry with exponential backoff (3 attempts), then fail with notification
- **Validation error:** Log the submission data and error, skip record, include in sync report

---

## ODK Central ↔ KoNote Mapping

### User/Access Mapping

```
KoNote UserProgramRole  →  ODK Central App User
- Staff in Program A    →  Access to ODK Project A
- Staff in Program B    →  Access to ODK Project B
- No role in Program C  →  No access to ODK Project C
```

### Data Model Mapping

| ODK Concept | KoNote Equivalent |
|------------|-------------------|
| Project | Program (with field_collection_enabled) |
| App User | User with UserProgramRole |
| Entity List "Participants" | ClientFile (filtered by program enrolment + tier) |
| Entity List "Groups" | Group (filtered by program) |
| Entity List "Circles" | Circle (via CircleMembership, filtered by program) |
| Form Submission (attendance) | GroupSession + GroupSessionAttendance |
| Form Submission (visit note) | ProgressNote (quick type) |
| Form Submission (circle obs) | ProgressNote with circle FK |

---

## Deployment

### ODK Central Infrastructure

- **Docker Compose** stack running on a Canadian cloud VM (Azure Canada East or similar)
- **Resources:** ~2 GB RAM, 15 GB disk minimum
- **Containers:** Node.js backend, PostgreSQL, Enketo, Nginx
- **Domain:** `odk.yourdomain.com` (separate from KoNote's domain)
- **HTTPS:** Handled by Central's built-in Nginx or external Caddy

### For Railway-hosted KoNote

ODK Central cannot run on Railway (multi-container stack). Deploy Central on a separate Azure VM (~$15-30 CAD/month). The `sync_odk` command runs on the Railway instance and reaches Central via HTTPS.

### For Docker Compose-hosted KoNote

Can run on the same server if it has 4-6 GB RAM total. Separate docker-compose files, shared reverse proxy.

---

## Platform Support

| Platform | Method | Offline Reliability | Notes |
|----------|--------|-------------------|-------|
| **Android** (primary) | ODK Collect native app | Excellent — days/weeks offline | Battle-tested by humanitarian orgs worldwide |
| **iOS** (fallback) | Enketo web forms in Safari | Functional with caveats | 7-day storage eviction risk; must use Safari; no background sync |
| **Desktop browser** | Enketo web forms | Good (for testing/office use) | Not the intended use case but works |

**iOS workaround training for agencies:** Staff using iPhones must open the Enketo form at least once every 5 days to prevent data eviction. Agency should provide Android tablets for dedicated field work if staff primarily use iPhones.

---

## Implementation Phases

### Phase 1: Foundation — ODK Central + Attendance + Visit Notes
**Depends on:** Nothing — can start now
**Estimated scope:** 2-3 weeks

Tasks:
1. Deploy ODK Central on a Canadian VM (Docker Compose)
2. Create Django app `apps/field_collection/`
3. Add Program model fields: `field_collection_enabled`, `field_data_tier`, `field_collection_profile`
4. Build `sync_odk` management command — push Entities, pull submissions
5. Design XLSForm for Session Attendance
6. Design XLSForm for Visit Note
7. Build admin UI section on Program settings page
8. Map ODK App Users from KoNote UserProgramRoles
9. Handle pulled submissions: create GroupSession/Attendance/ProgressNote records
10. Add sync logging to AuditLog
11. Write tests for sync command (push, pull, dedup, error handling)
12. Document ODK Central deployment and agency setup

### Phase 2: Configuration & Polish
**Depends on:** Phase 1 complete
**Estimated scope:** 1-2 weeks

Tasks:
1. Implement four PII tiers with scope control for Field+Contact
2. Implement program profiles (Group / Home Visiting / Circle / Full Field)
3. Build device loss protocol (ID regeneration capability)
4. Add sync status dashboard in KoNote admin (last sync, record counts, errors)
5. Write agency-facing documentation (ODK Collect setup guide, form usage guide)
6. French translations for admin UI and documentation
7. Test across Android devices and iOS Safari

### Phase 3: Circles Integration
**Depends on:** Phase 1 + Circles Lite (FAM-DESIGN1) both complete
**Estimated scope:** 1-2 weeks

Tasks:
1. Design XLSForm for Circle Observation
2. Push Circle and CircleMember Entity lists in sync command
3. Handle circle observation submissions: create ProgressNote with circle FK
4. Handle new relationship submissions: create CircleMembership records
5. Add Circle Observation to program profile options
6. Update tests and documentation

---

## GK Review Items

- [ ] Approve four-tier PII model and the "managed is better than banned" privacy position
- [ ] Review device loss protocol per tier
- [ ] Confirm that quick-type notes (no metrics) are sufficient for field collection
- [ ] Review whether a "Custom" PII tier allowing additional fields should be considered after initial deployment
