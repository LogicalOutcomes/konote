# Research: Session Reporting Requirements for Canadian Nonprofits (REP-REQ1)

*Completed 2026-02-24*

## Purpose

Identify what session-level data Canadian nonprofit funders typically require, so KoNote can design a flexible "Sessions by Participant" report template.

---

## Common Fields Across All Funders

| Field | Frequency | IRCC | Empl. ON | CFPB | United Way | Notes |
|-------|-----------|------|----------|------|------------|-------|
| **Session date** | Universal | Y | Y | Y | Y | Always required |
| **Session duration** | Universal | Y | -- | Y | -- | Hours or minutes; needed for dosage calculations |
| **Session type / template** | Universal | Y | Y | Y | Y | What kind of session (coaching, intake, check-in, crisis, tax clinic) |
| **Service modality** | Common | Y | -- | Y | -- | In-person, phone, video, text/email |
| **Group vs. individual** | Common | Y | -- | -- | Y | Needed for session counts and cost-per-client |
| **Service provider / coach** | Common | Y | -- | Y | -- | Who delivered the session |
| **Topics covered** | Common | Y | Y | Y | -- | Categorised from a predefined list |
| **Goals reviewed / set** | Common | -- | Y | Y | -- | Links sessions to participant goals |
| **Follow-up needed** | Recommended | -- | -- | Y | -- | Flags for next action |
| **Referrals made** | Common | Y | -- | -- | -- | Where was the participant referred |
| **Language of service** | Common | Y | -- | -- | -- | Canada-specific; bilingual reporting |
| **Location / site** | Recommended | Y | -- | -- | -- | Multi-site agencies need this |
| **Support services** | Recommended | Y | -- | -- | -- | Childcare, transportation provided |
| **Attendance / no-show** | Recommended | -- | Y | -- | Y | Needed for dosage and engagement metrics |
| **Session notes / summary** | Recommended | -- | -- | Y | -- | Narrative context |

---

## Funder-Specific Details

### IRCC / iCARE

IRCC-funded settlement agencies report monthly through iCARE. Key data elements per service record:

- Date of service (must be closed and reported by month-end; no "ongoing" status)
- Duration (hours/days — RAP module shifted from date-based to duration-based in 2025)
- Service stream (six streams: Needs Assessment, Information & Orientation, Language Assessment, Language Training, Employment-Related Services, Community Connections)
- Activity type (classified within each service stream)
- Service modality (group vs. individual; in-person vs. remote)
- Organisation / location
- Language of service
- Support services received (childcare, transportation, translation)
- Referrals made (categorised by topic)
- Client identifier (one service record per month per client per activity)

As of 2025, backdated data is limited to 30 days (down from 90).

### Employment Ontario (EOIS-CaMS)

- Activity date (real-time entry expected; cases marked "inactive" after 60 days without activity)
- Activity/plan item type (varies by program stream)
- Service plan linkage (each activity tied to a service plan with defined goals)
- Completion status
- Data quality reporting

### CFPB Financial Coaching Initiative

The U.S. CFPB model is the most referenced for financial coaching programs in Canada:

- Session date
- Session format/modality (in-person avg. 64 min vs. phone avg. 34 min)
- Session duration (minutes)
- Topics covered (from predefined list: budgeting, credit, savings, goals, etc.)
- Goals set/reviewed (over 48,000 goals recorded across the study)
- Financial Capability Scale score (5-item FCS administered periodically)
- Financial outcome data (credit scores, savings levels, debt levels)

### United Way / General Canadian Funders

Logic-model-based reporting, typically aggregate:

- Total sessions delivered
- Unique participants served
- Sessions per participant (dosage/intensity)
- Service type/category
- Outcome indicators (pre/post measures)
- Demographic breakdowns

---

## Canada-Specific Requirements

- **Language of service**: Required by IRCC and relevant to any bilingual program
- **PIPEDA consent**: Session data containing personal information requires documented consent
- **Quarterly and monthly cadences**: IRCC requires monthly; most other funders require quarterly
- **AODA accessibility**: Reports must be accessible (web views and exported PDFs/CSVs)
- **Multi-site tracking**: Many Canadian agencies operate from multiple locations
- **Support services provided**: IRCC tracks whether childcare, transportation, or interpretation was provided

