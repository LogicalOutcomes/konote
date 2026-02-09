# Participant Portal — Design Document

## Vision

A secure, participant-facing portal where people enrolled in nonprofit programs can track their own progress, see their goals, celebrate milestones, and optionally add their own reflections. Designed *for* participants, not as a window into staff records.

This is client-informed practice: participants are partners in their own journey, not passive subjects of case management.

## What the participant sees (and doesn't see)

### They DO see

| Data | Source in KoNote | Why |
|------|-----------------|-----|
| Their goals (in their own words) | `PlanTarget.client_goal` | "I want to find stable housing" — their words, their goals |
| Progress descriptors over time | `ProgressNoteTarget.progress_descriptor` | "Holding steady" → "Something's shifting" → "In a good place" |
| Metric scores as charts | `MetricValue.value` + `MetricDefinition` | Visual progress on outcomes like housing stability, PHQ-9, etc. |
| Their reflections (captured by staff) | `ProgressNote.participant_reflection` | What they said they're taking away from sessions |
| Their suggestions | `ProgressNote.participant_suggestion` | What they suggested for program improvement |
| What they said about each goal | `ProgressNoteTarget.client_words` | Their own words about their goals, captured during sessions |
| Active plan sections | `PlanSection.name` | "Social Skills", "Employment Goals" — section names only |
| Target names and descriptions | `PlanTarget.name`, `PlanTarget.description` | The goal itself (not staff-internal notes about it) |
| Milestones reached | Completed `PlanTarget` entries | Celebration of achievements |
| Group/project participation | `GroupMembership` (their own groups only) | Which groups they're in, upcoming sessions |
| Project milestones | `ProjectMilestone` (their groups only) | Progress on projects they're part of |

### They DO NOT see

| Data | Why not |
|------|---------|
| Staff progress notes (`notes_text`, `summary`) | Clinical observations for staff continuity — not for participants |
| Engagement observations | "Disengaged", "Going through the motions" — staff's clinical assessment |
| Staff-to-staff alerts | Safety information about the participant |
| Events and timeline | May contain sensitive safety information |
| Other participants' data | Obviously — but architecturally enforced, not just filtered |
| Group session notes | Staff observations about group dynamics |
| Group session highlights | Staff observations about individual behaviour in groups |
| Other group members' names | Privacy — participants shouldn't know who else is in their group via the portal |
| Custom field intake data | Demographics, immigration status, etc. — sensitive intake information |

## Architecture

### Principle: Complete separation

The participant portal is a **separate application** within the Django project, with its own:
- User model (`ParticipantUser` — not the staff `User`)
- Authentication backend
- URL namespace (`/my/`)
- Middleware path
- Templates directory
- Session configuration (shorter timeout)

Staff and participant auth systems never cross. A participant URL never resolves to a staff view. A staff URL never resolves to a participant view.

### New Django app: `apps/portal/`

```
apps/portal/
    __init__.py
    models.py          # ParticipantUser, PortalInvite, ParticipantReflection
    views.py           # Dashboard, goals, progress, reflections
    forms.py           # Login, password reset, reflection form
    urls.py            # All under /my/
    middleware.py       # ParticipantSessionMiddleware
    backends.py        # ParticipantAuthBackend
    templatetags/
        portal_tags.py # Template helpers
    templates/portal/
        base_portal.html     # Standalone base (like login.html — doesn't extend staff base.html)
        login.html
        dashboard.html
        goals.html
        goal_detail.html
        progress_chart.html
        reflections.html
        settings.html
```

### Data model

```python
class ParticipantUser(AbstractBaseUser):
    """
    A participant's login account. Completely separate from staff User.

    One-to-one link to ClientFile. The participant can ONLY access
    data belonging to their linked ClientFile — this is structural,
    not just filtered.
    """
    client_file = models.OneToOneField(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="portal_account",
    )
    email_hash = models.CharField(max_length=64, unique=True, db_index=True)
    _email_encrypted = models.BinaryField(default=b"")
    display_name = models.CharField(max_length=255)  # Preferred name, set at invite

    is_active = models.BooleanField(default=True)
    preferred_language = models.CharField(max_length=10, default="en")

    # MFA — required, not optional
    totp_secret_encrypted = models.BinaryField(default=b"", blank=True)
    mfa_confirmed = models.BooleanField(default=False)

    # Security
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_count = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email_hash"  # Login by email, stored as hash

    class Meta:
        db_table = "portal_participant_users"


class PortalInvite(models.Model):
    """
    Staff-initiated invite for a participant to join the portal.

    Invite-only — no self-registration. Staff must explicitly grant
    portal access, which requires the participant's informed consent.
    """
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Staff user
        on_delete=models.SET_NULL,
        null=True,
    )
    token = models.CharField(max_length=64, unique=True)  # Cryptographic token

    # Consent tracking
    consent_explained = models.BooleanField(default=False)  # Staff confirmed they explained
    consent_document_version = models.CharField(max_length=20)

    status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ], default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # 7 days from creation
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "portal_invites"


class ParticipantReflection(models.Model):
    """
    A reflection written by the participant themselves (not by staff).

    Separate from ProgressNote.participant_reflection, which is
    captured BY STAFF during sessions. This is the participant's
    own journal entry, written in the portal.
    """
    participant_user = models.ForeignKey(
        ParticipantUser,
        on_delete=models.CASCADE,
        related_name="reflections",
    )
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
    )
    plan_target = models.ForeignKey(
        "plans.PlanTarget",
        on_delete=models.SET_NULL,
        null=True, blank=True,  # Can be a general reflection not tied to a goal
    )
    _content_encrypted = models.BinaryField(default=b"")
    created_at = models.DateTimeField(auto_now_add=True)

    # Visible to staff? Participant controls this.
    share_with_staff = models.BooleanField(default=False)

    class Meta:
        db_table = "portal_participant_reflections"
        ordering = ["-created_at"]
```

