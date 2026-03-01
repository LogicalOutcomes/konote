# Per-Field Front Desk Access Controls

> **What you'll need:** Administrator access to KoNote. Your agency must be using **Tier 2** or **Tier 3**.
> **Related:** [Access Tiers](access-tiers.md) · [DV-Safe Mode & GATED Access](dv-safe-mode-and-gated-access.md) · [Users & Roles](users-and-roles.md)

---

## Overview

Not every agency wants Front Desk staff to see the same information. A drop-in centre might want reception to see phone numbers and email so they can follow up with participants. A clinical program might want to restrict everything except names.

KoNote lets administrators control **exactly which fields** Front Desk staff can see and edit for each participant. This is called **per-field access control**.

This feature is available at **Tier 2** and **Tier 3**. At Tier 1, safe defaults apply automatically and cannot be customised.

---

## How It Works

Every field on a participant's profile can have one of three access levels for the Front Desk role:

| Access Level | What It Means |
|---|---|
| **Hidden** | Front Desk staff cannot see this field at all. It doesn't appear on screen. |
| **View only** | Front Desk staff can see the field's value but cannot change it. |
| **View and edit** | Front Desk staff can both see and change the field's value. |

There are two types of fields, and they are configured in different places:

1. **Core fields** — built-in fields like phone, email, preferred name, and date of birth. These are configured on the **Field Access** admin page.
2. **Custom fields** — fields your agency has added (like address, emergency contact, employer). Each custom field has its own Front Desk access setting, also configured on the **Field Access** admin page.

---

## Default Settings (Out of the Box)

Before any administrator changes, KoNote uses safe defaults that balance usability with privacy:

### Always-Visible Fields

These fields are **always visible** to Front Desk staff and cannot be hidden. Front Desk needs them to identify and check in participants:

- First name
- Last name
- Display name
- Record ID
- Status (active, discharged, etc.)

### Configurable Core Fields — Defaults

| Field | Tier 1–2 Default | Tier 3 Default |
|---|---|---|
| Phone number | View and edit | View and edit |
| Email address | View and edit | View only |
| Preferred name | View only | View only |
| Date of birth | Hidden | Hidden |

> **Why is email view-only at Tier 3?** Agencies using Tier 3 (Clinical Safeguards) typically serve higher-risk populations. Email addresses can reveal a participant's location or be used for unwanted contact, so the default is more restrictive.

### Custom Fields

All custom fields default to **Hidden** for Front Desk staff. Administrators must explicitly grant access to each custom field they want Front Desk to see.

---

## How to Configure (Step by Step)

1. Go to **Admin → Field Access** (you'll find this in the admin settings area)
2. You'll see two sections:

### Core Fields

The top section shows the four configurable core fields:

- **Phone Number**
- **Email Address**
- **Preferred Name**
- **Date of Birth**

For each field, select the access level you want Front Desk staff to have:
- **Hidden** — they won't see it
- **View only** — they can see it but not change it
- **View and edit** — they can see and change it

### Custom Fields

Below the core fields, you'll see all your agency's active custom fields, organised by their field groups (for example, "Contact Information", "Demographics").

For each custom field, choose the same three options: Hidden, View only, or View and edit.

3. Click **Save** when you're done
4. Changes take effect immediately — no restart or logout needed

### Resetting to Defaults

If you've made changes and want to go back to the original safe defaults:

1. On the **Field Access** page, click **Reset to Defaults**
2. All core fields return to their tier-appropriate defaults (see the table above)
3. All custom fields return to **Hidden**
4. This action is logged in the audit trail

---

## Available Fields and What Each One Controls

### Core Fields

| Field | What It Contains | Notes |
|---|---|---|
| **Phone Number** | Participant's primary phone number | Commonly needed for scheduling and check-in |
| **Email Address** | Participant's email address | May reveal location (email domain) in sensitive situations |
| **Preferred Name** | The name the participant wants to be called | Useful for a welcoming front desk experience |
| **Date of Birth** | Participant's date of birth | Clinical information — hidden by default |

### Custom Fields

Your agency's custom fields are fully configurable. Common examples include:

| Example Field | Typical Access Level | Reason |
|---|---|---|
| Address | Hidden | Could reveal a participant's location |
| Emergency contact | Hidden or View only | May be sensitive in DV situations |
| Employer | Hidden | Could be used to locate someone |
| Preferred pronouns | View only or View and edit | Supports respectful front desk interaction |
| Allergies | View only | Safety information staff may need |

The right configuration depends on your agency's services, population, and safety considerations.

---

## Interaction with DV-Safe Mode

**DV-Safe Mode overrides field access settings.** Here's how the two features interact:

1. You configure a custom field (say, "Home Address") as **View only** for Front Desk
2. A participant has a DV safety flag set on their file
3. The "Home Address" field is marked as **DV-sensitive**

**Result:** Front Desk staff **cannot see** the Home Address for that participant, even though the field is normally set to "View only". The DV safety flag takes priority.

In other words:

| DV Flag On? | Field Is DV-Sensitive? | Normal Access Level | What Front Desk Sees |
|---|---|---|---|
| No | No | View only | The field value |
| No | No | Hidden | Nothing |
| No | Yes | View only | The field value |
| **Yes** | **Yes** | View only | **Nothing** (DV flag overrides) |
| **Yes** | **Yes** | View and edit | **Nothing** (DV flag overrides) |
| Yes | No | View only | The field value (DV flag only hides DV-sensitive fields) |

> **Key principle:** DV-Safe Mode is a safety net that sits *on top of* your field access configuration. It can hide fields that would otherwise be visible, but it never reveals fields that are already hidden.

---

## Examples: Common Configurations

### Drop-In Centre

A low-barrier drop-in centre where everyone on the team works together and there's no clinical data:

| Field | Access Level |
|---|---|
| Phone | View and edit |
| Email | View and edit |
| Preferred Name | View and edit |
| Date of Birth | Hidden |
| Address (custom) | View only |
| Emergency Contact (custom) | View only |

**Tier recommendation:** Tier 1 or Tier 2

### Community Counselling Agency

A counselling agency with a dedicated reception desk and clinical programs:

| Field | Access Level |
|---|---|
| Phone | View only |
| Email | View only |
| Preferred Name | View only |
| Date of Birth | Hidden |
| Address (custom) | Hidden |
| Emergency Contact (custom) | Hidden |

**Tier recommendation:** Tier 2

### Women's Shelter or DV Agency

An agency where participants may be at risk and contact information is highly sensitive:

| Field | Access Level |
|---|---|
| Phone | Hidden |
| Email | Hidden |
| Preferred Name | View only |
| Date of Birth | Hidden |
| All contact fields (custom) | Hidden |

Additionally, mark all contact-related custom fields as **DV-sensitive** and enable the DV safety flag for at-risk participants.

**Tier recommendation:** Tier 3

---

## Audit Logging

All changes to field access settings are recorded in the audit log. The log entry includes:

- Who made the change
- When it was made
- Which fields were changed and what the old and new access levels were

If you reset to defaults, that action is also logged separately.