---

## What KoNote Already Has vs. What It Needs

| Capability | Current State | Gap |
|------------|--------------|-----|
| Session date | Captured (note timestamp) | None |
| Session type | Captured (note template name) | None |
| Session duration | **Not captured** | **Add optional duration field to note form** |
| Service modality | **Not captured** | **Add modality dropdown to note form** |
| Coach/provider | Captured (note author) | None |
| Participant linkage | Captured (note linked to participant) | None |
| Topics/goals | Partially captured (note sections reference goals) | Could add structured topic tags |
| Language of service | **Not captured on notes** | **Add if IRCC reporting needed** |
| Location/site | **Not captured on notes** | **Add if multi-site** |
| Report export | CSV and PDF exist | Need new "Sessions by Participant" report type |

---

## Recommendations for "Sessions by Participant" Report

### Core fields (always include)

1. Participant name / ID (row grouping)
2. Session date
3. Session type (maps to existing note templates)
4. Session duration (minutes or hours)
5. Service modality (in-person, phone, video, text/email)
6. Coach / service provider

### Summary statistics per participant

7. Total sessions (count)
8. Total contact hours (sum of duration)
9. Date of first session
10. Date of most recent session
11. Days in program (first session to most recent or discharge)

### Optional columns (configurable per agency)

12. Topics covered (from a tag or category list)
13. Language of service
14. Location / site
15. Group vs. individual
16. Referrals made
17. Follow-up status (open / completed)
18. Support services provided (childcare, transportation, interpretation)

### Report-level aggregates (footer or summary page)

- Total unique participants
- Total sessions across all participants
- Average sessions per participant
- Average contact hours per participant
- Distribution by session type
- Distribution by modality

### Design principles

- **Filterable** by date range, program, coach, and session type (supports both monthly and quarterly reporting)
- **Exportable** to CSV and PDF
- **Note template as session type** — avoids adding a separate field
- **Duration and modality** are the two most important missing fields to add

---

## Key Takeaway

The two most universally required session fields that KoNote does not yet capture are **session duration** and **service modality**. Adding these two fields to the note form (as optional inputs) would unlock reporting for virtually every Canadian funder. Everything else is already captured through the existing Progress Note system.

---

## Sources

- [IRCC iCARE Privacy Impact Assessment](https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/access-information-privacy/privacy-impact-assessment/immigration-contribution-agreement-reporting-environment.html)
- [IRCC Settlement Program Core Data Sources (PDF)](https://www.canada.ca/content/dam/ircc/documents/pdf/english/corporate/settlement-resettlement-service-provider-information/data-research-reports/core-data-sources-settlement-resettlement.pdf)
- [IRCC Outcomes and Measurement Guidance](https://www.canada.ca/en/immigration-refugees-citizenship/corporate/partners-service-providers/funding/outcome-guidance.html)
- [CARMIS iCARE 2025 Updates](https://carmis.ca/knowledge-base/ircc-2025-updates-carmis-compliance-march-4-2025/)
- [EOIS-CaMS User Guide (PDF)](https://cesba.com/wp-content/uploads/2021/06/EOIS-CaMS-Case-Management-System-Service-Provider-User-Guide-2.pdf)
- [CFPB Financial Coaching Initiative Results](https://www.consumerfinance.gov/data-research/research-reports/financial-coaching-initiative-results-and-lessons-learned/)
- [CFPB Guide to Remote Financial Coaching](https://www.consumerfinance.gov/data-research/research-reports/guide-to-remote-financial-coaching/)
- [United Way Outcome Measurement Guide (PDF)](https://www.yourunitedway.org/wp-content/uploads/2015/12/UWGRP-Guide-to-Outcomes-and-Logic-Models-6-8-15.pdf)
- [Salesforce Nonprofit Cloud Case Management Objects](https://developer.salesforce.com/docs/atlas.en-us.nonprofit_cloud.meta/nonprofit_cloud/npc_case_management_objects.htm)
- [IRCC Settlement Program Evaluation](https://www.canada.ca/en/immigration-refugees-citizenship/corporate/reports-statistics/evaluations/settlement-program.html)
