"""Export Full Tier CIDS JSON-LD for one or more programs."""

import json
from datetime import date

from django.core.management.base import BaseCommand

from apps.reports.cids_full_tier import build_full_tier_jsonld


class Command(BaseCommand):
    help = "Export Full Tier CIDS JSON-LD for the agency."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", "-o",
            help="Output file path. Default: stdout.",
        )
        parser.add_argument(
            "--program-id",
            type=int,
            help="Export only this program (default: all active programs).",
        )
        parser.add_argument(
            "--indent",
            type=int,
            default=2,
            help="JSON indentation (default: 2).",
        )
        parser.add_argument(
            "--taxonomy-lens",
            choices=["common_approach", "iris_plus", "sdg"],
            default="common_approach",
            help="Which approved taxonomy family to include.",
        )
        parser.add_argument(
            "--date-from",
            type=date.fromisoformat,
            help="Start date (YYYY-MM-DD) for measurement period.",
        )
        parser.add_argument(
            "--date-to",
            type=date.fromisoformat,
            help="End date (YYYY-MM-DD) for measurement period.",
        )
        parser.add_argument(
            "--layer3",
            action="store_true",
            help="Include Layer 3 de-identified trajectories (placeholder).",
        )

    def handle(self, *args, **options):
        from apps.programs.models import Program

        program_filter = {}
        if options["program_id"]:
            program_filter["pk"] = options["program_id"]

        programs = Program.objects.filter(status="active", **program_filter)
        document = build_full_tier_jsonld(
            programs,
            taxonomy_lens=options["taxonomy_lens"],
            date_from=options.get("date_from"),
            date_to=options.get("date_to"),
            include_layer3=options["layer3"],
        )

        output = json.dumps(document, indent=options["indent"], ensure_ascii=False)

        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as f:
                f.write(output)
            self.stdout.write(
                self.style.SUCCESS(f"Exported Full Tier CIDS JSON-LD to {options['output']}")
            )
        else:
            self.stdout.write(output)
