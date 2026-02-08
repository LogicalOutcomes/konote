# QA Scenario Runner Update Plan

**Date:** 2026-02-08
**Source:** Gap analysis between `konote-qa-scenarios` (32 scenarios, 11 personas, 5 DITLs) and the test runner in `tests/scenario_eval/`.

The QA scenarios repo has grown significantly. The test runner currently handles only a subset. This plan covers everything needed to bring the runner up to date.

---

## 1. New Test Users in `_create_test_data()` (scenario_runner.py)

The runner creates test users for DS1b, DS2, DS3, and R2. These personas are **missing**:

| Persona | Username | Display Name | Role | Program | Needed By |
|---------|----------|-------------|------|---------|-----------|
| DS1c | `staff_adhd` | Casey Parker (ADHD) | staff | program_a | SCN-058 |
| DS4 | `staff_voice` | Riley Chen | staff | program_a | SCN-059 |
| PM1 | `program_mgr` | Morgan Tremblay | program_manager | program_a + program_b | SCN-035, SCN-042, SCN-070 |
| E2 | `admin2` | Kwame Asante | admin | program_a + program_b | SCN-030 |

**Note:** DS1c (Casey with ADHD) is the same person as DS1 (Casey) but with a cognitive accessibility profile. The runner should create a separate test user so the persona's cognitive_profile can be tested independently. PM1 needs cross-program access (both program_a and program_b) for SCN-042 and SCN-070.

---

## 2. New Test Client Data in `_create_test_data()` (scenario_runner.py)

Currently creates Aisha Mohamed (SCN-047) and James Thompson (SCN-048). These are **missing**:

| Client | Programs | Needed By | Notes |
|--------|----------|-----------|-------|
| Benoit Tremblay | program_a (+ accented name) | SCN-040 | French name with accent |
| Multi-program client | program_a + program_b | SCN-042 | Enrolled in two programs |
| Client with consent record | program_a | SCN-070 | Needs consent date, notes >= 5, service records |
| Client with 5+ notes | program_a | SCN-015 | Casey's batch note entry |
| Client for SCN-020 | program_a | SCN-020 | Phone number update |
| Client for SCN-025 | program_b | SCN-025 | Omar's quick lookup |

**SCN-035** (funder reporting) and **SCN-070** (consent withdrawal) also need prerequisite data: service records, outcomes, funder report templates, and consent records. These may require model fixtures or a setup step.

---

## 3. New Playwright Action Types in `_execute_actions()` (scenario_runner.py)

The runner currently handles: `goto`, `fill`, `click`, `press`, `type`, `clear`, `wait_for`, `wait_htmx`, `wait`, `set_viewport`, `set_zoom`, `emulate_touch`, `set_high_contrast`, `set_network`, `login_as`.

### Must add:

| Action | Used In | Implementation |
|--------|---------|---------------|
| `voice_command` | SCN-059 | Map to equivalent `click` on matching visible text. Dragon says "Click [text]" which is functionally a click. Log the voice intent for the evaluator. |
| `dictate` | SCN-059 | Map to `type` (keyboard.type). Dragon dictation is functionally typing. Log the voice intent. |
| `intercept_network` | SCN-062 step 5 | Use `page.route(url, handler)` to intercept and return a mocked error response. Playwright supports this natively. |
| `close_tab` | SCN-049 | Close the current page (`page.close()`). |
| `open_new_tab` | SCN-049 | Create a new page in the same context (`context.new_page()`), set `self.page` to it. |
| `screenshot` | Multiple | Already captured automatically per step, but explicit `screenshot` action should trigger an extra named capture. |
| `go_back` | SCN-025 | Use `page.go_back()`. Note: `press: "Alt+ArrowLeft"` already maps to `go_back()` — this is an alias. |

### Implementation notes for voice commands:

```python
elif "voice_command" in action:
    # Dragon NaturallySpeaking "Click [text]" = click on matching visible text
    command = action["voice_command"]
    if command.lower().startswith("click "):
        target_text = command[6:]  # Strip "Click "
        try:
            self.page.get_by_text(target_text, exact=False).first.click(timeout=5000)
        except Exception:
            pass  # Voice target not found — evaluator will note
    elif command.lower().startswith("go to "):
        # Dragon "Go to [field]" = focus on field
        target = command[6:]
        try:
            self.page.get_by_label(target, exact=False).first.focus()
        except Exception:
            pass
    # Log intent for LLM evaluator
    logger.info(f"Voice command: {command}")

elif "dictate" in action:
    # Dragon dictation = typing text
    text = action["dictate"]
    self.page.keyboard.type(text)
    logger.info(f"Dictation: {text}")
```

