"""
Configuration-aware demo data engine for KoNote.

Generates demo data (users, clients, plans, notes, events, etc.) that matches
the instance's actual configuration — programs, metrics, plan templates, and
surveys — rather than using hardcoded demo data.

Two layers:
  Layer 1 (Generic): Auto-generates plausible demo data from whatever is
    configured. Works with zero authoring.
  Layer 2 (Profile): Reads an optional JSON profile file that provides richer
    content — client personas, note text pools, suggestion themes — keyed to
    program names.

Usage:
  python manage.py generate_demo_data [--profile path/to/profile.json]
"""
import json
import logging
import random
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import Alert, Event, EventType
from apps.notes.models import (
    MetricValue,
    ProgressNote,
    ProgressNoteTarget,
    ProgressNoteTemplateMetric,
    SuggestionTheme,
)
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
    PlanTargetRevision,
    PlanTemplate,
)
from apps.programs.models import Program, UserProgramRole

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generic trend value generators (extracted from seed_demo_data.py)
# ---------------------------------------------------------------------------

TRENDS = ("improving", "struggling", "stable", "mixed", "crisis_then_improving")

# Metrics where lower values = better outcome (invert trend direction)
LOWER_IS_BETTER_KEYWORDS = (
    "phq", "gad", "k10", "distress", "shelter", "cravings",
)


def _is_lower_is_better(metric_name):
    """Heuristic: check if a metric name suggests lower is better."""
    name_lower = metric_name.lower()
    return any(kw in name_lower for kw in LOWER_IS_BETTER_KEYWORDS)


def generate_achievement_values(trend, count, metric_def):
    """Generate a list of achievement option strings that follow a realistic trend.

    For achievement metrics, returns categorical values (e.g. "Placed — full-time")
    with probability weighted by the trend direction.
    """
    options = metric_def.achievement_options or []
    success_values = set(metric_def.achievement_success_values or [])
    if not options:
        return [""] * count

    non_success = [o for o in options if o not in success_values]
    success = [o for o in options if o in success_values]

    values = []
    for i in range(count):
        t = i / max(count - 1, 1)

        if trend == "improving":
            success_prob = 0.1 + 0.7 * t
        elif trend == "struggling":
            success_prob = 0.15 - 0.05 * t
        elif trend == "mixed":
            success_prob = 0.3 + 0.2 * (1 if i % 3 == 2 else -1) * t
        elif trend == "crisis_then_improving":
            if t < 0.3:
                success_prob = 0.05
            else:
                recovery_t = (t - 0.3) / 0.7
                success_prob = 0.05 + 0.65 * recovery_t
        elif trend == "stable":
            success_prob = 0.6
        else:
            success_prob = 0.3

        success_prob = max(0.0, min(1.0, success_prob))

        if random.random() < success_prob and success:
            values.append(random.choice(success))
        elif non_success:
            values.append(random.choice(non_success))
        else:
            values.append(random.choice(options))

    return values


def generate_trend_values(trend, count, metric_name, metric_def):
    """Generate a list of metric values that follow a realistic trend."""
    if metric_def.metric_type == "achievement":
        return generate_achievement_values(trend, count, metric_def)

    lo = metric_def.min_value or 0
    hi = metric_def.max_value or 100
    lower_is_better = _is_lower_is_better(metric_name)

    values = []
    for i in range(count):
        t = i / max(count - 1, 1)

        if trend == "improving":
            if lower_is_better:
                base = hi * 0.7 + (hi * 0.2 - hi * 0.7) * t
            else:
                base = lo + (hi - lo) * (0.25 + 0.5 * t)
        elif trend == "struggling":
            if lower_is_better:
                base = hi * 0.5 + (hi * 0.1) * t
            else:
                base = lo + (hi - lo) * (0.35 - 0.1 * t)
        elif trend == "mixed":
            if i % 3 == 0:
                base = lo + (hi - lo) * 0.5
            elif i % 3 == 1:
                base = lo + (hi - lo) * 0.35
            else:
                base = lo + (hi - lo) * 0.6
            if lower_is_better:
                base = hi - base + lo
        elif trend == "crisis_then_improving":
            if t < 0.3:
                if lower_is_better:
                    base = hi * 0.8
                else:
                    base = lo + (hi - lo) * 0.15
            else:
                recovery_t = (t - 0.3) / 0.7
                if lower_is_better:
                    base = hi * 0.8 - (hi * 0.5) * recovery_t
                else:
                    base = lo + (hi - lo) * (0.15 + 0.55 * recovery_t)
        elif trend == "stable":
            if lower_is_better:
                base = lo + (hi - lo) * 0.2
            else:
                base = lo + (hi - lo) * 0.75
        else:
            base = lo + (hi - lo) * 0.5

        noise = (hi - lo) * 0.08 * (random.random() - 0.5)
        val = base + noise
        val = max(lo, min(hi, val))

        if metric_def.unit in (
            "days", "nights", "hours", "applications",
            "meals", "sessions", "connections",
        ):
            val = int(round(val))
        elif metric_def.unit == "$":
            val = round(val / 50) * 50
        elif metric_def.unit == "%":
            val = round(val)
        else:
            val = round(val, 1)

        values.append(val)

    return values


