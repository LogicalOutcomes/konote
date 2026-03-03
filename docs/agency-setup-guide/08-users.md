# 08 — Users & Authentication

## What This Configures

How staff log in to KoNote, how their accounts are created, and how their roles and program access are assigned. This document covers authentication method (single sign-on vs. local accounts), initial account creation, role assignments, and the ongoing process for adding and removing users.

## Decisions Needed

### Authentication Method

1. **How will staff log in?**
   - **Azure AD Single Sign-On (SSO)** → staff log in with their existing work email (Microsoft 365 account). Recommended if your organisation uses Microsoft 365. Accounts are created automatically the first time someone logs in — but roles must be assigned manually afterward.
   - **Local authentication** → staff log in with a username and password specific to KoNote. Recommended if your organisation does not use Microsoft 365, or for smaller agencies that prefer simplicity.
   - Default: Must choose one. Both can be active simultaneously (SSO as primary, local as fallback for admin access).

2. **If using Azure AD SSO, does every person who needs KoNote access have an Azure AD account (work email)?**
   - Yes → straightforward; all users log in with their work credentials
   - No → people without Azure AD accounts will need either a local KoNote account or an Azure AD guest account. Common for volunteers, contract workers, or board members.
   - Default: Must confirm before setup

3. **Do you need a local admin account as a fallback?**
   - Yes (recommended) → a local admin account with no program role that can be used if Azure AD has issues. This is a safety net, not for daily use.
   - No → all access goes through Azure AD
   - Default: Yes — a local admin fallback is created during infrastructure setup

### Account Creation

4. **How do you want to create user accounts?**
   - **Invite links (recommended)** → admin creates a link; the new person opens it and sets up their own username, display name, and password. Each link can only be used once and expires after a set number of days.
   - **Direct creation** → admin fills in all details including a temporary password. Faster for initial setup, but the admin knows the password.
   - **Azure AD auto-creation** → for SSO; accounts are created automatically on first login. Roles are assigned afterward.
   - Default: Invite links for local auth; auto-creation for SSO

5. **How long should invite links be valid?**
   - Options: 3 days, 7 days (default), 14 days, 30 days
   - Default: 7 days. If the link expires, create a new one.

### Role and Program Assignments

6. **For each person, what role do they have in which program?**
   - Use the role assignments decided in Document 03
   - A person can have different roles in different programs (e.g., PM in one program, Direct Service in another)
   - Default: Must assign at least one program role per user (unless the user is an admin-only account with no participant data access)

7. **Who has the System Administrator flag?**
   - Use the administrator designations from Document 03
   - Reminder: the admin flag does not grant participant data access. An admin who also needs to see participant files needs a program role in addition to the admin flag.
   - Default: At least one person must be a system administrator

8. **For Azure AD SSO, how will roles be assigned after first login?**
   - Option A: Prepare a list in advance — when each person logs in for the first time, assign their role immediately
   - Option B: Batch setup — wait until all initial users have logged in, then assign roles in one session
   - Default: Prepare a list in advance for faster onboarding

### Initial User List

9. **Who needs an account right now?**
   - List all staff who will use the system at launch
   - For each person, capture:
     - Name
     - Email
     - Role per program (from Document 03)
     - System Administrator? (Yes/No)
   - Default: Create accounts for all staff identified in the permissions interview (Document 03)

10. **Are there any accounts that should have admin access but no participant data access?**
    - These are typically IT staff, office managers, or system administrators who configure the system but do not do client work
    - Give them the admin flag with no program role
    - Default: Depends on the administrator decisions in Document 03

### Ongoing User Management

11. **Who is responsible for creating new accounts when staff join?**
    - System administrator creates accounts and assigns roles
    - Program Managers can manage staff within their own programs (if configured in Document 03)
    - Default: System administrator handles all user creation

12. **What happens when a staff member leaves?**
    - Their KoNote account must be deactivated on their last day
    - If using Azure AD SSO, deactivating their Azure AD account prevents KoNote login automatically — but their KoNote account should still be explicitly deactivated
    - If using local auth, deactivate the account through User Management
    - Historical data (notes, actions) is preserved; the account simply cannot log in
    - Default: Must have a documented offboarding process (from Document 03)

## Common Configurations

