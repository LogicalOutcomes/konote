# Messages Page UX Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the Messages page so staff can instantly see who left a message, how recently, and whether it's urgent.

**Architecture:** Add `is_urgent` field to StaffMessage model. Rework card templates to lead with sender name and add relative timestamps via a small vanilla JS function. Add CSS for urgent indicator and team/direct message distinction.

**Tech Stack:** Django 5 templates, HTMX, Pico CSS, vanilla JS, Django `timesince` for server fallback

**Design doc:** `docs/plans/2026-02-19-messages-ux-design.md`

---

### Task 1: Add `is_urgent` field to StaffMessage model

**Files:**
- Modify: `apps/communications/models.py` (StaffMessage class, around line 186)
- Create: new migration via `makemigrations`

**Step 1: Write the failing test**

Add to `tests/test_communications.py`:

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class StaffMessageModelTest(TestCase):
    """Test StaffMessage model fields and behaviour."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        self.staff = User.objects.create_user(
            username="test_staff_msg", password="testpass123", display_name="Test Staff",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_is_urgent_defaults_to_false(self):
        from apps.communications.models import StaffMessage
        msg = StaffMessage(client_file=self.client_file, left_by=self.staff)
        msg.content = "Test message"
        msg.save()
        msg.refresh_from_db()
        self.assertFalse(msg.is_urgent)

    def test_is_urgent_can_be_set_true(self):
        from apps.communications.models import StaffMessage
        msg = StaffMessage(client_file=self.client_file, left_by=self.staff, is_urgent=True)
        msg.content = "Urgent test"
        msg.save()
        msg.refresh_from_db()
        self.assertTrue(msg.is_urgent)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_communications.py::StaffMessageModelTest -v`
Expected: FAIL — `StaffMessage` has no field `is_urgent`

**Step 3: Add `is_urgent` field to the model**

In `apps/communications/models.py`, add after `read_at` field (line ~228):

```python
    is_urgent = models.BooleanField(
        default=False,
        help_text=_("Flag this message as urgent — shown at top of inbox"),
    )
```

**Step 4: Create and apply migration**

Run: `python manage.py makemigrations communications && python manage.py migrate`
Expected: Migration created and applied successfully

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_communications.py::StaffMessageModelTest -v`
Expected: PASS (both tests)

**Step 6: Commit**

```bash
git add apps/communications/models.py apps/communications/migrations/ tests/test_communications.py
git commit -m "feat(messages): add is_urgent field to StaffMessage model"
```

---

### Task 2: Add `is_urgent` to StaffMessageForm

**Files:**
- Modify: `apps/communications/forms.py` (StaffMessageForm class, around line 187)
- Test: `tests/test_communications.py`

**Step 1: Write the failing test**

Add to `tests/test_communications.py`:

```python
from apps.communications.forms import StaffMessageForm

class StaffMessageFormTest(TestCase):
    """Test StaffMessageForm validation."""

    def test_valid_with_urgent_flag(self):
        form = StaffMessageForm(
            data={"message": "Please call back ASAP", "is_urgent": True},
            staff_choices=[], worker_term="worker",
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["is_urgent"])

    def test_urgent_defaults_to_false(self):
        form = StaffMessageForm(
            data={"message": "Regular message"},
            staff_choices=[], worker_term="worker",
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["is_urgent"])

    def test_valid_without_urgent(self):
        form = StaffMessageForm(
            data={"message": "No rush"},
            staff_choices=[], worker_term="worker",
        )
        self.assertTrue(form.is_valid(), form.errors)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_communications.py::StaffMessageFormTest -v`
Expected: FAIL — `is_urgent` not in form fields

**Step 3: Add `is_urgent` field to StaffMessageForm**

In `apps/communications/forms.py`, add to `StaffMessageForm` class after `for_user`:

```python
    is_urgent = forms.BooleanField(
        required=False,
        label=_("Mark as urgent"),
        help_text=_("Urgent messages appear at the top of the inbox."),
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_communications.py::StaffMessageFormTest -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add apps/communications/forms.py tests/test_communications.py
git commit -m "feat(messages): add is_urgent checkbox to StaffMessageForm"
```

---

### Task 3: Wire `is_urgent` into the leave_message view

**Files:**
- Modify: `apps/communications/views.py` (leave_message function, around line 297)
- Test: `tests/test_communications.py`

**Step 1: Write the failing test**

Add to `tests/test_communications.py`:

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LeaveMessageViewTest(TestCase):
    """Test the leave_message view — creating staff messages."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        self.staff = User.objects.create_user(
            username="test_staff_lm", password="testpass123", display_name="Test Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_post_creates_message(self):
        from apps.communications.models import StaffMessage
        self.client.login(username="test_staff_lm", password="testpass123")
        url = f"/communications/participant/{self.client_file.pk}/leave-message/"
        response = self.client.post(url, {"message": "Call back please"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StaffMessage.objects.count(), 1)
        msg = StaffMessage.objects.first()
        self.assertEqual(msg.content, "Call back please")
        self.assertFalse(msg.is_urgent)

    def test_post_creates_urgent_message(self):
        from apps.communications.models import StaffMessage
        self.client.login(username="test_staff_lm", password="testpass123")
        url = f"/communications/participant/{self.client_file.pk}/leave-message/"
        response = self.client.post(url, {"message": "Emergency!", "is_urgent": "on"})
        self.assertEqual(response.status_code, 302)
        msg = StaffMessage.objects.first()
        self.assertTrue(msg.is_urgent)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_communications.py::LeaveMessageViewTest -v`
Expected: `test_post_creates_urgent_message` FAIL — `is_urgent` not saved

**Step 3: Wire `is_urgent` into the view**

In `apps/communications/views.py`, in the `leave_message` function, update the message creation (around line 333-339). After `msg.author_program = ...`, add:

```python
            msg.is_urgent = form.cleaned_data.get("is_urgent", False)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_communications.py::LeaveMessageViewTest -v`
Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add apps/communications/views.py tests/test_communications.py
git commit -m "feat(messages): save is_urgent flag from leave_message form"
```

---

### Task 4: Update `my_messages` view — urgent-first sorting

**Files:**
- Modify: `apps/communications/views.py` (my_messages function, around line 423)
- Test: `tests/test_communications.py`

**Step 1: Write the failing test**

Add to `tests/test_communications.py`:

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MyMessagesViewTest(TestCase):
    """Test the my_messages dashboard view."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        self.staff = User.objects.create_user(
            username="test_staff_mm", password="testpass123", display_name="Test Staff",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff", status="active",
        )
        self.sender = User.objects.create_user(
            username="test_sender", password="testpass123", display_name="Sender",
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_urgent_messages_sorted_first(self):
        from apps.communications.models import StaffMessage
        # Create regular message first (older)
        regular = StaffMessage(client_file=self.client_file, left_by=self.sender, for_user=self.staff)
        regular.content = "Regular message"
        regular.save()
        # Create urgent message second (newer, but urgent should be first regardless)
        urgent = StaffMessage(client_file=self.client_file, left_by=self.sender, for_user=self.staff, is_urgent=True)
        urgent.content = "Urgent message"
        urgent.save()

        self.client.login(username="test_staff_mm", password="testpass123")
        response = self.client.get("/communications/my-messages/")
        self.assertEqual(response.status_code, 200)
        msgs = list(response.context["staff_messages"])
        self.assertTrue(msgs[0].is_urgent)
        self.assertFalse(msgs[1].is_urgent)

    def test_my_messages_returns_200(self):
        self.client.login(username="test_staff_mm", password="testpass123")
        response = self.client.get("/communications/my-messages/")
        self.assertEqual(response.status_code, 200)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_communications.py::MyMessagesViewTest -v`
Expected: `test_urgent_messages_sorted_first` FAIL — messages not sorted by urgency

**Step 3: Add urgent-first sort to my_messages view**

In `apps/communications/views.py`, in the `my_messages` function, change the queryset (around line 437-442). Add `.order_by("-is_urgent", "-created_at")` to the chain:

```python
    staff_messages = StaffMessage.objects.filter(
        client_file_id__in=accessible_client_ids,
        status="unread",
    ).filter(
        db_models.Q(for_user=request.user) | db_models.Q(for_user__isnull=True)
    ).select_related("left_by", "for_user", "client_file").order_by("-is_urgent", "-created_at")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_communications.py::MyMessagesViewTest -v`
Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add apps/communications/views.py tests/test_communications.py
git commit -m "feat(messages): sort urgent messages first on My Messages"
```

---

### Task 5: Add CSS for urgent indicator and message card styles

**Files:**
- Modify: `static/css/theme.css` (add `--kn-urgent` variable)
- Modify: `static/css/main.css` (add message card styles)

**Step 1: Add `--kn-urgent` CSS variable to theme.css**

In `static/css/theme.css`, inside the `:root` block, add after the danger variables (around line 29):

```css
    --kn-urgent: #c0392b;
    --kn-urgent-bg: rgba(192, 57, 43, 0.06);
```

**Step 2: Add message card styles to main.css**

Append to `static/css/main.css`:

```css
/* ---- Staff messages — card styles ---- */
.message-card {
    border-left: 4px solid transparent;
}
.message-card.message-urgent {
    border-left-color: var(--kn-urgent);
    background: var(--kn-urgent-bg);
}
.message-card .urgent-label {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--kn-urgent);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-left: var(--kn-space-sm);
}
.message-card.message-team {
    opacity: 0.85;
}
.message-card .message-meta {
    color: var(--kn-text-muted);
    font-size: 0.875rem;
}
.message-card .message-meta a {
    color: var(--kn-text-secondary);
}
```

**Step 3: Commit**

```bash
git add static/css/theme.css static/css/main.css
git commit -m "feat(messages): add CSS for urgent indicator and card styles"
```

---

### Task 6: Add relative timestamp JS to app.js

**Files:**
- Modify: `static/js/app.js`

**Step 1: Add relativeTime function to app.js**

Add the following at the end of `static/js/app.js`:

```javascript
// --- Relative timestamps for <time> elements ---
// Updates elements with data-relative attribute to show "2 hours ago" etc.
// Falls back to absolute date if JS disabled (server renders it).
(function () {
    function updateRelativeTimes() {
        var times = document.querySelectorAll("time[data-relative]");
        var now = Date.now();
        times.forEach(function (el) {
            var dt = new Date(el.getAttribute("datetime"));
            if (isNaN(dt)) return;
            var diff = Math.floor((now - dt) / 1000);
            var text;
            if (diff < 60) text = t("just_now", "just now");
            else if (diff < 3600) {
                var m = Math.floor(diff / 60);
                text = m === 1 ? t("one_min_ago", "1 minute ago") : m + " " + t("mins_ago", "minutes ago");
            } else if (diff < 86400) {
                var h = Math.floor(diff / 3600);
                text = h === 1 ? t("one_hour_ago", "1 hour ago") : h + " " + t("hours_ago", "hours ago");
            } else if (diff < 604800) {
                var d = Math.floor(diff / 86400);
                text = d === 1 ? t("one_day_ago", "1 day ago") : d + " " + t("days_ago", "days ago");
            } else {
                return; // older than 7 days — keep absolute date
            }
            el.textContent = text;
        });
    }
    updateRelativeTimes();
    setInterval(updateRelativeTimes, 60000);
    document.body.addEventListener("htmx:afterSwap", updateRelativeTimes);
})();
```

**Step 2: Commit**

```bash
git add static/js/app.js
git commit -m "feat(messages): add relative timestamp updater for time elements"
```

---

### Task 7: Rework templates — My Messages page

**Files:**
- Create: `templates/communications/_my_message_card.html`
- Modify: `templates/communications/my_messages.html`

**Step 1: Create `_my_message_card.html` partial**

Create `templates/communications/_my_message_card.html`:

```html
{% load i18n %}
<article id="message-{{ msg.pk }}" class="message-card{% if msg.is_urgent %} message-urgent{% endif %}{% if not msg.for_user %} message-team{% endif %}">
    <header>
        <h2>
            {% if msg.left_by %}{{ msg.left_by.display_name }}{% else %}{% trans "Unknown" %}{% endif %}
            {% if msg.is_urgent %}<span class="urgent-label" aria-hidden="true">{% trans "Urgent" %}</span>{% endif %}
        </h2>
        {% if msg.is_urgent %}<span class="sr-only">{% trans "Urgent" %}</span>{% endif %}
        <div class="message-meta">
            {% if msg.for_user %}
                {% blocktrans with name=msg.for_user.display_name %}For: {{ name }}{% endblocktrans %}
            {% else %}
                {% blocktrans with worker=term.worker|default:"worker" %}For: Any {{ worker }}{% endblocktrans %}
                <span class="sr-only">({% trans "team message" %})</span>
            {% endif %}
            &middot;
            {% trans "About" %}:
            <a href="{% url 'clients:client_detail' client_id=msg.client_file.pk %}">{{ msg.client_file.display_name }} {{ msg.client_file.last_name }}</a>
            &middot;
            <time datetime="{{ msg.created_at|date:'c' }}" title="{{ msg.created_at|date:'SHORT_DATETIME_FORMAT' }}" data-relative>
                {{ msg.created_at|date:"SHORT_DATETIME_FORMAT" }}
            </time>
        </div>
    </header>

    <p>{{ msg.content|truncatewords:50 }}</p>

    {% if msg.status == "unread" %}
    <footer>
        <form method="post"
              action="{% url 'communications:mark_message_read' client_id=msg.client_file.pk message_id=msg.pk %}"
              hx-post="{% url 'communications:mark_message_read' client_id=msg.client_file.pk message_id=msg.pk %}"
              hx-target="#message-{{ msg.pk }}"
              hx-swap="outerHTML">
            {% csrf_token %}
            <button type="submit" class="secondary outline">{% trans "Mark as Read" %}</button>
        </form>
    </footer>
    {% endif %}
</article>
```

**Step 2: Update `my_messages.html` to use the new partial**

Replace the inline card loop in `templates/communications/my_messages.html`:

```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}{% trans "My Messages" %}{% endblock %}

{% block content %}
<h1>{% trans "My Messages" %}</h1>

{% if staff_messages %}
    <p>{% blocktrans with count=staff_messages|length %}You have {{ count }} unread message(s).{% endblocktrans %}</p>
    {% for msg in staff_messages %}
        {% include "communications/_my_message_card.html" %}
    {% endfor %}
{% else %}
    <p>{% trans "No unread messages." %}</p>
{% endif %}
{% endblock %}
```

**Step 3: Commit**

```bash
git add templates/communications/_my_message_card.html templates/communications/my_messages.html
git commit -m "feat(messages): rework My Messages card layout — sender first, urgent indicator"
```

---

### Task 8: Update `_message_card.html` — Client Messages context

**Files:**
- Modify: `templates/communications/_message_card.html`

**Step 1: Update the partial with proper heading, urgent indicator, and timestamp**

Replace `templates/communications/_message_card.html`:

```html
{% load i18n %}
<article id="message-{{ msg.pk }}" class="message-card{% if msg.is_urgent %} message-urgent{% endif %}{% if not msg.for_user %} message-team{% endif %}">
    <header>
        <h3>
            {% if msg.left_by %}{{ msg.left_by.display_name }}{% else %}{% trans "Unknown" %}{% endif %}
            {% if msg.is_urgent %}<span class="urgent-label" aria-hidden="true">{% trans "Urgent" %}</span>{% endif %}
        </h3>
        {% if msg.is_urgent %}<span class="sr-only">{% trans "Urgent" %}</span>{% endif %}
        <div class="message-meta">
            {% if msg.for_user %}
                {% blocktrans with name=msg.for_user.display_name %}For: {{ name }}{% endblocktrans %}
            {% else %}
                {% blocktrans with worker=term.worker|default:"worker" %}For: Any {{ worker }}{% endblocktrans %}
            {% endif %}
            &middot;
            <time datetime="{{ msg.created_at|date:'c' }}" title="{{ msg.created_at|date:'SHORT_DATETIME_FORMAT' }}" data-relative>
                {{ msg.created_at|date:"SHORT_DATETIME_FORMAT" }}
            </time>
        </div>
    </header>

    <p>{{ msg.content }}</p>

    {% if msg.status == "unread" %}
        <footer>
            <form method="post"
                  action="{% url 'communications:mark_message_read' client_id=client.pk message_id=msg.pk %}"
                  hx-post="{% url 'communications:mark_message_read' client_id=client.pk message_id=msg.pk %}"
                  hx-target="#message-{{ msg.pk }}"
                  hx-swap="outerHTML">
                {% csrf_token %}
                <button type="submit" class="secondary outline">{% trans "Mark as Read" %}</button>
            </form>
        </footer>
    {% elif msg.read_at %}
        <footer>
            <small>{% trans "Read" %}
                <time datetime="{{ msg.read_at|date:'c' }}" title="{{ msg.read_at|date:'SHORT_DATETIME_FORMAT' }}" data-relative>
                    {{ msg.read_at|date:"SHORT_DATETIME_FORMAT" }}
                </time>
            </small>
        </footer>
    {% endif %}
</article>
```

**Step 2: Commit**

```bash
git add templates/communications/_message_card.html
git commit -m "feat(messages): update client message card — sender heading, urgent indicator, relative time"
```

---

### Task 9: Update `leave_message.html` — add urgent checkbox

**Files:**
- Modify: `templates/communications/leave_message.html`

**Step 1: Add the urgent checkbox to the form**

In `templates/communications/leave_message.html`, add after the message textarea block (after `{% endif %}` for message errors, before `<div class="button-row">`):

```html
    <label>
        {{ form.is_urgent }} {{ form.is_urgent.label }}
    </label>
    <small>{{ form.is_urgent.help_text }}</small>
```

**Step 2: Commit**

```bash
git add templates/communications/leave_message.html
git commit -m "feat(messages): add urgent checkbox to leave message form"
```

---

### Task 10: Focus management after Mark as Read

**Files:**
- Modify: `static/js/app.js`

**Step 1: Add HTMX afterSwap handler for focus management**

Add to `static/js/app.js`:

```javascript
// --- Focus management: after marking a message read, focus next unread ---
document.body.addEventListener("htmx:afterSwap", function (event) {
    var swapped = event.detail.target;
    if (!swapped || !swapped.classList || !swapped.classList.contains("message-card")) return;
    // Find the next unread message card
    var next = swapped.nextElementSibling;
    while (next && !next.querySelector("button[type='submit']")) {
        next = next.nextElementSibling;
    }
    if (next) {
        next.setAttribute("tabindex", "-1");
        next.focus();
    }
});
```

**Step 2: Commit**

```bash
git add static/js/app.js
git commit -m "feat(messages): add focus management after marking message read"
```

---

### Task 11: French translations

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

**Step 1: Run extract to pick up new template strings**

Run: `python manage.py translate_strings`

**Step 2: Add French translations for new strings**

New strings to translate in `django.po`:

| English | French |
|---------|--------|
| `Mark as urgent` | `Marquer comme urgent` |
| `Urgent messages appear at the top of the inbox.` | `Les messages urgents apparaissent en haut de la boite de reception.` |
| `Urgent` | `Urgent` |
| `Unknown` | `Inconnu` |
| `About` | `Au sujet de` |
| `team message` | `message d'equipe` |
| `just now` | `a l'instant` |
| `1 minute ago` | `il y a 1 minute` |
| `minutes ago` | `minutes` |
| `1 hour ago` | `il y a 1 heure` |
| `hours ago` | `heures` |
| `1 day ago` | `il y a 1 jour` |
| `days ago` | `jours` |

Note: JS relative time strings use the `window.KN` translation object set in `base.html`, not Django `.po` files. Add the JS keys to the KN object in base.html if a French translation mechanism exists there. Otherwise, the JS strings remain English-only (acceptable — relative times are numeric and understandable).

**Step 3: Compile translations**

Run: `python manage.py translate_strings`

**Step 4: Commit**

```bash
git add locale/
git commit -m "i18n(messages): add French translations for messages UX improvements"
```

---

### Task 12: Run full communications test suite

**Step 1: Run all communications tests**

Run: `pytest tests/test_communications.py -v`
Expected: All tests PASS

**Step 2: Run related tests for any side effects**

Run: `pytest tests/test_communications.py tests/test_clients.py -v`
Expected: All PASS

---

### Task 13: Update TODO.md

**Step 1: Mark UX-MSG1 as complete in TODO.md**

Move `UX-MSG1` from Coming Up / Active Work to Recently Done with completion date.

**Step 2: Commit**

```bash
git add TODO.md
git commit -m "docs: mark UX-MSG1 messages page improvements as complete"
```
