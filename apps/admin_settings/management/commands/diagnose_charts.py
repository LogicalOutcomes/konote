"""Diagnostic command to check chart data availability."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Diagnose why charts might be empty for a client"

    def add_arguments(self, parser):
        parser.add_argument(
            "--client",
            default="DEMO-001",
            help="Client record ID to check (default: DEMO-001)",
        )

    def handle(self, *args, **options):
        from apps.clients.models import ClientFile
        from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
        from apps.plans.models import MetricDefinition, PlanTarget, PlanTargetMetric

        record_id = options["client"]

        # Check metric library
        lib_metrics = MetricDefinition.objects.filter(is_library=True).count()
        self.stdout.write(f"Library metrics: {lib_metrics}")

        total_ptm = PlanTargetMetric.objects.count()
        self.stdout.write(f"Total PlanTargetMetric links: {total_ptm}")

        # Check specific client
        client = ClientFile.objects.filter(record_id=record_id).first()
        if not client:
            self.stdout.write(self.style.ERROR(f"Client {record_id} not found"))
            return

        self.stdout.write(f"\n--- Client: {record_id} ---")

        targets = PlanTarget.objects.filter(client_file=client, status__in=PlanTarget.ACTIVE_STATUSES)
        self.stdout.write(f"Active targets: {targets.count()}")

        for t in targets:
            ptm_count = PlanTargetMetric.objects.filter(plan_target=t).count()
            self.stdout.write(f"  - {t.name}: {ptm_count} metrics linked")

        full_notes = ProgressNote.objects.filter(client_file=client, note_type="full", status="default")
        quick_notes = ProgressNote.objects.filter(client_file=client, note_type="quick", status="default")
        self.stdout.write(f"\nFull notes: {full_notes.count()}")
        self.stdout.write(f"Quick notes: {quick_notes.count()}")

        pnt_count = ProgressNoteTarget.objects.filter(
            progress_note__client_file=client
        ).count()
        self.stdout.write(f"ProgressNoteTarget entries: {pnt_count}")

        mv_count = MetricValue.objects.filter(
            progress_note_target__progress_note__client_file=client
        ).count()
        self.stdout.write(f"MetricValue entries: {mv_count}")

        # Diagnosis
        self.stdout.write("\n--- Diagnosis ---")
        if lib_metrics == 0:
            self.stdout.write(self.style.ERROR(
                "NO LIBRARY METRICS! Run: python manage.py seed"
            ))
        elif total_ptm == 0:
            self.stdout.write(self.style.ERROR(
                "NO METRICS LINKED TO TARGETS! The seed_demo_data may have run before the metric library was seeded."
            ))
        elif pnt_count == 0:
            self.stdout.write(self.style.WARNING(
                "No progress notes are linked to targets. Full notes need to record data against plan targets."
            ))
        elif mv_count == 0:
            self.stdout.write(self.style.WARNING(
                "No metric values recorded. Enter metric values when creating full notes."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Data looks good! {mv_count} metric values exist. Charts should display."
            ))
