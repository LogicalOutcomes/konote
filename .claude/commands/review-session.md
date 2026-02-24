# /review-session

Thorough end-of-session review of all code changes, followed by an expert panel discussion. Use this before merging, deploying, or wrapping up a session. For quick mid-session checks, use `/review-quick` instead.

## Process

### Step 1: Gather All Changes from This Session

If this is a git repository, run:
```bash
git diff HEAD
git status
git log --oneline --since="today"
```

Tell the user what commit range you're reviewing so they can confirm it's the right scope.

If not a git repository, review files discussed in this session instead.

### Step 2: Review the Changes

Review the diffs first. Only read full files when the diff doesn't provide enough context to assess an issue. Review for:

**Correctness**
- Logic errors, off-by-one bugs, race conditions
- Missing error handling or edge cases
- Broken assumptions about data types or state

**Security**
- Injection vulnerabilities (SQL, XSS, command injection)
- Secrets or credentials accidentally included
- Missing authentication/authorisation checks
- OWASP Top 10 issues

**Quality**
- Dead code or unused imports introduced
- Overly complex solutions where simpler ones exist
- Copy-paste duplication that should be abstracted
- Inconsistency with existing code patterns in the project

**Testing**
- If the project has tests, were they added or updated alongside the code changes?
- Flag if code changed but tests didn't

**Framework & Language Best Practices**
- Check the project's CLAUDE.md and tech stack for framework-specific rules
- Flag violations of whatever conventions the project already follows

**Accessibility**
- WCAG 2.2 AA compliance for any template/frontend changes
- Missing alt text, aria labels, semantic HTML issues

### Step 3: Write the Review Report

Explain all issues in plain language that a non-developer can understand. Be concise — if a category has no issues, say so in one sentence. Don't pad sections with non-findings.

**Lead with the action list** (this is what the user needs most):

1. **Fix now** — critical issues that should be resolved before merging/deploying
2. **Fix soon** — important issues to address in the next session
3. **Consider later** — suggestions that can wait

Then provide supporting detail in these sections:

1. **Summary** — one paragraph overview of what was built/changed
2. **Critical Issues** — things that MUST be fixed (bugs, security holes)
3. **Warnings** — things that SHOULD be fixed (quality, maintainability)
4. **Suggestions** — things that COULD be improved (nice-to-haves)
5. **What Looks Good** — acknowledge solid work

Be specific: reference file names and line numbers. Don't sugarcoat — this is a critical review. But also don't invent problems that aren't there.

### Step 4: Convene Expert Panel

After completing the review, use the **convening-experts** skill to discuss the report. Invoke it with the Skill tool, passing the review report as context.

The panel should include perspectives relevant to the changes (e.g., security engineer, accessibility expert, UX designer — whatever fits the code that was changed).

The experts should:
- Prioritise and contextualise the findings for a non-developer audience
- Debate the critical issues and whether the severity ratings are correct
- Suggest concrete solutions for each issue

### Step 5: Update Final Recommendations

After the expert discussion, revise the prioritised action list from Step 3 if the panel changed any severity ratings or priorities. Present the final version clearly.
