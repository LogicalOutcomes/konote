# Session 5: Parallel Tasks — Data Quality + Documentation + QA Seeding

## Pre-flight (do first, sequentially)

Merge the 2 open PRs if they're approved, then pull develop:

```
gh pr merge 234 --merge --repo LogicalOutcomes/konote
gh pr merge 235 --merge --repo LogicalOutcomes/konote
git pull origin develop
```

If either PR isn't approved yet, skip it — none of the tasks below conflict with those PRs.

Then create a feature branch: `git checkout -b feat/session-5-dq-docs`

---

## Parallel agents (launch all at once — no file conflicts between them)

### Agent A: DQ1-TIER2 — Second-tier "very unlikely" plausibility thresholds

**Branch:** `feat/dq1-tier2-thresholds` (worktree)
**Files:** `apps/plans/models.py`, `apps/plans/migrations/`, `apps/notes/forms.py`, `static/js/app.js`, `templates/notes/note_form.html`, `tests/test_plans.py`

The existing DQ1 system (tier-1) adds soft yellow warnings when metric values are outside `warn_min`/`warn_max`. Tier-2 adds a second, tighter threshold for extreme data-entry errors (e.g., typing $700,000,000 instead of $700).

#### Step 1: Model fields

**File:** `apps/plans/models.py` — `MetricDefinition` model

Add two new fields after `warn_max` (line ~57):

```python
very_unlikely_min = models.FloatField(
    null=True, blank=True,
    help_text=_("Hard floor — values below this are almost certainly data-entry errors. Requires two confirmations."),
)
very_unlikely_max = models.FloatField(
    null=True, blank=True,
    help_text=_("Hard ceiling — values above this are almost certainly data-entry errors. Requires two confirmations."),
)
```

#### Step 2: Validation

**File:** `apps/plans/models.py` — `MetricDefinition.clean()` (line ~165)

Add validation rules after the existing warn checks:

- `very_unlikely_min` must be <= `warn_min` (if both set)
- `very_unlikely_max` must be >= `warn_max` (if both set)
- `very_unlikely_min` must be >= `min_value` (if both set)
- `very_unlikely_max` must be <= `max_value` (if both set)
- `very_unlikely_min` must be < `very_unlikely_max` (if both set)

#### Step 3: Migration — schema

Run `python manage.py makemigrations plans` to create the schema migration.

#### Step 4: Migration — default thresholds

Create a data migration (like `0018_set_financial_warn_thresholds.py`) that sets tier-2 defaults. Use approximately 10x the tier-1 values:

```python
FINANCIAL_TIER2_THRESHOLDS = {
    "Total Debt": {"very_unlikely_min": -10000, "very_unlikely_max": 2000000},
    "Monthly Income": {"very_unlikely_min": -1000, "very_unlikely_max": 150000},
    "Monthly Savings": {"very_unlikely_min": -5000, "very_unlikely_max": 50000},
    "Credit Score Change": {"very_unlikely_min": -500, "very_unlikely_max": 500},
    "Debt-to-Income Ratio": {"very_unlikely_min": -10, "very_unlikely_max": 200},
    "Savings Rate (%)": {"very_unlikely_min": -100, "very_unlikely_max": 200},
    "Income Change ($)": {"very_unlikely_min": -50000, "very_unlikely_max": 100000},
}
```

#### Step 5: Form — pass tier-2 data attributes

**File:** `apps/notes/forms.py` — `MetricValueForm.__init__()` (line ~331)

After the existing `data-warn-min`/`data-warn-max` lines, add:

```python
if metric_def.very_unlikely_min is not None:
    attrs["data-very-unlikely-min"] = metric_def.very_unlikely_min
if metric_def.very_unlikely_max is not None:
    attrs["data-very-unlikely-max"] = metric_def.very_unlikely_max
```

Also update the condition for showing `plausibility_confirmed` (line ~342) to include the new fields:

```python
if (metric_def.warn_min is not None or metric_def.warn_max is not None
        or metric_def.very_unlikely_min is not None or metric_def.very_unlikely_max is not None):
```

#### Step 6: JavaScript — two-tier checking

**File:** `static/js/app.js` — `checkPlausibility()` function (line ~1650)

Enhance the function to check tier-2 first, then tier-1:

