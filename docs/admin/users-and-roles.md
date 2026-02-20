# Users & Roles

How to create user accounts, manage roles, and set up per-program permissions.

---

## Creating User Accounts

There are three ways to create user accounts, depending on the situation:

| Method | Best for | How it works |
|--------|----------|-------------|
| **Invite link** (recommended) | Onboarding new staff | Admin creates a link; the new person sets up their own username and password |
| **Direct creation** | Quick setup, temporary accounts | Admin fills in all details including password |
| **Azure AD SSO** | Organisations using Microsoft 365 | Users are created automatically on first login |

### Invite a New User (Recommended)

Invite links are the easiest way to onboard staff. The new person chooses their own username and password.

1. Click **gear icon** -> **User Management**
2. Click **Invite User**
3. Choose:
   - **Role** -- front desk, staff, program manager, executive, or admin
   - **Programs** -- which programs they'll have access to
   - **Link expiry** -- how many days the invite is valid (default: 7)
4. Click **Create Invite**
5. Copy the generated link and send it to the new person

When they open the link, they'll set up their display name, username, and password. They're logged in immediately with the correct role and program access.

> **Tip:** Each invite link can only be used once. If it expires or the person needs a new one, create another invite.

### Create a User Directly

For quick setup when you want to control the credentials:

1. Click **gear icon** -> **User Management**
2. Click **+ New User**
3. Fill in:
   - **Display Name:** Full name (shown in reports)
   - **Username:** (local auth) Login name
   - **Email:** Work email
   - **Password:** (local auth) Temporary password
   - **Is Admin:** Check for configuration access
4. Click **Create**

---

## User Roles

| Role | Can do |
|------|--------|
| **Admin** | All settings, user management, templates |
| **Program Manager** | Program-level management |
| **Staff** | Enter data, write notes, view participants in assigned programs |
| **Front Desk** | Limited participant info, basic data entry |

---

## Per-Program Role Assignments

A single user can hold **different roles in different programs**. This is common in small agencies where one person wears multiple hats.

**Examples:**
- Sarah is **Program Manager** in "Youth Housing" but delivers direct services as **Staff** in "Employment Support"
- David works the front desk for Drop-In Centre (**Front Desk**) but does casework in Mental Health (**Staff**)

**When to use this:**
- A senior staff member oversees one program but facilitates groups or sees participants in another
- A front-desk worker also does casework in a specific program
- Someone is covering temporarily in a different capacity

**How it works:**
- Each program assignment has its own role -- the system checks the role for the specific program being accessed
- When viewing a participant enrolled in multiple programs, the user's **highest** role across those programs applies
- The user's current role is shown as a badge in the navigation bar

**To manage per-program roles:**
1. Go to **User Management**
2. Click **Roles** next to the user's name
3. Use the table to see current program assignments
4. Use the form below the table to add a new program role
5. Click **Remove** to revoke access to a specific program

> **Tip:** When someone manages one program but personally runs groups in another, assign them as Program Manager in the first and Staff in the second. This gives them management tools where they need them and direct-service access where they're delivering services.

---

## Deactivate Users

When someone leaves:
1. Go to **User Management**
2. Click user -> **Edit**
3. Uncheck **Is Active**
4. Click **Save**

They can no longer log in, but historical data is preserved.

---

## Program Manager Administration

Program managers can manage configuration for their own programs without needing a full system administrator. This reduces the administrative burden on admins and lets PMs customise their program workflows independently.

### What PMs Can Manage

| Area | What they can do | Where to find it |
|------|-----------------|------------------|
| **Plan templates** | Create, edit, and delete plan templates for their program | Manage -> Plan Templates |
| **Note templates** | Create, edit, and delete progress note templates for their program | Manage -> Note Templates |
| **Event types** | Create, edit, and delete event types for their program | Manage -> Event Types |
| **Outcome metrics** | Create, edit, enable/disable metrics for their program | Manage -> Metric Library |
| **Suggestion themes** | Create, edit, and track participant feedback themes | Manage -> Suggestions |
| **Registration links** | Create and manage public registration links for their program | Manage -> Registration |
| **Team members** | View and manage staff assignments within their program | Manage -> Users |

### How Scoping Works

- PMs see **their own program's items** plus **global items** (created by admins) in read-only mode
- PMs can only **edit or delete items that belong to their program** -- global templates and metrics created by administrators are read-only for PMs
- When a PM creates a new template or metric, it is automatically assigned to their program (if they manage only one program)
- If a PM manages multiple programs, they choose which program to assign the new item to
- PMs **cannot** change system-wide settings, terminology, feature toggles, or create other PM/admin accounts

### What Admins Still Control

These tasks remain admin-only:

- Instance settings (product name, logo, support email)
- Terminology customisation
- Feature toggles (enabling/disabling modules)
- Custom participant field definitions
- Report templates
- User management (creating admins, executives, or PMs)
- Merging duplicate participants
- Secure export link management

> **Tip:** If a program manager needs a global template modified, they should ask an admin. PMs can create a program-specific copy of a global template and customise that instead.

---

[Back to Admin Guide](index.md)
