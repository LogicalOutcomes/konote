# KoNote

A secure, web-based Participant Outcome Management system for nonprofits. Agencies define desired outcomes with clients, record progress notes with metrics, and visualise progress over time. Each organisation runs their own instance with full control over configuration, terminology, and user access.

---

## Origins & Acknowledgements

**KoNote** is the second generation of [KoNote](https://github.com/LogicalOutcomes/KoNote), an open-source outcome tracking system originally created by **Dr. David Gotlib**. David, a former board member of [LogicalOutcomes](https://LogicalOutcomes.net), donated the original KoNote to the organisation and made it open source. LogicalOutcomes is a Canadian nonprofit focused on evaluation consulting and building organisational learning capacity.

The original KoNote was designed to help mental health professionals and social service agencies track client outcomes — "notes that count." As Dr. Gotlib put it, traditional EMRs are often "over-engineered and cluttered." KoNote took the opposite approach: a simple interface designed for frontline workers, not IT departments.

### Why KoNote?

When we implemented KoNote in nonprofit organisations, we discovered something important: **every nonprofit is different**. Each agency had:

- **Different vocabulary** — "clients" vs. "participants" vs. "members" vs. "service users"
- **Different workflows** — some wanted detailed structured notes, others needed quick check-ins
- **Different ways of thinking about services** — programs vs. streams vs. initiatives
- **Different access control needs** — who should see what about whom

We found it impossible to customise the software for each agency's needs while maintaining a central software platform at a price nonprofits could afford.

### The KoNote Approach

**KoNote is designed for agencies to run their own instances** — on their own infrastructure, even their own local network if needed. This gives each organisation:

- **Full control over customisation** — change terminology, enable/disable features, define your own fields
- **Data sovereignty** — your client data stays on your servers, under your control
- **Freedom to adapt** — modify the code to match your specific workflow

**AI-assisted development made this practical.** With tools like Claude Code, small nonprofits can now:

- Deploy and maintain their own secure infrastructure
- Customise terminology, workflows, and reports to match their practice
- Extend functionality without hiring a development team
- Get help troubleshooting and adapting the code

### Built-In Security Reviews

We've built automated security checks directly into the codebase. Whenever an agency modifies the code, these tools help catch common security issues before they become problems. The security audit system checks encryption configuration, access controls, audit logging, and production settings. All of this is documented in the repository — see the [Technical Reference](docs/technical-documentation.md) for details.

### Design Priorities

KoNote is a ground-up reimplementation using modern Python/Django, designed specifically for this kind of organisation-owned, AI-assisted customisation. The codebase prioritises:

- **Simplicity** — no complex JavaScript frameworks; plain Django templates + HTMX
- **Readability** — clear code structure that AI assistants can understand and modify
- **Security** — encryption at rest, audit logging, role-based access control
- **Compliance** — built with PIPEDA, GDPR, and healthcare regulations in mind

### Participant-Centred Practice

KoNote is built around a core philosophy: **documentation is part of the intervention, not administrative overhead**.

Research consistently shows that when participants engage in their own records, outcomes improve. Progress notes aren't just for funders or supervisors — they're opportunities to strengthen the relationship between staff and participants.

**How this shapes the software:**

- **Participant reflection prompts** — Every progress note includes a simple question to ask the participant: *"What's one thing you're taking away from today?"* This captures their voice in the record and makes documentation a collaborative moment.

- **"We created this note together"** — Instead of a consent checkbox, staff confirm they reviewed the note with the participant. This reinforces transparency and shared ownership.

- **Flexible terminology** — Every agency can customise language ("participant," "client," "member," "youth") to match their practice philosophy.

- **Outcome tracking that matters** — Metrics are participant-defined goals, not compliance data. Progress visualisations help participants see their own growth.

For the research basis behind these design choices, see [Design Principles](docs/design-principles.md).

---

## Features

### Client Management
- Secure client records with encrypted personally identifiable information (PII)
- Custom intake fields defined by your agency
- Program enrolment tracking
- Client search with role-based access control

### Outcome Tracking
- Plan sections with targets/goals
- Quantifiable metrics attached to targets
- Track progress over time with revision history
- Reusable plan templates

### Progress Notes
- Quick notes for brief interactions
- Full structured notes with template support
- Record metric values against targets
- Backdated notes with audit trail

### Timeline & Events
- Client timeline with significant events
- Event types (intake, discharge, crisis, milestone)
- Safety alerts on client files with two-person cancellation rule

### Communications & Messaging
- Log phone calls, emails, SMS, and in-person contacts on the client timeline
- Quick-log buttons for common interactions
- **Send SMS and email** — compose and send messages to participants with consent tracking (Twilio for SMS, SMTP for email)
- Appointment reminder previews before sending, with CASL-required unsubscribe links
- Staff-to-staff messaging about participants with unread badges and My Messages dashboard
- Safety-first mode — block all outbound messages when clients may be in unsafe situations
- System health monitoring banners when SMS or email delivery is failing

### Meetings & Calendar
- Schedule meetings with clients and track status (scheduled, completed, cancelled, no-show)
- Subscribe to iCal feeds in Outlook, Google Calendar, or Apple Calendar
- Privacy-safe summaries — initials and record ID only, no client names in external calendars
- Automated SMS/email reminders for upcoming meetings

### Consent Management
- CASL-compliant consent tracking for SMS and email on each client record
- Express and implied consent types with date tracking
- Consent withdrawal tracking and signed, time-limited unsubscribe links

### Groups & Projects
- Session logs and attendance tracking for group-based services
- Member highlights, milestones, and group-level outcomes
- Two modes: drop-in groups (attendance) and goal-oriented projects (milestones)

### Surveys
- Create structured feedback forms with sections, questions, and scoring
- Six question types: short text, long text, single choice, multiple choice, rating scale, yes/no
- **Trigger rules** — automatically assign surveys based on events, enrolment, time intervals, or participant characteristics
- **Shareable links** — generate public URLs for anonymous or identified survey completion without a portal account
- **Auto-save** — partial answers saved question-by-question so participants can resume later
- **Conditional sections** — show or hide sections based on answers to trigger questions
- **Section scoring** — sum or average scoring with optional display to participants
- CSV import for bulk survey creation from spreadsheets
- Bilingual support (EN/FR) for all survey content
- Three submission channels: participant portal, staff data entry, or shareable link

### Participant Portal
- Separate participant-facing interface for viewing goals, progress, and milestones
- Journal entries with optional disclosure to staff
- Messaging between participants and their workers
- **Survey completion** — fill in assigned surveys with multi-page forms and auto-save
- **Password reset** — self-service via 6-digit email code with rate limiting
- **Staff-assisted login** — one-time token for helping participants who can't self-register
- **PWA support** — "Add to Home Screen" for a native app experience on mobile
- **Usage analytics** — aggregate dashboard showing portal adoption, engagement, and feature usage
- Auto-deactivation on client discharge, with data preserved
- Staff manage portal access, invitations, and MFA resets from the client detail page

### Suggestion Tracking & Outcome Insights
- Capture participant suggestions and reflections in every progress note
- Automated theme identification from feedback (keyword matching and AI-generated)
- Responsiveness tracking — themes move through open → in progress → addressed
- Executive dashboard shows top themes per program

### Duplicate Detection & Merge
- Phone number and name/date-of-birth matching across programs
- Cross-program deduplication that respects confidentiality boundaries
- Admin merge tool with full data transfer between records

### Reporting & Analytics
- Progress charts (Chart.js) with template-driven interpretations
- Metric export to CSV with injection protection
- PDF reports via WeasyPrint
- Funder profiles with custom age bins, demographic merging, and small-cell suppression
- Audit log viewer for compliance (program-scoped for managers)
- Weekly export summary emails for privacy oversight

### AI Assist (Optional)
- **AI Goal Builder** — conversational goal-setting on the plan page; multi-turn dialogue helps staff and participants define measurable targets
- AI-suggested metrics, outcome statement improvements, and note structure
- Outcome Insights narrative generation from qualitative data
- PII scrubbed before any data leaves the server; all AI features gated by feature toggle and API key

### Dashboard Roles
- **Coach view** — active clients, priority items, recent notes, upcoming meetings
- **Program Manager view** — program summary with note volume, alert counts, and staff activity
- **Executive view** — cross-program overview with outcome trends, suggestion themes, and portal adoption

### Customisation
- **Terminology overrides** — call clients "Participants", programs "Services", etc.
- **Feature toggles** — enable/disable features to match your workflow
- **Custom fields** — capture agency-specific data with validation (postal code, phone, email)
- **Templates** — standardise plans and notes across your team
- **PM self-service** — program managers manage their own templates, metrics, event types, and registration links
- **Setup wizard** — guided first-run configuration for new instances (branding, terminology, features, programs, metrics, templates)

### Security & Compliance
- Field-level encryption for all PII (Fernet/AES)
- Dual-database architecture (app + immutable audit log)
- Role-based access control (Admin, Program Manager, Staff, Front Desk, Executive)
- Confidential program isolation for sensitive services (DV, counselling)
- Session management with configurable timeout
- HTTPS with HSTS, CSP headers, CSRF protection

### Privacy & Compliance
- **Data portability** — Individual client export (CSV/PDF) with selectable sections for PIPEDA compliance
- **Client data erasure** — Multi-program-manager approval workflow for PIPEDA/GDPR right to erasure
- **Self-service registration** — Public forms with capacity limits, duplicate detection, consent tracking
- **Export controls** — CSV injection protection, elevated export monitoring, recipient tracking, secure download links
- **Demo/real separation** — Immutable `is_demo` flags prevent cross-contamination between evaluation and production data

### Localisation
- **French (Français)** — 2,146+ translated strings, header language switcher (Canada.ca convention), cookie-based persistence
- **Canadian formats** — Postal code validation (A1A 1A1), phone normalisation ((613) 555-1234), auto-detection from field names

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.1, Python 3.12 |
| Database | PostgreSQL 16 (dual: app + audit) |
| Frontend | Django Templates, HTMX, Pico CSS |
| Charts | Chart.js |
| Auth | Azure AD SSO or local (Argon2) |
| Encryption | Fernet (AES-128-CBC + HMAC-SHA256) |
| PDF Export | WeasyPrint |
| Deployment | Docker, Gunicorn, WhiteNoise |

**No React. No Vue. No webpack. No npm.** Just Python, HTML, and a dash of vanilla JavaScript.

---

## Quick Start

> **Not a developer?** That's fine. If you've installed WordPress or used Excel competently, you can set up KoNote. Our [Deploying KoNote](docs/deploying-KoNote.md) guide explains every step in plain language.
>
> **Important:** Running your own instance means taking responsibility for client data security. KoNote has strong protections built in, but you need to configure them correctly. See the [security responsibility section](docs/deploying-KoNote.md#understanding-your-responsibility) to understand what that involves.

### Try It Instantly (Docker)

Want to see KoNote before committing to a full setup? Run the demo with one command:

```bash
docker-compose -f docker-compose.demo.yml up
```

Then open http://localhost:8000 in your browser.

> **Warning:** Demo mode uses default keys and is NOT SECURE. Do not enter real client data. For production, see the full setup below.

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/gilliankerr/KoNote.git
   cd KoNote
   ```

2. **Activate the pre-commit hook**

   Run the setup script to enable the pre-commit hook that keeps translation files in sync:
   ```bash
   scripts\setup.bat        # Windows
   # Or manually: git config core.hooksPath .githooks
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create environment file**

   Copy the example file:
   ```bash
   copy .env.example .env   # Windows
   # cp .env.example .env   # macOS/Linux
   ```

   Generate required security keys:
   ```bash
   # Generate SECRET_KEY (Django sessions)
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

   # Generate FIELD_ENCRYPTION_KEY (PII encryption - REQUIRED)
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Paste both keys into your `.env` file:
   ```
   SECRET_KEY=paste-your-generated-key-here
   FIELD_ENCRYPTION_KEY=paste-your-generated-key-here
   DATABASE_URL=postgresql://konote:password@localhost:5432/konote
   AUDIT_DATABASE_URL=postgresql://audit_writer:password@localhost:5432/konote_audit
   AUTH_MODE=local
   ```

   > **Getting `KoNote.E001` error?** Your encryption key is missing or invalid.
   > See [Deploying KoNote](docs/deploying-KoNote.md#troubleshooting) for help.

6. **Run migrations**
   ```bash
   python manage.py migrate
   python manage.py migrate --database=audit
   ```

7. **Create admin user**
   ```bash
   python manage.py createsuperuser
   ```

7.5. **Load seed data** (recommended)
   ```bash
   python manage.py seed
   ```
   Creates the metrics library, default templates, event types, and feature toggles.
   Runs automatically in Docker but must be run manually for local development.

8. **Start the server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to access the application.

---

## Deployment

KoNote is designed to run on your own infrastructure. See [Deploying KoNote](docs/deploying-KoNote.md) for complete instructions, including:

- **[Local Development (Docker)](docs/deploying-KoNote.md#local-development-docker)** — Try KoNote locally
- **[Railway](docs/deploying-KoNote.md#deploy-to-railway)** — Platform-as-a-Service, easy setup
- **[Azure](docs/deploying-KoNote.md#deploy-to-azure)** — Azure Container Apps + managed PostgreSQL
- **[Elestio](docs/deploying-KoNote.md#deploy-to-elestio)** — Docker Compose on managed hosting

### Docker

```bash
docker-compose up -d
```

The Docker setup includes:
- Web application (Gunicorn)
- PostgreSQL (main database)
- PostgreSQL (audit database)
- Caddy (reverse proxy with automatic HTTPS)

---

## Configuration

After deployment, configure your instance through the web interface:

1. **Instance Settings** — organisation name, logo, session timeout
2. **Terminology** — customise all terms (client, program, target, etc.)
3. **Features** — enable/disable modules to match your workflow
4. **Programs** — create service lines and assign staff
5. **Templates** — build reusable plan and note structures
6. **Custom Fields** — add agency-specific intake fields

See the [Admin Guide](docs/admin/index.md) for detailed instructions.

---

## Documentation

Start with the [Documentation Index](docs/index.md) to find what you need.

| Document | Audience | Description |
|----------|----------|-------------|
| [Deploying KoNote](docs/deploying-KoNote.md) | IT / Technical lead | Local setup, cloud deployments, PDF setup |
| [Admin Guide](docs/admin/index.md) | Program managers / Admins | Configuration, users, backups, security |
| [Using KoNote](docs/using-KoNote.md) | Front-line staff | Day-to-day usage guide |
| [Technical Reference](docs/technical-documentation.md) | Developers | Architecture, security, data models |

---

## Security

KoNote is designed for sensitive client data:

- **Encryption at rest** — All PII fields encrypted with Fernet (AES)
- **Audit logging** — Every data access and change logged to separate database
- **Role-based access** — Staff only see clients in their assigned programs
- **Session security** — Database-backed sessions, configurable timeout
- **HTTP security** — HSTS, CSP, X-Frame-Options, secure cookies

See [Security](docs/admin/security.md) for security operations and [Technical Reference](docs/technical-documentation.md) for architecture details.

### Trust, But Verify

KoNote encrypts all client names, notes, and outcome ratings at rest using AES encryption. Your encryption key stays with you — it never touches our codebase.

But don't just take our word for it.

Because KoNote is open source, any agency can run an **independent security review** at any time — using free AI tools, your own IT staff, or a professional security firm. We provide a [ready-made review prompt](docs/security-operations.md#ai-review-prompt) to get you started. Security-focused code reviews happen automatically every time code changes, and because the code is public, those reviews are verifiable too.

---

## Accessibility

KoNote follows **WCAG 2.2 AA** guidelines:

- Semantic HTML structure
- Proper form labels and error messages
- Keyboard navigation support
- Colour contrast compliant
- Screen reader compatible

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

For significant changes, please open an issue first to discuss the approach.

---

## License

This project is open source. See [LICENSE](LICENSE) for details.

---

## Acknowledgements

- **[Dr. David Gotlib](https://www.canhealth.com/2016/11/02/physician-created-KoNote-makes-it-easy-to-chart-notes-and-numbers/)** — Creator of the original KoNote, former LogicalOutcomes board member, who donated the software and made it open source
- **[LogicalOutcomes](https://github.com/LogicalOutcomes)** — Stewards of the original KoNote project
- **[Pico CSS](https://picocss.com/)** — Minimal CSS framework
- **[HTMX](https://htmx.org/)** — HTML extensions for dynamic interactions
- **[Chart.js](https://www.chartjs.org/)** — Progress visualisation

---

## Support

- **Documentation issues**: Open an issue in this repository
- **Security vulnerabilities**: Please report privately (see SECURITY.md)
- **General questions**: See the [Admin Guide](docs/admin/index.md)
