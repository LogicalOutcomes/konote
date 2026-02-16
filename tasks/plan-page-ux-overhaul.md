# Plan Page UX Overhaul

## Problem

The plan page (participant's goals and outcomes) has UX issues identified by user testing:

1. **Oversized buttons**: Section-level "Edit" and "Status" use Pico CSS `role="group"` which stretches them across the section header — they look like primary actions instead of management tools
2. **"Status" is cryptic**: The button label doesn't explain what it does (Active/Completed/Deactivated)
3. **Browser confirm dialog is bewildering**: `hx-confirm` triggers a raw `window.confirm()` showing "konote.llewelyn.ca says: Change the status of this section? This may affect related targets." — technical, scary, unhelpful
4. **Target-level action overload**: 4 buttons per target row (Edit, Status, Metrics, History) create visual clutter
5. **Caseworkers read plans far more than they edit them**: the page gives equal visual weight to infrequent admin actions and frequent reading

## Expert Panel Consensus (2026-02-16)

Panel: UX Designer, Accessibility Specialist, Social Services Software Consultant, Frontend Developer

### Unanimous recommendations:
- Remove `role="group"` from button containers
- Remove browser `hx-confirm` dialogs — the inline form IS the confirmation
- Rename "Status" to action-oriented language
- Reduce visual prominence of management actions
- Show specific consequences of status changes, not vague warnings
- Consolidate target-level buttons into a single Actions dropdown

---

## Phase A — UI Cleanup (immediate)

### PLAN-A1: Remove oversized button groups
- Remove `role="group"` from section-level Edit/Status buttons in `_section.html`
- Replace with a simple flex container or inline text links
- Style as small, subtle text links: `edit · mark complete`

### PLAN-A2: Remove browser confirm dialogs
- Remove `hx-confirm` from Status buttons in `_section.html` and `_target.html`
- The inline status form already has Cancel — it IS the confirmation step

### PLAN-A3: Rename Status to clear action labels
- Section level: Show the next logical action, not "Status"
  - If Active → show "Mark Complete" and "Deactivate" as options
  - If Completed → show "Reactivate"
  - If Deactivated → show "Reactivate"
- Target level: Same pattern in the Actions dropdown

### PLAN-A4: Enhance inline status form
- Replace `_section_status.html` and `_target_status.html` with plain-language forms
- Show: "Completing this area will also mark X goals as complete. You can undo this later."
- Include specific counts and reassurance of reversibility

### PLAN-A5: Target-level actions dropdown
- Replace 4-button row with a single "Actions" dropdown
- Menu items: Edit, Mark Complete/Deactivate, Manage Metrics, View History
- Use `button` + `aria-haspopup` + dropdown panel pattern (not `<details>/<summary>`)
- Reuse existing action-menu pattern from participant header

---

## Phase B — AI Goal Builder (next)

### PLAN-B1: `build_goal()` AI function
- New function in `konote/ai.py`
- Combines `improve_outcome()` + `suggest_metrics()` into one AI call
- Input: free-text description of what the participant wants to achieve
- Output: structured goal (name, description, client_goal quote, suggested metrics, suggested section)
- Uses existing OpenRouter infrastructure and rate limiting

### PLAN-B2: Goal Builder HTMX panel
- New template `_goal_builder.html`
- Triggered by "Add a Goal" button (replaces "Add Target")
- Step 1: Single text input — "What does the participant want to achieve?"
- Step 2: AI returns structured preview — all fields editable
- Step 3: One-click save

### PLAN-B3: One-save creation
- Goal Builder save creates PlanTarget + attaches MetricDefinitions + assigns PlanSection
- If suggested metrics don't exist in the library, create as custom metrics for the program
- If suggested section doesn't exist, offer to create it or assign to existing

### PLAN-B4: PII scrubbing
- Run input text through existing `pii_scrub.py` before AI call
- Only send scrubbed text + program type + metric catalogue
- No participant name, ID, file number, or dates

### PLAN-B5: Tests
- Mock AI responses in tests
- Verify PII is scrubbed from AI input
- Verify form validation (empty input, too-long input)
- Verify created objects (PlanTarget, metrics, section assignment)
