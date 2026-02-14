# TODO.md — French Translation Scope (Exact)

This note defines exactly what in `TODO.md` should be translated to French, and exactly what must remain unchanged.

## Translate to French

Translate **all human-readable English prose** in `TODO.md`, including:

1. Title and section headings
   - `# Project Tasks`
   - `## Flagged`
   - `## Active Work`
   - all subsection headers (for example `### Pre-Launch Checklist`, `### UX Walkthrough`, etc.)

2. Every task description sentence in checklist items
   - In each `- [ ] ...` and `- [x] ...` line, translate the natural-language description.
   - Keep the task status marker (`[ ]` / `[x]`) and structure unchanged.

3. Explanatory paragraphs and notes
   - Introductory prose under headings (for example "All UXP tasks complete...", QA guidance notes, explanatory table notes).

4. Table labels and explanatory text
   - Column headers and explanatory wording in the "Full QA Suite Commands" table.

5. Non-code inline labels in markdown prose
   - Words like "Calibration only", "Smoke test", "Single scenario", and narrative instructions around commands.

## Do NOT translate (keep exactly as-is)

1. Task IDs and codes
   - Anything in parentheses like `(UX-ADMIN3)`, `(QA-W54)`, `(PERM-P10)`.

2. Dates and numeric values
   - Example: `2026-02-14`, `57/57`, `321`.

3. File paths, links, command names, and code snippets
   - Backticked content such as `tasks/ux-review-latest.md`, `pytest ...`, `.env.example`, `/run-scenarios`, `C:\Users\...`.

4. Product and platform proper nouns
   - `KoNote`, `Railway`, `Playwright`, `PowerShell`, `VS Code`, `Claude Code`, `Kilo Code`, `Resend.com`, `M365`, `Twilio`, `PIPEDA`, `PHIPA`, `CASL`.

5. Branch names and git literals
   - `main`, `PR #73`, environment variable names like `DEMO_EMAIL_BASE`.

6. Existing quoted UI labels that are intentionally canonical
   - Keep exact quoted literals when they represent fixed UI text tokens or route/command identifiers.

## Practical rule for execution

- For each checklist line, translate the sentence **before** the trailing metadata block(s).
- Preserve trailing metadata exactly:
  - date segment (if present)
  - task ID segment in parentheses
  - linked file references and code literals

## Completion criteria

Translation of `TODO.md` is complete when:
- No free-form English prose remains in headings, descriptions, table labels, or explanatory paragraphs.
- All technical literals listed above remain unchanged.
- Line structure, checkbox markers, task IDs, and link/command syntax are preserved.
