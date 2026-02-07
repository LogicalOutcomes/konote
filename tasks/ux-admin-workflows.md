# UX Work-Through: Administrator Workflows (UX-ADMIN1)

## Purpose

Walk through every administrator workflow as if you're a new agency admin setting up KoNote2 for the first time. For each workflow, ask:

1. **Can I find it?** Is it obvious where to go?
2. **Do the steps make sense?** Is the order logical? Are labels clear?
3. **Does it actually work?** Does saving succeed? Do changes appear where expected?
4. **What happens when I make a mistake?** Are error messages helpful?
5. **Can I undo or fix things?** Can I edit/delete what I just created?

---

## Scenarios

### 1. First Login as Admin — Finding Your Way

**Scenario:** You just logged in as an admin for the first time. You need to configure the agency.

- [ ] Is the admin dashboard (`/admin/settings/`) easy to find from the main nav?
- [ ] Does the dashboard clearly show all configuration areas?
- [ ] Is there a logical "getting started" order suggested?
- [ ] Are the links/buttons labelled in plain language (not developer jargon)?

---

### 2. Setting Up Terminology

**Scenario:** Your agency calls participants "members" and programs "services."

- [ ] Go to Settings > Terminology
- [ ] Change "Client" to "Member" — does the label explain what this affects?
- [ ] Change "Program" to "Service" — does it preview where this word appears?
- [ ] Save — does a success message confirm the change?
- [ ] Navigate to another page — is the new terminology used everywhere?
- [ ] Reset one term to default — is the reset button obvious? Does it ask for confirmation?
- [ ] Try both English and French terminology — is the bilingual setup clear?

---

### 3. Enabling Features

**Scenario:** Your agency wants to turn on custom fields and events, but not reports yet.

- [ ] Go to Settings > Features
- [ ] Are the feature names self-explanatory? (e.g., does "Custom Fields" explain what it enables?)
- [ ] Toggle features on/off — does the page clearly show current state (on vs off)?
- [ ] Save — does the nav immediately reflect enabled/disabled features?
- [ ] Try disabling a feature that has existing data — does it warn you?

---

### 4. Creating a Program

**Scenario:** Your agency runs an "Employment Readiness" program for individuals.

- [ ] Find the Programs page from the nav or admin dashboard
- [ ] Click "Create Program" — is the button easy to find?
- [ ] Fill in name, description — are field labels clear?
- [ ] Set service model (individual/group/both) — is the choice explained?
- [ ] Set confidential flag — does it explain what confidential means and its consequences?
- [ ] Save — does it redirect somewhere logical? Success message?
- [ ] View the program detail — can you see who's assigned?
- [ ] Assign a staff member with a role — is the role picker intuitive?
- [ ] Remove a staff member — does it ask for confirmation?
- [ ] Edit the program — can you find the edit button easily?

---

### 5. Creating Metrics

**Scenario:** You want to track "Housing Stability" as a 1-5 scale metric.

- [ ] Find the Metric Library from admin dashboard or nav
- [ ] Browse existing metrics — are they grouped logically by category?
- [ ] Click "Create Metric" — is the form clear about what each field means?
- [ ] Set name, category, description — are there helpful hints or examples?
- [ ] Save — does the new metric appear in the library?
- [ ] Enable/disable a metric — is the toggle obvious? Does it explain what disabling does?
- [ ] Edit a metric — can you change it after creation?
- [ ] Try the CSV import — is the expected format documented? What happens with bad data?

---

### 6. Creating Plan Templates

**Scenario:** You want a standard intake plan template with 3 sections and specific targets.

- [ ] Find Plan Templates from admin dashboard
- [ ] Click "Create Template" — name and description fields clear?
- [ ] Save the template — then add sections
- [ ] Add Section 1 (e.g., "Housing Goals") — is the section form intuitive?
- [ ] Add a target to that section — does it link to available metrics?
- [ ] Add Section 2 and Section 3 with their own targets
- [ ] View the completed template — does it show the full structure clearly?
- [ ] Reorder sections — can you change the order? Is it obvious how?
- [ ] Edit a target — can you find and modify it easily?
- [ ] Delete a section — does it warn about losing targets within it?
- [ ] Apply the template to a client — is the workflow clear?

---

### 7. Creating Note Templates

**Scenario:** You want staff to use a structured progress note with specific sections.

- [ ] Find Note Templates from admin settings
- [ ] Click "Create Template" — is the formset for sections understandable?
- [ ] Add template name and several sections (e.g., "Session Summary", "Goals Discussed", "Next Steps")
- [ ] Save — does it show the complete template?
- [ ] Edit the template — can you add/remove/reorder sections?
- [ ] When staff write a note, does the template appear as an option?

