# 04 — Programs

## What This Configures

Programs are how KoNote organises your agency's work. Each program represents a distinct service line — for example, "Financial Coaching," "Housing Support," or "Youth Employment." Programs control which staff see which participants, which metrics and templates are available, and how reports are generated. If your agency runs one program, you still create it here so the system knows what it is called.

## Decisions Needed

1. **What are your distinct programs or service lines?**
   - List every program your agency runs that should be tracked separately in KoNote
   - Think of it as: if a funder asked "what do you do?", what would the list be?
   - Each program can have its own staff, templates, metrics, and reports
   - Default: Must create at least one program

2. **For each program, is it confidential?**
   - **Yes (confidential)** → even knowing someone is enrolled could cause harm (e.g., domestic violence shelter, substance use treatment, HIV/AIDS services, mental health crisis). Staff who work in both standard and confidential programs will be asked to choose which context they are working in before seeing any participant data. This prevents accidental information leakage.
   - **No (standard)** → enrolment itself is not sensitive (e.g., youth drop-in, housing search, employment support)
   - Default: Standard (not confidential)

3. **Do any staff work across multiple programs?**
   - Yes → they will need role assignments in each program (decided in Document 03). The system keeps program data separate even for cross-program staff.
   - No → each staff member works in one program only
   - Default: Each person is assigned to specific programs during user setup

4. **Are the programs distinct enough to need separate tracking, or could some be combined?**
   - Separate → different staff, different outcomes, different funders, different reporting
   - Combined → same staff, same approach, just different names or locations; consider making them one program with tags or custom fields to distinguish
   - Default: When in doubt, keep them separate — you can always merge data in reports, but you cannot separate data that was entered together

5. **Do different programs track different outcomes?**
   - Yes → each program will get its own set of enabled metrics (configured in Document 05)
   - No → one standard set of metrics across the organisation
   - Default: Programs share the metric library but can enable/disable metrics individually

6. **Will programs need separate plan templates, or can they share one?**
   - Separate → each program defines its own plan structure (e.g., financial coaching has budgeting/income/housing sections; youth employment has skills/education/employment sections)
   - Shared → one template works for all programs
   - Default: One global template; program-specific templates can be added later

7. **What is the public-facing name for each program?**
   - Internal names may differ from what participants see (e.g., "Substance Use Recovery" internally might display as "Wellness Support" on the participant portal)
   - Default: The program name is used everywhere. If the portal is enabled, consider whether the internal name is appropriate for participants to see.

## Common Configurations

- **Financial coaching agency (single funder):** One program ("Financial Coaching"), not confidential, shared plan template, all coaches assigned
- **Financial coaching agency (multiple funders):** One program per funder stream (e.g., "Financial Empowerment - Funder A," "Tax Clinic - Funder B"), separate reporting per program, shared plan template
- **Multi-service agency:** Several programs (e.g., "Housing Support," "Employment," "Counselling," "Youth Drop-In"), counselling marked confidential, separate metrics per program
- **DV shelter:** All programs marked confidential, strict program separation, no cross-program access for front desk

## Output Format

Programs are created through the KoNote admin interface or through the `apply_setup` management command.

**Admin interface steps:**
1. Click the gear icon, then "Programs"
2. Click "+ New Program"
3. Enter the program name and description
4. If confidential, check the confidential flag
5. Click "Create"
6. Assign staff to the program with appropriate roles (Direct Service, Program Manager, etc.)

**For each program, capture:**

| Field | Value |
|-------|-------|
| Program name | |
| Description | (brief — appears on reports and the portal) |
| Confidential? | Yes / No |
| Key staff | (names and roles) |
| Distinct metrics? | Yes / No (if yes, configured in Document 05) |
| Distinct plan template? | Yes / No (if yes, configured in Document 06) |

## Dependencies

- **Requires:** Document 03 (Roles & Permissions) — you need to know who has what role before assigning staff to programs
- **Feeds into:** Document 05 (Surveys & Metrics) — metrics are enabled per program. Document 06 (Templates) — plan and note templates can be program-specific. Document 07 (Reports) — reports are generated per program. Document 08 (Users) — user accounts are assigned to programs.

## Example: Financial Coaching Agency

**Programs created:**

| Program Name | Description | Confidential? | Key Staff | Notes |
|-------------|------------|--------------|----------|-------|
| Financial Empowerment | One-on-one financial coaching and goal setting | No | 2 coaches, 1 PM | Primary funder reporting stream |
| Tax Clinic | Seasonal free tax preparation service | No | 1 coach (seasonal), 1 PM | Runs January to April |
| Community Workshops | Group financial literacy workshops | No | All coaches | Group-based; uses group sessions feature |

**Rationale:**
- Three programs match three distinct funder reporting streams
- None are confidential — knowing someone uses a financial coaching service is not inherently sensitive
- The Program Manager oversees all three, with a Direct Service role in each
- Community Workshops uses the Groups feature for attendance tracking
- All three share the same plan template ("Action Plan") but may track slightly different metrics
