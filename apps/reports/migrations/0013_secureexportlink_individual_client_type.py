"""Add 'individual_client' to SecureExportLink.EXPORT_TYPE_CHOICES."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0012_alter_reportsection_section_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="secureexportlink",
            name="export_type",
            field=models.CharField(
                max_length=50,
                choices=[
                    ("client_data", "Participant Data"),
                    ("metrics", "Metric Report"),
                    ("funder_report", "Funder Report"),
                    ("individual_client", "Individual Client Export"),
                ],
            ),
        ),
    ]
