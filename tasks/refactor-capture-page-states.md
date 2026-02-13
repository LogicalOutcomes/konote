# Task: Refactor `/capture-page-states` Skill

## Context

The `/run-scenario-server` skill was recently overhauled because it kept failing — it mixed instructions for Claude with shell code, embedded Python implementations, had hardcoded paths, used inconsistent shell syntax (bash vs PowerShell vs CMD), and didn't handle prerequisites automatically. An expert panel recommended a pattern: short imperative skill files + shared `preflight` management command + reference docs in `tasks/`. That pattern was implemented and works well.

The `/capture-page-states` skill at `.claude/commands/capture-page-states.md` has all the same problems but **worse** — it's 538 lines and embeds two entire Python files (~300 lines of code). It needs the same treatment.

## The Problem (Specific Issues)

1. **Embedded Python code** (lines 106-281, 287-438): The skill file contains full implementations of `tests/utils/page_capture.py` and `tests/integration/test_page_capture.py`. Claude Code skill files should contain *instructions for Claude*, not code to copy-paste. When Claude reads this, it tries to create these files verbatim — but the code is speculative (written before the test infrastructure existed) and likely broken.

2. **Mixed audiences**: The top half reads like instructions ("Run preflight, start the server"), the bottom half reads like a developer spec ("Create this file with this code"). A skill file's only audience is Claude.

3. **Reference bloat**: Troubleshooting, state capture strategies, output format specs, manifest JSON schema — all useful as reference, but they make the skill file too long for Claude to reliably follow.

4. **Hardcoded paths**: No hardcoded paths remain (preflight handles that now), but the embedded code has hardcoded relative paths like `Path(__file__).parent.parent.parent.parent / "konote-qa-scenarios"`.

5. **Speculative implementation**: The `navigate_to_state()` function has bare `except:` blocks, placeholder logic (`pass` in the language toggle), and hardcoded ID replacements. This was a spec, not working code.

6. **Stale prerequisite section**: Lines 11-27 were already updated to reference preflight, but the rest of the file was not aligned.

## The Model to Follow

Look at the improved `/run-scenario-server` skill at `.claude/commands/run-scenario-server.md` (53 lines). It follows this pattern:

- **Line 1**: Title
- **Lines 3-5**: One-sentence description + "This is TEST INFRASTRUCTURE" callout
- **Lines 9+**: Numbered steps as imperative instructions
  - Step 1: Run preflight (handle warnings)
  - Step 2: Start dev server if not running (with specific success criteria)
  - Step 3: Run the actual command (with timeout warning)
  - Step 4: Report results (what to tell the user)
  - Next steps: What to do after
- **No code blocks** except the single pytest command to run
- **No embedded Python**, no troubleshooting, no reference tables
- Reference material lives in `tasks/qa-scenario-reference.md`

Also look at `/process-qa-report` at `.claude/commands/process-qa-report.md` — it's already in good shape (imperative steps, no embedded code, clear success criteria at each step).

## What To Do

### Step 1: Understand What Exists

Read these files to understand the current state:
- `.claude/commands/capture-page-states.md` (the skill to rewrite)
- `.claude/commands/run-scenario-server.md` (the model to follow)
- `.claude/commands/process-qa-report.md` (another good example)
- `tasks/qa-scenario-reference.md` (reference extracted from the old run-scenario-server)
- `apps/admin_settings/management/commands/preflight.py` (the shared preflight command)

Check whether any of the files referenced in the skill already exist:
- `tests/utils/page_capture.py` — does it exist?
- `tests/integration/test_page_capture.py` — does it exist?
- `konote-qa-scenarios/pages/page-inventory.yaml` — does it exist?

### Step 2: Decide What to Keep vs. Extract vs. Delete

The 538-line skill file has content in several categories. Decide what happens to each:

