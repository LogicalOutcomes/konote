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

Expected outcome: new dated reports in `qa-scenarios/reports/` and a prioritized fix list.

### Claude Code command flow

1. **konote-app:** `/run-scenario-server` (captures scenario screenshots)
2. **qa-scenarios:** `/run-scenarios` (evaluates scenarios, creates satisfaction report + improvement tickets)
3. **konote-app:** `/capture-page-states` (captures page screenshots)
4. **qa-scenarios:** `/run-page-audit` (evaluates pages, creates page-audit report + tickets)
5. *(Optional)* **konote-app:** `/process-qa-report` (expert panel synthesis + action plan)

### Kilo Code alternative (if slash commands are unavailable)

1. Read and follow `.claude/commands/run-scenarios.md`
2. Read and follow `.claude/commands/capture-page-states.md`
3. Read and follow `.claude/commands/run-page-audit.md`
4. Read and follow `.claude/commands/process-qa-report.md`

### PowerShell subset runs (in this repo)

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
