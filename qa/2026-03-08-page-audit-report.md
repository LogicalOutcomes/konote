# 2026-03-08 Page Audit Report

- Target: https://konote-dev.logicaloutcomes.net/
- Auditor: GitHub Copilot
- Status: Complete for this smoke-test pass
- Method: Manual click-through smoke test of accessible pages and key flows via browser automation

## Coverage log

| Area | Status | Notes |
| --- | --- | --- |
| Public pages / landing | Completed | Login, Privacy, Help, and participant safety page loaded successfully |
| Authentication flow | Completed | Demo login tested for `Alex Admin`, `Casey Worker`, and `Participant — Jordan`; sign-out works |
| In-app navigation | Completed | Admin, worker, and participant-portal route sweeps completed for key sections |
| Key forms and actions | Completed | Participant tabs, note expansion, documents external link, analytics table toggle, message read action, portal quick-exit, and portal message page tested |

## Pages / flows tested

- **Public / auth:** Login, Privacy, Help, demo account login buttons, sign-out
- **Admin routes:** Settings, Programs, Generate Report, Program Outcome Report, Team Activity, Suggestion Themes, Metric Library, Create/Edit/Import/Export Metrics, Plan Templates, Note Templates, Event Types, Surveys, Registration Links, Registration Submissions, Report Templates, Safety Oversight Reports, New Users, Audit Log, Merge Duplicates, Pending Erasure Requests
- **Worker routes:** Home dashboard, Participants list/search, Groups, Circles, Meetings, My Messages, Programs, Outcome Insights, Pending Alert Approvals, participant detail for `Jordan Rivera`, participant Plan / Notes / History / Analysis tabs, circle detail
- **Participant portal:** Home, My Goals, My Progress, Milestones, My Journal, Message My Worker, Surveys, Settings, Staying Safe Online, quick-exit button, `Resources` route

## Issues found

1. **Blank `Log Contact` save appears to succeed instead of showing validation**
	- **Where:** `https://konote-dev.logicaloutcomes.net/notes/participant/1/`
	- **Persona:** `Casey Worker`
	- **Steps:** Open participant `Jordan Rivera` → `Notes` tab → `Log Contact` → leave `Notes` empty → click `Save`
	- **Observed:** The UI shows a `Saved` confirmation instead of a required-field error or any obvious validation message.
	- **Expected:** Saving an empty contact note should either be blocked with a clear validation message or the form should explain that blank contact notes are allowed.
	- **Severity:** Medium
	- **Status:** Open

2. **Unread message total does not refresh immediately after marking a message as read**
	- **Where:** `https://konote-dev.logicaloutcomes.net/communications/my-messages/`
	- **Persona:** `Casey Worker`
	- **Steps:** Open `My Messages` → click `Mark as Read` on the first message
	- **Observed:** The message row changes to `Marked as read`, but the page summary still says `You have 3 unread messages.` until a later navigation/reload.
	- **Expected:** The unread total shown on the page should decrement immediately after a successful mark-as-read action.
	- **Severity:** Medium
	- **Status:** Open

3. **French localisation is incomplete on the Outcome Insights page**
	- **Where:** `https://konote-dev.logicaloutcomes.net/reports/insights/?program=1&time_period=6m&date_from=&date_to=`
	- **Persona:** `Casey Worker` after switching interface language to French
	- **Steps:** Open `Insights` → select `Supported Employment` → click `Show Insights` → switch to `Français`
	- **Observed:** Core UI elements translate to French, but multiple interface strings remain in English, including examples such as `3 of 3 enrolled have scores`, `8 suggestions this period`, `0 of 4 themes addressed`, and `suggestions were recorded` text.
	- **Expected:** All product UI copy on the page should appear in French when the interface language is French.
	- **Severity:** Medium
	- **Status:** Open

4. **Participant portal `Resources` page is linked in navigation but returns 404**
	- **Where:** `https://konote-dev.logicaloutcomes.net/my/resources/`
	- **Persona:** `Participant — Jordan`
	- **Steps:** Sign in via demo `Participant — Jordan` portal account → open `Resources`
	- **Observed:** The route returns HTTP 404 with `Page Not Found — KoNote`.
	- **Expected:** The `Resources` navigation item should lead to a working portal page, or the link should be hidden if the feature is not available.
	- **Severity:** High
	- **Status:** Open

5. **Participant portal quick-exit button redirects away but does not end the session**
	- **Where:** `https://konote-dev.logicaloutcomes.net/my/`
	- **Persona:** `Participant — Jordan`
	- **Steps:** In the participant portal, click `Leave quickly` → browser redirects to Google → manually return to `https://konote-dev.logicaloutcomes.net/my/`
	- **Observed:** The participant is still fully signed in. Browser console also reports `403` from `https://konote-dev.logicaloutcomes.net/my/emergency-logout/` during the quick-exit action.
	- **Expected:** A quick-exit / emergency-logout control should terminate the portal session before or while redirecting away.
	- **Severity:** High
	- **Status:** Open

## Notes / limitations

- This audit covers pages and features reachable from the deployed site during this session.
- Any areas requiring credentials, MFA, specific tenant data, or privileged roles can only be validated if accessible in-session.
- The participant `Documents` action opened an external Google Drive sign-in tab. The KoNote-side handoff worked, but the external storage destination itself could not be verified without Google authentication.
