# Agency Deployment Protocol — Azure

**Purpose:** End-to-end process for deploying KoNote for a new client organisation on Azure. Covers discovery through go-live and follow-up.

**Team roles:**
- **Sara** (PM) — leads client-facing sessions (Phases 0, 1, 3, 4 walkthrough, 5)
- **Prince** (Developer) — builds Azure infrastructure and applies configuration (Phases 2, 4 setup)
- **Gillian** — oversight, joins key sessions as needed

**Timeline:** 3–6 weeks from first call to go-live, depending on client readiness.

**Design:** [docs/plans/2026-02-19-deployment-protocol-design.md](../docs/plans/2026-02-19-deployment-protocol-design.md)

---

## Protocol Overview

| Phase | Name | Led by | With client? | Duration | Output |
|-------|------|--------|-------------|----------|--------|
| 0 | Discovery Call | Sara | Yes | 60 min | Discovery Worksheet |
| 1 | Permissions Setup | Sara | Yes (2 sessions) | 2 × 45 min | Signed Configuration Summary |
| 2 | Azure Infrastructure | Prince | No (needs client IT) | 2–4 hours | Running instance |
| 3 | Workflow Customisation | Sara | Yes | 60–90 min | Customisation Worksheet |
| 4 | Go-Live Verification | Prince + Sara | Yes (walkthrough) | 60 min | Signed go-live confirmation |
| 5 | 30-Day Check-In | Sara | Yes | 30 min | Updated config + action items |

**Rule:** Nothing is configured until it has been decided in a meeting and documented. Each phase produces an output that feeds the next.

---

## Phase 0: Discovery Call

**Purpose:** Understand the client's organisation, how they'll use KoNote, and their technical readiness for Azure deployment.

**Who's in the room:** Sara + client's project lead + their IT contact (if available)

**Duration:** ~60 minutes

**Before the call:** Review the client's website and any information they've shared. Understand their programs, size, and mission so you can ask informed questions.

---

### 0.1 Organisation & Deployment Model

**0.1.1** "Tell us about your organisation — what programs and services do you run?"

*Map their programs to potential KoNote programs. Note the scale — number of staff, number of participants, number of locations.*

**0.1.2** "Who will use KoNote day to day? Your own staff, community partner organisations, or both?"

*This is the most important question. The answer shapes everything else:*

| Model | What it means for KoNote |
|-------|-------------------------|
| **Own staff only** | Single instance, straightforward permissions |
| **Partners use it** | Each partner may need their own instance (multi-instance) or careful program-level separation |
| **Both** | Hybrid — headquarters sees aggregate data, partners enter client data |

*If partners will use it, explore: How many partners? Do they have their own IT? Would they log in to the same instance or need separate ones?*

**0.1.3** "How many staff or coaches will need accounts? Roughly — 5, 20, 50?"

**0.1.4** "Do different programs track different outcomes, or is there a standard set across the organisation?"

---

### 0.2 Azure & IT Readiness

**0.2.1** "Do you use Microsoft 365 / Azure Active Directory for your staff accounts?"

*If yes → Azure AD SSO is the natural fit. Staff log in with their work email.*
*If no → local authentication (username + password).*

**0.2.2** "Do you already have an Azure subscription, or would you need to set one up?"

