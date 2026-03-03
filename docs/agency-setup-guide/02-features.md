# 02 — Features & Modules

## What This Configures

KoNote is modular — you enable only the features your agency needs and disable the rest. This keeps the interface clean for staff and avoids confusion from features that are not relevant to your work. Features can be toggled on or off at any time without losing data.

## Decisions Needed

1. **Do you organise services into distinct programs?**
   - Yes → enable "Programs" (distinct service lines with their own staff, templates, and metrics)
   - No → disable if everything is one service; participants are not separated by program
   - Default: On

2. **Do you need extra data fields on participant files beyond name, contact, and demographics?**
   - Yes → enable "Custom Participant Fields" (e.g., funding source, referral date, income level)
   - No → the standard participant form is sufficient
   - Default: Off

3. **Do you run group sessions and need to track attendance?**
   - Yes → enable "Groups" (group session recording, attendance tracking, membership)
   - No → disable if all your work is one-on-one
   - Default: On

4. **Do you want to track significant events like intake, discharge, and crises?**
   - Yes → enable "Event Tracking" (record intake, discharge, crisis, and other events on a participant's timeline)
   - No → disable if you do not need a formal event timeline
   - Default: On

5. **Do you need lightweight contact logging for phone calls, texts, and emails?**
   - Yes → enable "Quick Notes" (brief contact records outside of formal session notes)
   - No → disable if all contacts are documented as full notes
   - Default: On

6. **Do you want progress visualisation charts on participant files?**
   - Yes → enable "Analysis Charts" (visual progress charts showing outcome trends over time)
   - No → disable if you prefer to review data in tables or reports only
   - Default: On

7. **Do you want staff to be alerted when outcome metrics hit certain thresholds?**
   - Yes → enable "Metric Alerts" (automatic notifications when a participant's score crosses a threshold)
   - No → disable if staff review metrics manually
   - Default: Off

8. **Do you need formatted outcome reports for funders?**
   - Yes → enable "Program Reports" (generate formatted reports with demographic breakdowns and outcome summaries)
   - No → disable if you report to funders through other channels
   - Default: Off

9. **Do you require documented participant consent before creating notes?**
   - Yes → enable "Consent Requirement" (PIPEDA/PHIPA consent checkbox on notes)
   - No → disable if consent is managed outside the system
   - Default: On

10. **Do you want to send email reminders or messages to participants?**
    - Yes → enable "Email Messaging" (requires SMTP configuration — your IT contact will need to provide email server details)
    - No → disable if you contact participants outside the system
    - Default: Off

11. **Do you want to send SMS text message reminders to participants?**
    - Yes → enable "SMS Messaging" (requires a Twilio account — a messaging service with per-message costs)
    - No → disable if you do not text participants
    - Default: Off

12. **Do you want participants to see their own goals, progress, and journal through a secure portal?**
    - Yes → enable "Participant Portal" (separate secure login with multi-factor authentication)
    - No / Later → disable until you are ready to set up the portal experience
    - Default: Off
    - If enabled, also decide on sub-features:
      - "Portal Journal" — participants can keep a private journal (Default: On when portal is enabled)
      - "Portal Messaging" — participants can send messages to their worker (Default: On when portal is enabled)

13. **Do you want to collect structured feedback through surveys?**
    - Yes → enable "Surveys" (create surveys with automatic assignment rules, scoring, and shareable links)
    - No → disable if you collect feedback through other tools
    - Default: Off
    - Note: Surveys work on their own, but if the participant portal is also enabled, participants can fill in surveys through the portal.

14. **Do you want AI-powered features like goal suggestions and narrative generation?**
    - Yes → enable "AI Assist" (requires an OpenRouter API key — a service that connects to language models)
    - No → disable if you prefer fully manual workflows or have concerns about AI and participant data
    - Default: Off

## Common Configurations

- **Financial coaching agency (small, no portal):** Programs On, Custom Fields On, Groups Off, Events On, Quick Notes On, Charts On, Metric Alerts Off, Program Reports On, Consent On, Email Off, SMS Off, Portal Off, Surveys Off, AI Off
- **Community counselling agency:** Programs On, Custom Fields On, Groups On, Events On, Quick Notes On, Charts On, Metric Alerts Off, Program Reports On, Consent On, Email On, SMS Off, Portal Off, Surveys Off, AI Off
- **Youth drop-in centre:** Programs On, Custom Fields Off, Groups On, Events On, Quick Notes On, Charts Off, Metric Alerts Off, Program Reports Off, Consent Off, Email Off, SMS Off, Portal Off, Surveys Off, AI Off
- **Multi-service agency with portal:** Programs On, Custom Fields On, Groups On, Events On, Quick Notes On, Charts On, Metric Alerts On, Program Reports On, Consent On, Email On, SMS On, Portal On (with Journal and Messaging), Surveys On, AI Off

## Output Format

Features are toggled through the KoNote admin interface or through the `apply_setup` management command.

**Admin interface steps:**
1. Click the gear icon, then "Features"
2. Toggle each feature on or off
3. Click "Save"

Disabling a feature hides it from the interface but preserves all associated data. You can re-enable it later and everything will still be there.

**Feature dependency map:** Some features depend on others.

```
participant_portal
  +-- portal_journal
  +-- portal_messaging
  +-- surveys (portal survey section)

messaging_sms
  requires: Twilio account credentials

messaging_email
  requires: SMTP email server configuration

program_reports
  enhanced_by: ai_assist (AI narrative generation)
```

## Dependencies

- **Requires:** Nothing — features can be toggled independently of other configuration
- **Feeds into:** Document 03 (Roles & Permissions) — the features you enable affect what permissions are relevant. Document 08 (Users) — messaging features require technical setup before user accounts are created.

## Example: Financial Coaching Agency

**Decisions:**
- Programs: On (three coaching programs with different funders)
- Custom Participant Fields: On (funding source, referral source, income bracket)
- Groups: Off (all work is one-on-one coaching)
- Event Tracking: On (track intake, discharge, milestones)
- Quick Notes: On (coaches log phone calls between sessions)
- Analysis Charts: On (visual progress tracking for coaching reviews)
- Metric Alerts: Off (coaches review metrics during sessions, not through alerts)
- Program Reports: On (quarterly funder reports required)
- Consent Requirement: On (standard PIPEDA practice)
- Email Messaging: Off (for now — may enable later for appointment reminders)
- SMS Messaging: Off (participants prefer phone calls)
- Participant Portal: Off (planned for Phase 2 after staff are comfortable)
- Surveys: Off (feedback collected through coaching conversations)
- AI Assist: Off (agency wants to evaluate AI policy first)

**Rationale:** This configuration keeps the interface focused on what coaches use daily — notes, plans, and metrics — without cluttering it with group tracking, surveys, or messaging features they do not need yet. Program Reports are on because the funder requires quarterly outcome reports.
