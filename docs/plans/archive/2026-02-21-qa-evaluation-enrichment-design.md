# QA Evaluation Enrichment Design

**Date:** 2026-02-21
**Status:** Draft — pending approval
**Scope:** Both `konote-app` and `konote-qa-scenarios` repos

## Problem

Despite 66 QA scenarios with detailed personas, the team still encounters bugs and poorly designed forms during real use. The scenarios were meant to replace tedious manual page-by-page testing, but they're not catching what matters.

**Root cause diagnosis (expert panel):** The current system evaluates *appearance, not behaviour*. The LLM scores screenshots of pages but never actually submits forms, triggers validation errors, or verifies that data saves. The bugs being found manually are behavioural — they only appear when you interact.

**Secondary issue:** Persona judgment is shallow. Rich persona profiles (ADHD, screen reader, executive time pressure) are passed to the LLM as context text, but the scoring dimensions are generic. A 3.2 score for Casey doesn't distinguish "missing button label" from "information density intolerable for ADHD."

**Brittleness concern:** Previous QA iterations bogged down because the system was too complex. Any enrichment must stay within a 30-minute monthly maintenance budget and produce output a non-technical team member can act on.

## Design: Two Tracks

### Track A: Quick Check (catches bugs)

**Purpose:** Verify that core workflows actually function — forms submit, data saves, errors are handled, permissions are enforced.

**Technology:** Standard Playwright Python tests using pytest. No YAML, no custom DSL, no LLM.

**When to run:** Every PR, every deploy, anytime someone asks "is it working?"

**Runtime target:** Under 10 minutes.

**Output:** Traffic-light summary.

```
QA Quick Check — 2026-02-21 — YELLOW

GREEN (working):
  + Login and navigation (all roles)
  + Client/participant search
  + Progress notes (create, edit, delete)
  + Dashboard loads for all roles

YELLOW (issues found):
  ! Survey form: submit button doesn't show confirmation
  ! French alerts: text shows English

RED (broken):
  (none)

15 passed, 2 warnings, 0 failures
```

**File location:** `tests/scenario_eval/test_interactions.py`

**What gets tested (initial 15 workflows):**

| # | Workflow | What's verified |
|---|---------|----------------|
| 1 | Login (each role) | Correct dashboard, no errors |
| 2 | Participant search | Results appear, no clinical data for receptionist |
| 3 | Create participant | Form saves, redirects to profile, record exists |
| 4 | Create progress note | Form saves, confirmation shown, note appears in list |
| 5 | Note validation error | Error message shown, input preserved, nothing saved |
| 6 | Edit existing note | Changes saved, confirmation shown |
| 7 | Create goal/plan | Form saves, goal appears on participant profile |
| 8 | Record metric value | Value saved, appears in target display |
| 9 | Submit survey (staff) | Responses saved, confirmation shown |
| 10 | Submit survey (portal) | Auto-save works, submission confirmed |
| 11 | Permission denial | 403 page is styled, helpful message, no data leaked |
| 12 | French language UI | lang="fr" set, French text appears, no English bleed |
| 13 | Session timeout recovery | After idle, form data preserved or helpful message |
| 14 | Funder report generation | Report generates, download link works |
| 15 | Admin settings change | Terminology saves, reflected across app |

**Test style:** Loose verification to reduce brittleness.

```python
# GOOD: text-based, resilient to template changes
expect(page.locator("text=Note saved")).to_be_visible()
expect(page).to_have_url(re.compile(r"/notes/"))

# BAD: selector-coupled, breaks on any template refactor
expect(page.locator("#success-toast .message")).to_have_text("Note saved successfully")
expect(page).to_have_url("/participants/12/notes/?created=true")
```

**Entry point:** `python manage.py qa_check` (management command wrapping pytest).

### Track B: Full Evaluation (judges quality)

**Purpose:** Persona-driven judgment of interface quality, usability, and experience — the "would Casey succeed?" question.

**Technology:** Existing YAML scenario + Playwright capture + LLM evaluation pipeline, enriched.

**When to run:** Monthly or before releases.

