# Project Tasks

## Flagged

- [ ] Choose Canadian hosting provider for pilot deployment — See `tasks/canadian-hosting-research.md` (HOST1)

## Active Work

_No active work. Ready for pilot testing._

## Roadmap — Prioritized Extensions

Based on usability review and expert panel analysis. See `tasks/usability-review-results.md` for full rationale.

### Phase A: Market Access (High Priority)

_All Phase A tasks complete._

### Phase B: Funder Reporting (High Priority)

- [x] Report aggregation functions — count, avg, min, max by grouping — (RPT3)
- [x] Demographic grouping in reports — age range, gender, geography — (RPT4)
- [x] Outcome achievement rate calculation — % clients meeting target — (RPT5)
- [x] Funder Report Template — draft export for funders (customise per funder) — (RPT6)
- [x] Fiscal year date range filter — April-March for Canadian nonprofits — (RPT7)

### Phase C: Documentation for Open-Source Adoption (High Priority)

See `tasks/documentation-improvement-plan.md` for full rationale.

- [x] Create getting-started.md — complete local dev setup guide — (DOC8)
- [x] Create security-operations.md — security tests, audit logs, key rotation — (DOC9)
- [x] Enhance README Quick Start — add key generation commands — (DOC10)
- [x] Add inline comments to .env.example — explain each variable — (DOC11)

**Phase C.2: Non-Developer Accessibility** — See `tasks/documentation-expert-review.md`

- [x] Add "What You'll Need" pre-flight checklist to getting-started.md — (DOC12)
- [x] Add "What just happened?" explanations after key generation steps — (DOC13)
- [x] Add expected output examples showing what success looks like — (DOC14)
- [x] Add glossary section: terminal, repository, migration, container — (DOC15)
- [x] Create "Before You Enter Real Data" checkpoint document — (DOC16)
- [x] Fix placeholders to obviously fake values like REPLACE_THIS — (DOC17)

### Phase E: Self-Service Registration (Medium Priority)

Public sign-up forms for programs — parents register kids for sports, adults sign up for classes. See `tasks/self-service-registration-design.md` for full design.

- [x] RegistrationLink model — shareable form config per program — (REG1)
- [x] Public registration form view — mobile-friendly, no login required — (REG2)
- [x] RegistrationSubmission model — pending entries awaiting review — (REG3)
- [x] Submission review UI — approve/reject/merge duplicates — (REG4)
- [x] Auto-approve option — skip staff review for low-risk programs — (REG5)
- [x] Duplicate detection — match by email/phone, flag for merge — (REG6)
- [x] Capacity limits and deadlines — close registration when full or past date — (REG7)
- [x] Iframe embed support — agencies can embed form on their own website — (REG8)

### Phase F: Staff Productivity (Medium Priority)

See `tasks/note-follow-ups-design.md` for full design and rationale.

- [x] Note follow-up dates — optional follow-up date on notes, shows on home page — (FU1)

### Planned Extensions (Build When Requested)

These features are designed but deferred until agencies request them. See expert panel rationale in `tasks/field-data-decision.md`.

- [ ] Field data collection integrations — KoBoToolbox, Forms, or other tools — (FIELD1)
- [ ] CSV bulk client import — simpler alternative to tool-specific integrations — (IMP1)

### Explicitly Out of Scope

These features are intentionally excluded. See technical documentation for rationale.

- ~~Calendar/scheduling~~ → Recommend Calendly, Google Calendar, Microsoft Bookings
- ~~Full document storage~~ → Recommend Google Drive, SharePoint, Dropbox
- ~~Offline PWA~~ → Paper forms acceptable; integrations available when needed
- ~~Multi-tenancy~~ → Fork required for coalition implementations

## Parking Lot

- [ ] Progress note encryption — encrypt clinical content (CLOUD Act protection) — (SEC1)
- [ ] First-run setup wizard — Claude skill + import command — See `tasks/setup-wizard-design.md` (SETUP1)
- [ ] Bulk operations for discharge, assign, export — (UX17)

## Recently Done

- [x] Azure deployment guide — step-by-step for Canadian hosting — See `tasks/azure-deployment-guide.md` — 2026-02-04 (DOC20)
- [x] Move old docs to archive folder — 2026-02-03 (DOC19)
- [x] Create "Quick Start for Staff" training doc — 2026-02-03 (DOC18)
- [x] Fix test suite configuration error — 2026-02-03 (TEST2)
- [x] PIPEDA/PHIPA consent workflow — block note entry until client consent recorded — 2026-02-03 (PRIV1)
- [x] Note follow-up dates on home page — 2026-02-03 (FU1)
- [x] Add backup automation examples to docs — 2026-02-03 (OPS1)
- [x] Add client search filters (program, status, date) — 2026-02-03 (UX19)
- [x] Note auto-save / draft recovery — 2026-02-03 (UX21)
- [x] Mobile responsiveness pass — 2026-02-03 (UI1)
- [x] Add CSV export for all client data — 2026-02-03 (EXP1)

_Older completed tasks moved to [tasks/ARCHIVE.md](tasks/ARCHIVE.md)._
