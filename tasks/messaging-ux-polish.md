# Messaging & Calendar UX Polish — Implementation Plan

Source: Two expert panel sessions (2026-02-13) assessed UX from each role's perspective and stress-tested implementation details.

## Summary

Six actionable improvements to messaging/calendar UX, grouped into two parallel batches. One recommendation (front desk message-taking) deferred to a separate feature.

---

## Batch 1 — No Dependencies, Run in Parallel

### UXP1: Add "Meetings" to Main Nav

**Problem:** The meetings dashboard (`/events/meetings/`) has no link in the main navigation. Workers can't find it.

**Changes:**

1. **`templates/base.html`** — Add nav link after Participants, before Programs:
   ```html
   {% has_permission "meeting.view" as can_see_meetings %}
   {% if can_see_meetings %}
   <li><a href="{% url 'events:meeting_list' %}"
          {% if nav_active == "meetings" %}class="nav-active" aria-current="page"{% endif %}>
       {% trans "Meetings" %}</a></li>
   {% endif %}
   ```
   - Position: immediately after the Participants `<li>` (line ~75)
   - Also add `aria-current="page"` to ALL existing nav links (currently only using CSS class, missing WCAG 2.4.5)

2. **`apps/events/views.py`** — `meeting_list` view already sets `"nav_active": "meetings"` (line 622). Confirmed.

3. **`static/js/app.js`** — Add `g m` keyboard shortcut in the `handleShortcut` function:
   ```javascript
   if (pendingKey === "g") {
       // ... existing "h" handler ...
       if (key === "m") {
           // g m = Go to Meetings
           window.location.href = "/events/meetings/";
           return true;
       }
   }
   ```

4. **`templates/base.html`** — Add to keyboard shortcuts modal:
   ```html
   <dt>g m</dt>
   <dd>{% trans "Go to Meetings" %}</dd>
   ```

5. **Mobile nav** — The `#nav-menu` mobile menu is a flex column with absolute positioning. Adding one item won't break it. No CSS changes needed — verified the menu already scrolls on mobile with `display: flex; flex-direction: column`.

**Test:** Log in as Staff, verify "Meetings" appears in nav between Participants and Programs. Log in as Front Desk/Executive, verify it does NOT appear. Test `g m` shortcut. Test mobile hamburger menu.

---

### UXP2: Success Toast for Reminder Sends

**Problem:** After sending a reminder, the HTMX swap silently updates a status badge. No visual/audible confirmation. WCAG 4.1.3 compliance gap.

**Scope:** Reminders ONLY (not quick-log — expert consensus is that the visual form swap is sufficient for quick-log; over-toasting causes toast blindness).

**Changes:**

1. **`templates/base.html`** — Add a success toast element (separate from the error toast, different ARIA role):
   ```html
   <div id="htmx-success-toast" class="toast toast-success" role="status" hidden>
       <span id="htmx-success-toast-message"></span>
       <button type="button" id="htmx-success-toast-close"
               aria-label="{% trans 'Dismiss' %}">&times;</button>
   </div>
   ```
   - `role="status"` (polite) — NOT `role="alert"` (assertive). Success messages don't interrupt.

2. **`static/css/main.css`** — Add success toast styling:
   ```css
   .toast-success {
       background-color: var(--kn-success-bg, #d4edda);
       color: var(--kn-success-text, #155724);
       border: 1px solid var(--kn-success-border, #c3e6cb);
   }
   ```

3. **`static/js/app.js`** — Add success toast handler:
   ```javascript
   // Listen for custom showSuccess event from HX-Trigger
   document.body.addEventListener("showSuccess", function(e) {
       var msg = (e.detail && e.detail.value) || e.detail || "";
       var toast = document.getElementById("htmx-success-toast");
       if (toast) {
           var msgEl = document.getElementById("htmx-success-toast-message");
           if (msgEl) msgEl.textContent = msg;
           toast.hidden = false;
           setTimeout(function() { toast.hidden = true; }, 4000);
       }
       // Also announce to screen readers
       var announcer = document.getElementById("sr-announcer");
       if (announcer) {
           announcer.textContent = "";
           setTimeout(function() { announcer.textContent = msg; }, 100);
       }
   });

   // Close button for success toast
   document.addEventListener("click", function(event) {
       if (event.target && event.target.id === "htmx-success-toast-close") {
           var toast = document.getElementById("htmx-success-toast");
           if (toast) toast.hidden = true;
       }
   });
   ```