### Implementation notes for network interception:

```python
elif "intercept_network" in action:
    config = action["intercept_network"]
    url_pattern = config.get("url", "")
    status = config.get("status", 500)

    def handler(route):
        route.fulfill(status=status, body=f"Mocked {status} error")

    self.page.route(url_pattern, handler)
```

---

## 4. New Test Classes in `test_scenario_eval.py`

Currently has 4 classes covering 10 scenarios. **22 scenarios have no test class.**

### Recommended new classes:

```
TestCalibrationScenarios (EXISTING — update)
  - CAL-001 ✓ (exists)
  - CAL-002 ✓ (exists)
  - CAL-003 ✓ (exists)
  + CAL-004  ← ADD (accessible page, DS3)
  + CAL-005  ← ADD (inaccessible page, DS3)

TestStarterScenarios (EXISTING — no changes needed)
  - SCN-005 ✓
  - SCN-010 ✓
  - SCN-050 ✓

TestDailyScenarios (NEW)
  + SCN-015 (batch note entry, DS1)
  + SCN-020 (phone update, R1)
  + SCN-025 (quick lookup, R2)

TestPeriodicScenarios (NEW)
  + SCN-030 (board prep, E1+E2)
  + SCN-035 (funder reporting, PM1)

TestCrossRoleScenarios (NEW)
  + SCN-040 (bilingual intake, DS2)
  + SCN-042 (multi-program client, PM1+DS1+R1)

TestEdgeCaseScenarios (NEW)
  + SCN-045 (error states, DS1+R1)
  + SCN-046 (session timeout, DS1)
  + SCN-049 (shared device handoff, DS1+R1)
  + SCN-070 (consent withdrawal, PM1+E1)

TestAccessibilityMicro (NEW)
  + SCN-051 (login focus, DS3)
  + SCN-052 (skip link, DS3)
  + SCN-053 (form accessibility, DS3)
  + SCN-054 (tab panel ARIA, DS3)
  + SCN-055 (HTMX announcement, DS3)
  + SCN-056 (high contrast + zoom, DS3)
  + SCN-057 (touch targets, DS1)
  + SCN-058 (cognitive load, DS1c)
  + SCN-059 (voice navigation, DS4)
  + SCN-061 (form errors keyboard, DS3)
  + SCN-062 (ARIA live fatigue, DS3)

TestRound3Scenarios (EXISTING — no changes needed)
  - SCN-047 ✓
  - SCN-048 ✓

TestDayInTheLife (EXISTING — update)
  - DITL-DS3 ✓ (exists)
  - DITL-E1 ✓ (exists)
  - DITL-DS2 ✓ (exists)
  + DITL-DS1  ← ADD (Casey's Tuesday)
  + DITL-R1   ← ADD (Dana's Monday)
```

### CAL-006 (meta-calibration) — Special handling

CAL-006 is NOT a standalone scenario. It bundles CAL-001 through CAL-005 and runs them with variant configurations (different models, prompts, temperatures) to test inter-rater reliability. This needs a separate test method or class:

```
TestInterRaterReliability (NEW — optional, advanced)
  + CAL-006: Run CAL-001 to CAL-005 with each variant,
    compute ICC and agreement metrics, check pass_criteria
```

This is **low priority** — it's a methodology validation tool, not a regression test.

---

## 5. Update `_get_scenarios()` in Calibration Class

The existing calibration test hardcodes `ids=["CAL-001", "CAL-002", "CAL-003"]`. Update to include CAL-004 and CAL-005:

```python
return discover_scenarios(holdout, ids=["CAL-001", "CAL-002", "CAL-003", "CAL-004", "CAL-005"])
```

Add test methods:

```python
def test_calibration_accessible_page(self):
    """CAL-004: Accessible login form should score 3.5-4.5 for DS3."""
    result = self._run_calibration("CAL-004")
    if self.use_llm and result.avg_score > 0:
        self.assertGreaterEqual(result.avg_score, 3.0,
            f"CAL-004 scored {result.avg_score:.1f} — expected >= 3.0 for accessible page")

def test_calibration_inaccessible_page(self):
    """CAL-005: Inaccessible data table should score 1.0-1.9 for DS3."""
    result = self._run_calibration("CAL-005")
    if self.use_llm and result.avg_score > 0:
        self.assertLessEqual(result.avg_score, 2.5,
            f"CAL-005 scored {result.avg_score:.1f} — expected <= 2.5 for inaccessible page")
```

