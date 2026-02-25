# Capture Page States: Screenshot Generator for Page Audit

Takes screenshots of every KoNote page for every authorised persona at multiple breakpoints. These screenshots feed into `/run-page-audit` in the konote-qa-scenarios repo.

**This is TEST INFRASTRUCTURE**, not application code.

The test framework handles database setup, test data seeding, and live server startup internally. No manual preflight or server startup needed.

---

## Before running: check the pipeline log

Read `qa/pipeline-log.txt`. This command is Pipeline B, Step B1. Only run it after Pipeline A is fully complete (Step 3 entry exists for the current round). If the last entry says "Step 2" with no "Step 3", tell the user to run `/process-qa-report` first.

## Steps

### Step 1: Verify test files exist

Check that these files exist:
- `tests/utils/page_capture.py`
- `tests/integration/test_page_capture.py`

If either is missing, STOP and tell the user:
> The page capture test infrastructure hasn't been built yet. See `tasks/page-capture-reference.md` for the design spec and `tasks/refactor-capture-page-states.md` for context. These test files need to be created as a separate task before this skill can run.

### Step 2: Verify page inventory exists

Check that `../konote-qa-scenarios/pages/page-inventory.yaml` exists.

If missing, STOP and tell the user:
> The page inventory file is missing. Clone the konote-qa-scenarios repo next to konote-app, or check that `pages/page-inventory.yaml` exists in it.

### Step 3: Run the page capture tests

Run from the konote-app directory:

```
pytest tests/integration/test_page_capture.py -v
```

**This takes 3-10 minutes** depending on page count and breakpoints. Use `timeout: 600000` (10 minutes) on the Bash call. Wait for it to finish. Do NOT poll or run other commands while it runs.

Optional environment variable filters (set before running to narrow scope):
- `PAGE_CAPTURE_PAGES` — comma-separated page IDs (e.g. `client-list,dashboard-staff`)
- `PAGE_CAPTURE_PERSONAS` — comma-separated persona IDs (e.g. `R1,DS1`)
- `PAGE_CAPTURE_BREAKPOINTS` — single breakpoint (e.g. `1366x768`)
- `PAGE_CAPTURE_SKIP_AXE` — set to `1` to skip axe-core accessibility scanning (faster for debugging)

### Step 4: Report results

After tests complete, report to the user:
- Number of pages captured and total screenshots saved
- Axe-core accessibility findings: total scans, pages with violations, total violations
- Manifest location: `../konote-qa-scenarios/reports/screenshots/pages/.pages-manifest.json`
- Axe report location: `../konote-qa-scenarios/reports/screenshots/pages/axe-a11y-report.json`
- Any skipped pages or missing screenshots
- Any failures or errors

### Next steps

Tell the user:
1. Review `axe-a11y-report.json` for a quick accessibility summary grouped by violation type
2. Switch to the `konote-qa-scenarios` repo
3. Run `/run-page-audit` to evaluate the captured screenshots
4. See `tasks/page-capture-reference.md` for troubleshooting, screenshot naming, and advanced options