**Runtime target:** 30-60 minutes (with LLM), 5-10 minutes (screenshot-only).

**Output:** Satisfaction report with traffic-light summary on top.

#### Enrichment 1: Health Check Before Evaluation

Before any scenario runs, the runner performs a health check:

- Can each scenario URL resolve? (catches stale URLs like TEST-21)
- Does referenced test data exist? (catches fixture sync issues)
- When was each scenario YAML last updated vs. the app page?

If >20% of scenarios fail health check, the run aborts with a "suite is stale" message instead of producing meaningless scores.

**File location:** New function in `tests/scenario_eval/scenario_runner.py`

#### Enrichment 2: Task Outcome Field

Add a new LLM output field alongside the existing 7 dimension scores:

```json
{
  "task_outcome": "independent",
  "task_outcome_reasoning": "Casey could complete this without help — form is simple, confirmation is clear"
}
```

**Four outcome levels:**

| Outcome | Meaning | Report colour |
|---------|---------|--------------|
| `independent` | Persona completes without help | Green |
| `assisted` | Persona would need to ask a colleague | Yellow |
| `abandoned` | Persona gives up or works around the system | Orange |
| `error_unnoticed` | Persona thinks they're done but entered incorrect data | Red |

This is the single most diagnostic addition — it captures "would this actually work for frontline staff?" as a binary judgment, not a numeric score.

**Where it goes:** Added to the LLM evaluation prompt, reported as a headline metric per scenario.

#### Enrichment 3: One-Line Persona Scoring Instruction

Instead of per-dimension-per-persona rubrics (maintenance nightmare), each persona gets ONE scoring instruction that the LLM must apply across all dimensions:

```yaml
# In persona YAML
scoring_instruction: >
  Casey has ADHD (inattentive type). Penalise any page with more than
  5 competing visual elements, unclear error messages, or auto-disappearing
  notifications. She blames herself for errors — if an error message
  doesn't say "this isn't your fault," deduct from Confidence and
  Error Recovery.
```

```yaml
scoring_instruction: >
  Margaret is an executive with a 5-minute daily KoNote budget. Score
  Efficiency based on "can she get her answer in under 90 seconds?"
  not on raw click count. If the dashboard requires scrolling to find
  key numbers, deduct from Clarity.
```

```yaml
scoring_instruction: >
  Amara uses JAWS screen reader and keyboard-only navigation. Score
  Clarity based on JAWS announcement sequence, not visual layout.
  Score Confidence based on whether aria-live regions confirm actions.
  If Tab order is illogical, deduct from Efficiency.
```

**How it's used:** Injected into the LLM prompt as a MUST-APPLY rule:

```
PERSONA-SPECIFIC SCORING RULE (you MUST apply this):
[scoring_instruction from persona YAML]
```

**Maintenance cost:** One sentence per persona. Update when persona profile changes. No cross-referencing with dimension definitions.

#### Enrichment 4: Interaction Test Gate

Each evaluation scenario can optionally reference its Quick Check counterpart:

```yaml
# In scenario YAML
id: SCN-010
interaction_test: "test_interactions::test_morning_intake"
```

If the referenced interaction test is currently failing, the evaluation is skipped and reported as `BLOCKED — interaction test failing` instead of producing a meaningless score on a broken page.

**This connects the two tracks** without coupling them tightly. Track A runs independently. Track B optionally checks Track A before scoring.

#### Enrichment 5: Traffic-Light Summary on Reports

Add a summary section at the top of every satisfaction report:

```
EVALUATION SUMMARY — 2026-02-21 — YELLOW

Scenarios run: 52/66 (14 stale, skipped)
Interaction tests: 13/15 passing

TASK OUTCOMES:
  Independent: 38 scenarios (73%)
  Assisted:     8 scenarios (15%)
  Abandoned:    4 scenarios (8%)
  Error:        2 scenarios (4%)

TOP CONCERNS:
  1. Survey form — Casey would abandon (no confirmation after submit)
  2. Admin settings — Morgan needs help (terminology page is confusing)
  3. French alerts — Jean-Luc would enter wrong data (English text misleads)

PERSONA HEALTH:
  Casey (DS1):    3.8 avg — mostly independent
  Amara (DS3):    3.2 avg — assisted on 3 workflows
  Margaret (E1):  4.1 avg — independent
  Dana (R1):      2.9 avg — abandoned 2 workflows
  Morgan (PM1):   3.5 avg — assisted on settings
```

