# KoNote Web

A secure, web-based client outcome management system for nonprofits. Agencies define desired outcomes with clients, record progress notes with metrics, and visualise progress over time. Each organisation runs their own instance with full control over configuration, terminology, and user access.

---

## Origins & Acknowledgements

**KoNote Web** is based on [KoNote](https://github.com/LogicalOutcomes/KoNote) — an open-source outcome tracking system created by **Dr. David Gotlib** and maintained by [LogicalOutcomes](https://github.com/LogicalOutcomes), a Canadian nonprofit focused on evaluation consulting and building organisational learning capacity.

The original KoNote was designed to help mental health professionals and social service agencies track client outcomes — "notes that count." As Dr. Gotlib put it, traditional EMRs are often "over-engineered and cluttered." KoNote took the opposite approach: a simple interface designed for frontline workers, not IT departments.

### Why This Reconfiguration?

The vision of the original KoNote was always for individual organisations to run their own instances, customised to their specific needs. However, setting up and maintaining custom software has historically required significant technical expertise.

**AI-assisted development has changed this.** Tools like Claude Code make it practical for small nonprofits to:

- Deploy and maintain their own secure infrastructure
- Customise terminology, workflows, and reports to match their practice
- Extend functionality without hiring a development team
- Keep client data under their own control

KoNote Web is a ground-up reimplementation using modern Python/Django, designed specifically for this kind of AI-assisted customisation. The codebase prioritises:

- **Simplicity** — no complex JavaScript frameworks; plain Django templates + HTMX
- **Readability** — clear code structure that AI assistants can understand and modify
- **Security** — encryption at rest, audit logging, role-based access control
- **Compliance** — built with PIPEDA, GDPR, and healthcare regulations in mind

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
- Safety alerts on client files

### Reporting & Analytics
- Progress charts (Chart.js)
- Metric export to CSV
- PDF reports via WeasyPrint
- Audit log viewer for compliance

### Customisation
- **Terminology overrides** — call clients "Participants", programs "Services", etc.
- **Feature toggles** — enable/disable features to match your workflow
- **Custom fields** — capture agency-specific data
- **Templates** — standardise plans and notes across your team

### Security & Compliance
- Field-level encryption for all PII (Fernet/AES)
- Dual-database architecture (app + immutable audit log)
- Role-based access control (Admin, Program Manager, Staff, Receptionist)
- Session management with configurable timeout
- HTTPS with HSTS, CSP headers, CSRF protection

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

> **Not a developer?** That's fine. If you've installed WordPress or used Excel competently, you can set up KoNote. Our [Getting Started Guide](docs/getting-started.md) explains every step in plain language. Plan for about 2 hours for your first setup — the technical steps are quick, but you'll be learning new concepts along the way.
>
> **Important:** Running your own instance means taking responsibility for client data security. KoNote has strong protections built in, but you need to configure them correctly and maintain them over time. The Getting Started Guide includes a [security responsibility section](docs/getting-started.md#before-you-begin-understanding-your-responsibility) to help you understand what that involves.

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/konote-web.git
   cd konote-web
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**

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

   > **Getting `konote.E001` error?** Your encryption key is missing or invalid.
   > See [Getting Started Guide](docs/getting-started.md#troubleshooting) for help.

5. **Run migrations**
   ```bash
   python manage.py migrate
   python manage.py migrate --database=audit
   ```

6. **Create admin user**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to access the application.

---

## Deployment

KoNote Web is designed to run on your own infrastructure. We provide deployment guides for:

- **[Railway](docs/deploy-railway.md)** — Platform-as-a-Service, easy setup
- **[Azure](docs/deploy-azure.md)** — Azure App Service + managed PostgreSQL
- **[Elestio / Self-hosted](docs/deploy-elestio.md)** — Docker Compose on a VPS

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

See the [Agency Setup Guide](docs/agency-setup.md) for detailed instructions.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Local development setup (Python or Docker) |
| [What KoNote Is](docs/what-konote-is.md) | Feature scope, boundaries, and design philosophy |
| [Security Operations](docs/security-operations.md) | Security checks, audit logs, key management |
| [Agency Setup Guide](docs/agency-setup.md) | Configure your instance after deployment |
| [Deploy to Railway](docs/deploy-railway.md) | Step-by-step Railway deployment |
| [Deploy to Azure](docs/deploy-azure.md) | Azure App Service deployment |
| [Deploy to Elestio/VPS](docs/deploy-elestio.md) | Self-hosted Docker deployment |
| [Technical Documentation](docs/technical-documentation.md) | Architecture, security, API reference |
| [Backup & Restore](docs/backup-restore.md) | Database backup procedures |
| [PDF Setup](docs/pdf-setup.md) | WeasyPrint dependencies for PDF exports |

---

## Security

KoNote Web is designed for sensitive client data:

- **Encryption at rest** — All PII fields encrypted with Fernet (AES)
- **Audit logging** — Every data access and change logged to separate database
- **Role-based access** — Staff only see clients in their assigned programs
- **Session security** — Database-backed sessions, configurable timeout
- **HTTP security** — HSTS, CSP, X-Frame-Options, secure cookies

See [Technical Documentation](docs/technical-documentation.md) for security architecture details.

---

## Accessibility

KoNote Web follows **WCAG 2.2 AA** guidelines:

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

- **[Dr. David Gotlib](https://www.canhealth.com/2016/11/02/physician-created-konote-makes-it-easy-to-chart-notes-and-numbers/)** — Creator of the original KoNote concept
- **[LogicalOutcomes](https://github.com/LogicalOutcomes)** — Stewards of the original KoNote project
- **[Pico CSS](https://picocss.com/)** — Minimal CSS framework
- **[HTMX](https://htmx.org/)** — HTML extensions for dynamic interactions
- **[Chart.js](https://www.chartjs.org/)** — Progress visualisation

---

## Support

- **Documentation issues**: Open an issue in this repository
- **Security vulnerabilities**: Please report privately to [your contact email]
- **General questions**: See the [Agency Setup Guide](docs/agency-setup.md)
