# CIDS Classification Workflow — Implementation Tasks

Task ID: CIDS-WORKFLOW1
Date: 2026-03-07
Status: Draft plan
Depends on:
- [tasks/design-rationale/cids-metadata-assignment.md](tasks/design-rationale/cids-metadata-assignment.md)
- [tasks/design-rationale/cids-batch-classification-workflow.md](tasks/design-rationale/cids-batch-classification-workflow.md)

---

## Goal

Add a reporting-oriented classification workflow that:

1. assigns deterministic local metadata immediately when staff create metrics and targets
2. delays interpretive taxonomy classification to an admin batch-review workflow
3. supports multiple reporting taxonomies such as Common Approach, IRIS+, SDG, and partner-specific code lists

## Phase 1 — Immediate Metadata Hardening

### Outcome

Keep current create-time behaviour limited to deterministic registration metadata.

### Tasks

1. Keep automatic local URI assignment for metrics and targets.
2. Keep automatic local `defined_by` fallback when no external standard is explicitly selected.
3. Keep unit carry-through from plain-language metric unit to human-readable CIDS unit description.
4. Ensure no save-time logic infers IRIS, SDG, Common Approach category, or partner taxonomy automatically.
5. Add tests that local defaults do not count as external standards alignment.

## Phase 2 — Mapping Data Model

### Outcome

Store draft and approved taxonomy mappings separately from local identity metadata.

### Tasks

1. Extend taxonomy mapping storage to support:
   - mapping status: draft, approved, rejected, superseded
   - mapping source: manual, imported, ai_suggested
   - confidence score
   - rationale text
   - reviewer and review timestamp
2. Allow one local item to have multiple mappings under different taxonomy systems.
3. Support targets, metrics, programs, and structured intake options as mappable entities.
4. Keep local CIDS URI fields separate from external mapping records.

## Phase 3 — Batch Suggestion Jobs

### Outcome

Admin can run asynchronous classification jobs without affecting frontline workflows.

### Tasks

1. Add a batch job that finds new or changed unmapped items.
2. Add a suggestion pipeline that narrows candidate codes first, then calls the LLM.
3. Support separate job modes for:
   - Common Approach
   - IRIS+
   - SDG
   - partner-specific taxonomy
4. Store all results as draft suggestions only.
5. Add logging and retry handling for long-running jobs.

## Phase 4 — Admin Review Queue

### Outcome

Admin or reporting lead can review, approve, reject, and refine AI suggestions.

### Tasks

1. Build an admin-only queue showing:
   - unmapped items
   - low-confidence items
   - draft suggestions awaiting review
   - items mapped for one taxonomy but not another
2. Show for each suggestion:
   - local wording
   - suggested code and label
   - taxonomy system
   - confidence
   - rationale
3. Allow approve, reject, search manually, and bulk-approve for repeated items.
4. Record reviewer identity and decision date.

## Phase 5 — Conversational Review

### Outcome

Admin can interrogate the AI about the proposed classifications.

### Tasks

1. Add an admin-only review conversation interface.
2. Support prompts such as:
   - why was this grouped here?
   - show alternate classifications
   - classify this set using SDG instead of IRIS
   - collapse these into broader report buckets
3. Keep the conversation grounded in current draft suggestions and approved mappings.
4. Do not let conversational output become official without explicit approval.

## Phase 6 — Reporting Profiles and Exports

### Outcome

Reports can be generated using different approved taxonomy lenses.

### Tasks

1. Add report profiles that specify which taxonomy system to use.
2. Default official exports to approved mappings only.
3. Show coverage warnings when required mappings are still draft or missing.
4. Support alternate export lenses such as:
   - Common Approach
   - IRIS+
   - SDG
   - partner custom taxonomy

## Guardrails

1. Frontline staff should not be required to classify targets or metrics into external taxonomies during ordinary work.
2. AI suggestions must remain draft until approved.
3. Sensitive demographics must not be inferred from free-text notes.
4. Demographic mapping should rely on structured fields, explicit responses, and admin-reviewed crosswalks.
5. Local fallback identifiers must not be reported as external standards alignment.

## Suggested Build Order

1. Phase 2 — mapping data model
2. Phase 3 — batch suggestion jobs
3. Phase 4 — admin review queue
4. Phase 6 — reporting profiles and export integration
5. Phase 5 — conversational review

## Open Questions

1. Should partner-specific taxonomies reuse the existing `TaxonomyMapping` model or move to a more explicit classification model?
2. Which admin roles may approve mappings?
3. Should approved mappings be global, agency-specific, program-specific, or a mix?
4. How should intake-option demographic mappings be represented in the data model?
