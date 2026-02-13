# Independent Review Guide

**Last updated:** February 2026 | **Applies to:** KoNote v1.x

KoNote is open-source software that handles sensitive client information for nonprofit social service agencies. Any agency considering adoption — or already using KoNote — can get an independent security review at any time, no vendor permission needed. This is a key advantage over proprietary case management tools where you have to trust the vendor's claims. This guide explains what you can verify, how to do it, and provides ready-made review prompts you can copy and paste.

---

## What You Can Verify

These are the specific security and privacy claims KoNote makes. Each one is verifiable in the source code.

**1. Encryption at rest** — All client names, progress notes, and outcome ratings are encrypted using Fernet, which combines AES-128-CBC encryption with HMAC-SHA256 authentication (a method that detects tampering). Encrypted fields are stored as unreadable ciphertext in the database. A database breach alone does not expose client data.

**2. Key management** — Agencies control their own encryption key. The key is stored outside the application code as an environment variable and never appears in the source repository. No one — including the KoNote developers — can read your encrypted data without your key.

**3. Audit logging** — Every data access, export, and administrative action is logged to a separate audit database. When configured as recommended, these logs are append-only and cannot be modified or deleted through the application, creating a reliable record for compliance reviews.

**4. Role-based access control** — Four roles (front desk, staff, program manager, admin) control what each person can see and do. These permissions are enforced on the server, not just in the user interface, so they cannot be bypassed by manipulating the browser.

**5. Export controls** — Elevated exports (such as bulk data downloads) have built-in time delays and generate audit entries, giving administrators visibility into data movement. Secure download links expire automatically.

**6. Demo/real data separation** — Demo users never see real client data and real users never see demo data. This separation is enforced at the database query level, not just the interface, so it cannot be accidentally circumvented.

> **Note:** The review prompts below check the code. KoNote also includes a `security_audit` management command that checks the actual data in your database. Both matter — code review verifies the design, the audit command verifies the reality.

---

## Three-Tier Review Model

KoNote uses three tiers of security review, each catching different kinds of issues.

### Tier 1: Automated (Every Code Change)

These tools run automatically whenever code is changed. Results are visible on the public GitHub repository. Agencies don't need to do anything — this happens in the background.

- **CodeRabbit** — AI-powered review of every pull request. Analyses code changes for security issues, logic errors, and best practice violations. Free for open-source repositories.
- **Semgrep** — Django-specific security rules that check for cross-site scripting (XSS), cross-site request forgery (CSRF), injection vulnerabilities, and unsafe template patterns.
- **GitHub Dependabot** — Monitors all Python dependencies for known vulnerabilities. When a vulnerability is discovered, Dependabot alerts the maintainers and automatically creates a pull request with the fix.

**CI failure policy:** Only genuinely dangerous patterns block code from being merged. Advisory findings are reviewed by the developer and addressed based on severity.

### Tier 2: AI Deep Review (Before Each Major Release)

Before each major release, structured review prompts are run against the full codebase using AI assistants (Claude, ChatGPT, Gemini, or similar tools). These reviews cover four dimensions:

1. **Security** — encryption, authentication, common vulnerabilities
2. **Privacy and compliance** — PIPEDA, PHIPA, data handling practices
3. **Deployment and operations** — configuration safety, backup, update paths
4. **Accessibility and usability** — WCAG compliance, workflow efficiency, bilingual support

Results are published as dated review reports for each major release. Agencies can also run their own review by cloning the repository and using the prompts provided in this guide.

### Tier 3: Human Expert Review (Before First Production Deployment, Then Annually)

A qualified security person reviews the application and runs dynamic testing (for example, OWASP ZAP) against a running instance. AI tools are excellent at finding patterns in code, but they are poor at finding logic flaws, business rule bypasses, and configuration mistakes in live environments. A human tester catches things automated tools miss.

Options for human review:

- **Freelance Django security specialist** — typically $500–$2,000 CAD for a focused review
- **Cybersecurity student capstone project** — many university programs require students to complete a real-world security assessment
- **OWASP chapter volunteer** — local OWASP chapters sometimes offer pro-bono reviews for nonprofits
- **Pro-bono engagement** — organisations like CyberPeace Institute and nonprofit tech networks sometimes connect agencies with volunteer security professionals

