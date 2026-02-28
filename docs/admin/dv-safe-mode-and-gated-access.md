# DV-Safe Mode & GATED Clinical Access

> **What you'll need:** Administrator access to KoNote.
> **Related:** [Access Tiers](access-tiers.md) · [Per-Field Front Desk Access](per-field-front-desk-access.md) · [Users & Roles](users-and-roles.md)

---

## Overview

Some agencies serve participants who are at risk of violence from a partner, family member, or other person. In these situations, even basic contact information — a phone number, an address, an emergency contact — can put someone in danger if the wrong person sees it.

KoNote includes two safety features designed to protect participants in these situations:

1. **DV-Safe Mode** — hides sensitive contact fields from Front Desk staff for specific participants who have been flagged as needing protection.
2. **GATED Clinical Access** — requires Program Managers to document a reason before viewing clinical notes, with time-limited access that expires automatically. This is only active at Tier 3.

Both features are designed to **fail closed**: if anything goes wrong or a setting can't be determined, KoNote hides the information rather than showing it. Safety comes first.

---

## DV-Safe Mode

### What It Does

When DV-Safe Mode is enabled on a participant's file, certain sensitive fields are automatically hidden from Front Desk staff. This protects participants whose contact information could be used to locate or harm them.

The fields that are hidden include any custom field marked as **DV-sensitive** by an administrator (for example, address, emergency contact, employer). These fields are hidden on screen — Front Desk staff simply don't see them.

Staff in other roles (Direct Service, Program Manager) continue to see all fields as usual.

### Turning It On

DV-Safe Mode works at the **participant level** — you set a DV safety flag on individual participant files, not as a system-wide switch.

DV-Safe Mode is available at **Tier 2** and **Tier 3**. (At Tier 1, the system uses basic role-based access without DV-specific protections.)

### Which Fields Are DV-Sensitive?

As an administrator, you control which custom fields are treated as DV-sensitive. When creating or editing a custom field in KoNote, you'll see a checkbox labelled **"DV-sensitive"**. When this is checked:

- The field behaves normally for Direct Service and Program Manager roles
- If a participant has a DV safety flag, the field is **completely hidden** from Front Desk staff — even if the field would otherwise be visible to them

Common fields to mark as DV-sensitive include:

- Home address
- Emergency contact name and phone
- Employer or workplace
- Alternate phone numbers
- Any field that could reveal a participant's location

> **Important:** DV-Safe Mode overrides normal field access settings. Even if you've configured a field to be visible to Front Desk, the DV safety flag will hide it for that participant.

### Setting the DV Flag on a Participant

Anyone with a Direct Service or Program Manager role can set the DV safety flag on a participant's file. Look for the **"DV-safe"** toggle on the participant's profile.

When this flag is turned on:

- All DV-sensitive custom fields are hidden from Front Desk staff for this participant
- The flag is visible to Direct Service and Program Manager staff so they know protections are in place
- An audit log entry is created

### Removing the DV Flag (Two-Person Workflow)

Removing a DV safety flag is deliberately harder than setting it. This uses a **two-person rule** to prevent accidental or coerced removal:

1. **Step 1 — Request removal.** A staff member (Direct Service or Program Manager) submits a removal request. They must provide a written reason explaining why the DV safety flag should be removed (for example, "Participant has confirmed the safety concern is resolved and requested the flag be removed").

2. **Step 2 — A different person reviews.** A Program Manager (who is **not** the person who submitted the request) reviews the request and either approves or rejects it. They can add a review note explaining their decision.

3. **If approved:** The DV safety flag is removed from the participant's file, and all DV-sensitive fields become visible to Front Desk again.

4. **If rejected:** The flag stays in place. The request is marked as rejected and a new request can be submitted later if circumstances change.

> **Why two people?** In domestic violence situations, an abuser may pressure a staff member into removing safety protections. Requiring a second person to review and approve the change adds an important safeguard.

### What Happens When Someone Is Denied Access

When a Front Desk staff member views a participant who has a DV safety flag:

- They see the participant's name, record ID, and status (these are always visible)
- DV-sensitive fields simply don't appear on the page — there is no error message or alert drawing attention to the flag
- The experience is designed to be discreet: the Front Desk user sees fewer fields, but the interface doesn't announce *why*

### Fail-Closed Behaviour

KoNote uses a **fail-closed** approach for DV safety. This means:

- If the system can't determine whether a participant has a DV flag (for example, due to a database error), it hides the sensitive fields by default
- If a staff member's access permissions can't be verified, they are denied access rather than granted it
- This "safe by default" design ensures that a technical glitch never accidentally reveals protected information

---

## GATED Clinical Access

### When It's Active (Tier 3 Only)

GATED clinical access is only enforced when your agency is using **Tier 3: Clinical Safeguards**. At Tier 1 and Tier 2, Program Managers can view clinical notes without needing to document a reason.

If you're not sure which tier your agency uses, check **Admin → Settings → Access Tier**. See the [Access Tiers](access-tiers.md) guide for details on what each tier provides.

### What It Does

At Tier 3, certain clinical data is protected behind a **justification gate**. When a Program Manager tries to view:

