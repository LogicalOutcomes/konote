# 06 — Templates

## What This Configures

The structure for coaching plans and session notes. Plan templates define what sections and goals appear when a coach creates a new plan for a participant. Note templates define what coaches see when they write a progress note — the sections, prompts, and structure for documenting each type of interaction. Together, these templates ensure consistent documentation across your team.

## Decisions Needed

### Plan Templates

1. **When a coach starts working with a new participant, what does the plan look like?**
   - A plan template is a collection of sections. Each section represents a broad goal area (e.g., "Financial Stability," "Income," "Housing").
   - Within each section, you define the default targets (specific goals) that coaches can choose from.
   - Coaches can always add, remove, or customise targets for individual participants — the template is a starting point, not a constraint.
   - Default: No plan template is pre-configured; you build one during setup.

2. **What sections (broad goal areas) should the plan cover?**
   - List the major areas of your agency's work. These become the sections of the plan template.
   - Example for a financial coaching agency: Financial Stability, Income, Housing, Education & Skills
   - Example for a counselling agency: Mental Health, Relationships, Daily Living, Employment
   - Default: Must define at least one section

3. **What are typical goals within each section?**
   - These become the suggested targets when a coach creates a plan. They are suggestions, not requirements.
   - Example: Under "Financial Stability" → "Create and follow a monthly budget," "Reduce debt by 20%," "Build emergency savings of $500"
   - Default: No suggested targets until you define them

4. **Do different programs use different plan structures, or is there one standard template?**
   - One standard template → simpler; works when all programs follow a similar approach
   - One template per program → necessary when programs track fundamentally different outcomes (e.g., a housing program tracks housing goals; an employment program tracks career goals)
   - Default: One global template. Program-specific templates can be added later by Program Managers.

5. **Would it be helpful to build a template during the setup session so you can see how it looks?**
   - Yes → build one live during the configuration meeting; this makes it tangible and gives the team something to react to
   - No → provide the section and target list and have the developer configure it
   - Default: Building a live template is recommended

### Note Templates

6. **What types of interactions do your coaches have with participants?**
   - For each type, decide whether the default note templates work or need adjustment.
   - KoNote comes with six default note templates:

   | Default Template | Use Case | Keep / Rename / Remove? |
   |-----------------|----------|------------------------|
   | Standard session | Regular participant meetings | |
   | Brief check-in | Quick touchpoints | |
   | Phone/text contact | Remote contact documentation | |
   | Crisis intervention | Safety concerns, urgent situations | |
   | Intake assessment | First meeting with new participants | |
   | Case closing | Discharge and case closure | |

   - Staff can also select "Freeform" for unstructured notes without pre-defined sections.
   - Default: All six templates are available. You can rename, restructure, or archive any of them.

7. **For a standard coaching session, what sections should the note include?**
   - Common sections:
     - Session summary (what happened) — free text
     - Plan progress (metrics and goals) — links to outcome tracking
     - Participant feedback or own words — free text
     - Next steps or action items — free text
   - Default: A basic structure with session summary and plan progress sections

8. **Do you need any additional note templates?**
   - Common additions: group workshop note, supervision note, outreach contact, referral follow-up
   - For each new template, define the name and sections
   - Default: No additional templates until you create them

9. **Do your funders require specific documentation in session notes?**
   - If yes, ensure the note template includes sections that capture required information (e.g., time spent, service type, follow-up actions)
   - Default: No funder-specific fields unless added

10. **Should the "co-creation" checkbox on notes be required or optional?**
    - Every progress note includes a checkbox labelled "We created this note together (this is recommended)"
    - Optional (default) → staff can save a note without ticking it; encourages co-creation without blocking submission
    - Required → staff must tick the checkbox; use this only if your agency's internal policy mandates documented co-creation confirmation on every note
    - Default: Optional (recommended — a mandatory tick can become a reflexive click that creates a false audit trail)

