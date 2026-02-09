# Privacy-by-Design Checklist

**Review this before any new feature ships.** Five questions. If you can't answer "yes" confidently to each, stop and fix the design before writing code.

---

## 1. Who sees this data?

- [ ] Does this feature display client information? Which roles can see it?
- [ ] Does a receptionist see anything they don't need for checking people in/out?
- [ ] Does a programme manager see individual client data they don't need?
- [ ] Are there fields that reveal diagnosis indirectly (medications, group names, referral reasons)?

## 2. Does it cross programme boundaries?

- [ ] Does this feature let someone in Programme A see data from Programme B?
- [ ] If yes: is there documented client consent for cross-programme sharing?
- [ ] Could the feature leak programme membership itself? (e.g., showing "enrolled in Youth Counselling" reveals reason for service)

## 3. Does it export or extract data?

- [ ] Does the feature create a file (CSV, PDF, etc.) containing client information?
- [ ] Who can trigger the export? Is it logged in the audit trail?
- [ ] Does the export contain individual records or only aggregates?
- [ ] Could someone screenshot or print the data? (If yes, that's OK -- but the audit trail should note the access)

## 4. Would it expose a DV client?

- [ ] Could this feature reveal that someone IS a client? (In a DV shelter, even the client list is sensitive)
- [ ] Could it reveal a client's location? (Address fields, programme location, check-in records)
- [ ] Could someone use this feature to find out if a specific person is receiving services?
- [ ] Apply the "angry ex-partner" test (see below)

## 5. Is the minimum necessary principle met?

- [ ] Does each role see ONLY the information needed for their job function?
- [ ] Could you achieve the same feature with LESS data visible?
- [ ] Are there fields included "just in case" that could be removed?
- [ ] When in doubt: it's clinical data, and clinical data is restricted.

---

## When to Use This Checklist

- Before building any new view that displays client data
- Before adding new fields to existing views
- Before building export or report features
- Before changing who can access existing features
- After ANY AI-generated code that touches client data

## Quick Reference: Safety vs Clinical Data

| Safety data (receptionist can see) | Clinical data (staff and above only) |
|------------------------------------|--------------------------------------|
| Allergies | Diagnosis |
| Medical alert conditions (name only) | Medications |
| Emergency contacts | Treatment plans |
| Staff alerts | Session notes |
| | Referral reasons |
| | Group membership |
| | Intake forms |
| | Metrics and events |

## The "Angry Ex-Partner" Test (for DV Programmes)

If an abusive ex-partner gained 5 minutes of access to a front desk workstation, could they:

| Risk | Fix |
|------|-----|
| Confirm their ex is a client here? | Search-only interface, never confirm or deny |
| Find their ex's address or phone number? | Address suppression for flagged clients |
| Read session notes about what their ex disclosed? | Clinical data blocked for receptionist role |
| See which programme their ex is in? | Programme names shouldn't reveal service type on screens visible to receptionist |
