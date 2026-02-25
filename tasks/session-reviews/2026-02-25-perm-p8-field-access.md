# Session Review: Access Tiers + PERM-P8 Per-Field Front Desk Access

**Date:** 2026-02-25  
**Branch:** `feat/wp1-field-access`  
**Commits reviewed:** `7b3e238..2c165df` (11 commits on branch vs `main`)  
**Reviewer process:** /review-session (5-step: gather → review diffs → report → expert panel → update recommendations)

---

## Action List (Final — updated after expert panel)

### Fix now (before merging)
1. ~~Reset button text inaccurate at Tier 3~~ — **Fixed** in commit `2c165df`. Simplified to "restore the safe defaults for your access tier" instead of listing specific values.

### Fix soon (next session)
2. `client_contact_edit` view hardcodes phone/email field checks. Make it loop over `form.cleaned_data` keys instead of checking specific field names.

### Consider later
3. French translations for new template strings (`{% trans %}` and `{% blocktrans %}` blocks).
4. Add `last_changed_by` field to `FieldAccessConfig` model for admin UI display.
5. Add deployment documentation noting P8 controls field visibility, not client visibility (for DV-serving agencies, client list visibility is a separate concern addressed by P5).

---

## Summary

This branch implements two features:

1. **Access Tier System (WP0):** Three additive tiers (Open Access, Role-Based, Clinical Safeguards) stored in `InstanceSetting`, with admin UI on the Instance Settings page and the setup wizard. The tier controls which advanced permission features are active. The baseline role matrix (front desk can't see clinical notes, executives see aggregate only) is always enforced.

2. **Per-Field Front Desk Access (WP1 / PERM-P8):** A `FieldAccessConfig` model that controls which contact fields the front desk role can see or edit. Admin UI at Tier 2+ with grouped custom fields, audit logging, reset-to-defaults, and tier-sensitive safe defaults (Tier 3 tightens email to view-only). The `@requires_permission` decorator sets `request.field_access_map` for the PER_FIELD permission level, and `ClientContactForm` dynamically adds/removes fields based on the map.

**23 files changed, ~1,950 lines added. 44 tests (15 tier + 29 field access), all passing.**

---

## Critical Issues
None found.

## Warnings

1. **Duplicate birth_date logic in `get_visible_fields()`.** Lines 287-290 explicitly compute `visible['birth_date']` after the loop already handled it via `access_map`. The result is identical — not a bug, just slightly redundant code.

2. **Hardcoded phone/email in `client_contact_edit` view.** If a new core field becomes PER_FIELD-configurable, the view needs manual updates. Low risk since preferred_name is unlikely to become editable on the contact form.

3. **`_get_defaults()` imports `get_access_tier` inside the method body** (to avoid circular imports) and does a DB query. Called once per request for receptionists only. Negligible performance impact.

## Suggestions

1. Add `blocktrans` entries to `.po` file manually — `translate_strings` can't auto-extract these from templates.
2. Consider a `last_changed_by` field on `FieldAccessConfig` for admin UI display.

## What Looks Good

1. **Fail-closed throughout.** Unknown levels denied, missing configs fall back to safe defaults, ALWAYS_VISIBLE prevents misconfiguration.
2. **Single enforcement point.** Decorator is the only place PER_FIELD is evaluated.
3. **Tier-sensitive defaults.** Tier 3 gets tighter email default without manual config.
4. **Audit logging.** Config changes logged with old/new values. No-change saves create no log noise.
5. **44 tests** covering tiers, field access, audit logging, reset, tier-sensitive defaults.
6. **Template UX.** Grouped custom fields, explanation text, collapsible reset option.

---

## Expert Panel Discussion

**Panel Members:**
- Privacy & Health Law Specialist (PHIPA/PIPEDA)
- Django Security Architect
- Nonprofit Operations Director
- Clinical Social Worker (RSW)

### Round 1: Initial Analysis

**Privacy & Health Law Specialist:**

The implementation satisfies PIPEDA's minimal necessary access principle. Three specific observations:

1. Audit logging with old/new values addresses the primary compliance concern. An auditor asking "who changed what the front desk could see?" will find the answer.

2. Tier-sensitive defaults (email → view-only at Tier 3) are proportionate to PHIPA's requirements. In clinical settings, email addresses can reveal care relationships. Defaulting to view-only prevents accidental edits that might trigger notifications visible to a controlling partner.

3. The reset button deletes config rows so `_get_defaults()` returns tier-appropriate values — functionally correct. But the description text said "phone (edit), email (edit)" which is misleading at Tier 3. This was the only finding requiring a code change.

4. The permission enforcement chain (config → decorator → request annotation → form field presence → save) matches privacy-by-design principles. At no point does the receptionist's browser receive field data they shouldn't see.

**Django Security Architect:**

Good defensive architecture with no security issues:

1. The audit log change tracking compares old values to new values and only creates entries when something actually changed. The `test_saving_unchanged_creates_no_audit_log` test confirms this. No audit noise.

2. The reset handler uses `request.POST.get("action") == "reset_defaults"` as a discriminator before the regular save logic. Clean separation.

3. The duplicate birth_date logic in `get_visible_fields()` is harmless — the explicit lines exist because birth_date has special clinical-access semantics for non-receptionist roles. Not a refactoring priority.

4. The hardcoded phone/email in `client_contact_edit` is a code quality item, not a security concern. The form dynamically removes fields in `__init__`, so forged POST data for missing fields is silently ignored by Django. No injection risk.

5. The `_get_defaults()` method's per-request import resolution and DB query is fine — only triggered once per request for the receptionist path.

**Nonprofit Operations Director:**

The admin experience is well-designed:

1. The explanation text at the top ("These settings control what the **front desk role** can see and edit") answers the first question every admin will have: "who does this affect?"

2. Custom fields grouped by section heading matches how agencies think about their fields — "Demographics fields" vs. "Health fields" vs. "Education fields."

3. The reset option is behind a `<details>` tag with a confirmation dialog — appropriate friction to prevent accidental use.

4. The dashboard card says "X fields accessible" which gives instant context without clicking through.

5. Minor UX suggestion: after saving, a flash message showing the specific changes (e.g., "Phone changed from Edit to View only") would reduce admin anxiety, but this is polish.

**Clinical Social Worker (RSW):**

No safety concerns with the implementation:

1. Birth date hidden by default from front desk is correct. In small communities, date of birth + name is enough to identify someone. Discussions about "the person born on January 5th" in a shared waiting area are real confidentiality breaches.

2. The `ALWAYS_VISIBLE` set (first name, last name, display name, record ID, status) is the minimum a front desk needs to function. Removing any of these would make check-in impossible.

3. The feature does NOT address "presence in the system" (whether the front desk can see a client exists at all). This is clearly out of scope for P8 — it's P5/DV-safe mode territory, and the implementation prompt addresses it correctly.

4. The reset function makes things more restrictive (everything defaults to hidden/view), not less. No safety risk from accidental reset.

### Round 2: Cross-Examination

**Privacy Specialist → Security Architect:** The hardcoded phone/email in `client_contact_edit` is low risk now, but the right fix is to loop over `form.cleaned_data` keys. The form already dynamically generates fields from the map in `__init__`, so the view should dynamically consume them too. Rate this as "fix soon" rather than "consider later."

**Security Architect → Privacy Specialist:** Your observation about the reset button text was the most actionable finding. Simplifying to "safe defaults for your access tier" avoids the maintenance burden of keeping specific values in the template text. Good catch.

**Operations Director → Clinical Social Worker:** The "presence in the system" point should be in the deployment documentation. During the agency permissions interview, we should ask: "Are there clients whose very presence in your system is sensitive?" That's a signal for Tier 3 + DV-safe mode.

**Clinical Social Worker → Operations Director:** Agreed — this is a deployment/onboarding conversation, not a code issue. The agency permissions interview questionnaire should include this question.

### Round 3: Convergence

All four panelists converge:

- **No critical issues.** The reset button text was the only code change needed, and it's been fixed.
- **One "fix soon" item:** Make `client_contact_edit` loop over form fields instead of hardcoding.
- **Approved for merge to `main`.**

---

## Decision

**Merge `feat/wp1-field-access` to `main`.** No blockers remain. All identified issues are either fixed or tracked as follow-up items.
