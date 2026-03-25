"""
Import custom field groups and definitions from a JSON file.

Reads a JSON file containing custom_field_groups and creates the corresponding
CustomFieldGroup and CustomFieldDefinition records. Idempotent — safe to run
multiple times; existing groups/fields are skipped.

Expected JSON structure::

    {
      "custom_field_groups": [
        {
          "title": "Demographics",
          "fields": [
            {
              "name": "Legal First Name",
              "input_type": "text",
              "options": ["opt1", "opt2"],
              "is_required": true,
              "is_sensitive": true
            }
          ]
        }
      ]
    }

Supported input_type values in JSON: text, textarea, select, multi_select,
select_other, multi_select_other, date, number, checkbox, lookup.

- ``checkbox`` is stored as ``select`` with options ``["Yes", "No"]``.
- ``lookup`` is stored as ``text`` (KoNote has no native lookup type).

Usage:
  python manage.py import_custom_fields path/to/custom-fields.json
  python manage.py import_custom_fields custom-fields.json --replace
  python manage.py import_custom_fields custom-fields.json --dry-run
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.clients.models import CustomFieldDefinition, CustomFieldGroup


# Map non-native input types to KoNote equivalents.
INPUT_TYPE_MAP = {
    "checkbox": "select",
    "lookup": "text",
}

# Default options injected when converting checkbox → select.
CHECKBOX_OPTIONS = ["Yes", "No"]


class Command(BaseCommand):
    help = "Import custom field groups and definitions from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to the JSON file containing custom_field_groups.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Archive all existing custom field groups before importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without writing to the database.",
        )

    def handle(self, *args, **options):
        json_path = Path(options["json_file"])
        if not json_path.exists():
            raise CommandError(f"File not found: {json_path}")

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CommandError(f"Invalid JSON: {exc}")

        groups_data = data.get("custom_field_groups")
        if not groups_data or not isinstance(groups_data, list):
            raise CommandError(
                "JSON must contain a 'custom_field_groups' list at the top level."
            )

        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved.\n"))
            self._preview(groups_data)
            return

        with transaction.atomic():
            if options["replace"]:
                archived = CustomFieldGroup.objects.filter(status="active").update(
                    status="archived"
                )
                self.stdout.write(f"  Archived {archived} existing group(s).")

            groups_created, fields_created = self._import(groups_data)

        self.stdout.write(
            self.style.SUCCESS(
                f"  Import complete: {groups_created} group(s) and "
                f"{fields_created} field(s) created."
            )
        )

    # ------------------------------------------------------------------

    def _preview(self, groups_data):
        """Print what would be created without touching the DB."""
        for sort_idx, group_def in enumerate(groups_data):
            title = group_def.get("title", f"(untitled group {sort_idx})")
            fields = group_def.get("fields", [])
            self.stdout.write(f"  Group: {title}  ({len(fields)} field(s))")
            for field_def in fields:
                name = field_def.get("name", "(unnamed)")
                raw_type = field_def.get("input_type", "text")
                mapped = INPUT_TYPE_MAP.get(raw_type, raw_type)
                suffix = f" (mapped from {raw_type})" if mapped != raw_type else ""
                self.stdout.write(f"    - {name}  [{mapped}{suffix}]")

    def _import(self, groups_data):
        """Create groups and fields, skipping duplicates."""
        groups_created = 0
        fields_created = 0

        for sort_idx, group_def in enumerate(groups_data):
            title = group_def.get("title")
            if not title:
                self.stdout.write(
                    self.style.WARNING(f"  Skipping group at index {sort_idx}: no title.")
                )
                continue

            group, created = CustomFieldGroup.objects.get_or_create(
                title=title,
                defaults={
                    "sort_order": (sort_idx + 1) * 10,
                    "status": "active",
                },
            )
            if created:
                groups_created += 1
                self.stdout.write(f"  + Group: {title}")
            else:
                # Re-activate if archived.
                if group.status != "active":
                    group.status = "active"
                    group.save(update_fields=["status"])
                    self.stdout.write(f"  ~ Group reactivated: {title}")
                else:
                    self.stdout.write(f"  = Group exists: {title}")

            for field_idx, field_def in enumerate(group_def.get("fields", [])):
                name = field_def.get("name")
                if not name:
                    continue

                raw_type = field_def.get("input_type", "text")
                mapped_type = INPUT_TYPE_MAP.get(raw_type, raw_type)

                # Validate that the mapped type is accepted by the model.
                valid_types = {c[0] for c in CustomFieldDefinition.INPUT_TYPE_CHOICES}
                if mapped_type not in valid_types:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    Skipping '{name}': unsupported type '{raw_type}'"
                        )
                    )
                    continue

                options = list(field_def.get("options", []))
                if raw_type == "checkbox" and not options:
                    options = list(CHECKBOX_OPTIONS)

                is_sensitive = field_def.get("is_sensitive", False)
                # Sensitive fields default to hidden from front desk.
                front_desk_access = "none" if is_sensitive else "edit"

                _, was_created = CustomFieldDefinition.objects.get_or_create(
                    group=group,
                    name=name,
                    defaults={
                        "input_type": mapped_type,
                        "is_required": field_def.get("is_required", False),
                        "is_sensitive": is_sensitive,
                        "front_desk_access": front_desk_access,
                        "options_json": options,
                        "sort_order": field_idx * 10,
                        "status": "active",
                    },
                )
                if was_created:
                    fields_created += 1

        return groups_created, fields_created