# ---------------------------------------------------------------------------
# Name bank for generating demo client personas
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Jordan", "Taylor", "Avery", "Sam", "Kai", "Jesse", "Jayden", "Maya",
    "Zara", "Amara", "Fatima", "Carlos", "Priya", "Liam", "Nadia",
    "Riley", "Morgan", "Quinn", "Alex", "Rowan", "Ellis", "Sage",
    "Harper", "Blake", "Drew", "Reese", "Skyler", "Finley", "Emery", "Dakota",
]

LAST_NAMES = [
    "Rivera", "Chen", "Osei", "Williams", "Dubois", "Morales", "Martinez",
    "Thompson", "Ahmed", "Diallo", "Hassan", "Reyes", "Sharma", "O'Connor",
    "Kovac", "Nguyen", "Kim", "Patel", "Singh", "Campbell", "Wilson",
    "Garcia", "Lee", "Robinson", "Clark", "Hall", "Young", "Hill", "Scott",
    "Torres",
]

# Generic goal statements that work for any program
GENERIC_GOALS = [
    "I want to feel more in control of my life",
    "I want things to be more stable than they are right now",
    "I want to feel like I'm making progress, even if it's slow",
    "I want to be able to do more things on my own",
    "I want to feel better about where I'm headed",
    "I want to stop worrying so much about the future",
    "I want to build something I can be proud of",
    "I want to feel safe and supported while I figure things out",
    "I want to feel less stuck and more like I'm moving forward",
    "I want to get to a place where things feel manageable",
]

# ---------------------------------------------------------------------------
# Generic note text pools by service model
# ---------------------------------------------------------------------------

INDIVIDUAL_QUICK_NOTES = [
    "Brief check-in. Reports feeling more positive this week.",
    "Phone call to confirm next appointment.",
    "Quick follow-up on action items from last session.",
    "Client dropped in to share some good news.",
    "Left voicemail about upcoming workshop opportunity.",
    "Brief check-in after missed appointment. Will reschedule.",
    "Quick call to discuss next steps in current plan.",
    "Client called with a question about services.",
]

INDIVIDUAL_FULL_SUMMARIES = [
    "Session focused on reviewing progress toward goals. Client identified areas of strength and areas still needing work.",
    "Worked through action plan for the coming week. Client feeling more confident about next steps.",
    "Reviewed current situation and adjusted goals based on recent changes. Good engagement throughout.",
    "Follow-up session. Discussed barriers encountered since last meeting and brainstormed solutions together.",
    "Goal-setting session. Client articulated clear priorities and identified resources to support them.",
    "Check-in session. Client reported steady progress. Celebrated small wins and discussed what's helping.",
    "Session focused on skill-building. Practised strategies that can be used independently between sessions.",
    "Monthly review. Looked at overall trajectory and made minor adjustments to the plan.",
]

GROUP_QUICK_NOTES = [
    "Quick check-in during group activity. In good spirits today.",
    "Arrived a few minutes late but engaged well once settled.",
    "Brief chat after session. Seemed quieter than usual.",
    "Participated actively in today's group discussion.",
    "Helped set up for the activity without being asked.",
    "Quick debrief after group. Good energy today.",
    "Brief check-in. Smaller group today but high engagement.",
    "Mentioned wanting to try something new in next session.",
]

GROUP_FULL_SUMMARIES = [
    "Group session. Participant engaged well with peers and contributed to the discussion.",
    "Attended full session. Showed good rapport with other group members. Practised new skills.",
    "Group activity. Took initiative in organising the activity. Growing confidence in social settings.",
    "Session focused on building connections. Participant shared personal experience with the group.",
    "Group discussion. Participant was quieter today but stayed for the full session.",
    "Productive session. Good teamwork observed. Participant offered to help newer members.",
    "End-of-session check-in. Participant reflected on what they gained from today's activity.",
    "Session went well. Participant asked questions and showed curiosity about next week's topic.",
]