## Common Configurations

- **Financial coaching agency:** One plan template with four sections (Financial Stability, Income, Housing, Education & Skills). Standard session note renamed to "Coaching Session." Keep brief check-in, phone/text contact, and case closing. Archive crisis intervention (refer externally). Add "Workshop Facilitation" note template for group sessions.
- **Community counselling agency:** One plan template per program. Clinical session note with presenting concerns, interventions, and risk assessment sections. Keep all six defaults. Add "Supervision" note template. Co-creation checkbox optional.
- **Youth drop-in centre:** Simple plan template with two sections (Goals, Skills). Simplified session note with just "What happened" and "Next steps." Keep intake and case closing. Archive others.

## Output Format

### Plan Templates

Plan templates are created through the admin interface.

**Admin interface steps:**
1. Click the gear icon, then "Plan Templates"
2. Click "+ New Template"
3. Enter a template name (e.g., "Financial Coaching Action Plan")
4. Add sections — each section has a name and optional description
5. Within each section, add suggested targets — each target has a name and optional description
6. Save the template

**Example template structure:**

```
Template: Financial Coaching Action Plan

Section: Financial Stability
  - Create and follow a monthly budget
  - Reduce total debt by a target percentage
  - Build emergency savings fund
  - Improve credit score

Section: Income
  - Obtain or maintain employment
  - Increase household income
  - Access entitled benefits (e.g., GST credit, CCB, WITB)

Section: Housing
  - Maintain stable housing for 3+ months
  - Reduce housing cost to under 30% of income

Section: Education & Skills
  - Enrol in training or certification program
  - Complete financial literacy course
```

### Note Templates

Note templates are created or edited through the admin interface.

**Admin interface steps:**
1. Click "Manage," then "Note Templates"
2. Click "+ New Template"
3. Enter a name (this appears in the "This note is for..." dropdown)
4. Add sections:
   - **Basic Text** — free-text area for narrative content
   - **Plan Targets** — shows the participant's active plan targets with metric inputs
5. Set the sort order for each section
6. Save the template

**Example note template:**

```
Template: Coaching Session

Section 1: Session Summary (Basic Text)
  "What happened in this session?"

Section 2: Plan Progress (Plan Targets)
  [Shows active goals with metric entry fields]

Section 3: Participant Feedback (Basic Text)
  "What did the participant say about their progress?"

Section 4: Next Steps (Basic Text)
  "What are the action items before the next session?"
```

## Dependencies

- **Requires:** Document 04 (Programs) — plan templates can be program-specific. Document 05 (Surveys & Metrics) — plan targets reference metrics for outcome tracking.
- **Feeds into:** Document 09 (Verification) — the walkthrough tests that templates appear correctly and capture the right information.

## Example: Financial Coaching Agency

**Plan template:** "Financial Coaching Action Plan" — four sections (Financial Stability, Income, Housing, Education & Skills) with 2-4 suggested targets per section. Used across all three programs.

**Note templates:**

| Template | Sections | Programs |
|----------|----------|----------|
| Coaching Session (renamed from "Standard session") | Session Summary, Plan Progress, Participant Feedback, Next Steps | All |
| Brief Check-in | Summary, Follow-up Actions | All |
| Phone/Text Contact | Contact Summary | All |
| Intake Assessment | Background, Presenting Concerns, Initial Goals, Referral Source | All |
| Case Closing | Closing Summary, Outcomes Achieved, Referrals Made | All |
| Workshop Facilitation (new) | Workshop Topic, Activities, Attendance Notes | Community Workshops only |

**Rationale:** The agency renamed "Standard session" to "Coaching Session" to match their language. They archived "Crisis intervention" because they refer crises externally rather than documenting them in KoNote. They added "Workshop Facilitation" for their group program. The co-creation checkbox is optional — coaches are encouraged to write notes with participants during sessions, but it is not enforced.
