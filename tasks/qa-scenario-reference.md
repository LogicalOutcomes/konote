# QA Scenario Testing — Reference Guide

## Running Specific Scenarios

To run only specific scenarios, use pytest's `-k` flag:

```powershell
$env:SCENARIO_HOLDOUT_DIR = "C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios"

# Only calibration scenarios
pytest tests/scenario_eval/ -v --no-llm -k "calibration"

# Only a specific scenario
pytest tests/scenario_eval/ -v --no-llm -k "SCN_010"

# Only smoke tests
pytest tests/scenario_eval/ -v --no-llm -k "smoke"
```

## Optional: Automated LLM Scoring

If you have an Anthropic API key (separate from Claude Code subscription), you can run with automated scoring:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:SCENARIO_HOLDOUT_DIR = "C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios"
pytest tests/scenario_eval/ -v
```

This calls Claude Haiku for each step (~$0.10 per full run) and generates a scored report automatically.

## Output Locations

All outputs go to the qa-scenarios repo:

| Output | Location |
|--------|----------|
| Screenshots | `konote-qa-scenarios/reports/screenshots/` |
| Satisfaction Report | `konote-qa-scenarios/reports/YYYY-MM-DD-satisfaction-report.md` |
| Console Logs | `konote-qa-scenarios/reports/screenshots/*_console.log` |

## QA Pipeline Overview

The full QA pipeline has three steps:

1. **`/run-scenario-server`** (konote-app) — captures screenshots via Playwright
2. **`/run-scenarios`** (konote-qa-scenarios) — evaluates captured screenshots
3. **`/process-qa-report`** (konote-app) — expert panel review + action plan

See `tasks/recurring-tasks.md` for the full workflow schedule.

## Troubleshooting

### "SCENARIO_HOLDOUT_DIR not found"
The qa-scenarios repo isn't cloned. Clone it:
```powershell
git clone https://github.com/gilliankerr/konote-qa-scenarios "C:/Users/gilli/OneDrive/Documents/GitHub/konote-qa-scenarios"
```

### "Browser not found"
Install Playwright browsers:
```powershell
playwright install chromium
```

### "Dev server failed to start"
Check for port conflicts or Django errors. Try running manually:
```powershell
python manage.py preflight
python manage.py runserver
```

### "Preflight FAILED"
Run `python manage.py preflight` to see exactly what's wrong. Common issues:
- Database not reachable (check `.env` has correct `DATABASE_URL`)
- Migrations pending (run `python manage.py migrate`)
- Test data missing (run `python manage.py seed && python manage.py seed_demo_data`)
