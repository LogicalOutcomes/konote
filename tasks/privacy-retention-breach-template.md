# Privacy, Retention, and Breach Operations Template

Status: Fill-in-ready template for organisation-specific decisions
Related: [SaaS service agreement](saas-service-agreement.md), [Agency data offboarding](agency-data-offboarding.md), [Serious reportable events](serious-reportable-events.md), [Deployment protocol](deployment-protocol.md)

## Purpose

This template turns KoNote's existing technical controls into organisation-specific operating decisions. It is intentionally incomplete: each agency still needs to confirm retention periods, named contacts, approval thresholds, and regulator or funder notification rules.

## Current AI Assumption for Open-Ended Suggestions

For planning and policy purposes, assume open-ended suggestion categorisation runs on a self-hosted open-source LLM managed by the KoNote operator. That means:

- suggestion text is processed on infrastructure controlled by the KoNote operator, not a third-party public API
- the model endpoint, access keys, logs, and server hardening remain operator responsibilities
- any future change to an external provider requires a fresh privacy review and explicit approval before production use

If your organisation does not permit AI processing of participant text at all, keep the participant-data AI toggle disabled.

## Section 1: Roles and Contacts

Fill in the table below before go-live.

| Role | Name | Email / Phone | Backup Contact | Notes |
|---|---|---|---|---|
| Privacy officer / delegate | [fill in] | [fill in] | [fill in] | Responsible for privacy decisions and breach notifications |
| Executive director / sponsor | [fill in] | [fill in] | [fill in] | Approves policy exceptions |
| IT / KoNote operator | [fill in] | [fill in] | [fill in] | Maintains backups, restores, access revocation |
| Clinical / program lead | [fill in] | [fill in] | [fill in] | Advises on program-specific sensitivity |
| Legal / external advisor | [fill in] | [fill in] | [fill in] | Optional but recommended |

## Section 2: Retention Schedule

Replace placeholders with the organisation's approved schedule.

| Data set | Default holder | Retention period | Trigger for deletion / archival | Legal or contract basis | Notes |
|---|---|---|---|---|---|
| Participant record | KoNote primary database | [fill in] | [fill in] | [fill in] | Include discharged clients |
| Progress notes and outcomes | KoNote primary database | [fill in] | [fill in] | [fill in] | |
| Survey responses | KoNote primary database | [fill in] | [fill in] | [fill in] | Distinguish anonymous vs identified if needed |
| Audit logs | KoNote audit database | [fill in] | [fill in] | [fill in] | Usually longer than operational data |
| Database backups | Backup storage | [fill in] | [fill in] | [fill in] | Include main and audit backups |
| Export files | Temporary export directory | [fill in] | [fill in] | [fill in] | Confirm download expiry and admin review window |
| Offboarding package | Agency-controlled storage | [fill in] | [fill in] | [fill in] | See agency-data-offboarding.md |

Retention decision notes:

- [fill in] minimum retention required by contract, funder, or regulator
- [fill in] whether anonymised aggregate reporting can be kept longer
- [fill in] whether litigation hold or investigation hold pauses deletion

## Section 3: Privacy Notice Inputs

Use these points when finalising the organisation's privacy notice or participant-facing policy.

| Topic | Organisation-specific wording to confirm |
|---|---|
| Purpose of collection | [fill in] |
| Authority / consent basis | [fill in] |
| Where data is stored | [fill in] |
| Who can access KoNote data | [fill in] |
| AI processing of participant text | [fill in: enabled or disabled, and for which features] |
| Cross-border disclosures | [fill in] |
| Participant rights / complaints contact | [fill in] |
| Retention summary for participants | [fill in] |

### Suggested participant-facing wording

Use or adapt the wording below once organisation-specific details are confirmed.

#### Full privacy notice paragraph

> We collect your survey responses, service information, and related notes so authorised staff can deliver services, understand outcomes, improve programs, and meet reporting obligations. Your information is stored in KoNote on systems managed for this organisation or its approved operators. If this organisation enables AI-assisted feedback analysis, direct identifiers are removed before participant text is processed. Open-ended suggestions are categorised using a self-hosted model managed by KoNote, and staff review AI-generated summaries before they are used in reporting or program improvement. If that feature is not enabled, your responses are reviewed only by authorised staff and KoNote reporting tools.

#### Short portal disclosure

> Your responses help staff improve services and report on program outcomes. If AI-assisted feedback analysis is enabled for this organisation, direct identifiers are removed before participant text is processed, and open-ended suggestions are categorised using a self-hosted model managed by KoNote.

#### Optional "AI disabled" variant

> This organisation does not use AI to process participant responses or suggestions. Your responses are reviewed only by authorised staff and standard KoNote reporting tools.

## Section 4: Breach and Security Incident Workflow

Set concrete time targets and contacts before production use.

### 1. Triage

- Incident intake point: [fill in]
- Required initial facts: date/time, reporter, systems involved, data types involved, whether data was actually disclosed, and whether KoNote is still actively exposed
- Initial containment target: [fill in, for example within 1 hour]

### 2. Containment

- Disable affected accounts, tokens, or integrations
- Preserve logs, exports, backups, and screenshots needed for investigation
- If the issue involves infrastructure, decide who can stop services or block traffic: [fill in]
- If the issue involves participant-data AI, suspend the participant-data AI toggle until review is complete

### 3. Assessment

Document the following:

- categories of data involved
- number of affected participants or staff, if known
- whether encrypted data, plain-text exports, or emailed reports were exposed
- whether the incident triggers contractual, funder, insurer, PIPEDA, PHIPA, or other reporting duties
- whether the self-hosted LLM server, OpenWebUI connection, or external AI provider was involved

### 4. Notification Matrix

| Audience | Notify when | Owner | Deadline / target | Method |
|---|---|---|---|---|
| Internal leadership | [fill in] | [fill in] | [fill in] | [fill in] |
| Privacy officer | [fill in] | [fill in] | [fill in] | [fill in] |
| Affected partner agency | [fill in] | [fill in] | [fill in] | [fill in] |
| Participants / clients | [fill in] | [fill in] | [fill in] | [fill in] |
| Regulator / commissioner | [fill in] | [fill in] | [fill in] | [fill in] |
| Funder / insurer | [fill in] | [fill in] | [fill in] | [fill in] |

### 5. Closure

- Root cause documented: [fill in]
- Corrective action owner assigned: [fill in]
- Evidence of completion stored at: [fill in]
- Policy, training, or configuration changes required: [fill in]

## Section 5: Review Cadence

Confirm a recurring review schedule.

| Review item | Owner | Frequency |
|---|---|---|
| Retention schedule | [fill in] | [fill in] |
| Breach contact list | [fill in] | [fill in] |
| Backup restore drill | [fill in] | [fill in] |
| Participant-data AI posture | [fill in] | [fill in] |
| Privacy notice wording | [fill in] | [fill in] |

## Minimum Decisions Still Required

The template is not complete until the organisation confirms:

1. Named privacy and incident contacts.
2. Record retention periods for live data, backups, audit logs, and exports.
3. Notification thresholds and deadlines that apply to the organisation.
4. Whether participant-data AI is enabled, and if so which features are in scope.
5. Whether any contract, funder, or regulator imposes stricter rules than the default KoNote setup.