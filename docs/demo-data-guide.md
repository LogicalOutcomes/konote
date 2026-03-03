# Demo Data Guide for KoNote Agencies

## What Is Demo Data?

Demo data is a set of realistic but fictional participant records, progress notes, plans, and events that KoNote can generate for your agency. It exists so your team can:

- **Learn the system** by exploring records that look like real ones, without affecting actual participant data
- **Train new staff** by letting them practise entering notes, reviewing plans, and navigating the interface
- **Show funders or partners** what KoNote looks like in action during presentations and demos
- **Test configuration changes** — after updating your programs, metrics, or templates, you can regenerate demo data to see how the changes look

Demo data is completely separate from real data. Real staff accounts cannot see demo participants, and demo accounts cannot see real participants.


## Before You Start

Demo data generation requires two things:

1. **Demo mode must be enabled.** Your system administrator needs to set the `DEMO_MODE=true` environment variable in your deployment configuration. If you are not sure whether this is enabled, check the Demo Data page (see next section) — it will tell you.

2. **At least one active program must exist.** The demo data engine reads your actual program configuration to create matching data. If you have not set up any programs yet, do that first (through the Setup Wizard or the Programs section).


## Using the Admin Interface

This is the recommended approach for most agency administrators.

### Step 1: Navigate to the Demo Data page

1. Log in to KoNote with an administrator account
2. Go to **Admin** in the main navigation
3. Click **Demo Data** (the URL is `/admin/settings/demo-data/`)

### Step 2: Review the status panel

At the top of the page you will see a status overview showing:

- **Demo Mode** — whether it is enabled or disabled
- **Active Programs** — how many programs are configured in your instance
- **Demo Users** — how many demo user accounts currently exist
- **Demo Participants** — how many demo participant records currently exist

If demo data has been generated before, you will also see the number of demo progress notes and when the data was last generated.

### Step 3: Choose your settings

If demo mode is enabled, you will see a "Generate Demo Data" section with two options:

- **Participants per program** — how many fictional participants to create for each of your programs. The default is 3, which is usually enough for training and demos. You can choose 3, 5, 8, or 10.
- **Time span** — how far back in time the demo data should stretch. The default is 6 months. Longer time spans give you more data points on charts and progress graphs.

### Step 4: Generate the data

Click the **Generate Demo Data** button. A confirmation dialog will appear asking you to confirm — this is because generating new data replaces any existing demo data.

The generation usually takes a few seconds. Once complete, you will see a success message and the status panel will update to show your new demo data.

### Step 5: Explore the demo data

After generating, you can:

- Click **View Demo Directory** on the Demo Data page to see a list of all demo users and demo participants, including their roles and program enrolments
- Log in as a demo user (see the next section) to explore the data from a staff perspective


## Demo User Accounts

When you generate demo data, KoNote creates six demo user accounts that represent different roles in your agency. Each account has the password **demo1234**.

| Username | Display Name | Role | What They Can See |
|----------|-------------|------|-------------------|
| `demo-admin` | Alex Admin | System administrator | Everything — all programs, all settings |
| `demo-executive` | Eva Executive | Executive | All programs (read-only overview, dashboards, reports) |
| `demo-manager` | Morgan Manager | Program manager | Programs they manage (full access including reports) |
| `demo-worker-1` | Casey Worker | Staff | Their assigned programs (notes, plans, events) |
| `demo-worker-2` | Noor Worker | Staff | Their assigned programs (notes, plans, events) |
| `demo-frontdesk` | Dana Front Desk | Receptionist | All programs (intake, scheduling, basic info) |

### How roles are distributed

- **Front desk and executive** accounts have access to all programs
- **Workers and managers** are split across your programs. If you have one program, all staff are on it. If you have two or more, workers are divided between them so you can see how cross-program access works.

### Logging in as a demo user

To log in as a demo user, go to the KoNote sign-in page and use one of the usernames from the table above with the password `demo1234`. If your instance uses Azure AD single sign-on, you may need to use the local login form instead (usually available at `/auth/login/`).

### Important

