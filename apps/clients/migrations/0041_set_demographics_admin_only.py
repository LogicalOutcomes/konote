"""Set admin_only=True for the Demographics group.

Demographic data (ethnicity, gender identity, sexual orientation, etc.)
is collected for funder reporting and equity analysis. It should not be
visible to frontline workers during routine service delivery.

Rationale (DEMO-VIS1):
- Prevents implicit bias activation during note-taking
- Protects small-sample de-identification in aggregate reports
- Follows PHIPA minimum necessary use principle
- Cultural safety comes from the relationship, not the database field

See tasks/design-rationale/access-tiers.md for the full expert panel analysis.
"""
from django.db import migrations


def set_demographics_admin_only(apps, schema_editor):
    CustomFieldGroup = apps.get_model("clients", "CustomFieldGroup")
    CustomFieldGroup.objects.filter(title="Demographics").update(admin_only=True)


def unset_demographics_admin_only(apps, schema_editor):
    CustomFieldGroup = apps.get_model("clients", "CustomFieldGroup")
    CustomFieldGroup.objects.filter(title="Demographics").update(admin_only=False)


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0040_customfieldgroup_admin_only"),
    ]

    operations = [
        migrations.RunPython(set_demographics_admin_only, unset_demographics_admin_only),
    ]
