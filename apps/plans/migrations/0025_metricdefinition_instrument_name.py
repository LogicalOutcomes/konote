# Generated migration for instrument_name field on MetricDefinition

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0024_alter_metricdefinition_category_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="metricdefinition",
            name="instrument_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Group name for multi-item instruments (e.g. 'PHQ-9'). "
                    "Metrics sharing an instrument_name are reported together."
                ),
                max_length=100,
            ),
        ),
    ]
