#!/usr/bin/env python
"""
Validate .po translation files for common errors.

Checks for:
  1. Duplicate msgid entries (would cause compilemessages to fail)
  2. Untranslated entries (msgid exists but msgstr is empty)

Run this before compilemessages to get clear, actionable error messages.
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def find_duplicate_msgids(po_file_path):
    """Find duplicate msgid entries in a .po file."""
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all msgid entries with their line numbers
    msgid_locations = defaultdict(list)

    for i, line in enumerate(content.split('\n'), start=1):
        if line.startswith('msgid "') and line != 'msgid ""':
            # Extract the msgid string
            match = re.match(r'^msgid "(.+)"$', line)
            if match:
                msgid = match.group(1)
                msgid_locations[msgid].append(i)

    # Find duplicates (msgids appearing more than once)
    duplicates = {
        msgid: lines
        for msgid, lines in msgid_locations.items()
        if len(lines) > 1
    }

    return duplicates


def find_untranslated_entries(po_file_path):
    """Find msgid entries that have no translation (empty msgstr)."""
    with open(po_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    untranslated = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip the header block (first msgid "")
        if line == 'msgid ""' and i < 5:
            # Skip past the header's msgstr block
            i += 1
            while i < len(lines) and lines[i].strip().startswith('"'):
                i += 1
            if i < len(lines) and lines[i].strip().startswith('msgstr'):
                i += 1
                while i < len(lines) and lines[i].strip().startswith('"'):
                    i += 1
            continue

        # Found a msgid line
        if line.startswith('msgid "') and line != 'msgid ""':
            msgid_line = i + 1  # 1-indexed
            match = re.match(r'^msgid "(.+)"$', line)
            if match:
                msgid = match.group(1)
                # Read continuation lines
                i += 1
                while i < len(lines) and lines[i].strip().startswith('"'):
                    msgid += lines[i].strip().strip('"')
                    i += 1

                # Now expect msgstr
                if i < len(lines) and lines[i].strip().startswith('msgstr'):
                    msgstr_line = lines[i].strip()
                    msgstr_match = re.match(r'^msgstr "(.*)"$', msgstr_line)
                    msgstr_value = msgstr_match.group(1) if msgstr_match else ''

                    # Read continuation lines for msgstr
                    i += 1
                    while i < len(lines) and lines[i].strip().startswith('"'):
                        msgstr_value += lines[i].strip().strip('"')
                        i += 1

                    if not msgstr_value:
                        untranslated.append((msgid_line, msgid))
                continue

        i += 1

    return untranslated


def check_mo_freshness(po_file):
    """Check that the .mo file exists and is newer than the .po file."""
    mo_file = po_file.with_suffix('.mo')
    if not mo_file.exists():
        return "MISSING", f".mo file not found — run: python manage.py compilemessages"
    if mo_file.stat().st_mtime < po_file.stat().st_mtime:
        return "STALE", f".mo is older than .po — run: python manage.py compilemessages"
    return "OK", None


def main():
    """Check all .po files in locale directories."""
    locale_dir = Path(__file__).parent.parent / 'locale'

    if not locale_dir.exists():
        print("No locale directory found - skipping translation validation")
        return 0

    po_files = list(locale_dir.glob('*/LC_MESSAGES/*.po'))

    if not po_files:
        print("No .po files found - skipping translation validation")
        return 0

    errors_found = False
    warnings_found = False

    for po_file in po_files:
        rel_path = po_file.relative_to(locale_dir.parent)

        # Check 1: Duplicates (errors — will break compilemessages)
        duplicates = find_duplicate_msgids(po_file)

        if duplicates:
            errors_found = True

            print(f"\n{'='*60}")
            print(f"ERROR: Duplicate translations in {rel_path}")
            print(f"{'='*60}")
            print(f"\nFound {len(duplicates)} duplicate msgid entries:\n")

            for msgid, lines in duplicates.items():
                print(f'  "{msgid}"')
                print(f'    appears on lines: {", ".join(map(str, lines))}')
                print()

            print("HOW TO FIX:")
            print("-----------")
            print(f"1. Open {rel_path}")
            print("2. Search for each duplicate msgid listed above")
            print("3. Keep ONE copy (usually the first one) and delete the others")
            print("4. Make sure to delete the entire block (msgid + msgstr lines)")
            print()

        # Check 2: Untranslated entries (warnings — will show English to users)
        untranslated = find_untranslated_entries(po_file)

        if untranslated:
            warnings_found = True

            print(f"\n{'='*60}")
            print(f"WARNING: {len(untranslated)} untranslated string(s) in {rel_path}")
            print(f"{'='*60}\n")

            for line_num, msgid in untranslated:
                print(f'  Line {line_num}: "{msgid}"')

            print(f"\nThese strings will appear in English for French users.")
            print(f"Add French translations in {rel_path} for each msgstr.\n")

        # Check 3: .mo freshness (error — deployed translations would be stale)
        status, message = check_mo_freshness(po_file)
        if status != "OK":
            errors_found = True
            mo_rel = po_file.with_suffix('.mo').relative_to(locale_dir.parent)
            print(f"\n{'='*60}")
            print(f"ERROR: {status} .mo file — {mo_rel}")
            print(f"{'='*60}")
            print(f"\n  {message}\n")

    if errors_found:
        print("Translation validation FAILED - fix duplicates before deploying")
        return 1

    if warnings_found:
        print("Translation validation passed with WARNINGS - untranslated strings found")
        return 0

    print(f"Translation validation passed - checked {len(po_files)} file(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
