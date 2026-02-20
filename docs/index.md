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

## What's New (v2.3)

- **Surveys** — structured feedback forms with trigger rules (auto-assign based on events, enrolment, or time), shareable public links, auto-save, conditional sections, section scoring, and CSV import
- **SMS and email sending** — compose and send messages to participants with consent tracking, appointment reminder previews, CASL-compliant unsubscribe links, and safety-first mode
- **Participant portal completion** — password reset via email code, staff-assisted login with one-time tokens, PWA "Add to Home Screen", portal usage analytics dashboard, auto-deactivation on discharge
- **Dashboard roles** — coach, program manager, and executive landing pages with role-specific data and summaries
- **AI Goal Builder** — conversational goal-setting tool on the plan page for defining measurable targets collaboratively
- **Portal survey completion** — participants fill in assigned surveys with multi-page forms, auto-save, and conditional section visibility

### Previous (v2.2)

- Suggestion tracking & Outcome Insights — automated theme identification, responsiveness tracking, executive dashboard
- PM self-service administration — manage templates, metrics, event types, and registration links at /manage/
- Staff messaging — internal messages about participants with unread badges
- Client transfers — move participants between programs with audit trail
- Portal staff management — invite, revoke, and reset MFA from client detail page
- Automated scheduling — meeting reminders via SMS/email, weekly export summary emails

For a full history of changes, see the [Changelog](../CHANGELOG.md).

---

## Quick Links

### For Everyone

- [Help & Quick Reference](help.md) — find answers fast
- [Surveys Guide](surveys.md) — creating, assigning, and completing surveys
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
- [Suggestion Themes](administering-KoNote.md#suggestion-themes) — tracking and responding to participant feedback
- [Security Operations (detailed)](security-operations.md) — encryption, audit logging, erasure, export controls

### For Staff

- [Finding Clients](using-KoNote.md#finding-a-client)
- [Writing Progress Notes](using-KoNote.md#writing-progress-notes)
- [Recording Events](using-KoNote.md#recording-events)
- [Logging Communications](using-KoNote.md#logging-communications)
- [Staff Messaging](using-KoNote.md#staff-messaging) — leave and read messages about participants
- [Surveys](using-KoNote.md#surveys) — assigning and entering survey responses
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
| [Surveys](surveys.md) | All users | Creating, assigning, and completing surveys |
| [Design Principles](design-principles.md) | All users | Research-based approach to participant-centred practice |
| [Deploying KoNote](deploying-KoNote.md) | IT / Technical lead | Get KoNote running (local or cloud) |
| [Privacy Policy Template](privacy-policy-template.md) | Admins / Legal | Customise for your organisation before going live |
| [Administering KoNote](administering-KoNote.md) | Program managers / Admins | Configure and maintain your instance |
| [Confidential Programs](confidential-programs.md) | Program managers / Admins | Sensitive program isolation and duplicate matching |
| [Using KoNote](using-KoNote.md) | Front-line staff | Day-to-day usage guide |
| [Technical Reference](technical-documentation.md) | Developers | Architecture, data models, customisation |

---

## Support

- **Documentation issues:** [Open an issue on GitHub](https://github.com/gilliankerr/KoNote/issues)
- **Security vulnerabilities:** See [SECURITY.md](../SECURITY.md)
