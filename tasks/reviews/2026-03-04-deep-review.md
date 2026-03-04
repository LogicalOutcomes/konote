# Deep Code Review — 2026-03-04

**Review type:** Comprehensive 6-dimension deep review
**Reviewer:** Claude Opus 4.6 (automated, 6 parallel agents)
**Codebase:** KoNote Web (Django 5 / PostgreSQL 16)
**Commit:** `9a7cfe9` (main branch)

---

## Executive Summary

| Dimension | Verdict | Critical | High | Medium | Low |
|-----------|---------|----------|------|--------|-----|
| A: Security (OWASP + RBAC + Encryption) | CONDITIONAL PASS | 0 | 0 | 3 | 5 |
| B: Privacy (PIPEDA / PHIPA) | CONDITIONAL PASS | 0 | 0 | 3 | 4 |
| C: Accessibility (WCAG 2.2 AA / AODA) | CONDITIONAL PASS | 0 | 0 | 2 | 4 |
| D: Deployment Reliability | PASS WITH WARNINGS | 0 | 0 | 1 | 3 |
| E: AI Governance (LLM Safety) | PASS WITH WARNINGS | 0 | 0 | 2 | 4 |
| F: Bilingual (EN/FR) | PASS WITH WARNING | 0 | 0 | 0 | 1 |
| **Total** | | **0** | **0** | **11** | **21** |

**No Critical or High findings.** The codebase demonstrates a mature security, privacy, and accessibility posture for a healthcare-adjacent Canadian nonprofit application. All 11 security gate checks pass. PHIPA cross-program consent enforcement is robust (fail-closed design). Translation coverage is 100% (5,066 entries). Deployment stack has strong security defaults with comprehensive startup checks.

The 11 Medium findings are incremental improvements, not fundamental design flaws.

---

### Top 5 Most Important Findings

1. **AI note_id hallucination path (E-WARNING-2)** — The AI insights system prompt requests `note_id` in responses but never sends note IDs to the AI. The AI fabricates IDs that are used to generate links in the template. A hallucinated ID could coincidentally match a real note PK, creating an unintended access path. Fix: remove `note_id` from prompt or inject correct IDs post-validation.

2. **Registration email hash uses plain SHA-256 (B-C-2)** — `RegistrationSubmission` uses unkeyed `hashlib.sha256()` for email deduplication, while the portal uses HMAC-SHA-256 with a secret key. Plain SHA-256 hashes of email addresses are reversible via rainbow tables. Fix: migrate to HMAC-SHA-256 consistent with portal.

3. **CSP `unsafe-inline` for scripts (A-F2)** — `script-src` includes `'unsafe-inline'` for Chart.js initialisation, significantly weakening XSS mitigation. Fix: migrate to nonce-based CSP or move inline scripts to external files.

4. **EMAIL_HASH_KEY empty string default (A-F1 / B-C-3)** — If `EMAIL_HASH_KEY` is not set and `DEMO_MODE` is False, HMAC operations use an empty key, weakening email hash resistance. Fix: add `require_env("EMAIL_HASH_KEY")` or a conditional check.

5. **Standalone pages missing skip nav + hardcoded lang (C-FAIL)** — `500.html`, `offline.html`, `auth/mfa_verify.html`, and `surveys/public_thank_you.html` bypass `base.html` and lack skip navigation, `<main>` landmarks, and dynamic `lang` attributes. These are WCAG 2.2 AA compliance failures.

---

## Deduplication Notes

The following findings were identified by multiple agents. Per the cross-prompt deduplication table, ownership is assigned to prevent double-counting:

| Concern | Primary Owner | Also Found In | Resolution |
|---------|--------------|---------------|------------|
| EMAIL_HASH_KEY default | Agent A (F1) | Agent B (C-3) | A owns security framing; B's C-3 counted once |
| Encryption self-test dead variable | Agent A (F3) | Agent B (C-7) | A owns; B's C-7 counted once |
| PII in AI prompts | Agent E | A (PASS), B (PASS) | E owns (WARNING-1 for log leakage) |
| Rate limiting (public) | Agent A (F6: survey) | Agent E (WARNING-3: AI 429 UX) | Split: A owns survey limits, E owns AI UX |
| DV-safe access control | Agent A (PASS) | Agent B (PASS) | No finding — both passed |
| Suppression thresholds | Agent A (PASS) | Agent B (PASS) | No finding — both passed |
| Bilingual error messages | Agent F (no finding) | Agent C (ADVISORY: portal survey) | F owns translation; C owns screen reader |

---

## Prioritised Action List

### Fix Now (Medium — address before next production deploy)

- [ ] **[SEC-M1]** Fix `EMAIL_HASH_KEY` empty string default — add validation when not in demo mode — Security — `base.py:329`
- [ ] **[SEC-M3]** Fix dead variable `_master_fernet` → `_fernet` in encryption self-test finally block — Security — `encryption.py:227`
- [ ] **[AI-M1]** Remove `note_id` from AI insights system prompt, or inject correct IDs post-validation using `quote_source_map` — AI Governance — `ai.py:467`, `_insights_ai.html:51-53`

### Fix Soon (Medium — address in next sprint)

