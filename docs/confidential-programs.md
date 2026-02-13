# Confidential Programs & Duplicate Matching

This guide explains how KoNote handles sensitive programs and prevents duplicate client records across programs.

> **Who is this for?** Administrators setting up programs, and program managers working with sensitive services (counselling, mental health, addiction, domestic violence support).

| I want to... | Go to... |
|--------------|----------|
| Understand the two program types | [Standard vs. Confidential Programs](#standard-vs-confidential-programs) |
| Set up a confidential program | [Creating a Confidential Program](#creating-a-confidential-program) |
| Understand duplicate matching | [Duplicate Detection](#duplicate-detection) |
| Know what staff see (and don't see) | [What Staff See](#what-staff-see) |
| Prepare for DV or high-risk services | [Readiness for High-Risk Services](#readiness-for-high-risk-services) |
| Understand soft-filter vs. hard-boundary | [Soft-Filter vs. Hard-Boundary Access Controls](#soft-filter-vs-hard-boundary-access-controls) |
| Complete a Privacy Impact Assessment | [Privacy Impact Assessment](#privacy-impact-assessment) |

---

## Standard vs. Confidential Programs

KoNote has two types of programs. The type is chosen when a program is created and affects who can see client records.

| | Standard Programs | Confidential Programs |
|---|-------------------|----------------------|
| **Examples** | Sports, employment, settlement, food bank, tutoring, youth programs | Counselling, mental health, addiction, sexual health, DV support |
| **Cross-program matching** | Enabled — helps prevent duplicate records | Completely disabled — no matching ever |
| **Visible to other staff?** | Yes — staff in other standard programs can discover shared clients | No — clients are invisible to everyone outside the program |
| **Visible in Django admin?** | Yes | No — even superusers cannot browse individual records |
| **Appears in reports?** | Yes, with full counts | Aggregate counts only, with small-cell suppression (shows "< 10" when fewer than 10 clients) |
| **Can be reversed?** | N/A | No — once a program is marked confidential, it cannot be changed back without a formal Privacy Impact Assessment |

### Why two types?

Multi-service agencies often run casual programs (basketball, employment) alongside sensitive services (addiction counselling, DV support). A front desk worker checking someone in for basketball must never learn they are also receiving DV support. Confidential programs solve this by making those clients completely invisible to staff in other programs.

---

## Creating a Confidential Program

1. Click **Admin** → **Programs** → **Create Program**
2. Enter the program name
3. Look for the **"Is this a confidential program?"** section

**Automatic suggestion:** If your program name contains words like "counselling," "mental health," "addiction," "domestic violence," or "shelter," KoNote will suggest marking it as confidential. This is a suggestion — you make the final decision.

4. Check **"Yes, this is a confidential program"** if needed
5. Click **Create**

### Important: This is a one-way decision

Once a program is marked confidential, it **cannot be changed back** to standard through the interface. This is intentional — downgrading a confidential program could expose sensitive client records to staff who should not see them.

If you need to reverse this setting, your agency must complete a formal Privacy Impact Assessment documenting why the change is safe.

---

## Duplicate Detection

When staff create a new client in a **standard** program, KoNote automatically checks whether that person might already have a record. This prevents duplicate records without requiring staff to manually search.

### How matching works

| Step | What happens | What staff see |
|------|-------------|----------------|
| Staff enters a phone number | System checks the phone against all standard-program clients | Nothing yet — check runs in the background |
| Phone match found | Banner appears at the top of the form | "A client named **[Name]** already has a record with this phone number." |
| No phone match, but name + date of birth match | System checks first name + date of birth | "A client with a similar name and date of birth already has a record." |
| No match at all | Nothing — the form continues normally | No banner, no delay |
| Client is in a confidential program | **Never matched. Completely invisible.** | Staff see nothing |

### What the banner looks like

The banner is a gentle notice — not a pop-up or blocker. Staff can:
- **View the existing record** to check if it's the same person
- **Continue creating a new record** if it's a different person with the same phone or similar name

### What is NOT used for matching

To protect privacy (especially for family members), these fields are **never** used for matching:
- Emergency contact names or phone numbers
- Addresses (too many people share a household)
- Case note content
- Custom field values

---

## What Staff See

### Staff in standard programs

- Can see clients enrolled in any standard program they have access to
- See duplicate match banners when creating new clients
- Can view client records across their standard programs
- **Cannot see** clients who are only enrolled in confidential programs
- **Cannot see** the names of confidential programs in client records

### Staff in confidential programs

- Can only see clients enrolled in their specific confidential program
- **Do not** see duplicate match banners (matching is disabled for confidential programs)
- Cannot search for or discover clients in other programs
- Their clients are invisible to all other staff

### Administrators and superusers

- Can see that a confidential program exists (name and aggregate statistics only)
- **Cannot browse** individual client records in confidential programs through Django admin
- See "< 10" instead of exact counts when a confidential program has fewer than 10 clients
- Every access to a confidential client record is logged in an immutable audit trail

### The key rule: Absence of results reveals nothing

If a staff member searches for someone and gets no results, the system simply says "No results found." It **never** hints that hidden records might exist — no messages like "some programs may not be included" or "results may be limited."

---

## Readiness for High-Risk Services

Before using confidential programs for domestic violence or other high-risk services, verify these safeguards are in place:

### 1. Admin isolation is active

Superusers and administrators cannot browse individual client records in confidential programs. This is enforced at the database query level, not just the interface.

### 2. Audit logging is active

Every access to a confidential client record is logged:
- **Who** accessed it (user, role)
- **When** (timestamp)
- **What** they did (viewed, edited, created)
- **Which** record

These logs are stored in a separate database and cannot be deleted by the person being audited. Program managers can pull an access report for any client at any time.

### 3. Small-cell suppression is active

Aggregate reports show "< 10" instead of exact counts when a confidential program has fewer than 10 clients. This prevents inference attacks (e.g., "there's exactly 1 client in DV services this week — it must be...").

### 4. Tests verify the boundary

A dedicated test suite (`tests/test_confidential_isolation.py`) verifies that confidential clients cannot be discovered through any code path — searches, matching, admin views, reports, or error messages.

### 5. Privacy Impact Assessment is complete

Your agency should complete a PIA before activating confidential programs for high-risk services. See [Privacy Impact Assessment](#privacy-impact-assessment) below.

### When to use a separate instance instead

KoNote's confidential program isolation protects against system-level disclosure — searches, matching, admin browsing, and reports. It does **not** protect against:
- A threat actor with administrative access to your hosting platform
- Physical access to the server
- Credential theft of a confidential program staff member

For the rare case where a known threat actor has hosting platform admin access, we recommend a **separate KoNote instance** with independent hosting credentials.

---

## Privacy Impact Assessment

KoNote ships with a pre-filled PIA template at [Privacy Impact Assessment Template](pia-template-answers.md). This template walks your agency through:

1. **What data does KoNote collect?** (Pre-filled from your configuration)
2. **Who has access?** (Pre-filled from user roles and program assignments)
3. **What safeguards are in place?** (Pre-filled: encryption, audit logging, confidential isolation)
4. **What are the residual risks?** (Pre-filled honestly: hosting provider access, credential compromise)
5. **What mitigations exist?** (Pre-filled: encrypted fields, query-level filtering, annual review)

Complete this assessment with your Privacy Officer before going live with confidential programs.

---

## Soft-Filter vs. Hard-Boundary Access Controls

KoNote uses two distinct levels of access control. Privacy officers should understand the difference when assessing risk.

### Soft-filter (standard programs)

Standard program access uses a **soft filter** — a preference-based view that limits what staff normally see, but does not create an impenetrable wall.

| Aspect | How it works |
|--------|-------------|
| **What it controls** | Which clients appear in a staff member's default list |
| **How it's enforced** | Database queries filter by the user's active program assignments |
| **Can admins override it?** | Yes — administrators can assign themselves to additional programs to broaden their view |
| **Can staff discover hidden clients?** | Only clients in other standard programs they could be assigned to. Duplicate detection intentionally surfaces potential matches across standard programs |
| **Purpose** | Keeps day-to-day views focused and manageable. Prevents accidental access, not determined access |

### Hard-boundary (confidential programs)

Confidential program access uses a **hard boundary** — an architectural wall that cannot be bypassed through normal system use.

| Aspect | How it works |
|--------|-------------|
| **What it controls** | Whether client records exist at all from the perspective of outside staff |
| **How it's enforced** | Query-level filtering that excludes confidential clients from all search, matching, admin browse, and report detail paths |
| **Can admins override it?** | No — even superusers and Django admin cannot browse individual confidential client records |
| **Can staff discover hidden clients?** | No — no search, matching, or browsing path reveals confidential clients to outside staff. Aggregate reports use small-cell suppression ("< 10") to prevent inference |
| **Purpose** | Protects sensitive service participation (DV, addiction, mental health) from disclosure to any staff outside the program |

### Key distinction for privacy assessments

A soft-filter protects against **accidental** access — a front desk worker doesn't see counselling clients in their daily list, but the system doesn't claim those clients don't exist. A hard-boundary protects against **intentional** discovery — even a determined administrator using Django admin, search, or reports cannot identify individual confidential clients.

When completing a Privacy Impact Assessment, document standard programs as using soft-filter controls and confidential programs as using hard-boundary controls. This distinction matters for regulatory compliance (PHIPA, PIPEDA) because the level of safeguard should match the sensitivity of the data.

---

## Edge Cases

### Family members across program types

A mother in DV counselling (confidential) and her child in after-school (standard). If the after-school worker enters the mother's phone as an emergency contact, no disclosure occurs — emergency contacts are excluded from matching, and matching never searches confidential clients.

### Client moving between program types

A client completes addiction counselling (confidential) and moves to employment support (standard). Their record must be manually migrated with the client's active participation. The counsellor and employment worker coordinate with the client present.

### Neutral program names

Confidential programs can use neutral names like "Community Support Services." Since confidential clients are invisible to other programs, the program name is never shown outside its own staff.

---

## Annual Security Review

Agencies using confidential programs should conduct an annual review. See the [Annual Security Review Checklist](confidential-program-review-checklist.md) for the complete checklist.

---

## Legal & Regulatory Basis (Ontario)

| Law | Requirement | How KoNote meets it |
|-----|-------------|---------------------|
| **PHIPA** | Access controls commensurate with sensitivity, audit logging, breach notification | Role-based access, immutable audit logs, program-level isolation |
| **PIPEDA** | Limit collection, use, and disclosure of personal information | Program-scoped access — staff only see clients in their programs |
| **FIPPA** | Reasonable safeguards against unauthorised access | Query-level filtering + field-level encryption |

No Ontario statute requires a physically separate database for DV programs. The legal requirement is **adequate safeguards**, which this design provides.

---

## Related Documentation

- [Administering KoNote](administering-KoNote.md) — general admin setup
- [Security Operations](security-operations.md) — encryption, audit logging, incident response
- [Privacy Policy Template](privacy-policy-template.md) — customise for your organisation
- [Privacy Impact Assessment Template](pia-template-answers.md) — pre-filled PIA for your agency
- [Annual Security Review Checklist](confidential-program-review-checklist.md) — yearly verification
