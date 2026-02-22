# Design Rationale Record: Circles (Family/Network Entity)

**Feature:** Circles — organic groupings of people bound by family, household, kinship, or caregiving relationships
**Status:** Circles Lite approved for Phase 1. Full design preserved as long-term vision.
**Date:** 2026-02-21
**Task ID:** FAM-DESIGN1
**Design document:** `tasks/family-entity-design.md`

---

## Keyword Index

bidirectional storage, orphaned rows, relationship pairs, circle-scoped relationships,
global relationships, RelationshipType table, inverse codes, FHIR codes, circle_type,
circle plans, CirclePlanSection, CirclePlanTarget, polymorphic plans, circle notes,
CircleNote, ProgressNote circle tag, non-participant members, member merge, merge pathway,
encrypted field search, name search index, role_in_circle, primary_contact, care team,
kinship, found family, household, PHIPA circle notes, consent per member,
ClientAccessBlock small circles, DV safety, circle permissions, adoption risk, shelfware,
intake integration, caseworker workflow, data quality, funder reporting, family count,
graduated complexity, feature toggle, terminology override

---

## How to Use This Document

This record captures expert analysis from **two formal panels (10 expert perspectives)** reviewing the Circles data model. It exists to prevent future developers from re-introducing designs that were already evaluated and rejected for specific reasons.

**Rules for future sessions:**
1. Read this document before modifying any model in `apps/circles/`
2. If a proposed change contradicts an anti-pattern below, do not proceed without explicit stakeholder approval
3. If you believe circumstances have changed and a deferred feature should be built, check the "Graduated Complexity Path" section for the conditions under which it should be reconsidered
4. When in doubt, favour simplicity — the panels unanimously found that over-engineering is the primary adoption risk

---

## Anti-Patterns: DO NOT Do These Things

### DO NOT create global person-to-person relationships

**What it looks like:** A `PersonRelationship` table that says "Maria is Juan's parent" at the system level, independent of any circle.

**Why it seems like a good idea:** It's architecturally cleaner. No duplication when two people appear in multiple circles. One source of truth.

**Why it was rejected:** Global relationships mean any staff member who can see Maria can discover that Juan exists — even if they have no access to Juan's record. Under PHIPA, the *existence* of a parent-child relationship is itself personal health information. Circle-scoped relationships provide natural privacy containment: you only see relationships within circles you have access to. The privacy risk outweighs the architectural elegance.

**If you're tempted:** The duplication concern is real but manageable at 200-2,000 participants. Implement soft-match pre-population instead: when creating a relationship in Circle B between two people who already have one in Circle A, offer to copy the details. Privacy containment with reduced data entry friction.

*Source: Privacy Specialist vs. Database Architect debate, Panel 1 Round 2. Resolved in favour of privacy by Panel 1 Round 3 consensus.*

---

### DO NOT store relationships as two bidirectional rows with a pair ID

**What it looks like:** "Maria → Juan = PARENT" and "Juan → Maria = CHILD" as two rows sharing a `relationship_pair_id` UUID.

**Why it seems like a good idea:** Makes queries fast — "give me all of Juan's relationships" is a single index lookup on `from_member`.

**Why it was rejected:** Creates an entire class of data integrity bugs:
- One row deleted without the other (orphaned half-relationship)
- Relationship type updated on one row but not the inverse
- Three rows sharing one pair_id instead of two
- Two rows with the same pair_id pointing in the same direction

At 200-2,000 participants, query performance is irrelevant — correctness matters more. The system already loads records into Python for decryption, so the query simplification doesn't help.

**Instead:** Store one row per relationship. Either always put the lower-ID member as `from_member` and derive the inverse in application code, or (in Circles Lite) use a simple text label on CircleMembership with no separate relationship table at all.

*Source: Database Architect, Panel 1 Round 1, item 1. Confirmed in Round 3 consensus.*

---

### DO NOT build a separate CircleNote model

