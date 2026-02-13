# KoNote Web — Agency Setup Guide

Welcome to KoNote Web! This guide walks you through initial configuration after your deployment goes live. No technical knowledge required — all setup is done through the web interface.

> **Estimated time:** 30–45 minutes for a basic setup; longer if you plan to customise terminology, create many programs, or build detailed templates.

---

## Table of Contents

1. [Deployment Phases](#deployment-phases)
2. [Demo Mode and Training Accounts](#demo-mode-and-training-accounts)
3. [First Login](#first-login)
4. [Configure Instance Settings](#configure-instance-settings)
5. [Customise Terminology](#customise-terminology)
6. [Enable/Disable Features](#enable-disable-features)
7. [Create Programs](#create-programs)
8. [Create User Accounts](#create-user-accounts)
9. [Set Up Plan Templates](#set-up-plan-templates)
10. [Set Up Progress Note Templates](#set-up-progress-note-templates)
11. [Configure Custom Fields](#configure-custom-fields)
12. [Review Event Types](#review-event-types)
13. [Next Steps](#next-steps)

---

## Deployment Phases

KoNote deployment happens in three phases. You can move through them at your own pace.

### Phase 1: Assessment

Explore the system using demo data before making any configuration decisions.

- Log in as one of the **demo users** (see table below for all 6 accounts)
- Browse the 15 sample clients (DEMO-001 through DEMO-015) across 5 programs
- See how plans, progress notes, metrics, and reports work
- No real client data is involved — experiment freely

**Goal:** Understand how KoNote works before customising it.

### Phase 2: Customisation

Configure KoNote for your organisation's needs.

- Set your agency's terminology ("Client" → "Participant", etc.)
- Create your programs and assign staff
- Build plan templates and progress note templates
- Configure custom fields for your intake forms
- Create real staff user accounts

Demo users automatically reflect your customisations — when you rename a role, the matching demo account updates accordingly. This lets you test how different roles see the system.

**Goal:** Configure everything before adding real clients.

### Phase 3: Production

Begin real work with real clients.

- Add your first real client
- Real staff log in with their own accounts
- Demo data remains available for training new staff
- There's no "flip the switch" moment — you can run training and production side by side

**Goal:** Deliver services and track outcomes.

---

## Demo Mode and Training Accounts

KoNote includes permanent demo data for training and demonstrations. This is by design — it keeps your real client data safe.

### How It Works

| Account type | What they see |
|--------------|---------------|
| **Demo users** (demo-admin, demo-manager, demo-worker-1, etc.) | Demo clients only |
| **Real users** (your staff accounts) | Real clients only |

There's no toggle or mode switch. Your login determines what you see. Demo users can never see real clients, and real users can never see demo clients.

### Demo Clients

Fifteen sample clients across 5 programs, each with realistic data:

| Program | Clients | Worker |
|---------|---------|--------|
| Supported Employment | DEMO-001 to DEMO-003 | Casey (Lead Worker) |
| Housing Stability | DEMO-004 to DEMO-006 | Casey (Staff) |
| Youth Drop-In | DEMO-007 to DEMO-009 | Noor (Staff) |
| Newcomer Connections | DEMO-010 to DEMO-012 | Noor (Staff) |
| Community Kitchen | DEMO-013 to DEMO-015 | Both workers |

Three clients are cross-enrolled in Community Kitchen from other programs. Each has plans, progress notes, metrics, and events — enough data to see how charts and reports work.

### Demo Users

Six demo accounts for testing different permission levels:

| Username | Display Name | Role | Programs | Use for testing... |
|----------|-------------|------|----------|-------------------|
| demo-admin | Alex Admin | Administrator | System-wide | System configuration, user management |
| demo-manager | Morgan Manager | Program Manager | Employment, Housing, Kitchen | Program oversight — but **cannot** see Youth Drop-In or Newcomer Connections |
| demo-worker-1 | Casey Worker | Lead Worker | program_manager(Employment), staff(Housing, Kitchen) | Mixed roles — manages one program, regular worker in others |
| demo-worker-2 | Noor Worker | Direct Service | staff(Youth Drop-In, Newcomer, Kitchen) | Standard front-line worker, restricted to assigned clients |
| demo-executive | Eva Executive | Executive | All 5 programs | Dashboard and reports only — cannot see individual client details |
| demo-frontdesk | Dana Front Desk | Front Desk | All 5 programs | Limited client info, intake fields only |

Log in as different demo users to see how the permission system restricts what each role can see and do.

### Using Demo Accounts

**For administrators:** Use the Demo Account Directory (Settings → Demo Accounts) to quickly log in as any demo user and test how the system looks for different roles.

**For training:** New staff can log in as the demo user matching their role and practise without affecting real data.

**For demonstrations:** Show funders or board members the system without exposing real client information.

### Demo Data in Reports

Demo clients are **never included** in official reports, exports, or aggregate statistics. When you generate a funder report, only real client data appears.

---

## First Login

### Azure AD (Enterprise) Login

If your agency uses Microsoft Azure AD (Office 365):

1. Navigate to the KoNote Web login page.
2. Click **Login with Azure AD**.
3. Enter your work email and password.
4. KoNote Web automatically creates your account on first login.

Your account is created as a **Staff user** by default. An admin must promote you to **Admin** if you need to configure the system.

### Local (Username/Password) Login

If your instance uses local authentication:

1. Navigate to the login page.
2. Log in with your **username** and **password** (provided during setup).
3. After first login, an admin can create additional user accounts.

**First-time setup:** The initial admin account is created during deployment. Use those credentials to log in and proceed.

---

## Configure Instance Settings

Instance settings control your organisation's branding and behaviour.

### Steps

1. Click the **gear icon** (settings) in the top-right corner.
2. Select **Instance Settings**.
3. You'll see a form with these fields:

| Field | What it does | Example |
|-------|---|---|
| **Product Name** | Name shown in the header and page titles. | "Youth Housing Program — KoNote" |
| **Support Email** | Displayed in the footer or help pages so users know who to contact. | support@agency.ca |
| **Logo URL** | Web address of your organisation's logo image. | https://example.com/logo.png |
| **Date Format** | How dates appear throughout the system. Choose one: ISO (2026-02-02), US (02/02/2026), or other formats. | 2026-02-02 |
| **Session Timeout** | Number of minutes of inactivity before a user is logged out. (Prevents accidental access if someone leaves their computer.) | 30 minutes |

4. **Logo tip:** Host your logo on your website or a cloud service like OneDrive. Paste the full URL (starting with `https://`).
5. Click **Save**.

Changes apply immediately to all logged-in users on their next page reload.

---

## Customise Terminology

KoNote uses standard terms out of the box — "Client", "Program", "Plan", "Progress Note", etc. You can change these to match your organisation's vocabulary.

### Why customise?

- Call participants "Clients", "Members", "Individuals", "Participants", or "Service Users".
- Call services "Programs", "Services", "Initiatives", or "Streams".
- Call goals "Targets", "Objectives", "Milestones", etc.
- Use British or Canadian spelling ("Colour" vs. "Color").

### Steps

1. Click the **gear icon** → **Terminology**.
2. You'll see a table of all terms used in the system.
3. For each term:
   - The **default** column shows the original English term.
   - The **current** column is editable.
   - Check if it's marked "overridden" (you've customised it).
4. Click in a field to change the term. Type your preferred word.
5. To revert a term to the default, click **Reset** next to it.
6. Click **Save** at the bottom.

**Important:** Terminology appears throughout the app — in reports, templates, data entry forms, etc. Changes are immediate.

**Example:** If you change "Client" → "Participant", the system will say "New Participant" instead of "New Client".

---

## Enable/Disable Features

Not all agencies need all features. Toggle features on or off based on your workflow.

### Steps

1. Click the **gear icon** → **Features**.
2. You'll see a list of available features with **Enable** / **Disable** buttons.

| Feature | What it does |
|---------|---|
| **Programs** | Lets you create multiple programs and assign staff to them. Turn OFF if your agency has only one program. |
| **Custom Client Fields** | Lets you define extra data fields for each client (e.g., "Funding Source", "Referral Date"). Turn ON if you need agency-specific information. |
| **Metric Alerts** | Alerts staff when a client's progress metrics hit a threshold (e.g., "Crisis Alert"). Turn ON if you track measurable outcomes. |
| **Event Tracking** | Record discrete events in a client's timeline (Intake, Discharge, Crisis, etc.). Turn OFF if you only use progress notes. |
| **Funder Report Exports** | Generate reports for funders in specific formats. Turn ON if you report to external funders. |

3. Click **Enable** or **Disable** next to each feature.
4. Click **Save**.

**Tip:** You can enable/disable features later without losing data. Start with the essentials and add as your team requests them.

---

## Create Programs

A **program** is a distinct service line or intervention model your agency offers. Each client can belong to one or more programs.

### Examples

- Youth Housing
- Mental Health Support
- Family Counselling
- Job Training
- Emergency Services

### Steps

1. Click the **gear icon** → scroll down → **Programs**.
2. You'll see a list of existing programs (if any).
3. Click **+ New Program**.
4. Fill in:
   - **Program Name:** e.g., "Youth Housing"
   - **Description:** (optional) A few sentences explaining what this program does.
5. Click **Create**.
6. The new program appears in your program list.

### Assign Staff to Programs

After creating a program, you can assign staff members to it.

1. Click on the program name to view its detail page.
2. You'll see a list of staff assigned to this program.
3. Use the form to add staff:
   - Select a user from the dropdown.
   - Choose their **role**: "Coordinator" (manages the program) or "Staff" (delivers services).
4. Click **Add**.
5. To remove someone, click **Remove** next to their name.

---

## Create User Accounts

Users log in to KoNote with either Azure AD or local credentials. As an admin, you create staff accounts and assign them roles and programs.

### Steps

1. Click the **gear icon** → **User Management**.
2. You'll see a list of all users in your instance.
3. Click **+ New User**.
4. Fill in:
   - **Display Name:** The person's full name (shown in reports and timelines).
   - **Username:** (Local auth only) A unique login name like `jane.smith` or `jsmith`.
   - **Email:** Their work email.
   - **Password:** (Local auth only) A temporary password. Ask them to change it after first login.
   - **Is Admin?:** Check this box if they need to configure terminology, features, templates, etc.

5. Click **Create**.
6. The user can now log in.

### User Roles

- **Admin:** Can access all settings, create programs, manage templates, and create other users. Give this role to 1–3 key managers.
- **Staff:** Can enter data, write notes, and create plans for their assigned programs. Most of your team will be Staff.

### Deactivating Users

If someone leaves your organisation:

1. Go to **User Management**.
2. Click their name → **Edit**.
3. Uncheck **Is Active**.
4. Click **Save**.

They can no longer log in, but their historical data remains visible for reporting.

---

## Set Up Plan Templates

A **plan template** is a reusable blueprint for client outcome plans. Instead of building each client's plan from scratch, staff can apply a template, which copies sections and targets into the client's file.

### Key Concepts (Plain Language)

- **Section:** A broad category of goals. Examples: "Housing", "Employment", "Health", "Social Connection".
- **Target:** A specific outcome within a section. Example: Under "Housing", a target might be "Maintain stable housing for 3 months".
- **Template:** A saved collection of sections and targets that you can apply to multiple clients.

Think of templates like a form — it's faster than reinventing the wheel for each client.

### Steps to Create a Template

1. Click the **gear icon** → **Plan Templates**.
2. Click **+ New Template**.
3. Fill in:
   - **Template Name:** e.g., "Youth Housing Standard Plan"
   - **Description:** What this template is for.
4. Click **Create**.
5. You're now on the template detail page.

### Add Sections to a Template

1. On the template detail page, click **+ Add Section**.
2. Fill in:
   - **Section Name:** e.g., "Housing", "Employment", "Health"
   - **Program:** (optional) If this section applies only to one program, select it.
   - **Sort Order:** (optional) A number to control the order sections appear. (1, 2, 3, etc.)
3. Click **Create Section**.

### Add Targets to a Section

1. On the template detail page, find the section you just created.
2. Click **+ Add Target** within that section.
3. Fill in:
   - **Target Name:** e.g., "Maintain stable housing"
   - **Description:** (optional) More details. Example: "Client will maintain current housing placement for a minimum of 3 months with less than 2 unplanned absences per week."
   - **Sort Order:** (optional) Order within the section. (1, 2, 3, etc.)
4. Click **Create Target**.

### Example Template

**Name:** "Standard Youth Housing Plan"

**Sections & Targets:**
- **Housing**
  - Maintain stable housing for 3+ months
  - Develop independent living skills
- **Education/Employment**
  - Enroll in or maintain employment/education
  - Achieve 80% attendance rate
- **Health & Wellness**
  - Keep regular health appointments
  - Develop healthy coping strategies
- **Social Connection**
  - Build positive relationships with family or community
  - Participate in peer support activities

### Editing Templates

- Click the template name to view and edit it.
- Rename, add, or delete sections and targets as needed.
- Changes to a template do **not** affect plans already applied to clients — only future applications.

---

## Set Up Progress Note Templates

A **progress note** is a record of what happened during a client interaction: what was discussed, what they achieved, what needs attention next.

A **progress note template** provides structure — sections and prompts — so staff don't have to write from scratch.

### Steps

1. Click the **gear icon** → **Progress Note Templates**.
2. Click **+ New Template**.
3. Fill in:
   - **Template Name:** e.g., "Standard Progress Note", "Crisis Response Note"
   - **Description:** When staff should use this template.
4. Click **Create**.
5. You're now on the template detail page.

### Add Sections to a Note Template

Progress note sections are like "chapters" in your note. Common examples:

- **Summary:** What happened during the interaction?
- **Progress on Plan Targets:** Which targets did we work on?
- **Barriers & Successes:** What went well? What's in the way?
- **Next Steps:** What happens next?
- **Safety Concerns:** Are there any red flags?

### Steps to Add a Section

1. On the template detail page, scroll to the bottom.
2. Click **+ Add Section**.
3. Fill in:
   - **Section Name:** e.g., "Summary", "Safety Concerns"
   - **Section Label:** (optional) A subtitle or instruction for staff.
4. Click **Add**.
5. Repeat for each section you want.

### Example Note Template

**Name:** "Standard Session Notes"

**Sections:**
1. Summary — What topics were covered?
2. Progress on Goals — Which targets did we discuss?
3. Barriers Identified — What's preventing progress?
4. Successes — What's going well?
5. Next Steps — What will we do next?

---

## Configure Custom Fields

Custom fields let you capture information specific to your organisation that isn't in the standard client form.

### Examples

- Funding Source (Government, Private Donation, Foundation)
- Referral Date
- Cultural/Spiritual Needs
- Special Dietary Requirements
- Driver's License Status
- Language(s) Spoken

### Key Concepts

- **Field Group:** A logical grouping of related fields. Example: "Demographic Info" or "Funding Details".
- **Field Type:** What kind of input. Examples: Text, Number, Date, Dropdown (multiple choice), Checkbox.
- **Required:** Whether staff must fill in this field.
- **Sensitive:** Whether this field contains private health or financial information. (Marked in the system for audit purposes.)

### Steps to Create a Field Group

1. Click the **gear icon** → **Custom Client Fields**.
2. Click **+ New Field Group**.
3. Fill in:
   - **Group Title:** e.g., "Funding & Referral"
   - **Description:** (optional)
4. Click **Create**.

### Steps to Add a Custom Field

1. On the **Custom Client Fields** page, click **+ New Custom Field**.
2. Fill in:
   - **Field Name:** e.g., "Funding Source"
   - **Field Type:** Choose from dropdown options (Text, Number, Date, etc.)
   - **Field Group:** Select the group this field belongs to.
   - **Required?:** Check if staff must enter a value.
   - **Sensitive?:** Check if this contains private information (health, financial, etc.).
   - **Help Text:** (optional) Instructions for staff.
   - **Choices** (if type is Dropdown): Enter comma-separated options. E.g., "Government, Private, Foundation"
3. Click **Create**.

### Example Field Configuration

**Group:** "Funding & Referral"

**Fields:**
1. **Funding Source** — Dropdown — Choices: "Government", "Foundation", "Private", "Self-funded" — Required
2. **Referral Date** — Date — Not required
3. **Referral Agency** — Text — Not required

---

## Review Event Types

An **event** is a discrete occurrence in a client's timeline: intake, discharge, crisis, hospital visit, etc.

Event types are pre-configured during setup. You can browse them to understand what's available.

### Steps

1. Click the **gear icon** → **Event Types**.
2. You'll see a list of available event types:
   - **Intake:** Client starts in the program.
   - **Discharge:** Client leaves the program.
   - **Crisis:** A significant incident or safety concern.
   - **Hospital Visit:** Client received hospital care.
   - (Others as configured during deployment.)

3. Each type shows:
   - **Name:** The event label.
   - **Status:** Active or Inactive.

### Enable/Disable Event Types

- If an event type is marked **Inactive**, staff won't see it when recording events.
- Inactive events are hidden but not deleted — historical data is preserved.

**You don't need to configure event types right now.** Staff can create events with these pre-set types when working with clients.

---

## Next Steps: Start Adding Clients

Congratulations! Your system is configured. Now you're ready to add clients and create their outcome plans.

### Quick Checklist

- [ ] Logged in successfully
- [ ] Instance name, logo, and support email set
- [ ] Terminology customised (if needed)
- [ ] Features enabled/disabled to match your workflow
- [ ] Programs created and staff assigned
- [ ] User accounts created for all staff
- [ ] Plan templates created
- [ ] Progress note templates created
- [ ] Custom fields configured (if needed)
- [ ] Event types reviewed

### First Client Setup

When you're ready to add your first client:

1. Click **New Client** in the main menu.
2. Enter their record ID and basic information.
3. Enroll them in a program.
4. Apply a plan template to create their initial outcome plan.
5. Configure their custom field values (housing, funding, etc.).
6. Staff can now start writing progress notes!

### A Note on Client Search and Encryption

KoNote encrypts all personally identifiable information (PII) — names, contact details, etc. — using Fernet (AES) encryption. This keeps client data secure, but it means the database cannot search encrypted fields directly using SQL.

Instead, when you search for a client, KoNote loads accessible client records into memory and filters them there. **This works well for agencies with up to approximately 2,000 clients.** Most small and mid-sized nonprofits will never notice a difference.

If your agency expects to serve significantly more than 2,000 clients, a search hash optimisation can be added to improve performance. This is tracked as **PERF1** in the project roadmap.

---

## Troubleshooting

### Q: I see a login error.
**A:** If using Azure AD, check that your email is registered with your Microsoft tenant. If using local auth, confirm your username and password with an admin.

### Q: Can I change terminology later?
**A:** Yes! Changes to terminology apply immediately. Existing notes and plans will show the new terms.

### Q: What if I delete a program?
**A:** You can't delete programs with active clients. Deactivate it instead: click the program, then **Status: Inactive**. Historical data is preserved.

### Q: Do staff need to use all the custom fields I create?
**A:** No. If a custom field is not marked **Required**, staff can leave it blank. Required fields must be filled in before saving.

### Q: I created a plan template. Does it affect existing client plans?
**A:** No. Existing plans are unchanged. Templates only apply to new plans going forward.

---

## Support & Questions

- **Documentation:** Refer back to this guide or visit the in-app help pages.
- **Bug Reports:** If something isn't working, contact your deployment support team.
- **Feature Requests:** Suggest new features to your administrator.

---

**Version 1.1** — KoNote Web
Last updated: 2026-02-05
