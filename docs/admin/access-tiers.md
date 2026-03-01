# Access Tiers — KoNote's 3-Tier Permission Model

> **What you'll need:** Administrator access to KoNote.
> **Related:** [DV-Safe Mode & GATED Access](dv-safe-mode-and-gated-access.md) · [Per-Field Front Desk Access](per-field-front-desk-access.md) · [Users & Roles](users-and-roles.md)

---

## Overview

Not all agencies have the same privacy needs. A small after-school program and a clinical counselling agency work with very different levels of data sensitivity.

KoNote's **access tier** system lets your agency choose the right level of access control for your situation. Think of it as a dial — you can turn up the protections as your needs require, without changing how your team works day-to-day.

There are three tiers:

| Tier | Name | Best For |
|---|---|---|
| **Tier 1** | Open Access | Small teams, non-sensitive data |
| **Tier 2** | Role-Based | Agencies with a dedicated front desk and distinct staff roles |
| **Tier 3** | Clinical Safeguards | Clinical programs, DV agencies, and organisations handling sensitive data |

Every tier includes the same baseline role permissions (Front Desk, Direct Service, Program Manager, Executive, Administrator). The tiers add features **on top of** that baseline.

---

## Comparison: What Each Tier Enables

| Feature | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| **Role-based permissions** (who can see what by role) | ✓ | ✓ | ✓ |
| **Front desk limited by default** (can't see clinical notes, plans, or metrics) | ✓ | ✓ | ✓ |
| **Executive role** (aggregate data only, no individual records) | ✓ | ✓ | ✓ |
| **Client access blocks** (block specific staff from specific participants) | ✓ | ✓ | ✓ |
| **Per-field front desk access** (choose which fields front desk can see/edit) | — | ✓ | ✓ |
| **DV-Safe Mode** (hide sensitive fields for flagged participants) | — | ✓ | ✓ |
| **Custom field DV-sensitivity** (mark fields as DV-sensitive) | — | ✓ | ✓ |
| **Tighter email defaults** (email view-only for front desk) | — | — | ✓ |
| **GATED clinical access** (managers must justify viewing clinical notes) | — | — | ✓ |
| **Time-limited access grants** (access expires automatically) | — | — | ✓ |
| **Configurable grant reasons and durations** | — | — | ✓ |

---

## Tier 1 — Open Access

### What Each Role Can Do

Tier 1 provides straightforward role-based access. Everyone on the team sees what they need for their role, and the system keeps clinical data away from people who don't need it.

| Role | What They Can Do |
|---|---|
| **Front Desk** | See participant names, contact info, and safety information. Check people in and out. Create new participant files. Leave messages for case workers. Cannot see clinical notes, plans, metrics, or group rosters. |
| **Direct Service** | Everything Front Desk can do, plus: view and write clinical notes, manage plans, see metrics, manage group rosters and sessions, record events, log communications, manage meetings. All scoped to their assigned program(s). |
| **Program Manager** | Everything Direct Service can do, plus: view all data across their program(s), generate reports, manage program configuration, manage templates, review alerts, manage erasure requests, audit logs for own program(s). Cannot delete clinical notes. |
| **Executive** | Aggregate data only — org-wide attendance reports, aggregate metrics, outcome insights, and funder reports. No individual participant records, names, or clinical data. |
| **Administrator** | System configuration: manage users, programs, settings, terminology, and features. Does **not** automatically have access to participant data — that requires a separate program role. |

### Front Desk Access at Tier 1

At Tier 1, Front Desk uses safe defaults that cannot be changed:

| Field | Default Access |
|---|---|
| First name, last name, display name, record ID, status | Always visible |
| Phone number | View and edit |
| Email address | View and edit |
| Preferred name | View only |
| Date of birth | Hidden |
| Custom fields | Hidden (unless individually set to view/edit) |

### Who Should Use Tier 1?

- Small agencies where everyone on the team knows each other
- Programs with non-sensitive data (recreation, education, after-school)
- Agencies where there is no dedicated front desk — everyone wears multiple hats
- Agencies just getting started with KoNote who want simplicity first

---

## Tier 2 — Role-Based

### What's Added

Tier 2 includes everything in Tier 1, plus:

- **Per-field front desk access controls** — administrators can choose exactly which fields Front Desk staff can see and edit. See the [Per-Field Front Desk Access](per-field-front-desk-access.md) guide.
- **DV-Safe Mode** — sensitive fields can be hidden from Front Desk for participants who have a DV safety flag. See the [DV-Safe Mode](dv-safe-mode-and-gated-access.md#dv-safe-mode) guide.
- **Custom field DV-sensitivity** — each custom field can be marked as DV-sensitive, so it's automatically hidden for flagged participants.

### How Roles Change at Tier 2

The roles themselves don't change — the same five roles work the same way. What changes is that administrators can **fine-tune** what Front Desk sees:

- Phone number: choose Hidden, View only, or View and edit
- Email address: choose Hidden, View only, or View and edit
- Preferred name: choose Hidden, View only, or View and edit
- Date of birth: choose Hidden, View only, or View and edit
- Each custom field: choose Hidden, View only, or View and edit

### Confidential Programs

At Tier 2, you can also designate programs as **confidential**. Confidential programs have additional restrictions on how data flows between programs — for example, clinical notes from a confidential program won't appear in cross-program views unless consent has been given.

### Who Should Use Tier 2?

- Agencies with a dedicated front desk / reception area
- Organisations where front desk and clinical staff have clearly different roles
- Agencies serving populations where some data is sensitive (e.g., health information, employment status)
- Agencies that want DV safety protections

---

## Tier 3 — Clinical Safeguards

### What's Added

Tier 3 includes everything in Tier 2, plus:

- **GATED clinical access** — Program Managers must document a reason before viewing individual clinical notes, plans, and related records. See the [GATED Clinical Access](dv-safe-mode-and-gated-access.md#gated-clinical-access) guide.
- **Time-limited access grants** — when a manager requests clinical access, it's granted for a set number of days (default: 7, maximum: 30) and expires automatically.
- **Configurable grant reasons** — administrators set the list of reasons managers choose from when requesting access (e.g., "Case supervision", "Safety concern follow-up").
- **Tighter front desk defaults** — email is view-only by default instead of editable, because email addresses can reveal a participant's location.
- **Admin grant review** — administrators can view all active and expired grants, providing accountability and oversight.

### How Roles Change at Tier 3

Program Managers experience the biggest change at Tier 3. Instead of having automatic access to all clinical data in their program(s), they must:

1. Click on a clinical record (note, plan, etc.)
2. Be redirected to a justification form
3. Select a reason, write a brief explanation, and choose a duration
4. Submit the form to receive time-limited access

This happens the first time they try to view gated content. Once they have an active grant, they can access clinical data normally until the grant expires.

**Direct Service** staff are **not** affected by GATED access — they continue to have full access to clinical data in their assigned program(s).

**Front Desk** and **Executive** roles are also unaffected, since they don't have clinical data access in any tier.

### The Gated Permissions

At Tier 3, the following permissions require an access grant for Program Managers:

| What's Gated | What This Means |
|---|---|
| View clinical data | Individual participant clinical information |
| View progress notes | Reading notes written by Direct Service staff |
| View participant plans | Goals, targets, and plan details |

### Who Should Use Tier 3?

- Clinical counselling agencies
- Agencies serving people experiencing domestic violence (DV)
- Organisations handling mental health, addiction, or trauma data
- Agencies where funders or regulators require documented access justification
- Organisations that want the strongest privacy protections KoNote offers

---

## How to Change Your Tier

Changing your access tier is a settings change — it takes effect immediately and doesn't require a system restart.

1. Go to **Admin → Settings**
2. Find the **Access Tier** setting
3. Select the tier you want:
   - **Tier 1 — Open Access** (previously called "Role-based only" in setup)
   - **Tier 2 — Role-Based** (previously called "Role-based + field-level access" in setup)
   - **Tier 3 — Clinical Safeguards** (previously called "Role-based + field-level + gated grants" in setup)
4. Click **Save**

### What Happens When You Change Tiers

**Moving up** (e.g., Tier 1 → Tier 2, or Tier 2 → Tier 3):

- New features become available immediately
- Existing data and access is preserved
- You may want to configure the new features (field access, DV flags, grant reasons) right away

**Moving down** (e.g., Tier 3 → Tier 2, or Tier 2 → Tier 1):

- Higher-tier features are deactivated immediately
- Existing access grants are preserved in the database (for audit purposes) but are no longer enforced
- Field access configurations are preserved but may not apply if you drop below Tier 2
- DV safety flags on participants are preserved but not enforced at Tier 1

> **Good to know:** You can move between tiers freely. There's no lock-in. If you try Tier 3 and find it's more than your agency needs, you can move back to Tier 2 without losing any data.

---

## Recommendations: Which Tier for Which Agency?

| Agency Type | Recommended Tier | Why |
|---|---|---|
| After-school or recreation programs | Tier 1 | Simple, low-sensitivity data |
| Employment services | Tier 1 or Tier 2 | Tier 2 if you have a front desk and want to control what they see |
| Community support programs | Tier 2 | Distinct front desk and staff roles, some sensitive data |
| Settlement / newcomer services | Tier 2 | Some DV risk may warrant DV-safe mode |
| Clinical counselling | Tier 3 | Clinical notes require access justification |
| Addiction services | Tier 3 | Highly sensitive data with regulatory requirements |
| Women's shelters / DV agencies | Tier 3 | Maximum protections for at-risk participants |
| Multi-program agencies (mix of sensitive and non-sensitive) | Tier 2 or Tier 3 | Tier 3 if any program involves clinical or DV data |

> **When in doubt, start with Tier 2.** It gives you fine-grained control without the overhead of access grants. You can always move to Tier 3 later if you need it.

---

## Frequently Asked Questions

**Can I use different tiers for different programs?**
No — the access tier is a system-wide setting that applies to all programs. If any of your programs handle sensitive clinical data, choose the tier that covers your most sensitive program.

**Does changing tiers affect existing data?**
No. Your participant records, notes, plans, and other data are unchanged. Only the access control features change.

**Will my users notice when I change tiers?**
- Moving from Tier 1 to Tier 2: Front Desk staff may notice fields appearing or disappearing, depending on how you configure field access
- Moving to Tier 3: Program Managers will see the justification form the first time they try to view clinical notes
- Moving down: users will notice fewer restrictions (e.g., no more justification forms)

**Is there a Tier 4?**
No. Three tiers cover the range of needs from low-sensitivity to clinical-grade protections. If you need something beyond Tier 3, contact KoNote support to discuss your requirements.

**Who can change the tier?**
Only administrators can change the access tier. The setting is in the admin settings area and requires admin privileges.