---

## What AI Review Proves (and Doesn't)

It is important to be honest about what AI-assisted code review can and cannot do.

**What it demonstrates:**
- Transparency and good-faith effort toward security
- That the codebase has been examined for common vulnerability patterns
- That privacy-relevant code paths have been identified and reviewed

**What it does not prove:**
- AI review is not a legal compliance certification. It does not replace a formal privacy impact assessment or legal opinion.
- AI review checks code as written. It cannot verify that a live deployment is configured correctly, that environment variables are set properly, or that the hosting environment is secured.
- Results are not perfectly consistent — running the same prompt twice may produce slightly different findings. This is normal for AI tools and does not indicate a problem.

**For compliance purposes** (PIPEDA, PHIPA), agencies should combine AI code review with:
- The built-in `security_audit` management command (checks your actual database)
- Organisational controls (privacy policies, staff training, breach response plans)
- A Privacy Impact Assessment tailored to your agency's specific context

---

## Review Prompts

The following prompts are designed to be copied and pasted into any AI assistant. No technical knowledge is needed beyond uploading files to an AI tool.

### For Agencies (Security and Privacy)

#### Prompt 1: Security Review

> You are reviewing an open-source Django web application called KoNote that stores sensitive client information for nonprofit social service agencies. Please conduct a security-focused code review and produce a report covering:
>
> **1. Encryption Implementation**
> - Are client names, notes, and ratings actually encrypted at rest?
> - What encryption algorithm is used? Is it current and appropriate?
> - How is the encryption key managed? Could it be accidentally exposed?
> - Are there any fields containing PII that are NOT encrypted?
>
> **2. Authentication & Authorisation**
> - Are role-based access controls enforced server-side (not just in templates)?
> - Can a lower-privilege user access higher-privilege endpoints?
> - Is the Azure AD SSO integration implemented securely?
> - Are local passwords hashed with a strong algorithm?
>
> **3. Data Export Security**
> - Are exports protected against unauthorised access?
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
> - SQL injection, Cross-site scripting (XSS), Cross-site request forgery (CSRF), Insecure direct object references, Security misconfiguration
>
> **6. Privacy Compliance**
> - Does the application support PIPEDA requirements (data portability, consent)?
> - Is there proper data separation between demo and production data?
>
> Please flag any issues found as Critical, High, Medium, or Low severity, and provide specific file paths and line numbers where possible.

#### Prompt 2: Privacy & Compliance Review

> You are reviewing KoNote, an open-source Django application that stores sensitive client data for Canadian nonprofits. Please review for privacy compliance and produce a report covering:
>
> **1. Data Minimisation** — Does the application collect only what's needed? Are there fields that store more data than necessary?
>
> **2. Purpose Specification** — Is the purpose of each data collection stated and documented? Are users informed why each field is collected?
>
> **3. Consent & Transparency** — Is consent captured before collecting personal information? Can clients see what data is held about them?
>
> **4. Accuracy** — Can clients or caseworkers correct inaccurate information? Is there an audit trail of corrections?
>
> **5. Data Portability** — Can client data be exported in a portable format? Is there a clear process for data subject access requests?
>
> **6. Data Retention & Erasure** — Is there a working erasure workflow? Does it actually delete data or just mark it inactive? Are audit records preserved after erasure (without PII)? Are retention limits enforced automatically or just documented?
>
> **7. Safeguards Proportional to Sensitivity** — Are progress notes (clinical content) protected more rigorously than non-sensitive fields? Do safeguards scale with data sensitivity?
>
> **8. Sub-Processor Accountability** — Are hosting provider responsibilities documented? Is there guidance on data processing agreements?
>
> **9. Cross-Border Considerations** — Where could data be stored? Are there CLOUD Act risks with the hosting options?
>
> **10. Breach Preparedness** — Does the application support PIPEDA's "as soon as feasible" breach notification requirement? Is there incident response documentation?
>
> Flag issues as Critical, High, Medium, or Low. Reference PIPEDA principles and PHIPA where relevant.

