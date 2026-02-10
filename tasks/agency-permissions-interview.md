# Agency Permissions Setup Interview

**Purpose:** Walk a new agency through all the decisions they need to make about who can see and do what in KoNote. The result is a completed Configuration Worksheet that maps directly to system settings.

**Time:** 60-90 minutes
**Who should be in the room:** Executive Director (or designate), at least one Program Manager, Front Desk lead (if applicable), privacy officer (if they have one)

---

## Before the Interview

### Send the Agency a Prep Sheet (1 week ahead)

> **Getting Ready for Your KoNote Permissions Setup**
>
> Next week we'll walk through how to set up who can see and do what in KoNote. To make the most of our time, please think about:
>
> 1. **Your staff roles** — a list of job titles and which program(s) each person works in
> 2. **Your programs/services** — the distinct programs you run (e.g., housing support, youth drop-in, counselling)
> 3. **Any sensitive programs** — services where even knowing someone is enrolled could cause harm (e.g., domestic violence shelters, substance use treatment)
> 4. **Your current intake form** — what information you collect when someone first walks in
> 5. **Any privacy incidents or near-misses** — situations where someone saw something they shouldn't have (no judgment — this helps us set it up right)
>
> You don't need to prepare formal documents. Even rough notes or a conversation among your team will help.

---

## The Interview

### Section 1: Your People

**Goal:** Map real job titles to KoNote's roles, and identify your system administrator(s).

KoNote has two layers of access:

1. **Program roles** — what client data you can see (one role per program, per person)
2. **System Administrator** — a separate flag that lets someone manage users, settings, and programs (but does NOT automatically grant access to client data)

