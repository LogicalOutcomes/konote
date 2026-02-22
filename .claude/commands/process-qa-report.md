# Process QA Report: Expert Panel Review

Reviews the latest satisfaction report and improvement tickets from the konote-qa-scenarios evaluation. Produces an action plan with prioritised fixes for TODO.md.

**This is Pipeline A, Step 3** — run after `/run-scenarios` deposits handoff files in `qa/`.

---

## Before running: verify handoff files exist

Read `qa/pipeline-log.txt`. The last entry should say "Step 2: Evaluation complete" with no subsequent "Step 3" entry. If Step 3 is already done for this round, STOP — the report has already been processed.

Check that `qa/` contains:
- Improvement tickets file for this round (e.g. `qa/2026-02-21-improvement-tickets.md`)
- `qa/satisfaction-history.json`
- `qa/pipeline-log.txt`

If these are missing, STOP and tell the user:
> The handoff files from `/run-scenarios` are not in `qa/`. Run `/run-scenarios` in the konote-qa-scenarios repo first.

## Steps

### Step 1: Read the latest improvement tickets

Find the most recent `*-improvement-tickets.md` file in `qa/`. Read it fully — this contains all tickets from the evaluation round.

### Step 2: Read the satisfaction history

Read `qa/satisfaction-history.json` for trend data across rounds.

### Step 3: Read the pipeline log

Read `qa/pipeline-log.txt` for context on what was captured and evaluated.

### Step 4: Convene expert panel review

Analyse the tickets and produce an action plan:
- Group tickets by severity (BLOCKER, BUG, IMPROVE, TEST)
- Identify regressions (scores that dropped 0.5+ pts from previous round)
- Prioritise into tiers: Tier 1 (fix now), Tier 2 (fix soon), Tier 3 (backlog)
- Write the action plan to `tasks/qa-action-plan-YYYY-MM-DD.md`

### Step 5: Update TODO.md

Add Tier 1 tasks to Active Work, Tier 2 to Coming Up, Tier 3 to Parking Lot.

### Step 6: Update the pipeline log

Append a "Step 3" entry to `qa/pipeline-log.txt`:
```
YYYY-MM-DD HH:MM — Step 3: Action plan created, N tasks added to TODO (M tickets analysed, 4-expert panel). See tasks/qa-action-plan-YYYY-MM-DD.md.
```

### Next steps

Tell the user:
1. Pipeline A is complete for this round
2. If Pipeline B (page audit) is needed, run `/capture-page-states` next
3. Review the action plan at `tasks/qa-action-plan-YYYY-MM-DD.md`