1. Read `data-very-unlikely-min` and `data-very-unlikely-max` from the input
2. **If value is outside tier-2 bounds:** show a RED error message: "This value (X) is extremely unlikely for [metric]. This is almost certainly a data-entry error. Please re-check and confirm twice if correct."
3. **Else if value is outside tier-1 bounds (existing):** show the existing YELLOW warning
4. **Else:** hide all warnings

For tier-2, require the user to click "Confirm" TWICE (the button text changes after first click: "Click again to confirm" → sets confirmed). This adds friction for truly extreme values.

Update the event selector to also match `data-very-unlikely-min`/`data-very-unlikely-max` attributes (lines ~1721, ~1726).

#### Step 7: Template — add tier-2 styling

**File:** `templates/notes/note_form.html` (line ~165)

The existing `.plausibility-warning` div handles both tiers via JS. Add CSS classes so tier-2 warnings show red:

In the existing `plausibility-warning` div area, the JS will add a `tier-2` class when the value is extremely unlikely. Add to `static/css/main.css` (or inline):

```css
.plausibility-warning.tier-2 .warning-text {
    color: var(--pico-form-element-invalid-border-color);
    font-weight: bold;
}
```

#### Step 8: Admin form — show tier-2 fields

**File:** `templates/plans/metric_form.html` (line ~18)

Add `very_unlikely_min` and `very_unlikely_max` to the `metric-scale-field` class condition so they appear alongside the existing warn fields:

```
field.name == "very_unlikely_min" or field.name == "very_unlikely_max"
```

#### Step 9: Tests

**File:** `tests/test_plans.py`

Add tests for:
1. Model validation: `very_unlikely_min` < `very_unlikely_max`
2. Model validation: `very_unlikely_min` >= `min_value`
3. Model validation: `very_unlikely_max` <= `max_value`
4. Model validation: ordering — `min_value <= very_unlikely_min <= warn_min <= warn_max <= very_unlikely_max <= max_value`
5. Form renders `data-very-unlikely-min` and `data-very-unlikely-max` attributes
6. Migration sets tier-2 defaults for financial metrics

Run: `pytest tests/test_plans.py -v`

#### Step 10: Translations

Run `python manage.py translate_strings`. Add French translations for:
- "This value is extremely unlikely" → "Cette valeur est extrêmement improbable"
- "Click again to confirm" → "Cliquez de nouveau pour confirmer"
- Model field help_text strings

Commit after each step.

---

### Agent B: DOC-DEMO1 — Demo data engine client guide

**Branch:** same as main session branch (`feat/session-5-dq-docs`) or a worktree
**Files:** `docs/demo-data-guide.md` (new file)

Write a client-facing guide for agency admins on how to use the demo data engine. This is documentation only — no code changes.

#### Source material to read first

1. `tasks/demo-data-engine-guide.md` — internal reference doc (176 lines)
2. `apps/admin_settings/demo_engine.py` — core engine (1,167 lines)
3. `apps/admin_settings/management/commands/generate_demo_data.py` — CLI command
4. `seeds/demo_data_profile_example.json` — example profile JSON
5. `templates/admin_settings/demo_data.html` — admin UI template
6. `apps/admin_settings/views.py` — `demo_data_management` function

#### Guide structure

Write a Markdown guide in `docs/demo-data-guide.md` with these sections:

1. **What the demo data engine does** — 2-3 paragraphs, non-technical
2. **When to use it** — during evaluation, training, after reconfiguring programs/metrics
3. **Using the admin interface** — step-by-step: navigate to Admin > Demo Data, set participant count, set time span, click Generate. What happens (old demo data is cleared first). What gets created (participants, plans, notes, events, alerts). How to regenerate after config changes.
4. **Using the command line** (optional, for technical staff) — `python manage.py generate_demo_data` with `--profile`, `--clients-per-program`, `--days` options
5. **Writing a custom profile JSON** — explain the format using `seeds/demo_data_profile_example.json` as a reference. What each field does. When you'd want a custom profile vs. auto-generation.
6. **Troubleshooting** — common issues: "No demo data appeared" (check programs exist), "Data doesn't match my metrics" (regenerate after changing metrics), "Demo data mixed with real data" (demo participants are flagged, can be purged)

