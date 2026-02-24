"""Data migration: set default thresholds for universal scale metrics.

Goal Progress (1-5): threshold_low=2, threshold_high=4
Self-Efficacy (1-5): threshold_low=2, threshold_high=4
Satisfaction (1-3):  threshold_low=1, threshold_high=3

Category-specific metrics are left null — they use the scale-thirds
fallback until GK sets clinical values.
"""
from django.db import migrations


def set_universal_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    # Universal 1-5 scales
    MetricDefinition.objects.filter(
        is_universal=True,
        min_value=1,
        max_value=5,
    ).update(threshold_low=2, threshold_high=4)
    # Satisfaction 1-3 scale
    MetricDefinition.objects.filter(
        is_universal=True,
        min_value=1,
        max_value=3,
    ).update(threshold_low=1, threshold_high=3)


def reverse_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    MetricDefinition.objects.filter(is_universal=True).update(
        threshold_low=None, threshold_high=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0013_add_metric_type_thresholds_achievements"),
    ]

    operations = [
        migrations.RunPython(set_universal_thresholds, reverse_thresholds),
    ]
