"""Export CIDS-compliant JSON-LD for the agency (Phase 3).

Produces a JSON-LD file conforming to Common Impact Data Standard v3.2.0.
All data is aggregated — no individual PII is included.

Usage:
    python manage.py export_cids_jsonld
    python manage.py export_cids_jsonld --output /path/to/export.jsonld
    python manage.py export_cids_jsonld --program-id 5

The export includes:
- cids:Organization (from OrganizationProfile)
- cids:Program (one per program)
- cids:Outcome (aggregated from PlanTarget)
- cids:Indicator (from MetricDefinition)
- cids:IndicatorReport (aggregated MetricValues in i72:Measure format)
- cids:Theme (from IRIS Impact Theme code lists)
- cids:BeneficialStakeholder (cohort-level, not individual)
- cids:StakeholderOutcome (junction: stakeholder group × outcome)
- cids:Activity (aggregated session counts)
- cids:ImpactReport (scale, depth, duration dimensions)
"""

import json

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from django.utils import timezone


CIDS_CONTEXT = "https://ontology.commonapproach.org/contexts/cidsContext.jsonld"
CIDS_VERSION = "3.2.0"


class Command(BaseCommand):
    help = "Export CIDS-compliant JSON-LD for the agency."

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

    def handle(self, *args, **options):
        from apps.admin_settings.models import CidsCodeList, OrganizationProfile
        from apps.clients.models import ServiceEpisode
        from apps.notes.models import MetricValue, ProgressNote
        from apps.plans.models import MetricDefinition, PlanTarget
        from apps.programs.models import Program

        program_filter = {}
        if options["program_id"]:
            program_filter["pk"] = options["program_id"]

        programs = Program.objects.filter(status="active", **program_filter)
        org = OrganizationProfile.get_solo()

        graph = []

        # ── Organization ─────────────────────────────────────────────
        org_id = f"urn:konote:org:{org.pk}" if org.pk else "urn:konote:org:1"
        org_node = {
            "@id": org_id,
            "@type": "cids:Organization",
            "hasLegalName": org.legal_name or "",
        }
        if org.operating_name:
            org_node["hasName"] = org.operating_name
        if org.description:
            org_node["hasDescription"] = org.description
        if org.legal_status:
            org_node["cids:hasOrganizationType"] = org.legal_status
        if org.province:
            org_node["org:hasJurisdiction"] = f"{org.province}, {org.country}"
        graph.append(org_node)

        # ── Programs ─────────────────────────────────────────────────
        for program in programs:
            prog_id = f"urn:konote:program:{program.pk}"
            prog_node = {
                "@id": prog_id,
                "@type": "cids:Program",
                "hasName": program.name,
                "org:offeredBy": {"@id": org_id},
            }
            if program.description:
                prog_node["hasDescription"] = program.description
            if program.cids_sector_code:
                prog_node["cids:hasSectorCode"] = program.cids_sector_code

            # BeneficialStakeholder (cohort-level, NOT individual)
            episode_stats = ServiceEpisode.objects.filter(
                program=program, status__in=["active", "on_hold", "finished"],
            ).aggregate(
                total=Count("pk"),
                new_intake=Count("pk", filter=Q(episode_type="new_intake")),
                re_enrolment=Count("pk", filter=Q(episode_type="re_enrolment")),
                transfer_in=Count("pk", filter=Q(episode_type="transfer_in")),
            )

            stakeholders = []
            if episode_stats["total"]:
                sh_id = f"urn:konote:stakeholder:{program.pk}:participants"
                sh_node = {
                    "@id": sh_id,
                    "@type": "cids:BeneficialStakeholder",
                    "hasName": f"Participants in {program.name}",
                    "hasDescription": (
                        f"Cohort of {episode_stats['total']} participants: "
                        f"{episode_stats['new_intake']} new intake, "
                        f"{episode_stats['re_enrolment']} re-enrolment, "
                        f"{episode_stats['transfer_in']} transfer in."
                    ),
                    "cids:hasStakeholderSize": {
                        "@type": "i72:Measure",
                        "i72:hasNumericalValue": str(episode_stats["total"]),
                        "i72:hasUnit": "persons",
                    },
                }
                graph.append(sh_node)
                stakeholders.append({"@id": sh_id})

            if stakeholders:
                prog_node["cids:hasStakeholder"] = stakeholders

            graph.append(prog_node)

            # ── Outcomes (aggregated PlanTargets) ────────────────────
            targets = PlanTarget.objects.filter(
                plan_section__program=program,
            ).exclude(status="deactivated")

            outcome_ids = []
            for target in targets:
                outcome_id = f"urn:konote:outcome:{target.pk}"
                outcome_node = {
                    "@id": outcome_id,
                    "@type": "cids:Outcome",
                    "hasName": target.name,
                }
                if target.cids_outcome_uri:
                    outcome_node["cids:hasOutcomeURI"] = target.cids_outcome_uri
                if target.achievement_status:
                    outcome_node["cids:achievementStatus"] = target.achievement_status
                if target.first_achieved_at:
                    outcome_node["cids:firstAchievedAt"] = (
                        target.first_achieved_at.isoformat()
                    )
                graph.append(outcome_node)
                outcome_ids.append({"@id": outcome_id})

                # StakeholderOutcome junction
                for sh in stakeholders:
                    so_id = f"urn:konote:stakeholder-outcome:{program.pk}:{target.pk}"
                    so_node = {
                        "@id": so_id,
                        "@type": "cids:StakeholderOutcome",
                        "cids:forStakeholder": sh,
                        "cids:forOutcome": {"@id": outcome_id},
                    }
                    graph.append(so_node)

            if outcome_ids:
                # Update program node with outcomes
                prog_node["cids:hasOutcome"] = outcome_ids

            # ── Activities (aggregated note counts) ──────────────────
            note_counts = (
                ProgressNote.objects.filter(
                    author_program=program,
                    status="default",
                )
                .values("interaction_type")
                .annotate(count=Count("pk"))
            )
            for entry in note_counts:
                activity_id = (
                    f"urn:konote:activity:{program.pk}:{entry['interaction_type']}"
                )
                activity_node = {
                    "@id": activity_id,
                    "@type": "cids:Activity",
                    "hasName": entry["interaction_type"].replace("_", " ").title(),
                    "cids:hasCount": {
                        "@type": "i72:Measure",
                        "i72:hasNumericalValue": str(entry["count"]),
                        "i72:hasUnit": "sessions",
                    },
                    "cids:forProgram": {"@id": prog_id},
                }
                graph.append(activity_node)

        # ── Indicators (MetricDefinitions) ───────────────────────────
        metrics = MetricDefinition.objects.filter(
            status="active",
        )
        for metric in metrics:
            indicator_id = f"urn:konote:indicator:{metric.pk}"
            indicator_node = {
                "@id": indicator_id,
                "@type": "cids:Indicator",
                "hasName": metric.name,
                "hasDescription": metric.definition,
            }
            if metric.cids_indicator_uri:
                indicator_node["cids:hasIndicatorURI"] = metric.cids_indicator_uri
            if metric.cids_unit_description:
                indicator_node["cids:unitDescription"] = metric.cids_unit_description
            if metric.cids_defined_by:
                indicator_node["cids:definedBy"] = metric.cids_defined_by
            if metric.cids_has_baseline:
                indicator_node["cids:hasBaseline"] = metric.cids_has_baseline

            # IndicatorReport — aggregate values
            values = MetricValue.objects.filter(metric_def=metric)
            value_count = values.count()
            if value_count:
                report_id = f"urn:konote:indicator-report:{metric.pk}"
                report_node = {
                    "@id": report_id,
                    "@type": "cids:IndicatorReport",
                    "cids:forIndicator": {"@id": indicator_id},
                    "cids:hasCount": {
                        "@type": "i72:Measure",
                        "i72:hasNumericalValue": str(value_count),
                        "i72:hasUnit": "measurements",
                    },
                }
                graph.append(report_node)
                indicator_node["cids:hasIndicatorReport"] = {"@id": report_id}

            graph.append(indicator_node)

        # ── Themes (from IRIS Impact Theme code lists) ───────────────
        themes = CidsCodeList.objects.filter(list_name="IRISImpactTheme")
        for theme in themes:
            theme_id = f"urn:konote:theme:{theme.pk}"
            theme_node = {
                "@id": theme.specification_uri or theme_id,
                "@type": "cids:Theme",
                "hasName": theme.label,
            }
            if theme.label_fr:
                theme_node["hasName_fr"] = theme.label_fr
            if theme.description:
                theme_node["hasDescription"] = theme.description
            graph.append(theme_node)

        # ── Impact dimensions ────────────────────────────────────────
        for program in programs:
            prog_id = f"urn:konote:program:{program.pk}"

            # ImpactScale — how many people affected
            active_clients = ServiceEpisode.objects.filter(
                program=program,
                status__in=["active", "on_hold"],
            ).values("client_file_id").distinct().count()

            # ImpactDepth — achievement distribution
            targets_with_status = PlanTarget.objects.filter(
                plan_section__program=program,
            ).exclude(
                achievement_status="",
            ).values("achievement_status").annotate(count=Count("pk"))

            depth_desc = ", ".join(
                f"{e['count']} {e['achievement_status']}"
                for e in targets_with_status
            ) or "No achievement data"

            # ImpactDuration — average episode length
            finished_episodes = ServiceEpisode.objects.filter(
                program=program,
                status="finished",
                started_at__isnull=False,
                ended_at__isnull=False,
            )
            avg_days = None
            if finished_episodes.exists():
                from django.db.models import F, ExpressionWrapper, DurationField
                durations = finished_episodes.annotate(
                    duration=ExpressionWrapper(
                        F("ended_at") - F("started_at"),
                        output_field=DurationField(),
                    )
                )
                avg_duration = durations.aggregate(
                    avg=Avg("duration")
                )["avg"]
                if avg_duration:
                    avg_days = avg_duration.days

            impact_id = f"urn:konote:impact-report:{program.pk}"
            impact_node = {
                "@id": impact_id,
                "@type": "cids:ImpactReport",
                "cids:forProgram": {"@id": prog_id},
                "cids:hasImpactScale": {
                    "@type": "i72:Measure",
                    "i72:hasNumericalValue": str(active_clients),
                    "i72:hasUnit": "persons",
                    "hasDescription": "Distinct active participants",
                },
                "cids:hasImpactDepth": {
                    "hasDescription": depth_desc,
                },
            }
            if avg_days is not None:
                impact_node["cids:hasImpactDuration"] = {
                    "@type": "i72:Measure",
                    "i72:hasNumericalValue": str(avg_days),
                    "i72:hasUnit": "days",
                    "hasDescription": "Average episode duration",
                }
            graph.append(impact_node)

        # ── Assemble document ────────────────────────────────────────
        document = {
            "@context": CIDS_CONTEXT,
            "@graph": graph,
            "cids:version": CIDS_VERSION,
            "cids:exportedAt": timezone.now().isoformat(),
            "cids:exportedBy": "KoNote",
        }

        output = json.dumps(document, indent=options["indent"], ensure_ascii=False)

        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as f:
                f.write(output)
            self.stdout.write(
                self.style.SUCCESS(f"Exported CIDS JSON-LD to {options['output']}")
            )
        else:
            self.stdout.write(output)
