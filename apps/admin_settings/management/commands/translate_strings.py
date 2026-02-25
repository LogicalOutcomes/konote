"""
Extract translatable strings from templates and Python, add to .po, compile .mo.

Replaces the need for gettext/makemessages on Windows. Uses regex extraction
and polib for .po/.mo handling — pure Python, no system dependencies.

Empty translations can be filled in by:
  - Claude Code (editing the .po file directly)
  - An OpenAI-compatible translation API (--auto-translate flag)

Usage:
    python manage.py translate_strings                       # Extract + add missing + compile
    python manage.py translate_strings --auto-translate      # Also auto-translate empty strings
    python manage.py translate_strings --auto-translate --review  # Mark API translations as fuzzy
    python manage.py translate_strings --dry-run             # Show what would change

Exit codes:
    0 = success
    1 = error (duplicate msgids, file write failure, etc.)

Environment variables (for --auto-translate):
    TRANSLATE_API_KEY   — API key (required)
    TRANSLATE_API_BASE  — API base URL (default: https://api.openai.com/v1)
    TRANSLATE_MODEL     — Model name (default: gpt-4o-mini)
"""

import json
import logging
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import polib
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# System prompt for the translation API — Canadian French nonprofit context.
TRANSLATION_SYSTEM_PROMPT = """\
You are a professional translator for a Canadian nonprofit case-management \
application. Translate English strings to Canadian French.

Rules:
- Use formal "vous" (never "tu")
- Use Canadian nonprofit terminology: organisme (not organisation), \
bénéficiaire, intervenant, programme
- Use Canadian French terms: courriel (not e-mail), téléverser (not uploader)
- Use French typographic conventions: space before : ; ? !
- Use « guillemets » for quotation marks (not "quotes")
- Preserve ALL placeholders exactly as-is: %(name)s, %(count)d, {{ var }}, \
{record_id}, etc.
- Preserve ALL HTML tags exactly as-is: <strong>, <em>, <a href="...">, etc.
- Do not translate text inside placeholders or HTML attributes

You will receive a JSON object mapping numbers to English strings.
Return a JSON object mapping the same numbers to French translations.
Return ONLY the JSON object — no markdown fences, no explanation.\
"""


