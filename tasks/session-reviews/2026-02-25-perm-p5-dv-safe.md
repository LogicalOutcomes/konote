# Session Review: PERM-P5 DV-Safe Mode

**Date:** 2026-02-25  
**Branch:** `feat/perm-p5-dv-safe`  
**Commits reviewed:** `cf5732f..98505c3` (5 commits on branch vs `main`)  
**Reviewer process:** /review-session (5-step: gather → review diffs → report → expert panel → update recommendations)

---

## Action List (Final — updated after expert panel)

### Fix now
1. ~~Remove dead code: `_get_user_role()` function and unused `InstanceSetting` import from `dv_views.py`.~~ — **Fixed** in commit [pending].

### Fix soon (next session)
2. **Self-approval check** in `dv_safe_review_remove` — add `if removal_request.requested_by == request.user` guard to enforce true two-person rule. Add clear error message and test.
3. **French translations** for ~15 new template strings (`{% trans %}` and `{% blocktrans %}` blocks).
4. **Save-side enforcement test** — verify receptionist POSTing DV-sensitive field values for a DV-safe client has those values silently ignored.

### Consider later
5. Idempotency + empty-reason validation tests.
6. PM notification when a DV removal request is created.
7. Inline styles → CSS classes for maintainability.

---

## Summary

This branch implements DV-safe mode (PERM-P5): a safety feature for domestic violence situations. When `is_dv_safe` is set on a participant, custom fields marked as DV-sensitive (address, emergency contact, employer, etc.) are hidden from front desk staff. Any staff member can enable the flag unilaterally (safety first), but removal requires a two-person workflow: staff submits a reason, a program manager approves or rejects. The front desk never sees the flag or any related UI. Feature is gated to Tier 2+ access. Fail-closed design: if the DV check errors, fields default to hidden.

**11 files changed, ~1,170 lines added. 28 tests, all passing.**

---

## Critical Issues
None found.

## Warnings

1. **Dead `_get_user_role()` function** in `dv_views.py` (lines 26–31). Defined but never called. Duplicates logic in the auth system.

2. **Unused `InstanceSetting` import** in `dv_views.py` (line 17). Only `get_access_tier` is used.

3. **Self-approval loophole.** `dv_safe_review_remove` checks role (`_is_pm_or_above`) but not identity. A user with both staff and PM roles could request and approve their own removal. Panel consensus: fix soon, include clear error message for small agencies.

4. **Missing French translations.** All template strings use `{% trans %}` / `{% blocktrans %}` correctly but no `.po` entries were added.

## Suggestions

1. Add save-side enforcement test for `client_save_custom_fields()`.
2. Add idempotency test (enable on already-enabled client) and empty-reason validation test.
3. Consider PM notification when removal requests are created.
4. Move inline styles to CSS classes in a future polish pass.

## What Looks Good

- **Fail-closed design** correctly implemented in both view-side and save-side enforcement.
- **Audit logging** on all three actions with correct AuditLog field names.
- **Front desk invisibility** enforced at template, view, and test levels.
- **Two-person-rule model** is clean: `approved=None/True/False` with `is_pending` property.
- **28 tests** across 8 classes covering models, field hiding, views, workflow, invisibility, tier gating, and admin form.
- **Seed migration** with reversible `unmark_dv_sensitive_fields`.
- **Safety-first unilateral enable** matches DV shelter intake best practices.

---

## Expert Panel

**Panel Members:**
- DV/Safety Practitioner
- Django Security Engineer
- Nonprofit Software UX Designer
- QA/Testing Specialist

### Key Panel Findings

1. **Self-approval rated higher than initial assessment.** DV Practitioner and Security Engineer both flagged this — in small nonprofits (5–15 staff), one person often holds both staff and PM roles. Panel consensus: upgrade from "consider later" to "fix soon."

2. **`is_pm_or_admin` false positive.** Initial report flagged it as missing from context. Panel verified it's already computed at `views.py` line 774 and passed in context. Removed from action list.

3. **UX is appropriate for high-stakes context.** Browser `confirm()` on enable is proportionate (safety-protective, not harmful). Approve/reject button styling is already differentiated. `<details>` accordion reduces clutter.

4. **Save-side test is the most important gap.** Protects against modified POST payloads bypassing view-side hiding.

5. **PM notification is a feature enhancement**, not a bug. PMs see pending requests on the participant's Info tab, but they have to visit the record to notice. Appropriate for parking lot.
