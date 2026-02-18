# Run Scenario Server: QA Scenario Evaluation Runner

Runs the QA scenario test suite using Playwright. Captures screenshots, page structure, and accessibility data for evaluation by the konote-qa-scenarios repo.

**This is TEST INFRASTRUCTURE**, not application code.

The test framework handles everything internally: database setup, migrations, test data seeding, live server startup, holdout repo resolution, and cleanup. No manual preflight or server startup needed.

---

## Steps

### Step 1: Run the scenario tests

Run from the konote-app directory:

```
pytest tests/scenario_eval/ -v --no-llm
```

**This takes 2-5 minutes.** Use `timeout: 360000` (6 minutes) on the Bash call. Wait for it to finish. Do NOT poll or run other commands while it runs.

Notes:
- `SCENARIO_HOLDOUT_DIR` auto-resolves to `../konote-qa-scenarios` if the repo is cloned next to konote-app. Only set it manually for non-standard layouts.
- The test framework starts its own live server (via `StaticLiveServerTestCase`) — do NOT start `runserver` separately.
- If tests skip with "Holdout repo not found", the user needs to clone the konote-qa-scenarios repo next to konote-app.

### Step 2: Report results

After tests complete, report to the user:
- Number of tests run and pass/fail counts
- Location of screenshots: `konote-qa-scenarios/reports/screenshots/`
- Location of satisfaction report: `konote-qa-scenarios/reports/YYYY-MM-DD-satisfaction-report.md`
- Any failures or errors

### Next steps

Tell the user:
1. Switch to the `konote-qa-scenarios` repo
2. Run `/run-scenarios` to evaluate the captured screenshots
3. See `tasks/qa-scenario-reference.md` for advanced options (specific scenarios, LLM scoring)