#### Quality checks

- Spot-check 3-5 claims against the actual code
- Verify the CLI command flags match `generate_demo_data.py`
- Verify the admin UI steps match `demo_data.html` and `views.py`
- Canadian spelling throughout
- Suitable for a non-technical agency admin to follow

---

### Agent C: DOC-PERM verification + QA-PA-TEST1/2 seed data

**Branch:** worktree (for konote changes) + direct work in `konote-qa-scenarios` repo

This agent has two small tasks:

#### Part 1: Verify DOC-PERM1/2/3 and mark done

Three permission docs already exist but are still marked `[ ]` in TODO.md. Verify them against code, then mark as done.

1. Read `docs/admin/dv-safe-mode-and-gated-access.md` — spot-check 3 claims against `apps/clients/dv_views.py` and `apps/auth_app/permissions.py`
2. Read `docs/admin/per-field-front-desk-access.md` — spot-check 3 claims against `apps/admin_settings/field_access_views.py`
3. Read `docs/admin/access-tiers.md` — spot-check 3 claims against `apps/admin_settings/models.py` and `apps/auth_app/`

If all three are accurate, update TODO.md to mark DOC-PERM1, DOC-PERM2, DOC-PERM3 as `[x]` with today's date. Move them to Recently Done.

If any doc has errors, fix them. The docs are documentation-only — no code changes needed.

#### Part 2: QA-PA-TEST1/2 — Verify and fix seed data

**Repo:** `C:\Users\gilli\GitHub\konote-qa-scenarios` (separate repo, create a branch there)

Two QA scenarios need seed data verification:

1. **QA-PA-TEST1 (groups-attendance):** The `page-inventory.yaml` expects 8 members x 12 sessions = 96 attendance cells.
   - Check `tests/scenario_eval/scenario_runner.py` for `seed_group_attendance_data()` — it should create a Group, 8 GroupMemberships, 12 GroupSessions, and 96 GroupSessionAttendance records
   - Check `tests/integration/test_page_capture.py` for duplicate seeding logic — if it exists, ensure it matches `scenario_runner.py`
   - Verify the models (`apps/groups/models.py`) haven't acquired new required fields since the seeding code was written
   - If seeding code is missing or broken, create/fix it

2. **QA-PA-TEST2 (comm-my-messages):** The `page-inventory.yaml` expects 5+ messages in the populated state.
   - Check `tests/scenario_eval/scenario_runner.py` for `seed_staff_messages()` — it should create 5+ StaffMessage objects
   - Check `apps/communications/models.py` for the StaffMessage model and required fields
   - Verify seeding code creates messages for the right personas (DS1, DS1b, DS2, PM1)
   - If seeding code is missing or broken, create/fix it

Run relevant tests to verify: `pytest tests/integration/test_page_capture.py -k "groups_attendance or comm_my_messages" -v`

If tests pass, mark QA-PA-TEST1 and QA-PA-TEST2 as `[x]` in TODO.md.

---

## After all agents finish

1. Review each agent's work — check for consistency, correct spelling, no conflicts
2. Run `python manage.py translate_strings` if any templates were modified (Agent A)
3. Run `pytest tests/test_plans.py -v` to verify DQ1-TIER2 (Agent A)
4. Commit each agent's work as a separate commit with the relevant task ID
5. Push and create PR to `develop`
6. Update TODO.md: mark DQ1-TIER2, DOC-DEMO1, DOC-PERM1/2/3, QA-PA-TEST1/2 as done

## File conflict matrix (why these are safe in parallel)

| Agent | Files touched | Conflicts with |
|-------|--------------|----------------|
| A (DQ1-TIER2) | `apps/plans/`, `apps/notes/forms.py`, `static/js/app.js`, `templates/notes/`, `tests/test_plans.py` | None |
| B (DOC-DEMO1) | `docs/demo-data-guide.md` (new file, read-only against code) | None |
| C (DOC-PERM + QA-PA) | `docs/admin/` (read-only verify), `TODO.md`, `konote-qa-scenarios/` (separate repo) | TODO.md conflict with A/B — Agent C should commit TODO.md changes last |

**Note:** Only Agent C touches TODO.md. Agents A and B should NOT update TODO.md. The main session updates TODO.md after all agents finish.
