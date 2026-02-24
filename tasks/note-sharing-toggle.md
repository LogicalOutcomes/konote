# QA-R7-PRIVACY2 — Note Sharing Toggle (Consent Withdrawal)

**Task ID:** QA-R7-PRIVACY2
**Date:** 2026-02-24
**Status:** Design approved by GK (expert panel, 2 rounds)
**Parking Lot item:** TODO.md line 140

---

## What

Add a binary On/Off toggle to the client profile that controls whether this participant's notes are shared across programs. This is the "consent withdrawal" mechanism — but the UI never uses that term.

## Key Insight: The Infrastructure Already Exists

The data model (`ClientFile.cross_program_sharing` with three states: `default`, `consent`, `restrict`) and the enforcement layer (`apply_consent_filter()` in `apps/programs/access.py`) are already built and tested. Changing the field to `restrict` immediately hides cross-program notes in all consent-enforced views.

**This task is a UI change only.** No new models, no migrations, no changes to the consent filter logic.

## Design Decisions (GK-approved)

### Binary Toggle UI

The three-state data model stays as-is (it's correct for the data layer). But the UI shows a **computed binary**:

- **ON** = effective sharing is enabled (field is `consent`, or field is `default` and agency setting is ON)
- **OFF** = effective sharing is disabled (field is `restrict`, or field is `default` and agency setting is OFF)

The toggle changes the field between `consent` and `restrict`. The `default` state is resolved at display time — the worker sees the result, not the configuration.

### When Agency Sharing Is Off

If the agency-level feature toggle `cross_program_note_sharing` is OFF, the per-client toggle is **hidden entirely**. There's nothing to toggle — sharing is off for everyone regardless.

### Language

- Label: **"Share notes across programs"**
- ON state: "Notes about [Name] are visible to staff in all their programs."
- OFF state: "Notes about [Name] are only visible to the program that created them."
- No mention of PIPEDA, consent, withdrawal, or legal terminology.

### Confirmation

A single confirmation step when turning sharing OFF:

> "Stop sharing [Name]'s notes across programs? Notes will only be visible to the program that created them."
>
> [Yes, stop sharing] [Cancel]

No wizard. No multi-step process. One click + one confirmation.

### Effect

- **Immediate.** When the toggle is set to OFF, `apply_consent_filter()` hides cross-program notes on the next page load. No grace period.
- **Retroactive at filter level.** Notes aren't deleted — they're filtered out of consent-enforced views. Staff who already read them retain that knowledge (documented as "information laundering" in the PHIPA DRR — not solvable in software).
- **Reversible.** The toggle can be turned back ON. Consent can be re-granted.
- **Independent of erasure.** Withdrawal controls visibility; erasure controls existence. Different intent, different process.

### Permissions

- **PM or Admin only.** Frontline workers cannot change this setting. A new hire shouldn't be able to flip a privacy control without understanding the consequences.
- If a worker needs to change it, they escalate to their PM — which is the right workflow for a privacy action.

### Notifications to Other Programs

**No, for v1.** Adding notifications for a rare event adds complexity. Build only if agencies ask for it.

### Audit Trail

Log the state change to the audit database: who changed it, when, old value, new value.

## Implementation

### Files

- `templates/clients/_tab_info.html` (or wherever the client profile info tab lives) — add the toggle, conditionally hidden when agency sharing is off
- `apps/clients/views.py` — add a small view or HTMX endpoint to handle the toggle POST
- `apps/clients/forms.py` — simple form for the toggle (CSRF, validation)
- No model changes. No migrations.
- `tests/test_cross_program_security.py` — add tests for toggle permission (PM yes, worker no), audit logging

### Effort

Small (2 hours). The heavy lifting (consent filtering, data model, enforcement) is already done. This is a template + one view endpoint.

## Expert Panel Context

Round 2 panel focused on the usability gap between the three-state model and how workers think:

- **Human Factors Specialist:** "The current three-state model is a usability problem. 'Default' means 'follow agency setting' — but the worker doesn't know what the agency setting is. Render it as binary: ON/OFF. The worker sees the result, not the configuration."
- **Nonprofit Consultant:** "My staff don't understand the current consent model. When a participant says 'I don't want Program B reading my notes,' the worker comes to me. The toggle should be something I can find and flip in 10 seconds."
- **Regulatory Pragmatist:** "Don't call it 'consent withdrawal.' Call it 'Change note sharing.' The worker sees: sharing is on, or sharing is off. That's it."

## Related Files

- `tasks/design-rationale/phipa-consent-enforcement.md` — enforcement matrix, anti-patterns, deferred work
- `apps/programs/access.py` — `apply_consent_filter()`, `check_note_consent_or_403()`
- `apps/clients/models.py` — `ClientFile.cross_program_sharing` field (line ~181)
- `tests/test_cross_program_security.py` — existing consent filter tests
