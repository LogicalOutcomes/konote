# Design Rationale Record: Offline Field Collection via ODK Central

**Feature:** Offline mobile data collection for field staff using ODK Central
**Status:** Design approved. Implementation waiting on Circles Lite (FAM-DESIGN1) completion.
**Date:** 2026-02-24
**Task ID:** FIELD-ODK1
**Design document:** `docs/plans/2026-02-24-offline-field-collection-design.md`

---

## Keyword Index

ODK Central, KoboToolbox, offline data collection, mobile forms, field staff, rural,
ODK Collect, Enketo, Entity lists, PII tiers, field_data_tier, field_collection_profile,
session attendance, visit note, circle observation, sync command, sync_odk,
four-tier PII, Restricted, Standard, Field, Field+Contact, device loss protocol,
per-program configuration, program profiles, App User mapping, XLSForm,
Android primary, iOS fallback, PHIPA device PII, managed vs banned PII,
scope control, scheduled visits, caseload scoping

---

## How to Use This Document

This record captures decisions from **three expert panels (16 expert perspectives)** evaluating offline field data collection architecture. It prevents future developers from re-introducing designs that were evaluated and rejected.

**Rules for future sessions:**
1. Read this document before modifying any model in `apps/field_collection/` or any ODK integration code
2. If a proposed change contradicts a decision below, do not proceed without explicit stakeholder approval
3. The PII tier model was specifically designed to address the "managed vs banned" privacy insight — do not regress to a binary "PII on device or not" framing
4. iOS limitations are architectural, not bugs — do not invest significant effort trying to make iOS offline work as well as Android

---

## Technology Choice: ODK Central (Not KoboToolbox, Not PWA)

### Why ODK Central was chosen

Three approaches were evaluated:

1. **KoboToolbox** — Hosted ODK platform with nicer form builder
2. **ODK Central (self-hosted)** — Open-source ODK server
3. **Progressive Web App (PWA)** — Custom offline forms built into KoNote

**ODK Central was chosen because:**
- **Entities feature** solves participant list synchronization. KoNote pushes participants as Entities via API; they appear automatically in ODK Collect forms. KoboToolbox lacks Entities — requires manual CSV uploads.
- **Self-hosted in Canada** satisfies PIPEDA/PHIPA. Data never leaves Canadian jurisdiction.
- **Lighter infrastructure** than KoboToolbox self-hosted (~2 GB RAM vs 4+ GB; no MongoDB dependency).
- **Rich API** (REST + OData) enables automated two-way sync. No REST API needed on the KoNote side.
- **Proven at scale** by WHO, UNICEF, and hundreds of humanitarian organizations for exactly this use case.

### Why KoboToolbox was rejected

- No Entities feature — participant list sync requires manual CSV uploads, creating a maintenance burden
- Self-hosted stack is heavier (MongoDB + PostgreSQL + Redis + Enketo = 4+ GB RAM)
- Cloud-hosted option puts PII on US/EU servers (PIPEDA risk)
- Form builder advantage is real but not worth the infrastructure and sync trade-offs

### Why PWA was rejected

- **4-8 weeks development effort** for service worker, IndexedDB queue, sync logic, conflict resolution, and new API endpoints
- **iOS 7-day storage eviction** — Safari silently deletes stored data if the PWA isn't opened for 7+ days. Real data loss risk for field workers.
- **No Background Sync on iOS** — sync only happens when user actively opens the app
- **Contradicts KoNote's tech philosophy** — "No React, no Vue, no webpack, no npm"
- All the infrastructure problems (offline sync, conflict resolution, device storage) are already solved by ODK

---

## Anti-Patterns: DO NOT Do These Things

### DO NOT put program names or service types on field devices

**What it looks like:** A form titled "DV Shelter Home Visit" or an Entity list called "Transitional Housing Clients."

**Why it was rejected:** A device screen is visible to anyone nearby — participants, family members, bystanders. Revealing that someone is a "DV Shelter Participant" or a "Mental Health Program Client" is a privacy breach of the service relationship itself, which is often more sensitive than the participant's name.