*If they're a registered charity, they likely qualify for Microsoft nonprofit credits ($2,000 USD/year). Walk them through the eligibility check:*
- Go to [nonprofit.microsoft.com](https://nonprofit.microsoft.com/)
- They need their CRA charity registration number
- Verification takes 2–10 business days
- An employee must apply — we can't do it on their behalf

**0.2.3** "Who is your IT contact for Azure? We'll need them to register an application in Azure AD and provide some configuration values."

*Record: name, email, role. Prince will work with this person during Phase 2.*

**0.2.4** "Do you have a domain name you'd like to use for KoNote? Something like `outcomes.yourorg.ca` or `konote.yourorg.ca`?"

*They'll need to create a DNS record pointing to Azure. Their IT contact or domain registrar handles this.*

**0.2.5** "Are there any specific data residency requirements beyond standard Canadian privacy law? For example, funder contracts that specify where data must be stored, or health information that falls under PHIPA?"

*Azure Canada Central (Toronto) satisfies most Canadian requirements. Flag anything unusual for review.*

---

### 0.3 Timeline & Stakeholders

**0.3.1** "What's your target date for going live? Is there a funder reporting deadline or program launch driving the timeline?"

**0.3.2** "For our permissions interview (our next session), we'll need your Executive Director or designate, at least one Program Manager, and ideally a front desk lead or privacy officer. Who should be in that meeting?"

**0.3.3** "Who has the authority to sign off on the final configuration? This person confirms that roles, access, and features are set up correctly before we start entering real data."

**0.3.4** "Are you replacing an existing system, or is this net new? If replacing, will you need to migrate historical data?"

*Data migration is out of scope for standard deployment but important to identify early. If they need it, scope it separately.*

---

### 0.4 Outputs

After the Discovery Call, create:

- [ ] **Discovery Worksheet** — completed with answers to all questions above
- [ ] **Deployment model decision** — single instance vs. multi-instance
- [ ] **Authentication decision** — Azure AD SSO vs. local auth
- [ ] **Nonprofit credit application** — started if applicable (remind client it takes 2–10 business days)
- [ ] **Permissions interview scheduled** — send the prep sheet from [agency-permissions-interview.md](agency-permissions-interview.md) (the "Getting Ready" section under "Before the Interview")
- [ ] **IT contact identified** — for Prince to coordinate Azure AD setup

---

### Discovery Worksheet Template

*Copy and fill in during the call.*

> **Organisation:** ___
> **Date:** ___
> **Participants:** ___
>
> **Programs/services:**
> 1. ___
> 2. ___
> 3. ___
>
> **Deployment model:** Own staff / Partners / Both / TBD
> **Estimated users:** ___
> **Estimated participants:** ___
>
> **Microsoft 365 / Azure AD:** Yes / No
> **Azure subscription:** Existing / Needs setup / Applying for nonprofit credits
> **IT contact:** ___ (name, email)
> **Custom domain:** ___
> **Data residency requirements:** Standard PIPEDA / Additional: ___
>
> **Target go-live:** ___
> **Replacing existing system:** Yes (___) / No
> **Data migration needed:** Yes / No / TBD
>
> **Permissions interview attendees:**
> - ___
> - ___
>
> **Sign-off authority:** ___

---

## Phase 1: Permissions Setup

**Purpose:** Walk the client through all access and privacy decisions — who can see what, who can do what.

**Full protocol:** [agency-permissions-interview.md](agency-permissions-interview.md)

**Duration:** Two sessions, about a week apart
- **Session 1 — Discovery** (~45 min): Learn about their people, programs, and how they work
- **Session 2 — Decisions** (~45 min): Walk through specific access choices

---

### What the Permissions Interview Covers

The interview document is comprehensive and self-contained. Here is a summary of what it walks through:

| Session | Section | Decisions Made |
|---------|---------|---------------|
| 1 | Your People | Map job titles to KoNote roles; identify system administrators |
| 1 | Your Programs | List programs; flag confidential ones |
| — | Homework | Client thinks about front desk scenarios, emergency access, leadership access |
| 2 | Front Desk Access | What front desk can and can't see (scenario-based) |
| 2 | PM Scope | Individual vs. aggregate access; cross-program visibility |
| 2 | Executive & Board | Leadership access level |
| 2 | Safety | Conflict of interest blocks; DV safeguards; PIPEDA handler; staff departure process |
| 2 | Features | Which KoNote features to enable/disable |

---

### Azure-Specific Additions

During the permissions interview, also confirm:

**In Section 1 (Your People):**
- [ ] If using Azure AD SSO, confirm that every person who needs KoNote access has an Azure AD account (work email). Flag anyone who doesn't — they'll need local auth or an Azure AD guest account.

**In Section 7 (Features):**
- [ ] Confirm export notification recipients — this should include whoever handles PIPEDA access requests at the organisation.
- [ ] If the organisation serves community partners, discuss whether each partner needs their own permissions interview (they likely do).

---

### Outputs

After both sessions:

- [ ] **Configuration Summary** created (same day) — one-page summary of all decisions. Template is in the permissions interview document under "After the Interview."
- [ ] **Configuration Summary sent for sign-off** (within 1 week) — ED or designate confirms.
- [ ] **Signed Configuration Summary received** — hand off to Prince for Phase 2.

---

## Phase 2: Azure Infrastructure Setup

**Purpose:** Build the Azure environment and deploy KoNote using the signed Configuration Summary.

**Who:** Prince (developer). May need the client's IT contact for Azure AD configuration.

**Duration:** 2–4 hours

**Full technical guide:** [docs/archive/deploy-azure.md](../docs/archive/deploy-azure.md)

---

### Pre-Flight Checklist

Before touching Azure, confirm all inputs are ready:

| Input | Source | Status |
|-------|--------|--------|
| Signed Configuration Summary | Phase 1 | |
| Resource group name (e.g., `konote-[orgname]-prod`) | Discovery Call | |
| Region: Canada Central | Default for Canadian orgs | |
| Azure AD SSO or local auth? | Discovery Call | |
| Azure AD tenant ID | Client IT contact | |
| Azure AD client ID + secret | Client IT contact (or Prince creates during setup) | |
| Custom domain name | Discovery Call | |
| Nonprofit credit application approved? | Discovery Call | |
| SMTP provider for email | Client IT contact | |
| Twilio needed for SMS? | Permissions interview (features section) | |

---

### Setup Steps

Follow the [Azure deployment guide](../docs/archive/deploy-azure.md) for detailed instructions. Summary:

**Infrastructure (Steps 1–3):**
1. Create resource group in Canada Central
2. Create two PostgreSQL Flexible Servers (main + audit) with databases
3. Create Azure Container Registry (Basic SKU)

**Application (Steps 4–6):**
4. Build Docker image and push to Container Registry
5. Create Container App (0.5 vCPU, 1 GB memory, port 8000)
6. Configure environment variables:
   - `SECRET_KEY` — generate and store securely
   - `FIELD_ENCRYPTION_KEY` — generate and store securely (critical — if lost, encrypted data is unrecoverable)
   - `DATABASE_URL` — main PostgreSQL connection string
   - `AUDIT_DATABASE_URL` — audit PostgreSQL connection string
   - `AUTH_MODE` — `azure` for SSO, `local` for username/password
   - `DEMO_MODE` — `true` (client needs demo data for exploration)
   - SMTP variables for email notifications

**Authentication (Step 7, if Azure AD):**
7. Register app in Azure AD (client IT does this, or Prince with their tenant access):
   - Redirect URI: `https://[custom-domain]/auth/callback/`
   - Create client secret (set calendar reminder for renewal — 12 or 24 months)
   - Add environment variables: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_REDIRECT_URI`

**Initialisation (Steps 8–9):**
8. Run migrations and seed data (Container Instance method)
9. Configure custom domain + SSL certificate
10. Lock down audit database: `python manage.py lockdown_audit_db`

---

### Post-Setup Verification

Before telling the client the instance is ready:

- [ ] App starts without errors
- [ ] `python manage.py check --deploy` passes clean
- [ ] `python manage.py security_audit` passes clean
- [ ] Demo mode loads — demo login buttons visible on login page
- [ ] Azure AD login works (test with client's IT contact or a test account)
- [ ] Local admin account works (fallback)
- [ ] Trigger a test export — email notification arrives
- [ ] Audit log captures the test actions
- [ ] Database backups configured (increase retention to 30 days)
- [ ] Encryption key backed up in a separate secure location from database backups

---

### Encryption Key Handover

The `FIELD_ENCRYPTION_KEY` is the most critical secret. If lost, all encrypted client data is permanently unrecoverable.

**Storage rules:**
- Store separately from database backups
- Store in a password manager (1Password, Bitwarden) or Azure Key Vault
- Never store in Git, plain text on shared drives, or in the same location as backups
- At least two people should know where the key is stored

**Document for the client:**
- Where the key is stored
- Who has access to it
- What happens if it's lost (all encrypted PII unrecoverable)

---

### Outputs

- [ ] Running KoNote instance on Azure (Canada Central)
- [ ] Demo mode active — client can explore with demo users
- [ ] Azure AD SSO configured and tested (if applicable)
- [ ] Encryption key generated, backed up, and documented
- [ ] Email notifications working
- [ ] Audit database locked down
- [ ] Instance URL and demo credentials sent to client with a note: "Explore for 1–2 weeks before our customisation session"

---

## Phase 3: Workflow Customisation Interview

**Purpose:** Configure KoNote to match how the client actually works — their language, programs, outcome metrics, templates, and data collection fields. After this session, the system should feel like theirs.

**Who's in the room:** Sara + client's program lead(s) + at least one frontline coach or counsellor

**Duration:** 60–90 minutes

**Prerequisite:** Client must have explored the demo instance for at least one week.

---

### Before the Session

Send the client a prep note (1 week ahead):

> **Getting Ready for Your KoNote Customisation Session**
>
> You've had a chance to explore the demo. Before we meet, please think about:
>
> 1. **What terms feel wrong?** Does "Client" fit, or would you say "Participant" or "Member"? What about "Program" — do you call them "Services" or "Streams"?
> 2. **Your programs** — which services would you set up as separate programs in KoNote?
> 3. **A typical coaching session** — walk through what happens. What would a progress note need to capture?
> 4. **Outcome metrics** — what do you measure? What does your funder need you to report on?
> 5. **Your intake form** — what information do you collect when someone first enrols?
>
> Bring your current intake form, any funder reporting templates, and a coaching session outline if you have one.

---

### 3.1 Terminology

Walk through each customisable term. These changes apply immediately across the entire interface.

| Default Term | What It Means | Their Term | Notes |
|-------------|--------------|-----------|-------|
| Client | The person receiving services | | e.g., Participant, Member, Learner, Coaching Client |
| Program | A distinct service line | | e.g., Service, Stream, Initiative, Project |
| Target / Goal | A specific outcome a participant works toward | | e.g., Goal, Objective, Milestone, Action Item |
| Plan | A collection of goals for a participant | | e.g., Action Plan, Support Plan, Coaching Plan, Service Plan |
| Progress Note | Documentation of a session or contact | | e.g., Session Note, Coaching Note, Contact Note |

**Also confirm:** English only, or bilingual (English + French)? If bilingual, the client provides French terminology during or after this session.

---

### 3.2 Programs

For each program or service line they run, capture:

| Program Name | Description | Confidential? | Key Staff | Notes |
|-------------|------------|--------------|----------|-------|
| | | Yes / No | | |
| | | Yes / No | | |
| | | Yes / No | | |
| | | Yes / No | | |

**Cross-reference with Phase 1:** Programs identified here should match the permissions interview. Flag any new ones — they may need additional role assignments.

**Questions to explore:**
- Are these programs distinct enough to need separate tracking, or could some be combined?
- Do different programs track different outcomes?
- Will programs need separate plan templates, or can they share one?
- Are there programs that share staff? (Affects role assignments from Phase 1)

---

### 3.3 Outcome Metrics

KoNote ships with a built-in metric library covering mental health, housing, employment, substance use, youth, and general categories.

**Before the session:** Export the metric library to CSV. Screen-share during the meeting.

**Walk through the library:**

**3.3.1** "Which of these metrics does your organisation already use?"

*Go category by category. Enable the ones they use, disable the rest.*

**3.3.2** "What does your funder require you to report on? Are there specific outcome measures in your funding agreement?"

*Match funder requirements to existing metrics. Flag any gaps.*

**3.3.3** "Do you use any standardised assessment tools?"

*For a financial empowerment org, ask about:*
- Financial capability or literacy scales
- Income change tracking
- Employment status measures
- Housing stability indices
- Wellbeing measures (e.g., Canadian Index of Wellbeing)

**3.3.4** "Are there any outcomes specific to your organisation that aren't in the library? We can create custom metrics."

*Record: name, definition, min/max values, unit, category.*

**Output:** Marked-up metric list (enabled/disabled) plus any custom metrics to create.

---

### 3.4 Plan Templates

A plan template defines the structure coaches use when creating participant outcome plans.

**3.4.1** "When a coach starts working with a new participant, what does the plan look like? What sections or goal areas does it cover?"

*Build the template structure together. Example for a financial coaching org:*
- Financial Stability (budgeting, debt management, savings)
- Income (employment, benefits access, income growth)
- Housing (stability, affordability)
- Education & Skills (training, certifications)

**3.4.2** "What are typical goals within each section? These become the default suggestions when coaches create a plan."

**3.4.3** "Do different programs use different plan structures, or is there one standard template?"

*If different: create one template per program. If standard: create one global template.*

**3.4.4** "Would it be helpful to build one or two templates right now so you can see how they look?"

*If time allows, build a template live in the demo instance during the session. This makes the configuration feel real and gives the client something to react to.*

---

### 3.5 Progress Note Templates

Note templates define what coaches see when they write a progress note. The "This note is for..." dropdown lists the available templates.

**3.5.1** "What types of interactions do your coaches have with participants? For each type, what information needs to be captured?"

*Common types for a coaching org:*

| Interaction | Current default template | Adjust? |
|-------------|------------------------|---------|
| Regular coaching session | Standard session | |
| Quick phone check-in | Brief check-in | |
| Phone/text/email contact | Phone/text contact | |
| Crisis or urgent situation | Crisis intervention | |
| First meeting / enrolment | Intake assessment | |
| Ending service | Case closing | |
| Group workshop | *(may need to create)* | |

**3.5.2** "For a standard coaching session, what sections would the note include?"

*Walk through sections:*
- Session summary (what happened)
- Plan progress (metrics and goals — this links to outcome tracking)
- Participant's own words or feedback
- Next steps / action items

**3.5.3** "Do your funders require specific documentation in session notes?"

---

### 3.6 Custom Client Fields

Fields beyond the standard KoNote intake form (name, contact, emergency contact, demographics).

**3.6.1** "Can you walk us through your current intake form? For each field, we'll check if it's already in KoNote or if we need to create it."

**3.6.2** "What information does your funder require you to collect about each participant?"

**3.6.3** For each custom field, capture:

| Field Name | Type | Required? | Sensitive? | Choices (if dropdown) | Field Group |
|-----------|------|----------|-----------|----------------------|------------|
| | Text / Number / Date / Dropdown / Checkbox | Yes / No | Yes / No | | |
| | | | | | |

*Organise into field groups (e.g., "Funding & Referral", "Financial Profile", "Demographics").*

**Sensitive fields** are encrypted the same way as names and contact info. Mark any field that contains personal information the participant might not want broadly visible.

---

### 3.7 Optional Features: Registration Forms & Participant Portal

Quick pass — these can be configured after go-live but good to know the intent now.

| Feature | Decision | Notes |
|---------|---------|-------|
| **Registration forms** — public web forms for program sign-up | Yes / No / Later | Useful if participants self-refer through a website |
| **Participant portal** — participants see their own goals and progress | Yes / No / Later | Separate secure login with MFA, journal, messaging |

If "Yes" or interested, note the requirements. Configuration can happen after go-live.

---

### 3.8 Outputs

After the Workflow Customisation session, create:

- [ ] **Customisation Worksheet** — completed with all decisions from sections 3.1–3.7
- [ ] **Metric list** — marked up (enabled/disabled/custom)
- [ ] **Plan template draft(s)** — sections and sample goals
- [ ] **Note template adjustments** — which defaults to keep, rename, or restructure
- [ ] **Custom field list** — organised into field groups
- [ ] **Feature decisions** — registration forms, portal, messaging: yes/no/later

Hand off to Prince for configuration in Phase 4.

---

### Customisation Worksheet Template

*Copy and fill in during the session.*

> **Organisation:** ___
> **Date:** ___
> **Participants:** ___
>
> **Terminology:**
> - Client → ___
> - Program → ___
> - Target/Goal → ___
> - Plan → ___
> - Progress Note → ___
> - Bilingual (EN + FR): Yes / No
>
> **Programs:**
> 1. ___ (confidential: Y/N)
> 2. ___ (confidential: Y/N)
> 3. ___ (confidential: Y/N)
>
> **Metrics:** See attached marked-up CSV or list
>
> **Plan templates:**
> - Template 1: ___ (sections: ___)
> - Template 2: ___ (sections: ___)
>
> **Note templates:** (keep / rename / restructure / add)
> - Standard session → ___
> - Brief check-in → ___
> - Phone/text contact → ___
> - Crisis intervention → ___
> - Intake assessment → ___
> - Case closing → ___
> - New: ___
>
> **Custom fields:**
> (see table in section 3.6)
>
> **Optional features:**
> - Registration forms: Yes / No / Later
> - Participant portal: Yes / No / Later
> - SMS messaging: Yes / No / Later

---

## Phase 4: Go-Live Verification

**Purpose:** Apply all configuration, create real user accounts, and verify everything works before the client starts entering real participant data.

**Who:** Prince applies configuration (internal). Sara walks through the system with the client.

**Duration:** Prince — 1–2 hours for configuration. Sara + client — 30 minutes for walkthrough.

---

### Step 1: Apply Configuration (Prince)

Using the Customisation Worksheet from Phase 3 and the Configuration Summary from Phase 1:

**Instance Settings:**
- [ ] Set product name (e.g., "Prosper Canada — KoNote")
- [ ] Set support email
- [ ] Upload logo (if provided)
- [ ] Set date format

**Terminology:**
- [ ] Apply all terminology overrides from section 3.1
- [ ] If bilingual: add French translations for each term

**Features:**
- [ ] Enable/disable features per Phase 1 decisions
- [ ] Configure messaging profile if SMS or email is being used
- [ ] Set Safety-First mode ON until messaging is verified

**Programs:**
- [ ] Create all programs from section 3.2
- [ ] Mark confidential programs
- [ ] Set program descriptions

**Metrics:**
- [ ] Import the marked-up metric CSV (enable/disable)
- [ ] Create any custom metrics from section 3.3

**Templates:**
- [ ] Create plan templates from section 3.4
- [ ] Adjust note templates per section 3.5

**Custom Fields:**
- [ ] Create field groups
- [ ] Create custom fields with correct types, required flags, and sensitivity flags
- [ ] Set front desk visibility per Phase 1 decisions

**Notifications:**
- [ ] Configure export notification recipients per Phase 1 decisions

---

### Step 2: Create User Accounts (Prince)

Using the Configuration Summary (Phase 1):

**If Azure AD SSO:**
- [ ] Verify Azure AD app registration is complete and environment variables are set
- [ ] Test SSO login with the client's IT contact or a test account
- [ ] Prepare role assignment instructions — Azure AD auto-creates accounts on first login, but roles must be assigned manually afterward
- [ ] Create a list for the client: "When each person logs in for the first time, we'll assign their role"

**If local auth:**
- [ ] Create invite links for all staff (with correct roles and program assignments)
- [ ] Send invite links to client's project lead for distribution

**For both:**
- [ ] Assign System Administrator flag to designated admins
- [ ] Verify that admins who should NOT have client data access have no program role

---

### Step 3: Verification Walkthrough (Sara + Client)

Walk through the configured system together. This builds confidence that everything matches their decisions.

**Role verification** (from [permissions interview](agency-permissions-interview.md)):

- [ ] Log in as Front Desk — confirm they see only agreed-upon fields and NOT clinical notes or group membership
- [ ] Log in as Direct Service — confirm client data scoped to their program only
- [ ] Log in as Program Manager — confirm oversight access (notes, reports) for their program
- [ ] Log in as Executive — confirm aggregate data only, no individual client files
- [ ] Log in as System Administrator (no program role) — confirm settings access but no client data
- [ ] Try accessing a client in a different program — confirm "access denied"
- [ ] If confidential programs exist — verify the context-switching prompt works
- [ ] If access blocks exist — verify the blocked user gets a generic "no access" message

**Workflow verification:**

- [ ] Terminology displays correctly throughout the interface
- [ ] Programs appear with correct names and descriptions
- [ ] Plan template has the right sections and suggested goals
- [ ] Start creating a sample plan — fields and metrics are correct
- [ ] Progress note template captures the right sections
- [ ] Write a sample note — "This note is for..." dropdown shows correct options
- [ ] Custom fields appear on the client intake form in the right order
- [ ] Metric library shows only enabled metrics
- [ ] Run a test export — report looks correct and notification email arrives

**Technical verification:**

- [ ] Azure AD SSO login works for a real staff member (not just test accounts)
- [ ] Calendar feed URL generates and works in Outlook (if applicable)
- [ ] Audit log captured all the test actions
- [ ] Check the access log — verify it shows who viewed what

---

### Step 4: Sign-Off

Walk through the "Before You Enter Real Data" checklist from [deploying-konote.md](../docs/deploying-konote.md):

- [ ] Encryption key backed up and retrievable
- [ ] Database backups configured and tested
- [ ] Email configured and working
- [ ] User accounts set up with correct roles
- [ ] Seed data loaded
- [ ] Security checks passing (`python manage.py check --deploy`)
- [ ] Audit database locked down

**Client confirms:**
- [ ] Roles and access are correct
- [ ] Workflow configuration matches their needs
- [ ] Staff know how to log in
- [ ] Ready to begin entering real participant data

**Disable demo mode?** Discuss with the client:
- Demo data stays invisible to real users either way
- Demo login buttons on the login page are useful for training
- Set `DEMO_MODE=false` if the client prefers a clean login page

---

### Outputs

- [ ] Fully configured production instance
- [ ] All staff accounts created and access verified
- [ ] Signed go-live confirmation from client
- [ ] "Before You Enter Real Data" checklist completed
- [ ] 30-day check-in scheduled

---

## Phase 5: 30-Day Check-In

**Purpose:** Review how things are going after a month of real use. Adjust configuration based on what they've learned.

**Who's in the room:** Sara + client's project lead + optionally a frontline coach

**Duration:** ~30 minutes

**Schedule this during Phase 4** — put it in the calendar before the go-live call ends.

---

### Review Checklist

**Access & Permissions:**
- [ ] Have any staff requested permission changes? (e.g., "I can't see X and I need it")
- [ ] Has front desk reported any gaps in what they can see or do?
- [ ] Any new staff joined or existing staff left since go-live?
- [ ] Have any new programs been added or planned?
- [ ] Review the access log for unusual patterns (someone accessing files they don't normally need)

**Workflow:**
- [ ] Are the note templates working for coaches, or do they need adjustment?
- [ ] Are the plan templates capturing the right goals?
- [ ] Are the outcome metrics useful? Are any never used? Are any missing?
- [ ] Any custom fields that turned out to be unnecessary? Any that are missing?
- [ ] How is funder reporting working — does the export output match what they need?
- [ ] Are coaches finding the system easy to use, or are there friction points?

**Technical:**
- [ ] Any performance issues or errors reported?
- [ ] Are database backups running successfully?
- [ ] Check Azure AD client secret expiry date — set renewal reminder if needed
- [ ] Verify email notifications are still working

**Future features:**
- [ ] Revisit any "Later" decisions from Phase 3 (portal, registration forms, SMS)
- [ ] Discuss training needs for new staff
- [ ] Any interest in features they've seen in the demo but haven't enabled?

---

### Outputs

- [ ] Updated Configuration Summary (if changes were made)
- [ ] Action items for any adjustments (with owner and timeline)
- [ ] Next check-in scheduled (quarterly recommended)

---

## Appendix A: Document References

| Document | Location | Used in |
|----------|----------|---------|
| Permissions Interview | [tasks/agency-permissions-interview.md](agency-permissions-interview.md) | Phase 1 |
| Azure Deployment Guide | [docs/archive/deploy-azure.md](../docs/archive/deploy-azure.md) | Phase 2 |
| Deploying KoNote (all platforms) | [docs/deploying-konote.md](../docs/deploying-konote.md) | Phase 2, 4 |
| Administering KoNote | [docs/administering-konote.md](../docs/administering-konote.md) | Phase 3, 4 |
| Data Offboarding | [tasks/agency-data-offboarding.md](agency-data-offboarding.md) | Post-deployment (if needed) |
| Deployment Workflow Design | [docs/plans/2026-02-05-deployment-workflow-design.md](../docs/plans/2026-02-05-deployment-workflow-design.md) | Background (Assessment → Customisation → Production phases) |

## Appendix B: Timeline Template

*Adjust based on client readiness.*

| Week | Activity | Owner |
|------|----------|-------|
| 1 | Discovery Call (Phase 0) | Sara |
| 1 | Send permissions prep sheet | Sara |
| 2 | Permissions Session 1 — Discovery (Phase 1) | Sara |
| 2 | Start Azure infrastructure (Phase 2) | Prince |
| 3 | Permissions Session 2 — Decisions (Phase 1) | Sara |
| 3 | Complete Azure setup; send demo credentials | Prince |
| 3–4 | Client explores demo instance | Client |
| 4 | Workflow Customisation (Phase 3) | Sara |
| 4–5 | Apply configuration (Phase 4 — Steps 1-2) | Prince |
| 5 | Go-Live Walkthrough (Phase 4 — Steps 3-4) | Sara + Prince |
| 5 | Staff begin entering real data | Client |
| 9 | 30-Day Check-In (Phase 5) | Sara |

## Appendix C: Lessons Learned

*Update this section after each deployment. What worked? What didn't? What would you change?*

*(This section will be populated after the Prosper Canada deployment.)*
