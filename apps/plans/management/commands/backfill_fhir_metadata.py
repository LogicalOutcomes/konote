"""Backfill FHIR metadata on existing records.

Handles three types of backfill:
1. Episode FK on ProgressNotes (deterministic — no AI)
2. Goal source on PlanTargets (heuristic — no AI)
3. Plan section periods (deterministic — no AI)

AI-based inference (goal_source refinement, continuous, target_date extraction)
is handled separately by infer_fhir_metadata command.
"""
from django.core.management.base import BaseCommand
from django.db.models import Min, Max, Q


class Command(BaseCommand):
    help = "Backfill FHIR metadata fields on existing records (deterministic only, no AI)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would change without saving")
        parser.add_argument("--episodes", action="store_true", help="Backfill episode FK on ProgressNotes")
        parser.add_argument("--goals", action="store_true", help="Backfill goal_source on PlanTargets")
        parser.add_argument("--sections", action="store_true", help="Backfill period on PlanSections")
        parser.add_argument("--all", action="store_true", help="Run all backfills")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        run_all = options["all"]

        if run_all or options["episodes"]:
            self._backfill_episodes(dry_run)
        if run_all or options["goals"]:
            self._backfill_goals(dry_run)
        if run_all or options["sections"]:
            self._backfill_sections(dry_run)

        if not any([run_all, options["episodes"], options["goals"], options["sections"]]):
            self.stdout.write("Specify --all or one of --episodes, --goals, --sections")

    def _backfill_episodes(self, dry_run):
        """Link existing ProgressNotes to their ServiceEpisode."""
        from apps.notes.models import ProgressNote
        from apps.clients.models import ServiceEpisode

        notes = ProgressNote.objects.filter(
            episode__isnull=True,
            author_program__isnull=False,
        )
        total = notes.count()
        linked = 0

        self.stdout.write(f"Processing {total} notes without episode link...")

        for note in notes.iterator():
            # Find episode that was active when note was written.
            # Uses date-range matching (not status filter) because historical
            # notes should link to the episode that was active at that time,
            # even if the episode is now finished.
            effective_date = note.backdate or note.created_at
            ep = ServiceEpisode.objects.filter(
                client_file_id=note.client_file_id,
                program_id=note.author_program_id,
                started_at__lte=effective_date,
            ).filter(
                Q(ended_at__isnull=True) | Q(ended_at__gte=effective_date)
            ).order_by("-started_at").first()

            if ep:
                if not dry_run:
                    ProgressNote.objects.filter(pk=note.pk).update(episode=ep)
                linked += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Linked {linked}/{total} notes to episodes"
        ))

    def _backfill_goals(self, dry_run):
        """Apply goal_source heuristic to existing PlanTargets."""
        from apps.plans.models import PlanTarget

        targets = PlanTarget.objects.filter(goal_source="")
        total = targets.count()
        classified = 0

        self.stdout.write(f"Processing {total} targets without goal_source...")

        for target in targets.iterator():
            has_desc = bool(target._description_encrypted and target._description_encrypted != b"")
            has_client = bool(target._client_goal_encrypted and target._client_goal_encrypted != b"")

            source = ""
            if has_client and has_desc:
                source = "joint"
            elif has_client:
                source = "participant"
            elif has_desc:
                source = "worker"

            if source:
                if not dry_run:
                    meta = target.metadata_sources if isinstance(target.metadata_sources, dict) else {}
                    meta["goal_source"] = "heuristic"
                    PlanTarget.objects.filter(pk=target.pk).update(
                        goal_source=source, metadata_sources=meta,
                    )
                classified += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Classified {classified}/{total} targets"
        ))

    def _backfill_sections(self, dry_run):
        """Compute period_start/period_end for PlanSections."""
        from apps.plans.models import PlanSection

        sections = PlanSection.objects.filter(period_start__isnull=True)
        total = sections.count()
        updated = 0

        self.stdout.write(f"Processing {total} sections without period dates...")

        for section in sections.iterator():
            agg = section.targets.aggregate(
                earliest=Min("created_at"), latest=Max("updated_at"),
            )
            if agg["earliest"]:
                period_start = agg["earliest"].date()
                period_end = None
                # Set period_end only if no targets are still active or on hold
                active_count = section.targets.filter(status__in=["default", "on_hold"]).count()
                if active_count == 0 and section.targets.exists():
                    period_end = agg["latest"].date()

                if not dry_run:
                    PlanSection.objects.filter(pk=section.pk).update(
                        period_start=period_start, period_end=period_end,
                    )
                updated += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Updated {updated}/{total} sections"
        ))