**Instead:** All form titles are generic ("Visit Note", "Session Attendance"). Entity lists are named "Participants" and "Groups." Program type is never on the device.

*Source: Outreach Worker, PII Tiers Panel. "Kids grab tablets. Community members look over my shoulder. Whatever is on that screen, assume the whole room sees it."*

---

### DO NOT allow per-field PII configuration

**What it looks like:** Admin toggles for each field independently: ☑ First name ☑ Last name ☐ DOB ☑ Phone ☐ Email.

**Why it was rejected:** Per-field toggles create 2^N possible configurations. With 8 toggleable fields, that's 256 combinations — impossible to test, document, or support. Bugs hide in rare combinations. The tiered preset approach gives agencies clear, tested options without combinatorial complexity.

**Instead:** Four fixed tiers (Restricted / Standard / Field / Field+Contact), each a known, tested schema. Agencies pick a tier per program, not individual fields.

*Source: Systems Architect, PII Tiers Panel. Confirmed by Change Management Specialist.*

---

### DO NOT build a full REST API on KoNote for ODK integration

**What it looks like:** Creating DRF serializers and API endpoints so ODK Central or field devices can query KoNote directly.

**Why it's unnecessary:** The sync is server-to-server, initiated by KoNote's management command. KoNote calls ODK Central's API — Central never calls KoNote. No external system needs to reach KoNote's data layer.

**Instead:** A management command (`sync_odk`) that runs periodically, pushes Entities to Central, and pulls submissions from Central. All logic is in KoNote's Django code, using Central's existing API.

---

### DO NOT try to make structured template-based notes work in ODK

**What it looks like:** Replicating KoNote's "full note" template system (sections, per-target entries, metric values) in XLSForm.

**Why it was rejected:** Full notes require seeing the participant's current plan, active targets, metric scales, and descriptor options — too much context for a mobile form. The complexity would make field forms unusable. Workers record free-text observations in the field; structured note completion happens in the office.

**Instead:** Field forms create "quick" type ProgressNotes with free-text observations. Workers can later enrich these in KoNote with metric values and target-specific entries.

---

### DO NOT require admins to log into ODK Central

**What it looks like:** Telling the agency admin "now go to central.yourdomain.com and configure your forms."

**Why it was rejected:** ODK Central is infrastructure, not a user-facing tool. Admins should configure field collection from KoNote's familiar admin interface. The sync command handles all ODK Central setup automatically.

**Instead:** All configuration is in KoNote admin (program settings page). The sync command creates/updates ODK Projects, deploys forms, manages App Users, and pushes Entity lists based on KoNote settings.

*Source: Change Management Specialist, Modular Forms Panel.*

---

## Decided Trade-offs

### Four PII tiers vs. single minimal data set
- **Chosen:** Four tiers (Restricted / Standard / Field / Field+Contact)
- **Trade-off:** More configuration complexity; more documentation needed per tier
- **Reason:** Different programs have genuinely different risk profiles. A DV shelter and a youth recreation program can't use the same PII level. One size forces either too much risk or too little usability.
- **Key insight:** "The risk comparison isn't 'phone numbers on device vs. no phone numbers.' It's 'phone numbers in a managed system vs. phone numbers in WhatsApp and personal contacts.'" The managed approach is demonstrably more private than banning PII that ends up on devices anyway.
- **Domains:** Privacy, Operations, UX

### Scope control (which participants) alongside field control (which fields)
- **Chosen:** Field+Contact tier pushes only scheduled visits or assigned caseload, not full roster
- **Trade-off:** Requires scheduling/assignment data to be maintained in KoNote
- **Reason:** Fewer records on the device is more effective for privacy than fewer fields per record. A worker doing 3-day trips needs 12 participants, not 85.
- **Domains:** Privacy, Data Model