# Generic client words (program-agnostic)
CLIENT_WORDS_POOL = [
    "It's hard right now and I don't know if I can keep going with this",
    "I don't know if this is working but I'm trying to stay with it",
    "I almost didn't come today but I'm glad I made myself show up",
    "I showed up today even though everything in me wanted to stay home",
    "I'm trying to take it one day at a time like we talked about",
    "It's getting a bit easier now that I have a plan to follow",
    "I actually wanted to come today which is new for me",
    "Something feels different this time like maybe things are actually changing",
    "I told my friend about what we talked about and they said it made sense",
    "I'm starting to believe this might actually work out for me",
]

PARTICIPANT_REFLECTIONS_POOL = [
    "I think the biggest thing I'm learning is that it's okay to ask for help",
    "Today I realised I've actually come a long way since we started",
    "I want to keep practising what we talked about because it really does make a difference",
    "I feel like I'm finally starting to understand what I need to do to move forward",
    "The hardest part is still showing up but once I'm here I always feel better",
]

GENERIC_SUGGESTIONS = [
    "It would help to have more flexibility in scheduling",
    "I think having a buddy system would help new people feel less alone at the start",
    "It would be nice to have some written materials I can take home and review later",
    "More evening or weekend options would make it easier for me to attend",
]


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

class DemoDataEngine:
    """Generate configuration-aware demo data for any KoNote instance.

    Reads the actual configured programs, metrics, plan templates, and surveys
    from the database, then creates demo users, clients, plans, notes, events,
    and other data that matches the instance's configuration.
    """

    def __init__(self, stdout=None, stderr=None):
        self.stdout = stdout
        self.stderr = stderr
        self.now = timezone.now()

    def log(self, msg):
        if self.stdout:
            self.stdout.write(msg)
        else:
            logger.info(msg)

    def log_warning(self, msg):
        if self.stderr:
            self.stderr.write(msg)
        else:
            logger.warning(msg)

    # ----- Profile loading -----

    def load_profile(self, profile_path):
        """Load an optional demo data profile JSON. Returns dict or empty dict."""
        if not profile_path:
            return {}
        path = Path(profile_path)
        if not path.exists():
            self.log_warning(f"  Profile not found: {profile_path}. Using auto-generation.")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            profile = json.load(f)
        self.log(f"  Loaded demo data profile: {profile_path}")
        return profile

    # ----- Cleanup -----

    def cleanup_demo_data(self):
        """Remove all existing demo data (users, clients, and cascaded objects)."""
        from apps.communications.models import Communication, StaffMessage
        from apps.events.models import CalendarFeedToken
        from apps.circles.models import Circle
        from apps.portal.models import (
            CorrectionRequest, ParticipantJournalEntry,
            ParticipantMessage, ParticipantUser, StaffPortalNote,
        )
        from apps.registration.models import RegistrationLink, RegistrationSubmission
        from apps.surveys.models import Survey

        demo_clients = ClientFile.objects.filter(is_demo=True)
        demo_users = User.objects.filter(is_demo=True)

        if not demo_clients.exists() and not demo_users.exists():
            self.log("  No existing demo data to clean up.")
            return

        self.log("  Cleaning up existing demo data...")

        # Delete in dependency order
        counts = {}

        # Suggestion themes (linked to Programs via created_by, won't cascade)
        counts["themes"] = SuggestionTheme.objects.filter(
            created_by__is_demo=True
        ).delete()[0]

        # Staff messages
        counts["staff_msgs"] = StaffMessage.objects.filter(
            client_file__is_demo=True
        ).delete()[0]

        # Communications
        counts["comms"] = Communication.objects.filter(
            client_file__is_demo=True
        ).delete()[0]

        # Portal content
        counts["journal"] = ParticipantJournalEntry.objects.filter(
            client_file__is_demo=True
        ).delete()[0]
        counts["portal_msgs"] = ParticipantMessage.objects.filter(
            client_file__is_demo=True
        ).delete()[0]
        counts["staff_notes"] = StaffPortalNote.objects.filter(
            client_file__is_demo=True
        ).delete()[0]
        counts["corrections"] = CorrectionRequest.objects.filter(
            client_file__is_demo=True
        ).delete()[0]

        # Surveys created by demo users
        counts["surveys"] = Survey.objects.filter(
            created_by__is_demo=True
        ).delete()[0]

        # Registration submissions for demo links
        counts["registrations"] = RegistrationSubmission.objects.filter(
            registration_link__slug="demo"
        ).delete()[0]

        # Demo circles
        counts["circles"] = Circle.objects.filter(is_demo=True).delete()[0]

        # Groups are cleaned by CASCADE when demo clients are deleted

        # Calendar feed tokens
        CalendarFeedToken.objects.filter(user__in=demo_users).delete()

        # Registration links
        RegistrationLink.objects.filter(slug="demo").delete()

        # Portal users (must delete before clients because of FK)
        ParticipantUser.objects.filter(client_file__is_demo=True).delete()

        # Delete demo clients — CASCADE handles plans, notes, events, etc.
        client_count = demo_clients.count()
        demo_clients.delete()
        counts["clients"] = client_count

        # Remove program roles for demo users
        UserProgramRole.objects.filter(user__in=demo_users).delete()

        # Delete demo users
        user_count = demo_users.count()
        demo_users.delete()
        counts["users"] = user_count

        self.log(
            f"  Removed {counts['clients']} demo clients, {counts['users']} demo users, "
            f"and associated data."
        )

    # ----- Program discovery -----

    def discover_programs(self):
        """Return all active programs in the instance."""
        programs = list(Program.objects.filter(status="active").order_by("pk"))
        if not programs:
            self.log_warning("  No active programs found. Cannot generate demo data.")
        return programs

    # ----- Metric discovery -----

    def discover_metrics_for_program(self, program):
        """Find metrics associated with a program via its templates.

        Priority:
        1. Metrics from note templates scoped to this program
        2. Metrics from global note templates (owning_program=None)
        3. Universal metrics (Goal Progress, Self-Efficacy, Satisfaction)

        Universal metrics are always included as a baseline.
        """
        metric_ids = set()

        # 1. Plan template targets don't directly link to metrics, but note
        #    templates do via ProgressNoteTemplateMetric. Check note templates
        #    scoped to this program first.
        note_template_metrics = ProgressNoteTemplateMetric.objects.filter(
            template_section__template__owning_program=program,
            template_section__template__status="active",
        ).values_list("metric_def_id", flat=True)
        metric_ids.update(note_template_metrics)

        # 2. Also check global note templates (owning_program=None)
        if not metric_ids:
            global_note_metrics = ProgressNoteTemplateMetric.objects.filter(
                template_section__template__owning_program__isnull=True,
                template_section__template__status="active",
            ).values_list("metric_def_id", flat=True)
            metric_ids.update(global_note_metrics)

        # 3. Fall back to universal metrics
        if not metric_ids:
            universal = MetricDefinition.objects.filter(
                is_universal=True, is_enabled=True,
            ).values_list("pk", flat=True)
            metric_ids.update(universal)

        # Also always include universals to ensure at least some metrics
        universal_ids = set(
            MetricDefinition.objects.filter(
                is_universal=True, is_enabled=True,
            ).values_list("pk", flat=True)
        )
        metric_ids.update(universal_ids)

        metrics = list(
            MetricDefinition.objects.filter(
                pk__in=metric_ids, is_enabled=True,
            ).order_by("pk")
        )
        return metrics

    # ----- Plan template discovery -----

    def discover_plan_template(self, program):
        """Find a plan template for the program (program-scoped first, then global)."""
        template = PlanTemplate.objects.filter(
            owning_program=program, status="active",
        ).first()
        if not template:
            template = PlanTemplate.objects.filter(
                owning_program__isnull=True, status="active",
            ).first()
        return template

    # ----- Demo user creation -----

    def create_demo_users(self, programs):
        """Create 6 demo users with roles distributed across programs.

        Returns a dict of {username: User}.
        """
        import os

        email_base = os.environ.get("DEMO_EMAIL_BASE", "")

        def demo_email(username):
            if email_base and "@" in email_base:
                local, domain = email_base.split("@", 1)
                return f"{local}+{username}@{domain}"
            return f"{username}@example.com"

        user_specs = [
            ("demo-frontdesk", "Dana Front Desk", False),
            ("demo-worker-1", "Casey Worker", False),
            ("demo-worker-2", "Noor Worker", False),
            ("demo-manager", "Morgan Manager", False),
            ("demo-executive", "Eva Executive", False),
            ("demo-admin", "Alex Admin", True),
        ]

        users = {}
        for username, display_name, is_admin in user_specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "display_name": display_name,
                    "is_admin": is_admin,
                    "is_demo": True,
                    "email": demo_email(username),
                    "preferred_language": "en",
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()
            else:
                # Ensure existing users have is_demo=True and is_active=True
                if not user.is_demo or not user.is_active:
                    user.is_demo = True
                    user.is_active = True
                    user.save()
            users[username] = user

        # Assign roles across programs
        front_desk = users["demo-frontdesk"]
        worker1 = users["demo-worker-1"]
        worker2 = users["demo-worker-2"]
        manager = users["demo-manager"]
        executive = users["demo-executive"]

        # Front desk: receptionist on all programs
        for prog in programs:
            UserProgramRole.objects.get_or_create(
                user=front_desk, program=prog,
                defaults={"role": "receptionist"},
            )

        # Executive: executive on all programs
        for prog in programs:
            UserProgramRole.objects.get_or_create(
                user=executive, program=prog,
                defaults={"role": "executive"},
            )

        # Distribute workers and manager across programs
        if len(programs) == 1:
            # Single program: both workers + manager
            for worker in (worker1, worker2):
                UserProgramRole.objects.get_or_create(
                    user=worker, program=programs[0],
                    defaults={"role": "staff"},
                )
            UserProgramRole.objects.get_or_create(
                user=manager, program=programs[0],
                defaults={"role": "program_manager"},
            )
        elif len(programs) == 2:
            # Two programs: split workers
            UserProgramRole.objects.get_or_create(
                user=worker1, program=programs[0],
                defaults={"role": "staff"},
            )
            UserProgramRole.objects.get_or_create(
                user=worker2, program=programs[1],
                defaults={"role": "staff"},
            )
            for prog in programs:
                UserProgramRole.objects.get_or_create(
                    user=manager, program=prog,
                    defaults={"role": "program_manager"},
                )
        else:
            # 3+ programs: split workers, manager on first half
            mid = len(programs) // 2
            for prog in programs[:mid]:
                UserProgramRole.objects.get_or_create(
                    user=worker1, program=prog,
                    defaults={"role": "staff"},
                )
            for prog in programs[mid:]:
                UserProgramRole.objects.get_or_create(
                    user=worker2, program=prog,
                    defaults={"role": "staff"},
                )
            # Worker1 also gets program_manager on first program
            role = UserProgramRole.objects.filter(
                user=worker1, program=programs[0],
            ).first()
            if role:
                role.role = "program_manager"
                role.save(update_fields=["role"])
            # Manager on first half of programs
            for prog in programs[:mid + 1]:
                UserProgramRole.objects.get_or_create(
                    user=manager, program=prog,
                    defaults={"role": "program_manager"},
                )

        self.log(f"  Created {len(user_specs)} demo users with roles across {len(programs)} programs.")
        return users

    # ----- Demo client creation -----

    def create_demo_clients(self, programs, users, clients_per_program, profile):
        """Create demo clients distributed across programs.

        Returns a list of (client, program, trend, worker) tuples.
        """
        profile_programs = profile.get("programs", {})
        client_assignments = []
        used_names = set()
        client_num = 1

        # Determine which worker handles which program
        program_workers = {}
        for prog in programs:
            # Check which worker has a role on this program
            for username in ("demo-worker-1", "demo-worker-2"):
                if UserProgramRole.objects.filter(
                    user=users[username], program=prog,
                ).exists():
                    program_workers[prog.pk] = users[username]
                    break
            else:
                program_workers[prog.pk] = users["demo-worker-1"]

        for prog in programs:
            prog_profile = profile_programs.get(prog.name, {})
            personas = prog_profile.get("client_personas", [])
            worker = program_workers[prog.pk]

            for i in range(clients_per_program):
                record_id = f"DEMO-{client_num:03d}"

                # Use persona from profile if available
                if i < len(personas):
                    persona = personas[i]
                    first_name = persona["first_name"]
                    last_name = persona["last_name"]
                    trend = persona.get("trend", TRENDS[i % len(TRENDS)])
                    goal = persona.get("goal_statement", "")
                else:
                    # Generate from name bank
                    first_name, last_name = self._pick_unique_name(used_names)
                    trend = TRENDS[i % len(TRENDS)]
                    goal = ""

                used_names.add((first_name, last_name))

                # Generate a plausible birth date (18-45 years old)
                age_days = random.randint(18 * 365, 45 * 365)
                dob = (self.now - timedelta(days=age_days)).strftime("%Y-%m-%d")

                client = ClientFile()
                client.first_name = first_name
                client.last_name = last_name
                client.birth_date = dob
                client.record_id = record_id
                client.status = "active"
                client.is_demo = True
                client.save()

                ClientProgramEnrolment.objects.create(
                    client_file=client, program=prog, status="active",
                )

                client_assignments.append((client, prog, trend, worker, goal))
                client_num += 1

        self.log(f"  Created {len(client_assignments)} demo clients across {len(programs)} programs.")
        return client_assignments

    def _pick_unique_name(self, used_names):
        """Pick a first/last name combination not already used."""
        for _ in range(100):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            if (first, last) not in used_names:
                return first, last
        # Fallback: append a number
        first = random.choice(FIRST_NAMES)
        return first, f"{random.choice(LAST_NAMES)}-{random.randint(1, 99)}"

    # ----- Plan generation -----

    def generate_plan(self, client, program, metrics, trend, worker, goal, profile):
        """Create a plan for a client using configured templates or generic structure.

        Returns list of (PlanTarget, [MetricDefinition, ...]) tuples.
        """
        template = self.discover_plan_template(program)
        all_targets = []

        if template and template.sections.exists():
            # Use the actual plan template
            for section_tmpl in template.sections.order_by("sort_order"):
                section = PlanSection.objects.create(
                    client_file=client,
                    name=section_tmpl.name,
                    program=program,
                    sort_order=section_tmpl.sort_order,
                )
                for target_tmpl in section_tmpl.targets.order_by("sort_order"):
                    target = PlanTarget.objects.create(
                        plan_section=section,
                        client_file=client,
                        name=target_tmpl.name,
                        description=target_tmpl.description,
                        sort_order=target_tmpl.sort_order,
                    )
                    PlanTargetRevision.objects.create(
                        plan_target=target,
                        name=target.name,
                        description=target.description,
                        status="default",
                        changed_by=worker,
                    )
                    # Distribute metrics across targets
                    target_metrics = self._assign_metrics_to_target(
                        target, metrics, len(all_targets),
                    )
                    all_targets.append((target, target_metrics))
        else:
            # Generic plan structure: one section with 1-2 targets
            section = PlanSection.objects.create(
                client_file=client,
                name=f"{program.name} Goals",
                program=program,
                sort_order=0,
            )
            # Create 1-2 targets
            num_targets = min(2, max(1, len(metrics) // 2))
            for t_idx in range(num_targets):
                target_name = f"Goal {t_idx + 1}"
                target_desc = "Work toward positive outcomes in this area."
                target = PlanTarget.objects.create(
                    plan_section=section,
                    client_file=client,
                    name=target_name,
                    description=target_desc,
                    sort_order=t_idx,
                )
                PlanTargetRevision.objects.create(
                    plan_target=target,
                    name=target.name,
                    description=target.description,
                    status="default",
                    changed_by=worker,
                )
                target_metrics = self._assign_metrics_to_target(
                    target, metrics, t_idx,
                )
                all_targets.append((target, target_metrics))

        # Set client goal on the first target
        if all_targets:
            first_target = all_targets[0][0]
            if goal:
                first_target.client_goal = goal
            else:
                first_target.client_goal = random.choice(GENERIC_GOALS)
            first_target.save()

        return all_targets

    def _assign_metrics_to_target(self, target, metrics, target_index):
        """Distribute metrics across targets and create PlanTargetMetric links."""
        if not metrics:
            return []

        # Give each target a slice of the available metrics
        per_target = max(2, len(metrics) // 2)
        start = (target_index * per_target) % len(metrics)
        assigned = []
        for i in range(per_target):
            md = metrics[(start + i) % len(metrics)]
            if md not in assigned:
                assigned.append(md)

        # Always include at least one universal metric
        universals = [m for m in metrics if m.is_universal]
        if universals and not any(m.is_universal for m in assigned):
            assigned.append(universals[0])

        for m_idx, md in enumerate(assigned):
            PlanTargetMetric.objects.create(
                plan_target=target,
                metric_def=md,
                sort_order=m_idx,
            )

        return assigned

    # ----- Note generation -----

    def generate_notes(self, client, program, all_targets, trend, worker,
                       note_count, days_span, profile):
        """Create progress notes with metric values following a trend pattern."""
        prog_profile = profile.get("programs", {}).get(program.name, {})

        # Choose note text pools
        is_group = program.service_model == "group"
        if prog_profile.get("note_text_pool"):
            full_summaries = prog_profile["note_text_pool"]
            quick_notes = full_summaries[:4] if len(full_summaries) > 4 else full_summaries
        elif is_group:
            quick_notes = GROUP_QUICK_NOTES
            full_summaries = GROUP_FULL_SUMMARIES
        else:
            quick_notes = INDIVIDUAL_QUICK_NOTES
            full_summaries = INDIVIDUAL_FULL_SUMMARIES

        # Client words pool
        client_words = prog_profile.get("client_words_pool", CLIENT_WORDS_POOL)

        # Spread notes over the time span
        note_days = sorted(
            [random.randint(5, days_span - 5) for _ in range(note_count)],
            reverse=True,
        )

        # Pre-generate metric value sequences
        metric_sequences = {}
        for target, target_metrics in all_targets:
            for md in target_metrics:
                key = (target.pk, md.pk)
                metric_sequences[key] = generate_trend_values(
                    trend, note_count, md.name, md,
                )

        # Determine interaction type based on service model
        if program.service_model == "group":
            interaction_types = ["group"]
        elif program.service_model == "both":
            interaction_types = ["session", "session", "group"]
        else:
            interaction_types = ["session", "session", "phone", "home_visit"]

        for note_idx, days_ago in enumerate(note_days):
            is_quick = note_idx % 3 == 0
            note_type = "quick" if is_quick else "full"
            backdate = self.now - timedelta(
                days=days_ago, hours=random.randint(8, 17),
            )
            interaction = random.choice(interaction_types)

            # Engagement observation progresses over time
            progress_fraction = note_idx / max(note_count - 1, 1)
            if progress_fraction < 0.3:
                engagement = "guarded"
            elif progress_fraction < 0.6:
                engagement = "engaged"
            else:
                engagement = "valuing"

            note = ProgressNote.objects.create(
                client_file=client,
                note_type=note_type,
                interaction_type=interaction,
                author=worker,
                author_program=program,
                backdate=backdate,
                notes_text=(
                    random.choice(quick_notes) if is_quick else ""
                ),
                summary=(
                    "" if is_quick else random.choice(full_summaries)
                ),
                engagement_observation=engagement,
            )

            # Backdate created_at
            ProgressNote.objects.filter(pk=note.pk).update(created_at=backdate)

            needs_save = False

            # Add participant reflection to ~half of full notes
            if not is_quick and note_idx % 2 == 0:
                reflection_idx = min(
                    int(progress_fraction * len(PARTICIPANT_REFLECTIONS_POOL)),
                    len(PARTICIPANT_REFLECTIONS_POOL) - 1,
                )
                note.participant_reflection = PARTICIPANT_REFLECTIONS_POOL[reflection_idx]
                needs_save = True

            # Add participant suggestion to ~1/3 of full notes
            if not is_quick and note_idx % 3 == 1:
                suggestions = prog_profile.get("suggestions_pool", GENERIC_SUGGESTIONS)
                suggestion_idx = note_idx % len(suggestions)
                note.participant_suggestion = suggestions[suggestion_idx]
                note.suggestion_priority = random.choice(
                    ["noted", "worth_exploring", "important"],
                )
                needs_save = True

            if needs_save:
                note.save()

            # For full notes, record metrics against each target
            if not is_quick:
                if progress_fraction < 0.3:
                    descriptor = "harder"
                elif progress_fraction < 0.5:
                    descriptor = "holding"
                elif progress_fraction < 0.75:
                    descriptor = "shifting"
                else:
                    descriptor = "good_place"

                words_idx = min(
                    int(progress_fraction * len(client_words)),
                    len(client_words) - 1,
                )

                for target, target_metrics in all_targets:
                    pnt = ProgressNoteTarget.objects.create(
                        progress_note=note,
                        plan_target=target,
                        notes=random.choice(full_summaries),
                        progress_descriptor=descriptor,
                        client_words=client_words[words_idx],
                    )
                    for md in target_metrics:
                        key = (target.pk, md.pk)
                        seq = metric_sequences[key]
                        val = seq[note_idx] if note_idx < len(seq) else seq[-1]
                        MetricValue.objects.create(
                            progress_note_target=pnt,
                            metric_def=md,
                            value=str(val),
                        )

    # ----- Event generation -----

    def generate_events(self, client, program, worker, days_span):
        """Create realistic events for a client."""
        event_types = {et.name: et for et in EventType.objects.all()}

        if not event_types:
            self.log_warning("  No EventType records found — skipping event generation.")
            return

        intake_type = event_types.get("Intake")
        followup_type = event_types.get("Follow-up")

        events_data = []

        # Intake event
        if intake_type:
            events_data.append({
                "type": intake_type,
                "title": f"{program.name} intake",
                "days_ago": days_span - random.randint(5, 15),
            })

        # 2-3 follow-up events
        if followup_type:
            for i in range(random.randint(2, 3)):
                events_data.append({
                    "type": followup_type,
                    "title": f"Follow-up session — check-in",
                    "days_ago": random.randint(10, days_span - 20),
                })

        for evt in events_data:
            Event.objects.create(
                client_file=client,
                title=evt["title"],
                event_type=evt["type"],
                author_program=program,
                start_timestamp=self.now - timedelta(days=evt["days_ago"]),
            )

    # ----- Alert generation -----

    def generate_alerts(self, client_assignments):
        """Create alerts for ~25% of clients (those with struggling/crisis trends)."""
        alert_messages = [
            "Attendance has dropped. Outreach recommended.",
            "Reported significant barrier this week. Follow-up needed.",
            "Situation has become more complex. Team discussion recommended.",
            "Has not attended in two weeks. Check-in call scheduled.",
        ]

        for client, program, trend, worker, _ in client_assignments:
            if trend in ("struggling", "crisis_then_improving"):
                Alert.objects.create(
                    client_file=client,
                    content=random.choice(alert_messages),
                    author=worker,
                    author_program=program,
                )

    # ----- Suggestion theme generation -----

    def generate_suggestion_themes(self, programs, users, profile):
        """Create suggestion themes for each program."""
        profile_programs = profile.get("programs", {})
        creator = users.get("demo-worker-1") or users.get("demo-admin")
        if not creator:
            return

        generic_themes = [
            {
                "name": "Scheduling flexibility",
                "description": "Participants have asked about alternative scheduling options.",
                "status": "open",
            },
            {
                "name": "Peer support connections",
                "description": "Interest in being connected with peers who have similar experiences.",
                "status": "in_progress",
            },
        ]

        for prog in programs:
            prog_profile = profile_programs.get(prog.name, {})
            themes = prog_profile.get("suggestion_themes", generic_themes)

            for theme_data in themes:
                theme, created = SuggestionTheme.objects.get_or_create(
                    program=prog,
                    name=theme_data["name"],
                    defaults={
                        "description": theme_data.get("description", ""),
                        "status": theme_data.get("status", "open"),
                        "source": theme_data.get("source", "manual"),
                        "keywords": theme_data.get("keywords", ""),
                        "created_by": creator,
                    },
                )

    # ----- Main orchestrator -----

    @transaction.atomic
    def run(self, clients_per_program=3, days_span=180, profile_path=None,
            force=False):
        """Generate demo data matching the instance's current configuration.

        Args:
            clients_per_program: Number of demo clients to create per program.
            days_span: Number of days of historical data to generate.
            profile_path: Optional path to a demo data profile JSON.
            force: If True, clear existing demo data before generating.
        """
        random.seed(42)  # Reproducible demo data

        profile = self.load_profile(profile_path)

        # Apply profile defaults
        profile_defaults = profile.get("defaults", {})
        if "clients_per_program" in profile_defaults and clients_per_program == 3:
            clients_per_program = profile_defaults["clients_per_program"]
        if "days_span" in profile_defaults and days_span == 180:
            days_span = profile_defaults["days_span"]

        note_count_range = profile_defaults.get("note_count_range", [7, 12])

        # Check for existing demo data
        existing = ClientFile.objects.filter(is_demo=True).exists()
        if existing and not force:
            self.log("  Demo data already exists. Use --force to regenerate.")
            return False

        if existing and force:
            self.cleanup_demo_data()

        # 1. Discover programs
        programs = self.discover_programs()
        if not programs:
            return False

        # 2. Create demo users
        users = self.create_demo_users(programs)

        # 3. Create demo clients
        client_assignments = self.create_demo_clients(
            programs, users, clients_per_program, profile,
        )

        # 4. For each client: create plan, notes, events
        for client, program, trend, worker, goal in client_assignments:
            metrics = self.discover_metrics_for_program(program)
            note_count = random.randint(note_count_range[0], note_count_range[1])

            # Create plan
            all_targets = self.generate_plan(
                client, program, metrics, trend, worker, goal, profile,
            )

            # Create notes with metric values
            self.generate_notes(
                client, program, all_targets, trend, worker,
                note_count, days_span, profile,
            )

            # Create events
            self.generate_events(client, program, worker, days_span)

            self.log(
                f"  {client.record_id}: {client.first_name} {client.last_name} "
                f"— {program.name} ({trend})"
            )

        # 5. Create alerts for struggling/crisis clients
        self.generate_alerts(client_assignments)

        # 6. Create suggestion themes
        self.generate_suggestion_themes(programs, users, profile)

        # Warn about profile program names that didn't match any active program
        if profile and "programs" in profile:
            active_names = {p.name for p in programs}
            for profile_name in profile["programs"]:
                if profile_name not in active_names:
                    self.log_warning(
                        f"  Profile program '{profile_name}' did not match "
                        f"any active program — its content was not used."
                    )

        total_clients = len(client_assignments)
        self.log(
            f"  Demo data generated: {total_clients} clients across "
            f"{len(programs)} programs."
        )
        return True
