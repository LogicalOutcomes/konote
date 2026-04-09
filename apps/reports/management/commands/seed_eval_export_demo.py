"""
Seed demo data for the evaluation export feature.

Sets up the Supported Employment program with enough participants,
demographics, and configuration to demonstrate the full evaluation
export flow. Idempotent — safe to run multiple times.

Run with: python manage.py seed_eval_export_demo
Only runs when DEMO_MODE is enabled.
"""
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.admin_settings.demo_engine import (
    FIRST_NAMES,
    LAST_NAMES,
    TRENDS,
    generate_trend_values,
)
from apps.clients.models import (
    ClientDetailValue,
    ClientFile,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
)
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import (
    PlanSection,
    PlanTarget,
    PlanTargetRevision,
)
from apps.programs.models import Program, UserProgramRole

User = get_user_model()

# Target: 35 participants in Supported Employment
TARGET_PARTICIPANTS = 35

# How many participants should NOT consent to aggregate reporting
# (demonstrates consent filtering in the export)
NON_CONSENTING_COUNT = 3

# How many participants should be discharged
DISCHARGED_COUNT = 6

# Demo users who receive the report.evaluation_export grant. Governance
# model (tasks/eval-export-governance.md): per-user grant only, admins
# are NOT auto-granted. Casey Worker is PM in Supported Employment (the
# program the demo export is wired to), Morgan is PM elsewhere, and Eva
# is the ED who authorises evaluations.
EVAL_EXPORT_GRANTEES = [
    ("demo-worker-1", "Casey Worker"),
    ("demo-manager", "Morgan Manager"),
    ("demo-executive", "Eva Executive"),
]

# Demographic distributions (counts, not percentages, for 35 people)
GENDER_DISTRIBUTION = [
    ("Woman", 16),
    ("Man", 14),
    ("Non-binary and/or gender-diverse", 3),
    ("Prefer not to say", 2),
]

RACIAL_DISTRIBUTION = [
    ('["White"]', 10),
    ('["Black"]', 7),
    ('["South Asian"]', 5),
    ('["East Asian"]', 4),
    ('["Latin American"]', 3),
    ('["Indigenous (First Nations, Inuk/Inuit, Métis)"]', 2),
    ('["Middle Eastern"]', 2),
    ('["Southeast Asian"]', 1),
    ('["Prefer not to say"]', 1),
]

INDIGENOUS_DISTRIBUTION = [
    ('["No"]', 30),
    ('["Yes, First Nations"]', 2),
    ('["Yes, Métis"]', 1),
    ('["Prefer not to say"]', 2),
]

DISABILITY_DISTRIBUTION = [
    ("Yes", 9),
    ("No", 22),
    ("Prefer not to say", 4),
]

# Ontario postal code FSAs — second character determines urban/rural
# 0 = rural, 1-9 = urban
URBAN_FSAS = ["M5V", "M4K", "K1N", "L5B", "N2L", "M6H", "K2P", "L4T"]
RURAL_FSAS = ["K0A", "N0B", "P0A", "L0R"]

# Age distribution for employment programs (days from today)
# 60% age 25-44, 25% age 18-24, 15% age 45-65
AGE_RANGES = [
    ((18 * 365, 24 * 365), 9),   # 18-24
    ((25 * 365, 44 * 365), 21),  # 25-44
    ((45 * 365, 65 * 365), 5),   # 45-65
]

# Note text pools
QUICK_NOTES = [
    "Checked in briefly. Participant is doing well with job search.",
    "Quick follow-up on interview prep from last session.",
    "Discussed resume updates. Will bring revised version next time.",
    "Brief check-in. Shared a job posting that matches their interests.",
    "Short call to confirm next appointment and review action items.",
]