These are independent. Someone can be a Staff member who is also an Admin, or an Admin with no program role at all (they can configure the system but can't see any client files).

#### Program Roles

Every person who works with client data gets assigned one of these roles per program. Someone can have different roles in different programs (e.g., a counsellor who also does intake in a smaller program).

| Program Role | Typical Job Titles | What They Generally Do |
|---|---|---|
| **Receptionist** | Front desk, intake worker, admin assistant | Greet clients, answer phones, book appointments, do intake paperwork |
| **Staff** | Counsellor, case worker, outreach worker, facilitator | Direct work with clients — notes, plans, group facilitation |
| **Program Manager** | Program coordinator, team lead, clinical supervisor | Oversee a program, supervise staff, review reports |
| **Executive** | Executive Director, board member, funder liaison | See the big picture — aggregate numbers, not individual files |

#### System Administrator

The System Administrator flag is separate from program roles. It controls:
- Creating and deactivating user accounts (across the whole agency)
- Managing programs (creating, editing, archiving)
- Changing system settings (feature toggles, terminology, branding)
- Viewing the full audit log

**The administrator flag does NOT grant access to client data.** An admin with no program role can set up the entire system without ever seeing a client file. If the admin also needs to see client data, they need a program role too.

Program Managers already get some admin-like powers for their own program (managing their team, viewing their program's audit log). The System Administrator flag is for agency-wide system management.

#### Questions to Ask

**1.1** "Can you walk me through the job titles at your agency? For each person (or type of person), tell me what they actually do day-to-day."

*Record each title and map it to one of the four program roles. Flag any that don't fit neatly.*

**1.2** "Does anyone wear multiple hats? For example, is your ED also a direct service provider? Does a counsellor also do intake?"

*These people will need roles in multiple programs. Note which hat they wear in which program.*

**1.3** "Do you have any volunteers or students who need system access? What should they be able to see?"

*Typically map to Receptionist (limited view) or Staff (if doing direct service under supervision).*

**1.4** "Is anyone on your board going to use the system? What would they need to see?"

*Board members are typically Executive role — aggregate data only, never individual client files.*

**1.5** "Who should be your system administrator — the person who can create user accounts, turn features on and off, and manage programs?"

*Common patterns:*
- **ED is the admin** — common in small agencies. Give them the admin flag plus whatever program role they need.
- **PM is the admin** — common when the ED is hands-off. The PM already manages their own team; the admin flag extends this to the whole agency.
- **Dedicated IT/office manager** — in larger agencies, someone handles system admin without needing to see client data. Give them the admin flag with no program role.
- **Two admins** — recommended for continuity. If one person is away, the other can manage accounts.

**1.6** "Should your system administrator also be able to see client files? Or should they just manage the system?"

*This is a meaningful privacy choice. An admin with no program role has zero access to client data — they can't even accidentally see it. This is the most restrictive option and works well for IT staff or office managers who don't do direct service.*

#### Common Tensions to Explore

- **"Our front desk person also does counselling."** → They'll be Receptionist in the intake flow but Staff in their counselling program. Two role assignments.
- **"Our ED reads all the client files."** → This is a privacy risk worth discussing. KoNote supports it (give them a Staff or PM role), but the question is whether they *should*. See Section 5.
- **"We're too small for roles — everyone does everything."** → Fine. Assign everyone as Staff. But still designate at least one person as PM (for reporting) and consider whether front desk volunteers should see clinical notes.
- **"Our admin needs to troubleshoot issues with client records."** → Consider giving them a PM role in one program (limited scope) rather than Staff in all programs (full clinical access everywhere). They can see enough to troubleshoot without having blanket access.

#### Record

| Person/Title | Program(s) | Program Role | System Admin? | Notes |
|---|---|---|---|---|
| | | | Yes / No | |
| | | | Yes / No | |

---

### Section 2: Your Programs

**Goal:** Set up programs and identify which ones are confidential.

**2.1** "What distinct programs or services do you run? Think of it as: if a funder asked 'what do you do?', what would the list be?"

*Each distinct service with its own staff, clients, or reporting becomes a KoNote program.*

**2.2** "For each program, would someone be harmed if an unauthorized person found out they were enrolled?"

*This identifies confidential programs. Examples:*
- Domestic violence shelter — knowing someone is there could put them at risk
- Substance use treatment — stigma, employment consequences
- HIV/AIDS services — disclosure could cause discrimination
- Mental health crisis — stigma in small communities

*A youth drop-in or housing search program is usually NOT confidential — enrollment itself isn't sensitive.*

**2.3** "Do any staff work across programs? Which ones?"

*This matters because KoNote can restrict what people see based on their program. If a housing worker also helps in the DV program, they'll need access to both — but the system will keep those contexts separate.*

**2.4** "What do you call your programs internally? And would you want clients to see different names?"

*Some programs have clinical or funder-facing names that shouldn't appear on a client's screen. Example: "Substance Use Recovery" might be better displayed as "Wellness Support" on a client portal.*

#### Important: The Confidential Program Rule

> When a program is marked as confidential, staff who work in both standard and confidential programs will be asked to choose which context they're working in before seeing any client data. This prevents accidental information leakage — for example, a receptionist covering the front desk for the whole building won't accidentally see that a client is enrolled in the DV program.

**2.5** "Is that separation something you'd want? Or does everyone in your agency already know about all programs?"

*Small agencies with 5 staff may not need this. Large multi-service agencies almost always do.*

#### Record

| Program Name | Confidential? | Staff Who Work In It | Notes |
|---|---|---|---|
| | | | |
| | | | |

---

### Section 3: What Front Desk Can See

**Goal:** Make the hardest privacy decision — what does the person who answers the phone need to know?

This is where agencies differ the most. KoNote's default gives front desk (Receptionist role) access to:
- Client name
- Phone number and email
- Emergency contact
- Allergies (safety)
- Status (active/inactive)

Front desk does NOT see by default:
- Clinical notes
- Group membership (because the group name can reveal the reason for service)
- Medications (reveals diagnosis)
- Diagnosis or clinical assessments
- Detailed progress metrics

#### Walk Through Scenarios

Read each scenario aloud and ask: "What would need to happen at your agency?"

**Scenario A — Phone call:**
> "A client calls and says: 'I have an appointment today but I'm running late.' The front desk person needs to check whether they have an appointment and with whom."

- *What do they need to see?* (Name, appointment/schedule, their worker's name)
- *What should they NOT see?* (Why they're coming, what program they're in)

**Scenario B — Walk-in:**
> "Someone walks in for the first time. Front desk does the intake — collects their name, contact info, emergency contact, and some demographic information."

- *What intake fields does front desk fill in?*
- *Are there any fields on your intake form that front desk should NOT fill in?* (e.g., presenting concerns, referral source with clinical detail)

**Scenario C — Emergency:**
> "A client has a medical emergency in your lobby. Paramedics arrive and ask: 'Does this person have any allergies? Are they on any medications?'"

- *Should front desk be able to see allergies?* (Usually yes — this is a safety issue)
- *Should front desk be able to see medications?* (This is the tension — medications reveal diagnosis, but paramedics may need it)

**Scenario D — Family member calls:**
> "Someone calls and says 'I'm looking for my partner — are they a client of yours?' Front desk needs to handle this without confirming or denying."

- *How do you handle this currently?*
- *What should the system show or not show that could affect this?*

**Scenario E — Group pickup:**
> "A parent calls to check what time the youth group ends so they can pick up their child."

- *Should front desk know which groups exist and their schedules?*
- *Should they see who is in the group?* (Remember: group name can reveal reason for service — "Anger Management Group" tells you something about the members)

#### Decision Points

Based on the scenarios, confirm these choices:

| What Front Desk Sees | Default | Your Choice | Notes |
|---|---|---|---|
| Client name | Yes | | |
| Phone / email | Yes | | |
| Emergency contact | Yes | | |
| Allergies | Yes | | |
| Client status (active/inactive) | Yes | | |
| Birth date | No | | Reveals age; may or may not be needed at desk |
| Medications | No | | Reveals diagnosis; discuss paramedic scenario |
| Group names and schedules | No | | Group name can reveal diagnosis |
| Group membership (who is in which group) | No | | Most sensitive — reveals reason for service |
| Which program a client is in | No | | Could reveal reason for service |
| Clinical notes | No | | Almost always no |
| Progress metrics | No | | Almost always no |

#### Custom Intake Fields

**3.6** "You mentioned you collect [demographic fields] at intake. For each one, should front desk be able to see it, edit it, or not see it at all?"

*Go through the agency's actual intake form field by field.*

| Intake Field | Front Desk Access | Notes |
|---|---|---|
| | None / View / Edit | |
| | None / View / Edit | |

---

### Section 4: What Program Managers Can See

**Goal:** Decide the scope of PM access — especially for agencies with multiple programs.

KoNote's default gives Program Managers:
- Full client data for clients in their program (including clinical notes)
- Ability to view (not write) clinical notes for oversight purposes
- Aggregate reporting for their program
- User management within their program (assigning staff to roles)
- Audit log for their program

**4.1** "Should Program Managers be able to see individual client files? Or just aggregate numbers?"

*Most agencies say yes — PMs need to supervise clinical work. But some agencies (especially those with union environments or where PM is more administrative) prefer PMs to see only aggregate data unless they have a specific reason.*

**4.2** "Can a PM in Program A see files for clients in Program B?"

*Default: No. PMs are scoped to their own program. Discuss whether this is right for their agency.*

**4.3** "Should PMs be able to create or cancel safety alerts?"

*KoNote uses a two-person safety rule by default: Staff create alerts, PMs cancel them. This prevents one person from both raising and dismissing a safety concern. Does this work for your agency, or are you too small for two-person rules?*

**4.4** "Should PMs manage their own program's user accounts, or should that be centralized?"

*Options: PM manages their own team (default), or all user management goes through one system administrator.*

#### Record

| PM Decision | Choice | Notes |
|---|---|---|
| Can see individual client files? | Yes / No / With justification | |
| Can see across programs? | Own only / All / Specific ones | |
| Can create safety alerts? | Yes / No | |
| Can cancel safety alerts? | Yes / No (2-person rule) | |
| Can manage users in their program? | Yes / No (centralized) | |

---

### Section 5: Executive & Board Access

**Goal:** Set appropriate boundaries for leadership.

**5.1** "Who at the leadership level needs access to the system? What do they actually need to see?"

*Common patterns:*
- **ED who is operational** (meets with clients, supervises staff): Needs a PM or Staff role in specific programs, PLUS Executive for org-wide reporting
- **ED who is administrative only**: Executive role is sufficient (aggregate data)
- **Board members**: Executive role (aggregate only) — or no system access at all if they receive reports through other channels

**5.2** "Is your ED ever involved in direct client work?"

*If yes, they need a program-level role (Staff or PM) in addition to Executive. If no, Executive is sufficient and they will not see individual client files.*

**5.3** "Does your board review client-level data, or just aggregate reports?"

*If aggregate only: Executive role with no program assignments. If they need client data: this is a significant privacy decision that should be documented.*

**Important privacy note to share with the agency:**

> Every person who can see individual client data increases your privacy risk surface. It's not that you can't give leadership access — it's that every access point should be intentional and documented. If a privacy breach occurs, you'll need to show that access was appropriate and necessary.

#### Record

| Leader | Role | Sees Individual Data? | Notes |
|---|---|---|---|
| | | | |

---

### Section 6: Safety & Special Situations

**Goal:** Plan for conflict of interest, domestic violence safety, and access requests.

**6.1 Conflict of Interest**

"Has it ever happened that a staff member personally knew a client? What did you do?"

*KoNote can block specific staff-client pairs. If Worker A is blocked from Client B's file, they'll get a "you don't have access to this file" message — no details about why, no indication the client exists.*

**6.2** "Do you want to set up any blocks now, or just know the feature exists for when it's needed?"

**6.3 Domestic Violence Safety**

"Do you serve clients who are fleeing domestic violence? Could a perpetrator ever be a client or staff member at your agency?"

*If yes:*
- Use the client access block feature to prevent specific individuals from seeing specific files
- Mark the DV program as confidential (Section 2)
- Consider whether program names visible to front desk could reveal DV involvement
- Discuss quick-exit features for the participant portal (if using it)

**6.4 Privacy Access Requests (PIPEDA)**

"Under Canadian privacy law, clients have the right to see what information you hold about them. Who handles those requests currently?"

*KoNote can support this with a designated permission. Options:*
- Program Managers handle requests for their program
- A single privacy officer handles all requests
- Executive Director handles requests

**6.5 Staff Departure**

"When a staff member leaves your agency, what's your current process for revoking their access?"

*KoNote supports deactivating users and removing program assignments. Important to have a process — not just a feature.*

#### Record

| Safety Decision | Choice | Notes |
|---|---|---|
| Any current access blocks needed? | Yes (list) / Not now | |
| DV program safeguards? | N/A / Confidential flag / Access blocks / Both | |
| Who handles privacy access requests? | PM / Privacy officer / ED | |
| Staff departure process? | Describe | |

---

### Section 7: Features to Turn On

**Goal:** Quick pass through optional features — on or off for this agency.

KoNote has features that can be turned on or off for each agency. Walk through the list:

| Feature | What It Does | Default | Your Choice |
|---|---|---|---|
| **Programs** | Organize services into distinct programs | On | |
| **Groups** | Track group sessions and membership | On | |
| **Alerts** | Safety alerts between staff about clients | On | |
| **Quick Notes** | Brief notes outside of formal session notes | On | |
| **Charts & Analysis** | Visual progress charts for clients | On | |
| **Events** | Calendar events and appointments | On | |
| **Shift Summaries** | End-of-shift handover notes | Off | |
| **Client Photos** | Profile photos for clients | Off | |
| **Plan Export to Word** | Export care plans as Word documents | Off | |
| **AI Assist** | AI-powered suggestions for note writing | Off | |
| **Participant Portal** | Clients can see their own goals and progress | Off | |

**7.1** For each feature marked "On" that you're turning off: "Tell me why — is it not relevant, or are you concerned about it?"

*Their answer helps distinguish "we don't need this" from "we're worried about this" — the latter may need further discussion.*

**7.2** For each feature marked "Off" that they want on: "Let me explain what turning this on means for privacy and workload."

---

## After the Interview

### 1. Create the Configuration Summary (same day)

Write up a one-page summary of all decisions made, organized as:

> **Agency:** [Name]
> **Date:** [Date]
> **Participants:** [Who was in the room]
>
> **Programs:** [List with confidential flags]
> **System Administrator(s):** [Who has the admin flag, and do they also have a program role?]
> **Role Assignments:** [Table of people → program roles → programs]
> **Front Desk Visibility:** [What receptionist can/cannot see]
> **PM Scope:** [Individual vs aggregate, cross-program access]
> **Executive Access:** [Who, what level]
> **Safety Measures:** [Access blocks, confidential programs, DV safeguards]
> **Feature Toggles:** [What's on/off]
> **Privacy Request Handler:** [Who]
> **Staff Departure Process:** [Summary]

### 2. Send for Sign-Off (within 1 week)

Send the Configuration Summary to the ED or designated decision-maker with:

> "Please review these permission settings. Once you confirm, we'll configure your KoNote instance to match. You can change any of these settings later, but it's important to start with intentional choices rather than defaults."

### 3. Configure the System

Use the Configuration Summary to:
- Create programs (mark confidential ones)
- Set feature toggles
- Create user accounts with correct program role assignments
- Assign the System Administrator flag to designated admin(s)
- Configure custom field visibility for front desk
- Set up any access blocks
- Set terminology overrides if the agency uses different words

### 4. Verify with a Walkthrough (30 minutes)

After configuration, do a quick walkthrough with the agency:
- Log in as a front desk user — show what they can and can't see
- Log in as a staff user — show program-scoped access
- Log in as PM — show oversight capabilities
- Log in as executive — show aggregate-only view
- Log in as admin (with no program role) — show they can manage settings but can't see client files
- Try to access something they shouldn't — show the "access denied" message

This builds confidence that the system is doing what they decided.

### 5. Schedule a 30-Day Check-In

> "After your team has used the system for 30 days, let's revisit these decisions. Sometimes agencies discover that front desk needs to see one more field, or that a PM needs different access. That's normal — the system is designed to adjust."

---

## Quick Reference: What's Configurable vs Fixed

### Agencies CAN change:
- Which program role each person has (and in which program)
- Who has the System Administrator flag
- Whether the admin also has a program role (and which one)
- What custom fields front desk can see
- Which features are turned on/off
- Program names and confidentiality flags
- Terminology (what you call clients, programs, etc.)
- Access blocks for specific staff-client pairs

### Agencies CANNOT change:
- The four program roles themselves (Receptionist, Staff, PM, Executive)
- The separation between program roles and system administration
- The core permission rules (e.g., front desk never sees clinical notes)
- The two-person safety rule for alert cancellation
- The separation between demo and real data
- The audit trail (all access is logged, always)
- Encryption of personal information (always on)

### Privacy Non-Negotiables (built into the system):
- Clinical notes are never visible to front desk
- Group membership is never visible to front desk (group type reveals diagnosis)
- Executive/board members never see individual client data unless explicitly given a program role
- All data access is logged in an immutable audit trail
- Personal information is encrypted at rest
- Deleted records are soft-deleted (audit trail preserved)

---

## Appendix: Difficult Conversations

### "Why can't front desk see everything? They need to help clients."

Front desk staff are often the most trusted people in an agency. The restriction isn't about trust — it's about liability. If front desk can see clinical notes and there's a privacy breach, the agency is liable for every piece of data that was accessible. Limiting access limits the blast radius of any incident.

**Reframe:** "It's not that we don't trust your front desk. It's that if their password is stolen, or they leave their screen unlocked, the damage is contained to names and phone numbers — not clinical histories."

### "We're too small for all this — everyone knows everything anyway."

Even in a 5-person agency, documenting your permission decisions matters because:
1. Staff change. The next hire might not be appropriate for full access.
2. Funders and accreditors ask about privacy controls.
3. If a client files a privacy complaint, you need to show intentional decisions, not "everyone had access to everything."

**Reframe:** "You're right that your current team is trusted. This isn't for today — it's for the day something goes wrong, or someone new starts, or an accreditor asks how you protect client data."

### "Our ED needs to see everything."

This is common and often legitimate — especially in small agencies where the ED is also the clinical supervisor. The question to ask:

"Does your ED *need* to see individual client files to do their job, or do they *want* to because they always have? If they need to — great, we'll set that up. If it's habit, there might be a lighter-touch option that still gives them oversight without the liability."

**Options:**
- ED gets PM role in all programs (full individual access, logged)
- ED gets Executive role + PM role in one program (oversight for most, detailed access where they supervise)
- ED gets Executive role only (aggregate data, requests individual access when needed)

### "Why is admin separate from the roles? Our admin needs to see client files to help people."

The separation exists to protect client data. Many system problems (password resets, user account issues, turning features on/off) can be solved without ever opening a client file. Keeping those separate means your IT person or office manager can keep the system running without having clinical access they don't need.

If your admin genuinely needs to see client data — for example, they're also a Program Manager — that's fine. Give them both: the admin flag for system management, and a PM role in their program for client oversight. The point is that each access level is an intentional choice, not a side effect.

**Reframe:** "Think of it like keys to a building. The janitor has a master key to every room for maintenance — but they don't automatically get the key to the filing cabinet with client records. If they need both, we give them both. We just don't bundle them together by default."

### "Can we change this later?"

Yes. Every permission setting can be changed at any time. Role assignments, feature toggles, custom field visibility, access blocks — all adjustable through the admin panel. The 30-day check-in exists specifically for this.

The only thing that can't be undone is access that already happened. Once someone has seen a client's file, you can revoke future access but not the fact that they saw it. That's why it's worth getting it right from the start — even knowing you can change it.