Demo users can only see demo participants. If you log in as a demo user, you will not see any real participant data — and vice versa, your real staff accounts will not see demo participants.


## Clearing Demo Data

If you no longer need demo data, or if you want to start fresh:

1. Go to **Admin > Demo Data**
2. Scroll down to the **Clear Demo Data** section
3. Click **Clear All Demo Data**
4. Confirm the action in the dialog

This permanently removes all demo users, demo participants, and everything associated with them (plans, notes, events, alerts). It cannot be undone — but you can always regenerate demo data later.


## How Demo Data Matches Your Configuration

The demo data engine does not use hardcoded sample data. Instead, it reads your actual instance configuration:

- **Programs** — demo participants are enrolled in your real programs
- **Metrics** — progress notes include values for the metrics linked to your note and plan templates
- **Plan templates** — plans are created using your configured plan templates (sections, targets)
- **Event types** — events match your configured event types (e.g. Intake, Follow-up)

This means your demo data will look different from another agency's demo data, because it reflects your specific setup. If you change your configuration (add a program, enable new metrics, update templates), regenerating demo data will incorporate those changes.

### Trend patterns

Each demo participant follows one of five realistic trend patterns:

- **Improving** — steady positive progress over time
- **Stable** — consistent outcomes with minor variation
- **Mixed** — ups and downs with no clear direction
- **Struggling** — difficulty maintaining progress
- **Crisis then improving** — a rough start followed by a recovery arc

These patterns make the data feel realistic and give you a range of scenarios to explore on charts and in progress summaries.


## Customising Demo Data (Advanced)

### Profile JSON Format

For agencies that want richer, more realistic demo data, you can create a **demo data profile** — a JSON file that provides program-specific content like realistic note text, participant personas, and participant quotes.

This is optional. Without a profile, the engine auto-generates plausible data for all your programs. A profile lets you add a layer of polish on top.

Here is the structure of a profile JSON file:

```json
{
  "description": "Demo data profile for [Your Agency Name]",
  "defaults": {
    "clients_per_program": 3,
    "days_span": 180,
    "note_count_range": [7, 12]
  },
  "programs": {
    "Your Program Name": {
      "note_text_pool": [
        "Session focused on reviewing progress. Participant identified areas of strength.",
        "Follow-up session. Discussed barriers and brainstormed solutions together."
      ],
      "client_words_pool": [
        "I almost didn't come today but I'm glad I did",
        "Something feels different this time"
      ],
      "suggestions_pool": [
        "It would help to have more evening options"
      ],
      "suggestion_themes": [
        {
          "name": "Scheduling flexibility",
          "description": "Participants have asked about alternative scheduling options.",
          "status": "open"
        }
      ],
      "client_personas": [
        {
          "first_name": "Jordan",
          "last_name": "Chen",
          "trend": "improving",
          "goal_statement": "I want to feel more in control of my life."
        }
      ]
    }
  }
}
```

### What each section means

| Section | Purpose |
|---------|---------|
| `description` | A label for your own reference — not displayed anywhere |
| `defaults.clients_per_program` | How many participants per program (default: 3) |
| `defaults.days_span` | How many days of historical data to generate (default: 180) |
| `defaults.note_count_range` | Minimum and maximum number of notes per participant (default: 7 to 12) |
| `programs` | Program-specific content, keyed by exact program name |
| `note_text_pool` | 6 to 10 realistic session summaries written in the voice of a worker |
| `client_words_pool` | First-person quotes from participants — these appear in the "participant words" field |
| `suggestions_pool` | Participant suggestions for program improvement |
| `suggestion_themes` | Grouped themes that emerge from suggestions |
| `client_personas` | Named participants with specific trends and goal statements |

### Important rules

- **Program names must match exactly.** The name in your JSON must be identical to the program name in KoNote (including capitalisation). If a name does not match, the engine will log a warning and fall back to auto-generated data for that program.
- **You do not need to cover every program.** Programs not listed in the profile will still get auto-generated data.
- **Trend options** for personas are: `improving`, `struggling`, `stable`, `mixed`, `crisis_then_improving`.
- **If you provide fewer personas than participants per program**, the remaining participants will be auto-generated. For example, if you define 2 personas but set `clients_per_program` to 5, the extra 3 will get auto-generated names and trends.

