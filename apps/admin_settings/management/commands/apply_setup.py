"""Apply a setup configuration JSON file to configure a new KoNote instance.

Reads a JSON config file and creates instance settings, terminology overrides,
feature toggles, programs, plan templates, custom field groups, and metric
enable/disable flags. Uses get_or_create throughout for idempotency.

Usage:
    python manage.py apply_setup setup_config.json
    python manage.py apply_setup setup_config.json --dry-run
"""
import json

from django.core.management.base import BaseCommand, CommandError


# Sections applied in order — each key maps to its handler method name.
SECTION_ORDER = [
    "instance_settings",
    "terminology",
    "features",
    "programs",
    "plan_templates",
    "custom_field_groups",
    "metrics_enabled",
    "metrics_disabled",
]


class Command(BaseCommand):
    help = "Apply a setup configuration JSON file to a new KoNote instance."

    def add_arguments(self, parser):
        parser.add_argument(
            "config_file",
            help="Path to the JSON configuration file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without making changes.",
        )

    def handle(self, *args, **options):
        config_path = options["config_file"]
        self.dry_run = options["dry_run"]

        # Load and validate JSON
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in {config_path}: {e}")

        if not isinstance(config, dict):
            raise CommandError("Configuration file must contain a JSON object.")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made.\n"))

        # Apply each section in order
        for section in SECTION_ORDER:
            if section in config:
                handler = getattr(self, f"_apply_{section}")
                handler(config[section])

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\nDry run complete. No changes were made."))
        else:
            self.stdout.write(self.style.SUCCESS("\nSetup configuration applied successfully."))

    # ------------------------------------------------------------------
    # Instance settings
    # ------------------------------------------------------------------

    def _apply_instance_settings(self, settings_dict):
        from apps.admin_settings.models import InstanceSetting

        self.stdout.write("Instance settings:")
        created = 0
        for key, value in settings_dict.items():
            if self.dry_run:
                self.stdout.write(f"  Would set {key} = {value}")
            else:
                _, was_created = InstanceSetting.objects.get_or_create(
                    setting_key=key,
                    defaults={"setting_value": str(value)},
                )
                if was_created:
                    created += 1
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {created} created, {len(settings_dict) - created} already existed."
                )
            )

    # ------------------------------------------------------------------
    # Terminology overrides
    # ------------------------------------------------------------------

    def _apply_terminology(self, terms_dict):
        from apps.admin_settings.models import TerminologyOverride

        self.stdout.write("Terminology overrides:")
        created = 0
        for term_key, display_value in terms_dict.items():
            # Support both simple string and dict with en/fr
            if isinstance(display_value, dict):
                en_value = display_value.get("en", "")
                fr_value = display_value.get("fr", "")
            else:
                en_value = str(display_value)
                fr_value = ""

            if self.dry_run:
                msg = f"  Would set {term_key} = {en_value}"
                if fr_value:
                    msg += f" (fr: {fr_value})"
                self.stdout.write(msg)
            else:
                _, was_created = TerminologyOverride.objects.get_or_create(
                    term_key=term_key,
                    defaults={
                        "display_value": en_value,
                        "display_value_fr": fr_value,
                    },
                )
                if was_created:
                    created += 1
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {created} created, {len(terms_dict) - created} already existed."
                )
            )

    # ------------------------------------------------------------------
    # Feature toggles
    # ------------------------------------------------------------------

    def _apply_features(self, features_dict):
        from apps.admin_settings.models import FeatureToggle

        self.stdout.write("Feature toggles:")
        created = 0
        for feature_key, is_enabled in features_dict.items():
            if self.dry_run:
                state = "ON" if is_enabled else "OFF"
                self.stdout.write(f"  Would set {feature_key} = {state}")
            else:
                _, was_created = FeatureToggle.objects.get_or_create(
                    feature_key=feature_key,
                    defaults={"is_enabled": bool(is_enabled)},
                )
                if was_created:
                    created += 1
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {created} created, {len(features_dict) - created} already existed."
                )
            )

    # ------------------------------------------------------------------
    # Programs
    # ------------------------------------------------------------------

    def _apply_programs(self, programs_list):
        from apps.programs.models import Program

        self.stdout.write("Programs:")
        created = 0
        for prog_data in programs_list:
            name = prog_data.get("name", "")
            if not name:
                self.stdout.write(self.style.WARNING("  Skipping program with no name."))
                continue

            defaults = {}
            if "description" in prog_data:
                defaults["description"] = prog_data["description"]
            if "colour_hex" in prog_data:
                defaults["colour_hex"] = prog_data["colour_hex"]
            if "service_model" in prog_data:
                defaults["service_model"] = prog_data["service_model"]
            if "status" in prog_data:
                defaults["status"] = prog_data["status"]
            if "name_fr" in prog_data:
                defaults["name_fr"] = prog_data["name_fr"]

            if self.dry_run:
                colour = defaults.get("colour_hex", "#3B82F6")
                self.stdout.write(f"  Would create program: {name} ({colour})")
            else:
                _, was_created = Program.objects.get_or_create(
                    name=name,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {created} created, {len(programs_list) - created} already existed."
                )
            )

    # ------------------------------------------------------------------
    # Plan templates (with sections and targets)
    # ------------------------------------------------------------------

    def _apply_plan_templates(self, templates_list):
        from apps.plans.models import PlanTemplate, PlanTemplateSection, PlanTemplateTarget

        self.stdout.write("Plan templates:")
        templates_created = 0
        sections_created = 0
        targets_created = 0

        for tmpl_data in templates_list:
            name = tmpl_data.get("name", "")
            if not name:
                self.stdout.write(self.style.WARNING("  Skipping template with no name."))
                continue

            tmpl_defaults = {}
            if "description" in tmpl_data:
                tmpl_defaults["description"] = tmpl_data["description"]
            if "name_fr" in tmpl_data:
                tmpl_defaults["name_fr"] = tmpl_data["name_fr"]
            if "description_fr" in tmpl_data:
                tmpl_defaults["description_fr"] = tmpl_data["description_fr"]
            if "status" in tmpl_data:
                tmpl_defaults["status"] = tmpl_data["status"]

            if self.dry_run:
                self.stdout.write(f"  Would create template: {name}")
                for i, section_data in enumerate(tmpl_data.get("sections", [])):
                    section_name = section_data.get("name", "")
                    self.stdout.write(f"    Section: {section_name}")
                    for target_data in section_data.get("targets", []):
                        target_name = target_data.get("name", "")
                        self.stdout.write(f"      Target: {target_name}")
            else:
                template, was_created = PlanTemplate.objects.get_or_create(
                    name=name,
                    defaults=tmpl_defaults,
                )
                if was_created:
                    templates_created += 1

                for i, section_data in enumerate(tmpl_data.get("sections", [])):
                    section_name = section_data.get("name", "")
                    if not section_name:
                        continue

                    section_defaults = {"sort_order": i}
                    if "name_fr" in section_data:
                        section_defaults["name_fr"] = section_data["name_fr"]

                    section, sec_created = PlanTemplateSection.objects.get_or_create(
                        plan_template=template,
                        name=section_name,
                        defaults=section_defaults,
                    )
                    if sec_created:
                        sections_created += 1

                    for j, target_data in enumerate(section_data.get("targets", [])):
                        target_name = target_data.get("name", "")
                        if not target_name:
                            continue

                        target_defaults = {"sort_order": j}
                        if "description" in target_data:
                            target_defaults["description"] = target_data["description"]
                        if "name_fr" in target_data:
                            target_defaults["name_fr"] = target_data["name_fr"]
                        if "description_fr" in target_data:
                            target_defaults["description_fr"] = target_data["description_fr"]

                        _, tgt_created = PlanTemplateTarget.objects.get_or_create(
                            template_section=section,
                            name=target_name,
                            defaults=target_defaults,
                        )
                        if tgt_created:
                            targets_created += 1

        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {templates_created} templates, {sections_created} sections, "
                    f"{targets_created} targets created."
                )
            )

    # ------------------------------------------------------------------
    # Custom field groups (with field definitions)
    # ------------------------------------------------------------------

    def _apply_custom_field_groups(self, groups_list):
        from apps.clients.models import CustomFieldDefinition, CustomFieldGroup

        self.stdout.write("Custom field groups:")
        groups_created = 0
        fields_created = 0

        for i, group_data in enumerate(groups_list):
            title = group_data.get("title", "")
            if not title:
                self.stdout.write(self.style.WARNING("  Skipping group with no title."))
                continue

            if self.dry_run:
                self.stdout.write(f"  Would create group: {title}")
                for field_data in group_data.get("fields", []):
                    field_name = field_data.get("name", "")
                    input_type = field_data.get("input_type", "text")
                    self.stdout.write(f"    Field: {field_name} ({input_type})")
            else:
                group, grp_created = CustomFieldGroup.objects.get_or_create(
                    title=title,
                    defaults={"sort_order": i, "status": "active"},
                )
                if grp_created:
                    groups_created += 1

                for j, field_data in enumerate(group_data.get("fields", [])):
                    field_name = field_data.get("name", "")
                    if not field_name:
                        continue

                    field_defaults = {
                        "input_type": field_data.get("input_type", "text"),
                        "is_required": field_data.get("is_required", False),
                        "is_sensitive": field_data.get("is_sensitive", False),
                        "sort_order": j,
                        "status": "active",
                    }
                    if "options" in field_data:
                        field_defaults["options_json"] = field_data["options"]

                    _, fld_created = CustomFieldDefinition.objects.get_or_create(
                        group=group,
                        name=field_name,
                        defaults=field_defaults,
                    )
                    if fld_created:
                        fields_created += 1

        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {groups_created} groups, {fields_created} fields created."
                )
            )

    # ------------------------------------------------------------------
    # Metrics — enable specific metrics
    # ------------------------------------------------------------------

    def _apply_metrics_enabled(self, metric_names):
        from apps.plans.models import MetricDefinition

        self.stdout.write("Metrics to enable:")
        updated = 0
        not_found = []
        for name in metric_names:
            if self.dry_run:
                self.stdout.write(f"  Would enable: {name}")
            else:
                count = MetricDefinition.objects.filter(name=name).update(is_enabled=True)
                if count:
                    updated += count
                else:
                    not_found.append(name)
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"  {updated} metrics enabled.")
            )
            if not_found:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Not found in metric library: {', '.join(not_found)}"
                    )
                )

    # ------------------------------------------------------------------
    # Metrics — disable specific metrics
    # ------------------------------------------------------------------

    def _apply_metrics_disabled(self, metric_names):
        from apps.plans.models import MetricDefinition

        self.stdout.write("Metrics to disable:")
        updated = 0
        not_found = []
        for name in metric_names:
            if self.dry_run:
                self.stdout.write(f"  Would disable: {name}")
            else:
                count = MetricDefinition.objects.filter(name=name).update(is_enabled=False)
                if count:
                    updated += count
                else:
                    not_found.append(name)
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"  {updated} metrics disabled.")
            )
            if not_found:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Not found in metric library: {', '.join(not_found)}"
                    )
                )