4. **`apps/communications/views.py`** — In `send_reminder_preview` POST handler, after successful send:
   ```python
   import json
   response = render(request, "events/_meeting_status.html", {"meeting": meeting})
   response["HX-Trigger"] = json.dumps({"showSuccess": str(_("Reminder sent."))})
   return response
   ```

5. **For failed sends** — The existing status badge already shows "Reminder failed" with a red badge. No additional toast needed for errors here since the badge is visible. But do announce via `#sr-announcer` so screen readers know about the failure too.

**Test:** Send a reminder. Verify green toast appears for 4 seconds then auto-dismisses. Verify screen reader announces "Reminder sent." Test close button. Test that quick-log saves do NOT show a toast (existing behaviour preserved).

---

### UXP3: Date Format Standardisation

**Problem:** Meeting cards use `D, M d, Y — g:i A` (English-only), timeline uses `Y-m-d H:i` (ISO). Two formats on the same page. Neither handles French locale.

**Changes:**

1. **`konote/settings/base.py`** — Add locale-aware format settings:
   ```python
   # Human-readable date/time formats (used by {{ value|date }} without format arg)
   DATE_FORMAT = "N j, Y"              # "Feb. 10, 2026"
   DATETIME_FORMAT = "N j, Y, P"       # "Feb. 10, 2026, 2:30 p.m."
   SHORT_DATE_FORMAT = "Y-m-d"         # For machine contexts only
   USE_L10N = True                     # Respect locale formatting
   ```

2. **Create `konote/formats/fr/formats.py`** (if not exists):
   ```python
   DATE_FORMAT = "j N Y"               # "10 fév. 2026"
   DATETIME_FORMAT = "j N Y, H:i"      # "10 fév. 2026, 14:30"
   ```

3. **`templates/events/_meeting_card.html`** — Replace hardcoded format:
   ```html
   <!-- Before -->
   {{ meeting.event.start_timestamp|date:"D, M d, Y — g:i A" }}
   <!-- After -->
   <time datetime="{{ meeting.event.start_timestamp|date:'c' }}">{{ meeting.event.start_timestamp|date }}</time>
   ```

4. **`templates/events/_tab_events.html`** — Replace all date formats in the timeline:
   - All-day events: `{{ entry.date|date }}` (date only)
   - Timed events: `{{ entry.date|date:"DATETIME_FORMAT" }}` or just `{{ entry.date|date }}`
   - Wrap all dates in `<time datetime="...">` elements

5. **Other templates to check and fix** (search for `|date:"` across all templates):
   - `_communication_card.html`
   - `_meeting_status.html` (if any dates)
   - `event_list.html`
   - `calendar_feed_settings.html`

