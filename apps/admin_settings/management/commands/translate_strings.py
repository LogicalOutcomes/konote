"""
Extract translatable strings from templates and Python, auto-translate, compile .mo.

Replaces the need for gettext/makemessages on Windows. Uses regex extraction
and polib for .po/.mo handling — pure Python, no system dependencies.

Auto-translates empty strings via any OpenAI-compatible API when configured.
Uses only the `requests` library (already a project dependency) — no vendor SDK needed.

Configuration (environment variables):
    TRANSLATE_API_KEY   — API key (required to enable auto-translation)
    TRANSLATE_API_BASE  — API base URL (default: https://api.openai.com/v1)
    TRANSLATE_MODEL     — Model name (default: gpt-5)

Translation quality matters — the default is a flagship model because this
runs infrequently (only when new strings are added). Override TRANSLATE_MODEL
for a cheaper option if needed.

Works with OpenAI, Open Router, Anthropic, local Ollama, or any
provider that supports the OpenAI chat completions format.

Usage:
    python manage.py translate_strings                # Extract + translate + compile
    python manage.py translate_strings --dry-run      # Show what would change
    python manage.py translate_strings --no-translate  # Extract + compile only

Exit codes:
    0 = success
    1 = error (duplicate msgids, file write failure, etc.)
"""

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand


# ── Translation prompt ──────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a translator for a Canadian nonprofit client management system called KoNote.

Rules:
- Translate English to Canadian French
- Use formal "vous" (not "tu")
- Use Canadian nonprofit terminology (organisme, bénéficiaire, intervenant)
- Use Canadian French terms: courriel (not e-mail), téléverser (not uploader)
- Keep UI text concise — space is limited
- Preserve ALL placeholders exactly: %(name)s, %(count)d, {{ var }}, {record_id}
- Preserve ALL HTML tags exactly: <strong>, <em>, <a href="...">, etc.
- Use French typographic conventions: space before colon, semicolon, question/exclamation marks
- Use « guillemets » for quotation marks
- Canadian spelling: organisation (not organization)

