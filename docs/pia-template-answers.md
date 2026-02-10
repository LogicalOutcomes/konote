# Privacy Impact Assessment — Template Answers

**Last updated:** February 2026 | **Applies to:** KoNote v1.x

---

This document provides template answers for common Privacy Impact Assessment (PIA) questions about KoNote. These answers describe the software's built-in privacy features. You should adapt them to reflect your agency's specific configuration, policies, and procedures. This document is not legal advice — consult your privacy officer or legal counsel for your specific situation.

**Instructions:** Copy the answers below and adapt them for your agency. Text in [square brackets] needs to be replaced with your agency's specific information.

---

## Questions and Answers

### Q1. What personal information does the system collect?

**A:** KoNote collects the following personal information about program participants: first name, middle name, last name, preferred name, date of birth, and contact information (email, phone). It also stores progress notes written by caseworkers, outcome measurements, and any custom fields defined by the agency. Custom fields can be marked as "sensitive" by the agency administrator, which triggers additional encryption protection.

---

### Q2. What is the purpose of collecting this information?

**A:** Personal information is collected to deliver [program/service name] services to participants, track progress toward agreed-upon outcomes, generate reports for funders, and meet regulatory record-keeping requirements. The purpose of each data collection is specified during program setup by the agency administrator.

---

### Q3. Where is personal information stored?

**A:** Personal information is stored in a PostgreSQL database hosted by [your hosting provider, e.g., Railway.com]. All personally identifiable fields — including names, dates of birth, contact information, and progress notes — are encrypted at rest using AES-128 encryption with HMAC-SHA256 authentication (Fernet). The database and the encryption key are stored separately. A database breach alone would not expose readable client data.

---

### Q4. Who has access to personal information?

**A:** Access is controlled by four role levels, enforced on the server (not just in the user interface):

- **Front desk** — Can see limited client fields (e.g., name, program enrolment) but not full records or progress notes.
- **Staff** — Can see full records for clients in their assigned programs only.
- **Program manager** — Can see and export data for clients in their programs.
- **Admin** — Can configure the system, manage users, and export data across all programs. Admins do not automatically see client records unless they also have a program role.

All data access is logged to a separate audit database.

---

### Q5. Is the information encrypted?

**A:** Yes. All personally identifiable information is encrypted at rest in the database using Fernet encryption (AES-128-CBC with HMAC-SHA256 authentication). This includes client names, dates of birth, contact information, progress notes, and any custom fields marked as sensitive. The encryption key is stored as an environment variable on the hosting platform, separate from the database and codebase. Data is also encrypted in transit using HTTPS/TLS.

---

### Q6. How is access to personal information logged?

**A:** Every data access, export, and administrative action is logged to a separate audit database. Audit entries include who accessed what data, when, and from what IP address. The audit database is configured with write-only permissions for the application — audit entries cannot be modified or deleted through KoNote. Audit logs can be reviewed through the web interface (Admin > Audit Logs) or queried directly.

---

### Q7. How long is personal information retained?

**A:** KoNote stores personal information until it is explicitly deleted by an authorised user through the erasure workflow. [Your agency should define and document specific retention periods based on program requirements, funder agreements, and applicable legislation. For example: "Client records are retained for 7 years after the last service date, then deleted through the erasure process."]

---

### Q8. How is personal information deleted when no longer needed?

**A:** KoNote includes a formal erasure workflow. A staff member or program manager requests erasure, and all program managers for the client's programs must approve. Upon approval, all personally identifiable information is permanently deleted — not just marked inactive. This includes the client record, all progress notes, outcome measurements, custom field values, and alerts. An audit record of the erasure is preserved (recording who requested it, who approved it, and counts of deleted records) but contains no personal information.

---

### Q9. Can individuals access or correct their personal information?

**A:** Yes. Caseworkers can update client information through the application at any time. For formal data access requests, staff can export a single client's data in a portable format, selecting which sections to include (plans, notes, metrics, events, custom fields). This export capability supports PIPEDA's data portability requirements. [Your agency should document the process for clients to submit access or correction requests.]

---

### Q10. What happens in the event of a data breach?

**A:** KoNote includes several features that support breach response:

- All data access is logged, allowing investigation of what was accessed and by whom.
- The encryption key can be rotated immediately, re-encrypting all data with a new key.
- The Django SECRET_KEY can be rotated to invalidate all active sessions.
- The built-in security audit command can verify data integrity after an incident.

[Your agency must have a breach response plan that includes: how to detect breaches, who is responsible for investigation, notification procedures (PIPEDA requires notification "as soon as feasible" to the Privacy Commissioner and affected individuals if there is a real risk of significant harm), and documentation requirements.]

---

### Q11. Is personal information transferred outside Canada?

**A:** [This depends on your hosting provider. If using Railway.com, data may be stored in the United States. If using a Canadian hosting provider or self-hosting in Canada, data remains in Canada. Document your specific hosting arrangement here.] KoNote's encryption means that even if data is stored outside Canada, it is encrypted at rest and the encryption key can be managed separately by the agency. However, agencies subject to PHIPA or handling particularly sensitive data should consider hosting within Canada to avoid CLOUD Act implications.

---

### Q12. What security measures protect personal information?

**A:** KoNote implements the following security measures:

- **Encryption at rest** — All PII encrypted with AES-128 (Fernet).
- **Encryption in transit** — HTTPS/TLS for all connections.
- **Role-based access control** — Four role levels, enforced server-side.
- **Audit logging** — Separate, append-only audit database.
- **Strong password hashing** — Argon2id (when using local authentication).
- **Session management** — Automatic logout after 8 hours of inactivity.
- **Export controls** — Time delays on bulk exports, recipient tracking.
- **Multi-factor authentication** — Available through Azure AD SSO integration.
- **CSRF protection** — Django's built-in cross-site request forgery prevention.
- **CSV injection protection** — Sanitised export files safe to open in spreadsheet applications.

[Your agency should also document organisational security measures: staff training, acceptable use policies, physical security of devices, etc.]

---

### Q13. Has the system been independently reviewed?

**A:** KoNote is open-source software (MIT licence). The full source code is publicly available on GitHub, allowing independent security review at any time. Automated security scanning tools (CodeRabbit, Semgrep, GitHub Dependabot) run on every code change. AI-powered deep security reviews are conducted before each major release and published as dated reports. [If your agency has commissioned an independent review or penetration test, reference it here.]

---

### Q14. Who is responsible for privacy compliance?

**A:** KoNote provides technical privacy controls, but privacy compliance is the responsibility of each agency using the software. [Your agency's designated privacy officer is: _______________. They are responsible for: ensuring staff training, maintaining consent procedures, responding to access requests, managing breach response, and conducting periodic privacy reviews.]

---

## What This Document Does Not Cover

This document describes KoNote's built-in privacy features. Your PIA should also address:

- Your agency's privacy policies and procedures
- Staff training and acceptable use policies
- Physical security of devices used to access KoNote
- Consent forms and procedures specific to your programs
- Data sharing agreements with partner agencies or funders
- Your agency's specific retention schedule
- Your breach response plan and notification procedures

**For more information:**

- Security Overview — non-technical summary of KoNote's security features
- Security Operations Guide — for IT staff setting up and maintaining KoNote
- Independent Review Guide — how to verify KoNote's security claims
- Office of the Privacy Commissioner of Canada — PIPEDA guidance: <https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/>
- Information and Privacy Commissioner of Ontario — PHIPA: <https://www.ipc.on.ca/health/>
