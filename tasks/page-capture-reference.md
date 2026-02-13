# Page Capture — Reference Guide

## Overview

The page capture system takes screenshots of every KoNote page for every authorized persona at multiple breakpoints. It is Step 1 of the page audit pipeline:

1. **`/capture-page-states`** (konote-app) — screenshots + manifest
2. **`/run-page-audit`** (konote-qa-scenarios) — evaluation + tickets
3. **`/process-qa-report`** (konote-app) — expert panel + action plan

## Key Files

| File | Purpose |
|------|---------|
| `tests/utils/page_capture.py` | Shared utilities (URL resolution, screenshot capture, manifest) |
| `tests/integration/test_page_capture.py` | Main pytest test that iterates pages x personas x breakpoints |
| `../konote-qa-scenarios/pages/page-inventory.yaml` | Source of truth for pages, personas, and states |

## Screenshot Naming Convention

Screenshots are saved to: `../konote-qa-scenarios/reports/screenshots/pages/`

Filename format: `{page_id}-{persona_id}-{state}-{breakpoint}.png`

Examples:
- `client-list-R1-populated-1366x768.png`
- `dashboard-staff-DS1-default-1920x1080.png`
- `auth-403-R2-denied-375x667.png`

## Breakpoints

| Breakpoint | Represents |
|-----------|------------|
| `1366x768` | Standard laptop |
| `1920x1080` | Desktop monitor |
| `375x667` | Mobile (iPhone SE) |

## State Capture Strategies

| State | Strategy |
|-------|----------|
| **default** | Navigate to URL with normal test data |
| **empty** | Clear filters, search for nonexistent term, or navigate to page with no data |
| **populated** | Navigate with seed test data (50+ clients, 10+ notes, etc.) |
| **error** | Submit form with invalid data (missing required fields, wrong format) |
| **success** | Complete form submission and capture confirmation message |
| **denied** | Log in as wrong role and attempt access (Permission Gate test) |

**Note:** Phase 1 only captures `default` and `populated` states. Other states require page-specific form interaction logic (future work).

## Manifest Format

The manifest is written to `../konote-qa-scenarios/reports/screenshots/pages/.pages-manifest.json`:

```json
{
  "timestamp": "2026-02-08T14:32:00+00:00",
  "pages_captured": 37,
  "personas_tested": ["DS1", "DS2", "R1", "R2"],
  "states_captured": ["default", "populated"],
  "breakpoints": ["1366x768", "1920x1080", "375x667"],
  "total_screenshots": 487,
  "skipped": [],
  "missing_screenshots": [],
  "pages": [
    {
      "page_id": "client-list",
      "url": "/clients/",
      "personas_captured": ["R1", "R2", "DS1"],
      "states_captured": ["default", "populated"],
      "screenshot_count": 18
    }
  ]
}
```

## Environment Variable Filters

Set these before running to narrow the capture scope:

| Variable | Example | Effect |
|----------|---------|--------|
| `PAGE_CAPTURE_PAGES` | `auth-login,client-list` | Only capture these pages |
| `PAGE_CAPTURE_PERSONAS` | `R1,DS1` | Only use these personas |
| `PAGE_CAPTURE_BREAKPOINTS` | `1366x768` | Only capture at this size |

## Persona Mapping

Persona IDs map to test usernames in `tests/utils/page_capture.py` (`PERSONA_MAP`). The test file creates all persona users via `_create_extra_persona_users()`.

## Troubleshooting

### "No username mapping for persona X"
The persona ID from the page inventory doesn't have a matching entry in `PERSONA_MAP` in `tests/utils/page_capture.py`. Add the mapping there.

### "Login failed"
- Check the Django dev server is running (`http://localhost:8000`)
- Check test users were created (the test creates them automatically via `_create_test_data()`)
- Check login form selectors in `tests/ux_walkthrough/browser_base.py`

### "Could not resolve URL"
The URL pattern has a placeholder (like `<int:client_id>`) that couldn't be resolved. Check `_build_test_data_dict()` in the test file has the right IDs.

### Screenshots are blank or wrong page
Increase `wait_for_timeout()` values in `page_capture.py`. HTMX or JavaScript may need more time to render.

### "Non-routable URL pattern"
Pages with patterns like `(any 403 error)` are skipped automatically — they represent error states, not real URLs.
