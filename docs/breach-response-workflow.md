# Data Breach Response Workflow

**Last updated:** March 2026 | **Legal basis:** PIPEDA s.10.1 (Breach of Security Safeguards Regulations)

> **Instructions:** This checklist supplements the technical incident response steps in the [Security Operations Guide](security-operations.md). Print this document and keep it accessible to your privacy officer and IT contact. In a breach, you will not have time to search for procedures.

---

## Definitions

**Data breach (breach of security safeguards):** The loss of, unauthorised access to, or unauthorised disclosure of personal information resulting from a breach of an organisation's security safeguards, or from a failure to establish those safeguards.

**Real risk of significant harm (RROSH):** The threshold under PIPEDA for mandatory notification. Consider the sensitivity of the information and the probability that it will be misused.

---

## Phase 1: Containment (Immediately — within hours)

The goal is to stop the breach from getting worse.

- [ ] **Identify what happened** — Is this unauthorised access, accidental disclosure, lost device, stolen credentials, ransomware, or something else?
- [ ] **Stop the ongoing breach:**
  - [ ] If credentials were compromised: rotate all passwords, revoke API keys, invalidate sessions (see [Security Operations — Incident Response](security-operations.md#incident-response))
  - [ ] If the encryption key was exposed: rotate the encryption key immediately (see Security Operations — Key Management)
  - [ ] If a device was lost/stolen: remotely wipe if possible, disable the user's account
  - [ ] If an insider accessed records without authorisation: suspend the account pending investigation
- [ ] **Preserve evidence** — Do not delete logs, emails, or files related to the incident. Screenshot or export audit logs before making system changes.
- [ ] **Notify your privacy officer** (see Roles below)
- [ ] **Record the time** you discovered the breach and each action taken

---

## Phase 2: Assessment (Within 24–48 hours)

Determine the scope, severity, and whether notification is required.

### Scope Assessment

- [ ] **What personal information was involved?**
  - [ ] Names, contact information (directly identifying PII)
  - [ ] Health information, case notes, progress notes (sensitive)
  - [ ] Financial information, SIN numbers (high sensitivity)
  - [ ] De-identified or aggregate data only (low sensitivity)
- [ ] **How many individuals were affected?** (count or estimate)
- [ ] **What programs or services are affected?**
- [ ] **Was the information encrypted?** (If the encrypted database was accessed but the encryption key was not compromised, the actual PII may not have been exposed)
- [ ] **Is the information still accessible to the unauthorised party?**

### Risk of Significant Harm Assessment

Under PIPEDA, you must assess whether there is a "real risk of significant harm" (RROSH). Consider:

| Factor | Higher Risk | Lower Risk |
|--------|------------|------------|
| **Sensitivity** | Health, financial, SIN, children's data | De-identified, aggregate, publicly available |
| **Likelihood of misuse** | Data taken deliberately, criminal access | Accidental disclosure to trusted party |
| **Who accessed it** | Unknown external party, criminal actor | Known employee, breach quickly contained |
| **Volume** | Many individuals affected | Single record |
| **Recovery** | Data copied, cannot be recovered | Data retrieved, access confirmed revoked |

- [ ] **Document your RROSH assessment** — Write down your reasoning. If you determine notification is not required, document why. PIPEDA requires you to keep records of all breaches for 24 months, regardless of whether you notify.

---

## Phase 3: Notification (As soon as feasible)

If there is a real risk of significant harm, you must notify affected individuals **and** the Privacy Commissioner. There is no fixed deadline, but "as soon as feasible" is the legal standard. Delays must be justified (e.g., law enforcement requested a delay).

### Notify the Privacy Commissioner of Canada

- [ ] **Submit a breach report** to the Office of the Privacy Commissioner (OPC)
  - Online: [https://www.priv.gc.ca/en/report-a-concern/report-a-privacy-breach-at-your-organization/](https://www.priv.gc.ca/en/report-a-concern/report-a-privacy-breach-at-your-organization/)
  - The report must include:
    - Description of the breach circumstances
    - Date or period of the breach
    - Description of the personal information involved
    - Number of affected individuals (estimate if exact count unknown)
    - Steps taken to reduce risk of harm
    - Steps taken or planned to notify affected individuals
    - Contact person at your organisation

### Notify Affected Individuals

- [ ] **Draft notification content** that includes:
  - [ ] Description of what happened (in plain language)
  - [ ] What personal information was involved
  - [ ] What you have done to contain the breach
  - [ ] What individuals can do to protect themselves
  - [ ] Contact information for questions
  - [ ] How to file a complaint with the OPC
- [ ] **Choose notification method:**
  - Direct (email, letter, phone) if you have current contact information
  - Indirect (public notice, website) if direct notification would be unreasonable
- [ ] **Send notifications** and record the method, date, and recipient count
- [ ] **If the breach involves children's data:** notify the parent or guardian

### Notify Other Parties (If Applicable)

- [ ] **Funder(s)** — Check your funding agreements for breach notification clauses
- [ ] **Provincial privacy commissioner** — If provincial legislation also applies (e.g., PHIPA in Ontario requires notification to the Information and Privacy Commissioner of Ontario)
- [ ] **Insurance provider** — If you have cyber liability insurance
- [ ] **Law enforcement** — If criminal activity is suspected
- [ ] **Board of directors** — Per your governance policies

---

## Phase 4: Documentation (Ongoing)

PIPEDA requires you to keep records of all breaches of security safeguards for **24 months** after the breach is determined to have occurred.

- [ ] **Create a breach incident record** with:
  - [ ] Date and time of discovery
  - [ ] Description of the breach
  - [ ] Personal information involved
  - [ ] Number of affected individuals
  - [ ] Cause of the breach (if known)
  - [ ] Timeline of response actions
  - [ ] RROSH assessment and reasoning
  - [ ] Notifications sent (to whom, when, how)
  - [ ] Remediation steps taken
- [ ] **Store the incident record** securely (not in KoNote — use your document management system)
- [ ] **Review KoNote audit logs** and export relevant entries for the incident file

---

## Phase 5: Remediation (Within 30 days)

Prevent the same type of breach from happening again.

- [ ] **Root cause analysis** — What failed? Was it technical (security flaw), procedural (staff error), or both?
- [ ] **Run the KoNote security audit:**
  ```bash
  python manage.py security_audit --verbose
  ```
- [ ] **Implement corrective actions:**
  - [ ] Patch the vulnerability or fix the configuration
  - [ ] Update access controls if the breach was caused by excessive permissions
  - [ ] Add monitoring for the type of activity that caused the breach
- [ ] **Staff training** — Brief all staff on what happened and how to prevent it. Do not share affected individuals' names with staff who were not involved in the response.
- [ ] **Update policies** — Revise your privacy policy, security practices, or data handling acknowledgement if needed
- [ ] **Review this document** — Did the response workflow work? What should change for next time?

---

## Roles and Contacts

Fill in your organisation's contacts:

| Role | Name | Contact | Backup |
|------|------|---------|--------|
| **Privacy Officer** | ____________ | ____________ | ____________ |
| **IT Contact / MSP** | ____________ | ____________ | ____________ |
| **Executive Director** | ____________ | ____________ | ____________ |
| **Board Chair** | ____________ | ____________ | ____________ |
| **Legal Counsel** | ____________ | ____________ | ____________ |
| **Cyber Insurance** | ____________ | Policy #: ____________ | Claims line: ____________ |

**Office of the Privacy Commissioner of Canada**
- Website: [https://www.priv.gc.ca](https://www.priv.gc.ca)
- Phone: 1-800-282-1376
- Breach report: [https://www.priv.gc.ca/en/report-a-concern/report-a-privacy-breach-at-your-organization/](https://www.priv.gc.ca/en/report-a-concern/report-a-privacy-breach-at-your-organization/)

---

## Special Scenarios

### Lost Encryption Key

If the `FIELD_ENCRYPTION_KEY` is lost and no backup exists:

- All encrypted PII (names, contact info, sensitive custom fields) is **permanently unrecoverable**
- All encrypted progress note content is **permanently unrecoverable**
- This constitutes a loss of personal information — follow the full breach workflow above
- Non-encrypted data (metric values, program assignments, dates) remains intact
- You will need to re-enter client identifying information manually

**Prevention:** Store the encryption key in a password manager. Ensure at least two people know where it is. Test key retrieval every 6 months.

### Accidental Disclosure to Another Client

If a staff member accidentally shows one client's information to another:

- This is a breach, even if the information was only seen briefly
- Assess the sensitivity of what was disclosed
- Consider whether notification to the affected client is required
- Document the incident even if notification is not required

### Unauthorised Staff Access

If a staff member accessed records outside their program assignment:

- Suspend the account immediately
- Review audit logs to determine the scope of access
- Determine whether the access was intentional or accidental (e.g., misconfigured program assignment)
- If intentional: follow your HR and security policies
- If accidental: fix the configuration and retrain

---

*This document is provided as part of KoNote documentation. Each organisation must adapt it to their specific legal and regulatory requirements. This is not legal advice — consult legal counsel for your breach response obligations.*
