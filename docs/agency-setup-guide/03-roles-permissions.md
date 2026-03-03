# 03 — Roles & Permissions

## What This Configures

Who can see what, who can do what, and how much privacy protection is built into the system. This is the most important configuration step because it determines how participant data is protected. Every access decision you make here is logged permanently — there is no way to erase the record of who saw what.

## Decisions Needed

### Access Tier

1. **How much privacy protection does your agency need?**
   - **Tier 1 — Open Access** → straightforward role-based access; best for small teams with non-sensitive data (after-school programs, recreation, education)
   - **Tier 2 — Role-Based** → adds per-field front desk controls and DV-Safe Mode; best for agencies with a dedicated front desk and some sensitive data
   - **Tier 3 — Clinical Safeguards** → adds GATED clinical access (managers must justify viewing clinical notes) and time-limited access grants; best for clinical counselling, addiction services, DV agencies
   - Default: Tier 1

   **Quick guide to choosing:**
   - Do you collect health information (diagnosis, treatment plans, medications)? → Tier 2 minimum, likely Tier 3
   - Do you serve people at risk of domestic violence? → Tier 3 with DV-Safe Mode
   - Do you have distinct roles (front desk, case workers, supervisors)? → Tier 2 minimum
   - Would a funder or accreditor expect an audit trail of who accessed individual records? → Tier 2 or 3
   - Everyone does everything, non-sensitive data? → Tier 1

### Role Assignments

2. **Who are your system administrators?**
   - These people can create user accounts, manage programs, change settings, and view the full access log
   - The administrator flag does NOT automatically grant access to participant data — it is a separate permission
   - Options: ED is admin (common in small agencies), PM is admin (common when ED is hands-off), dedicated IT/office manager (no participant data access), two admins (recommended for continuity)
   - Default: Must designate at least one

3. **Should your system administrator also see participant files?**
   - Yes → give them a program role (Direct Service or Program Manager) in addition to the admin flag
   - No → admin flag only; they can configure the system without ever seeing a participant file
   - Default: No program role (most restrictive option)

4. **How does each staff member map to a KoNote role?**

   For each person, choose one role per program:

   | Role | Typical Job Titles | What They See |
   |------|-------------------|---------------|
   | **Front Desk** | Receptionist, intake worker, admin assistant | Names, contact info, safety info. Cannot see clinical notes, plans, metrics, or group membership |
   | **Direct Service** | Counsellor, case worker, coach, facilitator | Full participant data for their assigned programs — notes, plans, metrics, groups |
   | **Program Manager** | Coordinator, team lead, clinical supervisor | Everything Direct Service sees, plus reports, team management, and access logs for their programs |
   | **Executive** | Executive Director, board member, funder liaison | Aggregate data only — counts, summaries, outcome reports. No individual participant files |

   - A person can have different roles in different programs (e.g., PM in one program, Direct Service in another)
   - Default: Must assign at least one role per user

### Front Desk Access

5. **What information does your front desk need to see?** (Tier 2 and 3 only)

   For each field, choose Hidden, View only, or View and edit:

   | Field | Default (Tier 1-2) | Default (Tier 3) |
   |-------|-------------------|------------------|
   | Phone number | View and edit | View and edit |
   | Email address | View and edit | View only |
   | Preferred name | View only | View only |
   | Date of birth | Hidden | Hidden |
   | Custom fields | Hidden | Hidden |

   - Default: Safe defaults apply. At Tier 1, these cannot be customised. At Tier 2+, administrators control each field.
   - Consider: Does front desk need to see allergies for emergencies? Should they see which program a participant is in? (At most agencies, no — the program name can reveal the reason for service.)

6. **Are there custom intake fields that front desk should be able to see or edit?**
   - For each custom field, decide: Hidden / View only / View and edit
   - Default: All custom fields are hidden from front desk

### Program Manager Scope

7. **Should Program Managers see individual participant files, or just aggregate numbers?**
   - Individual files → standard for clinical supervision
   - Aggregate only → for administrative PMs who do not supervise clinical work
   - Default: Individual files within their own programs

8. **Can a PM in Program A see files for participants in Program B?**
   - Own program only → most restrictive; standard for most agencies
   - All programs → only if the PM role spans the entire organisation
   - Specific programs → if a PM oversees multiple but not all programs
   - Default: Own program only

9. **Should PMs manage their own program's user accounts, or should that be centralised?**
   - PM manages their team → PMs can assign staff to roles within their own program
   - Centralised → all user management goes through the system administrator
   - Default: PM manages their own team

### Executive and Board Access

10. **Does your Executive Director need to see individual participant files?**
    - Yes, they are operationally involved → give them a PM or Direct Service role in specific programs, plus Executive for organisation-wide reporting
    - No, they are administrative only → Executive role is sufficient (aggregate data only)
    - Default: Executive role only

