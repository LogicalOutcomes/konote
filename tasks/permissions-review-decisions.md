# Permissions Review Decisions (2026-02-09)

Two rounds of expert panel review of the KoNote2 RBAC permission structure. Goal: conservative defaults that protect client confidentiality while being practical for most Canadian nonprofits.

---

## Roles

| Role | Who | Scope |
|------|-----|-------|
| **Front Desk** | Reception staff | Operational only — names, contact, safety info |
| **Direct Service** | Counsellors, case workers, facilitators | Full clinical access, scoped to their program |
| **Program Manager** | Program leads, supervisors | Administrative + oversight across their program(s) |
| **Executive** | Directors, board members, funders | Org-wide aggregate data only — no individual records |
| **Administrator** | System admins | System config only — NO client data unless also assigned a program role |

---

## 5 Changes to Make Now

All confirmed by 8 experts across two panel rounds.

### 1. Staff: group.manage_members — DENY → SCOPED

**Why:** Facilitators manage their own group rosters in practice. Requiring manager approval for every roster change creates a bottleneck that drives workarounds (paper lists, giving staff higher roles). Especially critical for drop-in and harm reduction programs where membership is fluid.

**Safeguard:** All roster changes must create an audit entry (who added/removed whom, when, which group). Group roster is health information under PHIPA because group type can indicate diagnosis.

### 2. Staff: alert.cancel — SCOPED → DENY

**Why:** Two-person rule for safety. If a worker creates an alert ("client expressed suicidal ideation") and can also cancel it, there's a single point of failure. A worker might cancel after one good session, then the client is in crisis and nobody knows there was a prior flag.

**Implementation detail:** Staff should be able to post a "recommend cancellation" update with their assessment. The program manager reviews and cancels. System should notify the manager when a cancellation recommendation is posted. Without this notification workflow, alerts will pile up and staff will stop creating them (alert fatigue).

### 3. PM: consent.manage — ALLOW → SCOPED

**Why:** First panel said DENY, second panel overrode to SCOPED. In smaller programs, the manager often does intake and must record consent. DENY would generate support tickets immediately.

**Safeguard:** Consent records must capture two things: (a) who obtained consent, and (b) who recorded it in the system. These may be different people. The record is immutable — can't be edited after creation, only withdrawn and re-recorded.

### 4. Add client.create (missing from matrix)

| Role | Level | Rationale |
|------|-------|-----------|
| Front Desk | ALLOW | Creates records at walk-in and check-in |
| Direct Service | SCOPED | Creates records for new clients in their program (especially outreach/drop-in where there is no front desk) |
| Program Manager | SCOPED | Does intake in smaller programs |
| Executive | DENY | Never creates client records |

**Note:** `client.create` should eventually trigger a consent workflow prompt (record consent or document the exception). Not a permission matrix item but should be noted.

### 5. PM: alert.create — DENY → ALLOW

**Why:** Supervisors reviewing case files should be able to flag safety concerns directly. No barriers to creating safety alerts — any role that can identify a risk should be able to flag it. Unanimous across both panels.

---

## 1 Recommendation Overturned

### PM: note.view — first panel said change ALLOW → SCOPED; second panel said keep ALLOW

**Why it was overturned:** In Phase 1, SCOPED behaves identically to ALLOW (both are program-wide). Program isolation already prevents managers from seeing notes outside their program. Changing the label creates documentation debt with no actual security improvement. Revisit when Phase 2 introduces assignment-level scoping.

---

## Changes for Phase 2 (prioritized)

| Priority | Change | Reasoning |
|----------|--------|-----------|
| 1st | Add `group.view_schedule` (separate from `group.view_roster`) | Front desk needs to know when groups meet without seeing who's in them. Low-risk, high-value. |
| 2nd | Front Desk: `client.edit` → PER_FIELD | Small agencies need front desk to enter demographics. Needs admin UI for configuring which fields front desk can edit. |
| 3rd | Rename SCOPED to PROGRAM + split `note.edit_own` / `note.edit_any` | Do when building Phase 2 assignment-level scoping. SCOPED currently says "assigned clients" but behaves as "whole program" — the label should match the behaviour for audit honesty. `note.edit` has a comment saying "own notes only" but that's enforced in view code, not the permission level. |
| 4th | PM: `client.view_clinical` → GATED | GATED requires a new UI for documenting reasons and review trails. Don't rush it. |

---

## New Items Identified

| Item | Description | When |
|------|-------------|------|
| Alert update workflow | Staff can't cancel alerts, but can post "recommend cancellation" with assessment. Manager reviews and approves. System notifies manager. | Build alongside change #2 above |
| Discharge access | After a client exits a program, access transitions to read-only, then restricted. Triggered by enrollment status, not permissions. #1 finding in PHIPA compliance audits. | Phase 2 |
| Attendance aggregate for Front Desk | Future `attendance.view_aggregate` (count only, no names) separate from `attendance.view_report` (individual records). Many agencies have front desk compile daily attendance numbers for funders. | Phase 3+ |
| Documentation: not all roles required | Agencies without a front desk (drop-in, outreach) should use Direct Service for all frontline workers. The 4 roles are archetypes — not every agency uses all of them. | Now (in docs) |
| Supervision notes | Clinical supervisors need to add supervision notes to client files — distinct from clinical notes. Consider a note type that PMs can create. | Phase 3+ |

---

## Permissions Confirmed as Correct (do not change)

Reviewed by both panels and confirmed:

- **Front Desk: group.view_roster = DENY** — group type reveals diagnosis
- **Staff: group.edit = DENY** — group configuration is a management decision
- **Staff: report.program_report = DENY** — reports are a management function
- **PM: client.edit = DENY** — managers review, workers edit, maintains accountability
- **PM: group.log_session = DENY** — only facilitators record sessions
- **PM: note.create/edit = DENY** — managers don't write clinical notes
- **PM: note.view = ALLOW** — supervision requires reading notes; program isolation already limits scope
- **Executive: all client data = DENY** — aggregate only
- **Admin: no client access without program role** — best practice
- **ClientAccessBlock overrides everything** — essential for DV and conflict of interest
- **Program isolation for all roles** — maps to PHIPA circle of care
- **No delete permissions for any program role** — cancel/archive, never delete

---

## Current Full Permission Matrix (before changes)

For reference, the single source of truth is `apps/auth_app/permissions.py`. The matrix uses 5 permission levels:

- **ALLOW** — always permitted within program scope
- **DENY** — never permitted
- **SCOPED** — limited to assigned clients/groups within program (Phase 1: behaves as program-wide)
- **GATED** — allowed with documented reason (not yet implemented)
- **PER_FIELD** — depends on each field's individual access setting
