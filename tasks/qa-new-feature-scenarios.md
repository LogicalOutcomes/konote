# QA Scenarios: Messaging, Calendar & Funder Reporting Coverage

## Summary

7 new scenarios (SCN-080 through SCN-086) covering features added in the messaging/calendar/funder-reporting wave. No existing scenarios test these features. Scenario YAML files go in **konote-qa-scenarios** repo; test methods go in **konote-app**.

## Scenarios at a Glance

| ID | Title | Type | Persona(s) | Directory |
|----|-------|------|------------|-----------|
| SCN-080 | Staff Logs a Phone Call | Daily | DS1 | scenarios/daily/ |
| SCN-081 | Schedule Meeting + Send Reminder | Daily | DS1 | scenarios/daily/ |
| SCN-082 | PM Meeting Dashboard Review | Periodic | PM1 | scenarios/periodic/ |
| SCN-083 | Calendar Feed Setup | Daily | DS1 | scenarios/daily/ |
| SCN-084 | Consent + Messaging Guardrails | Cross-role | DS1, PM1 | scenarios/cross-role/ |
| SCN-085 | Front Desk Permission Denials | Cross-role | R1, DS1 | scenarios/cross-role/ |
| SCN-086 | Funder Report + Suppression | Periodic | PM1, E1 | scenarios/periodic/ |

## Writing Order

1. SCN-085 (simplest, permission-only)
2. SCN-080 (single persona, quick-log)
3. SCN-083 (single persona, calendar)
4. SCN-081 (single persona, chains meetings + reminders)
5. SCN-082 (single persona, HTMX dashboard)
6. SCN-084 (cross-role, consent edge cases)
7. SCN-086 (cross-role, requires funder profile + confidential programme)

## URLs Referenced by New Scenarios

| URL | Feature | Used In |
|-----|---------|---------|
| `/communications/client/<id>/quick-log/` | Quick-log buttons | SCN-080, 085 |
| `/communications/client/<id>/log/` | Full comm log form | SCN-080, 084 |
| `/communications/client/<id>/meeting/<id>/send-reminder/` | Send reminder preview | SCN-081, 084 |
| `/events/meetings/` | Meeting dashboard | SCN-081, 082, 085 |
| `/events/client/<id>/meetings/create/` | Quick-create meeting | SCN-081 |
| `/events/meetings/<id>/status/` | HTMX status update | SCN-082 |
| `/events/calendar/settings/` | Calendar feed token | SCN-083, 085 |
| `/calendar/<token>/feed.ics` | iCal feed (public) | SCN-083 |
| `/reports/funder-report/` | Funder report form | SCN-086 |

## Permissions Tested

| Permission | Role | Level | Scenario |
|-----------|------|-------|----------|
| communication.log | Staff | SCOPED (200) | SCN-080, 084 |
| communication.log | Front desk | DENY (403) | SCN-085 |
| communication.view | PM | ALLOW (200) | SCN-084 |
| communication.view | Front desk | DENY (403) | SCN-085 |
| event.create | Staff | SCOPED (200) | SCN-081 |
| meeting.view | Staff | SCOPED (200) | SCN-081, 085 |
| meeting.view | PM | ALLOW (200) | SCN-082 |
| meeting.view | Front desk | DENY (403) | SCN-085 |
| report.funder_report | PM | ALLOW (200) | SCN-086 |
| report.funder_report | Executive | ALLOW (200) | SCN-086 |

## Prerequisite Data Requirements

### Existing (already in seed_demo_data)
- Staff user ("staff") with Housing Support programme
- PM user ("manager") with Housing Support programme
- Front desk user ("frontdesk") with Housing Support programme
- Executive user ("executive")
- Demo clients (DEMO-001 through DEMO-015)
- Demo meetings (10 meetings across statuses)
- Demo communications (various channels)
- Calendar feed tokens for demo workers

### Needed (verify or add to seed_demo_data)
- Client with no phone number and no email (for SCN-084 step 1)
- Client with SMS consent explicitly withdrawn (`sms_consent=False`, `sms_consent_withdrawn_date` set) for SCN-084 step 2
- A confidential programme (`is_confidential=True`) with <5 clients for SCN-086 step 3
- At least one uploaded funder profile with custom age bins for SCN-086

## Test Methods (in konote-app)

Add to `tests/scenario_eval/test_scenario_eval.py`:

**TestDailyScenarios:**
- `test_quick_log_phone_call` (SCN-080)
- `test_schedule_meeting_reminder` (SCN-081)
- `test_calendar_feed_setup` (SCN-083)

**TestPeriodicScenarios:**
- `test_meeting_dashboard_review` (SCN-082)
- `test_funder_report_suppression` (SCN-086)

**TestCrossRoleScenarios:**
- `test_messaging_consent_blocks` (SCN-084)
- `test_front_desk_messaging_denied` (SCN-085)

## Dependencies and Notes

- All 7 scenarios are independent of each other (no cascading dependencies)
- SCN-086 depends on funder profile data existing in seed
- SCN-084 requires specific consent states on clients
- After writing scenarios, update `pages/page-inventory.yaml` in qa-scenarios repo with new pages: meeting_list, meeting_form, calendar_settings, quick_log, send_reminder_preview
- SCN-081 is a strong candidate for the smoke test subset in a future round
