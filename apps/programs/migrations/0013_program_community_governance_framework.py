"""LTE — Add community_governance_framework field to Program.

When set, Longitudinal Trajectory Export submissions on this program
require community reviewer signoff and, for OCAP/EGAP, a higher
population floor (n>=15). See
tasks/design-rationale/evaluation-microdata-export.md, LTE section.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0012_program_default_goal_review_days"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="community_governance_framework",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "No specific framework"),
                    ("ocap", "OCAP (First Nations, Inuit, Métis)"),
                    ("egap", "EGAP (Black communities)"),
                    ("other", "Other small-population community review"),
                ],
                default="",
                help_text=(
                    "If set, Longitudinal Trajectory Export submissions on this "
                    "program require community reviewer signoff. OCAP and EGAP "
                    "raise the LTE population floor to n>=15."
                ),
                max_length=10,
            ),
        ),
    ]
