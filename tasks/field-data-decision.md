# Field Data Collection — Build Decision

**Decision:** Defer until agencies request specific integrations.

**Date:** 2026-02-03

## Context

Phase D proposed building:
- KoBoToolbox import API endpoint
- SharePoint Lists webhook receiver
- Field data import documentation

Current state: Agencies use paper forms in the field and manually enter data later.

## Expert Panel Recommendation

A panel of three experts (Nonprofit Technology Consultant, Lean Product Strategist, Open Source Community Builder) unanimously recommended deferring.

### Key Reasons

1. **No demonstrated demand** — No agency has requested this. Building speculatively creates maintenance burden with zero users.

2. **Agencies won't ask by tool name** — They'll say "data entry takes forever," not "we need KoBoToolbox integration." Document the pain point so you can respond when asked.

3. **Stage 1-2 adoption focus** — KoNote is still establishing core adoption. Advanced integrations won't attract new users (they evaluate on core features) and won't retain users (they haven't hit this friction yet).

4. **Tool choice should follow demand** — When an agency requests this, ask which tool they actually use. Build for real tools, not hypothetical ones.

## What We Did Instead

- Moved field data integrations to "Planned Extensions (Build When Requested)"
- Kept CSV bulk import as a simpler alternative (broader utility, lower complexity)
- Updated "Out of Scope" to clarify integrations are available when needed
- Created this decision document

## When to Revisit

Build field data integrations when:

1. An agency explicitly requests it
2. They specify which tool they use (KoBoToolbox, Microsoft Forms, Google Forms, etc.)
3. They can describe their volume (how many clients/records)
4. They're willing to test the integration

## Documentation to Add

When ready to build, add to the README or a docs page:

> **Field Data Collection (Extensible)**
>
> KoNote can be extended to import data from field collection tools. If your agency would benefit from integration with a specific tool, open an issue describing your current workflow.