### Missing Scenarios to Add

#### Priority 1: Surveys (8 scenarios)
Already designed in `tasks/qa-survey-scenarios.md` (SCN-110 through SCN-117).

| ID | Scenario | Personas |
|---|---------|---------|
| SCN-110 | Admin creates survey with sections and questions | PM1 |
| SCN-111 | CSV import of standardised instrument (PHQ-9) | PM1 |
| SCN-112 | Staff assigns survey to participant | DS1 |
| SCN-113 | Participant completes survey via portal | (new: Participant persona) |
| SCN-114 | Staff reviews survey responses | DS1, PM1 |
| SCN-115 | Trigger rule auto-assigns survey | PM1 |
| SCN-116 | Shareable link survey completion | (anonymous) |
| SCN-117 | Survey permission boundaries | R1 (denied), DS1 (scoped) |

#### Priority 2: Admin Workflows (6 scenarios)

| ID | Scenario | Personas |
|---|---------|---------|
| SCN-120 | Terminology customisation | Admin |
| SCN-121 | Feature toggle enable/disable | Admin |
| SCN-122 | User invite and role assignment | Admin |
| SCN-123 | Audit log search and export | Admin, PM1 |
| SCN-124 | Report template upload and config | Admin |
| SCN-125 | Custom field configuration | Admin, PM1 |

#### Priority 3: Portal Participant View (5 scenarios)

| ID | Scenario | Personas |
|---|---------|---------|
| SCN-130 | Participant first login (cold start) | Participant |
| SCN-131 | Participant views goals and progress | Participant |
| SCN-132 | Participant writes journal entry | Participant |
| SCN-133 | Participant sends message to worker | Participant |
| SCN-134 | Participant completes "Questions for You" | Participant |

#### Priority 4: Interruption & Error Recovery (4 scenarios)

| ID | Scenario | Personas |
|---|---------|---------|
| SCN-140 | Session timeout mid-note (does data survive?) | DS1 |
| SCN-141 | Back button after form submit (double-submit?) | DS1 |
| SCN-142 | Friday catch-up (5 notes in 30 minutes) | DS1 |
| SCN-143 | Wrong client selected (correct after submit) | DS1 |

#### New Persona Needed: Participant

```yaml
# New persona for portal scenarios
P1:
  name: "Aisha"
  role: "Participant"
  title: "Program participant using the portal"
  agency: "Accessing services from home"
  tech_comfort: "low"
  language: "English"
  device: "Phone (Android, Chrome)"

  background: >
    Aisha is a 28-year-old participant in a housing stabilisation program.
    She accesses the portal on her phone, usually on the bus or at home.
    She's nervous about technology and worried about who can see her information.

  frustrations:
    - "Small text on phone screen"
    - "Not knowing if her worker got the message"
    - "Confusing medical or legal terminology"
    - "Being asked to create yet another password"

  mental_model: >
    Compares to texting and social media. Expects instant feedback.
    Doesn't understand why she can't just text her worker directly.

  scoring_instruction: >
    Aisha uses a phone with low tech comfort. Score Clarity based on
    mobile readability (font size, touch targets, scroll length).
    Score Confidence based on whether she knows her information is
    private and her worker received her input. If any step requires
    understanding system terminology, deduct from Clarity.
```

#### New Persona Needed: System Administrator

