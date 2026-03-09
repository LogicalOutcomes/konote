# Evaluation Planning and Enrichment Workflow

Date: 2026-03-07
Status: Draft
Audience: KoNote product, implementation, and managed-service design

## Purpose

Define an end-to-end workflow that starts before KoNote is configured and continues through report export, validation, metadata enrichment, and cross-agency dashboarding.

## The workflow in plain language

1. An agency defines its evaluation framework before or during KoNote setup.
2. KoNote is configured to match that framework.
3. Staff use KoNote normally during service delivery.
4. The agency approves an aggregate report for a partner or funder.
5. A non-PII AI pipeline validates that report and enriches its metadata.
6. The enriched result supports partner exports, Full Tier CIDS output, and multi-agency dashboards.

## Stage A: Evaluation planning before implementation

This stage happens before the agency is fully live in KoNote.

### Inputs

1. program descriptions
2. grant applications or proposals
3. logic models, theories of change, or evaluation plans
4. funder reporting requirements
5. known risks and assumptions
6. any existing outcomes, indicators, or dashboard expectations

### Outputs

1. intervention model description
2. participant/cohort definitions
3. services and activities list
4. expected outputs
5. intended outcomes and outcome chains
6. draft risks, mitigations, and counterfactual assumptions
7. recommended metrics and reporting lenses
8. mapping of these concepts into KoNote setup elements

### AI role

AI assists with:

1. structuring messy planning material
2. drafting logic-model language
3. suggesting outputs and outcome chains
4. proposing risks and mitigations
5. proposing standard taxonomy mappings

### Human role

Humans can:

1. review and confirm the framework
2. edit parts they disagree with
3. skip review and accept the AI-generated planning package

Human review is recommended for complex elements, especially:

1. intervention descriptions
2. risk statements
3. mitigations
4. counterfactual language

But it is not mandatory.

## Stage B: KoNote configuration

The planning package should feed setup directly.

Examples:

1. program records inherit structured descriptions
2. metrics inherit draft code mappings
3. templates inherit known services and activities
4. partner report templates inherit schema expectations

This reduces later cleanup.

## Stage C: Operational use

During day-to-day use, staff should not be asked to do evaluation architecture work.

They keep doing:

1. notes
2. plans
3. metrics
4. events
5. reports

The evaluation framework sits behind the scenes.

## Stage D: Approved non-PII report export

Before any external AI call, the agency approves a report that is already suitable for partner sharing.

Requirements:

1. aggregate only
2. participant data removed
3. report approval recorded
4. recipient and purpose recorded
5. machine-readable export package created

## Stage E: Post-export validation

Non-AI checks run first.

Examples:

1. required sections exist
2. expected metrics are present
3. date ranges valid
4. suppression rules applied
5. export marked non-PII
6. CIDS payload parses
7. SHACL validation attempted where supported

## Stage F: AI enrichment

Only after the report is proven safe does AI enrich it.

### What AI can enrich

1. taxonomy mappings
2. intervention labels
3. program/service/activity/input/output descriptions
4. impact model summaries
5. stakeholder framing
6. risk and mitigation descriptions
7. counterfactual wording
8. dashboard category alignment

### Model policy

1. use standard/local models for simpler tasks
2. escalate automatically to a frontier API for the most complex planning and metadata tasks
3. store provenance for every generated field

## Stage G: Quality ladder

Not all enriched metadata is equal.

The system should reflect that.

### Suggested quality states

1. AI-generated
2. AI-generated and deterministic checks passed
3. human-confirmed
4. manually authored

This lets the system recommend better practices without blocking agencies.

## Stage H: Multi-instance managed service

For umbrella funders or shared dashboarding programs, use a central service.

### Local instance responsibilities

1. hold participant data locally
2. build the non-PII package
3. submit only safe artifacts
4. receive enriched metadata back

### Central service responsibilities

1. store partner schemas
2. store shared prompts and ontology mappings
3. run validation and enrichment
4. maintain reusable planning profiles
5. return structured results for dashboard rollups

## Prosper Canada fit

This workflow fits Prosper Canada in two ways.

### During onboarding

It helps agencies define:

1. intervention types
2. intended outcomes
3. service/output structures
4. shared reporting expectations

### During reporting

It helps generate consistent metadata across agencies after report approval.

That produces cleaner cross-agency dashboarding without centralising participant data.

## What should be built first

### First build

1. planning package schema
2. canonical non-PII report artifact
3. deterministic validation layer
4. enrichment result storage linked to approved exports

### Second build

1. planning UI and review flow
2. AI enrichment service client
3. provenance and quality-state tracking

### Third build

1. managed central service for opted-in agencies
2. shared partner profiles
3. shared planning templates
4. dashboard rollup consumption

## Key principle

The planning work and the enrichment work are connected, but they are not the same.

Planning creates better source structure.
Enrichment validates and improves what comes out later.

If both exist, Full Tier metadata quality gets much better.