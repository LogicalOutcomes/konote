# Privacy Policy Template for KoNote2

> **Setup Instructions:** This privacy policy template must be customised by each organisation before deploying KoNote2. Replace all `[PLACEHOLDER]` values with your organisation's specific information. Review the entire document with your privacy officer or legal counsel before publishing.

---

# Privacy Policy — [ORGANISATION NAME]

**Last Updated:** [DATE]
**Effective Date:** [DATE]
**Data Controller:** [ORGANISATION NAME]

---

## 1. Introduction

This Privacy Policy describes how [ORGANISATION NAME] ("we," "us," or "our") collects, uses, stores, and protects personal information through our client management system. This policy applies to all users of the system, including staff members, administrators, and the clients whose information is recorded.

We comply with the *Personal Information Protection and Electronic Documents Act* (PIPEDA) and applicable provincial privacy legislation.

---

## 2. Information We Collect

### 2.1 Client Information

We collect personal information about clients to deliver and track services:

| Data Category | Examples | Classification |
|---------------|----------|----------------|
| **Identifiers** | Name, date of birth, client ID | Directly identifying PII |
| **Contact Information** | Address, phone number, email address | Directly identifying PII |
| **Demographic Data** | Age, gender, language preference | Indirectly identifying |
| **Service Records** | Programme enrolment, case notes, progress metrics | Sensitive service data |
| **Consent Records** | Consent forms, consent dates, scope of consent | Legal records |
| **Custom Fields** | Organisation-defined fields (varies by programme) | Variable sensitivity |

### 2.2 Staff and User Information

| Data Category | Examples | Purpose |
|---------------|----------|---------|
| **Account Credentials** | Email address, hashed password (local auth only) | Authentication |
| **Identity Provider Data** | Azure AD profile (name, email, object ID) | SSO authentication |
| **Access Logs** | Login timestamps, IP addresses, user agent | Security auditing |
| **Activity Records** | Actions performed, records accessed | Audit trail |

### 2.3 Technical Data

- Browser type and version
- Operating system
- Session identifiers (cookies)
- Request timestamps
- Error logs (anonymised where possible)

---

## 3. How We Protect Your Information

### 3.1 Encryption at Rest

All personally identifiable information (PII) is encrypted before storage using **Fernet symmetric encryption**, which implements:

- **Algorithm:** AES-128 in CBC mode
- **Authentication:** HMAC using SHA-256
- **Key Derivation:** Keys derived from a master secret using HKDF
- **Key Storage:** Encryption keys stored in environment variables, isolated from the database and source code

**Encrypted fields include:**
- Client names (first, middle, last) and date of birth
- All progress note content (notes text, summaries, participant reflections, per-target notes)
- User email addresses
- Registration submission data (name, email, phone)
- Any custom field values marked as sensitive by administrators

**Technical note:** Because PII is encrypted at the application layer, database-level searches on these fields are not possible. Client search operations decrypt permitted records in application memory and filter there. This architecture is designed for deployments with up to approximately 2,000 active clients.

### 3.2 Encryption in Transit

All data transmitted between your browser and our servers is encrypted using:

- **Protocol:** TLS 1.2 or TLS 1.3 (depending on hosting platform configuration)
- **Certificate:** Minimum 2048-bit RSA or ECDSA certificates
- **HSTS:** HTTP Strict Transport Security enabled

> **Hosting Note:** TLS configuration depends on your hosting platform (Azure, Railway, Elest.io, or self-hosted). Ensure your platform is configured to enforce HTTPS and disable older TLS versions.

### 3.3 Password Security

For users authenticating with local accounts (not SSO):

- **Hashing Algorithm:** Argon2id (winner of the Password Hashing Competition)
- **Parameters:** Django's default Argon2 parameters (automatically updated with Django security releases)
- **Salting:** Unique random salt per password
- **Rehashing:** Passwords automatically rehashed if security parameters are upgraded
- **Minimum Length:** 10 characters

### 3.4 Database Security

