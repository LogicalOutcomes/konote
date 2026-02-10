# Annual Security Review Checklist — Confidential Programs

Use this checklist once a year (or after any security incident) to verify that confidential program isolation is working correctly. This review should be completed by an administrator or Privacy Officer.

**Last reviewed:** ____________
**Reviewed by:** ____________
**Next review due:** ____________

---

## 1. Access Control

- [ ] Each confidential program has a designated program manager
- [ ] Only staff who need access have roles in confidential programs
- [ ] No staff members have been granted confidential program access "just in case"
- [ ] Former staff (resigned, transferred, terminated) have been removed from confidential program roles
- [ ] Superuser accounts are limited to the minimum necessary (ideally 1–2)
- [ ] Superusers understand they cannot browse confidential client records

---

## 2. Audit Log Review

- [ ] Pull the audit log for each confidential program (click **Admin** → **Audit Logs**, filter by program)
- [ ] Review access patterns — are the right people accessing records?
- [ ] Check for any unusual access (unexpected users, off-hours access, bulk record views)
- [ ] Verify that access denials (403 errors) are being logged
- [ ] Confirm audit logs are stored in the separate audit database (not the main application database)
- [ ] Verify audit log entries cannot be modified or deleted by staff

---

## 3. Confidential Isolation Verification

- [ ] Log in as a **standard program** staff member and confirm:
  - [ ] Confidential program clients do **not** appear in client search results
  - [ ] Confidential program clients do **not** appear in the client list
  - [ ] Confidential program names do **not** appear on any client's profile
  - [ ] Creating a new client does **not** show duplicate matches from confidential programs
  - [ ] "No results found" messages do **not** hint at hidden records
- [ ] Log in as a **superuser** and confirm:
  - [ ] Individual confidential client records are **not** browsable in Django admin
  - [ ] Confidential program aggregate counts show "< 10" when below threshold
- [ ] Log in as a **confidential program** staff member and confirm:
  - [ ] Only clients in their specific confidential program are visible
  - [ ] No cross-program matching banners appear when creating clients

---

## 4. Test Suite

- [ ] Run the confidential isolation tests: `python manage.py test tests.test_confidential_isolation -v 2`
- [ ] All tests pass with zero failures
- [ ] No tests have been skipped or commented out
- [ ] Test file has not been modified to weaken assertions since last review

---

## 5. Reports & Exports

- [ ] Exported CSV files do **not** include confidential program client data for non-authorised users
- [ ] Aggregate reports use small-cell suppression (show "< 10" for confidential programs with fewer than 10 clients)
- [ ] PDF exports do **not** leak confidential program enrolment information
- [ ] Funder reports do **not** include confidential program data unless the funder is explicitly authorised

---

## 6. Data Handling

- [ ] Encryption keys are backed up securely and separately from database backups
- [ ] Database backups are stored in a location with access restricted to authorised personnel only
- [ ] Hosting provider's data processing agreement is current and on file
- [ ] No confidential client data has been copied to spreadsheets, emails, or other systems outside KoNote

---

## 7. Staff Training

- [ ] Confidential program staff understand what "confidential" means in KoNote
- [ ] Confidential program staff know how to report a suspected privacy breach
- [ ] Standard program staff understand they will not see confidential program clients (so they don't assume the system is broken)
- [ ] New staff hired since last review have been oriented on confidential program policies

---

## 8. Policy & Documentation

- [ ] Privacy Impact Assessment is on file and up to date
- [ ] Agency privacy policy reflects confidential program handling
- [ ] Incident response plan is documented and staff know where to find it
- [ ] Any changes to confidential program configuration since last review are documented

---

## Review Outcome

- [ ] **All items verified** — no issues found
- [ ] **Issues found** — document below and assign follow-up

### Issues Found

| # | Issue | Severity | Assigned to | Resolved |
|---|-------|----------|-------------|----------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

### Sign-Off

Reviewer: ________________________ Date: ____________

Privacy Officer: ________________________ Date: ____________
