# Access Tiers — Design Rationale Record

Task ID: PERM-TIER1 | Date: 2026-02-25 | Status: Draft — GK reviews PERM-P5 and PERM-P6 before implementation
Expert panel: Privacy & Health Law Specialist (PHIPA/PIPEDA), Nonprofit Operations Director, Security Architect, Clinical Social Worker (RSW), Nonprofit Technology Consultant, Program Evaluator, UX/Onboarding Specialist, Privacy & Risk Analyst (three rounds across two panels)

Keyword Index: access tier, permission complexity, Open Access, Role-Based, Clinical Safeguards, GATED, PER_FIELD, DV-safe, per-field front desk, proportional privacy, configuration interview, agency sensitivity, PERM-P5, PERM-P6, PERM-P8

---

## The Decision

KoNote's permission system needs to serve agencies that range from recreational sports programs (names, attendance, t-shirt sizes) to DV shelters (location is life-safety). The full permission system — GATED clinical access, DV-safe mode, per-field front desk configuration — is correct for clinical and DV-serving agencies but creates adoption barriers for the majority of Canadian nonprofits that handle lower-sensitivity data.

**Decision:** Introduce three additive access tiers that control which advanced permission features are active. The baseline role matrix (4 roles, front desk can't see clinical notes, executives see aggregate only) is **always enforced at every tier**. Tiers never weaken the baseline — they add layers of protection on top.

**Critical principle corrected during panel discussion:** The first panel incorrectly described Tier 1 as "everyone sees everything." This was challenged and overturned. Even a sports league has personal information (parent phone numbers, emergency contacts) that must be role-appropriate under PIPEDA. The role matrix is the floor, not a feature.

---

## Three Access Tiers

| | Tier 1: Open Access | Tier 2: Role-Based | Tier 3: Clinical Safeguards |
|---|---|---|---|
| **Good for** | Rec programs, food banks, settlement services, after-school | Employment, housing, family services, community development | Mental health, addictions, DV shelters, health services |
| **Baseline role matrix** | Always on | Always on | Always on |
| **Front desk sees clinical notes** | Never | Never | Never |
| **Executives see individual data** | Never | Never | Never |
| **Admin has client data** | Only with program role | Only with program role | Only with program role |
| **Per-field front desk config** | Safe defaults, no admin UI | Admin can customise (PERM-P8) | Admin can customise (PERM-P8) |
| **DV-safe mode** | Not available | Available on request | Prompted during setup |
| **GATED PM clinical access** | Not active (PM has ALLOW) | Not active (PM has ALLOW) | Active — justification + time-boxing (PERM-P6) |
| **Audit logging** | Always on | Always on | Always on |
| **Admin UI complexity** | Minimal | Moderate (+ field access table) | Full (+ GATED config + DV settings) |

### What each tier adds (tiers are additive)

**Tier 1 (Open Access):** The baseline. Role matrix enforced. Safe defaults for front desk field visibility (phone: edit, email: edit). No admin UI to change per-field access. No DV-safe mode. PM has full clinical access within their program (no justification required).

**Tier 2 (Role-Based):** Everything in Tier 1, plus:
- Admin UI to configure which core and custom fields front desk can see/edit (PERM-P8)
- DV-safe mode available (can be enabled per client, but not prompted during setup)

**Tier 3 (Clinical Safeguards):** Everything in Tier 2, plus:
- GATED PM clinical access — PM must document why they need to view clinical notes, with a time-boxed grant (PERM-P6)
- DV-safe mode is prompted during setup (agency identifies DV-sensitive fields and programs)

---

## Expert Panel Findings

### Panel 1 (5 experts): Feature Design for PERM-P5, P6, P8

#### Key decisions

1. **PERM-P6 (GATED) scope:** Program-level grants for routine supervision, individual client grants for cross-program access. Per-client-only grants would create unsustainable overhead for PMs in small agencies.

2. **PERM-P6 justification flow:** Redirect to form, then redirect back. Never show clinical content behind a modal or while the justification is pending. The clinical data must not load until after the reason is submitted.

3. **PERM-P6 audit:** Two-layer. The `AccessGrant` record is the authorisation event ("I need access for supervision"). Each individual note view is a separate `AuditLog` entry ("I opened Client X's note #42"). Both must be logged separately because PHIPA auditors will ask "who accessed Client X's file?"

4. **PERM-P6 break-glass (deferred):** Emergency immediate access (24-hour grant without pre-approval) was discussed. Deferred because it requires a notification system (admin must review every break-glass event within 48 hours). For Phase 2, all GATED access requires upfront justification. The 10-second form is fast enough for most real scenarios.

5. **PERM-P8 admin UI:** One page, two visual sections — core fields (from `FieldAccessConfig`) above, custom fields (from `CustomFieldDefinition.front_desk_access`) below. Two separate pages for "which fields can front desk see" is a usability problem for administrators.

6. **PERM-P5 flag setting:** Any worker on the case can set the DV flag unilaterally (safety first). Removing requires PM approval using the same two-person-rule pattern as alert cancellation (`recommend_cancel` → `review_cancel_recommendation`).

7. **PERM-P5 circle cascade (deferred):** When one family member has a DV flag, ideally the address should be hidden for all circle members. Deferred to after Circles are stable. The per-client flag is the 80% case.

8. **PERM-P5 front desk invisibility:** The front desk must not see that the flag is set. They see fields disappear without knowing why. If the DV check query fails (database error), default to hiding the fields (fail closed).

### Panel 2 (4 experts): Tier System Design

#### Key decisions

1. **Three tiers, determined by a short scenario-based interview** during agency setup. Not by manual permission configuration.

2. **Tiers are additive.** The permission enforcement code doesn't change between tiers — only the data in the matrix and the active features change. The `@requires_permission` decorator handles enforcement identically; the tier check relaxes GATED to ALLOW at lower tiers.

3. **PERM-P6 (GATED), PERM-P5 (DV-safe), and the full PERM-P8 admin UI are higher-tier features.** They do not appear in the admin interface for Tier 1 agencies.

4. **Audit logging is always on.** Even Tier 1 rec programs need the "who did what when" trail. PIPEDA applies to names and contact info regardless of program type.

5. **Configuration drift detection (future):** A periodic check that compares data patterns (e.g., fields named "medications" or "diagnosis") against tier assumptions. If the agency's data has become more sensitive than their tier allows for, surface a gentle prompt suggesting they review their access settings. Not an automatic tier upgrade — a nudge with context.

6. **The configurator interview must produce both a database state and a document.** The configuration summary becomes the agency's privacy reference for board members, funders, and auditors.

---

## Why Tiers Won (Not the Alternatives)

| Alternative | Verdict | Why Rejected |
|---|---|---|
| No tiers — every agency configures everything | Rejected | Configuration paralysis. Most agencies won't configure 40+ toggles. They'll use defaults (which may be wrong) or give up. |
| Two tiers only (simple / full) | Rejected | Doesn't capture the middle ground. Many agencies need per-field front desk access (Tier 2) but not GATED PM access (Tier 3). |
| Per-feature toggles (DV-safe toggle, GATED toggle, per-field toggle) | Rejected | Creates incoherent configurations. An agency could enable GATED without per-field, or DV-safe without understanding the field infrastructure. The tier model ensures features that depend on each other are activated together. |
| Automatic detection (no manual tier selection) | Rejected | Can't reliably infer sensitivity from field names or program types. A "Youth Services" program could be a basketball league or a mental health program. The agency must make an intentional decision. |
| Four or more tiers | Rejected | Diminishing returns. Three tiers cover the meaningful boundaries (non-clinical / role-differentiated / clinical). More tiers would create distinctions that don't map to real-world agency types. |

---

## Anti-Patterns (Rejected)

### DO NOT make the baseline role matrix optional

The first panel incorrectly described Tier 1 as "everyone sees everything." Even a rec program has:
- A parent's phone number (personal information under PIPEDA)
- An emergency contact (need-to-know for safety staff, not the board)
- Allergy/medical alerts (relevant at check-in, not for the ED's quarterly report)

The 4-role matrix is the floor. Front desk never sees clinical notes. Executives never see individual data. These are PIPEDA minimums, not advanced features.

### DO NOT let agencies skip tiers

Tiers must be 1, 2, or 3 — not a custom mix. An agency can cherry-pick *upward* (a Tier 1 agency enables DV-safe mode), but this surfaces a warning suggesting they review whether the full next tier is appropriate. Downward cherry-picking (a Tier 3 agency disables GATED but keeps DV-safe) is not permitted without changing the tier.

### DO NOT use a dropdown for tier selection

Use radio buttons with full descriptions visible. Each option should say what it adds in plain language. The descriptions are the most important part — not the tier number.

### DO NOT show higher-tier admin UI at lower tiers

If an agency is at Tier 1, the admin dashboard should not show cards for "Field Access Configuration" or "DV-Safe Settings." Hidden features don't create confusion. An agency that needs to move up tiers does so through the tier selector, which then reveals the relevant settings.

### DO NOT ask feature-based questions in the configurator

Wrong: "Do you want per-field front desk access?" (meaningless to a rec coordinator)
Right: "Does your front desk staff need to update phone numbers and addresses?" (a scenario they can answer)

### DO NOT create a dynamic permission matrix

The permission matrix in `permissions.py` should represent the strictest tier (Tier 3). The decorator relaxes GATED to ALLOW at lower tiers. This is simpler and safer than dynamically modifying the PERMISSIONS dict at runtime, which would create cache invalidation issues and make the matrix harder to audit.

---

## Key Technical Decisions

| Decision | Choice | Why |
|---|---|---|
| Where to store the tier | `InstanceSetting` (key: `access_tier`, value: `"1"`/`"2"`/`"3"`) | Reuses existing key-value infrastructure. No migration needed. Available in templates via `{{ site.access_tier }}`. |
| How to enforce tier in Python | `get_access_tier()` helper in `apps/admin_settings/models.py` | Single point of truth. Called by decorator and views. |
| How to enforce tier in templates | `{% if site.access_tier >= "2" %}` | String comparison works because values are single digits. |
| Permission matrix approach | Static matrix at Tier 3 strictness; decorator relaxes at lower tiers | Avoids dynamic matrix mutation. Matrix is auditable. Decorator logic is simple: `if GATED and tier < 3: treat as ALLOW`. |
| Default tier | Tier 1 (Open Access) | Most agencies start simple. The configurator interview may recommend Tier 2 or 3, but unassisted fresh installs default to the simplest safe configuration. |
| Tier change direction | Upward always allowed. Downward requires admin confirmation + warning. | Downgrading removes protections. The admin must acknowledge this. |

---

## Configurator Interview Integration

The existing agency-permissions-interview.md (Session 2) should start with four scenario questions that map to a tier recommendation:

1. **"Does your program collect health information?"** (diagnosis, treatment, medications, mental health notes)
   - Yes → Tier 2 minimum, likely Tier 3

2. **"Do you serve clients who may be at risk of domestic violence, stalking, or family conflict?"**
   - Yes → Tier 3 with DV-safe mode

3. **"Do you have distinct roles — front desk, case workers, supervisors — who should see different information?"**
   - Yes → Tier 2 minimum
   - No, everyone does everything → Tier 1

4. **"Would a funder or accreditor expect you to show an audit trail of who accessed individual client records?"**
   - Yes → Tier 2 or 3

The interviewer presents a recommendation: "Based on your answers, we recommend **Role-Based** access. Here's what that means for your team..." with a plain-language summary.

The agency confirms or overrides. The override and reasoning are recorded in the Configuration Summary.

---

## Feature Activation Matrix (Implementation Reference)

| Permission Feature | Code Location | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|---|
| `client.edit_contact` for receptionist | `permissions.py` | ALLOW (safe defaults) | PER_FIELD (admin configures) | PER_FIELD (admin configures) |
| `client.view_clinical` for PM | `permissions.py` | GATED → relaxed to ALLOW | GATED → relaxed to ALLOW | GATED (enforced) |
| `note.view` for PM | `permissions.py` | GATED → relaxed to ALLOW | GATED → relaxed to ALLOW | GATED (enforced) |
| `plan.view` for PM | `permissions.py` | GATED → relaxed to ALLOW | GATED → relaxed to ALLOW | GATED (enforced) |
| Per-field admin UI | `admin_settings/field_access_views.py` | Hidden | Shown | Shown |
| DV-safe controls on client file | `clients/_tab_info.html` | Hidden | Shown (if enabled) | Shown (prompted at setup) |
| GATED justification form | `auth_app/access_grant_views.py` | Never triggered | Never triggered | Triggered when PM accesses clinical content |
| Access grant list | `auth_app/access_grant_views.py` | Hidden | Hidden | Shown for PM and admin |

---

## Build Order

| Order | Feature | Depends On | GK Review? |
|---|---|---|---|
| 1st | Tier system (InstanceSetting + helper + admin UI + setup wizard) | Nothing | DRR only |
| 2nd | PERM-P8: Per-field front desk edit (FieldAccessConfig + admin UI + decorator) | Tier system | No |
| 3rd | PERM-P5: DV-safe mode (is_dv_safe + removal workflow + field hiding) | PERM-P8 | Yes |
| 4th | PERM-P6: GATED clinical access (AccessGrant + justification UI + decorator) | Tier system | Yes |
| 5th | Integration (translations, CLAUDE.md, TODO.md) | All above | No |

PERM-P5 depends on PERM-P8 because DV-safe mode overrides per-field access — it needs the per-field infrastructure to exist. PERM-P6 is independent of PERM-P5 and PERM-P8 (it only needs the tier check) but is built last because it's the most complex.

---

## Deferred Work

| Item | Why Deferred | When to Build |
|---|---|---|
| Break-glass emergency access (PERM-P6) | Requires notification system (admin must review every break-glass within 48h). Adds meaningful complexity. | After notification infrastructure exists (email or in-app alerts to admin). |
| Circle cascade for DV flag (PERM-P5) | Requires stable Circles feature. Doubles implementation complexity. Per-client flag is the 80% case. | After Circles are stable and in production use. |
| Configuration drift detection | Valuable but not blocking. Requires data pattern analysis. | After 3+ agencies are in production. Real-world data patterns needed to calibrate the detection. |
| Per-field admin UI for Tier 1 | Tier 1 uses safe defaults. Adding configurability defeats the simplicity purpose. | Only if a Tier 1 agency specifically requests it (at which point, they should probably move to Tier 2). |

---

## Risk Registry

| Risk | Severity | Consequence | Mitigation |
|---|---|---|---|
| Agency selects wrong tier (too low) | MEDIUM | Sensitive data accessible to more roles than intended | Scenario questions steer toward correct tier. Configuration drift detection nudges if data patterns suggest higher sensitivity. |
| Agency selects wrong tier (too high) | LOW | Unnecessary friction for staff, adoption resistance | Configurator explains what each tier means. Agency can downgrade with admin confirmation. |
| PM finds GATED too onerous at Tier 3 | MEDIUM | PM escalates to admin to lower tier, weakening protections | Default to 7-day program grants (not per-client). Monitor admin override rates in first 3 months of production use. |
| DV flag set but front desk already saw the address | LOW | Past access cannot be revoked | Document as known limitation. Flag protects future access, not past knowledge. Audit trail shows who accessed what before the flag was set. |
| Admin never configures per-field access at Tier 2 | LOW | Safe defaults apply (phone: edit, email: edit), which may not match agency needs | Defaults are safe. Setup wizard prompts for field access configuration. 30-day check-in reviews gaps. |
| `AccessGrant` table grows unbounded | LOW | Performance degradation on grant lookups | Grants are small records. Add `granted_at` index. Archive grants older than 7 years (PHIPA retention period). |
| Tier change from 3 to 2 leaves orphaned AccessGrants | LOW | Grants exist but aren't checked (GATED relaxed to ALLOW at Tier 2) | Acceptable — grants expire naturally. No data integrity issue. Document that downgrading does not delete historical grants. |

---

## GK Review Items

- [ ] PERM-P6: Justification categories — are the 5 enumerated reasons correct for Canadian nonprofit clinical supervision? (clinical supervision, complaint investigation, safety concern, quality assurance, intake/case assignment)
- [ ] PERM-P6: Default grant duration of 7 days with max 30 — does this match supervision cycles?
- [ ] PERM-P5: DV-safe hidden fields list — address, emergency contact name, emergency contact phone, employer/school. Are there others?
- [ ] PERM-P5: Two-person-rule for flag removal — does the PM approval pattern match existing DV safety protocols?
- [ ] Tier names ("Open Access" / "Role-Based" / "Clinical Safeguards") — are these clear and non-judgmental?
- [ ] Configurator scenario questions — are the 4 questions sufficient to determine the right tier?