### For Developers and Technical Reviewers

#### Prompt 3: Deployment & Operations Review

> You are reviewing KoNote, an open-source Django application intended to be self-hosted by small nonprofits with limited IT resources. Please review for deployment reliability and produce a report covering:
>
> **1. First-Run Experience** — Can someone with basic Docker knowledge get this running? Are the instructions clear and complete? What could go wrong?
>
> **2. Configuration Safety** — Are environment variables well-documented? What happens if a required variable is missing? Are there good defaults vs. dangerous defaults?
>
> **3. Database Migrations** — Are migrations safe to run? Could any migration cause data loss? Is there rollback documentation?
>
> **4. Backup & Recovery** — Is there clear documentation for backing up and restoring? Does the encryption key management make recovery realistic?
>
> **5. Monitoring & Health** — Can an operator tell if the application is healthy? Are errors logged clearly? Is there a health check endpoint?
>
> **6. Update Path** — Can an agency update to a new version safely? What's the worst that could happen during an update?
>
> Write your findings in plain language. The audience is a nonprofit executive director or IT volunteer, not a developer.

#### Prompt 4: Accessibility & Usability Review

> You are reviewing KoNote, an open-source Django web application used by caseworkers at nonprofit social service agencies. These users are typically not tech-savvy and may be using the system under time pressure. Please review for accessibility and usability and produce a report covering:
>
> **1. WCAG 2.2 AA Compliance** — Semantic HTML, colour contrast, keyboard navigation, screen reader support, form labels, focus management in HTMX interactions.
>
> **2. Error Handling** — Are error messages helpful to a non-technical user? Do HTMX errors fail silently? Is there a global error handler?
>
> **3. Workflow Efficiency** — Can common tasks (add a note, search for a client, record a metric) be completed quickly? Are there unnecessary clicks or pages?
>
> **4. Mobile Responsiveness** — Can a caseworker use this on a tablet during a home visit?
>
> **5. Bilingual Support** — Does the French translation work? Are there untranslated strings? Does switching languages preserve state?
>
> **6. Cognitive Load** — Are there too many options on any single page? Is the navigation intuitive? Would a new caseworker understand what to do without training?

---

## How to Run Your Own Review

You do not need to be a developer to run a review. Here is the process, step by step.

1. **Go to the KoNote GitHub repository** — [github.com/[org]/konote-web](https://github.com/[org]/konote-web)
2. **Download the code** — Click the green "Code" button on GitHub, then "Download ZIP." Alternatively, if you have Git installed, clone the repository.
3. **Open your preferred AI assistant** — Claude, ChatGPT, Gemini, or any tool that can analyse code.
4. **Upload the code** — Upload the ZIP file to the AI tool, or if you are using a code-aware tool like Claude Code or Cursor, point it at the cloned repository folder.
5. **Paste a review prompt** — Copy one of the prompts above and paste it into the AI tool.
6. **Review the generated report** — The AI will produce a structured report with findings organised by severity. Share this with your team, IT consultant, or board.

If you are not comfortable doing this yourself, ask your IT consultant or a tech-savvy board member. The prompts are designed to be copy-pasted — no technical knowledge is needed beyond uploading files to an AI tool.

---

## Pre-Generated Review Reports

We publish review reports for each major release. These are generated using the prompts above, run by independent AI tools against the full codebase. Reports are dated and versioned so you can see exactly what was reviewed and when.

| Version | Date | Reviewer | Report |
|---------|------|----------|--------|
| v1.0 | — | — | *Report link will be added upon release* |

As new releases are published, review reports will be added to this table.

---

## Re-Reviewing After Updates

Because KoNote is open source, every code change is visible and auditable on GitHub. Agencies can re-run their review after any update to verify that nothing has regressed. The process is the same — download the updated code, paste a review prompt, and compare the new report against the previous one.

For agencies that want continuous assurance, the Tier 1 automated tools (CodeRabbit, Semgrep, Dependabot) run on every code change and their results are always visible on the GitHub repository. You do not need to re-run a manual review to know that automated checks are passing.

---

**KoNote** — Participant Outcome Management

*Open source. Independently verifiable. No vendor trust required.*
