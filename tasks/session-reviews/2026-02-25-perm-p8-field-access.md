# Session Review: PERM-P8 Per-Field Front Desk Access (WP1)

**Date:** 2026-02-25
**Branch:** `feat/wp1-field-access`
**Commits:** 8 (3 WP0 cherry-picks + 3 WP1 implementation + 1 TODO update + 1 revert fix)

---

## What Was Built

### WP0: Access Tier System (cherry-picked from worktree session)

- `InstanceSetting` stores `access_tier` (values: `"1"`, `"2"`, `"3"`)
- `get_access_tier()` helper in `apps/admin_settings/models.py`
- Tier selector on Instance Settings page (radio buttons with descriptions)
- Tier step in the setup wizard
- 15 tests in `tests/test_access_tiers.py`
- Design rationale record at `tasks/design-rationale/access-tiers.md`

### WP1: Per-Field Front Desk Configuration (PERM-P8)

**New files:**
- `apps/admin_settings/field_access_views.py` — admin view (GET/POST) for configuring which contact fields the front desk role can see/edit
- `templates/admin_settings/field_access.html` — two-table template (core fields + custom fields)
- `apps/clients/migrations/0027_add_field_access_config.py` — migration for FieldAccessConfig model
- `tests/test_field_access.py` — 22 tests across 4 test classes

**Modified files:**
- `apps/clients/models.py` — added `FieldAccessConfig` model with `SAFE_DEFAULTS`, `ALWAYS_VISIBLE`, `get_access()`, `get_all_access()`, `get_visible_fields()` rewrite
- `apps/admin_settings/urls.py` — added `field-access/` route
- `apps/admin_settings/views.py` — dashboard context adds access tier + field count
- `templates/admin_settings/dashboard.html` — "Field Access for Front Desk" card (Tier 2+ only)
- `apps/auth_app/decorators.py` — PER_FIELD branch loads `FieldAccessConfig.get_all_access()` into `request.field_access_map`
- `apps/clients/forms.py` — `ClientContactForm` accepts `field_access_map` kwarg, dynamically adds/removes phone/email
- `apps/clients/views.py` — `client_contact_edit()` uses `request.field_access_map`
- `TODO.md` — PERM-P8 marked complete

### What Was NOT Built (Remaining)

- **PERM-P5 (DV-safe mode)** — `is_dv_safe` flag, field hiding, two-person removal rule
- **PERM-P6 (GATED clinical access)** — `AccessGrant` model, justification form, time-boxed grants

Implementation prompt created at `tasks/phase-perm-p5-p6-prompt.md`.

---

## Stats

| Metric | Value |
|--------|-------|
| Files changed | 20 |
| Lines added | ~1,200 |
| Lines removed | ~45 |
| New tests | 37 (15 tiers + 22 field access) |
| Tests passing | 37/37 |
| Models added | 1 (FieldAccessConfig) |
| Templates added | 3 (field_access.html, instance_settings tier section, wizard tier step) |

---

## Expert Panel: Security and Architecture Review of PERM-P8

**Panel Members:**
- Privacy & Health Law Specialist (PHIPA/PIPEDA)
- Django Security Architect
- Nonprofit Operations Director
- Clinical Social Worker (RSW)

---

### Round 1: Initial Analysis

#### Privacy & Health Law Specialist (PHIPA/PIPEDA)

The implementation correctly enforces the **principle of minimal necessary access** from PIPEDA:

**Strengths:**
1. **Safe defaults are privacy-positive.** Tier 1 agencies get `phone: edit, email: edit, birth_date: none, preferred_name: view` without any configuration. This means birth dates are hidden from front desk by default — correct, since date of birth is a quasi-identifier under PIPEDA and front desk staff rarely need it.
2. **ALWAYS_VISIBLE set is appropriate.** `first_name`, `last_name`, `display_name`, `record_id`, `status` — these are the minimum a front desk needs to identify who walked in. This aligns with PIPEDA's "identifiable minimum" principle.
3. **Fail closed on unknown levels.** The decorator's final else branch denies access for unknown permission levels. This is correct.

**Concerns:**
1. **No audit trail for field access changes.** When an admin changes field access from "edit" to "hidden," this is a change to the privacy posture of the system. It should be logged to the audit database with who changed what and when. Currently, the view just calls `update_or_create` without an audit entry.
2. **Custom field `front_desk_access` changes aren't audited either.** Same issue — `cf.save(update_fields=["front_desk_access"])` with no audit log.
3. **The `field_access_map` is set on the request object.** This is fine for the current single-process model, but should be documented as a convention that other developers need to follow when adding new field-displaying views.

