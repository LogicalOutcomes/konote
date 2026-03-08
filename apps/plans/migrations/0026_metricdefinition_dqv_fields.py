"""Add data quality descriptor fields for CIDS DQV export.

Three descriptive fields on MetricDefinition that tell funders *how*
data is generated, without creating a quality hierarchy.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0025_metricdefinition_instrument_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="metricdefinition",
            name="evidence_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("self_report", "Self-report (participant completes)"),
                    ("staff_observed", "Staff-observed (recorded by worker)"),
                    ("administrative_record", "Administrative record (system data)"),
                    ("third_party_assessed", "Third-party assessed (external evaluator)"),
                    ("coded_qualitative", "Coded qualitative (open responses coded to scale)"),
                ],
                default="",
                help_text="How the data is generated. Describes the source, not quality.",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="metricdefinition",
            name="measure_basis",
            field=models.CharField(
                blank=True,
                choices=[
                    ("published_validated", "Published, validated for this population"),
                    ("published_adapted", "Published, adapted for local context"),
                    ("custom_participatory", "Custom, developed with participant input"),
                    ("custom_staff_designed", "Custom, designed by staff"),
                    ("administrative", "Administrative or system-generated"),
                ],
                default="",
                help_text="How the measure was developed. Not a quality ranking.",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="metricdefinition",
            name="derivation_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("direct_response", "Direct participant response"),
                    ("coded_from_qualitative", "Coded from qualitative responses"),
                    ("calculated_composite", "Calculated composite score"),
                    ("staff_rating", "Staff rating or judgment"),
                ],
                default="",
                help_text="How the recorded value was produced. Only needed when the value isn't a direct participant response.",
                max_length=30,
            ),
        ),
    ]