- **Database Engine:** PostgreSQL 16
- **Connection Security:** SSL/TLS required for all database connections
- **Access Control:** Role-based database permissions; application uses a restricted service account
- **Separation:** Audit logs stored in a separate database from application data
- **Backups:** [DESCRIBE YOUR BACKUP PROCEDURES AND ENCRYPTION]

> **Hosting Note:** Database security configuration varies by hosting platform. Document your specific backup procedures, encryption methods, and data centre locations.

### 3.5 Application Security

- **Session Management:** Secure, HTTP-only, SameSite cookies; sessions expire after configurable inactivity period
- **CSRF Protection:** All state-changing requests require valid CSRF tokens
- **Content Security Policy:** Strict CSP headers to prevent XSS attacks
- **Input Validation:** All user input validated server-side using Django forms
- **SQL Injection Prevention:** Parameterised queries via Django ORM
- **Rate Limiting:** Authentication endpoints rate-limited to prevent brute force attacks
- **Export Security:** Exported files protected against formula injection; download links expire after a configurable period; all exports audit-logged

---

## 4. Access Control

### 4.1 Role-Based Access Control (RBAC)

Access to client information is controlled through a role-based permission system:

| Role | Access Level |
|------|--------------|
| **Administrator** | System settings and user management. No client data access unless also assigned a programme role. |
| **Programme Manager** | Full access to assigned programme(s) and their clients. Can edit plans and export data. |
| **Staff** | Access to clients in assigned programmes. Can write notes and record events. |
| **Front Desk** | Limited client information only. Cannot view full records or export data. |

### 4.2 Client Assignment

Staff can only access client records for programmes they are assigned to. Assignment is programme-based: users are assigned to one or more programmes and can access all clients enrolled in those programmes.

### 4.3 Administrative Access

Administrative functions (user management, system configuration, terminology settings) are restricted to administrative routes and protected by middleware that verifies administrator role membership.

---

## 5. Audit Logging

### 5.1 What We Log

All access to and modifications of client data are recorded:

| Event Type | Data Recorded |
|------------|---------------|
| **Authentication** | User ID, timestamp, IP address, success/failure, method (SSO/local) |
| **Record Access** | User ID, client ID, timestamp, access type (view/edit) |
| **Data Changes** | User ID, record ID, field changed, previous and new values (encrypted), timestamp |
| **Permission Changes** | User ID, target user, permissions granted/revoked, timestamp |
| **Export Events** | User ID, export type, record count, timestamp |

### 5.2 Log Protection

- Audit logs are stored in a **separate PostgreSQL database** with independent access controls
- Log entries are append-only; application accounts cannot modify or delete logs
- Logs are retained for **[RETENTION PERIOD - e.g., 7 years]** in accordance with regulatory requirements
- Log access is restricted to designated compliance personnel

### 5.3 Log Review

Audit logs are reviewed **[FREQUENCY - e.g., monthly]** for:
- Unusual access patterns
- Failed authentication attempts
- Bulk data exports
- Access outside normal business hours

---

## 6. Hosting and Data Location

> **Important:** Each organisation hosts their own instance of KoNote2 on infrastructure they select and control. Complete this section based on your hosting choices.

### 6.1 Hosting Platform

**Platform:** [YOUR HOSTING PLATFORM - e.g., Azure, Railway, Elest.io, self-hosted]
**Data Centre Location:** [COUNTRY/REGION]
**Provider Certifications:** [e.g., SOC 2 Type II, ISO 27001, if applicable]

### 6.2 Data Residency

All data, including:
- Client records
- User accounts
- Audit logs
- Encrypted backups

is stored in **[COUNTRY/REGION]**.

> **Canadian Organisations:** If PIPEDA compliance requires Canadian data residency, ensure your hosting platform stores data in Canadian data centres.

### 6.3 Subprocessors

[LIST ANY THIRD-PARTY SERVICES THAT PROCESS DATA ON YOUR BEHALF]

| Service | Purpose | Data Shared | Location |
|---------|---------|-------------|----------|
| [Hosting provider] | Infrastructure | All application data | [Location] |
| [Backup provider, if separate] | Backup storage | Encrypted backups | [Location] |

