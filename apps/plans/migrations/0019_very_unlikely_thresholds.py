"""Schema migration: add very_unlikely_min and very_unlikely_max to MetricDefinition."""
from django.db import migrations, models
import django.utils.translation


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0018_set_financial_warn_thresholds"),
    ]

    operations = [
        migrations.AddField(
            model_name="metricdefinition",
            name="very_unlikely_min",
            field=models.FloatField(
                blank=True,
                help_text=django.utils.translation.gettext_lazy(
                    "Hard floor \u2014 values below this are almost certainly data-entry errors. Requires two confirmations."
                ),
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="metricdefinition",
            name="very_unlikely_max",
            field=models.FloatField(
                blank=True,
                help_text=django.utils.translation.gettext_lazy(
                    "Hard ceiling \u2014 values above this are almost certainly data-entry errors. Requires two confirmations."
                ),
                null=True,
            ),
        ),
    ]
