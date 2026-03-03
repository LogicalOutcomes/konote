"""Data migration: set default plausibility warning thresholds for financial coaching metrics."""
from django.db import migrations


FINANCIAL_THRESHOLDS = {
    "Total Debt": {"warn_min": 0, "warn_max": 200000},
    "Monthly Income": {"warn_min": 0, "warn_max": 15000},
    "Monthly Savings": {"warn_min": -500, "warn_max": 5000},
    "Credit Score Change": {"warn_min": -100, "warn_max": 150},
    "Debt-to-Income Ratio": {"warn_min": 0, "warn_max": 50},
    "Savings Rate (%)": {"warn_min": -20, "warn_max": 60},
    "Income Change ($)": {"warn_min": -5000, "warn_max": 10000},
}


def set_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    for name, thresholds in FINANCIAL_THRESHOLDS.items():
        MetricDefinition.objects.filter(name=name).update(
            warn_min=thresholds["warn_min"],
            warn_max=thresholds["warn_max"],
        )


def clear_thresholds(apps, schema_editor):
    MetricDefinition = apps.get_model("plans", "MetricDefinition")
    MetricDefinition.objects.filter(name__in=FINANCIAL_THRESHOLDS.keys()).update(
        warn_min=None,
        warn_max=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0017_plausibility_warnings"),
    ]
    operations = [
        migrations.RunPython(set_thresholds, clear_thresholds),
    ]