### Android primary, iOS fallback
- **Chosen:** Design for ODK Collect on Android; Enketo web forms as iOS fallback
- **Trade-off:** iOS users get a degraded experience (Enketo in Safari, storage eviction risk)
- **Reason:** No native ODK app exists for iOS. All offline approaches (ODK, Kobo, PWA) have iOS limitations. Investing in iOS parity has diminishing returns vs. providing Android devices.
- **Domains:** UX, Operations, Budget

### Program profiles for configuration vs. raw form toggles
- **Chosen:** Four profiles (Group / Home Visiting / Circle / Full Field) with underlying form toggles
- **Trade-off:** Profiles may not cover every edge case; advanced users can override
- **Reason:** Profiles get 80% of agencies to the right configuration in one click. Prevents analysis paralysis for non-technical admins.
- **Domains:** UX, Onboarding

### Quick notes only in field (no metrics, no template sections)
- **Chosen:** Field forms create quick-type ProgressNotes only
- **Trade-off:** Field observations lack structured metric data; workers must add metrics later in the office
- **Reason:** Metric recording requires plan context (targets, scales, descriptors) that's too complex for mobile forms. Free-text captures observations; structured data entry happens where the full context is available.
- **Domains:** UX, Data Quality

---

## Risk Registry

### Device Loss Exposing PII (MEDIUM — mitigated by tiers)
**What:** A field device is lost or stolen with participant data cached.
**Consequence:** PII exposure scaled to the tier level — from "meaningless IDs" (Restricted) to "names + phone numbers for 12 scheduled participants" (Field+Contact).
**Mitigation:** Four-tier system limits exposure. Device PIN required for Field+. ID regeneration capability invalidates lost device data. Android full-disk encryption protects locked devices. ODK form-level encryption available.
**Monitor:** Agency reports of device loss incidents. Track tier-to-loss correlation.

### iOS Storage Eviction (MEDIUM — documented limitation)
**What:** iOS Safari silently deletes cached Enketo forms and unsent submissions if the PWA isn't opened for 7+ days.
**Consequence:** Data loss for iOS users who collect data but don't sync within a week.
**Mitigation:** Documented limitation. Android is primary platform. Agencies advised to provide Android devices for dedicated field work. iOS users trained to sync within 5 days.
**Monitor:** Sync error rates by platform. User reports of missing submissions.

