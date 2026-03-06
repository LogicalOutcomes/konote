"""Set collapsed_by_default=True for the Demographics group.

Sensitive demographic fields (gender identity, racial identity, etc.)
should not be displayed by default on the participant info tab.
"""
from django.db import migrations


def set_demographics_collapsed(apps, schema_editor):
    CustomFieldGroup = apps.get_model("clients", "CustomFieldGroup")
    CustomFieldGroup.objects.filter(title="Demographics").update(collapsed_by_default=True)


def unset_demographics_collapsed(apps, schema_editor):
    CustomFieldGroup = apps.get_model("clients", "CustomFieldGroup")
    CustomFieldGroup.objects.filter(title="Demographics").update(collapsed_by_default=False)


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0038_customfieldgroup_collapsed_by_default"),
    ]

    operations = [
        migrations.RunPython(set_demographics_collapsed, unset_demographics_collapsed),
    ]
