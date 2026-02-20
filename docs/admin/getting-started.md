# Getting Started

How to set up a new KoNote instance for your agency.

**Time estimate:** 30-45 minutes for basic setup.

---

## Creating the First Admin Account

Every new KoNote instance starts with no users. You need to create the first admin from the command line before anyone can log in:

```bash
# Docker:
docker-compose exec web python manage.py createsuperuser

# Direct / Railway:
python manage.py createsuperuser
```

You'll be prompted for a **username** and **password**. This creates a user with full admin access (`is_admin=True`).

> **Demo mode shortcut:** If `DEMO_MODE=true`, the seed process automatically creates a `demo-admin` user with password `demo1234`. You can log in with that immediately and skip this step.

---

## First Login

**Azure AD (Office 365):**
1. Navigate to your KoNote URL
2. Click **Login with Azure AD**
3. Enter your work email and password
4. An admin must then assign your program roles through the web interface

**Local authentication:**
1. Navigate to your KoNote URL
2. Enter the username and password you created above

---

## Instance Settings

Control your organisation's branding and behaviour.

1. Click the **gear icon** (top-right) -> **Instance Settings**
2. Configure:

| Field | What it does | Example |
|-------|--------------|---------|
| **Product Name** | Shown in header and titles | "Youth Housing -- KoNote" |
| **Support Email** | Displayed in footer | support@agency.ca |
| **Logo URL** | Your organisation's logo | https://example.com/logo.png |
| **Date Format** | How dates appear throughout the system | 2026-02-03 (ISO) |
| **Session Timeout** | Minutes before auto-logout | 30 |

3. Click **Save**

---

## Setup Wizard

The setup wizard guides you through the most common configuration steps in order. It covers:

1. Instance settings (product name, logo, support email)
2. Terminology customisation
3. Feature toggles
4. Programs

Access it from **gear icon -> Setup Wizard** or the admin dashboard.

---

## Apply Setup Command

> **Status:** The `apply_setup` management command is **planned but not yet built**. It will be created when the first agency requests setup assistance. The design is documented below so you know what to expect.

The `apply_setup` command will create a full agency configuration from a single JSON file. This is intended for consultants setting up new KoNote instances, replacing the need to manually configure each setting through the web interface.

### How It Will Work

```bash
# Apply a configuration file
python manage.py apply_setup config.json

# Preview without making changes
python manage.py apply_setup config.json --dry-run
```

The command will create, in order:

1. **Instance settings** -- product name, logo, support email, date format
2. **Terminology overrides** -- customised terms (e.g., "Client" -> "Participant")
3. **Feature toggles** -- which modules to enable or disable
4. **Programs** -- service lines with names, descriptions, and colours
5. **Plan templates** -- complete templates with sections and targets
6. **Custom field groups and fields** -- agency-specific data fields
7. **Metric enable/disable flags** -- which metrics from the library to activate

### Configuration File Format

The configuration file is a JSON document. Here is a simplified example:

```json
{
  "instance_settings": {
    "product_name": "Youth Services -- KoNote",
    "support_email": "support@agency.ca"
  },
  "terminology": {
    "client": "Participant",
    "target": "Goal"
  },
  "features": {
    "programs": true,
    "events": true,
    "alerts": false
  },
  "programs": [
    {
      "name": "Youth Housing",
      "description": "Transitional housing support for youth aged 16-24",
      "colour_hex": "#6366F1"
    }
  ],
  "metrics_enabled": ["PHQ-9 (Depression)", "GAD-7 (Anxiety)"]
}
```

See `tasks/setup-wizard-design.md` in the codebase for the full configuration file specification.

### Important Notes

- The command is **not idempotent** -- running it twice creates duplicates. Clear the database or remove items manually before re-running.
- User accounts, custom metrics, and client data imports are handled separately through their own workflows.
- For now, use the web interface to configure your instance manually.

---

## Troubleshooting

### Q: I see a login error
**A:** For Azure AD, check your email is registered. For local auth, confirm credentials with an admin.

### Q: Can I change settings later?
**A:** Yes. All settings can be changed at any time through the admin interface.

---

## Next Steps

After initial setup, continue with:
- [Features & Modules](features-and-modules.md) -- enable the modules your agency needs
- [Terminology](terminology.md) -- customise the language
- [Users & Roles](users-and-roles.md) -- create staff accounts

---

[Back to Admin Guide](index.md)
