"""
Fix custom field ordering and input types for the info page edit screen.

Changes:
1. Reorder Contact Information fields logically:
   Identity → Contact details → Communication preferences → Address
2. Ensure Emergency Contact Relationship and Preferred Communication Format
   use select_other (not select) so the "Other" option shows a text field.
3. Rename "Other family member" to "Another family member" in Emergency
   Contact Relationship to avoid confusion with the system "Other" option.
4. Remove duplicate "Other" from options_json on select_other fields —
   the template already adds "Other" automatically.
"""
from django.db import migrations


# Desired sort order for Contact Information fields:
# Identity → Contact details → Communication preferences → Address
CONTACT_SORT_ORDER = {
    "Preferred Name": 0,
    "Pronouns": 10,
    "Primary Phone": 20,
    "Secondary Phone": 30,
    "Email": 40,
    "Secondary Email": 50,
    "Preferred Contact Method": 60,
    "Best Time to Contact": 70,
    "Preferred Language of Service": 80,
    "Mailing Address": 90,
    "Postal Code": 100,
    "Province or Territory": 110,
}


def forwards(apps, schema_editor):
    CustomFieldDefinition = apps.get_model("clients", "CustomFieldDefinition")

    # 1. Fix Contact Information sort order
    for field_name, sort_val in CONTACT_SORT_ORDER.items():
        CustomFieldDefinition.objects.filter(
            group__title="Contact Information",
            name=field_name,
        ).exclude(sort_order=sort_val).update(sort_order=sort_val)

    # 2. Ensure select_other type for fields that need an "Other" text field
    CustomFieldDefinition.objects.filter(
        group__title="Emergency Contact",
        name="Emergency Contact Relationship",
        input_type="select",
    ).update(input_type="select_other")

    CustomFieldDefinition.objects.filter(
        group__title="Accessibility & Accommodation",
        name="Preferred Communication Format",
        input_type="select",
    ).update(input_type="select_other")

    # 3. Rename "Other family member" to avoid confusion with "Other" free-text
    for field in CustomFieldDefinition.objects.filter(
        group__title="Emergency Contact",
        name="Emergency Contact Relationship",
    ):
        opts = field.options_json if isinstance(field.options_json, list) else []
        if "Other family member" in opts:
            opts[opts.index("Other family member")] = "Another family member"
            field.options_json = opts
            field.save(update_fields=["options_json"])

    # 4. Remove duplicate "Other" from options_json on select_other fields —
    # the template adds "Other" automatically via __other__ value
    for field in CustomFieldDefinition.objects.filter(input_type="select_other"):
        opts = field.options_json if isinstance(field.options_json, list) else []
        if "Other" in opts:
            opts.remove("Other")
            field.options_json = opts
            field.save(update_fields=["options_json"])


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0021_province_field_select_other"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
