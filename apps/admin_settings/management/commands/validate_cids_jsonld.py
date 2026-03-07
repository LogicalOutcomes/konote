"""Validate a CIDS JSON-LD export against the official Common Approach SHACL file."""

from __future__ import annotations

import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.programs.models import Program
from apps.reports.cids_jsonld import build_cids_jsonld_document


DEFAULT_SHAPES_URL = "https://ontology.commonapproach.org/validation/shacl/cids.basictier.shacl.ttl"


class Command(BaseCommand):
    help = "Validate CIDS JSON-LD against the Common Approach Basic Tier SHACL shapes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            help="Optional path to an existing JSON-LD file. If omitted, KoNote exports one in memory first.",
        )
        parser.add_argument(
            "--program-id",
            type=int,
            help="Validate only this program when exporting in memory.",
        )
        parser.add_argument(
            "--taxonomy-lens",
            choices=["common_approach", "iris_plus", "sdg"],
            default="common_approach",
            help="Which approved taxonomy family to include as linked CIDS codes.",
        )
        parser.add_argument(
            "--date-from",
            type=date.fromisoformat,
            help="Optional start date (YYYY-MM-DD) when exporting in memory.",
        )
        parser.add_argument(
            "--date-to",
            type=date.fromisoformat,
            help="Optional end date (YYYY-MM-DD) when exporting in memory.",
        )
        parser.add_argument(
            "--shapes-url",
            default=DEFAULT_SHAPES_URL,
            help="SHACL URL or local path to validate against.",
        )

    def handle(self, *args, **options):
        try:
            from pyshacl import validate
            from rdflib import Graph
        except ImportError as exc:
            raise CommandError(
                "pyshacl is required for validation. Install test dependencies first."
            ) from exc

        if options["input"]:
            data_graph = Graph().parse(options["input"], format="json-ld")
        else:
            program_filter = {}
            if options["program_id"]:
                program_filter["pk"] = options["program_id"]
            programs = Program.objects.filter(status="active", **program_filter)
            if not programs.exists():
                raise CommandError("No active programs matched the validation request.")
            document = build_cids_jsonld_document(
                programs=programs,
                taxonomy_lens=options["taxonomy_lens"],
                date_from=options.get("date_from"),
                date_to=options.get("date_to"),
            )
            data_graph = Graph().parse(
                data=json.dumps(document, ensure_ascii=False),
                format="json-ld",
            )

        shapes_graph = Graph().parse(options["shapes_url"], format="turtle")
        conforms, _results_graph, results_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="rdfs",
            serialize_report_graph=False,
            advanced=False,
        )

        if conforms:
            self.stdout.write(self.style.SUCCESS("CIDS Basic Tier validation passed."))
            return

        self.stdout.write(self.style.ERROR("CIDS Basic Tier validation failed."))
        self.stdout.write(results_text)
        raise CommandError("CIDS validation failed.")