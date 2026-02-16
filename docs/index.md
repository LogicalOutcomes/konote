# KoNote Documentation

Welcome! Find what you need based on what you're trying to do.

---

## Which Guide Do I Need?

| I want to... | Start here |
|--------------|------------|
| **Get quick help with a task** | [Help](help.md) — in-app help and quick reference |
| **Understand what KoNote is** | [README](../README.md) — overview, features, tech stack |
| **Understand the design philosophy** | [Design Principles](design-principles.md) — research-based approach to participant engagement |
| **Set up KoNote for the first time** | [Deploying KoNote](deploying-KoNote.md) — local setup, cloud hosting |
| **Configure my agency's settings** | [Administering KoNote](administering-KoNote.md) — terminology, programs, users, backups |
| **Learn how to use KoNote daily** | [Using KoNote](using-KoNote.md) — staff training guide |
| **Understand the technical architecture** | [Technical Reference](technical-documentation.md) — data models, security, APIs |

---

## What's New

- **Staff messaging & My Messages** — leave messages for case workers about participants, view and manage your inbox. Front desk can leave messages; staff and PMs can read messages for their programs.
- **Client transfer workflow** — move participants between programs with a dedicated transfer form, permission key, and full audit trail. Confidential program enrolments are preserved.
- **PM admin self-service** — program managers can now manage their own program's plan templates, note templates, event types, metrics, and registration links without needing a system administrator
- **Portal staff management** — invite participants to the portal, manage and revoke access, reset MFA — all from the client detail page
- **Automated meeting reminders** — the `send_reminders` command sends SMS/email reminders for meetings in the next 36 hours, with automatic retry for failures
- **Weekly export summary emails** — the `send_export_summary` command emails admins a digest of all export activity for privacy oversight
- **System health monitoring banners** — the Meetings page shows yellow/red warnings when SMS or email channels are experiencing failures
- **Messaging & communications** — log phone calls, emails, SMS, and in-person contacts on the client timeline. Quick-log buttons for common interactions.
- **Meetings & calendar** — schedule meetings with clients, track status (completed/cancelled/no-show), and subscribe to an iCal feed in Outlook or Google Calendar
- **Consent management** — CASL-compliant consent tracking for SMS and email, with withdrawal dates and implied/express consent types
- **Alert safety workflow** — two-person rule for alert cancellation: staff recommend, program managers approve or reject
- **Report templates** — upload demographic breakdowns as CSV, generate reports with small-cell suppression
- **Permissions audit & UX** — 48-key permission matrix enforced across all roles, scoped audit logs for program managers, role-aware 403 page
- **French language support** — full bilingual interface with 748+ translated strings
- **Client data erasure** — multi-PM approval workflow for PIPEDA/GDPR compliance
- **Self-service registration** — public forms with capacity limits and duplicate detection
- **Export hardening** — CSV injection protection, elevated export monitoring, secure download links
- **Canadian localisation** — postal code and phone number validation
- **Confidential programs** — sensitive program isolation with audit logging and duplicate detection
- **Demo mode** — safe evaluation with separated demo data

---

## Quick Links

### For Everyone

- [Help & Quick Reference](help.md) — find answers fast
- [Keyboard Shortcuts](help.md#keyboard-shortcuts)
- [Troubleshooting](help.md#troubleshooting)

### For Administrators

- [Privacy Policy Template](privacy-policy-template.md) — customise before going live
- [Agency Setup](administering-KoNote.md#agency-configuration) — terminology, features, programs
- [PM Admin Access](administering-KoNote.md#program-manager-administration) — let PMs manage their own program config
- [Registration Forms](administering-KoNote.md#set-up-registration-forms) — public signup forms, reviewing submissions
- [User Management](administering-KoNote.md#user-management) — creating accounts, assigning roles
- [Automated Reminders](administering-KoNote.md#automated-reminders) — set up scheduled SMS/email meeting reminders
- [Weekly Export Summary](administering-KoNote.md#weekly-export-summary-email) — privacy oversight digest for admins
- [System Health Monitoring](administering-KoNote.md#system-health-monitoring) — SMS/email channel health banners
- [Backup & Restore](administering-KoNote.md#backup-and-restore) — protecting your data
- [Security Operations](administering-KoNote.md#security-operations) — audit logs, encryption keys
- [Export Operations](export-runbook.md) — managing exports and download links
- [Confidential Programs & Matching](confidential-programs.md) — sensitive program isolation and duplicate detection
- [Security Operations (detailed)](security-operations.md) — encryption, audit logging, erasure, export controls

### For Staff

- [Finding Clients](using-KoNote.md#finding-a-client)
- [Writing Progress Notes](using-KoNote.md#writing-progress-notes)
- [Recording Events](using-KoNote.md#recording-events)
- [Logging Communications](using-KoNote.md#logging-communications)
- [Staff Messaging](using-KoNote.md#staff-messaging) — leave and read messages about participants
- [Client Transfer](using-KoNote.md#transferring-a-client) — move participants between programs
- [Scheduling Meetings](using-KoNote.md#scheduling-meetings)
- [Using the Calendar Feed](using-KoNote.md#using-the-calendar-feed)
- [Viewing Plans](using-KoNote.md#viewing-the-outcome-plan)

### For Deployment

- [Local Development (Docker)](deploying-KoNote.md#local-development-docker)
- [Deploy to Railway](deploying-KoNote.md#deploy-to-railway)
- [Deploy to Azure](deploying-KoNote.md#deploy-to-azure)
- [Deploy to Elestio](deploying-KoNote.md#deploy-to-elestio)
- [PDF Reports Setup](deploying-KoNote.md#pdf-report-setup)

---

## Document Overview

| Document | Audience | Purpose |
|----------|----------|---------|
| [Help](help.md) | All users | Quick reference and in-app help |
| [Design Principles](design-principles.md) | All users | Research-based approach to participant-centred practice |
| [Deploying KoNote](deploying-KoNote.md) | IT / Technical lead | Get KoNote running (local or cloud) |
| [Privacy Policy Template](privacy-policy-template.md) | Admins / Legal | Customise for your organisation before going live |
| [Administering KoNote](administering-KoNote.md) | Program managers / Admins | Configure and maintain your instance |
| [Confidential Programs](confidential-programs.md) | Program managers / Admins | Sensitive program isolation and duplicate matching |
| [Using KoNote](using-KoNote.md) | Front-line staff | Day-to-day usage guide |
| [Technical Reference](technical-documentation.md) | Developers | Architecture, data models, customisation |

---

## Support

- **Documentation issues:** [Open an issue on GitHub](https://github.com/your-org/KoNote-web/issues)
- **Security vulnerabilities:** See [SECURITY.md](../SECURITY.md)
