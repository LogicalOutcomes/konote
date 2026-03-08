# CIDS Batch Classification Workflow — Design Rationale Record

Task ID: CIDS-CLASSIFY1
Date: 2026-03-07
Status: Draft

---

## Problem

KoNote needs a practical way to classify local metrics, targets, programs, and structured demographic values into external reporting taxonomies.

That classification work is important for funder and partner reporting, but it does not belong in frontline documentation workflows. Staff writing notes or setting up goals should not have to perform taxonomy review while serving participants.

At the same time, agencies may need more than one reporting lens. The same local item may need to be expressed differently for Common Approach, IRIS+, SDG, or a custom partner taxonomy.

The design problem is how to:

1. support batch AI-assisted classification without burdening frontline staff
2. allow an admin or reporting lead to review and refine the results
3. support more than one taxonomy for the same local item

## Decision

KoNote will use an admin-facing batch classification workflow.

The workflow will generate draft suggestions asynchronously and store them separately from approved mappings.

An admin, evaluator, or reporting lead will review those drafts, approve or reject them, and use approved mappings when producing official exports.

KoNote will support multiple taxonomy systems for the same local item.

## Core Workflow

### Step 1: Frontline work happens normally

Staff create notes, targets, metrics, attendance records, and intake responses in practice language.

### Step 2: KoNote identifies items needing classification

Examples:

1. new targets
2. new metrics
3. new intake answer options
4. changed program descriptions
5. items with no approved mapping for the current report taxonomy

### Step 3: A batch job creates draft suggestions

The suggestion engine may use rules, code-list narrowing, and AI to propose likely mappings.

These remain draft suggestions only.

### Step 4: Admin reviews a classification queue

The admin sees:

1. original local wording
2. suggested code and label
3. taxonomy system
4. confidence
5. rationale
6. alternate suggestions where available

### Step 5: Admin may interrogate the AI

The admin may ask follow-up questions such as:

1. why was this classified here?
2. what are the alternatives?
3. show this using SDG instead of IRIS
4. collapse these items into broader categories for a board report

### Step 6: Only approved mappings are used by default in official reports

Draft suggestions are not official until explicitly approved.

## Why Batch Instead of Live Suggestions

### 1. Better fit for nonprofit workflow

The people responsible for taxonomy alignment are usually reporting leads, evaluators, managers, or admins, not frontline workers.

### 2. Lower performance pressure

Batch processing means the LLM does not need to be instant. KoNote can use slower, more careful prompts and asynchronous jobs.

### 3. More coherent classification

Batch review allows the system and the admin to look at sets of related items together instead of guessing one item at a time in isolation.

### 4. Easier support for alternate taxonomies

If an admin later says "use SDG instead of IRIS," batch classification and review make that feasible without changing frontline data entry.

## Multiple Taxonomy Lenses

KoNote will treat taxonomy systems as reporting lenses, not as a single permanent truth.

Examples of supported lenses:

1. Common Approach
2. IRIS+
3. SDG
4. partner-specific taxonomy

The same local item may have more than one approved mapping, one per taxonomy system.

## Required State Separation

KoNote must keep these states separate:

1. local service data
2. local identity metadata
3. draft AI suggestions
4. approved external mappings

This separation prevents silent promotion of guesses into official reporting outputs.

## Demographics Rule

Demographic mapping should be stricter than outcome or metric mapping.

For demographics:

1. use structured intake fields and answer options as the source
2. allow admin-reviewed crosswalks
3. do not infer sensitive demographic classifications from free-text case notes

## Guardrails

1. AI suggestions are draft until approved.
2. Frontline staff are not required to do taxonomy work during service delivery.
3. Official exports use approved mappings by default.
4. Admin may change taxonomy lens per report.
5. A single local item may carry several approved mappings under different systems.

## Anti-Patterns Rejected

| Approach | Why Rejected |
|----------|-------------|
| Live taxonomy prompting during frontline note-taking or target entry | Interrupts service workflow and assigns reporting work to the wrong role |
| Storing only one taxonomy per local item | Fails when a funder or partner asks for SDG instead of IRIS, or another custom view |
| Treating AI output as official automatically | Too risky for auditability and reporting accuracy |
| Inferring sensitive demographics from free-text notes | Privacy and governance risk |
| Requiring the LLM to be interactive and low-latency for this feature | Unnecessary cost and complexity for a back-office task |

## Consequences

### Positive

1. Frontline workflow stays clean.
2. Reporting staff get a focused review workspace.
3. KoNote can support more than one reporting taxonomy.
4. The AI can run asynchronously and more cheaply.
5. Mapping decisions become auditable.

### Trade-offs

1. Additional workflow is needed before a fully classified export is available.
2. The platform needs queue, job, and approval concepts.
3. Some reports may remain partially unmapped until admin review is complete.

## Implementation Implications

1. Add draft and approved mapping states.
2. Add asynchronous classification jobs.
3. Build an admin review queue.
4. Add conversational interrogation for admin refinement.
5. Support report profiles that select a taxonomy lens.