**What it looks like:** A `CircleNote` model with its own `circle` FK, `_note_text_encrypted`, `author`, timestamps — parallel to `ProgressNote`.

**Why it seems like a good idea:** Clean separation. Circle notes are "about the circle," individual notes are "about the person."

**Why it was rejected (two independent reasons):**

1. **Workflow death.** Caseworkers live on participant pages. They write notes there. Asking them to navigate to a separate circle page to write a circle note means the note won't get written. "Build it into the workflow I already use" — Caseworker, Panel 2. The note that gets written is the one that's on the screen the caseworker is already looking at.

2. **Privacy landmine.** A separate circle note model needs its own access control rules. The original design proposed "visible to staff with access to any member." Under PHIPA, a note about Margaret's care team written by a Caregiver Support coach contains Margaret's PHI — visible to staff who only have access to Tom's record. This is unauthorized disclosure. Building a separate model forces you to solve this hard privacy problem. Tagging existing notes avoids it entirely.

**Instead:** Add an optional `circle` FK to the existing `ProgressNote`. When a caseworker writes a note on Maria's record and tags it to the Garcia Family, it's Maria's note (governed by Maria's access rules) that also appears when viewing the circle's timeline. One model, one permission system, one audit trail.

*Source: Caseworker and Technology Consultant, Panel 2 Rounds 1-2. IT Manager confirmed from maintenance perspective.*

---

### DO NOT build circle-level plans (CirclePlanSection / CirclePlanTarget) until agencies prove they need them

**What it looks like:** A parallel plan structure attached to Circle instead of ClientFile, with its own sections, targets, metrics, views, and templates.

**Why it seems like a good idea:** Families have shared goals ("maintain housing stability"). Those goals don't belong to one person.

**Why it was rejected for Phase 1 (two independent reasons):**

1. **Maintenance time bomb.** Two parallel plan engines (individual + circle) will diverge. Every future change to plans — adding progress percentages, changing how metrics attach, adding plan templates — must be made in two places. Within a year, one copy falls behind. Features exist on individual plans that don't exist on circle plans. Staff ask "why can't I do X on a circle plan?"

2. **Unproven need.** No agency has demonstrated they can't work without circle-level outcomes. Tracking a shared goal on the primary contact's individual plan is sufficient for most agencies. Build circle plans only when usage data shows agencies are working around this limitation.

**When to reconsider:** After 6-12 months of Circles Lite usage, if multiple agencies report that they're creating duplicate individual goals to represent shared family outcomes. When built, use a polymorphic model: one `PlanSection` with an optional `circle` FK alongside the existing `client_file` FK. Never two separate model hierarchies.

*Source: Database Architect Option B, Panel 1 Round 1. Confirmed unanimously by all four Panel 2 experts.*

---

### DO NOT create a RelationshipType table with inverse codes for Phase 1

**What it looks like:** A `RelationshipType` model with `code`, `inverse_code`, `category`, `fhir_code`, `is_system`, `sort_order` — 18+ seeded types.

**Why it seems like a good idea:** Structured data enables reporting ("how many grandparent-headed households?"), FHIR interoperability, and consistent terminology.

**Why it was deferred:**

1. **Adoption killer.** A dropdown of 18 relationship types overwhelms caseworkers. "I'll pick 'Other' every time because it's at the bottom and I'm in a hurry." — Caseworker, Panel 2. When the most common selection is "Other," the entire taxonomy is useless.

2. **Premature structure.** Most agencies need 4-5 types: Parent, Child, Spouse, Sibling, Other. A free-text label ("parent", "grandparent", "mom") captures this with zero training. Staff write what makes sense to them. It's searchable enough for small datasets.

3. **Inverse codes are fragile.** Maintaining bidirectional inverse relationships (PARENT ↔ CHILD, GUARDIAN ↔ WARD) requires careful application logic and creates the orphan-row risk described above.

**Instead (Phase 1):** A simple text field (`relationship_label`) on `CircleMembership`. Caseworker types "parent" or "spouse." No dropdown, no codes, no inverses.

