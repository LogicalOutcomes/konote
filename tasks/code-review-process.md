# Code Review Process (REV1)

## What This Is

A periodic code review you run with Claude Code in VS Code. It catches issues that accumulate over time — inconsistencies, security gaps, dead code, missing tests — before they become problems.

## When to Do It

- **After finishing a major phase** (you just finished Phase H + cleanup — good time)
- **Before a production deploy** to a new agency
- **Every 2-4 weeks** during active development
- **After merging a large PR** with many files changed

## How to Run a Review

Open Claude Code in VS Code and use one of these prompts depending on what you want checked:

### Full Review (recommended first time)

> Review the codebase for code quality, security, and consistency issues. Focus on:
> 1. Security — encryption, auth, permissions, input validation, OWASP top 10
> 2. Code quality — dead code, duplicated logic, unclear naming
> 3. Consistency — are patterns used the same way everywhere (e.g., encrypted field access, audit logging, demo isolation)
> 4. Test coverage — are there views or features without tests
> 5. Translation — are there untranslated strings or stale .po entries
> 6. Accessibility — WCAG 2.2 AA compliance in templates
>
> Give me a prioritised list of findings: critical first, then important, then nice-to-have.

### Focused Reviews (pick one area)

**Security only:**
> Review the codebase for security issues — authentication, authorization, encryption, input validation, CSRF, XSS, SQL injection, and data leakage risks.

**Consistency only:**
> Check that these patterns are used consistently across the codebase:
> - Encrypted field access via properties (not direct _encrypted fields)
> - Demo isolation (get_client_queryset)
> - Audit logging for sensitive actions
> - Permission checks on all views
> - Error handling in HTMX responses

**Dead code and cleanup:**
> Find dead code, unused imports, unreachable branches, commented-out code, and files that aren't referenced anywhere.

**Test gaps:**
> Identify views, forms, and management commands that don't have corresponding tests. Prioritise by risk — admin actions and data-modifying views first.

## What to Do with Findings

1. Claude will give you a prioritised list
2. **Critical issues** (security, data loss risk) — fix immediately
3. **Important issues** (bugs, inconsistencies) — add to Active Work in TODO.md
4. **Nice-to-have** (style, minor cleanup) — add to Parking Lot or fix inline

## Review History

Track completed reviews here so you know what's been checked:

| Date | Scope | Findings | Notes |
|------|-------|----------|-------|
| 2026-02-07 | Full (security, quality, tests, i18n, a11y) | 4 critical, 6 high, 20+ medium | See `tasks/code-review-2026-02-07.md` |