### Security architecture

#### Layer 1: Structural isolation

Every portal view starts with the same pattern:

```python
def get_participant_client(request):
    """Return the ONE ClientFile this participant can access.

    This is not a queryset filter — it's a direct FK lookup.
    There is no way to pass a different client_id.
    """
    return request.participant_user.client_file
```

There is **no client_id in any portal URL**. The participant doesn't choose which client to view — the system knows who they are from their login. This makes cross-participant data leaks structurally impossible (not just "filtered out").

Example URL patterns:
```
/my/                    → Dashboard (their data only)
/my/goals/              → Their plan targets
/my/goals/<target_id>/  → Detail for one of THEIR targets (validated)
/my/progress/           → Their metric charts
/my/reflections/        → Their journal entries
/my/settings/           → Language, password, MFA
```

For target_id, the view validates:
```python
target = get_object_or_404(
    PlanTarget,
    pk=target_id,
    client_file=request.participant_user.client_file  # Structural constraint
)
```

#### Layer 2: Separate authentication

- `ParticipantAuthBackend` — completely separate from staff `ModelBackend`
- Staff login URL: `/auth/login/`
- Portal login URL: `/my/login/`
- Different session cookie names (e.g., `portal_sessionid` vs `sessionid`)
- Different session timeout: 15 minutes idle (vs 2 hours for staff)
- Mandatory MFA from day one (TOTP via authenticator app)

#### Layer 3: Middleware enforcement

```python
class ParticipantSessionMiddleware:
    """Enforces portal-specific security rules."""

    def process_request(self, request):
        if request.path.startswith("/my/"):
            # 1. Must be authenticated as ParticipantUser
            # 2. MFA must be confirmed
            # 3. Account must be active
            # 4. Linked ClientFile must be active (not discharged/erased)
            # 5. Session timeout check (15 min idle)
            pass
```

#### Layer 4: Audit logging

Every portal data access logged to the audit database:
- Who (participant_user_id)
- What (which data was viewed: goals, metrics, reflections)
- When (timestamp)
- From where (IP address)
- Context: `portal_access=True` flag to distinguish from staff access

#### Layer 5: Account lifecycle

| Event | What happens |
|-------|-------------|
| Client discharged | Portal account deactivated immediately |
| Client erased | Portal account deleted (CASCADE from ClientFile) |
| Client merged | Portal account transfers to surviving ClientFile |
| Staff revokes access | PortalInvite set to "revoked", account deactivated |
| Participant requests deletion | Account deactivated, staff notified |
| 90 days of inactivity | Account deactivated (reactivation requires new invite) |

### Invite flow

1. Staff member opens a client's record and clicks "Invite to Portal"
2. Staff confirms they've explained what the portal is and obtained consent
3. System generates a cryptographic invite link (valid 7 days)
4. Staff shares the link with the participant (email, text, printed card)
5. Participant clicks link, creates a password, sets up MFA
6. Portal account is created, linked to their ClientFile
7. Audit log records: who invited, when, consent version

### What the dashboard looks like