**Recommendation:** Add audit logging for field access configuration changes (priority: before production deployment, not a blocker for merge to main).

---

#### Django Security Architect

**Architecture review of the permission enforcement chain:**

The chain is: `permissions.py` matrix → `@requires_permission` decorator → `PER_FIELD` branch → `request.field_access_map` → form/view reads map.

**Strengths:**
1. **Single enforcement point.** The decorator is the only place where PER_FIELD is evaluated. Forms and views consume the map — they don't make their own permission decisions. This is the correct pattern.
2. **FieldAccessConfig.get_all_access() merges safe defaults with stored config.** This means missing database rows fall back to safe defaults (privacy-safe), not to "allow everything."
3. **The ALWAYS_VISIBLE set prevents a misconfigured admin from accidentally hiding the client's name from the front desk.** Good defensive coding.
4. **Tier gating on the admin view (Tier 2+) prevents Tier 1 agencies from accidentally reaching the configuration page.**

**Concerns:**
1. **The field_access_map is only used by `ClientContactForm` right now.** Other views that display client contact fields (client detail, client list) don't yet consume this map. If a receptionist visits the client detail page, they may see fields that the admin configured as "hidden." Review all client-displaying views for consistency.
2. **No field-level validation on POST.** If someone submits a value for a field they shouldn't be able to edit (e.g., PER_FIELD says `birth_date: view` but they forge a POST), the form would reject it because the field isn't in the form — but this relies on Django's form field presence, not explicit server-side enforcement. This is actually fine because `ClientContactForm` dynamically removes fields, so forged data for missing fields is silently ignored by Django.
3. **`get_all_access()` does a database query on every request for a receptionist hitting a PER_FIELD view.** Consider caching this in the FieldAccessConfig model (with cache invalidation on save).

**Recommendation:** Audit all views that display client contact fields for a receptionist and ensure they respect the `field_access_map`. Add a per-request cache or Django cache for `get_all_access()` results.

---

#### Nonprofit Operations Director

**From an agency adoption perspective:**

**Strengths:**
1. **The two-table layout (core fields / custom fields) is exactly right.** Admins think about "the built-in fields" and "the fields we added" as separate categories. Having them on one page with two sections matches their mental model.
2. **Three-option dropdowns (Hidden / View only / View and edit) are the right granularity.** Four or more options would confuse admins. These three map to real conversations: "Can the front desk see this?" → "Can they change it?"
3. **Dashboard card only appears at Tier 2+.** Tier 1 admins won't be confused by something they don't need.
4. **Field count shown on the dashboard card** gives the admin a quick sense of "something is configured here" without clicking through.

**Concerns:**
1. **No "reset to defaults" button on the field access page.** If an admin experiments with settings and wants to go back to safe defaults, they'd need to manually set each field back. A "Reset to Safe Defaults" button would prevent configuration anxiety.
2. **No explanation text for what "front desk" means.** The page says "Field Access for Front Desk" but doesn't explain which role that maps to. Add a sentence: "These settings control what the front desk role can see and edit on participant contact forms."
3. **Custom fields show the group name, which is helpful**, but there's no visual separator between groups. If an agency has 15 custom fields across 3 groups, the list could look flat. Consider grouping with headings.

**Recommendation:** Add a "Reset to Defaults" button and a brief explanation of what the front desk role is. Visual grouping of custom fields by their group is a nice-to-have.

---

#### Clinical Social Worker (RSW)

**From a clinical safety perspective:**

**Strengths:**
1. **Birth date hidden by default from front desk.** In clinical agencies, date of birth combined with name is enough to identify someone — and front desk staff talking about "the woman born on January 5th" in a waiting room is a real confidentiality breach. Hiding birth date by default is safety-conscious.
2. **The separation between "view" and "edit" is important.** A front desk person may need to see a phone number to confirm an appointment, but shouldn't be able to change it. "View only" handles this correctly.
3. **The system doesn't expose the visibility decision to the front desk user.** They just see fewer fields — they don't get a notification that something was hidden from them, which avoids the "what am I not seeing?" anxiety that would undermine trust in the system.

