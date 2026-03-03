# 09 — Verification

## What This Configures

Nothing new — this document is a testing checklist. Before the agency starts entering real participant data, you walk through the configured system together to confirm that everything matches the decisions made in Documents 01 through 08. The verification walkthrough builds confidence that the system is set up correctly and catches any misconfigurations before they affect real data.

## Decisions Needed

1. **Who will participate in the verification walkthrough?**
   - At minimum: the developer (or person who applied configuration), the agency's project lead, and one frontline worker
   - Recommended: also include the system administrator and someone in the front desk role (if applicable)
   - Default: Developer + agency project lead + one staff member

2. **Do you want to keep demo mode active after go-live?**
   - **Yes** → demo login buttons remain on the login page. Useful for ongoing training — staff can explore with sample data without affecting real records. Demo data is invisible to real users regardless.
   - **No** → cleaner login page with no demo buttons. Set `DEMO_MODE=false` in environment variables.
   - Default: Keep demo mode on for training purposes

3. **Has the Data Handling Acknowledgement (Document 10) been reviewed and signed?**
   - The signed acknowledgement is a go-live prerequisite
   - It confirms the agency understands their responsibilities for data outside KoNote (encryption key custody, document storage, exports, staff departures)
   - Default: Must be signed before entering real participant data

## Verification Checklist

### Role Verification

Test each role by logging in as a user with that role. Confirm they see only what was agreed upon in Document 03.

- [ ] **Front Desk login** — confirm they see only the agreed-upon fields (names, contact info as configured) and do NOT see clinical notes, plans, metrics, or group membership
- [ ] **Direct Service login** — confirm they see full participant data scoped to their assigned program(s) only
- [ ] **Program Manager login** — confirm oversight access (notes, reports) for their program(s)
- [ ] **Executive login** — confirm aggregate data only, no individual participant files
- [ ] **System Administrator login (no program role)** — confirm they can access settings but cannot see any participant data
- [ ] **Cross-program test** — try to access a participant in a different program; confirm "access denied"
- [ ] **Confidential program test** (if applicable) — verify the context-switching prompt works when moving between standard and confidential programs
- [ ] **Access block test** (if applicable) — verify blocked users see a generic "no access" message with no indication the participant exists

### Terminology Verification

- [ ] Terminology displays correctly throughout the interface (check navigation menus, page headings, form labels)
- [ ] If bilingual: French terms appear correctly when the language is switched

### Program Verification

- [ ] All programs appear with correct names and descriptions
- [ ] Confidential programs are flagged correctly
- [ ] Staff assignments match the decisions in Document 03

### Template Verification

- [ ] Plan template has the right sections and suggested targets
- [ ] Start creating a sample plan — fields and targets appear as expected
- [ ] Progress note template captures the right sections
- [ ] Write a sample note — the "This note is for..." dropdown shows the correct template options
- [ ] The co-creation checkbox behaves as configured (optional or required)

### Metric and Survey Verification

- [ ] Metric library shows only enabled metrics
- [ ] Disabled metrics are hidden from staff
- [ ] Custom metrics appear with correct names, ranges, and units
- [ ] If surveys are enabled: a test survey can be created and assigned
- [ ] If survey trigger rules are configured: test that they fire correctly

### Custom Fields Verification

- [ ] Custom fields appear on the participant intake form in the correct order
- [ ] Field groups are correctly organised
- [ ] Required fields enforce entry
- [ ] Sensitive fields are encrypted (verify by checking the database or admin tools)
- [ ] Front desk visibility matches the decisions in Document 03

### Feature Verification

- [ ] Enabled features appear in the interface
- [ ] Disabled features are hidden (no menu items, no buttons)
- [ ] If messaging is enabled: Safety-First mode is on (no real messages sent during testing)

### Report and Export Verification

- [ ] Run a test export — the report looks correct and the notification email arrives
- [ ] If report templates are configured: demographic breakdowns match funder requirements
- [ ] Export notification recipients are correct (check who received the test notification)

### Authentication Verification

- [ ] Azure AD SSO login works for a real staff member (not just test accounts) — if applicable
- [ ] Local admin fallback account works — if applicable
- [ ] Invite links generate correctly and new users can complete registration

### Technical Verification

