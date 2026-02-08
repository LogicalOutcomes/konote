# Scenario QA Evaluation — How To

## What This Does

Runs realistic user scenarios (e.g., "Casey logs in for the first time") against a live test server using Playwright. Captures screenshots, page structure, and accessibility data at each step. Then you show the results to Claude for satisfaction scoring.

## When to Run

- After major UX changes (new pages, redesigned flows, navigation changes)
- Before a release, as a spot-check
- **Not** on every commit — it takes ~60 seconds and isn't a substitute for unit tests

## Step 1: Run the Dry-Run Capture

In a **VS Code terminal** (not Claude Code), run:

```
set SCENARIO_HOLDOUT_DIR=C:\Users\gilli\OneDrive\Documents\GitHub\konote-qa-scenarios
pytest tests/scenario_eval/ -v --no-llm
```

This captures screenshots and page state without any API calls. Results go to:
- **Screenshots**: `konote-qa-scenarios/reports/screenshots/`
- **Report**: `konote-qa-scenarios/reports/YYYY-MM-DD-satisfaction-report.md`

## Step 2: Review with Claude

Open a **separate VS Code window** on the `konote-qa-scenarios` folder. Start a new Claude Code conversation there and ask it to evaluate the screenshots and report. This uses your existing Claude subscription — no API key needed.

Example prompt:
> Look at the screenshots in reports/screenshots/ and the report in reports/. For each scenario, evaluate how satisfied each persona would be. Use the persona definitions in personas/ for context. Score each on clarity, efficiency, feedback, error recovery, accessibility, language, and confidence (1-5 each).

## Why a Separate Window?

**Holdout separation.** The scenarios in `konote-qa-scenarios` are deliberately kept outside the main codebase so that when Claude is writing KoNote2 code, it can't see the test scenarios and optimise for them. Using a separate window keeps the two contexts apart:

- **konote-web window** = writing code (Claude can't see scenarios)
- **konote-qa-scenarios window** = evaluating QA (Claude can see scenarios + screenshots)

## Running Specific Scenarios

```
:: Only calibration scenarios
pytest tests/scenario_eval/ -v --no-llm -k "calibration"

:: Only a specific scenario
pytest tests/scenario_eval/ -v --no-llm -k "SCN_010"
```

## Optional: Automated LLM Scoring

If you ever get an Anthropic API key (separate from your Claude subscription, from console.anthropic.com), you can run with automated scoring:

```
set ANTHROPIC_API_KEY=sk-ant-...
set SCENARIO_HOLDOUT_DIR=C:\Users\gilli\OneDrive\Documents\GitHub\konote-qa-scenarios
pytest tests/scenario_eval/ -v
```

This calls Claude Haiku for each step (~$0.10 per full run) and generates a scored report automatically. But the manual approach above works just as well.