**Test:** Switch language to French, verify dates render in French format. Check mobile (shorter format shouldn't wrap). Verify `<time>` elements have valid ISO `datetime` attributes.

---

## Batch 2 — After Batch 1 is Merged

### UXP4: Split "New Event" into "Schedule Meeting" + "Record Event"

**Problem:** "New Event" is ambiguous — staff don't know if it means scheduling a meeting or recording that something happened. Meeting creation is buried.

**Changes:**

1. **`templates/events/_tab_events.html`** — Replace action bar:
   ```html
   <!-- Before -->
   <div class="action-bar">
       <a href="{% url 'events:event_create' ... %}" role="button">{% trans "New Event" %}</a>
       <a href="{% url 'events:alert_create' ... %}" role="button" class="outline">{% trans "New Alert" %}</a>
   </div>

   <!-- After -->
   {% has_permission "meeting.create" as can_create_meeting %}
   <div class="action-bar" role="group" aria-label="{% trans 'Actions' %}">
       {% if can_create_meeting %}
       <a href="{% url 'events:meeting_create' client_id=client.pk %}" role="button">{% trans "Schedule Meeting" %}</a>
       {% endif %}
       <a href="{% url 'events:event_create' client_id=client.pk %}" role="button" class="outline">{% trans "Record Event" %}</a>
       <a href="{% url 'events:alert_create' client_id=client.pk %}" role="button" class="outline secondary">{% trans "New Alert" %}</a>
   </div>
   ```
   - "Schedule Meeting" = primary button (most common action)
   - "Record Event" = outline button (replaces "New Event" — same destination, clearer label)
   - "New Alert" = outline secondary (infrequent, high-consequence)

2. **`apps/events/views.py`** — `meeting_create` already exists and works. No view changes.

3. **Meeting consent indicator** — In `meeting_create` view, add consent info to context:
   ```python
   context["can_send_reminders"] = (
       client.email_consent or client.sms_consent
   ) and (features.get("messaging_email") or features.get("messaging_sms"))
   ```
   In `meeting_form.html`, disable the `send_reminder` checkbox if no consent:
   ```html
   {% if not can_send_reminders %}
   <fieldset>
       <label class="secondary">
           <input type="checkbox" disabled>
           {% trans "Send reminder" %}
           <small>({% trans "Participant has not consented to reminders" %})</small>
       </label>
   </fieldset>
   {% else %}
   <!-- existing send_reminder checkbox -->
   {% endif %}
   ```

**Test:** Verify three buttons appear with correct visual hierarchy. Click "Schedule Meeting" — goes to meeting form. Click "Record Event" — goes to event form. Test consent indicator with a client who has opted out.

---

### UXP5: Timeline Filtering

**Problem:** Client timeline mixes events, notes, and communications. Becomes unmanageable after 6 months.

**Changes:**

1. **Extract `templates/events/_timeline_entries.html`** — Move the timeline loop from `_tab_events.html` into its own partial:
   ```html
   {% load i18n %}
   {% for entry in timeline %}
   <div class="timeline-item">
       <!-- existing entry rendering (event/note/communication) -->
   </div>
   {% endfor %}
   {% if not timeline %}
   <div class="empty-state">
       {% if active_filter == "notes" %}
           <p>{% trans "No progress notes recorded yet." %}</p>
       {% elif active_filter == "events" %}
           <p>{% trans "No events recorded yet." %}</p>
       {% elif active_filter == "communications" %}
           <p>{% trans "No communications logged yet." %}</p>
       {% else %}
           <p>{% trans "No events or notes recorded yet. Add events or progress notes to build a timeline." %}</p>
       {% endif %}
   </div>
   {% endif %}
   ```

2. **Update `templates/events/_tab_events.html`** — Add filter bar above timeline:
   ```html
   <h2>{% trans "Timeline" %}</h2>
   <div id="timeline-section">
       <div class="filter-bar" role="group" aria-label="{% trans 'Filter timeline' %}">
           <button class="filter-btn {% if active_filter == 'all' %}filter-active{% endif %}"
                   aria-pressed="{% if active_filter == 'all' %}true{% else %}false{% endif %}"
                   hx-get="{% url 'events:event_list' client_id=client.pk %}"
                   hx-target="#timeline-entries"
                   hx-swap="innerHTML">{% trans "All" %}</button>
           <button class="filter-btn {% if active_filter == 'notes' %}filter-active{% endif %}"
                   aria-pressed="{% if active_filter == 'notes' %}true{% else %}false{% endif %}"
                   hx-get="{% url 'events:event_list' client_id=client.pk %}?filter=notes"
                   hx-target="#timeline-entries"
                   hx-swap="innerHTML">{% trans "Notes" %}</button>
           <button class="filter-btn {% if active_filter == 'events' %}filter-active{% endif %}"
                   aria-pressed="{% if active_filter == 'events' %}true{% else %}false{% endif %}"
                   hx-get="{% url 'events:event_list' client_id=client.pk %}?filter=events"
                   hx-target="#timeline-entries"
                   hx-swap="innerHTML">{% trans "Events" %}</button>
           <button class="filter-btn {% if active_filter == 'communications' %}filter-active{% endif %}"
                   aria-pressed="{% if active_filter == 'communications' %}true{% else %}false{% endif %}"
                   hx-get="{% url 'events:event_list' client_id=client.pk %}?filter=communications"
                   hx-target="#timeline-entries"
                   hx-swap="innerHTML">{% trans "Communications" %}</button>
       </div>
       <div id="timeline-entries">
           {% include "events/_timeline_entries.html" %}
       </div>
   </div>
   ```

3. **`apps/events/views.py`** — In `event_list` view, add filter handling:
   ```python
   filter_type = request.GET.get("filter", "all")
   if filter_type == "notes":
       timeline = [e for e in timeline if e["type"] == "note"]
   elif filter_type == "events":
       timeline = [e for e in timeline if e["type"] == "event"]
   elif filter_type == "communications":
       timeline = [e for e in timeline if e["type"] == "communication"]

   # Cap at 20 entries, add "show more" support
   page_size = 20
   offset = int(request.GET.get("offset", 0))
   has_more = len(timeline) > offset + page_size
   timeline = timeline[offset:offset + page_size]

   context = {
       "timeline": timeline,
       "active_filter": filter_type,
       "has_more": has_more,
       "next_offset": offset + page_size,
       # ... existing context ...
   }

   if request.headers.get("HX-Request"):
       return render(request, "events/_timeline_entries.html", context)
   ```

4. **`static/js/app.js`** — Add generic `aria-pressed` toggle handler:
   ```javascript
   // Toggle aria-pressed on filter button groups
   document.body.addEventListener("click", function(e) {
       var btn = e.target.closest("[aria-pressed]");
       if (btn) {
           var group = btn.closest("[role='group']");
           if (group) {
               group.querySelectorAll("[aria-pressed]").forEach(function(b) {
                   b.setAttribute("aria-pressed", "false");
                   b.classList.remove("filter-active");
               });
               btn.setAttribute("aria-pressed", "true");
               btn.classList.add("filter-active");
           }
       }
   });
   ```

5. **`static/css/main.css`** — Add filter button styling:
   ```css
   .filter-bar {
       display: flex;
       gap: var(--kn-space-xs);
       margin-bottom: var(--kn-space-base);
       flex-wrap: wrap;
   }
   .filter-btn {
       padding: var(--kn-space-xs) var(--kn-space-sm);
       border: 1px solid var(--pico-muted-border-color);
       border-radius: var(--pico-border-radius);
       background: transparent;
       cursor: pointer;
       font-size: 0.875rem;
   }
   .filter-btn[aria-pressed="true"],
   .filter-btn.filter-active {
       background-color: var(--kn-primary, #0d7377);
       color: #fff;
       border-color: var(--kn-primary, #0d7377);
   }
   ```

6. **"Show more" button** at bottom of `_timeline_entries.html`:
   ```html
   {% if has_more %}
   <button class="outline secondary" style="width: 100%; margin-top: var(--kn-space-sm);"
           hx-get="{% url 'events:event_list' client_id=client.pk %}?filter={{ active_filter }}&offset={{ next_offset }}"
           hx-target="this"
           hx-swap="outerHTML">
       {% trans "Show more" %}
   </button>
   {% endif %}
   ```

**Important:** Filter does NOT persist across page loads (no session storage). Default is always "All." URL params (`?filter=notes`) support bookmarking.

**Important:** Quick-log section is ABOVE the timeline and outside `#timeline-entries`. It is NOT affected by filtering.

**Test:** Click each filter button — verify entries filter correctly. Verify empty states for each filter. Verify "Show more" loads next batch. Verify `aria-pressed` updates. Verify scroll position preserved after filter. Test with French locale.

---

### UXP6: Direction Toggle on Full Communication Log Form

**Problem:** The direction (inbound/outbound) is a hidden field in quick-log. Staff can't distinguish "they called me" from "I called them."

**Expert consensus:** Keep direction hidden in quick-log (optimised for speed, 10-20 uses/day). Add visible direction to the FULL communication log form only.

**Changes:**

1. **`templates/communications/communication_log_form.html`** — Add direction fieldset:
   ```html
   <fieldset>
       <legend>{% trans "Direction" %}</legend>
       <label>
           <input type="radio" name="direction" value="inbound"
                  {% if form.direction.value == "inbound" %}checked{% endif %}>
           {% trans "Incoming (they contacted us)" %}
       </label>
       <label>
           <input type="radio" name="direction" value="outbound"
                  {% if form.direction.value == "outbound" %}checked{% endif %}>
           {% trans "Outgoing (we contacted them)" %}
       </label>
   </fieldset>
   ```

2. **`apps/communications/forms.py`** — In `CommunicationLogForm`, ensure `direction` is a visible field (not hidden). Set default based on channel if desired.

3. **Quick-log defaults** (no UI change, just smarter defaults):
   - Phone → inbound (clients call in)
   - Text/Email → outbound (workers reach out)
   - In-person → no direction (not meaningful for walk-ins)

   In `QuickLogForm.__init__` or in the `quick_log` view, set `initial["direction"]` based on channel.

**Test:** Open full communication log form — verify direction radio buttons visible with `<fieldset>` + `<legend>`. Open quick-log — verify no direction toggle visible (hidden field only). Test each channel's default direction.

---

## Deferred — Tier 3 (Separate Feature Branch)

### Front Desk Message-Taking

**Why deferred:** The first panel underestimated the scope. Three blockers:
1. No `primary_worker` field on ClientFile — can't route messages to the right person
2. The existing quick-log form sits inside `_tab_events.html`, which shows the clinical timeline — PIPEDA violation if front desk see it
3. Without notification/flagging, logged messages get lost in timelines (digital sticky note)

**When to build:** After `primary_worker` field is added to ClientFile (prerequisite for several other features). Needs its own route, template, permission key, and notification model.

**Reference:** See expert panel notes for safe implementation design (separate `/take-message/` route, `communication.take_message` permission, no timeline access).

---

## Cross-Cutting Concerns

### aria-current="page" on All Nav Links

While adding the Meetings nav link, fix ALL existing nav links to include `aria-current="page"` when active. Currently they only use a CSS class (`nav-active`) which screen readers don't announce.

Pattern for every nav link:
```html
<a href="..."{% if nav_active == "xxx" %} class="nav-active" aria-current="page"{% endif %}>
```

### Translations

All new strings must be wrapped in `{% trans %}` or `{% blocktrans %}`. After implementation:
1. Run `python manage.py translate_strings`
2. Translate new French strings in `locale/fr/LC_MESSAGES/django.po`
3. Run `python manage.py translate_strings` again to compile
4. Commit both `.po` and `.mo`

### get_accessible_client_ids Utility

Suggested by the safety panel for future-proofing. Add to `apps/programs/access.py`:
```python
def get_accessible_client_ids(user):
    """Return queryset of client IDs accessible to user (program scope + access blocks)."""
    blocked = ClientAccessBlock.objects.filter(user=user).values_list("client_id", flat=True)
    programs = user.program_roles.filter(is_active=True).values_list("program_id", flat=True)
    return ClientFile.objects.filter(programs__in=programs).exclude(pk__in=blocked).values_list("pk", flat=True)
```

This is for the future team meeting view (Tier 3) but establishing the pattern now prevents DV-safety bugs later.

---

## Implementation Order

```
Batch 1 — All independent, run in parallel:
  UXP1  Nav link + keyboard shortcut     (~30 min)
  UXP2  Success toast for reminders      (~1.5 hours)
  UXP3  Date format standardisation      (~1.5 hours)

Batch 2 — After Batch 1 merged:
  UXP4  Button split + consent indicator (~1.5 hours)
  UXP5  Timeline filtering               (~3 hours)
  UXP6  Direction on full log form       (~30 min)

After all — Translation pass + tests
```

## Questions for User

1. **Quick-log direction:** Do your funders require reporting on inbound vs. outbound contact? If yes, we should make direction visible in quick-log too (not just the full form). If not, the quick-log stays fast with smart defaults.

2. **Meeting consent indicator:** When scheduling a meeting for someone who opted out of reminders, should the form show "reminders unavailable" upfront, or only tell you when you try to send? (Recommendation: show upfront — already designed above.)
