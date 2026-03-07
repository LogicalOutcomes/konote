# CIDS Metadata Assignment Timing — Design Rationale Record

Task ID: CIDS-META1
Date: 2026-03-07
Status: Draft

---

## Problem

KoNote needs standards-aligned metadata for metrics, targets, and later reporting exports. The question is not only what metadata to store, but when it should be assigned.

If KoNote asks frontline staff to classify targets and metrics into external taxonomies during ordinary service work, it creates friction in note-taking and plan setup. In most nonprofits, the people who care about taxonomy alignment are the staff preparing funder, partner, board, or standards-based reports later.

At the same time, some metadata is safe and useful to assign immediately because it is deterministic and does not require interpretation.

The design problem is to separate:

1. metadata that should be assigned automatically at creation time
2. metadata that should only be assigned later through admin review, batch processing, or report-specific classification

## Decision

KoNote will assign only deterministic, low-burden metadata when a metric or target is created.

KoNote will delay interpretive taxonomy mapping and report-specific classification until a later admin-facing workflow, typically batch preparation for reporting.

Creation-time metadata is for identity, provenance, and direct carry-through from what the user already entered.

Deferred metadata is for categorisation, crosswalks, and external reporting lenses such as Common Approach code lists, IRIS+, SDGs, and partner-specific taxonomies.

## What Gets Assigned Immediately

### Targets

When a target is created, KoNote may assign:

1. A stable local outcome identifier.
   Example: a local URN used as the target's outcome URI.

This is appropriate because it is mechanical, requires no judgement, and gives KoNote a stable internal identifier even when no external mapping exists yet.

### Metrics

When a metric is created, KoNote may assign:

1. A stable local indicator identifier.
   Example: a local URN used as the metric's indicator URI.

2. A local `defined_by` value when no external standard was explicitly selected.
   Example: a local organisation URI.

3. A simple unit carry-through.
   If the user entered a plain-language unit such as `days`, `sessions`, `score`, `%`, or `$`, KoNote may copy that into a human-readable CIDS unit description field.

4. Any explicit external reference deliberately chosen by the creator.
   Example: if an admin explicitly picks an IRIS+ code while creating the metric, KoNote may store it immediately.

5. Operational metric structure that is required for ordinary use.
   Examples: metric type, minimum and maximum values, achievement options, instrument name, assessment schedule.

These fields are part of how the metric works in practice. They are not reporting classifications.

## What Gets Delayed

The following metadata should generally be delayed to a later admin workflow:

1. External taxonomy mapping inferred by AI.
   Example: guessing an IRIS+ code from a metric name.

2. SDG mapping.
   SDGs are broad, interpretive, and often depend on reporting purpose.

3. Detailed Common Approach category assignment when it requires judgement.
   A local target may fit several outcome categories depending on context.

4. Theme overrides or reporting-oriented theme selection.

5. Partner-specific or funder-specific crosswalks.

6. Baseline narrative text prepared for export.
   Baseline wording often depends on the reporting period or later analysis.

7. Normalisation into alternate code lists chosen later by the admin.
   Example: "use SDG instead of IRIS for this report."

## Why This Split

### 1. It protects frontline workflow

Frontline staff should not be asked to do taxonomy work while creating targets, metrics, or notes. Their job is to document service delivery and outcomes in practice language.

### 2. It matches how nonprofit reporting actually works

Classification is usually done by a reporting lead, evaluator, manager, or admin person near the reporting deadline, not by every worker at data-entry time.

### 3. It keeps immediate automation safe

Local identifiers and provenance are deterministic. They can be assigned without guessing.

### 4. It supports multiple reporting lenses

The same local target or metric may later need to be mapped differently for Common Approach, IRIS+, SDG, or a custom partner taxonomy. Delaying that layer avoids freezing one interpretation too early.

### 5. It makes batch AI practical

If classification is delayed, the AI does not need to be interactive or low-latency. It can run in batch, generate draft mappings, and support a later admin review process.

## Guardrails

1. AI-generated taxonomy mappings are draft suggestions until a human approves them.

2. Official exports should use approved mappings by default, not raw model guesses.

3. Sensitive demographic categories must not be inferred from free-text case notes.
   Demographic mapping should rely on structured intake fields, explicit participant responses, or admin-reviewed crosswalks.

4. A local fallback URI must not be treated as evidence of external standards alignment.
   Local identifiers are identity metadata, not proof of IRIS, SDG, or Common Approach categorisation.

## Anti-Patterns Rejected

| Approach | Why Rejected |
|----------|-------------|
| Asking frontline staff to classify each target or metric into external code lists during creation | Adds reporting burden to service delivery workflow |
| Treating local fallback URIs as if they were external taxonomy mappings | Overstates standards alignment and produces misleading coverage numbers |
| Assigning AI-guessed taxonomy codes automatically at save time | High risk of silent misclassification and hard-to-audit exports |
| Forcing a single taxonomy choice at creation time | Prevents later use of alternate reporting lenses such as SDG instead of IRIS |
| Inferring sensitive demographics from free-text notes | Privacy and governance risk; not defensible for nonprofit practice |

## Consequences

### Positive

1. Staff workflow stays simple.
2. KoNote always has stable local identifiers for metrics and targets.
3. Reporting classification can happen later in a dedicated admin review workflow.
4. The platform can support more than one external taxonomy without changing frontline data entry.
5. Batch AI becomes viable and cheaper to operate.

### Trade-offs

1. Standards alignment will be incomplete until the later review step is done.
2. Reporting prep requires an explicit review queue or batch process.
3. Some exports may contain only local identifiers until external mappings are approved.

## Implementation Implications

1. Keep automatic local metadata assignment on create/save for metrics and targets.

2. Treat IRIS+, SDG, Common Approach categorisation, and partner crosswalks as a separate layer.

3. Build a later admin workflow for batch suggestion, review, approval, and override of taxonomy mappings.

4. Support multiple mappings per local item so a single metric or target can be classified under different reporting systems.

5. Distinguish in code and reporting between:
   - local identity metadata
   - explicit human-approved external mappings
   - draft AI suggestions

## Current KoNote Direction

This DRR supports the current approach of assigning local fallback identifiers and basic provenance immediately for metrics and targets, while deferring deeper categorisation.

That means the following immediate assignments are in scope:

1. local indicator URI for metrics
2. local outcome URI for targets
3. local `defined_by` when no external standard is explicitly selected
4. carry-through of plain-language unit text into a human-readable description field

It also means the following should remain deferred unless explicitly chosen by an admin:

1. IRIS+ categorisation
2. SDG categorisation
3. Common Approach code-list categorisation that requires interpretation
4. theme override
5. partner-specific taxonomy mapping
