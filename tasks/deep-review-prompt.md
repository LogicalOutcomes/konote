# Deep Code Review — All 6 Dimensions

**Purpose:** Run all six review prompts from `tasks/code-review-framework.md` in a single session using parallel agents. Each agent runs independently with its own checklist and produces a structured report.

**When to use:** Quarterly, before major releases, or when a new agency is evaluating KoNote.

**Time:** ~30-60 minutes (agents run in parallel).

---

## How to Run

Paste the prompt below into a **new Claude Code conversation** (fresh context). It will launch 6 agents in parallel, one per review dimension, then synthesize findings.

---

## Prompt

> Run a comprehensive code review of the KoNote codebase across all 6 review dimensions defined in `tasks/code-review-framework.md`. Use parallel agents — one per dimension — to maximise speed.
>
> **Before launching agents:**
> 1. Read `tasks/code-review-framework.md` to get the full prompt text for each dimension (Prompts A through F)
> 2. Read `tasks/code-review-framework.md` Part 4.5 (Cross-Prompt Deduplication) so you understand which prompt owns which concern
>
> **Launch 6 agents in parallel, one per prompt:**
>
> Each agent should:
> - Read the full prompt text for its assigned dimension from `tasks/code-review-framework.md`
> - Read every file listed in that prompt's Scope section
> - Work through every checklist item, noting PASS / FAIL / NOT APPLICABLE with file:line evidence
> - Produce the full output in the format specified by the prompt
> - Be thorough — read files deeply, trace code paths, check for edge cases
>
> **Agent assignments:**
> 1. **Agent A — Security (OWASP + RBAC + Encryption):** Use Prompt A. This is the largest review — read all 40+ files, check all 11 gate checks, trace all 15 RBAC attack scenarios, verify all 9 encryption checks.
> 2. **Agent B — Data Privacy (PIPEDA/PHIPA):** Use Prompt B. Check all 10 PIPEDA principles, the PHIPA cross-program consent section, and breach readiness. Pay special attention to `export_agency_data.py` demo/real data boundaries and suppression thresholds.
> 3. **Agent C — Accessibility (WCAG 2.2 AA / AODA):** Use Prompt C. Review templates across all three surfaces (staff UI, participant portal, public surveys). Check HTMX, Chart.js, and portal-specific accessibility.
> 4. **Agent D — Deployment Reliability:** Use Prompt D. Review Dockerfile, entrypoint.sh, all startup phases, ghost migration healer, seed commands, and hosting provider compatibility.
> 5. **Agent E — AI Governance (LLM Integration Safety):** Use Prompt E. Trace every data flow from user input through PII scrubbing to external API call. Verify feature toggles fail closed. Check rate limiting.
> 6. **Agent F — Bilingual Compliance (EN/FR):** Use Prompt F. Count untranslated strings using `python manage.py translate_strings --dry-run` (do NOT use `grep 'msgstr ""'`). Check language switching, bilingual survey content, WCAG 3.1.2, and export headers.
>
> **After all agents complete:**
> 1. Collect all findings from all 6 agents
> 2. Deduplicate using the cross-prompt deduplication table in Part 4.5
> 3. Produce a **combined executive summary**:
>    - Overall status per dimension (PASS / FAIL / WITH FIXES)
>    - Total findings by severity (Critical / High / Medium / Low)
>    - Top 5 most important findings across all dimensions
> 4. Produce a **prioritised action list**:
>    - **Fix now** — Critical and High findings that block production readiness
>    - **Fix soon** — Medium findings to address in the next session
>    - **Consider later** — Low findings and recommendations
> 5. Save the combined report to `../konote-qa-scenarios/reviews/YYYY-MM-DD/deep-review.md` (use today's date). Review results go in the private QA repo, not this public repo.
> 6. Save each individual dimension report to `../konote-qa-scenarios/reviews/YYYY-MM-DD/{dimension}.md`
> 7. Create tasks in TODO.md for any Critical or High findings

---

## What to Expect

- Each agent reads 10-40 files and works through its checklist independently
- The security agent (A) takes longest because it has the most files and scenarios
- The bilingual agent (F) may run a management command to count translations
- After all agents finish, you'll get a combined report with deduplicated findings
- Typical output: 0-2 Critical, 3-8 High, 10-20 Medium, 5-15 Low findings across all dimensions

## After the Review

1. Review the combined report — focus on the "Fix now" list
2. Create a feature branch for fixes: `git checkout -b fix/deep-review-YYYY-MM-DD`
3. Fix Critical issues first, then High
4. Add the review date to the history table in `tasks/code-review-process.md`
5. The next deep review should reference this one and track what was fixed
