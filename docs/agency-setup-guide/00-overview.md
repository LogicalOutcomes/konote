# KoNote Agency Setup Guide — Overview

## How to Use This Guide

This guide is a set of **decision documents** — one per configuration area. Each document lists the decisions an agency needs to make, explains the options and their consequences, and shows what the completed configuration looks like.

**For AI-assisted setup:** Give your AI tool (Claude, ChatGPT, etc.) this overview document plus the specific decision documents you need. Ask it to walk you through the decisions. It will ask questions, explain trade-offs, and produce configuration output.

**For manual setup:** Read each document in order. Answer the questions. Hand the completed worksheets to your developer for configuration.

**For developer setup:** Read this overview to understand the order of operations, then use the individual decision documents as checklists while configuring the instance.

## What "Fully Configured" Means

A KoNote instance is ready for real data when all of these are in place:

1. **Terminology** — the system uses the agency's own words (participant/client/member, plan/pathway, etc.)
2. **Features** — only the modules the agency needs are turned on
3. **Roles & permissions** — staff see only what they should; privacy rules are enforced
4. **Programs** — the agency's service lines are set up with correct visibility rules
5. **Metrics & surveys** — the outcome measures and assessment tools the agency uses are configured
6. **Templates** — coaching plan structures and session note formats match the agency's workflow
7. **Reports** — funder reporting requirements are mapped to KoNote's export formats
8. **Users** — staff accounts created with correct roles and program access
9. **Verification** — everything has been tested and signed off

## Order of Operations

These must be done roughly in this order because later steps depend on earlier ones.

```
Step 1: Terminology          (no dependencies)
Step 2: Features             (no dependencies)
Step 3: Roles & Permissions  (no dependencies, but informed by Features)
Step 4: Programs             (depends on Roles)
Step 5: Metrics & Surveys    (depends on Programs)
Step 6: Plan & Note Templates (depends on Programs + Metrics)
Step 7: Reports              (depends on Metrics + Programs)
Step 8: Users                (depends on Roles + Programs)
Step 9: Verification         (depends on everything above)
```

Steps 1-3 can be done in parallel. Steps 5-7 can be done in parallel once Programs exist.

## Decision Documents

| # | Document | What It Covers | Decisions |
|---|----------|---------------|-----------|
| [01](01-terminology.md) | Terminology | What the agency calls participants, plans, notes, goals, programs | 5-7 term choices |
| [02](02-features.md) | Features & Modules | Which KoNote modules to turn on/off — portal, messaging, AI, surveys, bilingual | ~10 on/off toggles |
| [03](03-roles-permissions.md) | Roles & Permissions | Who can see what, who can do what, privacy rules | ~15 access decisions |
| [04](04-programs.md) | Programs | Service lines, confidentiality flags, staff assignments | Per-program setup |
| [05](05-surveys-metrics.md) | Surveys & Metrics | Which outcomes to track, assessment tools, custom metrics | Enable/disable from library + custom |
| [06](06-templates.md) | Plan & Note Templates | Structure for coaching plans and session documentation | Template sections and defaults |
| [07](07-reports.md) | Reports | Funder reporting requirements, export formats, demographic breakdowns | Report schema choices |
| [08](08-users.md) | Users & Authentication | Staff accounts, authentication method (SSO vs local), initial invitations | Per-user setup |
| [09](09-verification.md) | Verification | Testing checklist, role verification, sign-off | Pass/fail checks |

## Starting from a Template

If the agency belongs to an umbrella organisation (like a partner agency), start from the umbrella's configuration template instead of answering every question from scratch.

Available templates:
- **[partner agency]** — financial coaching agencies ([see example](examples/financial-coaching/))

With a template, the conversation changes from "answer all 50 decisions" to "here are the standard answers — what's different for your agency?" This typically cuts setup time from 3-6 weeks to 1-2 weeks.

## What Each Decision Document Contains

Every document follows the same structure:

- **What This Configures** — 2-3 sentences in plain language
- **Decisions Needed** — numbered list of questions with options and consequences
- **Defaults** — what happens if you skip a decision
- **Common Configurations** — pre-answered sets for common agency types
- **Output Format** — what the completed configuration looks like (JSON, admin steps, or management command)
- **Dependencies** — what must be done before and after
- **Example** — a completed configuration for a real agency

## For Developers: Technical Context

KoNote configuration is applied through a combination of:

1. **`apply_setup` management command** — loads JSON configuration files for terminology, features, metrics, plan templates, and custom fields. See [config_templates/README.md](../../config_templates/README.md).
2. **Django admin interface** — for settings not yet supported by `apply_setup` (note templates, report templates, role permissions).
3. **Environment variables** — for infrastructure settings (database URLs, encryption keys, authentication mode).

The decision documents produce output compatible with these mechanisms. As `apply_setup` expands to cover more configuration areas, more of the process can be automated.

## Reference Documents

These provide deeper context when needed:

| Document | What it covers |
|----------|---------------|
| [Deployment Protocol](../../tasks/deployment-protocol.md) | Full 5-phase deployment process with interview scripts and worksheets |
| [Permissions Interview](../../tasks/agency-permissions-interview.md) | Detailed guided interview for all access and privacy decisions |
| [Admin Documentation](../admin/index.md) | Feature-by-feature admin guide |
| [Deploying KoNote](../deploying-konote.md) | Platform comparison and technical deployment steps |
| [Config Template Design](../../tasks/config-template-design.md) | How umbrella templates work |
| [Security Architecture](../security-architecture.md) | Encryption, audit logging, privacy compliance |

## Status

| Document | Status | Notes |
|----------|--------|-------|
| 00 Overview (this file) | Done | |
| 01 Terminology | To do | Reformat from deployment-protocol.md 3.1 |
| 02 Features | To do | Reformat from permissions interview Session 2.7 |
| 03 Roles & Permissions | To do | Reformat from permissions interview (full) |
| 04 Programs | To do | Reformat from deployment-protocol.md 3.2 |
| 05 Surveys & Metrics | To do | Reformat from deployment-protocol.md 3.3 |
| 06 Templates | To do | Reformat from deployment-protocol.md 3.4-3.5 |
| 07 Reports | To do | New — needs funder reporting requirements |
| 08 Users | To do | Reformat from deployment-protocol.md Phase 2, 4 |
| 09 Verification | To do | Reformat from deployment-protocol.md Phase 4 |
| [funder partner] example | Partial | Config templates exist in config_templates/ |