- [ ] Audit log captured all the test actions (check under Manage, then Audit Logs)
- [ ] `python manage.py check --deploy` passes clean
- [ ] `python manage.py security_audit` passes clean
- [ ] Database backups are configured and tested
- [ ] Encryption key is backed up and retrievable (verify with the designated custodians from Document 10)
- [ ] Email notifications are working (confirmed by the test export notification)

### Document Storage Verification (if enabled)

- [ ] SharePoint: "Open Documents Folder" button opens the correct library for each program
- [ ] SharePoint: permissions are set correctly — staff can access their program's library but not others
- [ ] Google Drive (portal): participant document link appears in portal for active enrolments
- [ ] If document storage is not enabled: confirm the decision to defer (record in the Configuration Summary)

## Sign-Off Checklist

Before the agency starts entering real participant data, confirm:

- [ ] Encryption key backed up and retrievable by at least two people
- [ ] Database backups configured and tested
- [ ] Email configured and working
- [ ] User accounts set up with correct roles and program assignments
- [ ] Demo data loaded (if keeping demo mode on)
- [ ] Security checks passing
- [ ] Audit database locked down
- [ ] Data Handling Acknowledgement signed (Document 10)

**Client confirms:**
- [ ] Roles and access are correct
- [ ] Workflow configuration matches their needs
- [ ] Staff know how to log in
- [ ] Data handling responsibilities understood and acknowledged
- [ ] Ready to begin entering real participant data

## Output Format

The verification produces two outputs:

### 1. Signed Go-Live Confirmation

A brief document confirming that the agency has reviewed the configured system and is ready to enter real data.

```
Go-Live Confirmation

Agency: [Name]
Date: [Date]
KoNote Instance URL: [URL]
Configuration verified by: [Names of people in the walkthrough]

All verification checks passed: Yes / No (if no, list exceptions)
Data Handling Acknowledgement signed: Yes
Demo mode: Kept on / Turned off

Signed: _________________ (Agency representative)
Signed: _________________ (KoNote operator)
```

### 2. 30-Day Check-In Scheduled

Schedule a follow-up 30 days after go-live. At that check-in, review:
- Have any staff requested permission changes?
- Are the templates working for the team?
- Are the metrics useful? Any missing?
- How is funder reporting working?
- Any new staff or departures since go-live?
- Are the designated contacts in the Data Handling Acknowledgement still current?

## Dependencies

- **Requires:** All previous documents (01 through 08) must be configured. Document 10 (Data Responsibilities) must be reviewed and signed.
- **Feeds into:** Phase 5 (30-Day Check-In) — the verification walkthrough establishes the baseline that the check-in reviews against.

## Example: Financial Coaching Agency

**Walkthrough participants:** Maria Santos (PM/admin), Sarah Chen (coach), developer

**Verification results:**

| Check | Result | Notes |
|-------|--------|-------|
| Role verification | Pass | All five roles tested; access boundaries correct |
| Terminology | Pass | "Participant," "Goal," "Action Plan," "Session Note" appear throughout |
| Programs | Pass | Three programs created with correct names and staff |
| Plan template | Pass | "Financial Coaching Action Plan" with four sections |
| Note templates | Pass | Coaching Session, Brief Check-in, Phone/Text, Intake, Case Closing, Workshop |
| Metrics | Pass | Financial capability, income, employment, housing enabled; custom metrics working |
| Custom fields | Pass | Funding source, referral source, income bracket on intake form |
| Features | Pass | Groups off, Program Reports on, Portal off, others as configured |
| Reports | Pass | Test export generated; notification received by Maria and James |
| Authentication | Pass | SSO login working for Sarah and Maria; local admin fallback working |
| Technical | Pass | Security audit clean; backups configured; encryption key verified |
| Document storage | N/A | Not enabled for this agency |

**Post-walkthrough:**
- Demo mode: Kept on (Sarah wants to use demo data for training new seasonal staff)
- Data Handling Acknowledgement: Signed by James (ED) and the developer
- 30-day check-in: Scheduled for four weeks after go-live

**Rationale:** The walkthrough took 45 minutes. Sarah tested the coach workflow (creating a plan, writing a note, recording metrics) while Maria tested admin functions (running a report, checking the audit log). The developer confirmed technical checks. One issue was found and corrected during the walkthrough: the "Workshop Facilitation" note template was missing the attendance notes section, which was added on the spot.
