# Configuration-Aware Demo Data Engine

## What It Does

When you deploy a new KoNote instance for a client, the demo data engine generates realistic demo participants, plans, progress notes, events, and alerts that match **that client's actual configuration** — their programs, metrics, plan templates, and surveys.

This replaces the generic 5-program demo data with data that looks like the client's agency, so they can:

1. **Evaluate** KoNote with data that feels familiar
2. **Learn** the system by exploring realistic demo records
3. **Iterate** on their configuration and regenerate demo data to see results

## How It Works — Two Layers

### Layer 1: Auto-generation (always works)

The engine reads whatever programs, metrics, and templates are currently configured in the database and generates plausible demo data automatically. No authoring required — if programs exist, demo data will match them.

**What it reads:**
- Active programs (name, service model)
- Metrics linked to note templates (program-scoped, then global, then universal fallback)
- Plan templates (program-scoped, then global, then generic structure)
- Event types (Intake, Follow-up)

**What it creates per program:**
- 3 demo participants (configurable up to 10)
- A plan for each participant with sections, targets, and metrics
- 7-12 progress notes per participant with metric values following trend patterns
- Intake and follow-up events
- Alerts for participants on "struggling" or "crisis" trends
- Suggestion themes

**6 demo users** are created across all programs:
- `demo-frontdesk` — receptionist on all programs
- `demo-worker-1`, `demo-worker-2` — staff split across programs
- `demo-manager` — program manager
- `demo-executive` — executive on all programs
- `demo-admin` — system admin

### Layer 2: Profile JSON (optional polish)

For clients who need a more compelling demo, you can write a **demo data profile** — a JSON file with program-specific content like realistic note text, participant personas, and client quotes.

Programs not included in the profile still get auto-generated data from Layer 1.

See `seeds/demo_data_profile_example.json` for the complete format.

## When to Use It

| Situation | What to do |
|-----------|-----------|
| Default KoNote demo (existing) | Don't change anything. The hardcoded demo continues to work as before. |
| New client deployment, default programs | Run `generate_demo_data` after setup — auto-generation gives decent results. |
| New client deployment, custom programs | Run `generate_demo_data` after their programs are configured. Optionally write a profile JSON for richer content. |
| Client changed their configuration | Click "Regenerate Demo Data" in the admin panel, or re-run the command. |
| Client wants to go live (disable demo) | Set `DEMO_MODE=false` in the environment. Demo data is isolated and invisible to real users, but can be cleared via the admin panel. |

## How to Generate Demo Data

### Option A: Admin UI (simplest)

1. Go to **Admin > Demo Data** (or click "Demo Data" on the admin dashboard)
2. Choose participants per program (3, 5, 8, or 10) and time span (3, 6, or 12 months)
3. Click **Generate Demo Data**
4. Existing demo data is automatically replaced

Requires `DEMO_MODE=true` in the environment.

### Option B: Management Command (more control)

```bash
# Basic: auto-generate from current config
python manage.py generate_demo_data --force

# With a profile JSON for richer content
python manage.py generate_demo_data --profile seeds/demo_profile.json --force

# Custom options
python manage.py generate_demo_data --clients-per-program 5 --days 365 --force

# Run without DEMO_MODE env var
python manage.py generate_demo_data --demo-mode --force
```

### Option C: Automatic on Container Start

Set the `DEMO_DATA_PROFILE` environment variable to a file path:

```
DEMO_MODE=true
DEMO_DATA_PROFILE=seeds/demo_profile.json
```

When the container starts and runs `seed`, it will use the config-aware engine with the specified profile instead of the hardcoded default demo.

If `DEMO_DATA_PROFILE` is not set but `DEMO_MODE=true`, the existing hardcoded demo is used (no regression).

## Writing a Demo Data Profile

A profile JSON lets you provide richer, program-specific content. Place it alongside your `setup_config.json` in the `seeds/` directory.

### Structure

```json
{
  "description": "Demo data profile for [Agency Name]",
  "defaults": {
    "clients_per_program": 3,
    "days_span": 180,
    "note_count_range": [7, 12]
  },
  "programs": {
    "Exact Program Name": {
      "note_text_pool": ["..."],
      "client_words_pool": ["..."],
      "suggestions_pool": ["..."],
      "suggestion_themes": [{ "name": "...", "description": "...", "status": "open" }],
      "client_personas": [
        {
          "first_name": "Jordan",
          "last_name": "Chen",
          "trend": "improving",
          "goal_statement": "I want to feel safe and stable."
        }
      ]
    }
  }
}
```

### Key Rules

- **Program names must match exactly.** The engine matches by the program's `name` field. If a program is renamed after a profile was written, the engine logs a warning and falls back to auto-generation for that program. Update the profile and regenerate to fix.
- **Trend options:** `improving`, `struggling`, `stable`, `mixed`, `crisis_then_improving`
- **Programs not in the profile** get auto-generated content — you don't need to cover every program.
- **`note_text_pool`** — 6-10 realistic session summaries in the voice of the worker. These appear in progress notes.
- **`client_words_pool`** — Quotes from participants in first person. These appear in the "client words" field of progress notes.
- **`client_personas`** — Named participants with specific trends and goal statements. If you provide 3 personas and set `clients_per_program` to 5, the extra 2 will be auto-generated.

## Demo Data Isolation

Demo data is completely isolated from real data:

- Demo users have `is_demo=True` — they can only see demo participants
- Demo participants have `is_demo=True` — they are invisible to real users
- All demo user passwords are `demo1234`
- Demo user emails use the `DEMO_EMAIL_BASE` env var pattern (e.g. `user+demo-worker-1@agency.org`)

## Clearing Demo Data

- **Admin UI:** Click "Clear All Demo Data" on the Demo Data page
- **Command line:** The `--force` flag on `generate_demo_data` clears and regenerates
- **Manual:** Demo data can be identified by `is_demo=True` on users and client files

Clearing demo data removes: demo users, demo participants (and all their plans, notes, events, alerts via CASCADE), suggestion themes created by demo users, circles, portal users, registrations, and calendar tokens.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "No active programs found" | No programs configured yet | Run the setup wizard or create programs first, then generate |
| Profile program not matched | Program name in JSON doesn't match database | Check exact spelling (case-sensitive) |
| No metrics on demo notes | No note templates configured for programs | Configure note templates with metrics, or the engine falls back to universal metrics |
| No events created | No EventType records in the database | Run `seed_event_types` first (usually done by the `seed` command) |
| Demo data not appearing | Not logged in as a demo user | Use the demo login buttons, not a real account |

## Files

| File | Purpose |
|------|---------|
| `apps/admin_settings/demo_engine.py` | Core engine — all generation and cleanup logic |
| `apps/admin_settings/management/commands/generate_demo_data.py` | Management command wrapper |
| `seeds/demo_data_profile_example.json` | Example profile with two programs |
| `templates/admin_settings/demo_data.html` | Admin UI page |
| `apps/admin_settings/views.py` | `demo_data_management` view (at the end of file) |
