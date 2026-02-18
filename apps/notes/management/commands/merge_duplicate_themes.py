"""Merge duplicate SuggestionTheme records that share the same name per program.

Usage:
    python manage.py merge_duplicate_themes --dry-run   # preview only
    python manage.py merge_duplicate_themes              # merge + delete dupes
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.notes.models import (
    SuggestionLink, SuggestionTheme, recalculate_theme_priority,
)


class Command(BaseCommand):
    help = "Merge duplicate suggestion themes (same name, same program)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would be merged without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Group all themes by (program_id, normalised name)
        groups = defaultdict(list)
        for theme in SuggestionTheme.objects.select_related("program").order_by("pk"):
            key = (theme.program_id, theme.name.strip().lower())
            groups[key].append(theme)

        # Filter to groups with duplicates
        dupes = {k: v for k, v in groups.items() if len(v) > 1}

        if not dupes:
            self.stdout.write(self.style.SUCCESS("No duplicate themes found."))
            return

        self.stdout.write(f"Found {len(dupes)} duplicate group(s):\n")

        total_merged = 0
        total_deleted = 0

        for (program_id, name_lower), themes in dupes.items():
            # Pick the theme with the most links as primary (oldest as tiebreaker)
            link_counts = {}
            for t in themes:
                link_counts[t.pk] = SuggestionLink.objects.filter(theme=t).count()

            themes.sort(key=lambda t: (-link_counts[t.pk], t.pk))
            primary = themes[0]
            duplicates = themes[1:]

            self.stdout.write(
                f"\n  Program {program_id}: \"{primary.name}\"\n"
                f"    Primary: pk={primary.pk} ({link_counts[primary.pk]} links)\n"
                f"    Duplicates: {', '.join(f'pk={d.pk} ({link_counts[d.pk]} links)' for d in duplicates)}"
            )

            if dry_run:
                total_merged += len(duplicates)
                continue

            with transaction.atomic():
                for dupe in duplicates:
                    # Move links from duplicate to primary
                    moved = 0
                    for link in SuggestionLink.objects.filter(theme=dupe):
                        _, created = SuggestionLink.objects.get_or_create(
                            theme=primary,
                            progress_note_id=link.progress_note_id,
                            defaults={
                                "auto_linked": link.auto_linked,
                                "linked_by": link.linked_by,
                            },
                        )
                        if created:
                            moved += 1

                    # Merge keywords
                    if dupe.keywords and not primary.keywords:
                        primary.keywords = dupe.keywords

                    # Keep the longer description
                    if len(dupe.description) > len(primary.description):
                        primary.description = dupe.description

                    self.stdout.write(
                        f"    Merged pk={dupe.pk} -> pk={primary.pk} "
                        f"({moved} links moved)"
                    )
                    dupe.delete()
                    total_deleted += 1

                primary.save(update_fields=["keywords", "description", "updated_at"])
                recalculate_theme_priority(primary)

            total_merged += len(duplicates)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry run: {total_merged} theme(s) would be merged. "
                    f"Run without --dry-run to apply."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDone: {total_deleted} duplicate(s) merged and deleted."
                )
            )
