"""
Apply a setup configuration JSON to initialise a KoNote instance.

Usage:
    python manage.py apply_setup setup_config.json
    python manage.py apply_setup setup_config.json --dry-run
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Apply a setup configuration file to initialise instance settings, terminology, features, programs, metrics, templates, and custom fields."

    def add_arguments(self, parser):
        parser.add_argument(
            "config_file",
            nargs="?",
            help="Path to the JSON configuration file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without making changes.",
        )

    def handle(self, *args, **options):
        config_file = options.get("config_file")
        if not config_file:
            raise CommandError("You must provide a path to a JSON configuration file.")

        path = Path(config_file)
        if not path.exists():
            raise CommandError(f"Configuration file not found: {config_file}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON: {e}")

        dry_run = options["dry_run"]
        summary = apply_setup_config(config, dry_run=dry_run, stdout=self.stdout)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN \u2014 no changes were made ==="))
        else:
            self.stdout.write(self.style.SUCCESS("\n=== Setup complete ==="))

        for key, value in summary.items():
            self.stdout.write(f"  {key}: {value}")



def apply_setup_config(config, dry_run=False, stdout=None):
    """Apply a setup configuration dict. Returns a summary dict.

    This function is used by both the management command and the setup wizard view.
    """
    summary = {}

    if dry_run:
        summary.update(_preview_config(config))
        return summary

    with transaction.atomic():
        summary.update(_apply_instance_settings(config.get("instance_settings", {}), stdout))
        summary.update(_apply_terminology(config.get("terminology", {}), stdout))
        summary.update(_apply_features(config.get("features", {}), stdout))
        summary.update(_apply_programs(config.get("programs", []), stdout))
        summary.update(_apply_metrics(
            config.get("metrics_enabled", []),
            config.get("metrics_disabled", []),
            stdout,
        ))
        summary.update(_apply_plan_templates(config.get("plan_templates", []), stdout))
        summary.update(_apply_custom_fields(config.get("custom_field_groups", []), stdout))

    return summary


def _preview_config(config):
    """Return a summary of what would be created without making changes."""
    summary = {}
    inst = config.get("instance_settings", {})
    summary["Instance settings"] = f"{len(inst)} setting(s) to configure"
    terms = config.get("terminology", {})
    summary["Terminology"] = f"{len(terms)} term(s) to override"
    features = config.get("features", {})
    summary["Features"] = f"{len(features)} toggle(s) to set"
    programs = config.get("programs", [])
    summary["Programs"] = f"{len(programs)} program(s) to create"
    enabled = config.get("metrics_enabled", [])
    disabled = config.get("metrics_disabled", [])
    summary["Metrics"] = f"{len(enabled)} to enable, {len(disabled)} to disable"
    templates = config.get("plan_templates", [])
    total_sections = sum(len(t.get("sections", [])) for t in templates)
    total_targets = sum(
        len(s.get("targets", []))
        for t in templates
        for s in t.get("sections", [])
    )
    summary["Plan templates"] = (
        f"{len(templates)} template(s), {total_sections} section(s), "
        f"{total_targets} target(s)"
    )
    field_groups = config.get("custom_field_groups", [])
    total_fields = sum(len(g.get("fields", [])) for g in field_groups)
    summary["Custom fields"] = f"{len(field_groups)} group(s), {total_fields} field(s)"
    return summary


def _log(stdout, msg):
    if stdout:
        stdout.write(msg)



def _apply_instance_settings(settings_data, stdout):
    from apps.admin_settings.models import InstanceSetting

    count = 0
    for key, value in settings_data.items():
        InstanceSetting.objects.update_or_create(
            setting_key=key,
            defaults={"setting_value": str(value)},
        )
        count += 1
    _log(stdout, f"  Instance settings: {count} configured.")
    return {"Instance settings": f"{count} configured"}


def _apply_terminology(terms_data, stdout):
    from apps.admin_settings.models import TerminologyOverride

    count = 0
    for key, value in terms_data.items():
        TerminologyOverride.objects.update_or_create(
            term_key=key,
            defaults={"display_value": str(value)},
        )
        count += 1
    _log(stdout, f"  Terminology: {count} term(s) set.")
    return {"Terminology": f"{count} term(s) set"}


def _apply_features(features_data, stdout):
    from apps.admin_settings.models import FeatureToggle

    count = 0
    for key, enabled in features_data.items():
        FeatureToggle.objects.update_or_create(
            feature_key=key,
            defaults={"is_enabled": bool(enabled)},
        )
        count += 1
    _log(stdout, f"  Features: {count} toggle(s) set.")
    return {"Features": f"{count} toggle(s) set"}


def _apply_programs(programs_data, stdout):
    from apps.programs.models import Program

    created = 0
    for prog in programs_data:
        _, was_created = Program.objects.get_or_create(
            name=prog["name"],
            defaults={
                "description": prog.get("description", ""),
                "colour_hex": prog.get("colour_hex", "#3B82F6"),
            },
        )
        if was_created:
            created += 1
    _log(stdout, f"  Programs: {created} created.")
    return {"Programs": f"{created} created"}


def _apply_metrics(enabled_names, disabled_names, stdout):
    from apps.plans.models import MetricDefinition

    enabled_count = 0
    disabled_count = 0

    for name in enabled_names:
        updated = MetricDefinition.objects.filter(name=name).update(is_enabled=True)
        enabled_count += updated

    for name in disabled_names:
        updated = MetricDefinition.objects.filter(name=name).update(is_enabled=False)
        disabled_count += updated

    _log(stdout, f"  Metrics: {enabled_count} enabled, {disabled_count} disabled.")
    return {"Metrics": f"{enabled_count} enabled, {disabled_count} disabled"}



def _apply_plan_templates(templates_data, stdout):
    from apps.plans.models import PlanTemplate, PlanTemplateSection, PlanTemplateTarget

    template_count = 0
    section_count = 0
    target_count = 0

    for tpl in templates_data:
        template = PlanTemplate.objects.create(
            name=tpl["name"],
            description=tpl.get("description", ""),
        )
        template_count += 1

        for i, sec in enumerate(tpl.get("sections", [])):
            section = PlanTemplateSection.objects.create(
                plan_template=template,
                name=sec["name"],
                sort_order=i,
            )
            section_count += 1

            for j, tgt in enumerate(sec.get("targets", [])):
                PlanTemplateTarget.objects.create(
                    template_section=section,
                    name=tgt["name"],
                    description=tgt.get("description", ""),
                    sort_order=j,
                )
                target_count += 1

    _log(stdout, f"  Plan templates: {template_count} templates, {section_count} sections, {target_count} targets.")
    return {
        "Plan templates": f"{template_count} template(s), {section_count} section(s), {target_count} target(s)"
    }


def _apply_custom_fields(groups_data, stdout):
    from apps.clients.models import CustomFieldDefinition, CustomFieldGroup

    group_count = 0
    field_count = 0

    for i, grp in enumerate(groups_data):
        group = CustomFieldGroup.objects.create(
            title=grp["title"],
            sort_order=i,
        )
        group_count += 1

        for j, fld in enumerate(grp.get("fields", [])):
            CustomFieldDefinition.objects.create(
                group=group,
                name=fld["name"],
                input_type=fld.get("input_type", "text"),
                is_required=fld.get("is_required", False),
                is_sensitive=fld.get("is_sensitive", False),
                options_json=fld.get("options", []),
                sort_order=j,
            )
            field_count += 1

    _log(stdout, f"  Custom fields: {group_count} groups, {field_count} fields.")
    return {"Custom fields": f"{group_count} group(s), {field_count} field(s)"}