Return ONLY a JSON object mapping each number to its French translation.
Example input: {"1": "Sign In", "2": "Password"}
Example output: {"1": "Connexion", "2": "Mot de passe"}
"""

BATCH_SIZE = 25  # strings per API call


class Command(BaseCommand):
    help = "Extract translatable strings, auto-translate empty ones, compile .mo."

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
            "--no-translate",
            action="store_true",
            help="Skip auto-translation (extract and compile only).",
        )
        parser.add_argument(
            "--lang",
            default="fr",
            help="Target language code (default: fr).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        skip_translate = options["no_translate"]
        lang = options["lang"]

        self.stdout.write("\nKoNote Translation Sync")
        self.stdout.write("=" * 40)

        base_dir = Path(settings.BASE_DIR)

        # ----------------------------------------------------------
        # Phase 1: Extract strings
        # ----------------------------------------------------------
        self.stdout.write("\n[1/4] Extracting strings...")

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
        self.stdout.write(f"\n[2/4] Comparing with django.po...")

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
            1 for entry in po if entry.msgstr and not entry.obsolete
        )
        empty_count = sum(
            1 for entry in po
            if not entry.msgstr and not entry.obsolete and entry.msgid
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
            if total_empty:
                self.stdout.write(self.style.WARNING(
                    f"\n  {total_empty} strings would be auto-translated."
                ))
            self._print_summary(0, total_empty, dry_run=True)
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
        # Phase 3: Auto-translate empty strings
        # ----------------------------------------------------------
        # Collect all empty entries (including any we just added)
        empty_entries = [
            e for e in po
            if not e.msgstr and not e.obsolete and e.msgid
        ]

        if empty_entries and not skip_translate:
            self.stdout.write(
                f"\n[3/4] Auto-translating {len(empty_entries)} "
                f"empty strings..."
            )
            translated = self._auto_translate(empty_entries, lang)
            if translated > 0:
                self._save_po(po, po_path)
                self.stdout.write(self.style.SUCCESS(
                    f"      [OK] Translated {translated} strings"
                ))
            # Reload after saving
            po = polib.pofile(str(po_path))
        elif empty_entries and skip_translate:
            self.stdout.write(
                f"\n[3/4] Skipping translation (--no-translate)"
            )
            self.stdout.write(self.style.WARNING(
                f"      [!!] {len(empty_entries)} strings still untranslated"
            ))
        else:
            self.stdout.write(f"\n[3/4] No empty strings to translate.")

        # ----------------------------------------------------------
        # Phase 4: Compile .mo
        # ----------------------------------------------------------
        self.stdout.write(f"\n[4/4] Compiling django.mo...")

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
            if not entry.msgstr and not entry.obsolete and entry.msgid
        )
        self._print_summary(0, remaining_empty, dry_run=False)

    # ------------------------------------------------------------------
    # Auto-translation
    # ------------------------------------------------------------------

    def _auto_translate(self, empty_entries, lang):
        """
        Translate empty entries via OpenAI-compatible chat completions API.

        Uses only the `requests` library — no vendor SDK needed.
        Works with OpenAI, Open Router, Anthropic, Ollama, etc.

        Returns count of strings translated.
        """
        import requests as http_client

        api_key = os.environ.get("TRANSLATE_API_KEY", "")
        if not api_key:
            self.stdout.write(self.style.WARNING(
                "      [!!] TRANSLATE_API_KEY not set — skipping auto-translate.\n"
                "      Set the env var to enable. Works with any OpenAI-compatible API.\n"
                "      See: TRANSLATE_API_KEY, TRANSLATE_API_BASE, TRANSLATE_MODEL"
            ))
            return 0

        api_base = os.environ.get(
            "TRANSLATE_API_BASE", "https://api.openai.com/v1"
        ).rstrip("/")
        model = os.environ.get("TRANSLATE_MODEL", "gpt-5")
        url = f"{api_base}/chat/completions"

        self.stdout.write(
            f"      Using: {model} via {api_base}"
        )

        total_translated = 0

        for batch_start in range(0, len(empty_entries), BATCH_SIZE):
            batch = empty_entries[batch_start:batch_start + BATCH_SIZE]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (
                (len(empty_entries) + BATCH_SIZE - 1) // BATCH_SIZE
            )

            self.stdout.write(
                f"      Batch {batch_num}/{total_batches} "
                f"({len(batch)} strings)..."
            )

            # Build numbered dict for the prompt
            source = {}
            for i, entry in enumerate(batch, 1):
                source[str(i)] = entry.msgid

            payload = {
                "model": model,
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Translate these to {lang}. "
                            f"Return ONLY valid JSON.\n\n"
                            f"{json.dumps(source, ensure_ascii=False, indent=2)}"
                        ),
                    },
                ],
            }

            try:
                resp = http_client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract text from OpenAI-compatible response
                text = data["choices"][0]["message"]["content"].strip()

                # Strip markdown code fences if present
                if text.startswith("```"):
                    text = re.sub(r"^```\w*\n?", "", text)
                    text = re.sub(r"\n?```$", "", text)
                    text = text.strip()

                translations = json.loads(text)

                # Apply translations
                batch_count = 0
                for i, entry in enumerate(batch, 1):
                    key = str(i)
                    if key in translations and translations[key]:
                        entry.msgstr = translations[key]
                        batch_count += 1

                total_translated += batch_count

            except json.JSONDecodeError as e:
                self.stdout.write(self.style.WARNING(
                    f"      [!!] Could not parse API response for batch "
                    f"{batch_num}: {e}"
                ))
            except http_client.exceptions.HTTPError as e:
                self.stdout.write(self.style.WARNING(
                    f"      [!!] API HTTP error on batch {batch_num}: "
                    f"{e.response.status_code} {e.response.reason}"
                ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"      [!!] API error on batch {batch_num}: {e}"
                ))

        return total_translated

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

    def _print_summary(self, new_strings_count, empty_count, dry_run=False):
        """Print final summary line."""
        prefix = "(Dry run) " if dry_run else ""

        self.stdout.write("")
        if empty_count:
            self.stdout.write(self.style.WARNING(
                f"{prefix}Summary: {empty_count} strings still need "
                f"French translations."
            ))
            self.stdout.write(
                "  Set TRANSLATE_API_KEY to enable auto-translation."
            )
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{prefix}Summary: All strings have French translations."
            ))
        self.stdout.write("")
