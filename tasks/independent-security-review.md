# Independent Security Review — Trust Through Transparency

## The Pitch

KoNote2 is open-source software that handles sensitive client information. Any agency considering adoption (or already using it) can get an **independent security review** at any time — no vendor permission needed. This is a key advantage over proprietary case management tools where you just have to trust the vendor's claims.

## What Agencies Can Verify

These are the specific claims we make that a third-party review can confirm:

1. **Encryption at rest** — All client names, notes, and outcome ratings are encrypted using Fernet (AES-128-CBC with HMAC). The encrypted fields are stored as ciphertext in the database — a database breach alone does not expose client data.

2. **Key management options** — Agencies can either:
   - Manage their own encryption key (set `FIELD_ENCRYPTION_KEY` themselves)
   - Use a hosting-managed key (provider sets it during deployment)
   - Either way, the key never touches the codebase

3. **Audit logging** — Every data access, export, and admin action is logged to a separate audit database. Logs cannot be modified through the application.

4. **Role-based access control** — Four roles (receptionist, staff, program manager, admin) with server-side enforcement. No client-side-only checks.

5. **Export controls** — Elevated exports require admin approval, have time delays, and generate audit entries.

6. **Demo/real data separation** — Demo users never see real client data and vice versa, enforced at the query level.

## How to Do a Review

### Option 1: AI-Powered Code Review (Free, Fast)

Use an AI code review tool to scan the entire codebase. Recommended tools:

- **Jules** (jules.google.com) — Google's AI code agent
- **GPT Codex** — OpenAI's code review tool
- **Claude Code** — Anthropic's CLI tool (what built this software)

Any of these can review the full codebase in minutes and produce a detailed security report.

### Option 2: Professional Penetration Test (Paid, Thorough)

Hire a security firm to do a full penetration test. The open-source codebase means they have white-box access — far more thorough than black-box testing.

### Option 3: Internal IT Review

If your agency has IT staff, they can clone the repo and review the security architecture directly.

## Suggested AI Review Prompt

Agencies can use this prompt (or write their own) with any AI code review tool:

---

> You are reviewing an open-source Django web application called KoNote2 that stores sensitive client information for nonprofit social service agencies. Please conduct a security-focused code review and produce a report covering:
>
> **1. Encryption Implementation**
> - Are client names, notes, and ratings actually encrypted at rest?
> - What encryption algorithm is used? Is it current and appropriate?
> - How is the encryption key managed? Could it be accidentally exposed?
> - Are there any fields containing PII that are NOT encrypted?
>
> **2. Authentication & Authorization**
> - Are role-based access controls enforced server-side (not just in templates)?
> - Can a lower-privilege user access higher-privilege endpoints?
> - Is the Azure AD SSO integration implemented securely?
> - Are local passwords hashed with a strong algorithm?
>
> **3. Data Export Security**
> - Are exports protected against unauthorized access?
> - Do secure download links expire properly?
> - Is there CSV injection protection?
> - Are exports logged in the audit trail?
>
> **4. Audit Logging**
> - Is the audit log stored separately from application data?
> - Can audit entries be modified or deleted through the application?
> - Are all sensitive operations logged?
>
> **5. Common Vulnerabilities (OWASP Top 10)**
> - SQL injection
> - Cross-site scripting (XSS)
> - Cross-site request forgery (CSRF)
> - Insecure direct object references
> - Security misconfiguration
>
> **6. Privacy Compliance**
> - Does the application support PIPEDA requirements (data portability, consent)?
> - Is there proper data separation between demo and production data?
>
> Please flag any issues found as Critical, High, Medium, or Low severity, and provide specific file paths and line numbers where possible.

---

## Documentation Locations

This messaging should appear in:

1. **Security documentation** (`docs/security-operations.md` or similar) — detailed section on independent verification
2. **Website / landing page** — brief trust statement with link to the review prompt
3. **README or Getting Started** — mention that independent review is encouraged

## Messaging for Website

Suggested copy:

> ### Trust, But Verify
>
> KoNote2 encrypts all client names, notes, and outcome ratings at rest using AES encryption. Your encryption key stays with you — it never touches our codebase.
>
> But don't just take our word for it.
>
> Because KoNote2 is open source, any agency can run an independent security review at any time — using free AI tools, your own IT staff, or a professional security firm. We even provide a ready-made review prompt to get you started.
>
> Security-focused code reviews happen automatically every time code changes. And because the code is public, those reviews are verifiable too.

## Ongoing Security Story

For the "automatic security reviews" claim, we can point to:

- Pre-commit hooks that check for common issues
- AI-assisted development where security is reviewed with every change
- Open-source community visibility — anyone can flag issues at any time
- Agencies can re-run their review after any update to verify nothing has regressed

## TODO Items

- [x] Add "Independent Security Review" section to security docs (SEC-DOC1) — 2026-02-06
- [x] Add review prompt template to docs or repo (SEC-DOC2) — 2026-02-06
- [x] Add "Trust, But Verify" section to website/landing page (SEC-WEB1) — 2026-02-06
- [x] Mention independent review capability in README (SEC-DOC3) — 2026-02-06
