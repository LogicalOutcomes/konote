"""Cleanup migration: make partner non-nullable, remove programs M2M from ReportTemplate.

The data migration (0009) already ensured every existing ReportTemplate has a
Partner assigned, so the AlterField to non-nullable is safe.

Programs are now managed on the Partner entity, not the ReportTemplate.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0009_migrate_templates_to_partners"),
    ]

    operations = [
        # Make partner FK non-nullable (all rows already have a value from 0009)
        migrations.AlterField(
            model_name="reporttemplate",
            name="partner",
            field=models.ForeignKey(
                help_text="The partner this report template belongs to.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="report_templates",
                to="reports.partner",
            ),
        ),
        # Remove the programs M2M (now lives on Partner)
        migrations.RemoveField(
            model_name="reporttemplate",
            name="programs",
        ),
    ]
