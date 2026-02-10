# What KoNote Is (and Isn't)

KoNote is a **Participant Outcome Management system** designed for Canadian nonprofits. It helps agencies track client progress, document service delivery, and report on outcomes to funders.

This page explains what KoNote does, what it intentionally does not do, and why those boundaries exist.

---

## What KoNote IS

KoNote focuses on **outcome-based service delivery** — helping agencies document what they do with clients and whether it's working.

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Client Records** | Secure storage of participant information with encrypted PII (names, contact details, sensitive data). |
| **Outcome Plans** | Goal-based planning with sections, targets, and measurable metrics. |
| **Progress Notes** | Quick notes for brief updates and structured notes with templates for detailed documentation. |
| **Metric Tracking** | Record quantitative measures (attendance, satisfaction scores, goal progress) and visualise trends over time. |
| **Event Logging** | Document discrete occurrences: intakes, discharges, milestones, crises, hospital visits. |
| **Charts & Visualisation** | See client progress as line charts and combined timelines. |
| **Funder Reporting** | Export data for external funders; generate PDF reports. |
| **Role-Based Access** | Four roles (Admin, Manager, Direct Service, Front Desk) with appropriate permissions for each. |
| **Customisable Terminology** | Change "Client" to "Participant", "Member", or whatever your agency uses. |
| **Multi-Program Support** | Manage multiple service streams within one organisation. |
| **Custom Client Fields** | Add agency-specific data fields (funding source, referral date, etc.). |

### Who KoNote Is For

- Community service agencies
- Youth programs and housing supports
- Mental health and addiction services
- Employment and training programs
- Family support organisations
- Any nonprofit tracking client outcomes for internal use or funder reporting

---

## What KoNote is NOT

KoNote is intentionally focused. It does one thing well rather than trying to do everything poorly. Here's what falls outside its scope — and what tools to use instead.

### Not a Calendar or Scheduler

KoNote does not manage appointments, room bookings, or staff schedules.

**Use instead:**
- [Calendly](https://calendly.com) — appointment scheduling
- [Google Calendar](https://calendar.google.com) — team calendars
- [Microsoft Bookings](https://www.microsoft.com/en-ca/microsoft-365/business/scheduling-and-booking-app) — client self-booking
- [Acuity Scheduling](https://acuityscheduling.com) — appointment management

### Not Document Storage

KoNote stores structured data (notes, plans, metrics) — not files like PDFs, consent forms, or case documents.

**Use instead:**
- [SharePoint](https://www.microsoft.com/en-ca/microsoft-365/sharepoint) — enterprise document management
- [Google Drive](https://drive.google.com) — cloud file storage
- [Dropbox](https://www.dropbox.com) — simple file sharing

**Integration:** KoNote can link to a client's document folder in SharePoint or Google Drive. You store documents there; KoNote links to them.

### Not an Offline Application

KoNote requires an internet connection. It's a web application hosted on a server.

**Use instead for field data collection:**
- [KoBoToolbox](https://www.kobotoolbox.org) — free offline forms for humanitarian work
- Paper intake forms — scan and upload later

**Future integration:** KoNote can import field data from KoBoToolbox and SharePoint Lists.

### Not Multi-Tenant SaaS

Each agency runs their own KoNote instance. There's no shared platform where multiple organisations log in to the same system.

**Why:** Data isolation. Your client data lives on your server, not mixed with other agencies.

**For coalitions:** If multiple agencies need to share one system, a forked deployment with shared access can be configured — but this requires technical setup.

### Not a CRM (Customer Relationship Management)

KoNote tracks service outcomes, not fundraising relationships or donor management.

**Use instead:**
- [Salesforce Nonprofit](https://www.salesforce.org/nonprofit/) — donor and constituent management
- [Bloomerang](https://bloomerang.co) — donor retention
- [Little Green Light](https://www.littlegreenlight.com) — nonprofit donor database

### Not a Case Management System

KoNote does not include workflows, approvals, task routing, or case assignments. It's simpler than enterprise case management.

**Use instead:**
- [Apricot](https://www.socialsolutions.com/software/apricot/) — full case management
- [Penelope](https://www.athenasoft.ca) — case management for Canadian social services
- [Link2Feed](https://www.link2feed.com) — food bank case management

### Not an EHR/EMR

KoNote is not designed for clinical healthcare documentation. It doesn't meet healthcare-specific compliance requirements (HL7, FHIR, clinical terminology standards).

**Use instead:**
- [OSCAR](https://oscar-emr.com) — open-source Canadian EMR
- [Accuro](https://www.accuromd.com) — Canadian EMR
- [Jane App](https://jane.app) — health and wellness practice management

---

## Integration Philosophy

KoNote is designed to **work alongside** other tools, not replace them.

| Integration | How It Works |
|-------------|--------------|
| **Document folders** | Link to client folders in SharePoint or Google Drive |
| **CSV export** | Export data for use in Excel, Power BI, or funder templates |
| **Field data import** | (Future) Import intake data from KoBoToolbox or SharePoint Lists |

The goal: **use the best tool for each job.** Scheduling tools do scheduling better. Document systems do storage better. KoNote does outcome tracking better.

---

## Why These Boundaries Exist

### Simplicity

Fewer features means easier training, faster onboarding, and less confusion. Staff can learn KoNote in an afternoon, not a week.

### Focus

KoNote does outcome tracking really well. Adding calendars, document storage, and offline sync would dilute that focus and add complexity without improving the core mission.

### Integration Over Duplication

Specialised tools (Google Calendar, SharePoint, KoBoToolbox) have years of development behind them. Rather than build inferior versions of those features, KoNote integrates with them.

### Security

The less data KoNote stores, the smaller the attack surface. Client documents in SharePoint stay in SharePoint — KoNote just links to them.

### Cost

Simpler systems require less hosting resources, less maintenance, and less support. This keeps KoNote affordable for small nonprofits.

---

## Summary

**KoNote is:**
- Client records + encrypted PII
- Outcome plans with goals and metrics
- Progress notes (quick and structured)
- Charts and funder reporting
- Role-based access control
- Customisable terminology and fields

**KoNote is not:**
- A scheduler → use Calendly, Google Calendar
- Document storage → use SharePoint, Google Drive
- An offline app → use KoBoToolbox for field work
- Multi-tenant SaaS → each agency has its own instance
- A CRM → use Salesforce, Bloomerang
- Case management → use Apricot, Penelope
- An EHR/EMR → use OSCAR, Accuro, Jane App

---

**Version 1.0** — KoNote Web
Last updated: 2026-02-03