FULL_SUMMARIES = [
    "Reviewed job search strategy and updated resume. Participant has been applying to 2-3 positions per week and had one callback. Discussed interview preparation techniques.",
    "Worked on interview skills through role-play exercises. Participant is more confident speaking about their experience. Set goal to apply for 3 positions this week.",
    "Explored barriers to employment including transportation and childcare. Connected with community resources for transit subsidy. Will follow up next session.",
    "Discussed workplace communication skills. Participant shared a positive experience from volunteer placement. Building transferable skills portfolio.",
    "Reviewed labour market information for target sector. Identified two training opportunities. Participant will register for online course before next session.",
    "Goal-setting session. Participant identified specific employment targets and timeline. Discussed realistic expectations and incremental progress.",
    "Supported with online job applications. Completed three applications together. Participant gaining confidence with digital tools.",
    "Debriefed after a difficult job interview. Processed feelings of disappointment. Reframed as learning experience and identified improvements for next time.",
]

REFLECTIONS = [
    "I feel like I'm making real progress.",
    "It's hard but I'm sticking with it.",
    "I didn't think I could do this but I'm learning.",
    "The interview was scary but I did it.",
    "I'm more confident than when I started.",
    "Some days are harder than others.",
]


def _expand_distribution(distribution):
    """Expand a (value, count) distribution into a flat list and shuffle."""
    items = []
    for value, count in distribution:
        items.extend([value] * count)
    random.shuffle(items)
    return items