---

## 7. AI-Assisted Analysis (If Applicable)

> **Complete this section if you enable the AI report summary feature. Delete if not using AI features.**

### 7.1 Purpose

KoNote2's Outcome Insights feature can optionally use AI to generate draft narrative summaries of programme outcomes. This helps staff identify patterns in service delivery and prepare reports. The feature is off by default and must be explicitly enabled by an administrator.

### 7.2 Data Sent to the AI Provider

Before any data is sent, KoNote2 removes personally identifying information:

| Data Type | What Is Sent | What Is Removed |
|-----------|-------------|-----------------|
| **Statistics** | Aggregate counts and percentages (e.g., "60% of participants reported improvement") | Nothing — these are already anonymous |
| **Quotes** | Short excerpts from progress notes, with all identifying details scrubbed | Client names, staff names, email addresses, phone numbers, SIN numbers, postal codes, and street addresses |
| **Context** | Programme name, date range, goal/target names | Nothing — these are organisational terms, not personal data |

**The following are never sent:** client names, dates of birth, contact information, full case records, unprocessed notes, database credentials, or encryption keys.

### 7.3 AI Provider

**Provider:** [YOUR AI PROVIDER — e.g., OpenRouter, local Ollama instance, OpenAI]
**Data Processing Location:** [LOCATION — e.g., US-based cloud, on-premises]

> **Note:** If PIPEDA requires Canadian data residency, consider using a locally hosted AI (such as Ollama) that processes all data on your own servers.

| Provider Type | Data Leaves Your Servers? | Recommended For |
|--------------|--------------------------|-----------------|
| **Local (Ollama)** | No — all processing on-premises | Maximum data control |
| **Cloud (OpenRouter, OpenAI)** | Yes — de-identified excerpts only | Convenience, higher quality output |

### 7.4 Data Retention by AI Provider

De-identified data sent to cloud AI providers is subject to the provider's data retention policies. [ORGANISATION NAME] selects providers whose terms do not retain input data for training purposes. See the provider's terms of service for details:

- [PROVIDER PRIVACY POLICY URL]

### 7.5 Consent and Transparency

- AI-generated content is clearly labelled as "AI-Generated Draft" in the interface
- Staff must review and edit all AI-generated content before use
- The feature can be disabled at any time by an administrator without affecting existing data

---

## 8. Third-Party Authentication (If Applicable)

> **Complete this section if using Azure AD SSO. Delete if using local authentication only.**

### 7.1 Azure Active Directory (SSO)

If your organisation uses Azure AD single sign-on:

- **Data Shared with Microsoft:** Authentication requests
- **Data Received:** Authentication token, user profile (email, display name), group memberships (if configured)
- **Data Stored Locally:** Azure AD object ID (for account linking), email, display name
- **Microsoft's Privacy Policy:** https://privacy.microsoft.com

---

## 9. Cookies and Session Management

### 9.1 Essential Cookies

We use only essential cookies required for the application to function:

| Cookie Name | Purpose | Duration |
|-------------|---------|----------|
| `sessionid` | Maintains your login session | [SESSION DURATION - default: 30 minutes of inactivity] |
| `csrftoken` | Prevents cross-site request forgery attacks | 1 year |

### 9.2 No Tracking Cookies

We do not use:
- Advertising cookies
- Third-party tracking cookies
- Analytics cookies that share data with external parties

---

## 10. Data Retention

| Data Type | Retention Period | Rationale |
|-----------|------------------|-----------|
| **Active Client Records** | Duration of service + [X years] | Service delivery and regulatory compliance |
| **Closed Client Records** | [X years] after closure | Statutory retention requirements |
| **Audit Logs** | [X years] | Compliance and incident investigation |
| **User Accounts** | Duration of employment + [X months] | Access management |
| **Session Data** | [X hours] after last activity | Security |
| **Error Logs** | [X days] | Troubleshooting |

> **Note:** Retention periods should align with your organisation's record retention policy and applicable regulations (e.g., funder requirements, professional standards).

### 10.1 Data Erasure

KoNote2 supports formal data erasure requests in compliance with PIPEDA:

