# Run Scenario Server: QA Scenario Evaluation Runner

Runs the QA scenario test suite against a live dev server using Playwright. Captures screenshots, page structure, and accessibility data for evaluation by the konote-qa-scenarios repo.

**This is TEST INFRASTRUCTURE**, not application code.

---

## Steps

### Step 1: Run preflight check

Run `python manage.py preflight`. If it fails, show the output to the user and STOP. Do not proceed until all critical checks pass.

If preflight reports missing test data (warning), run `python manage.py seed` then `python manage.py seed_demo_data` before continuing.

If preflight reports pending migrations (warning), run `python manage.py migrate` before continuing.

### Step 2: Start the dev server if not running

Check if `http://127.0.0.1:8000/` responds with HTTP 200.

If NOT responding:
1. Start `python manage.py runserver` in the background (use `run_in_background: true`)
2. Poll `http://127.0.0.1:8000/` every 2 seconds, up to 30 seconds
3. Verify the response is HTTP 200 (not a 500 error page)
4. If it doesn't come up, read the server's error output and show it to the user. STOP.

### Step 3: Run the scenario tests

Set `SCENARIO_HOLDOUT_DIR` to the path confirmed by preflight, then run:

```
pytest tests/scenario_eval/ -v --no-llm
```

**This takes 2–5 minutes.** Wait for it to finish. Do NOT poll or run other commands while it runs.

### Step 4: Report results

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