- **Small agency (5 staff, local auth):** Create accounts using invite links, 7-day expiry. PM is admin. All staff get Direct Service roles. No admin-only accounts needed.
- **Medium agency (20 staff, Azure AD SSO):** SSO as primary, one local admin fallback. Prepare role assignment list before first login day. Batch assign roles after first-login wave. IT manager has admin flag with no program role.
- **Large agency (40+ staff, Azure AD SSO):** SSO as primary, two local admin fallbacks. PMs manage their own program's staff assignments. HR triggers account deactivation on departure, IT executes it.

## Output Format

### For Azure AD SSO

The developer configures Azure AD integration during infrastructure setup (Phase 2). The agency's IT contact needs to:

1. Register an application in Azure AD
2. Set the redirect URI to `https://[your-domain]/auth/callback/`
3. Create a client secret (set a calendar reminder for renewal — 12 or 24 months)
4. Provide the tenant ID, client ID, and client secret to the developer

**Environment variables set by the developer:**
```
AUTH_MODE=azure
AZURE_CLIENT_ID=[from IT contact]
AZURE_CLIENT_SECRET=[from IT contact]
AZURE_TENANT_ID=[from IT contact]
AZURE_REDIRECT_URI=https://[your-domain]/auth/callback/
```

### For Local Authentication

**Creating accounts via invite links:**
1. Go to the gear icon, then "User Management"
2. Click "Invite User"
3. Choose the role, programs, and link expiry
4. Click "Create Invite"
5. Send the generated link to the new staff member

**Creating accounts directly:**
1. Go to the gear icon, then "User Management"
2. Click "+ New User"
3. Fill in display name, username, email, and temporary password
4. Check "Is Admin" if they should have admin access
5. Click "Create"
6. Assign program roles afterward

### User Account Checklist

For each person at launch:

| Name | Email | Auth Method | Program(s) | Role per Program | System Admin? | Notes |
|------|-------|-------------|-----------|-----------------|---------------|-------|
| | | SSO / Local | | FD / DS / PM / Exec | Yes / No | |

### Deactivation Steps

When a staff member leaves:
1. Go to "User Management"
2. Click the user, then "Edit"
3. Uncheck "Is Active"
4. Click "Save"
5. If applicable: remove from SharePoint groups, transfer Google Drive folder ownership, review for exported data on personal devices

## Dependencies

- **Requires:** Document 03 (Roles & Permissions) — role assignments and administrator designations. Document 04 (Programs) — programs must exist before assigning users to them. Phase 2 infrastructure setup must be complete (for SSO configuration).
- **Feeds into:** Document 09 (Verification) — the walkthrough tests that each user can log in and sees the correct data for their role.

## Example: Financial Coaching Agency

**Authentication:** Azure AD SSO (the agency uses Microsoft 365). One local admin fallback account created during setup.

**Initial user list:**

| Name | Email | Auth Method | Programs | Role | Admin? |
|------|-------|-------------|----------|------|--------|
| Sarah Chen | sarah@example.ca | SSO | Financial Empowerment, Tax Clinic | Direct Service | No |
| David Kumar | david@example.ca | SSO | Financial Empowerment, Community Workshops | Direct Service | No |
| Lisa Park | lisa@example.ca | SSO | Tax Clinic (seasonal) | Direct Service | No |
| Maria Santos | maria@example.ca | SSO | All three programs | Program Manager | Yes |
| James Thompson | james@example.ca | SSO | Organisation-wide | Executive | Yes (backup) |
| admin-fallback | (local) | Local | None | None | Yes |

**Onboarding process:**
1. Maria (admin) sends a note to all staff: "When you log in to KoNote for the first time at [URL], use your work email. I will assign your role within 24 hours."
2. After each person's first SSO login, Maria assigns their program role(s)
3. The admin-fallback local account is documented in the agency's password manager, accessible to Maria and James

**Offboarding process:**
1. When a staff member leaves, their manager notifies Maria
2. Maria deactivates their KoNote account on their last day
3. IT deactivates their Azure AD account (which also prevents KoNote SSO login)
4. Maria reviews whether the departing person exported any data recently (checks the export log)

**Rationale:** SSO simplifies login for staff and means the agency does not need to manage separate KoNote passwords. The local admin fallback ensures someone can always access the system even if Azure AD has issues. Maria (PM) is the primary admin because she manages all three programs. James (ED) is the backup admin with Executive role only — he can manage the system in Maria's absence but does not routinely access individual participant files.