**When to reconsider:** When an agency needs structured relationship reporting for funders (e.g., "count of grandparent-headed households"). At that point, build the RelationshipType table and offer a migration that maps common text labels to structured types. Also add `CO_PARENT` (symmetric) — it was identified as the most common missing type in the original 18.

*Source: Social Services Veteran and Caseworker, Panels 1-2. Program Manager confirmed 4-5 types cover 90% of need.*

---

### DO NOT build role_in_circle as a multi-value field alongside relationship types

**What it looks like:** CircleMembership has both a `role_in_circle` (member, head_of_household, primary_caregiver, care_recipient, etc.) AND separate relationship types per person.

**Why it was rejected:** These encode overlapping information. In the care team example, Tom is `primary_caregiver` (role) AND has a SPOUSE relationship to Margaret AND has a CAREGIVER relationship. Three fields encoding similar information. Staff fill in one and not the others, or fill them in inconsistently. Two sources of truth for "how is this person connected?"

**Instead (Phase 1):** `is_primary_contact` boolean flag on CircleMembership + free-text `relationship_label`. That's it. "Primary contact" is the only role that has operational meaning (who does the agency call first?). Everything else belongs in the relationship label or in a note.

*Source: Social Services Veteran, Panel 1 Round 1. IT Manager confirmed from training perspective, Panel 2.*

---

### DO NOT make circle_type a single-select enum expecting it to be permanent

**What it looks like:** `circle_type = CharField(choices=[family, household, support_network, kinship_group, care_team])`

**Why it's problematic:** A multigenerational Indigenous family sharing a home is simultaneously a family, a household, a kinship group, and (if an elder needs care) a care team. Forcing one label means reports that filter by type give incomplete data.

**For Phase 1:** Don't include circle_type at all. A circle is a circle. If reporting needs emerge that require categorization, add it as a tag/multi-select field, not a single-select enum. Or add a `primary_type` with optional `secondary_types` (PostgreSQL ArrayField / SQLite comma-separated CharField).

*Source: Complexity Thinker, Panel 1 Round 1. Database Architect proposed the ArrayField compromise in Round 2.*

---

## Decided Trade-offs

### Circle-scoped relationships vs. global relationships
- **Chosen:** Circle-scoped (relationships exist within a circle context)
- **Trade-off:** Some duplication when two people appear in multiple circles
- **Reason:** PHIPA privacy containment — relationship existence is itself PHI
- **Mitigation:** Soft-match pre-population when same people appear in multiple circles
- **Domains:** Privacy, Data Model

### Free-text relationship labels vs. structured RelationshipType table
- **Chosen:** Free-text for Phase 1, structured table deferred
- **Trade-off:** Can't do structured relationship reporting until Phase 2
- **Reason:** Adoption — 18-type dropdown kills caseworker compliance; text field is zero-friction
- **Mitigation:** Common labels will naturally converge ("parent", "spouse"); migration path exists
- **Domains:** UX, Data Quality, Reporting

### Circle note as ProgressNote tag vs. separate CircleNote model
- **Chosen:** Optional `circle` FK on existing ProgressNote
- **Trade-off:** A "circle note" is always authored on one person's record (not neutral)
- **Reason:** Workflow (caseworkers stay on participant pages) + privacy (existing access rules apply) + maintenance (one model, not two)
- **Mitigation:** The note appears in the circle timeline regardless of which member's record it was written on
- **Domains:** UX, Privacy, Maintenance

### Intake-integrated circle creation vs. standalone circle management
- **Chosen:** Circle creation as part of intake workflow, with standalone creation also available
- **Trade-off:** Slightly more complex intake form
- **Reason:** Data completeness — features integrated into existing workflow get near-100% adoption; add-on features get 30%
- **Domains:** Adoption, Data Quality

