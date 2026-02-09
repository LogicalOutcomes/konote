"""
Check that French translations are healthy.

Loads the French .mo file, verifies canary strings are translated, and
counts overall coverage. Designed for CI, startup checks, or manual use.

Usage:
    python manage.py check_translations          # Check all languages
    python manage.py check_translations --lang fr # Check French only
    python manage.py check_translations --strict  # Exit 1 on any warning

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
"""

import gettext as gettext_module
import os
import re
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify translation files exist, load correctly, and cover key strings."

    # ------------------------------------------------------------------
    # Canary strings: critical UI strings that must be translated.
    # Each tuple is (English msgid, expected French msgstr substring).
    # If the French translation is missing or equals the English, the
    # check fails. We only need a substring match so minor wording
    # changes don't break the check.
    # ------------------------------------------------------------------
    CANARY_STRINGS = [
        # Login page
        ("Sign In", "Connexion"),
        ("Password", "Mot de passe"),
        # Navigation
        ("Home", "Accueil"),
        ("Reports", "Rapports"),
        ("Settings", "Param"),
        ("Sign Out", "connexion"),
        # Core workflow
        ("Save Changes", "Enregistrer"),
        ("Cancel", "Annuler"),
        ("First Name", "nom"),
        # Export/reports (the SafeLocaleMiddleware canary string)
        ("Program Outcome Report", "résultats"),
        # Accessibility
        ("Skip to main content", "Passer au contenu"),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--lang",
            default="fr",
            help="Language code to check (default: fr).",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat warnings (e.g. low coverage) as errors.",
        )

    def handle(self, *args, **options):
        lang = options["lang"]
        strict = options["strict"]

        self.stdout.write(f"\nKoNote2 Translation Check (language: {lang})")
        self.stdout.write("=" * 55)

        errors = []
        warnings = []

        # ----------------------------------------------------------
        # 1. Check that the .mo file exists
        # ----------------------------------------------------------
        mo_path = self._find_mo_file(lang)
        if mo_path is None:
            errors.append(
                f"Compiled translation file (.mo) not found for '{lang}'. "
                f"Expected at: locale/{lang}/LC_MESSAGES/django.mo"
            )
            self.stdout.write(self.style.ERROR(f"  [FAIL] .mo file missing for '{lang}'"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  [PASS] .mo file exists: {mo_path}"))

            # ----------------------------------------------------------
            # 2. Check that the .mo file loads without errors
            # ----------------------------------------------------------
            catalog = self._load_catalog(mo_path)
            if catalog is None:
                errors.append(
                    f"Failed to load .mo file at {mo_path}. "
                    "The file may be corrupted. "
                    "Re-run: python manage.py compilemessages"
                )
                self.stdout.write(self.style.ERROR("  [FAIL] .mo file failed to load"))
            else:
                self.stdout.write(self.style.SUCCESS("  [PASS] .mo file loads correctly"))

                # ----------------------------------------------------------
                # 3. Check canary strings
                # ----------------------------------------------------------
                canary_failures = self._check_canaries(catalog, lang)
                if canary_failures:
                    for msgid, detail in canary_failures:
                        errors.append(f"Canary string not translated: \"{msgid}\" -- {detail}")
                        self.stdout.write(
                            self.style.ERROR(f"  [FAIL] Missing: \"{msgid}\" -- {detail}")
                        )
                else:
                    count = len(self.CANARY_STRINGS)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [PASS] All {count} canary strings translated"
                        )
                    )

                # ----------------------------------------------------------
                # 4. Count coverage from the .po file
                # ----------------------------------------------------------
                po_path = mo_path.with_suffix(".po")
                if po_path.exists():
                    total, translated, untranslated, fuzzy = self._count_coverage(po_path)
                    if total > 0:
                        pct = (translated / total) * 100
                        self.stdout.write(
                            f"  [INFO] Coverage: {translated}/{total} "
                            f"({pct:.0f}%) translated"
                        )
                        if fuzzy:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  [WARN] {fuzzy} fuzzy (needs review) entries"
                                )
                            )
                            warnings.append(f"{fuzzy} fuzzy entries need review")
                        if untranslated:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  [WARN] {untranslated} untranslated entries"
                                )
                            )
                            warnings.append(f"{untranslated} untranslated entries")
                        # Coverage threshold: warn below 90%
                        if pct < 90:
                            msg = f"Translation coverage is {pct:.0f}% (below 90% threshold)"
                            warnings.append(msg)
                            self.stdout.write(self.style.WARNING(f"  [WARN] {msg}"))
                    else:
                        warnings.append("No translatable strings found in .po file")
                        self.stdout.write(
                            self.style.WARNING("  [WARN] No translatable strings found")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [WARN] .po source file not found at {po_path} "
                            "(coverage check skipped)"
                        )
                    )

                # ----------------------------------------------------------
                # 5. Check .mo is not older than .po
                # ----------------------------------------------------------
                if po_path.exists() and mo_path.exists():
                    po_mtime = po_path.stat().st_mtime
                    mo_mtime = mo_path.stat().st_mtime
                    if po_mtime > mo_mtime:
                        msg = (
                            ".po file is newer than .mo file -- translations may be stale. "
                            "Run: python manage.py compilemessages"
                        )
                        warnings.append(msg)
                        self.stdout.write(self.style.WARNING(f"  [WARN] {msg}"))
                    else:
                        self.stdout.write(
                            self.style.SUCCESS("  [PASS] .mo file is up to date with .po")
                        )

                # ----------------------------------------------------------
                # 6. Lightweight check: template string count vs .po entries
                #    Catches the common case of new pages with untranslated
                #    strings. Full extraction lives in translate_strings.
                # ----------------------------------------------------------
                if po_path.exists():
                    template_count = self._quick_template_count()
                    po_count = total if total > 0 else 0
                    gap = template_count - po_count
                    # Threshold: warn if templates have 5+ more strings than .po
                    if gap > 5:
                        msg = (
                            f"Template files contain ~{template_count} "
                            f"translatable items (trans + blocktrans) but "
                            f"django.po has only {po_count} entries "
                            f"(gap: {gap}). "
                            f"Run: python manage.py translate_strings"
                        )
                        warnings.append(msg)
                        self.stdout.write(self.style.WARNING(f"  [WARN] {msg}"))
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  [PASS] Template items (~{template_count} "
                                f"trans + blocktrans) vs .po entries "
                                f"({po_count}) — no significant gap"
                            )
                        )

        # ----------------------------------------------------------
        # Summary
        # ----------------------------------------------------------
        self.stdout.write("")

        if errors:
            self.stdout.write(self.style.ERROR(
                f"  FAILED: {len(errors)} error(s) found.\n"
            ))
            for err in errors:
                self.stdout.write(self.style.ERROR(f"    - {err}"))
            self.stdout.write("")
            sys.exit(1)

        if warnings and strict:
            self.stdout.write(self.style.WARNING(
                f"  STRICT MODE: {len(warnings)} warning(s) treated as errors.\n"
            ))
            for warn in warnings:
                self.stdout.write(self.style.WARNING(f"    - {warn}"))
            self.stdout.write("")
            sys.exit(1)

        if warnings:
            self.stdout.write(self.style.WARNING(
                f"  PASSED with {len(warnings)} warning(s).\n"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "  All translation checks passed.\n"
            ))

        sys.exit(0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_mo_file(self, lang):
        """Find the .mo file for the given language in LOCALE_PATHS."""
        # Check each path in LOCALE_PATHS
        for locale_dir in getattr(settings, "LOCALE_PATHS", []):
            mo_path = Path(locale_dir) / lang / "LC_MESSAGES" / "django.mo"
            if mo_path.exists():
                return mo_path

        # Fallback: check BASE_DIR/locale
        base_dir = getattr(settings, "BASE_DIR", None)
        if base_dir:
            mo_path = Path(base_dir) / "locale" / lang / "LC_MESSAGES" / "django.mo"
            if mo_path.exists():
                return mo_path

        return None

    def _load_catalog(self, mo_path):
        """Try to load a .mo file and return the GNUTranslations object."""
        try:
            with open(mo_path, "rb") as f:
                catalog = gettext_module.GNUTranslations(f)
            return catalog
        except Exception as e:
            self.stderr.write(f"Error loading .mo file: {e}")
            return None

    def _check_canaries(self, catalog, lang):
        """Check that canary strings are translated. Returns list of failures."""
        failures = []
        for english, expected_substring in self.CANARY_STRINGS:
            translated = catalog.gettext(english)

            # If the translation equals the English original, it's untranslated
            if translated == english:
                failures.append((english, "returned English (untranslated)"))
                continue

            # If the expected substring is not in the translation, flag it
            if expected_substring.lower() not in translated.lower():
                failures.append((
                    english,
                    f"got \"{translated}\" but expected it to contain \"{expected_substring}\""
                ))

        return failures

    def _count_coverage(self, po_path):
        """
        Parse a .po file and count translated vs untranslated entries.
        Returns (total, translated, untranslated, fuzzy).
        """
        total = 0
        translated = 0
        untranslated = 0
        fuzzy = 0

        with open(po_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        in_header = True
        is_fuzzy = False

        while i < len(lines):
            line = lines[i].strip()

            # Track fuzzy flag
            if line.startswith("#,") and "fuzzy" in line:
                is_fuzzy = True
                i += 1
                continue

            # Found a msgid line (not the header empty msgid)
            if line.startswith('msgid "') and line != 'msgid ""':
                # This is a real entry
                if in_header:
                    in_header = False

                # Collect the full msgid (may be multiline)
                msgid_text = self._extract_string(line, 'msgid "')
                i += 1
                while i < len(lines) and lines[i].strip().startswith('"'):
                    msgid_text += self._extract_continuation(lines[i].strip())
                    i += 1

                # Now find the msgstr
                msgstr_text = ""
                while i < len(lines):
                    sline = lines[i].strip()
                    if sline.startswith('msgstr "'):
                        msgstr_text = self._extract_string(sline, 'msgstr "')
                        i += 1
                        while i < len(lines) and lines[i].strip().startswith('"'):
                            msgstr_text += self._extract_continuation(lines[i].strip())
                            i += 1
                        break
                    i += 1

                total += 1
                if msgstr_text:
                    translated += 1
                else:
                    untranslated += 1

                if is_fuzzy:
                    fuzzy += 1
                    is_fuzzy = False

                continue
            elif line == 'msgid ""':
                # Could be header or multiline msgid
                # Check if next line is also a string continuation (multiline msgid)
                i += 1
                if i < len(lines) and lines[i].strip().startswith('"') and not in_header:
                    # Multiline msgid -- collect it
                    msgid_text = ""
                    while i < len(lines) and lines[i].strip().startswith('"'):
                        msgid_text += self._extract_continuation(lines[i].strip())
                        i += 1

                    if msgid_text:
                        # Find msgstr
                        msgstr_text = ""
                        while i < len(lines):
                            sline = lines[i].strip()
                            if sline.startswith('msgstr "'):
                                msgstr_text = self._extract_string(sline, 'msgstr "')
                                i += 1
                                while i < len(lines) and lines[i].strip().startswith('"'):
                                    msgstr_text += self._extract_continuation(lines[i].strip())
                                    i += 1
                                break
                            elif sline.startswith('msgstr ""'):
                                i += 1
                                while i < len(lines) and lines[i].strip().startswith('"'):
                                    msgstr_text += self._extract_continuation(lines[i].strip())
                                    i += 1
                                break
                            i += 1

                        total += 1
                        if msgstr_text:
                            translated += 1
                        else:
                            untranslated += 1

                        if is_fuzzy:
                            fuzzy += 1
                            is_fuzzy = False
                else:
                    # This is the header -- skip through it
                    if in_header:
                        in_header = False
                        # Skip past the header msgstr
                        while i < len(lines):
                            sline = lines[i].strip()
                            if sline.startswith("msgstr"):
                                i += 1
                                while i < len(lines) and lines[i].strip().startswith('"'):
                                    i += 1
                                break
                            i += 1
                continue

            # Reset fuzzy if we hit a non-comment, non-msgid line
            if not line.startswith("#"):
                is_fuzzy = False

            i += 1

        return total, translated, untranslated, fuzzy

    def _extract_string(self, line, prefix):
        """Extract string content from a line like: msgid "Hello" """
        # Remove prefix and trailing quote
        content = line[len(prefix):]
        if content.endswith('"'):
            content = content[:-1]
        return content

    def _extract_continuation(self, line):
        """Extract string content from a continuation line like: "more text" """
        if line.startswith('"') and line.endswith('"'):
            return line[1:-1]
        return ""

    def _quick_template_count(self):
        """
        Fast count of unique translatable strings in templates.

        Counts both {% trans %} strings and {% blocktrans %} blocks.
        This is a lightweight check — counts unique strings without
        building a full extraction set. The full extraction lives in
        the translate_strings command.
        """
        trans_pattern = re.compile(
            r"""\{%[-\s]*trans\s+['"](.+?)['"]\s*[-]?%\}"""
        )
        # Count blocktrans blocks (each block = one translatable unit)
        blocktrans_pattern = re.compile(
            r"""\{%[-\s]*blocktrans[\s%]"""
        )
        trans_strings = set()
        blocktrans_count = 0
        base_dir = getattr(settings, "BASE_DIR", None)
        if not base_dir:
            return 0

        template_dir = Path(base_dir) / "templates"
        if not template_dir.exists():
            return 0

        for html_file in template_dir.rglob("*.html"):
            try:
                content = html_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            trans_strings.update(trans_pattern.findall(content))
            blocktrans_count += len(blocktrans_pattern.findall(content))

        return len(trans_strings) + blocktrans_count