class Command(BaseCommand):
    help = "Seed demo data for evaluation export demonstration."

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            self.stdout.write(self.style.WARNING(
                "DEMO_MODE is not enabled. Skipping."
            ))
            return

        with transaction.atomic():
            self._run()

    def _run(self):
        now = timezone.now()

        # 1. Find or verify the Supported Employment program
        program = Program.objects.filter(name="Supported Employment").first()
        if not program:
            self.stdout.write(self.style.ERROR(
                "Supported Employment program not found. "
                "Run generate_demo_data first."
            ))
            return

        self.stdout.write(f"Target program: {program.name} (id={program.pk})")

        # Fast path: if the demo is already set up (target participants
        # reached AND the permission grantees already hold the flag) skip
        # the full idempotent sweep. This matters because `seed` runs on
        # every container startup and the sweep otherwise does ~1-5 s of
        # read + unconditional-write DB work.
        #
        # Correctness depends on handle() wrapping _run() in
        # transaction.atomic() (see line ~160): because the whole run
        # either commits or rolls back, "enrolments at target AND all
        # grantees granted" is a reliable proxy for "every earlier step
        # also finished". If that atomic wrapper is ever removed or
        # narrowed, this short-circuit could skip a partially-seeded
        # state — re-audit the check before relaxing atomicity.
        from apps.auth_app.models import EvaluationExportGrant

        enrolment_count = ClientProgramEnrolment.objects.filter(
            program=program, client_file__is_demo=True,
        ).count()
        granted_count = EvaluationExportGrant.objects.filter(
            user__username__in=[u for u, _ in EVAL_EXPORT_GRANTEES],
            active=True,
        ).count()
        if (
            enrolment_count >= TARGET_PARTICIPANTS
            and granted_count == len(EVAL_EXPORT_GRANTEES)
        ):
            self.stdout.write(
                "  Evaluator Export demo already seeded — skipping."
            )
            return

        # 2. Find the PM worker for this program
        pm_role = UserProgramRole.objects.filter(
            program=program, role="program_manager", status="active",
        ).select_related("user").first()

        worker_role = UserProgramRole.objects.filter(
            program=program, role="staff", status="active",
        ).select_related("user").first()

        worker = (
            (worker_role and worker_role.user)
            or (pm_role and pm_role.user)
        )
        if not worker:
            self.stdout.write(self.style.ERROR(
                "No worker or PM assigned to Supported Employment."
            ))
            return

        # 3. Count existing participants
        existing_enrolments = ClientProgramEnrolment.objects.filter(
            program=program,
            client_file__is_demo=True,
        ).select_related("client_file")

        existing_count = existing_enrolments.count()
        self.stdout.write(f"  Existing participants: {existing_count}")

        needed = max(0, TARGET_PARTICIPANTS - existing_count)

        # 4. Create additional participants if needed
        if needed > 0:
            self._create_participants(program, worker, needed, now)

        # 5. Populate demographics for ALL participants in the program
        self._populate_demographics(program, now)

        # 6. Set consent flags (3 non-consenting)
        self._set_consent_flags(program)

        # 7. Discharge some participants
        self._discharge_participants(program, now)

        # 8. Create plans and notes for new participants
        # (existing participants already have plans/notes from demo engine)
        if needed > 0:
            self._create_plans_and_notes(program, worker, needed, now)

        # 9. Mark Demographics group as evaluation-exportable
        self._configure_exportable_fields()

        # 10. Grant evaluation export permission to demo-manager
        self._grant_permission()

        self.stdout.write(self.style.SUCCESS(
            "\nEvaluation export demo data seeded successfully."
        ))

    def _create_participants(self, program, worker, count, now):
        """Create additional demo clients enrolled in the program."""
        # Find highest existing record ID
        highest = ClientFile.objects.filter(
            is_demo=True, record_id__startswith="DEMO-",
        ).order_by("-record_id").values_list("record_id", flat=True).first()

        start_num = 1
        if highest:
            try:
                start_num = int(highest.split("-")[1]) + 1
            except (IndexError, ValueError):
                pass

        # Build age distribution
        age_pool = []
        for (min_days, max_days), age_count in AGE_RANGES:
            # Scale counts to match needed
            scaled = max(1, round(age_count * count / TARGET_PARTICIPANTS))
            age_pool.extend([(min_days, max_days)] * scaled)
        random.shuffle(age_pool)

        # Track used names to avoid duplicates within this batch.
        # With 30 first names x 30 last names = 900 combos and only
        # ~15 new clients, collisions are unlikely but we check anyway.
        used_names = set()

        created = 0
        for i in range(count):
            # Pick a name not used in this batch
            for _ in range(50):
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                if (first, last) not in used_names:
                    break
            used_names.add((first, last))

            record_id = f"DEMO-{start_num + i:03d}"

            # Age
            if i < len(age_pool):
                min_days, max_days = age_pool[i]
            else:
                min_days, max_days = 25 * 365, 44 * 365
            age_days = random.randint(min_days, max_days)
            dob = (now - timedelta(days=age_days)).strftime("%Y-%m-%d")

            client = ClientFile()
            client.first_name = first
            client.last_name = last
            client.birth_date = dob
            client.record_id = record_id
            client.status = "active"
            client.is_demo = True
            client.consent_given_at = now - timedelta(days=random.randint(1, 30))
            client.consent_type = random.choice(["written", "verbal", "electronic"])
            client.save()

            # Enrollment
            started_at = now - timedelta(days=random.randint(30, 180))
            ClientProgramEnrolment.objects.create(
                client_file=client,
                program=program,
                status="active",
                referral_source=random.choice([
                    "self", "agency_external", "healthcare",
                    "community", "shelter",
                ]),
                primary_worker=worker,
                started_at=started_at,
                consent_to_aggregate_reporting=True,
            )
            created += 1

        self.stdout.write(f"  Created {created} additional participants.")

    def _populate_demographics(self, program, now):
        """Populate demographic custom fields for all program participants."""
        enrolments = ClientProgramEnrolment.objects.filter(
            program=program, client_file__is_demo=True,
        ).select_related("client_file")

        clients = [e.client_file for e in enrolments]
        client_count = len(clients)

        if client_count == 0:
            return

        # Get demographic field definitions
        field_defs = {}
        for name in [
            "Gender Identity", "Racial Identity",
            "Indigenous Identity", "Disability",
        ]:
            fd = CustomFieldDefinition.objects.filter(name=name).first()
            if fd:
                field_defs[name] = fd

        # Also find the Postal Code field for geography QI
        postal_code_fd = CustomFieldDefinition.objects.filter(
            name="Postal Code",
        ).first()
        if not postal_code_fd:
            # Try by validation type
            postal_code_fd = CustomFieldDefinition.objects.filter(
                validation_type="postal_code",
            ).first()

        if not field_defs:
            self.stdout.write(self.style.WARNING(
                "  No demographic field definitions found. "
                "Run seed_intake_fields first."
            ))
            return

        # Build distribution pools scaled to actual client count
        def scale_distribution(dist, target_count):
            """Scale a distribution to target count, preserving proportions."""
            total = sum(c for _, c in dist)
            scaled = []
            remaining = target_count
            for i, (value, count) in enumerate(dist):
                if i == len(dist) - 1:
                    scaled.append((value, remaining))
                else:
                    n = max(1, round(count * target_count / total))
                    n = min(n, remaining)
                    scaled.append((value, n))
                    remaining -= n
            return _expand_distribution(scaled)

        gender_pool = scale_distribution(GENDER_DISTRIBUTION, client_count)
        racial_pool = scale_distribution(RACIAL_DISTRIBUTION, client_count)
        indigenous_pool = scale_distribution(INDIGENOUS_DISTRIBUTION, client_count)
        disability_pool = scale_distribution(DISABILITY_DISTRIBUTION, client_count)

        # Pre-fetch existing values to avoid overwriting hand-crafted data
        existing_values = set(
            ClientDetailValue.objects.filter(
                client_file__in=clients,
                field_def__in=field_defs.values(),
            ).values_list("client_file_id", "field_def_id")
        )

        cdvs_to_create = []
        updated = 0
        skipped = 0

        for idx, client in enumerate(clients):
            for field_name, field_def in field_defs.items():
                if (client.id, field_def.id) in existing_values:
                    skipped += 1
                    continue

                if field_name == "Gender Identity":
                    value = gender_pool[idx % len(gender_pool)]
                elif field_name == "Racial Identity":
                    value = racial_pool[idx % len(racial_pool)]
                elif field_name == "Indigenous Identity":
                    value = indigenous_pool[idx % len(indigenous_pool)]
                elif field_name == "Disability":
                    value = disability_pool[idx % len(disability_pool)]
                else:
                    continue

                cdv = ClientDetailValue(
                    client_file=client, field_def=field_def,
                )
                cdv.set_value(value)
                cdvs_to_create.append(cdv)
                updated += 1

        if cdvs_to_create:
            ClientDetailValue.objects.bulk_create(cdvs_to_create)

        # Ensure all clients have postal codes (for geography QI)
        postal_codes_added = 0
        if postal_code_fd:
            clients_with_postal = set(
                ClientDetailValue.objects.filter(
                    client_file__in=clients,
                    field_def=postal_code_fd,
                ).values_list("client_file_id", flat=True)
            )
            postal_cdvs = []
            for client in clients:
                if client.id not in clients_with_postal:
                    if random.random() < 0.7:
                        fsa = random.choice(URBAN_FSAS)
                    else:
                        fsa = random.choice(RURAL_FSAS)
                    suffix = (
                        f"{random.randint(1,9)}"
                        f"{random.choice('ABCDEFGHJKLMNPRSTVWXYZ')}"
                        f"{random.randint(0,9)}"
                    )
                    cdv = ClientDetailValue(
                        client_file=client, field_def=postal_code_fd,
                    )
                    cdv.set_value(f"{fsa} {suffix}")
                    postal_cdvs.append(cdv)
                    postal_codes_added += 1
            if postal_cdvs:
                ClientDetailValue.objects.bulk_create(postal_cdvs)
        else:
            self.stdout.write(self.style.WARNING(
                "  Postal Code field not found — geography QI won't work."
            ))

        self.stdout.write(
            f"  Demographics: {updated} values set, {skipped} skipped "
            f"(already have data), {postal_codes_added} postal codes added."
        )

    def _set_consent_flags(self, program):
        """Set a few participants to not consent to aggregate reporting."""
        # Use deterministic ordering (last by record_id) so repeated runs
        # always mark the same participants as non-consenting.
        consented = ClientProgramEnrolment.objects.filter(
            program=program,
            client_file__is_demo=True,
        ).order_by("-client_file__record_id")[:NON_CONSENTING_COUNT]

        ids = list(consented.values_list("pk", flat=True))
        updated = ClientProgramEnrolment.objects.filter(
            pk__in=ids,
        ).update(consent_to_aggregate_reporting=False)

        # Ensure the rest are consented
        ClientProgramEnrolment.objects.filter(
            program=program,
            client_file__is_demo=True,
        ).exclude(pk__in=ids).update(consent_to_aggregate_reporting=True)

        self.stdout.write(
            f"  Consent: {updated} participants set to non-consenting, "
            f"rest set to consenting."
        )

    def _discharge_participants(self, program, now):
        """Discharge some participants with realistic exit reasons."""
        # Don't re-discharge already finished ones
        active = ClientProgramEnrolment.objects.filter(
            program=program,
            client_file__is_demo=True,
            status="active",
        )

        already_finished = ClientProgramEnrolment.objects.filter(
            program=program,
            client_file__is_demo=True,
            status="finished",
        ).count()

        to_discharge = max(0, DISCHARGED_COUNT - already_finished)
        if to_discharge == 0:
            self.stdout.write(
                f"  Discharges: already have {already_finished} finished episodes."
            )
            return

        candidates = list(active.order_by("?")[:to_discharge])
        reasons = [
            "completed", "goals_met", "goals_met",
            "withdrew", "lost_contact", "completed",
        ]

        for i, enrolment in enumerate(candidates):
            enrolment.status = "finished"
            enrolment.end_reason = reasons[i % len(reasons)]
            enrolment.ended_at = now - timedelta(days=random.randint(7, 60))
            enrolment.save(update_fields=["status", "end_reason", "ended_at"])

        self.stdout.write(
            f"  Discharged {len(candidates)} participants "
            f"(total finished: {already_finished + len(candidates)})."
        )

    def _create_plans_and_notes(self, program, worker, count, now):
        """Create outcome plans and progress notes for new participants."""
        # Get recently created clients (those without plans)
        clients_with_plans = set(
            PlanSection.objects.filter(
                program=program,
            ).values_list("client_file_id", flat=True)
        )

        new_enrolments = ClientProgramEnrolment.objects.filter(
            program=program,
            client_file__is_demo=True,
        ).exclude(
            client_file_id__in=clients_with_plans,
        ).select_related("client_file")

        # Get metrics for this program via the demo engine helper.
        # MetricDefinition isn't directly linked to programs — it's linked
        # through note templates, so we use discover_metrics_for_program.
        from apps.admin_settings.demo_engine import DemoDataEngine
        engine = DemoDataEngine()
        metrics = engine.discover_metrics_for_program(program)

        if not metrics:
            self.stdout.write(self.style.WARNING(
                "  No metrics found for Supported Employment. "
                "Notes will be created without metric values."
            ))

        plans_created = 0
        notes_created = 0

        for enrolment in new_enrolments:
            client = enrolment.client_file
            trend = random.choices(
                TRENDS, weights=[40, 20, 20, 10, 10], k=1,
            )[0]

            # Create plan with 2 sections
            targets_with_metrics = []

            section1 = PlanSection.objects.create(
                client_file=client,
                name="Employment Goals",
                program=program,
                sort_order=0,
            )
            target1 = PlanTarget.objects.create(
                plan_section=section1,
                client_file=client,
                name="Find stable employment",
                description="Work toward finding and keeping a job that matches skills and interests.",
                goal_source="joint",
                goal_source_method="heuristic",
                sort_order=0,
            )
            PlanTargetRevision.objects.create(
                plan_target=target1,
                name=target1.name,
                description=target1.description,
                status="default",
                changed_by=worker,
            )

            section2 = PlanSection.objects.create(
                client_file=client,
                name="Personal Well-being",
                program=program,
                sort_order=1,
            )
            target2 = PlanTarget.objects.create(
                plan_section=section2,
                client_file=client,
                name="Build confidence for job search",
                description="Strengthen belief in ability to succeed in employment.",
                goal_source="joint",
                goal_source_method="heuristic",
                sort_order=0,
            )
            PlanTargetRevision.objects.create(
                plan_target=target2,
                name=target2.name,
                description=target2.description,
                status="default",
                changed_by=worker,
            )

            # Assign metrics to targets
            if len(metrics) >= 2:
                targets_with_metrics = [
                    (target1, metrics[:2]),
                    (target2, metrics[2:3] if len(metrics) > 2 else []),
                ]
            elif metrics:
                targets_with_metrics = [(target1, metrics)]
            else:
                targets_with_metrics = [(target1, []), (target2, [])]

            plans_created += 1

            # Create progress notes
            note_count = random.randint(7, 12)
            days_span = (now - enrolment.started_at).days or 90
            note_days = sorted(
                [random.randint(0, max(1, days_span - 5)) for _ in range(note_count)],
                reverse=True,
            )

            # Pre-generate metric value sequences
            metric_sequences = {}
            for target, target_metrics in targets_with_metrics:
                for md in target_metrics:
                    key = (target.pk, md.pk)
                    metric_sequences[key] = generate_trend_values(
                        trend, note_count, md.name, md,
                    )

            for note_idx, days_ago in enumerate(note_days):
                is_quick = note_idx % 3 == 0
                backdate = now - timedelta(
                    days=days_ago, hours=random.randint(8, 17),
                )

                progress_fraction = note_idx / max(note_count - 1, 1)
                if progress_fraction < 0.3:
                    engagement = "guarded"
                elif progress_fraction < 0.6:
                    engagement = "engaged"
                else:
                    engagement = "valuing"

                note = ProgressNote.objects.create(
                    client_file=client,
                    note_type="quick" if is_quick else "full",
                    interaction_type=random.choice(
                        ["session", "session", "phone", "home_visit"],
                    ),
                    author=worker,
                    author_program=program,
                    episode=enrolment,
                    backdate=backdate,
                    notes_text=(
                        random.choice(QUICK_NOTES) if is_quick else ""
                    ),
                    summary=(
                        "" if is_quick else random.choice(FULL_SUMMARIES)
                    ),
                    engagement_observation=engagement,
                )
                ProgressNote.objects.filter(pk=note.pk).update(
                    created_at=backdate,
                )

                # Add reflection to some full notes
                if not is_quick and note_idx % 2 == 0:
                    note.participant_reflection = random.choice(REFLECTIONS)
                    note.save()

                notes_created += 1

                # Record metrics on full notes
                if not is_quick:
                    for target, target_metrics in targets_with_metrics:
                        pnt = ProgressNoteTarget.objects.create(
                            progress_note=note,
                            plan_target=target,
                        )
                        for md in target_metrics:
                            key = (target.pk, md.pk)
                            sequence = metric_sequences.get(key, [])
                            if note_idx < len(sequence):
                                MetricValue.objects.create(
                                    progress_note_target=pnt,
                                    metric_def=md,
                                    value=str(sequence[note_idx]),
                                )

        self.stdout.write(
            f"  Created {plans_created} plans and {notes_created} notes "
            f"for new participants."
        )

    def _configure_exportable_fields(self):
        """Mark the Demographics custom field group as evaluation-exportable."""
        updated = CustomFieldGroup.objects.filter(
            title="Demographics",
        ).update(is_evaluation_exportable=True)

        if updated:
            self.stdout.write("  Marked Demographics group as evaluation-exportable.")
        else:
            self.stdout.write(self.style.WARNING(
                "  Demographics custom field group not found."
            ))

    def _grant_permission(self):
        """Grant report.evaluation_export to each user in EVAL_EXPORT_GRANTEES.

        Creates `EvaluationExportGrant` rows (not direct flag writes)
        so the demo mirrors the real governance flow: every grant has a
        reason and a granting admin in the audit trail. The post_save
        signal on the grant model updates `User.evaluation_export_granted`.
        """
        from apps.auth_app.models import EvaluationExportGrant

        demo_reason = (
            "Demo seed: pre-authorised for DEMO_MODE evaluation export "
            "walkthrough. Replace with a real ED authorisation before "
            "using this flow with live data."
        )

        # Pick a seeded admin to attribute the grants to. Fall back to
        # the first admin if the expected demo admin is missing.
        demo_admin = (
            User.objects.filter(username="demo-admin").first()
            or User.objects.filter(is_admin=True).order_by("pk").first()
        )

        for username, display_name in EVAL_EXPORT_GRANTEES:
            user = User.objects.filter(username=username).first()
            if not user:
                self.stdout.write(self.style.WARNING(
                    f"  {username} user not found."
                ))
                continue

            existing = EvaluationExportGrant.objects.filter(
                user=user, active=True,
            ).first()
            if existing:
                self.stdout.write(
                    f"  {display_name} ({username}) already has an "
                    f"active evaluation export grant."
                )
                continue

            EvaluationExportGrant.objects.create(
                user=user,
                granted_by=demo_admin,
                reason=demo_reason,
            )
            self.stdout.write(
                f"  Granted evaluation export permission to "
                f"{display_name} ({username})."
            )