1. **Request** — Any staff member can initiate an erasure request for a client
2. **Approval** — All programme managers for that client's programmes must approve the request
3. **Execution** — Once approved, all client data is permanently and irreversibly deleted, including:
   - Client profile and contact information
   - All notes, plans, events, and alerts
   - All metric recordings and custom field values
   - Programme enrolment records
4. **Audit Trail** — The audit log records that an erasure occurred (date, who requested, who approved) but retains no personal information about the erased client

Self-approval is prevented — the person requesting erasure cannot also be the sole approver. A single rejection from any programme manager cancels the entire request.

### 10.2 Data Deletion on Retention Expiry

After retention periods expire, data is securely deleted:
- Database records permanently deleted with verification
- Encrypted backups rotated according to backup retention schedule
- Deletion logged in audit system

---

## 11. Your Rights Under PIPEDA

You have the right to:

1. **Access** — Request a copy of your personal information we hold
2. **Correction** — Request correction of inaccurate information
3. **Erasure** — Request deletion of your personal information (subject to a multi-step approval process)
4. **Withdrawal of Consent** — Withdraw consent for specific uses (where consent is the legal basis)
5. **Complaint** — File a complaint with the Office of the Privacy Commissioner of Canada

### 11.1 For Clients

If you are a client whose information is recorded in this system, contact us at **[CONTACT EMAIL]** to:
- Request access to your records
- Request corrections to inaccurate information
- Ask questions about how your information is used
- Withdraw consent (subject to legal and service requirements)

### 11.2 For Staff

Contact your system administrator or **[PRIVACY OFFICER EMAIL]** for:
- Access to your employment-related data
- Questions about workplace privacy

### 11.3 Response Time

We respond to access requests within **30 days** as required by PIPEDA. If we need additional time, we will notify you of the extension and the reasons.

---

## 12. Data Breach Response

In the event of a data breach involving personal information:

1. **Containment** — Immediate action to stop ongoing breach and secure systems
2. **Assessment** — Determine scope, affected individuals, and risk of significant harm
3. **Notification** — If there is a real risk of significant harm:
   - Notify affected individuals as soon as feasible
   - Report to the Office of the Privacy Commissioner of Canada
   - Notify other regulators as required by law
4. **Documentation** — Maintain records of all breaches regardless of notification requirement
5. **Remediation** — Implement measures to prevent recurrence

### 12.1 Breach Contact

Report suspected breaches to: **[SECURITY CONTACT EMAIL]**

---

## 13. Changes to This Policy

We may update this Privacy Policy to reflect changes in our practices or legal requirements. When we make changes:

- This page will be updated with a new "Last Updated" date
- Users will be notified of material changes via **[EMAIL / IN-APP NOTIFICATION]**
- Changes take effect **[X days]** after posting (or immediately for changes required by law)

---

## 14. Contact Us

**Privacy Officer:** [NAME]
**Email:** [EMAIL]
**Phone:** [PHONE]

**Mailing Address:**
[ORGANISATION NAME]
[STREET ADDRESS]
[CITY, PROVINCE, POSTAL CODE]
Canada

For complaints not resolved to your satisfaction, you may contact:

**Office of the Privacy Commissioner of Canada**
Website: https://www.priv.gc.ca
Phone: 1-800-282-1376

---

## Setup Checklist

Before publishing this privacy policy, ensure you have:

- [ ] Replaced all `[PLACEHOLDER]` values with your organisation's information
- [ ] Specified your hosting platform and data centre location
- [ ] Documented your backup procedures
- [ ] Set appropriate retention periods based on your policies and regulations
- [ ] Designated a privacy officer and contact information
- [ ] If using AI features: completed Section 7 with your AI provider details
- [ ] Reviewed with legal counsel or privacy advisor
- [ ] Configured your instance's session timeout to match the policy
- [ ] Published the policy on your instance (link from login page or footer)

---

*This privacy policy template is provided as part of KoNote2. Each organisation is responsible for customising this policy to reflect their specific practices, hosting configuration, and regulatory requirements.*
