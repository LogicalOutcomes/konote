# Recurring Tasks

Chores to run periodically. This file keeps the full run instructions; TODO.md keeps only one-line reminders.

## Start Here (for teammates)

- If you are not sure where to start, run **UX Walkthrough (UX-WALK1)** first.
- Run **Full QA Suite (QA-FULL1)** after larger releases or when multiple UI areas changed.
- Use **Code Review (REV1)** before production deployment or at least every 2–4 weeks.
- If a TODO item says “see recurring tasks,” this file is the source of truth for commands.

## Tool and Repo Quick Guide

- **Claude Code slash commands available?** Use the command flow in this file directly.
- **Using Kilo Code or another tool without slash commands?** Use the “Kilo Code alternative” steps below.
- **konote-app repo:** run capture/server commands here.
- **konote-qa-scenarios repo:** run evaluation commands here.
- If in doubt, verify your folder before running commands.

| Task | When | How |
|------|------|-----|
| Agency Permissions Interview | Before every new agency deployment | Complete interview, get ED sign-off on Configuration Summary. See `tasks/agency-permissions-interview.md` (ONBOARD-RECUR) |
| UX walkthrough | After UI changes | Run `pytest tests/ux_walkthrough/ -v`, then review `tasks/ux-review-latest.md` (UX-WALK1) |
| French translation review | After adding strings | Have a French speaker spot-check. Run `python manage.py check_translations` (I18N-REV1) |
| Redeploy to Railway | After merging to main | Push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1) |
| Redeploy to FullHost | After merging to main | Push to `main`, trigger redeploy. See `docs/deploy-fullhost.md` (OPS-FH1) |
| Code review | Periodically | Open Claude Code and run a full review prompt. See `tasks/code-review-process.md` (REV1) |

## UX Walkthrough (UX-WALK1)

1. Run `pytest tests/ux_walkthrough/ -v`
2. Open `tasks/ux-review-latest.md`
3. Add resulting fixes to TODO.md (Active Work if immediate, Parking Lot if deferred)

Expected outcome: updated `tasks/ux-review-latest.md` plus actionable follow-up items in TODO.md.

## Full QA Suite (QA-FULL1)

Run after major releases or substantial UI changes.

Expected outcome: new dated reports in `qa-scenarios/reports/` and a prioritised fix list.

There are **two independent pipelines**. Do them in order. Each pipeline is a sequence of sessions — finish one step before starting the next.

### Pipeline A: Scenario Evaluation (always do this)

Scores how real personas experience the app across 65+ scripted workflows.

| Step | Session | Repo | Command | Prompt for Claude Code |
|------|---------|------|---------|----------------------|
| A1 | 1 | konote-app | Manual (see prompt below) | Capture scenario screenshots |
| A2 | 2 | konote-qa-scenarios | `/run-scenarios` | Evaluate screenshots, produce satisfaction report |
| A3 | 3 | konote-app | `/process-qa-report` | Expert panel review, action plan |

**A1 prompt** (paste into a new konote-app session):
```
Pull latest main, run migrations, re-seed demo data, then run the scenario evaluation suite:

git fetch origin main && git checkout main && git pull origin main
python manage.py migrate && python manage.py migrate --database=audit
python manage.py seed && python manage.py seed_demo_data --demo-mode --force

SCENARIO_HOLDOUT_DIR="c:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios" \
  python -m pytest tests/scenario_eval/test_scenario_eval.py -v --no-llm

Report: how many passed/failed/skipped, how many screenshots captured.
```

**A2 prompt** (paste into a new konote-qa-scenarios session):
```
Fresh screenshots were captured today. Run /run-scenarios for the full evaluation — all scenarios, not just the smoke subset. Update TODO.md with results.
```

**A3 prompt** (paste into a new konote-app session):
```
Run /process-qa-report on the latest satisfaction report from konote-qa-scenarios.
```

### Pipeline B: Page Audit (do after Pipeline A)

Scores individual pages against Nielsen heuristics. Uses different screenshots than Pipeline A.

| Step | Session | Repo | Command | Prompt for Claude Code |
|------|---------|------|---------|----------------------|
| B1 | 4 | konote-app | `/capture-page-states` | Capture page-state screenshots |
| B2 | 5 | konote-qa-scenarios | `/run-page-audit` | Evaluate page screenshots, produce audit report |

**B1**: Run `/capture-page-states` in a konote-app session.
**B2**: Run `/run-page-audit` in a konote-qa-scenarios session.

### Summary: session order

1. **konote-app** — A1: capture scenario screenshots
2. **konote-qa-scenarios** — A2: evaluate scenarios
3. **konote-app** — A3: process QA report
4. **konote-app** — B1: capture page states
5. **konote-qa-scenarios** — B2: page audit

Each step must finish before the next starts. Each step is a separate Claude Code session.

### Kilo Code alternative (if slash commands are unavailable)

Follow the same session order. Instead of slash commands, read and follow:
- A1: use the prompt above
- A2: `.claude/commands/run-scenarios.md` (in qa-scenarios repo)
- A3: `.claude/commands/process-qa-report.md` (in konote-app)
- B1: `.claude/commands/capture-page-states.md` (in konote-app)
- B2: `.claude/commands/run-page-audit.md` (in qa-scenarios repo)

### PowerShell subset runs (in konote-app repo)

```powershell
$env:SCENARIO_HOLDOUT_DIR = "C:\Users\gilli\OneDrive\Documents\GitHub\konote-qa-scenarios"
# Calibration only
pytest tests/scenario_eval/ -v --no-llm -k "calibration"
# Smoke test (6 scenarios)
pytest tests/scenario_eval/ -v --no-llm -k "smoke"
# Single scenario
pytest tests/scenario_eval/ -v --no-llm -k "SCN_010"
```

All reports save to `qa-scenarios/reports/` with date stamps.
