"""Add database constraint ensuring exactly one FK is set on TaxonomyMapping."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_settings", "0010_taxonomymapping_taxonomy_system_labels"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="taxonomymapping",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(metric_definition__isnull=False, program__isnull=True, plan_target__isnull=True)
                    | models.Q(metric_definition__isnull=True, program__isnull=False, plan_target__isnull=True)
                    | models.Q(metric_definition__isnull=True, program__isnull=True, plan_target__isnull=False)
                ),
                name="taxonomy_exactly_one_fk",
            ),
        ),
    ]