- Progress notes
- Participant plans
- Other clinical records

...they are redirected to a short form asking them to document **why** they need access. This creates an accountability record — the access is granted, but the reason is logged.

This design reflects a principle called **"need-to-know" access**: managers should only view individual clinical records when they have a specific reason to do so, not routinely.

### How a Staff Member Requests Access

When a Program Manager clicks on a clinical record that is protected by a gate, KoNote automatically redirects them to the **Access Request** form. The form asks for:

1. **Reason for access** — choose from a dropdown of pre-configured reasons (for example: "Case supervision", "Quality assurance review", "Safety concern follow-up")
2. **Brief explanation** — a free-text field where they describe what they need to see and why
3. **How long do you need access?** — choose a duration (1 day, 3 days, 7 days, 14 days, or 30 days)

After submitting the form, the manager is immediately redirected to the page they originally wanted to see. There is no separate approval step — the gate creates an accountability record, not a waiting queue.

### Grant Scope

Access grants can cover:

- **An entire program** — the manager can view all clinical records in that program for the duration of the grant
- **A specific participant** — the manager can view that participant's clinical records only

The scope is determined automatically based on what the manager was trying to access when the gate was triggered.

### Grant Expiry and Renewal

All access grants are **time-limited**. The default duration is 7 days, and the maximum is 30 days — but administrators can configure both of these values.

When a grant expires:

- The manager's access to the gated clinical data is automatically revoked
- No action is required by anyone — it happens automatically
- If the manager needs access again, they submit a new request with a fresh justification

Managers can also **revoke their own grant early** from their access grants page if they no longer need it.

### Configuring Reasons and Durations

As an administrator, you can customise the GATED access system:

**Managing reasons:**

1. Go to **Admin → Access Grant Reasons**
2. You'll see the list of reasons that appear in the dropdown when staff request access
3. To add a new reason, type the label (and optionally a French translation) and click **Add**
4. To deactivate a reason you no longer want available, click the toggle next to it — deactivated reasons won't appear in the dropdown, but existing grants that used them are preserved
5. Five default reasons are created when KoNote is first set up

**Configuring default and maximum durations:**

Default and maximum grant durations are managed as instance settings:

- **Default duration** (`access_grant_default_days`): How many days a grant lasts by default. The default is **7 days**.
- **Maximum duration** (`access_grant_max_days`): The longest grant any user can request. The default is **30 days**.

The duration options shown to staff (1, 3, 7, 14, or 30 days) are automatically filtered so that no option exceeds the maximum you've set.

### How Admins Review Active Grants

Administrators can see all access grants across all users and programs:

1. Go to **Admin → Access Grants**
2. You'll see a list of all grants — active and expired — with who requested them, the program, the reason, the justification text, when they were granted, and when they expire
3. This page is only available at Tier 3

Individual users can also see their own grants at **My Access Grants**, where they can review their active grants and revoke them early if needed.

### Audit Trail

Every access grant is recorded in the audit log with:

- Who requested the access
- What program (and optionally, which participant)
- The selected reason and written justification
- The duration and expiry date
- When the grant was revoked (if applicable)

This audit trail supports privacy compliance reviews, clinical supervision, and funder accountability.

---

## Frequently Asked Questions

**Can I use DV-Safe Mode without Tier 3?**
Yes. DV-Safe Mode is available at Tier 2 and above. You don't need to enable GATED clinical access to use DV protections.

**Do Direct Service staff see DV-flagged participants differently?**
Direct Service staff see all fields (including DV-sensitive ones) regardless of the DV flag. The flag only affects what Front Desk staff can see. Direct Service staff *can* see that the DV flag is set, so they know protections are in place.

**What if Front Desk needs to reach a participant urgently?**
If Front Desk staff need contact information that's hidden by a DV flag, they should ask a Direct Service or Program Manager to provide it. This ensures there's always a clinical judgement involved before sharing protected information.

**What if I set Tier 3 and then switch back to Tier 2?**
GATED access is immediately relaxed — Program Managers can view clinical notes without justification. Existing access grant records are preserved for audit purposes but are no longer enforced. You can switch back to Tier 3 at any time to re-enable the gates.

**Can a manager bypass the gate in an emergency?**
No — the gate cannot be bypassed. However, submitting the justification form takes less than a minute, and access is granted immediately after submission. There is no approval wait time.

**Are access grants logged even at Tier 1 and Tier 2?**
No. At Tier 1 and Tier 2, GATED permissions are automatically relaxed to "allow", so no grant is needed and none is logged. The audit trail for grants only exists at Tier 3.

**Who can set the DV safety flag?**
Any staff member with a Direct Service or Program Manager role can set the DV safety flag on a participant's file. Front Desk staff cannot set or see the flag.

**What if the two reviewers disagree on removing a DV flag?**
If the reviewing Program Manager rejects the removal request, the flag stays in place. A new request can be submitted later — perhaps with additional context or by a different staff member. The rejected request is preserved in the audit trail.

**Does the system hide the fact that a participant has a DV flag from Front Desk?**
Yes. Front Desk staff simply see fewer fields — they don't see a message saying "fields hidden due to DV flag" or anything similar. The design is intentionally discreet.
