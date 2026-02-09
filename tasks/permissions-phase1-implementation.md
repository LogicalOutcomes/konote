# Permissions Redesign — Phase 1 Implementation
**Date:** 2026-02-08
**Status:** Implementation in progress

## Critical Security Issues Found

Through manual testing, discovered three critical permissions failures:

1. **Front Desk can access clinical data** — Group members, session notes, attendance visible to receptionists
2. **"Funder Report" exports client-level data** — Record IDs, individual metrics labeled as "aggregate"
3. **System admin can bulk-download sensitive data** — No oversight for data extract

## Root Cause

The permissions decorator `@minimum_role("staff")` checks user's **highest role across ALL programmes**, not their role in the specific programme for the resource.

**Example:** Sam is Front Desk in Youth Programme + Staff in Adult Programme → Sam's highest role is "staff" → Sam can access Youth Programme groups with clinical data.

## Phase 1 Implementation Plan

**Approved:** 2026-02-08
**Full plan:** `C:\Users\gilli\.claude\plans\sequential-gliding-kahan.md`

### Fix 1: Block Front Desk from Clinical Data
- Add `@programme_role_required()` decorator that checks role in SPECIFIC programme
- Update all 11 group views + 7 note views to use new decorator
- **Status:** Starting now

### Fix 2: Split Reports
- **Programme Report** (new) → aggregate only, PDF, for funders/board/donors
  - Total clients, sessions, achievement rates, demographic summaries
  - NO client names, NO record IDs, NO individual data
- **Data Extract** (rename existing) → hide, restrict to admin, add warnings
- **Status:** Pending

### Fix 3: Central Permissions File
- Create `apps/auth_app/permissions.py` with full matrix
- Documents what each role can/cannot do
- Foundation for future phases
- **Status:** Pending

### Fix 4: Permission Review Screen
- After role changes, show plain-language "CAN" / "CANNOT" summary
- Catches configuration mistakes
- **Status:** Pending

## Verification Tests

1. **Front Desk isolation** — dual-role user (receptionist + staff) blocked from receptionist programme's clinical data
2. **Programme Report** — verify PDF has only aggregates, no client names/IDs
3. **Data Extract hidden** — managers get 403, only admins see warning banner
4. **Review screen** — changing role shows updated capabilities
5. **Permissions validation** — all roles have all keys defined

## Estimated Effort
~20 hours focused work