### Non-participant members as simple name field vs. structured record
- **Chosen:** Nullable `client_file` FK + `member_name` text field on CircleMembership
- **Trade-off:** Non-participants have no structured data (phone, address, role details)
- **Reason:** Simplicity — adding structured non-participant records creates a shadow participant model. If someone needs a full record, make them a participant.
- **Mitigation:** "Merging" a non-participant with a new ClientFile is just updating the FK and clearing the name field. No complex merge logic.
- **Domains:** Data Model, Maintenance

---

## Risk Registry

### Adoption Risk (HIGH — primary risk)
**What:** Staff don't create circles because it's too many steps, too many fields, or not part of their existing workflow.
**Consequence:** Data is incomplete; program managers can't trust circle reports; feature becomes shelfware.
**Mitigation:** Circles Lite strips to minimum fields. Intake integration makes creation part of existing workflow. Circle notes use existing ProgressNote model. No separate circle pages required for daily work.
**Monitor:** Track circle creation rate vs. new participant creation rate. If ratio is below 0.3 after 3 months, investigate workflow friction.

### Data Quality Risk (MEDIUM)
**What:** Circles created with incomplete membership (missing family members) or inconsistent relationship labels.
**Consequence:** Family count reports are inaccurate. Same family might have multiple circles if staff don't search before creating.
**Mitigation:** Intake integration catches most families at enrolment. Participant page sidebar makes existing circles visible. Free-text labels reduce friction (staff write what's natural).
**Monitor:** Count circles with only 1 member (likely incomplete). Count participants in 0 circles vs. those with circle notes in individual records (suggests workaround).

### Privacy Risk — Circle Notes Under PHIPA (MEDIUM)
**What:** A note tagged to a circle contains one member's PHI, visible to staff who have access to a different member.
**Consequence:** Unauthorized disclosure of personal health information under PHIPA.
**Mitigation (Phase 1):** Notes are ProgressNotes on a specific participant's record, governed by that participant's access rules. The circle tag adds visibility but doesn't override individual access. Staff who can't see Maria's records can't see Maria's notes, even if those notes are tagged to a circle they can see through Tom.
**Residual risk:** A note written on Tom's record that says "Margaret didn't recognise Tom today" is Tom's note (accessible to Tom's staff) but contains Margaret's PHI. Mitigate with UI guidance: "Circle-tagged notes should describe observations about the group, not clinical details about specific members."
**Future consideration:** If a dedicated circle note model is ever built, it needs per-member consent tracking and a decision on whether visibility requires access to *all* members or *any* member. The panels did not reach consensus on this — it's a policy decision for agencies.

### Privacy Risk — ClientAccessBlock in Small Circles (LOW)
**What:** In a 2-person household, hiding one member (DV safety block) leaves a 1-person "household" that reveals the hidden member's existence by absence.
**Mitigation:** When ClientAccessBlock would hide a member from a circle with fewer than 4 visible members, hide the entire circle from the blocked staff member.

### Encrypted Field Search Performance (LOW for Phase 1)
**What:** Circle names are encrypted. Searching for a circle by name requires loading all circles into memory and decrypting.
**Consequence:** Slow circle search as circle count grows.
**Mitigation (Phase 1):** At 200-2,000 participants with maybe 300-800 circles, in-memory search is acceptable (same pattern as participant search). Circles are found primarily through participant pages, not standalone search.
**Future:** If standalone circle search becomes important, add a `name_search_index` (trigram hash or first-letter index) alongside the encrypted name.

### Maintenance Risk — Future Feature Divergence (LOW if rules followed)
**What:** A future developer adds a feature to individual plans but forgets to add it to circle plans (or vice versa).
**Mitigation:** Circle plans are deferred. When built, they MUST use a polymorphic model (one PlanSection with optional `circle` FK). Never two parallel model hierarchies. This anti-pattern is documented above.

---

## Graduated Complexity Path

Each level should only be built when the trigger condition is met — not proactively.

### Level 1: Circles Lite (Phase 1 — build now)
- Circle model: name (encrypted), status, is_demo
- CircleMembership: client_file (nullable), member_name, relationship_label (text), is_primary_contact, status
- ProgressNote gains optional `circle` FK
- Intake form integration
- Participant page sidebar showing circle members
- Feature toggle (default: off)
- Terminology entries (overridable)
- Report: count of circles served, average size

### Level 2: Structured Relationships (build when triggered)
**Trigger:** An agency needs structured relationship reporting for funders (e.g., "count of grandparent-headed households") OR FHIR export is required.
**Scope:** Add RelationshipType table (start with 6-8 common types, not 18). Add CircleRelationship model (single-row storage). Migrate existing text labels to structured types. Add `CO_PARENT` as a default type.
**Prerequisite:** At least 3 months of Circles Lite usage to validate adoption.

### Level 3: Circle Plans (build when triggered)
**Trigger:** Multiple agencies report that they're creating duplicate individual goals to represent shared family outcomes, and workarounds are causing data quality problems.
**Scope:** Add optional `circle` FK to existing PlanSection/PlanTarget (polymorphic, NOT separate models). Add circle plan UI.
**Prerequisite:** Level 1 adopted with >50% data completeness. At least 6 months of usage.

### Level 4: Advanced Features (build when triggered)
**Trigger:** Interoperability requirements or specialized agency needs.
**Scope:** FHIR codes on RelationshipType. Genogram/family tree visualization. Circle-level reports (composition demographics, family stability metrics, caregiver burden). Export circle data alongside individual data.
**Prerequisite:** Levels 1-2 stable in production.

---

## Expert Panel Sources

### Panel 1: Technical Architecture Review (2026-02-21)
Four experts, three rounds. Focused on data model integrity, privacy, and technical risk.
- **Social Services Data Systems Veteran** — recommended global relationships (later reversed after privacy debate), simplified roles, fewer default relationship types
- **Relational Database Architect** — recommended single-row relationship storage, polymorphic plans, merge pathway for non-participants, searchable name index
- **Privacy & Compliance Specialist** — recommended circle-scoped relationships for PHIPA containment, per-member consent on circle notes, whole-circle hiding for small DV-safety circles
- **Complexity & Systems Thinker** — recommended multi-select circle types, CO_PARENT relationship type, status field on relationships, humility about modelling human relationships

### Panel 2: Practitioner Adoption Review (2026-02-21)
Four experts, three rounds. Focused on whether real people would actually use this.
- **Nonprofit Program Manager** — needs family count for funders and family notes; found full design overwhelming; endorsed Circles Lite with notes
- **Frontline Caseworker** — will only use features built into existing workflow (intake, participant page, note form); wants text fields not dropdowns; wants note tagging not separate circle notes
- **Nonprofit IT Manager** — sole IT person; wants 2-3 tables not 8; endorsed reusing ProgressNote model; concerned about migration risk and debugging encrypted data
- **Social Services Technology Consultant** — has seen family tracking become shelfware at 6 of 11 agencies; identified intake integration as the key adoption driver; proposed the three-option framework (linked participants / minimal circles / full design)

---

## Appendix: The Shelfware Pattern

The Technology Consultant described a pattern seen at multiple agencies that this entire design strategy is built to avoid:

1. **Design phase:** Everyone excited about family tracking. Requirements document is comprehensive.
2. **Build phase:** Developers build everything requested. Technically correct and thorough.
3. **Launch phase:** Training goes well. Staff create practice circles.
4. **Month 2:** Usage drops. Staff create circles for ~30% of families. Rest tracked as individuals with notes.
5. **Month 6:** Program manager can't trust data for funder reports. Goes back to counting by hand.
6. **Year 2:** Feature is technically present but treated as optional. New staff aren't trained. Shelfware.

**Root cause:** The feature saves the *program manager* time at reporting season but *costs the caseworker* time every day. Caseworkers have no daily incentive to create circles. Adoption fails.

**Circles Lite counters this by:** Making circle creation part of intake (not a separate task), using existing ProgressNote for circle notes (not a separate workflow), and showing circle info on participant pages (where caseworkers already work). The caseworker's daily experience is unchanged — they just see family context on the pages they already use.