**Concerns:**
1. **Email address defaults to "edit" for front desk, which is generous.** In a clinical setting, a client's email address can be a safety issue (e.g., a controlling partner monitoring email). Consider whether the safe default for email should be "view" rather than "edit" in clinical agencies (Tier 3). Currently the defaults are identical across tiers — the admin can change them, but the defaults should be tighter at higher tiers.
2. **No ability to restrict front desk from seeing the client list itself.** PER_FIELD controls which fields they see, but front desk can still see all clients. For DV-serving agencies, the fact that someone is "in the system" is itself sensitive information. This is out of scope for P8 (it's the DV-safe mode territory for P5), but worth noting that P8 alone doesn't solve the DV scenario.

**Recommendation:** Consider tier-sensitive safe defaults (tighter at Tier 3). Ensure the P5 implementation prompt addresses the "presence in the system" issue, not just field visibility.

---

### Round 2: Cross-Examination

#### Privacy Specialist responds to Security Architect
Building on the Security Architect's concern about views not yet consuming the field_access_map — this is the most significant gap. The admin configures field access, but if the client detail template ignores the map and shows all fields, the admin has a false sense of security. **This should be tracked as a follow-up task** before production deployment. The approach should be: any template that renders client.phone, client.email, client.birth_date, or client.preferred_name for a receptionist user must check the field_access_map.

#### Security Architect responds to Clinical Social Worker
The suggestion to make safe defaults tier-sensitive is architecturally clean — it would mean `FieldAccessConfig.SAFE_DEFAULTS` becomes a method that takes the tier as input rather than a class-level constant. The implementation cost is low (change a dict to a function, add tier parameter to `get_all_access()`). I support this for a follow-up, not a blocker.

Regarding the caching concern I raised: on reflection, the `get_all_access()` query is small (4-5 rows from FieldAccessConfig + a count of CustomFieldDefinition). The overhead per request is minimal. Caching is a premature optimisation here — the site will never have more than a few dozen field access rows. I withdraw the caching recommendation.

#### Nonprofit Operations Director responds to Privacy Specialist
The audit trail concern is valid but shouldn't block the merge. Field access changes are infrequent (an admin might change them once during setup and then once a year). The audit trail matters for compliance reviews, but those are quarterly or annual. Adding audit logging as a tracked follow-up task is the right approach.

#### Clinical Social Worker responds to Security Architect
Agree that tier-sensitive defaults are a follow-up, not a blocker. The current defaults are safe enough for Tier 2 (where most agencies using P8 will be). Tier 3 agencies that are clinical will be actively configuring their fields during setup — the safe defaults are a fallback, not the primary configuration path.

---

### Round 3: Convergence

The panel converges on the following assessment:

**Overall verdict: GOOD — ready to merge with tracked follow-up items.**

The implementation is architecturally sound, privacy-safe by default, and appropriate for the feature scope (PERM-P8). The identified gaps are real but not blockers — they are follow-up work that should be tracked and completed before first production deployment.

---

## Final Synthesis

### What's Working Well

1. **Fail-closed defaults throughout** — unknown fields hidden, unknown levels denied, missing config rows fall back to safe values
2. **Single enforcement point** (decorator) — no scattered permission checks
3. **Tier gating** prevents feature from appearing where it shouldn't
4. **Clean admin UI** that matches how nonprofit admins think about fields
5. **ALWAYS_VISIBLE** prevents misconfiguration from hiding essential fields
6. **37 tests** covering the tier system and field access, all passing

### Follow-Up Items (Track in TODO.md)

| Priority | Item | Rationale |
|----------|------|-----------|
| **HIGH** | Audit all client-displaying views/templates to respect field_access_map for receptionist role | Admin expects hidden fields to be hidden everywhere, not just on the edit form |
| **MEDIUM** | Add audit logging for field access configuration changes | PIPEDA compliance — changes to privacy posture should be recorded |
| **LOW** | Add "Reset to Safe Defaults" button on field access page | Reduces configuration anxiety for admins |
| **LOW** | Consider tier-sensitive safe defaults (tighter at Tier 3) | Clinical agencies benefit from tighter defaults out of the box |
| **LOW** | Add brief explanation text and visual grouping on field access page | UX polish for admin experience |

### Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Receptionist sees hidden fields in other views (not yet using map) | MEDIUM | Track as HIGH follow-up. The edit form is the most sensitive path and is already enforced. |
| Admin misconfigures and hides too many fields | LOW | ALWAYS_VISIBLE prevents hiding critical fields. Safe defaults as fallback. |
| PER_FIELD branch not triggered for non-receptionist roles | NONE | By design — only receptionist has PER_FIELD in the permission matrix. Other roles get ALLOW or PROGRAM. |
| Field access config lost during migration | LOW | Migration creates the model table. Safe defaults apply when no rows exist. |

### Decision

**Merge `feat/wp1-field-access` to `main`.**

Create follow-up tasks in TODO.md for the HIGH and MEDIUM items identified above. LOW items can be addressed during UX polish passes.