---

## 6. Fields the Evaluator Should Be Aware Of

These YAML fields are **evaluator-facing** (used by the LLM, not by the Playwright runner). The runner doesn't need to execute them, but `llm_evaluator.py` should include them in the prompt if present:

| Field | Used In | Purpose |
|-------|---------|---------|
| `cognitive_load_checks` | SCN-058 | Boolean checklist for cognitive accessibility (e.g., `distinct_info_blocks_on_screen`) |
| `mechanical_checks` | Multiple | Boolean checklist for specific UI verifications |
| `task_completion_criteria` | All new scenarios | yes/partial/no outcome definitions |
| `prerequisites.accessibility` | SCN-059, SCN-062 | `screen_reader: true`, `speech_recognition: true` |
| `prerequisites.config` | SCN-046, SCN-049 | `session_timeout_minutes`, `shared_device` |

### Changes to `llm_evaluator.py`:

In `evaluate_step()`, include these fields in the prompt when present:

```python
# Add cognitive load checks if present
cognitive_checks = step.get("cognitive_load_checks", {})
if cognitive_checks:
    prompt += f"\n\nCOGNITIVE LOAD CHECKS (verify these):\n"
    for check, expected in cognitive_checks.items():
        prompt += f"- {check}: expected {expected}\n"

# Add mechanical checks if present
mechanical_checks = step.get("mechanical_checks", {})
if mechanical_checks:
    prompt += f"\n\nMECHANICAL CHECKS (verify these):\n"
    for check, expected in mechanical_checks.items():
        prompt += f"- {check}: expected {expected}\n"

# Add task completion criteria if present
completion = step.get("task_completion_criteria", {})
if completion:
    prompt += f"\n\nTASK COMPLETION CRITERIA:\n"
    for outcome, description in completion.items():
        prompt += f"- {outcome}: {description}\n"
```

---

## 7. CI Workflow Update (`.github/workflows/qa-scenarios.yml`)

The CI workflow runs all discovered scenarios, so new scenarios will be picked up automatically. However:

- **SCN-059** (voice commands) will fail until `voice_command` and `dictate` actions are implemented. Either implement them or add a skip marker.
- **SCN-062 step 5** (network interception) will fail until `intercept_network` is implemented.
- **SCN-049** (tab management) will fail until `close_tab` and `open_new_tab` are implemented.

**Recommended approach:** Implement the action types first (item 3 above), then all scenarios will run cleanly. Alternatively, add `skip_in_ci: true` to the YAML files for scenarios that need unsupported features, and have the runner check this field.

---

## 8. Priority Order

| Priority | Task | Effort | Unlocks |
|----------|------|--------|---------|
| **1** | Add test users (DS1c, DS4, PM1, E2) | Small | SCN-058, SCN-059, SCN-035, SCN-042, SCN-070, SCN-030 |
| **2** | Add test client data | Small | SCN-015, SCN-020, SCN-025, SCN-040, SCN-042, SCN-070 |
| **3** | Implement `voice_command` and `dictate` actions | Medium | SCN-059 |
| **4** | Implement `intercept_network` action | Small | SCN-062 step 5 |
| **5** | Implement `close_tab` and `open_new_tab` actions | Small | SCN-049 |
| **6** | Implement `go_back` and `screenshot` actions | Tiny | SCN-025, multiple |
| **7** | Add calibration tests (CAL-004, CAL-005) | Small | Calibration coverage |
| **8** | Add new test classes (Daily, Periodic, CrossRole, EdgeCase, AccessibilityMicro) | Medium | All 22 uncovered scenarios |
| **9** | Add DITL-DS1 and DITL-R1 to TestDayInTheLife | Small | Full DITL coverage |
| **10** | Update LLM evaluator for new fields | Medium | Better evaluation quality |
| **11** | CAL-006 / IRR automation | Large | Inter-rater reliability (optional) |

---

## Files to Modify

| File | Changes |
|------|---------|
| `tests/scenario_eval/scenario_runner.py` | Add test users, client data, new action types |
| `tests/scenario_eval/test_scenario_eval.py` | Add test classes and methods for 22 new scenarios |
| `tests/scenario_eval/llm_evaluator.py` | Include new YAML fields in prompts |
| `TODO.md` | Add QA runner update tasks |
