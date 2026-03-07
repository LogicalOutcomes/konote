"""Create EvaluationFramework, EvaluationComponent, and EvaluationEvidenceLink."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("programs", "0009_program_cids_sector_code_program_description_fr_and_more"),
        ("reports", "0006_rename_funder_profile_to_report_template"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluationFramework",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], default="draft", max_length=20)),
                ("planning_quality_state", models.CharField(choices=[("ai_generated", "AI-generated"), ("checks_passed", "Checks passed"), ("human_confirmed", "Human-confirmed"), ("manual", "Manually entered")], default="manual", max_length=20)),
                ("summary", models.TextField(blank=True, default="")),
                ("output_summary", models.TextField(blank=True, default="")),
                ("outcome_chain_summary", models.TextField(blank=True, default="")),
                ("risk_summary", models.TextField(blank=True, default="")),
                ("counterfactual_summary", models.TextField(blank=True, default="")),
                ("partner_requirements_summary", models.TextField(blank=True, default="")),
                ("source_documents_json", models.JSONField(blank=True, default=list)),
                ("evaluator_attestation_at", models.DateTimeField(blank=True, null=True)),
                ("evaluator_attestation_scope", models.JSONField(blank=True, null=True)),
                ("evaluator_attestation_text", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("program", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evaluation_frameworks", to="programs.program")),
                ("report_template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="evaluation_frameworks", to="reports.reporttemplate")),
                ("evaluator_attestation_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attested_frameworks", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_frameworks", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_frameworks", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "evaluation_frameworks",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="EvaluationComponent",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("component_type", models.CharField(choices=[("participant_group", "Participant group"), ("service", "Service"), ("activity", "Activity"), ("output", "Output"), ("outcome", "Outcome"), ("risk", "Risk"), ("mitigation", "Mitigation"), ("counterfactual", "Counterfactual"), ("assumption", "Assumption"), ("input", "Input"), ("impact_dimension", "Impact dimension")], max_length=30)),
                ("cids_class", models.CharField(blank=True, default="", max_length=100)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("sequence_order", models.IntegerField(default=0)),
                ("structured_payload", models.JSONField(blank=True, default=dict)),
                ("quality_state", models.CharField(choices=[("ai_generated", "AI-generated"), ("checks_passed", "Checks passed"), ("human_confirmed", "Human-confirmed"), ("manual", "Manually entered")], default="manual", max_length=20)),
                ("provenance_source", models.CharField(choices=[("manual", "Manual"), ("ai_local", "AI (local)"), ("ai_external", "AI (external)"), ("imported", "Imported")], default="manual", max_length=20)),
                ("provenance_model", models.CharField(blank=True, default="", max_length=200)),
                ("confidence_score", models.FloatField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("framework", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="components", to="programs.evaluationframework")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="programs.evaluationcomponent")),
            ],
            options={
                "db_table": "evaluation_components",
                "ordering": ["framework", "sequence_order", "pk"],
            },
        ),
        migrations.CreateModel(
            name="EvaluationEvidenceLink",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("source_type", models.CharField(choices=[("proposal", "Proposal"), ("logic_model", "Logic model"), ("funder_requirement", "Funder requirement"), ("website", "Website"), ("manual_note", "Manual note"), ("report_template", "Report template")], max_length=30)),
                ("storage_path", models.CharField(blank=True, default="", max_length=500)),
                ("external_reference", models.URLField(blank=True, default="", max_length=500)),
                ("excerpt_text", models.TextField(blank=True, default="")),
                ("contains_pii", models.BooleanField(default=False)),
                ("used_for_ai", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("framework", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidence_links", to="programs.evaluationframework")),
            ],
            options={
                "db_table": "evaluation_evidence_links",
                "ordering": ["-created_at"],
            },
        ),
    ]