### Sync Conflicts (LOW — by design)
**What:** Two workers record attendance for the same group session, or office staff creates a record that conflicts with a field submission.
**Consequence:** Duplicate records in KoNote.
**Mitigation:** Sync command checks for existing records before creating (dedup by group + date for attendance, no dedup needed for notes since they're always new). Conflicts flagged for manual review rather than auto-resolved.
**Monitor:** Duplicate detection rate in sync logs.

### ODK Central Maintenance Burden (LOW-MEDIUM)
**What:** ODK Central requires periodic updates, security patches, and monitoring.
**Consequence:** Additional infrastructure to maintain alongside KoNote.
**Mitigation:** Central is Docker Compose-based — updates are `git pull + docker compose up`. Can be included in existing maintenance schedule. Health check endpoint for monitoring.
**Monitor:** Central version currency. Container health checks.

### Adoption Risk — Field Staff Resistance (MEDIUM)
**What:** Field staff find ODK Collect cumbersome or prefer their existing (informal) data collection methods.
**Consequence:** Low adoption; data quality doesn't improve despite infrastructure investment.
**Mitigation:** Forms designed to be simpler than paper equivalents. Only relevant forms shown per program. Attendance form is faster than manual check-off. Visit note is a single text box plus two dropdowns.
**Monitor:** Submission rates per worker. Compare to expected visit/session frequency.

---

## Graduated Complexity Path

### Level 1: Foundation (build when Circles Lite is ready)
- ODK Central deployment alongside KoNote
- Sync command (`sync_odk`) — push Entities, pull submissions
- Two forms: Session Attendance, Visit Note
- Admin configuration in KoNote (per-program toggle, tier, profile)
- App User mapping from KoNote UserProgramRoles
- Four PII tiers implemented
- Device loss protocol documented

### Level 2: Circles Integration (build immediately after Level 1)
- Circle Observation form
- Circle Entity list sync (circle name + member names per tier)
- Relationship recording in field (free-text label, per Circles DRR)
- ProgressNote circle FK populated from field submissions

### Level 3: Advanced Features (build when triggered)
**Trigger:** Agencies request, usage data supports
- **Scheduled visit sync** — KoNote pushes worker schedules to ODK, scoping Field+Contact Entity lists to upcoming visits
- **Photo/media attachments** — Field workers capture photos (home conditions, group activities) that sync to KoNote
- **Custom field forms** — Dynamic forms that include agency-specific custom fields from KoNote's EAV system
- **Two-way notes** — Office staff add instructions that appear on the worker's device for the next visit
- **Offline metric recording** — Simplified metric entry for achievement-type metrics (yes/no, milestone reached)

### Level 4: Multi-Agency (build after multi-tenancy)
**Trigger:** Multi-tenancy deployed per multi-tenancy DRR
- Per-tenant ODK Central instances (or projects)
- Consortium-level field data aggregation
- Shared form templates across agencies

---

## Expert Panel Sources

### Panel 1: Technology Selection (2026-02-24)
Evaluated KoboToolbox vs ODK Central vs PWA for offline field data collection. Research covered API capabilities, offline reliability, iOS limitations, privacy implications, and integration effort.

### Panel 2: PII Tiers for Field Devices (2026-02-24)
Four experts, two rounds. Focused on what participant data should be available on field devices.
- **Privacy & Compliance Specialist** — Argued for fixed minimal data; revised to support four tiers after "managed vs banned" insight; proposed device loss protocol and ID regeneration
- **Nonprofit Program Manager** — Demonstrated that different programs need different data levels (DV vs community rec vs home visiting); recommended per-program tiers
- **Systems Architect** — Argued against per-field toggles (combinatorial explosion); proposed tiered presets as tested, documented configurations; designed per-program implementation
- **Frontline Outreach Worker** — Provided field reality: workers already have PII on devices informally; program type is more sensitive than names; last initial sufficient for disambiguation

### Panel 3: Modular Form Configuration (2026-02-24)
Four experts, two rounds. Focused on how admins configure which forms are available per program.
- **Nonprofit Program Manager** — Mapped 5 real programs with different field needs; advocated per-program configuration not per-agency
- **ODK Form Designer** — Proposed one ODK Central Project per KoNote Program; Entity lists scoped by program; forms deployed per configuration
- **KoNote Systems Architect** — Designed configuration model: master toggle + profile + tier on Program settings; sync command handles all ODK Central setup automatically
- **Change Management Specialist** — Proposed program profiles (Group / Home Visiting / Circle / Full Field) to prevent admin analysis paralysis; recommended Circles form auto-hidden when feature toggle is off

---

## Appendix: The "Managed vs Banned" Insight

The PII Tiers Panel produced a key insight that shaped the entire tier design:

**The realistic alternative to phone numbers in a managed system isn't "no phone numbers on devices" — it's phone numbers in WhatsApp, personal contacts, screenshots, and paper.**

Every agency the Operations Director surveyed that bans PII on devices has staff who violate the policy daily. The ban creates liability without reducing risk. Staff need phone numbers to confirm appointments. If the system doesn't provide them, staff find workarounds that are:
- Unencrypted (personal contacts)
- Persistent (never deleted)
- Unaudited (no trail of who accessed what)
- Unmanaged (no remote wipe capability)

The Field+Contact tier provides phone numbers in a managed container with:
- Time-limited access (refreshed per trip/sync cycle)
- Scope-limited records (scheduled visits only, not full roster)
- Audit trail (sync logs record which data was pushed to which device)
- Device-level encryption (Android full-disk + ODK app-private storage)

This is demonstrably more private than the status quo at most agencies.
