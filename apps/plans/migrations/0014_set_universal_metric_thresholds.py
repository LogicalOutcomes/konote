# Data migration: set default thresholds for universal 1-5 scale metrics.
from django.db import migrations


def set_universal_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    MetricDefinition.objects.filter(is_universal=True).update(
        threshold_low=2,
        threshold_high=4,
    )


def reverse_universal_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    MetricDefinition.objects.filter(is_universal=True).update(
        threshold_low=None,
        threshold_high=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0013_add_metric_distribution_fields"),
    ]

    operations = [
        migrations.RunPython(set_universal_thresholds, reverse_universal_thresholds),
    ]