An example profile file is included in the KoNote repository at `seeds/demo_data_profile_example.json`.

### Command Line Usage

If you are comfortable with the command line, or if a technical colleague is helping you, the demo data command offers more control than the admin interface.

**Basic usage** (auto-generate from your current configuration):

```bash
python manage.py generate_demo_data --force
```

**With a profile JSON** (for richer, customised content):

```bash
python manage.py generate_demo_data --profile seeds/your_profile.json --force
```

**Custom participant count and time span:**

```bash
python manage.py generate_demo_data --clients-per-program 5 --days 365 --force
```

**Without the DEMO_MODE environment variable** (one-time override):

```bash
python manage.py generate_demo_data --demo-mode --force
```

### Command options reference

| Option | What it does | Default |
|--------|-------------|---------|
| `--force` | Clear existing demo data and regenerate from scratch | Off (will not overwrite existing data) |
| `--profile PATH` | Path to a demo data profile JSON file | None (auto-generate everything) |
| `--clients-per-program N` | Number of participants to create per program | 3 |
| `--days N` | Number of days of historical data to generate | 180 |
| `--demo-mode` | Enable demo mode for this run only (alternative to the environment variable) | Off |


## Troubleshooting

### "Demo mode is not enabled"

Demo mode must be turned on before you can generate or manage demo data. Your system administrator needs to set the `DEMO_MODE=true` environment variable in the deployment configuration and restart the application. If you are self-hosting, this is typically set in your `.env` file or Docker Compose configuration.

### "No active programs found"

The demo data engine needs at least one active program to generate data. You need to create your programs first — either through the Setup Wizard (recommended for new instances) or by going to the Programs section in Admin.

### I generated demo data but I cannot see any participants

Make sure you are logged in as a **demo user** (such as `demo-worker-1` with password `demo1234`). Demo participants are only visible to demo accounts. Your real staff account will not show demo data — this is by design to keep demo and real data separate.

### Demo participants do not have any metric data on their charts

This usually means no note templates with metrics have been configured for your programs. The engine tries to find metrics in this order:

1. Metrics from note templates scoped to the specific program
2. Metrics from global note templates (not scoped to any program)
3. Universal metrics (Goal Progress, Self-Efficacy, Satisfaction)

If none of these exist, notes will be created without metric values. To fix this, configure note templates with metrics for your programs, then regenerate demo data.

### No events appear on demo participants

Event types need to exist in the system. These are usually created automatically during initial setup (the `seed` command). If your instance is missing event types, ask your system administrator to check.

### My profile JSON programme name is not being used

Program names in the profile must match **exactly** — including capitalisation, spacing, and any special characters. For example, if your program is called "Youth Mental Health" in KoNote, the profile must use `"Youth Mental Health"` (not `"youth mental health"` or `"Youth mental health"`).

When a profile programme name does not match, the engine logs a warning but continues — that programme's data will be auto-generated instead of using your custom content.

### I changed my programmes and the demo data is outdated

Simply regenerate demo data. Go to **Admin > Demo Data** and click **Regenerate Demo Data** (or run the command line tool with `--force`). The engine will clear the old demo data and create new data matching your current configuration.


## Important Notes

- **Demo data does not affect real data.** Demo users and participants are completely isolated. You can generate and clear demo data at any time without risk to real records.
- **All demo user passwords are the same:** `demo1234`. This is intentional — demo accounts are for training and presentation purposes only.
- **Demo data is reproducible.** The engine uses a fixed random seed, so regenerating with the same settings and configuration will produce similar (though not identical) data each time.
- **Clearing demo data is permanent** but reversible — you can always regenerate. However, any manual edits you made to demo records (adding notes, changing plans) will be lost when you regenerate or clear.
- **When your agency is ready to go live**, you can either clear the demo data or simply set `DEMO_MODE=false`. Even without clearing, demo data is invisible to real staff accounts.
