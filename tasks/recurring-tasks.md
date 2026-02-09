# Recurring Tasks

Chores to run periodically. Not tracked in TODO.md — check back here as needed.

| Task | When | How |
|------|------|-----|
| UX walkthrough | After UI changes | `pytest tests/ux_walkthrough/ -v`, review `tasks/ux-review-latest.md` (UX-WALK1) |
| French translation review | After adding strings | Have a French speaker spot-check. Run `python manage.py check_translations` (I18N-REV1) |
| Redeploy to Railway | After merging to main | Push to `main`, Railway auto-deploys. See `docs/deploy-railway.md` (OPS-RAIL1) |
| Redeploy to FullHost | After merging to main | Push to `main`, trigger redeploy. See `docs/deploy-fullhost.md` (OPS-FH1) |
| Code review | Periodically | Open Claude Code, "review the codebase". See `tasks/code-review-process.md` (REV1) |

## Full QA Suite (QA-FULL1)

Run after major releases or UI changes. Creates 4 reports.

1. **konote-web:** Run `/run-scenario-server` (captures scenario screenshots)
2. **qa-scenarios:** Run `/run-scenarios` (evaluates scenarios, creates satisfaction report + improvement tickets)
3. **konote-web:** Run `/capture-page-states` (captures page screenshots)
4. **qa-scenarios:** Run `/run-page-audit` (evaluates pages, creates page audit report + tickets)
5. *(Optional)* **konote-web:** Run `/process-qa-report` (expert panel + action plan)

All reports saved to `qa-scenarios/reports/` with date stamps.
