# QA-DATA7: Fix SCN-061 Screenshot Timeout

**Created:** 2026-02-08
**Status:** Done (2026-02-08)
**Affects:** 1 failing scenario test (SCN-061: Form Errors Keyboard)

## Problem

SCN-061 (form error recovery by keyboard-only, for DS3/Amara) times out at 30 seconds waiting for a screenshot to complete. The scenario runner already has a 10-second `networkidle` timeout with fallback to `domcontentloaded` (see `_wait_for_idle()` in scenario_runner.py lines 105-121), so the hang is likely in the **screenshot capture** itself, not the page wait.

## What SCN-061 Does

1. **Step 1:** Log in as `staff_a11y`, navigate to `/clients/create/`, tab through the form skipping First Name, press Enter to submit (triggers validation error)
2. **Step 2:** Type "James" in First Name, tab to submit, press Enter (successful submission)

Both steps include `wait_for: "networkidle"` which should fall back after 10 seconds.

## Investigation Steps

### 1. Check where the 30-second timeout originates

The screenshot capture happens in the scenario runner after action execution. Look for `page.screenshot()` calls and their timeout settings:

```
scenario_runner.py — search for "screenshot" to find capture logic
```

The 30-second timeout likely comes from Playwright's default `page.screenshot()` timeout. If the page has an animation loop, infinite scroll, or HTMX polling that prevents a stable paint, the screenshot may hang.

### 2. Check the create form page for hanging resources

Navigate to `/clients/create/` in the running app and check:
- Does the page have HTMX polling (e.g., `hx-trigger="every 2s"`)?
- Are there CSS animations that never stop?
- Does form validation trigger a spinner that doesn't resolve?
- Are there any `setInterval()` or `setTimeout()` loops?

### 3. Check if the form submission error page is the problem

After submitting with a missing required field, Django returns the form with error messages. Check:
- Does the error page include any auto-focus JavaScript that loops?
- Does the ARIA live region announcement trigger re-renders?
- Does the error page load any additional resources (fonts, icons) that might hang?

## Likely Fix Options

### Option A: Add explicit screenshot timeout (quick fix)

In the screenshot capture code, add a shorter timeout with a fallback:

```python
try:
    self.page.screenshot(path=screenshot_path, timeout=15000)
except Exception:
    # If screenshot times out, try with a smaller viewport clip
    self.page.screenshot(path=screenshot_path, timeout=15000, full_page=False)
```

### Option B: Wait for a specific element before screenshot

Instead of relying on networkidle, wait for the error message or success element:

```python
# After form submission with errors:
self.page.wait_for_selector(".errorlist, .alert-danger, [role='alert']", timeout=5000)
```

### Option C: Fix the page itself (root cause)

If the create form page has a hanging resource (most likely an HTMX polling interval or animation), fix it in the template. This is the cleanest solution but requires identifying the exact cause.

## Verification

After fixing, run only SCN-061:
```
pytest tests/scenario_eval/ -k "SCN-061" -v
```

Should complete within the normal timeout (< 60 seconds total).