| Content | Current Location | Action |
|---------|-----------------|--------|
| Prerequisites + server startup | Lines 11-27 | KEEP (already good) |
| "What This Skill Does" overview | Lines 30-42 | KEEP (condense to 2-3 sentences at top) |
| File structure / output paths | Lines 44-97 | EXTRACT to reference doc |
| `page_capture.py` implementation | Lines 106-281 | DELETE from skill. If the file doesn't exist yet, create it properly as a real file — not embedded in the skill |
| `test_page_capture.py` implementation | Lines 287-438 | Same as above |
| Usage steps | Lines 441-463 | KEEP (these become the core steps) |
| State capture strategies table | Lines 467-480 | EXTRACT to reference doc |
| Troubleshooting | Lines 484-506 | EXTRACT to reference doc |
| Output summary format | Lines 510-525 | KEEP (this is what Claude should report) |
| QA pipeline integration | Lines 529-537 | Already in `qa-scenario-reference.md`, DELETE |

### Step 3: Rewrite the Skill File

Rewrite `.claude/commands/capture-page-states.md` following the same pattern as `run-scenario-server.md`:

**Target: ~50-60 lines.** Structure:

```
# Capture Page States: Screenshot Generator for Page Audit

One-sentence description.

**This is TEST INFRASTRUCTURE**, not application code.

---

## Steps

### Step 1: Run preflight check
(Same as run-scenario-server — run preflight, handle warnings)

### Step 2: Start the dev server if not running
(Same as run-scenario-server — check HTTP 200, start if needed)

### Step 3: Verify page inventory exists
(Check that konote-qa-scenarios/pages/page-inventory.yaml exists.
If not, tell user and STOP.)

### Step 4: Run the page capture tests
(The actual pytest command — with timeout warning)

### Step 5: Report results
(What to tell the user — screenshot count, manifest location, missing screenshots)

### Next steps
(Run /run-page-audit in the qa-scenarios repo)
```

Key principles:
- Every instruction is imperative ("Run X", "Check Y", "If Z, STOP")
- Success criteria after every step (what does "pass" look like?)
- One code block max (the pytest command)
- No Python implementations, no JSON schemas, no troubleshooting

### Step 4: Create Reference Doc (if Needed)

If there's enough reference material to justify it, create `tasks/page-capture-reference.md` with:
- State capture strategies table
- Screenshot naming convention and output paths
- Manifest JSON schema
- Troubleshooting common errors
- Page inventory format

If the reference material fits naturally into the existing `qa-scenario-reference.md`, add it there instead of creating a new file.

### Step 5: Handle the Python Files

If `tests/utils/page_capture.py` and `tests/integration/test_page_capture.py` don't exist yet:
- **Do NOT create them from the embedded code.** The embedded code was speculative.
- Instead, note in the skill file that these files need to be created as a separate task.
- Add a TODO item if appropriate.

If they DO exist:
- Check if they work. Run them.
- The skill file should reference them, not embed them.

### Step 6: Run a Quick Review

After rewriting, run `/review-quick` to check the changes.

## Design Principles (from Expert Panel)

These principles were established during the run-scenario-server rewrite:

1. **Skill files are for Claude, not humans.** Write imperative instructions, not documentation.
2. **Shared infrastructure goes in management commands.** `preflight` handles env checks for all skills.
3. **Reference material goes in `tasks/`.** Keep skills short; link to reference docs for advanced options.
4. **No embedded code in skill files.** Code belongs in actual files that can be tested and versioned.
5. **Every step has success criteria.** Claude should know what "pass" looks like before proceeding.
6. **PowerShell is the default shell.** Use `$env:VAR = "value"` syntax, not `set VAR=value` or `export VAR=value`.
7. **Paths come from preflight.** Don't hardcode `C:/Users/gilli/...` in skill files.

## Files That Will Change

- `.claude/commands/capture-page-states.md` — complete rewrite (538 lines -> ~50-60 lines)
- `tasks/page-capture-reference.md` — NEW (or append to `tasks/qa-scenario-reference.md`)
- Possibly `tests/utils/page_capture.py` and `tests/integration/test_page_capture.py` — only if they already exist and need fixes

## Verification

After the rewrite:
1. The skill file should be under 70 lines
2. It should have no embedded Python code
3. It should have no hardcoded paths
4. Steps 1-2 should be identical (or nearly so) to `run-scenario-server.md`
5. Running `/review-quick` should show no issues with the changes