11. **Do board members need system access?**
    - Yes, aggregate data → Executive role (counts and summaries, no individual files)
    - No → board members receive reports through other channels; no KoNote account needed
    - Default: No system access

### Safety and Special Situations

12. **Do you need to block specific staff from seeing specific participant files?**
    - Yes → set up client access blocks (staff member sees a generic "no access" message; no indication the participant exists)
    - Not now, but want the option → note the feature for later
    - Default: No blocks (available on demand)

13. **Do you serve participants at risk of domestic violence?**
    - Yes → mark the relevant program as confidential; enable DV-Safe Mode (Tier 2+); consider hiding contact fields from front desk
    - No → skip DV-specific safeguards
    - Default: DV-Safe Mode available but not active until a participant is flagged

14. **Who handles privacy access requests (PIPEDA)?**
    - Participants have the right to see what information you hold about them
    - Options: Program Managers handle requests for their program / a single privacy officer handles all requests / Executive Director handles requests
    - Default: Must designate

15. **What is your staff departure process?**
    - When a staff member leaves: deactivate their KoNote account, remove SharePoint/Google Drive access, review for data on personal devices
    - Default: Must document a process; KoNote can deactivate accounts but cannot revoke access to external systems

### Export Notifications

16. **Who should be notified when someone exports participant data?**
    - Default (all system administrators) → simple, covers most agencies
    - Specific people (e.g., privacy officer, ED) → more targeted oversight
    - Default: All system administrators receive export notification emails

## Common Configurations

- **Small coaching agency (5 staff, non-clinical):** Tier 1, ED is admin with PM role in all programs, all staff are Direct Service, no front desk role needed, no DV safeguards, ED handles privacy requests
- **Community counselling agency (15 staff):** Tier 2, dedicated office manager as admin (no program role), clinical supervisors as PMs, front desk sees name/phone/email only, DV-Safe Mode enabled, privacy officer handles access requests
- **Women's shelter (10 staff, DV-focused):** Tier 3, two admins (neither with participant data access), all programs marked confidential, front desk sees names only (phone/email hidden), GATED clinical access for PMs, DV-Safe Mode mandatory, privacy officer designated

## Output Format

Permissions are configured through a combination of:

**Admin interface steps:**
1. Go to Admin, then Settings, then Access Tier — select Tier 1, 2, or 3
2. Go to User Management — create user accounts with appropriate roles and program assignments
3. Go to Field Access (Tier 2+) — configure which fields front desk can see
4. Go to Programs — mark confidential programs

**Configuration Summary (produced after the permissions interview):**

```
Agency: [Name]
Date: [Date]
Access Tier: [1 / 2 / 3]
System Administrators: [Names, with or without program roles]
Programs: [List with confidential flags]
Role Assignments: [Table of people → roles → programs]
Front Desk Visibility: [Field-by-field access levels]
PM Scope: [Individual / aggregate, own program / cross-program]
Executive Access: [Who, what level]
Safety Measures: [Access blocks, confidential programs, DV safeguards]
Export Notification Recipients: [Default or specific emails]
Privacy Request Handler: [Name and role]
Staff Departure Process: [Summary]
```

## Dependencies

- **Requires:** Nothing — but informed by Document 02 (Features), because the features you enable affect which permissions are relevant
- **Feeds into:** Document 04 (Programs) — programs are created based on the role mapping done here. Document 08 (Users) — user accounts are created with the roles and program assignments decided here. Document 09 (Verification) — the walkthrough tests that permissions work as configured.

## Example: Financial Coaching Agency

**Decisions:**
- Access Tier: Tier 1 (non-clinical coaching, small team, no front desk)
- System Administrator: Program Director (also has PM role in all programs)
- Backup Administrator: Executive Director (Executive role only — aggregate data for board reports)
- Role Assignments:
  - 3 Coaches → Direct Service in their assigned program
  - 1 Program Director → Program Manager in all three programs + admin flag
  - 1 Executive Director → Executive role + admin flag (backup)
- Front Desk: Not applicable (no dedicated front desk; all intake done by coaches)
- PM Scope: Individual files in own programs; cross-program visibility not needed
- Executive Access: ED sees aggregate data only; does not review individual participant files
- Safety Measures: No confidential programs; no DV safeguards needed; access blocks available if needed
- Export Notifications: Program Director and ED both receive notifications
- Privacy Request Handler: Program Director
- Staff Departure: Program Director deactivates account on last day; reviews for exported files on personal devices

**Rationale:** This small agency does not need complex permissions. Tier 1 provides role-based access without the overhead of per-field controls or clinical gates. The ED chose aggregate-only access to reduce the agency's privacy footprint — fewer people with individual file access means less exposure if something goes wrong.
