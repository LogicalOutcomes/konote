# Process QA Report: Expert Panel Review

Reviews the latest satisfaction report and improvement tickets from the konote-qa-scenarios evaluation. Produces an action plan with prioritised fixes for TODO.md.

**This is Pipeline A, Step 3** — run after `/run-scenarios` deposits handoff files in `qa/`.

---

## Before running: verify handoff files exist

Read `qa/pipeline-log.txt`. The last entry **MUST** say "Step 2: Evaluation complete" with no subsequent "Step 3" entry.

**Hard gates (STOP if any fail):**
1. If Step 3 is already done for this round, STOP — the report has already been processed.
2. If there is no Step 2 entry for this round, STOP and tell the user:
   > There is no Step 2 (evaluation) entry in the pipeline log for this round. The improvement tickets file may exist, but without a logged evaluation, the ticket provenance is unclear. Run `/run-scenarios` in the konote-qa-scenarios repo first, or manually add the Step 2 entry if the evaluation was done outside the pipeline.
3. If the improvement tickets file, `qa/satisfaction-history.json`, or `qa/pipeline-log.txt` are missing, STOP and tell the user:
   > The handoff files from `/run-scenarios` are not in `qa/`. Run `/run-scenarios` in the konote-qa-scenarios repo first.

## Steps

### Step 1: Read the latest improvement tickets

Find the most recent `*-improvement-tickets.md` file in `qa/`. Read it fully — this contains all tickets from the evaluation round.

### Step 2: Read the satisfaction history

Read `qa/satisfaction-history.json` for trend data across rounds.

### Step 3: Read the pipeline log

Read `qa/pipeline-log.txt` for context on what was captured and evaluated.

### Step 4: Cross-reference completed work (MANDATORY)

**Before analysing any tickets**, read these sources to identify what has already been fixed:

1. **`qa/fix-log.json`** — persistent record of ticket resolutions. Any ticket matching a known fix should be labelled "VERIFY" (check if fix has regressed) rather than "FIX NOW".
2. **Recently Done section of `TODO.md`** — items completed since the last QA round.
3. **`tasks/ARCHIVE.md`** — older completed items that have rolled off Recently Done. Search for QA-related completions (grep for "QA-R", "TIER", "BUG-", "BLOCKER-", etc.).

For each ticket in the improvement file, check whether it matches a known fix. If it does, classify it as:
- **VERIFY** — the fix exists, check if it has regressed or if the evaluation tested stale code
- **NEW** — no previous fix exists for this issue

Include a "Previously Fixed (Verify)" section in the action plan showing which tickets match known fixes.

### Step 5: Convene expert panel review

Analyse the tickets and produce an action plan. Follow the format of the most recent `tasks/qa-action-plan-*.md` file for consistency across rounds.

- Group tickets by severity (BLOCKER, BUG, IMPROVE, TEST)
- Separate genuinely NEW tickets from VERIFY tickets
- Identify regressions (scores that dropped 0.5+ pts from previous round)
- Prioritise into tiers: Tier 1 (fix now), Tier 2 (fix soon), Tier 3 (backlog)
- Within Tier 1, separate "Fix" items (genuinely new) from "Verify" items (previously fixed)
- Write the action plan to `tasks/qa-action-plan-YYYY-MM-DD.md`

### Step 6: Update TODO.md

Add Tier 1 tasks to Active Work, Tier 2 to Coming Up, Tier 3 to Parking Lot. Flag any items that match GK's consultation gates (see CLAUDE.md § "Consultation Gates") with "GK reviews [topic]" in the owner field.

**For VERIFY items:** prefix with "Verify:" in TODO.md so future sessions know to check before re-implementing.

### Step 7: Update the fix log

If any tickets from a previous round are confirmed fixed (based on the evaluation showing improved scores), update their `verified_date` in `qa/fix-log.json`.

### Step 8: Update the pipeline log

Append a "Step 3" entry to `qa/pipeline-log.txt`:
```
YYYY-MM-DD HH:MM — Step 3: Action plan created, N tasks added to TODO (M tickets analysed, K previously fixed, 4-expert panel). See tasks/qa-action-plan-YYYY-MM-DD.md.
```

**Verification:** After writing the entry, recount the actual tasks added to each section of TODO.md and confirm the number matches what you wrote. Fix any discrepancy before finishing.

### Next steps

Tell the user:
1. Pipeline A is complete for this round
2. **Run `/capture-page-states` next** to start Pipeline B (page audit). This is the standard next step after every Pipeline A completion.
3. Review the action plan at `tasks/qa-action-plan-YYYY-MM-DD.md`