class Command(BaseCommand):
    help = "Extract translatable strings, add missing entries to .po, compile .mo."

    # Regex for {% trans "string" %} and {% trans 'string' %}
    TEMPLATE_PATTERN = re.compile(
        r"""\{%[-\s]*trans\s+['"](.+?)['"]\s*[-]?%\}"""
    )

    # Regex for _("string"), gettext("string"), gettext_lazy("string")
    PYTHON_PATTERN = re.compile(
        r"""(?:gettext_lazy|gettext|_)\(\s*['"](.+?)['"]\s*\)"""
    )

    # Directories/patterns to skip when scanning Python files
    PYTHON_SKIP = {"migrations", "__pycache__", "tests", "test_"}

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without modifying files.",
        )
        parser.add_argument(
            "--lang",
            default="fr",
            help="Target language code (default: fr).",
        )
        parser.add_argument(
            "--auto-translate",
            action="store_true",
            help=(
                "Auto-translate empty strings via an OpenAI-compatible API. "
                "Requires TRANSLATE_API_KEY environment variable."
            ),
        )
        parser.add_argument(
            "--review",
            action="store_true",
            help=(
                "Mark API-translated strings as fuzzy for human review. "
                "Only used with --auto-translate."
            ),
        )

    # Batch size for API translation calls.
    TRANSLATE_BATCH_SIZE = 25

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        lang = options["lang"]
        auto_translate = options["auto_translate"]
        review = options["review"]

        # Determine total phases for display numbering.
        total_phases = 4 if auto_translate else 3

        self.stdout.write("\nKoNote Translation Sync")
        self.stdout.write("=" * 40)

        base_dir = Path(settings.BASE_DIR)

        # ----------------------------------------------------------
        # Phase 1: Extract strings
        # ----------------------------------------------------------
        self.stdout.write(f"\n[1/{total_phases}] Extracting strings...")

        template_strings, template_file_count, blocktrans_count = (
            self._extract_templates(base_dir)
        )
        python_strings, python_file_count = self._extract_python(base_dir)

        all_strings = template_strings | python_strings

        self.stdout.write(
            f"      Templates: {len(template_strings):,} trans strings "
            f"+ {blocktrans_count} blocktrans blocks "
            f"from {template_file_count} files"
        )
        self.stdout.write(
            f"      Python:    {len(python_strings):,} strings "
            f"from {python_file_count} files"
        )
        self.stdout.write(
            f"      Total unique: {len(all_strings):,} extractable strings"
        )
        if blocktrans_count:
            self.stdout.write(
                f"      [i] {blocktrans_count} blocktrans blocks are in "
                f".po from earlier extraction — verify they have translations"
            )

        # ----------------------------------------------------------
        # Phase 2: Compare with .po and add missing
        # ----------------------------------------------------------
        self.stdout.write(f"\n[2/{total_phases}] Comparing with django.po...")

        po_path = self._find_po_file(lang, base_dir)
        if po_path is None:
            self.stderr.write(self.style.ERROR(
                f"\n  ERROR: .po file not found for '{lang}'. "
                f"Expected at: locale/{lang}/LC_MESSAGES/django.po\n"
            ))
            sys.exit(1)

        po = polib.pofile(str(po_path))
        existing_msgids = {entry.msgid for entry in po}

        translated_count = sum(
            1 for entry in po
            if (entry.msgstr or entry.msgstr_plural) and not entry.obsolete
        )
        empty_count = sum(
            1 for entry in po
            if not entry.msgstr and not entry.msgstr_plural
            and not entry.obsolete and entry.msgid
        )

        self.stdout.write(
            f"      Existing .po entries: {len(po)} "
            f"({translated_count} translated)"
        )

        new_strings = sorted(all_strings - existing_msgids)
        stale_strings = sorted(existing_msgids - all_strings - {""})

        self.stdout.write(
            self.style.SUCCESS(
                f"      [OK] {translated_count} already translated"
            )
        )

        if new_strings:
            self.stdout.write(
                self.style.WARNING(
                    f"      + {len(new_strings)} new strings to add"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "      + 0 new strings (all code strings are in .po)"
                )
            )

        if empty_count:
            self.stdout.write(
                self.style.WARNING(
                    f"      [!!] {empty_count} existing strings with "
                    f"empty translation"
                )
            )

        if stale_strings:
            self.stdout.write(
                f"      [i] {len(stale_strings)} strings in .po "
                f"not found in code (possibly stale)"
            )

        # Check for duplicate msgids
        msgid_counts = {}
        for entry in po:
            if entry.msgid:
                msgid_counts[entry.msgid] = msgid_counts.get(entry.msgid, 0) + 1
        duplicates = {k: v for k, v in msgid_counts.items() if v > 1}
        if duplicates:
            self.stderr.write(self.style.ERROR(
                f"\n  ERROR: {len(duplicates)} duplicate msgid(s) in .po file:"
            ))
            for msgid, count in sorted(duplicates.items()):
                self.stderr.write(
                    self.style.ERROR(f"    - \"{msgid}\" appears {count} times")
                )
            self.stderr.write(self.style.ERROR(
                "  Fix duplicates before running translate_strings.\n"
            ))
            sys.exit(1)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n  --dry-run: No files modified."
            ))
            if new_strings:
                self.stdout.write("\n  New strings that would be added:")
                for s in new_strings[:20]:
                    self.stdout.write(f"    + \"{s}\"")
                if len(new_strings) > 20:
                    self.stdout.write(
                        f"    ... and {len(new_strings) - 20} more"
                    )
            total_empty = len(new_strings) + empty_count
            if auto_translate and total_empty:
                num_batches = (
                    (total_empty + self.TRANSLATE_BATCH_SIZE - 1)
                    // self.TRANSLATE_BATCH_SIZE
                )
                self.stdout.write(self.style.WARNING(
                    f"\n  --auto-translate: {total_empty} strings "
                    f"would be sent to the translation API "
                    f"({num_batches} batch(es) of "
                    f"{self.TRANSLATE_BATCH_SIZE})."
                ))
                if review:
                    self.stdout.write(
                        "  --review: translations would be marked fuzzy."
                    )
            self._print_summary(total_empty, dry_run=True)
            return

        # Add new strings to .po
        if new_strings:
            for msgid in new_strings:
                entry = polib.POEntry(msgid=msgid, msgstr="")
                po.append(entry)
            self._save_po(po, po_path)
            self.stdout.write(self.style.SUCCESS(
                f"      [OK] Added {len(new_strings)} entries to {po_path.name}"
            ))

        # ----------------------------------------------------------
        # Phase 3 (optional): Auto-translate empty strings via API
        # ----------------------------------------------------------
        if auto_translate:
            self.stdout.write(
                f"\n[3/{total_phases}] Auto-translating empty strings..."
            )
            translated = self._auto_translate_empty(po, review=review)
            if translated:
                self._save_po(po, po_path)
                self.stdout.write(self.style.SUCCESS(
                    f"      [OK] Translated {translated} strings via API"
                ))
                if review:
                    self.stdout.write(
                        "      [i] Translations marked as fuzzy for review"
                    )
            else:
                self.stdout.write(
                    "      No empty strings to translate."
                )

        # ----------------------------------------------------------
        # Final phase: Compile .mo
        # ----------------------------------------------------------
        compile_phase = total_phases
        self.stdout.write(
            f"\n[{compile_phase}/{total_phases}] Compiling django.mo..."
        )

        mo_path = po_path.with_suffix(".mo")
        fd, tmp_mo = tempfile.mkstemp(suffix=".mo", dir=str(mo_path.parent))
        os.close(fd)
        try:
            po.save_as_mofile(tmp_mo)
            shutil.move(tmp_mo, str(mo_path))
            compiled_count = len([e for e in po if e.translated()])
            self.stdout.write(self.style.SUCCESS(
                f"      [OK] Compiled {compiled_count} entries to {mo_path.name}"
            ))
        except Exception as e:
            if os.path.exists(tmp_mo):
                os.unlink(tmp_mo)
            self.stderr.write(self.style.ERROR(
                f"\n  ERROR compiling .mo file: {e}\n"
            ))
            sys.exit(1)

        # ----------------------------------------------------------
        # Summary
        # ----------------------------------------------------------
        remaining_empty = sum(
            1 for entry in po
            if not entry.msgstr and not entry.msgstr_plural
            and not entry.obsolete and entry.msgid
        )
        self._print_summary(remaining_empty, dry_run=False)

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def _save_po(self, po, po_path):
        """Save .po file safely via temp file."""
        fd, tmp_path = tempfile.mkstemp(
            suffix=".po", dir=str(po_path.parent)
        )
        os.close(fd)
        try:
            po.save(tmp_path)
            shutil.move(tmp_path, str(po_path))
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            self.stderr.write(self.style.ERROR(
                f"\n  ERROR writing .po file: {e}\n"
            ))
            sys.exit(1)

    # ------------------------------------------------------------------
    # Auto-translation helpers
    # ------------------------------------------------------------------

    def _auto_translate_empty(self, po, review=False):
        """Translate all empty msgstr entries via an OpenAI-compatible API.

        Sends strings in batches of TRANSLATE_BATCH_SIZE. Returns the total
        number of strings successfully translated.
        """
        api_key = os.environ.get("TRANSLATE_API_KEY", "")
        if not api_key:
            self.stderr.write(self.style.ERROR(
                "      ERROR: TRANSLATE_API_KEY environment variable not set."
            ))
            return 0

        api_base = os.environ.get(
            "TRANSLATE_API_BASE", "https://api.openai.com/v1"
        ).rstrip("/")
        model = os.environ.get("TRANSLATE_MODEL", "gpt-4o-mini")
        url = f"{api_base}/chat/completions"

        # Collect entries with empty translations.
        empty_entries = [
            entry for entry in po
            if not entry.msgstr and not entry.msgstr_plural
            and not entry.obsolete and entry.msgid
        ]

        if not empty_entries:
            return 0

        total_translated = 0

        # Process in batches.
        for batch_start in range(
            0, len(empty_entries), self.TRANSLATE_BATCH_SIZE
        ):
            batch = empty_entries[
                batch_start:batch_start + self.TRANSLATE_BATCH_SIZE
            ]
            batch_num = batch_start // self.TRANSLATE_BATCH_SIZE + 1
            total_batches = (
                (len(empty_entries) + self.TRANSLATE_BATCH_SIZE - 1)
                // self.TRANSLATE_BATCH_SIZE
            )

            # Build the numbered mapping for the API.
            source_map = {
                str(i): entry.msgid for i, entry in enumerate(batch)
            }

            self.stdout.write(
                f"      Batch {batch_num}/{total_batches} "
                f"({len(batch)} strings)..."
            )

            try:
                translations = self._call_translation_api(
                    url, api_key, model, source_map
                )
            except Exception as exc:
                logger.warning(
                    "Translation API error on batch %d: %s", batch_num, exc
                )
                self.stderr.write(self.style.WARNING(
                    f"      [!] Batch {batch_num} failed: {exc} — skipping"
                ))
                continue

            # Apply translations to the .po entries.
            batch_translated = 0
            for i, entry in enumerate(batch):
                key = str(i)
                if key in translations and translations[key]:
                    entry.msgstr = translations[key]
                    if review:
                        if "fuzzy" not in entry.flags:
                            entry.flags.append("fuzzy")
                    batch_translated += 1

            total_translated += batch_translated

        return total_translated

    def _call_translation_api(self, url, api_key, model, source_map):
        """Make a single API call and return the parsed translation mapping.

        Args:
            url: Full chat completions endpoint URL.
            api_key: API bearer token.
            model: Model name to use.
            source_map: Dict mapping string indices to English source strings.

        Returns:
            Dict mapping string indices to French translations.

        Raises:
            requests.RequestException: On HTTP errors or timeouts.
            ValueError: On JSON parse failures.
        """
        payload = {
            "model": model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(
                    source_map, ensure_ascii=False
                )},
            ],
        }

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if the model wraps the response.
        if content.startswith("```"):
            # Remove opening fence (with optional language tag) and closing fence.
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            translations = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"API returned invalid JSON: {exc}. "
                f"Response: {content[:200]}"
            ) from exc

        if not isinstance(translations, dict):
            raise ValueError(
                f"API returned {type(translations).__name__}, expected dict."
            )

        return translations

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    # Regex to detect {% blocktrans %} blocks (for gap reporting)
    BLOCKTRANS_PATTERN = re.compile(
        r"""\{%[-\s]*blocktrans[\s%]"""
    )

    def _extract_templates(self, base_dir):
        """Scan templates/**/*.html for {% trans %} strings and count blocktrans blocks.

        Scans both the top-level templates/ directory AND app-level
        templates (apps/*/templates/) so that all Django template dirs
        are covered including apps with APP_DIRS=True.
        """
        strings = set()
        file_count = 0
        blocktrans_count = 0

        # Collect all template directories: top-level + app-level
        template_dirs = []
        top_level = base_dir / "templates"
        if top_level.exists():
            template_dirs.append(top_level)

        apps_dir = base_dir / "apps"
        if apps_dir.exists():
            for app_dir in apps_dir.iterdir():
                app_templates = app_dir / "templates"
                if app_templates.exists():
                    template_dirs.append(app_templates)

        if not template_dirs:
            return strings, file_count, blocktrans_count

        comment_pattern = re.compile(
            r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}",
            re.DOTALL,
        )

        for template_dir in template_dirs:
            for html_file in template_dir.rglob("*.html"):
                try:
                    content = html_file.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue

                content = comment_pattern.sub("", content)

                matches = self.TEMPLATE_PATTERN.findall(content)
                bt_matches = self.BLOCKTRANS_PATTERN.findall(content)
                if matches or bt_matches:
                    strings.update(matches)
                    blocktrans_count += len(bt_matches)
                    file_count += 1

        return strings, file_count, blocktrans_count

    def _extract_python(self, base_dir):
        """Scan apps/**/*.py for _() / gettext() / gettext_lazy() strings."""
        strings = set()
        file_count = 0
        apps_dir = base_dir / "apps"

        if not apps_dir.exists():
            return strings, file_count

        for py_file in apps_dir.rglob("*.py"):
            parts = py_file.parts
            if any(skip in parts for skip in self.PYTHON_SKIP):
                continue
            if py_file.name.startswith("test_"):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            matches = self.PYTHON_PATTERN.findall(content)
            if matches:
                strings.update(matches)
                file_count += 1

        return strings, file_count

    def _find_po_file(self, lang, base_dir):
        """Find the .po file for the given language."""
        for locale_dir in getattr(settings, "LOCALE_PATHS", []):
            po_path = Path(locale_dir) / lang / "LC_MESSAGES" / "django.po"
            if po_path.exists():
                return po_path

        po_path = base_dir / "locale" / lang / "LC_MESSAGES" / "django.po"
        if po_path.exists():
            return po_path

        return None

    def _print_summary(self, empty_count, dry_run=False):
        """Print final summary line."""
        prefix = "(Dry run) " if dry_run else ""

        self.stdout.write("")
        if empty_count:
            self.stdout.write(self.style.WARNING(
                f"{prefix}Summary: {empty_count} strings still need "
                f"French translations."
            ))
            self.stdout.write(
                "  Ask Claude Code to translate the empty entries in django.po."
            )
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{prefix}Summary: All strings have French translations."
            ))
        self.stdout.write("")