```
┌─────────────────────────────────────────────────┐
│  Hi, [Preferred Name]! 👋                        │
│  Here's how your journey is going.               │
│                                                   │
│  ┌─────────────────────────────────────────┐     │
│  │  🎯 My Goals                             │     │
│  │                                           │     │
│  │  Housing Stability                        │     │
│  │  "I want to find a safe place to live"    │     │
│  │  ████████████░░░  In a good place ✨      │     │
│  │                                           │     │
│  │  Employment                               │     │
│  │  "Get my resume together"                 │     │
│  │  ████████░░░░░░░  Something's shifting    │     │
│  │                                           │     │
│  │  [See all goals →]                        │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  ┌─────────────────────────────────────────┐     │
│  │  📈 My Progress                          │     │
│  │                                           │     │
│  │  [Chart: Housing Stability over time]     │     │
│  │  Started: 3/10  →  Now: 7/10              │     │
│  │  "You've come a long way!"                │     │
│  │                                           │     │
│  │  [See detailed charts →]                  │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  ┌─────────────────────────────────────────┐     │
│  │  💭 What I've been saying                │     │
│  │                                           │     │
│  │  Jan 15: "I feel like things are          │     │
│  │  starting to click"                       │     │
│  │                                           │     │
│  │  Jan 8: "Still feels hard but I showed    │     │
│  │  up today"                                │     │
│  │                                           │     │
│  │  [Add a reflection →]                     │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  ┌─────────────────────────────────────────┐     │
│  │  🏆 Milestones                           │     │
│  │                                           │     │
│  │  ✅ Completed intake assessment (Jan 3)   │     │
│  │  ✅ Set 3 personal goals (Jan 5)          │     │
│  │  ✅ Housing Stability: reached 7/10!      │     │
│  │  🔲 Employment: resume draft              │     │
│  └─────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

### Mobile-first design

Most nonprofit participants access the internet via phone. The portal must be:
- Mobile-first responsive (Pico CSS handles this well)
- Touch-friendly (large tap targets)
- Low bandwidth (no heavy JS frameworks — server-rendered with HTMX)
- Installable as PWA (add to home screen)
- Works on older devices and slower connections

### Bilingual support

Full EN/FR support using the existing translation infrastructure:
- Language toggle on portal login and settings
- All portal strings wrapped in `{% trans %}` / `{% blocktrans %}`
- SafeLocaleMiddleware already handles language fallback

### Reflection feature (participant writes)

The participant can optionally write their own reflections:
- Free-text entry, optionally linked to a specific goal
- **Share toggle**: participant chooses whether staff can see it
- If shared, appears in the staff view with a clear "Participant wrote this" label
- If private, only visible to the participant in their portal
- Encrypted at rest using the same Fernet encryption
- Cannot be edited by staff (read-only if shared)

## Implementation phases

### Phase A: Foundation (the portal shell)
- New `apps/portal/` Django app
- `ParticipantUser` and `PortalInvite` models
- Separate auth backend and login page
- MFA setup flow (TOTP)
- Basic dashboard showing participant's name and greeting
- Middleware and security infrastructure
- Audit logging for portal access
- Migrations and tests

### Phase B: Goals and progress (the core value)
- Goals page: plan targets with `client_goal` text
- Progress descriptors timeline ("Harder right now" → "In a good place")
- Metric charts using Chart.js (already in the stack)
- Milestones (completed targets)
- "What I've been saying" — display `participant_reflection` and `client_words` from notes

### Phase C: Participant reflections (write capability)
- `ParticipantReflection` model
- Reflection form (with optional goal link)
- Share/private toggle
- Staff-side display of shared reflections
- Reflection history in portal

### Phase D: Polish and lifecycle
- Account deactivation on discharge/erasure
- 90-day inactivity timeout
- Staff-side "Manage portal access" UI
- Progress celebrations (visual milestones, encouraging messages)
- PWA manifest for "add to home screen"
- Accessibility audit (WCAG 2.2 AA)
- Penetration testing

## Privacy and consent considerations

### What consent is needed
- Informed consent before portal access is granted
- Staff must explain: what data is visible, who can see reflections, how to revoke
- Consent version tracked on the invite record
- Participant can revoke at any time (deactivates account)

### PIPEDA / PHIPA compliance
- Participants have a right to access their own personal information
- The portal satisfies this right in a self-service way
- Portal access is voluntary — never mandatory
- Agency retains the right to limit portal access if safety concerns exist (e.g., DV situations where a partner might coerce access)

### Safety considerations
- Staff can revoke portal access immediately if safety concerns arise
- No information about other participants is ever exposed
- Group membership shows group names only, never other members
- If a participant is in a confidential program, the program name should be reviewed before it appears in the portal (some program names reveal diagnosis)

## Questions for expert review

1. **Program name visibility**: Should participants see the names of programs they're enrolled in? Some program names (e.g., "Substance Use Recovery") reveal clinical information that could be seen by someone looking over the participant's shoulder.

2. **Reflection editing**: Should participants be able to edit/delete their own reflections after posting? Or is immutability better for clinical integrity?

3. **Notification to participants**: Should the portal notify participants when new progress data is recorded? (e.g., "Your worker recorded a session on Jan 15 — see your updated progress")

4. **Offline access**: Should there be any offline capability (cached progress data)? This trades convenience for security.

5. **Shared devices**: Many participants access the internet from library computers or shared phones. How aggressive should session timeout be?

6. **Staff visibility of portal usage**: Should staff see when a participant last logged in? This could be useful (engagement indicator) or problematic (surveillance feeling).

7. **Consent for specific data**: Should participants be able to choose which goals/programs are visible in their portal, or is it all-or-nothing?

8. **MFA burden**: TOTP requires a smartphone with an authenticator app. Is this a barrier for the population served? Should email-based MFA be an alternative?
