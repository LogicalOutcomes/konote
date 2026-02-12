# Run Scenario Server: QA Scenario Evaluation Runner

## Purpose

This command runs the QA scenario evaluation suite against a live test server using Playwright. It captures screenshots, page structure, and accessibility data at each step for evaluation by the konote-qa-scenarios repo.

**This is TEST INFRASTRUCTURE**, not application code. It runs pytest-based scenario tests that simulate real user journeys.

---

## Prerequisites

1. **Test server running:** The Django dev server must be running with test data loaded. Run `python manage.py runserver` before invoking this command.

2. **Test data seeded:** All test users (from personas), test clients, and test content must exist. Run `python manage.py seed_demo_data` if not already seeded.

3. **Browser automation:** Playwright must be installed (`playwright install chromium`).

4. **Holdout repo:** The `konote-qa-scenarios` repo must be cloned at `../konote-qa-scenarios` or specified via `SCENARIO_HOLDOUT_DIR` environment variable.

---

## What This Command Does

1. Sets the `SCENARIO_HOLDOUT_DIR` environment variable to point to the qa-scenarios repo
2. Runs `pytest tests/scenario_eval/ -v --no-llm` to capture screenshots without LLM evaluation
3. Outputs screenshots to `konote-qa-scenarios/reports/screenshots/`
4. Outputs satisfaction report to `konote-qa-scenarios/reports/YYYY-MM-DD-satisfaction-report.md`

---

## Execution Steps

### Step 1: Verify Environment

Check that the holdout directory exists:

```bash
# Check if SCENARIO_HOLDOUT_DIR is set, otherwise use default
if [ -z "$SCENARIO_HOLDOUT_DIR" ]; then
    export SCENARIO_HOLDOUT_DIR="C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios"
fi

# Verify it exists
if [ ! -d "$SCENARIO_HOLDOUT_DIR" ]; then
    echo "ERROR: SCENARIO_HOLDOUT_DIR not found: $SCENARIO_HOLDOUT_DIR"
    echo "Please clone konote-qa-scenarios repo or set SCENARIO_HOLDOUT_DIR"
    exit 1
fi
```

### Step 2: Run Scenario Tests

> **⚠️ This is a long-running command (101+ tests, ~2–5 minutes).** When you run it, the terminal will report "Command is still running" — this is normal. **Wait for the terminal to return the final output. Do NOT run echo or polling commands to check status.** The results will appear automatically when pytest finishes.

Run the pytest scenario evaluation suite:

```bash
# Windows CMD
set SCENARIO_HOLDOUT_DIR=C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios
pytest tests/scenario_eval/ -v --no-llm
```

Or for PowerShell:

```powershell
$env:SCENARIO_HOLDOUT_DIR = "C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios"
pytest tests/scenario_eval/ -v --no-llm
```

### Step 3: Report Results

After tests complete, report:

- Number of scenarios run
- Number of screenshots captured
- Location of satisfaction report
- Any failures or errors

---

## Running Specific Scenarios

To run only specific scenarios, use pytest's `-k` flag:

```bash
# Only calibration scenarios
pytest tests/scenario_eval/ -v --no-llm -k "calibration"

# Only a specific scenario
pytest tests/scenario_eval/ -v --no-llm -k "SCN_010"

# Only smoke tests
pytest tests/scenario_eval/ -v --no-llm -k "smoke"
```

---

## Optional: Automated LLM Scoring

If you have an Anthropic API key (separate from Claude subscription), you can run with automated scoring:

```bash
set ANTHROPIC_API_KEY=sk-ant-...
set SCENARIO_HOLDOUT_DIR=C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios
pytest tests/scenario_eval/ -v
```

This calls Claude Haiku for each step (~$0.10 per full run) and generates a scored report automatically.

---

## Output Locations

All outputs go to the qa-scenarios repo:

| Output | Location |
|--------|----------|
| Screenshots | `konote-qa-scenarios/reports/screenshots/` |
| Satisfaction Report | `konote-qa-scenarios/reports/YYYY-MM-DD-satisfaction-report.md` |
| Console Logs | `konote-qa-scenarios/reports/screenshots/*_console.log` |

---

## Troubleshooting

### "SCENARIO_HOLDOUT_DIR not set"

Set the environment variable to point to your konote-qa-scenarios repo:

```bash
set SCENARIO_HOLDOUT_DIR=C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios
```

### "Browser not found"

Install Playwright browsers:

```bash
playwright install chromium
```

### "Test data missing"

Seed the demo data:

```bash
python manage.py seed_demo_data
```

### "Server not running"

Start the Django dev server in a separate terminal:

```bash
python manage.py runserver
```

---

## Next Steps

After running this command:

1. Switch to the `konote-qa-scenarios` repo
2. Run `/run-scenarios` to evaluate the captured screenshots
3. Review the satisfaction report and improvement tickets

See `tasks/recurring-tasks.md` for the full QA workflow.