---

### 8. Creating Event Types

**Scenario:** You want to track "Court Date", "Hospital Visit", and "Case Conference."

- [ ] Find Event Types management
- [ ] Create a new event type — name and colour picker clear?
- [ ] Save — does it appear in the list?
- [ ] Create two more event types
- [ ] Edit one — can you change the colour?
- [ ] When staff create an event, do these types appear in the dropdown?

---

### 9. Setting Up Custom Client Fields

**Scenario:** You need intake fields for "Referral Source", "Housing Status", and "Income Level."

- [ ] Find Custom Fields management
- [ ] Create a field group (e.g., "Intake Information") — is the group concept explained?
- [ ] Create a dropdown field "Referral Source" with options — is the options entry clear?
- [ ] Create a text field "Housing Status"
- [ ] Create a number field "Income Level" — can you set validation (min/max)?
- [ ] Set encryption on sensitive fields — is it clear which fields need encrypting?
- [ ] View the fields page — does it show groups and fields in a logical layout?
- [ ] Edit a field — can you add options to an existing dropdown?
- [ ] When viewing a client, do these fields appear on the intake/profile form?

---

### 10. Managing Users

**Scenario:** A new staff member is joining and needs access.

- [ ] Find User Management from admin dashboard
- [ ] View the user list — is it clear who's active, who's admin, who's deactivated?
- [ ] Create a new user — are all fields clear? Is the role/program assignment intuitive?
- [ ] Save — does the user appear in the list?
- [ ] Edit the user — can you change their role or program assignments?
- [ ] Deactivate the user — does it explain what happens (can't log in, data preserved)?
- [ ] Try the invite link system — create an invite, copy the link, understand the flow

---

### 11. Setting Up Registration Links

**Scenario:** You want a public registration form embedded on your website.

- [ ] Find Registration Links management
- [ ] Create a registration link — program assignment, custom fields selection, slug
- [ ] Is it clear which fields will appear on the public form?
- [ ] Get the embed code — is the iframe snippet easy to copy?
- [ ] Review a pending submission — is duplicate detection visible?
- [ ] Approve a submission — does it create a client record?
- [ ] Reject a submission — can you provide a reason?
- [ ] Waitlist a submission — is the status clearly tracked?

---

### 12. Instance Settings

**Scenario:** You need to set the agency name and configure retention periods.

- [ ] Find Instance Settings
- [ ] Set agency name — where does it appear in the app?
- [ ] Set retention periods — are the options explained (what happens when data ages out)?
- [ ] Save — is the confirmation clear?

---

### 13. Reviewing Audit Logs

**Scenario:** You need to check who accessed a specific client's file last week.

- [ ] Find Audit Logs from admin dashboard
- [ ] Can you filter by user? By date range? By action type?
- [ ] Is the log readable — timestamps, usernames, actions in plain language?
- [ ] Export to CSV — does it include the filtered results or everything?
- [ ] View program-specific audit log — is it scoped correctly?

---

## Cross-Cutting Concerns

### Navigation & Discoverability
- [ ] Can every admin feature be reached from the admin dashboard?
- [ ] Is the admin dashboard linked prominently in the nav?
- [ ] Are breadcrumbs present so you know where you are?
- [ ] Do links use the agency's custom terminology (not defaults)?

### Error Handling
- [ ] What happens if you submit a form with missing required fields?
- [ ] What happens if you try to create a duplicate (same name)?
- [ ] Are error messages next to the field that has the problem?
- [ ] Do errors preserve what you already typed (no lost work)?

### Accessibility
- [ ] Can all admin workflows be completed with keyboard only?
- [ ] Do form fields have proper labels (not just placeholders)?
- [ ] Are success/error messages announced to screen readers (aria-live)?
- [ ] Do colour pickers have text alternatives?

### Bilingual
- [ ] Do all admin pages work in French?
- [ ] Are form labels and help text translated?
- [ ] Can you switch languages mid-workflow without losing data?

---

## How to Run This Review

1. **Manual walkthrough** — Log in as a demo admin and go through each scenario above, checking the boxes
2. **Fresh eyes test** — Have someone unfamiliar with KoNote2 try the first 5 scenarios and note where they get stuck
3. **Record issues** — For each problem found, note: what you tried, what happened, what you expected
4. **Prioritise fixes** — Sort issues by: (a) blocks basic setup, (b) confusing but workaround exists, (c) minor polish
