"""Data migration: set default tier-2 plausibility thresholds for financial coaching metrics.

These are approximately 10x the tier-1 warning thresholds and represent
values that are almost certainly data-entry errors.
"""
from django.db import migrations


FINANCIAL_TIER2_THRESHOLDS = {
    "Total Debt": {"very_unlikely_min": -10000, "very_unlikely_max": 2000000},
    "Monthly Income": {"very_unlikely_min": -1000, "very_unlikely_max": 150000},
    "Monthly Savings": {"very_unlikely_min": -5000, "very_unlikely_max": 50000},
    "Credit Score Change": {"very_unlikely_min": -500, "very_unlikely_max": 500},
    "Debt-to-Income Ratio": {"very_unlikely_min": -10, "very_unlikely_max": 200},
    "Savings Rate (%)": {"very_unlikely_min": -100, "very_unlikely_max": 200},
    "Income Change ($)": {"very_unlikely_min": -50000, "very_unlikely_max": 100000},
}


def set_tier2_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    for name, thresholds in FINANCIAL_TIER2_THRESHOLDS.items():
        MetricDefinition.objects.filter(name=name).update(
            very_unlikely_min=thresholds["very_unlikely_min"],
            very_unlikely_max=thresholds["very_unlikely_max"],
        )


def clear_tier2_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    MetricDefinition.objects.filter(name__in=FINANCIAL_TIER2_THRESHOLDS.keys()).update(
        very_unlikely_min=None,
        very_unlikely_max=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0019_very_unlikely_thresholds"),
    ]
    operations = [
        migrations.RunPython(set_tier2_thresholds, clear_tier2_thresholds),
    ]
