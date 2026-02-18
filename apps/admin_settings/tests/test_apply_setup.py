"""Tests for the apply_setup management command.

Verifies that the command correctly creates instance settings, terminology
overrides, feature toggles, programs, plan templates, custom field groups,
and metric enable/disable flags from a JSON configuration file.

Run with:
    python manage.py test apps.admin_settings.tests.test_apply_setup --settings=konote.settings.test
"""
import json
import os
import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from io import StringIO


class ApplySetupTests(TestCase):
    """Tests for the apply_setup management command."""

    databases = {"default"}

    def _write_config(self, config_dict):
        """Write a config dict to a temp JSON file and return the path."""
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(config_dict, f)
        f.close()
        self._temp_files.append(f.name)
        return f.name

    def setUp(self):
        self._temp_files = []

    def tearDown(self):
        for path in self._temp_files:
            try:
                os.unlink(path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_missing_file_raises_error(self):
        """A non-existent file should raise CommandError."""
        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("apply_setup", "/nonexistent/path/config.json", stdout=out)
        self.assertIn("not found", str(ctx.exception))

    def test_invalid_json_raises_error(self):
        """Malformed JSON should raise CommandError."""
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        f.write("{this is not valid json")
        f.close()
        self._temp_files.append(f.name)

        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("apply_setup", f.name, stdout=out)
        self.assertIn("Invalid JSON", str(ctx.exception))

    def test_non_object_json_raises_error(self):
        """A JSON array instead of object should raise CommandError."""
        path = self._write_config([1, 2, 3])

        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("apply_setup", path, stdout=out)
        self.assertIn("JSON object", str(ctx.exception))

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    def test_dry_run_creates_nothing(self):
        """With --dry-run, no database records should be created."""
        from apps.admin_settings.models import FeatureToggle, InstanceSetting, TerminologyOverride
        from apps.clients.models import CustomFieldDefinition, CustomFieldGroup
        from apps.plans.models import PlanTemplate
        from apps.programs.models import Program

        config = {
            "instance_settings": {"product_name": "Test Agency"},
            "terminology": {"client": "Participant"},
            "features": {"programs": True},
            "programs": [{"name": "Test Program", "colour_hex": "#FF0000"}],
            "plan_templates": [
                {
                    "name": "Test Template",
                    "sections": [
                        {
                            "name": "Test Section",
                            "targets": [{"name": "Test Target", "description": "A test target."}],
                        }
                    ],
                }
            ],
            "custom_field_groups": [
                {
                    "title": "Test Group",
                    "fields": [{"name": "Test Field", "input_type": "text"}],
                }
            ],
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, "--dry-run", stdout=out)

        output = out.getvalue()
        self.assertIn("DRY RUN", output)
        self.assertIn("no changes were made", output.lower())

        # Verify nothing was actually created
        self.assertEqual(InstanceSetting.objects.filter(setting_key="product_name").count(), 0)
        self.assertEqual(TerminologyOverride.objects.filter(term_key="client").count(), 0)
        self.assertEqual(FeatureToggle.objects.filter(feature_key="programs").count(), 0)
        self.assertEqual(Program.objects.filter(name="Test Program").count(), 0)
        self.assertEqual(PlanTemplate.objects.filter(name="Test Template").count(), 0)
        self.assertEqual(CustomFieldGroup.objects.filter(title="Test Group").count(), 0)
        self.assertEqual(CustomFieldDefinition.objects.filter(name="Test Field").count(), 0)

    # ------------------------------------------------------------------
    # Instance settings
    # ------------------------------------------------------------------

    def test_creates_instance_settings(self):
        """Instance settings from config should be created in the database."""
        from apps.admin_settings.models import InstanceSetting

        config = {
            "instance_settings": {
                "product_name": "Youth Services - KoNote",
                "support_email": "tech@youth.ca",
            }
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        self.assertEqual(
            InstanceSetting.objects.get(setting_key="product_name").setting_value,
            "Youth Services - KoNote",
        )
        self.assertEqual(
            InstanceSetting.objects.get(setting_key="support_email").setting_value,
            "tech@youth.ca",
        )
        self.assertIn("2 configured", out.getvalue())

    # ------------------------------------------------------------------
    # Terminology overrides
    # ------------------------------------------------------------------

    def test_creates_terminology_overrides(self):
        """Terminology overrides should be created from config."""
        from apps.admin_settings.models import TerminologyOverride

        config = {
            "terminology": {
                "client": "Youth",
                "plan": "Service Plan",
                "target": "Goal",
            }
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        self.assertEqual(
            TerminologyOverride.objects.get(term_key="client").display_value,
            "Youth",
        )
        self.assertEqual(
            TerminologyOverride.objects.get(term_key="plan").display_value,
            "Service Plan",
        )
        self.assertEqual(
            TerminologyOverride.objects.get(term_key="target").display_value,
            "Goal",
        )
        self.assertIn("3 term(s) set", out.getvalue())

    def test_creates_terminology_with_french(self):
        """Terminology overrides with dict values should store both en and fr."""
        from apps.admin_settings.models import TerminologyOverride

        config = {
            "terminology": {
                "client": {"en": "Youth", "fr": "Jeune"},
            }
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        override = TerminologyOverride.objects.get(term_key="client")
        self.assertEqual(override.display_value, "Youth")
        self.assertEqual(override.display_value_fr, "Jeune")

    # ------------------------------------------------------------------
    # Feature toggles
    # ------------------------------------------------------------------

    def test_creates_feature_toggles(self):
        """Feature toggles should be created from config."""
        from apps.admin_settings.models import FeatureToggle

        config = {
            "features": {
                "programs": True,
                "events": True,
                "shift_summaries": False,
            }
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        self.assertTrue(FeatureToggle.objects.get(feature_key="programs").is_enabled)
        self.assertTrue(FeatureToggle.objects.get(feature_key="events").is_enabled)
        self.assertFalse(FeatureToggle.objects.get(feature_key="shift_summaries").is_enabled)
        self.assertIn("3 toggle(s) set", out.getvalue())

    # ------------------------------------------------------------------
    # Programs
    # ------------------------------------------------------------------

    def test_creates_programs(self):
        """Programs should be created from config."""
        from apps.programs.models import Program

        config = {
            "programs": [
                {
                    "name": "Youth Mental Health",
                    "description": "Counselling for youth.",
                    "colour_hex": "#8B5CF6",
                    "service_model": "both",
                },
                {
                    "name": "Employment Readiness",
                    "description": "Job coaching for youth.",
                    "colour_hex": "#10B981",
                    "service_model": "individual",
                },
            ]
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        prog1 = Program.objects.get(name="Youth Mental Health")
        self.assertEqual(prog1.colour_hex, "#8B5CF6")
        self.assertEqual(prog1.service_model, "both")

        prog2 = Program.objects.get(name="Employment Readiness")
        self.assertEqual(prog2.service_model, "individual")

        self.assertIn("2 created", out.getvalue())

    # ------------------------------------------------------------------
    # Plan templates with sections and targets
    # ------------------------------------------------------------------

    def test_creates_plan_templates_with_sections_and_targets(self):
        """Plan templates, their sections, and targets should all be created."""
        from apps.plans.models import PlanTemplate, PlanTemplateSection, PlanTemplateTarget

        config = {
            "plan_templates": [
                {
                    "name": "Standard Support Plan",
                    "description": "Default template for new participants.",
                    "sections": [
                        {
                            "name": "Emotional Wellbeing",
                            "targets": [
                                {
                                    "name": "Develop coping strategies",
                                    "description": "Practise 3 healthy coping strategies.",
                                },
                                {
                                    "name": "Improve self-regulation",
                                    "description": "Better manage emotional responses.",
                                },
                            ],
                        },
                        {
                            "name": "Social Connections",
                            "targets": [
                                {
                                    "name": "Build peer relationships",
                                    "description": "Maintain 2+ positive friendships.",
                                },
                            ],
                        },
                    ],
                }
            ]
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        template = PlanTemplate.objects.get(name="Standard Support Plan")
        self.assertEqual(template.description, "Default template for new participants.")

        sections = PlanTemplateSection.objects.filter(plan_template=template).order_by("sort_order")
        self.assertEqual(sections.count(), 2)
        self.assertEqual(sections[0].name, "Emotional Wellbeing")
        self.assertEqual(sections[1].name, "Social Connections")

        targets_s1 = PlanTemplateTarget.objects.filter(template_section=sections[0]).order_by("sort_order")
        self.assertEqual(targets_s1.count(), 2)
        self.assertEqual(targets_s1[0].name, "Develop coping strategies")
        self.assertEqual(targets_s1[1].name, "Improve self-regulation")

        targets_s2 = PlanTemplateTarget.objects.filter(template_section=sections[1])
        self.assertEqual(targets_s2.count(), 1)
        self.assertEqual(targets_s2[0].name, "Build peer relationships")

        output = out.getvalue()
        self.assertIn("1 template(s)", output)
        self.assertIn("2 section(s)", output)
        self.assertIn("3 target(s)", output)

    # ------------------------------------------------------------------
    # Custom field groups and fields
    # ------------------------------------------------------------------

    def test_creates_custom_field_groups_and_fields(self):
        """Custom field groups and their field definitions should be created."""
        from apps.clients.models import CustomFieldDefinition, CustomFieldGroup

        config = {
            "custom_field_groups": [
                {
                    "title": "Demographics",
                    "fields": [
                        {
                            "name": "Gender Identity",
                            "input_type": "select",
                            "options": ["Woman", "Man", "Non-binary", "Prefer not to say"],
                            "is_required": False,
                            "is_sensitive": True,
                        },
                        {
                            "name": "Primary Language",
                            "input_type": "select",
                            "options": ["English", "French", "Other"],
                            "is_required": False,
                            "is_sensitive": False,
                        },
                    ],
                },
                {
                    "title": "Referral",
                    "fields": [
                        {
                            "name": "Referral Date",
                            "input_type": "date",
                            "is_required": False,
                            "is_sensitive": False,
                        },
                    ],
                },
            ]
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        # Groups
        self.assertEqual(CustomFieldGroup.objects.count(), 2)
        demo_group = CustomFieldGroup.objects.get(title="Demographics")
        self.assertEqual(demo_group.sort_order, 0)

        referral_group = CustomFieldGroup.objects.get(title="Referral")
        self.assertEqual(referral_group.sort_order, 1)

        # Fields
        gender_field = CustomFieldDefinition.objects.get(name="Gender Identity")
        self.assertEqual(gender_field.input_type, "select")
        self.assertTrue(gender_field.is_sensitive)
        self.assertEqual(
            gender_field.options_json,
            ["Woman", "Man", "Non-binary", "Prefer not to say"],
        )

        lang_field = CustomFieldDefinition.objects.get(name="Primary Language")
        self.assertFalse(lang_field.is_sensitive)

        date_field = CustomFieldDefinition.objects.get(name="Referral Date")
        self.assertEqual(date_field.input_type, "date")

        output = out.getvalue()
        self.assertIn("2 group(s)", output)
        self.assertIn("3 field(s)", output)

    # ------------------------------------------------------------------
    # Metrics enable/disable
    # ------------------------------------------------------------------

    def test_enables_metrics(self):
        """Metrics listed in metrics_enabled should be set to is_enabled=True."""
        from apps.plans.models import MetricDefinition

        # Create metrics that start disabled
        MetricDefinition.objects.create(
            name="PHQ-9 (Depression)",
            definition="Test metric",
            category="mental_health",
            is_enabled=False,
        )
        MetricDefinition.objects.create(
            name="GAD-7 (Anxiety)",
            definition="Test metric",
            category="mental_health",
            is_enabled=False,
        )

        config = {"metrics_enabled": ["PHQ-9 (Depression)", "GAD-7 (Anxiety)"]}
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        self.assertTrue(MetricDefinition.objects.get(name="PHQ-9 (Depression)").is_enabled)
        self.assertTrue(MetricDefinition.objects.get(name="GAD-7 (Anxiety)").is_enabled)
        self.assertIn("2 metrics enabled", out.getvalue())

    def test_disables_metrics(self):
        """Metrics listed in metrics_disabled should be set to is_enabled=False."""
        from apps.plans.models import MetricDefinition

        # Create metrics that start enabled
        MetricDefinition.objects.create(
            name="Days Clean",
            definition="Test metric",
            category="substance_use",
            is_enabled=True,
        )
        MetricDefinition.objects.create(
            name="Cravings Intensity",
            definition="Test metric",
            category="substance_use",
            is_enabled=True,
        )

        config = {"metrics_disabled": ["Days Clean", "Cravings Intensity"]}
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        self.assertFalse(MetricDefinition.objects.get(name="Days Clean").is_enabled)
        self.assertFalse(MetricDefinition.objects.get(name="Cravings Intensity").is_enabled)
        self.assertIn("2 metrics disabled", out.getvalue())

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_idempotent_running_twice_does_not_duplicate(self):
        """Running the command twice with the same config should not create duplicates."""
        from apps.admin_settings.models import FeatureToggle, InstanceSetting, TerminologyOverride
        from apps.clients.models import CustomFieldDefinition, CustomFieldGroup
        from apps.plans.models import PlanTemplate, PlanTemplateSection, PlanTemplateTarget
        from apps.programs.models import Program

        config = {
            "instance_settings": {"product_name": "Test Agency"},
            "terminology": {"client": "Participant"},
            "features": {"programs": True},
            "programs": [{"name": "Test Program", "colour_hex": "#FF0000"}],
            "plan_templates": [
                {
                    "name": "Test Template",
                    "sections": [
                        {
                            "name": "Section A",
                            "targets": [
                                {"name": "Target 1", "description": "First target."},
                            ],
                        }
                    ],
                }
            ],
            "custom_field_groups": [
                {
                    "title": "Test Group",
                    "fields": [{"name": "Test Field", "input_type": "text"}],
                }
            ],
        }
        path = self._write_config(config)

        # Run twice
        out1 = StringIO()
        call_command("apply_setup", path, stdout=out1)

        out2 = StringIO()
        call_command("apply_setup", path, stdout=out2)

        # Verify no duplicates
        self.assertEqual(InstanceSetting.objects.filter(setting_key="product_name").count(), 1)
        self.assertEqual(TerminologyOverride.objects.filter(term_key="client").count(), 1)
        self.assertEqual(FeatureToggle.objects.filter(feature_key="programs").count(), 1)
        self.assertEqual(Program.objects.filter(name="Test Program").count(), 1)
        self.assertEqual(PlanTemplate.objects.filter(name="Test Template").count(), 1)
        self.assertEqual(PlanTemplateSection.objects.filter(name="Section A").count(), 1)
        self.assertEqual(PlanTemplateTarget.objects.filter(name="Target 1").count(), 1)
        self.assertEqual(CustomFieldGroup.objects.filter(title="Test Group").count(), 1)
        self.assertEqual(CustomFieldDefinition.objects.filter(name="Test Field").count(), 1)

        # Second run should report 0 created
        output2 = out2.getvalue()
        self.assertIn("0 created", output2)

    # ------------------------------------------------------------------
    # Empty config
    # ------------------------------------------------------------------

    def test_empty_config_succeeds(self):
        """An empty config (no sections) should succeed without errors."""
        config = {}
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        self.assertIn("applied successfully", out.getvalue())

    # ------------------------------------------------------------------
    # Partial config
    # ------------------------------------------------------------------

    def test_partial_config_only_creates_specified_sections(self):
        """A config with only some sections should only create those items."""
        from apps.admin_settings.models import FeatureToggle, InstanceSetting
        from apps.programs.models import Program

        config = {
            "instance_settings": {"product_name": "Partial Test"},
            "features": {"events": True},
        }
        path = self._write_config(config)

        out = StringIO()
        call_command("apply_setup", path, stdout=out)

        # These should exist
        self.assertEqual(
            InstanceSetting.objects.get(setting_key="product_name").setting_value,
            "Partial Test",
        )
        self.assertTrue(FeatureToggle.objects.get(feature_key="events").is_enabled)

        # Programs should not have been touched
        self.assertEqual(Program.objects.count(), 0)
