# Self-Service Registration Feature Design

## Overview

Allow participants (or parents/guardians) to register for programs without staff intervention. Designed for:
- Youth sports and recreation programs
- After-school programs
- Summer camps
- Community enrichment classes
- Drop-in programs

## Design Principles

1. **Mobile-first**: Most registrations happen on phones
2. **No login required**: Public link with hard-to-guess slug
3. **One form, one participant**: Keep it simple (family registration documented as customization)
4. **Manual review by default**: Auto-approve is opt-in for trusted programs
5. **Duplicates flagged, not blocked**: Staff decides whether to merge or create new

## User Stories

1. **Parent registers child for after-school soccer**: Receives link from school flyer, fills out form on phone, child appears in pending queue, staff approves
2. **Adult signs up for fitness class**: Finds program on agency website, completes registration, gets confirmation email when approved
3. **Coordinator at registration table**: Hands tablet to parent, parent fills form, submission creates pending entry
4. **Program manager reviews registrations**: Sees new submissions, approves or rejects with reason

## Data Model

### RegistrationLink

```python
class RegistrationLink(models.Model):
    """A shareable link for self-service program registration."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)  # URL-friendly, hard-to-guess
    title = models.CharField(max_length=255)  # "Summer Soccer 2025 Registration"
    description = models.TextField(blank=True)  # Instructions shown on form

    # Which custom field groups to show on the form
    field_groups = models.ManyToManyField(CustomFieldGroup)

    # Simple options
    auto_approve = models.BooleanField(default=False)  # Skip staff review?
    max_registrations = models.PositiveIntegerField(null=True, blank=True)  # Capacity limit
    closes_at = models.DateTimeField(null=True, blank=True)  # Registration deadline

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

### RegistrationSubmission

```python
class RegistrationSubmission(models.Model):
    """A submitted registration awaiting review or auto-approved."""

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("waitlist", "Waitlisted"),
    ]

    registration_link = models.ForeignKey(RegistrationLink, on_delete=models.CASCADE)

    # Core PII — encrypted like ClientFile
    _first_name_encrypted = models.BinaryField()
    _last_name_encrypted = models.BinaryField()
    _email_encrypted = models.BinaryField(null=True, blank=True)
    _phone_encrypted = models.BinaryField(null=True, blank=True)

    # For duplicate detection without decryption
    email_hash = models.CharField(max_length=64, blank=True, db_index=True)

    # Custom field values stored as JSON
    field_values = models.JSONField(default=dict)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    client_file = models.ForeignKey(ClientFile, null=True, blank=True, on_delete=models.SET_NULL)

    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)  # Required for rejections

    # Property accessors for encrypted fields (like ClientFile)
    @property
    def first_name(self):
        return decrypt_field(self._first_name_encrypted)

    @first_name.setter
    def first_name(self, value):
        self._first_name_encrypted = encrypt_field(value)

    # ... same pattern for last_name, email, phone
```

## URL Structure

```
# Public (no login)
/register/<slug>/                    # Registration form
/register/<slug>/submitted/          # Confirmation page

# Admin (staff login required)
/admin/registration-links/           # List all registration links
/admin/registration-links/create/    # Create new link
/admin/registration-links/<id>/edit/ # Edit link settings
/admin/registration-links/<id>/delete/

/admin/submissions/                  # Review pending submissions
/admin/submissions/<id>/             # View single submission
/admin/submissions/<id>/approve/     # Approve → create client
/admin/submissions/<id>/reject/      # Reject with reason
/admin/submissions/<id>/waitlist/    # Add to waitlist
```

## Workflows

### Creating a Registration Link (Staff)

1. Staff navigates to Admin → Registration Links → Create
2. Selects program (e.g., "After-School Soccer")
3. Enters title and description (shown on public form)
4. Chooses which field groups to include:
   - ☑ Contact Information
   - ☑ Emergency Contact
   - ☑ Parent/Guardian Information
   - ☐ Demographics (not needed for sports)
5. Sets options:
   - ☐ Auto-approve registrations (default: off)
   - Max registrations: 25
   - Closes: 2025-09-01
6. Saves → gets shareable link: `https://agency.KoNote.ca/register/soccer-fall-2025`
7. Shares link on website, flyers, social media

### Submitting a Registration (Public)

1. Parent clicks link on phone
2. Sees form with program title and description
3. Enters participant name
4. Fills required and optional fields
5. Checks consent checkbox: "I agree to the program terms and data collection policy"
6. Submits form
7. Sees confirmation: "Registration received! Reference: REG-2025-0042"
8. If auto-approve enabled: client created immediately
9. If manual review: staff reviews within SLA

### Reviewing Submissions (Staff)

1. Staff sees dashboard notification: "3 new registrations pending"
2. Goes to Admin → Pending Submissions
3. For each submission:
   - Reviews info for completeness
   - System shows duplicate warning if email matches existing client
   - **Approve** → Creates ClientFile, enrols in program, sends confirmation email
   - **Reject** → Requires reason, sends notification email with reason
   - **Waitlist** → Flags as waitlisted, sends "you're on the waitlist" email
4. Submissions pending > 30 days are auto-deleted

### Duplicate Handling

When submission email hash matches an existing client:
1. System shows warning: "Possible match: Jordan Smith (ID: 1234)"
2. Staff can:
   - **Approve as new**: Create separate client record
   - **Merge**: Enrol existing client in program, update fields if needed
   - **Reject**: Already enrolled or duplicate submission

## UI Wireframes

### Public Registration Form