```yaml
ADMIN1:
  name: "Priya"
  role: "System Administrator"
  title: "KoNote system administrator"
  agency: "Manages KoNote for the organisation"
  tech_comfort: "high"
  language: "English"
  device: "Desktop (Windows, Chrome)"

  background: >
    Priya is the designated KoNote administrator for a mid-size agency.
    She's tech-comfortable but not a developer. She configures the system,
    manages users, and runs reports. She does admin tasks 2-3 times per week,
    not daily — she forgets where things are between sessions.

  frustrations:
    - "Settings scattered across different pages"
    - "No confirmation that a change took effect across the system"
    - "Can't tell which settings are agency-wide vs. program-specific"
    - "Audit log is a wall of text with no filtering"

  mental_model: >
    Expects settings to work like Google Workspace admin console —
    one place for everything, clear labels, immediate confirmation.

  scoring_instruction: >
    Priya is tech-comfortable but uses admin features infrequently.
    Score Clarity based on whether settings are discoverable without
    remembering where they are. Score Feedback based on whether changes
    are confirmed as applied system-wide. If the admin interface feels
    like a developer tool, deduct from Confidence.
```

### Incident-to-Scenario Pipeline

When the team finds a bug during manual use:

1. Record in a lightweight template:
   ```
   Date: 2026-02-21
   Found by: Gillian
   What happened: Submitted a note but no confirmation appeared. Wasn't sure if it saved.
   Page: /participants/12/notes/add/
   Role: Staff
   Expected: "Note saved" confirmation
   ```

2. This becomes a Quick Check interaction test (Track A) — 5-minute task.
3. Optionally, if it reveals a persona judgment gap, add to an evaluation scenario (Track B).

Over time, the test suite reflects real problems encountered by real users rather than hypothetical scenarios.

## Brittleness Prevention Rules

1. **Interaction tests are Python, not YAML.** Standard Playwright, standard pytest. Breaks are obvious and fixable.
2. **Health check before evaluation.** Stale scenarios get flagged, not silently scored.
3. **Loose verification.** Text matching, not CSS selectors. `url_contains`, not `url_equals`.
4. **One persona instruction, not seven dimension rules.** One sentence per persona, update when profile changes.
5. **Traffic-light output first.** Detailed scores for developers. Summary for everyone else.
6. **30-minute monthly maintenance budget.** If updating scenarios after an app change takes longer, the design is too coupled.

## Implementation Scope

### Changes to `konote-app`

| File | Change |
|------|--------|
| `tests/scenario_eval/test_interactions.py` | **New** — 15 Playwright interaction tests |
| `apps/core/management/commands/qa_check.py` | **New** — `python manage.py qa_check` entry point |
| `tests/scenario_eval/scenario_runner.py` | **Modify** — add health check before evaluation |
| `tests/scenario_eval/llm_evaluator.py` | **Modify** — add task_outcome field and persona scoring_instruction to prompt |
| `tests/scenario_eval/report_generator.py` | **Modify** — add traffic-light summary and task outcome reporting |

### Changes to `konote-qa-scenarios`

| File | Change |
|------|--------|
| `personas/participant.yaml` | **New** — Aisha (P1) persona |
| `personas/administrator.yaml` | **New** — Priya (ADMIN1) persona |
| `personas/staff.yaml` | **Modify** — add `scoring_instruction` to each persona |
| `personas/executive.yaml` | **Modify** — add `scoring_instruction` |
| `personas/program-manager.yaml` | **Modify** — add `scoring_instruction` |
| `personas/receptionist.yaml` | **Modify** — add `scoring_instruction` |
| `scenarios/surveys/SCN-110–117.yaml` | **New** — 8 survey scenarios |
| `scenarios/admin/SCN-120–125.yaml` | **New** — 6 admin scenarios |
| `scenarios/portal/SCN-130–134.yaml` | **New** — 5 portal participant scenarios |
| `scenarios/edge-cases/SCN-140–143.yaml` | **New** — 4 interruption scenarios |
| `tasks/ref/scoring.md` | **Modify** — add task_outcome definitions |
| `tasks/ref/incident-template.md` | **New** — incident-to-scenario template |

## Not In Scope

- Automated DITL narratives (keep manual — too complex to automate robustly)
- Per-dimension-per-persona scoring rubrics (one-line instruction is sufficient)
- Verification blocks in YAML (interaction testing is Python, not YAML)
- Self-healing URL resolution (flag stale, don't auto-fix — too risky)
- Real-time monitoring or CI integration (future work if needed)