- [ ] **[SEC-M2]** Migrate from CSP `unsafe-inline` to nonce-based CSP or external JS files for Chart.js — Security — `base.py:261`
- [ ] **[PRIV-M1]** Add retention expiry field or periodic cleanup command for Communication model — Privacy — `communications/models.py`
- [ ] **[PRIV-M2]** Migrate RegistrationSubmission email hash from plain SHA-256 to HMAC-SHA-256 (requires data migration) — Privacy — `registration/models.py`
- [ ] **[PRIV-M3]** Encrypt `RegistrationSubmission.field_values` JSON or document custom field PII constraints — Privacy — `registration/models.py`
- [ ] **[AI-M2]** Enforce HTTPS for remote `INSIGHTS_API_BASE` endpoints (allow HTTP for localhost only) — AI Governance — `ai.py:361`
- [ ] **[A11Y-M1]** Fix standalone pages: add skip nav, `<main>` landmark, dynamic `lang` to `500.html`, `offline.html`, `mfa_verify.html`, `public_thank_you.html` — Accessibility — 4 templates
- [ ] **[A11Y-M2]** Change public survey rating scale from `<div role="group">` to `<fieldset><legend>` to match portal pattern — Accessibility — `public_form.html:110`
- [ ] **[DEPLOY-M1]** Complete `rotate_tenant_key` to include data re-encryption, or document that it must not be used without companion command — Deployment — `rotate_tenant_key.py`

### Consider Later (Low + recommendations)

- [ ] **[SEC-L1]** Standardise token entropy to `secrets.token_urlsafe(48)` across all token generation — Security
- [ ] **[SEC-L2]** CSP `unsafe-inline` for styles (documented Pico CSS dependency) — Security
- [ ] **[SEC-L3]** Review public survey rate limit 30/h after launch based on traffic patterns — Security
- [ ] **[SEC-L4]** Improve X-Forwarded-For handling for multi-proxy environments — Security
- [ ] **[SEC-L5]** Add expiry field to CalendarFeedToken — Security
- [ ] **[PRIV-L1]** Add explicit audit logging for registration submissions — Privacy
- [ ] **[PRIV-L2]** Document whether AuditLog old_values/new_values contain PII; encrypt audit DB at rest — Privacy
- [ ] **[AI-L1]** Replace AI response log snippets with length/hash indicators to reduce PII surface — AI Governance
- [ ] **[AI-L2]** Add HTTP 429 handling to client-side HTMX error handler — AI Governance
- [ ] **[AI-L3]** Document `INSIGHTS_API_*` settings in `base.py` and `.env.example` — AI Governance
- [ ] **[AI-L4]** Add operator data residency guidance mapping AI tiers to data destinations — AI Governance
- [ ] **[DEPLOY-L1]** Add retry logic to `scripts/backup-vps.sh` — Deployment
- [ ] **[DEPLOY-L2]** Consider rotating demo Fernet key periodically — Deployment
- [ ] **[DEPLOY-L3]** Create documented restore-from-backup procedure — Deployment
- [ ] **[A11Y-L1]** Add submit button fallback for `onchange` form submits (program switcher, executive dashboard) — Accessibility
- [ ] **[A11Y-L2]** Add `prefers-reduced-motion` check to disable Chart.js animations — Accessibility
- [ ] **[A11Y-L3]** Translate portal survey "Could not save" message — Accessibility
- [ ] **[A11Y-L4]** Add CSS `:has()` fallback for scale pill focus indicators — Accessibility
- [ ] **[BILIN-L1]** Install pre-commit hook for `.html`/`.po` synchronisation — Bilingual

---

## Notable Strengths

The review identified several security and privacy engineering patterns above baseline expectations:

1. **Fail-closed PHIPA consent filtering** — Cross-program notes hidden by default; consent must be explicitly recorded.
2. **Two-person rule for DV flag removal** — Prevents a single compromised account from exposing DV-safe clients.
3. **Separate audit database with INSERT-only permissions** — Full app DB compromise cannot tamper with audit logs.
4. **Portal timing equalisation** — `make_password("dummy-timing-equalisation")` on email miss prevents enumeration.
5. **Two-pass PII scrubbing before AI** — Regex patterns + known names with word boundaries, longest-first.
6. **100% translation coverage** — 5,066 entries, zero untranslated, zero fuzzy.
7. **DV small-circle hiding** — When blocked member reduces visible count below 2, entire circle hidden.
8. **Emergency logout with sendBeacon** — DV-safe panic button works even during navigation.
9. **Agency data export with AES-256-GCM** — 600K PBKDF2 iterations, Diceware passphrase, out-of-band delivery.
10. **Suppression with secondary suppression** — Prevents derivation by subtraction in funder reports.

---

## Individual Reports

- [Security](2026-03-04-security.md)
- [Privacy (PIPEDA / PHIPA)](2026-03-04-privacy.md)
- [Accessibility (WCAG 2.2 AA / AODA)](2026-03-04-accessibility.md)
- [Deployment Reliability](2026-03-04-deployment.md)
- [AI Governance](2026-03-04-ai-governance.md)
- [Bilingual Compliance (EN/FR)](2026-03-04-bilingual.md)

---

*Combined report generated by Claude Opus 4.6 on 2026-03-04. This is an automated review and should be validated by qualified professionals before acting on findings.*