```
┌─────────────────────────────────────────────────────────────┐
│  [Agency Logo]                                              │
│                                                             │
│  After-School Soccer — Fall 2025                            │
│  ─────────────────────────────────────────────────          │
│  Registration for grades 4-6. Sessions run Tuesdays         │
│  and Thursdays, 3:30-5:00pm at Community Centre.            │
│                                                             │
│  ▼ Participant Information                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ First Name *          [________________]              │  │
│  │ Last Name *           [________________]              │  │
│  │ Date of Birth         [____-__-__]                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ▼ Parent/Guardian Contact                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Parent Name *         [________________]              │  │
│  │ Phone *               [________________]              │  │
│  │ Email *               [________________]              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ▼ Emergency Contact                                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Name *                [________________]              │  │
│  │ Phone *               [________________]              │  │
│  │ Relationship          [Parent/Guardian    ▼]         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ☐ I agree to the program terms and data collection policy  │
│    [View full policy]                                       │
│                                                             │
│            [ Submit Registration ]                          │
│                                                             │
│  Registration closes September 1, 2025                      │
│  15 spots remaining                                         │
└─────────────────────────────────────────────────────────────┘
```

### Submission Review (Staff)

```
┌─────────────────────────────────────────────────────────────┐
│  Pending Registrations                              [3 new] │
│  ─────────────────────────────────────────────────          │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚠ Possible duplicate                                  │  │
│  │ Jordan Smith — After-School Soccer                    │  │
│  │ Submitted: Jan 15, 2025 at 3:42pm                     │  │
│  │ Parent: Sarah Smith (sarah@email.com)                 │  │
│  │                                                       │  │
│  │ Matches existing client: Jordan Smith (ID: 1234)      │  │
│  │                                                       │  │
│  │ [View Details]  [Approve New]  [Merge]  [Reject]      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ✓ Ready to review                                     │  │
│  │ Emma Chen — After-School Soccer                       │  │
│  │ Submitted: Jan 15, 2025 at 4:15pm                     │  │
│  │ Parent: Wei Chen (wei.chen@email.com)                 │  │
│  │                                                       │  │
│  │ [View Details]  [Approve]  [Waitlist]  [Reject]       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Technical Considerations

### Security

- **CSRF protection**: Even on public forms
- **Rate limiting**: Max 5 submissions per hour per session (not IP, to handle shared networks)
- **Input validation**: Server-side, not just client-side
- **Slug generation**: Use secrets.token_urlsafe(8) for hard-to-guess URLs

### Privacy (PIPEDA)

- **Purpose statement**: Form shows why data is collected (in description field)
- **Consent**: Single checkbox covering program terms and data collection
- **Retention**: Pending/rejected submissions auto-deleted after 30 days
- **Encryption**: PII fields encrypted at rest, matching ClientFile approach

### Accessibility (AODA/WCAG 2.2 AA)

- **Keyboard navigation**: All fields accessible without mouse
- **Screen reader labels**: Proper ARIA labels on all inputs
- **Error messages**: Clear, specific, associated with fields via aria-describedby
- **Colour contrast**: Meets WCAG 2.2 AA requirements
- **Collapsible sections**: Use `<details>` with keyboard support

### Performance

- **No auth overhead**: Public forms skip session/permission checks
- **Duplicate detection**: Hash-based lookup, O(1) not O(n)
- **Async email**: Don't block submission on email send

## Implementation Phases

### Phase 1: Core Registration Flow (REG1-REG3)

- [ ] RegistrationLink model and admin CRUD
- [ ] RegistrationSubmission model with encryption
- [ ] Public registration form view
- [ ] Form rendering with selected field groups
- [ ] Submission confirmation page

### Phase 2: Review Workflow (REG4-REG5)

- [ ] Pending submissions list for staff
- [ ] Submission detail view
- [ ] Approve action (creates ClientFile, enrols in program)
- [ ] Reject action with required reason
- [ ] Waitlist action
- [ ] Auto-approve option

### Phase 3: Duplicate Detection + Notifications (REG6-REG7)

- [ ] Email hash generation on submission
- [ ] Duplicate warning in review UI
- [ ] Merge workflow (enrol existing client)
- [ ] Email notifications (confirmation, rejection, waitlist)
- [ ] 30-day auto-expiry for pending submissions

## Out of Scope (Document as Customizations)

These features are intentionally not built-in. See `docs/registration-customizations.md` for guidance:

- **Family/multi-participant registration** — Use separate submissions with shared email
- **Email verification** — Add using Django's signing module
- **CAPTCHA** — Integrate Django-reCAPTCHA if spam is a problem
- **Payment integration** — Redirect to external payment after submission
- **Save/resume drafts** — Use localStorage or email-based magic links
- **Capacity reservation (soft holds)** — Implement with Redis if needed
- **Custom email templates** — Override templates in templates/registration/emails/
- **Bulk approve/reject** — Add Django admin actions
- **SLA alerts** — Set up cron job with management command

## Files to Create

### New App: `apps/registration/`

```
apps/registration/
├── __init__.py
├── admin.py
├── apps.py
├── forms.py              # PublicRegistrationForm (dynamic)
├── models.py             # RegistrationLink, RegistrationSubmission
├── urls.py               # Public and admin routes
├── views.py              # Public form views
├── admin_views.py        # Link management, submission review
└── migrations/
```

### Templates

```
templates/registration/
├── public_form.html      # Mobile-friendly registration form
├── submitted.html        # Confirmation page
└── admin/
    ├── link_list.html
    ├── link_form.html
    ├── submission_list.html
    └── submission_detail.html
```

### Modified Files

- `konote/urls.py` — Add registration URLs
- `konote/settings.py` — Add `apps.registration` to INSTALLED_APPS
