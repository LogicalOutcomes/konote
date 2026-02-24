# PHIPA Cross-Program Consent Enforcement — Design Rationale Record

Task ID: PHIPA-ENFORCE1
Date: 2026-02-22
Status: Approved (two expert panel rounds)
Supersedes: `docs/plans/2026-02-20-phipa-consent-enforcement-design.md` (original design — data model and helpers)

---

## Problem

When a participant is enrolled in multiple programs and a staff member has access to more than one of those programs, clinical notes from ALL shared programs are visible. Under PHIPA (Ontario's Personal Health Information Protection Act), clinical information should only be shared across program boundaries when appropriate consent exists.

The data model (`ClientFile.cross_program_sharing`), feature toggle (`cross_program_note_sharing`), and helper functions (`should_share_across_programs()`, `apply_consent_filter()`) were implemented per the original design doc. The `note_list()` view enforces consent. Other views that display clinical note content do not.

## Expert Panel Findings

### Round 1: Correctness and Scope

Panel: Healthcare Privacy Specialist, Django Security Architect, Systems Thinker, Nonprofit Technology Consultant

**Key decisions:**

1. **Portal views are out of scope.** PHIPA s. 52 gives individuals the right to access their own health information. The portal participant is viewing their own data — no restriction needed.

2. **Aggregate views are out of scope.** Executive dashboard, home dashboard counts, and de-identified report aggregates are not PHI. No consent filter needed.

3. **Plan views are out of scope.** PlanTarget and PlanSection are already scoped by `plan_section__program_id`. The plan structure (goal names, sections) is not clinical note content.

4. **Note search is a side channel.** `_find_clients_with_matching_notes` in `clients/views.py` loads notes from all programs without filtering. A search for "suicidal ideation" could reveal that a restricted-program note contains that term. This is a real disclosure risk but requires a separate implementation approach (program-level filtering in the search function). **Deferred to separate ticket.**

5. **Note cancel has a decorator gap.** `_get_program_from_note` resolves to the user's best shared program, not the note's authoring program. A staff member could reach the cancel form for a note from a restricted program. **Deferred — low likelihood (requires guessing note ID).**

6. **Client analysis (metric values) is a rare edge case.** MetricValue queries filter targets by program but don't filter the contributing notes. A cross-program metric recording would be unusual (targets are typically owned by one program). **Deferred to separate ticket.**

### Round 2: Brittleness and Maintenance

Panel: Django Middleware Architect, Tech Debt Analyst, Small Nonprofit Technology Advisor, Reliability Engineer

**Key decisions:**

7. **Reduce enforcement scope to prevent shotgun surgery.** The original plan added consent checks to 7-9 views across 4 files. Every future view that touches `ProgressNote` would need to remember to add the check. For a small nonprofit with no dedicated developer, this is unsustainable. **Enforce in 4 views only:** `note_list` (done), `note_detail`, `note_summary`, `event_list`.

8. **A custom QuerySet manager was considered and rejected.** It adds a new concept (two managers on the model) without eliminating the core problem (developers must still remember which to use). A well-documented function in `access.py` is more appropriate for this codebase. **Revisit if KoNote grows a development team.**

9. **Fix the fail-open bug.** When sharing is OFF and `get_author_program()` returns None (no shared program found), `apply_consent_filter` currently returns the unfiltered queryset. For a privacy feature, fail-closed is safer: return an empty queryset. A bug here should result in "can't see notes" (safe) rather than "can see everything" (unsafe).

10. **Fix the CONF9 context switcher interaction.** `apply_consent_filter` calls `get_author_program(user, client)` which ignores the context switcher. If a user switches to "Program A only" in the UI, the consent filter might still pick Program B as the viewing program. **Pass `active_program_ids` through the consent filter.**

11. **Single consent banner include file.** Don't copy-paste the `{% blocktrans %}` block across templates. Create `_consent_banner.html` and use `{% include %}`. One source of truth for wording and translation.

12. **Document in CLAUDE.md.** Add a "PHIPA Consent Enforcement" section so future AI sessions know to apply consent filtering when adding note views. This is more reliable than hoping a developer reads module docstrings.

## Anti-Patterns (Rejected)

| Approach | Why Rejected |
|----------|-------------|
| Middleware that intercepts note responses | Fragile, violates Django conventions, hard to test |
| Decorator that auto-filters context querysets | Too magical, hides filtering, makes debugging hard |
| Per-client consent check in note search | Too expensive (one check per client in search results); use program-level filter instead |
| Enforce in every view that touches notes | Shotgun surgery — 7-9 enforcement points is too many to maintain for a small nonprofit |
| Default-False (restrict by default) | Agencies that never configure the setting would accidentally over-restrict their own staff |

## Deferred Work

| Item | Risk | Ticket |
|------|------|--------|
| Note search program-level filtering | HIGH — search can reveal restricted program data | Create after this PR |
| qualitative_summary consent filter | MEDIUM — shows client words from note entries | Create after this PR |
| Note cancel consent check | LOW — requires guessing note ID | Parking lot |
| Client analysis metric value filter | LOW — rare cross-program metric pattern | Parking lot |
| check_note_date consent filter | LOW — shows existence only | Parking lot |
| Audit log viewer check | LOW — admin-only access | Parking lot |

## Known Limitations

1. **"Information laundering"** — A staff member who reads notes in one program context may reference that information when creating a note in another context. PHIPA controls what the system discloses, not what clinicians remember. Documented, not solvable in software.

2. **Feature toggle cache (300s).** When an admin turns sharing OFF, notes may remain visible in views for up to 5 minutes due to cache TTL. Acceptable for a configuration change that happens rarely.

3. **No safety alert exception.** No `safety_alert` field exists on `ProgressNote`. If a future feature allows flagging safety-critical notes, those should bypass consent restrictions. Deferred until the feature is built.

## Enforcement Matrix (Final)

| View | Enforced? | Method | Notes |
|------|-----------|--------|-------|
| `note_list` | YES (already done) | `apply_consent_filter()` on queryset | Primary display |
| `note_detail` | **YES (this PR)** | `check_note_consent_or_403()` | Direct URL bypass prevention |
| `note_summary` | **YES (this PR)** | `check_note_consent_or_403()` | HTMX partial, same risk |
| `event_list` | **YES (this PR)** | `apply_consent_filter()` on notes queryset | Renders note text inline |
| `qualitative_summary` | Deferred | — | Separate ticket |
| `check_note_date` | Deferred | — | Near-zero risk |
| `note_cancel` | Deferred | — | Decorator limits access |
| Home dashboard | No (exempt) | — | Aggregate counts, not PHI |
| Executive dashboard | No (exempt) | — | De-identified aggregates |
| Plan views | No (exempt) | — | Already program-scoped |
| Portal views | No (exempt) | — | Participant's own data |
| Report exports | No (exempt) | — | De-identified aggregates |
| Client analysis | Deferred | — | Rare edge case |
