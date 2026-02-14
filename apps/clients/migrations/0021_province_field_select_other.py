from django.db import migrations


PROVINCE_OPTIONS = [
    "Alberta",
    "British Columbia",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Northwest Territories",
    "Nova Scotia",
    "Nunavut",
    "Ontario",
    "Prince Edward Island",
    "Quebec",
    "Saskatchewan",
    "Yukon",
]


def forwards(apps, schema_editor):
    CustomFieldDefinition = apps.get_model("clients", "CustomFieldDefinition")
    CustomFieldDefinition.objects.filter(name="Province or Territory").update(
        input_type="select_other",
        options_json=PROVINCE_OPTIONS,
    )


def backwards(apps, schema_editor):
    CustomFieldDefinition = apps.get_model("clients", "CustomFieldDefinition")
    CustomFieldDefinition.objects.filter(name="Province or Territory").update(
        input_type="select",
        options_json=PROVINCE_OPTIONS,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0020_clientfile__email_encrypted_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
