"""Data migration: create a Partner for each existing ReportTemplate.

For each existing template, a Partner is created with the template's name
and partner_type="funder" (safe default). The template's programs M2M is
copied to the partner's programs M2M, and the template is linked to the
new partner.

Some production databases were left in a partially-migrated state where the
legacy ReportTemplate/FunderProfile M2M table was missing even though the main
tables existed. Accessing ``template.programs`` through the ORM crashes in that
state, so this migration reads the join table defensively and falls back to the
pre-rename table name when needed.
"""
from django.db import migrations


CURRENT_TEMPLATE_PROGRAMS_TABLE = "report_templates_programs"
LEGACY_TEMPLATE_PROGRAMS_TABLE = "funder_profiles_programs"


def _get_existing_tables(connection):
    return set(connection.introspection.table_names())


def _read_program_ids(connection, quote_name, table_name, template_column, template_pk):
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {quote_name('program_id')} "
            f"FROM {quote_name(table_name)} "
            f"WHERE {quote_name(template_column)} = %s",
            [template_pk],
        )
        return [row[0] for row in cursor.fetchall()]


def _get_template_program_ids(connection, quote_name, template_pk, existing_tables=None):
    existing_tables = (
        existing_tables
        if existing_tables is not None
        else _get_existing_tables(connection)
    )

    if CURRENT_TEMPLATE_PROGRAMS_TABLE in existing_tables:
        return _read_program_ids(
            connection,
            quote_name,
            CURRENT_TEMPLATE_PROGRAMS_TABLE,
            "reporttemplate_id",
            template_pk,
        )

    if LEGACY_TEMPLATE_PROGRAMS_TABLE in existing_tables:
        return _read_program_ids(
            connection,
            quote_name,
            LEGACY_TEMPLATE_PROGRAMS_TABLE,
            "funderprofile_id",
            template_pk,
        )

    return []


def _ensure_partner_programs_table(schema_editor, Partner, existing_tables=None):
    existing_tables = (
        existing_tables
        if existing_tables is not None
        else _get_existing_tables(schema_editor.connection)
    )
    through_model = Partner._meta.get_field("programs").remote_field.through
    through_table = through_model._meta.db_table

    if through_table not in existing_tables:
        schema_editor.create_model(through_model)
        existing_tables.add(through_table)

    return through_table


def forwards(apps, schema_editor):
    ReportTemplate = apps.get_model("reports", "ReportTemplate")
    Partner = apps.get_model("reports", "Partner")
    connection = schema_editor.connection
    existing_tables = _get_existing_tables(connection)

    _ensure_partner_programs_table(schema_editor, Partner, existing_tables)

    for template in ReportTemplate.objects.all():
        partner = Partner.objects.create(
            name=template.name,
            partner_type="funder",
        )
        program_ids = _get_template_program_ids(
            connection,
            schema_editor.quote_name,
            template.pk,
            existing_tables,
        )
        if program_ids:
            partner.programs.set(program_ids)
        # Link template to partner
        template.partner = partner
        template.save(update_fields=["partner"])


def backwards(apps, schema_editor):
    # Reverse: copy partner.programs back to template.programs, unlink partner
    ReportTemplate = apps.get_model("reports", "ReportTemplate")
    Partner = apps.get_model("reports", "Partner")
    existing_tables = _get_existing_tables(schema_editor.connection)

    for template in ReportTemplate.objects.select_related("partner").all():
        if template.partner:
            if CURRENT_TEMPLATE_PROGRAMS_TABLE in existing_tables:
                template.programs.set(template.partner.programs.all())
            template.partner = None
            template.save(update_fields=["partner"])

    # Delete auto-created partners
    Partner.objects.filter(partner_type="funder").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0008_partner_report_section_metric"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
