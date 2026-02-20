# Messaging

How to configure SMS and email messaging, set up automated reminders, and monitor messaging health.

---

## Messaging Modes

KoNote can log communications and optionally send SMS or email reminders to participants.

| Mode | What it does |
|------|--------------|
| **Record-keeping only** (default) | Staff log phone calls, emails, and texts manually. No messages are actually sent. |
| **Active messaging** | Staff can send SMS and email reminders to participants who have consented. |

---

## Configure Messaging

1. Click **gear icon** -> **Features**
2. Enable **SMS Messaging** and/or **Email Messaging**
3. Click **gear icon** -> **Instance Settings** -> **Messaging**
4. Choose a messaging profile: **Record keeping** or **Active**

**Safety-First mode:** If enabled, this blocks ALL outbound messages regardless of other settings. Use this during setup and testing to make sure no real messages go out while you're configuring things.

---

## SMS Setup

Requires a Twilio account. Add the following to your environment variables:

| Variable | What it is |
|----------|------------|
| `TWILIO_ACCOUNT_SID` | Your Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | Your Twilio authentication token |
| `TWILIO_FROM_NUMBER` | The phone number messages are sent from |

---

## Email Setup

Requires SMTP configuration. Add the following to your environment variables:

| Variable | What it is |
|----------|------------|
| `EMAIL_HOST` | Your mail server address |
| `EMAIL_PORT` | Mail server port (typically 587 for TLS) |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |
| `DEFAULT_FROM_EMAIL` | The "from" address on outgoing emails |

See `.env.example` for details and example values.

**Export notification recipients:** When someone exports a report containing individual participant data, KoNote sends a notification email. By default this goes to all system administrators. To send it to specific people instead (e.g., a privacy officer or ED), set:

| Variable | What it is |
|----------|------------|
| `EXPORT_NOTIFICATION_EMAILS` | Comma-separated email addresses (e.g., `privacy@agency.ca,ed@agency.ca`) |

If this variable is not set, notifications fall back to all active admin users.

---

## Calendar Feed Token Management

Staff can subscribe to their KoNote meetings in external calendar apps such as Outlook, Google Calendar, or Apple Calendar.

**How it works:**
- Each staff member generates their own feed URL from **Meetings** -> **Calendar Feed Settings**
- Feed tokens are private -- each user's feed only shows meetings where they are an attendee
- **Privacy:** Calendar entries display initials and record ID only (no full names, phone numbers, or email addresses)
- If a staff member leaves, deactivating their user account also invalidates their calendar feed token

**No admin action is needed for day-to-day management** -- staff self-serve. You only need to be aware that deactivating a user also cuts off their calendar feed.

---

## Automated Reminders

KoNote can automatically send SMS or email reminders for upcoming meetings. This requires the `send_reminders` management command to run on a schedule.

### How It Works

1. The command looks for meetings in the next **36 hours** (by default) that are scheduled and haven't been reminded yet
2. For each meeting, it sends a reminder via the participant's preferred contact method (SMS or email)
3. Participants must have **active consent** for the chosen channel -- if no consent, the reminder is skipped (not treated as a failure)
4. Failed reminders are **retried automatically** on the next run
5. After each batch, the system checks messaging channel health and sends admin alerts if channels are failing persistently

### Prerequisites

- **SMS Messaging** and/or **Email Messaging** must be enabled in Features
- SMS and/or email service must be configured (see above)
- The participant must have a valid phone number or email address
- The participant must have active consent for the channel

### Running Manually

```bash
# Send reminders for meetings in the next 36 hours
python manage.py send_reminders

# Preview what would be sent without actually sending
python manage.py send_reminders --dry-run

# Use a custom lookahead window (e.g., 24 hours)
python manage.py send_reminders --hours 24
```

### Setting Up as a Scheduled Task

**Linux/Mac (cron) -- run hourly:**

```bash
# Add to crontab with: crontab -e
0 * * * * cd /path/to/konote && python manage.py send_reminders >> /var/log/konote-reminders.log 2>&1
```

**Docker Compose -- run hourly:**

```bash
0 * * * * docker compose -f /path/to/docker-compose.yml exec -T web python manage.py send_reminders >> /var/log/konote-reminders.log 2>&1
```

**Railway:**

Add a cron job service in your Railway project configuration that runs `python manage.py send_reminders` on an hourly schedule (e.g., `0 * * * *`).

**Windows Task Scheduler:**

Create a scheduled task that runs hourly:

```powershell
$Action = New-ScheduledTaskAction -Execute "python" -Argument "manage.py send_reminders" -WorkingDirectory "C:\KoNote\KoNote-web"
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "KoNote Reminders" -Action $Action -Trigger $Trigger
```

### Output

Each run reports a summary:

- **Sent** -- reminder delivered successfully
- **Skipped** -- participant has no consent or no contact information (won't change on retry)
- **Failed** -- delivery error (will be retried on the next run)

---

## System Health Monitoring

KoNote tracks the health of SMS and email messaging channels and surfaces warnings when something is wrong.

### How It Works

Every time KoNote sends (or attempts to send) an SMS or email reminder, it records the result in a `SystemHealthCheck` record for that channel. The system tracks:

- When the last successful send occurred
- When the last failure occurred
- How many consecutive failures have happened
- The reason for the last failure

### Staff-Visible Banners

When messaging is enabled and a channel has recent failures, staff see warning banners on the **Meetings** page:

| Condition | Banner colour | Message |
|-----------|--------------|---------|
| 1-2 failures in the last 24 hours | Yellow (warning) | "X SMS/Email reminder(s) could not be sent recently." |
| 3 or more consecutive failures | Red (danger) | "SMS/Email reminders have not been working since [date]. Please contact your support person." |

Banners disappear automatically once the channel starts working again (the failure counter resets on success).

### Admin Alert Emails

After **24 hours of sustained failures**, administrators receive an email alert. This gives your support team early warning to investigate connectivity, credentials, or service outages.

### Viewing Health Status

Administrators can also see channel health status on the **Messaging Settings** page (gear icon -> Messaging). This shows the current state of each channel, including the last success/failure timestamps and failure count.

### Common Causes of Failures

| Channel | Common issue | What to check |
|---------|-------------|---------------|
| **SMS** | Invalid Twilio credentials | Verify `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` in environment variables |
| **SMS** | Account balance exhausted | Check your Twilio account balance |
| **Email** | SMTP authentication failed | Verify `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` |
| **Email** | Connection timeout | Check `EMAIL_HOST` and `EMAIL_PORT` settings |

---

[Back to Admin Guide](index.md)
