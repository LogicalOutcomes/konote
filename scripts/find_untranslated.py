#!/usr/bin/env python
"""
Find untranslated strings in Django templates.

Scans HTML templates for visible English text that is not wrapped in
{% trans %} or {% blocktrans %} tags. Outputs a report of suspected
untranslated strings with file paths and line numbers.

Usage:
    python scripts/find_untranslated.py                  # Scan all templates
    python scripts/find_untranslated.py --summary        # Counts only
    python scripts/find_untranslated.py --verbose        # Include low-confidence matches
    python scripts/find_untranslated.py --fix-hints      # Show suggested {% trans %} wrapping
"""

import argparse
import re
import sys
from pathlib import Path


# --- Configuration ---

# Minimum length for a string to be flagged (shorter = more noise)
MIN_LENGTH = 3

# Strings that are OK to leave untranslated (brand names, technical terms, etc.)
ALLOWLIST = {
    # Brand / product names
    "KoNote", "Microsoft", "Azure", "GitHub", "Google",
    "Pico", "Chart.js", "HTMX", "Django", "MSYS2",
    # Language names (always shown in their own language)
    "English", "Français",
    # Bilingual hero text (shown before language is chosen on login page)
    "Participant Outcome Management",
    "Gestion des résultats des participants",
    # Technical / form tokens
    "csrf_token", "POST", "GET", "HTML", "CSS", "PDF", "CSV",
    "AM", "PM",
    # Keyboard shortcuts (displayed as-is in all languages)
    "Esc", "Ctrl+S", "g h",
    # Common HTML/template artifacts
    "&rarr;", "&larr;", "&mdash;", "&ndash;", "&nbsp;", "&bull;",
    "&times;", "&hellip;", "&copy;",
}

# Regex fragments that indicate the text is already translated or dynamic
SKIP_PATTERNS = [
    r'^\s*$',                        # Whitespace only
    r'^[\d\s\.\,\:\;\-\+\=\#\%]+$', # Numbers / punctuation only
    r'^\{\{.*\}\}$',                 # Pure template variable
    r'^\{%.*%\}$',                   # Pure template tag
    r'^https?://',                    # URLs
    r'^/[\w/\-\.]+$',                # URL paths
    r'^\w+://',                      # Protocol URLs
    r'^[\*\+\-/\?\!]\s*$',           # Markdown list markers and symbols
    r'^[A-Z_]+$',                    # ALL_CAPS constants
    r'^\d+px$',                      # CSS values
    r'^#[0-9a-fA-F]+$',             # Hex colours
    r'^var\(--',                      # CSS variables
    r'^aria-',                        # ARIA attribute names
    r'^(Ctrl|Alt|Shift|Cmd)\s*[\+\s]', # Keyboard shortcuts
    r'^python\s+manage\.py',           # Django management commands
    r'^hx-',                          # HTMX attribute names
    r'^\u2014\s*\w+$',                   # Em-dash attributions (— Dana)
    r'^\d*,',                           # CSV data rows
    r'^(apt|brew|pip)\s+install\b',      # Package-manager commands
]


def strip_template_tags(line):
    """Remove Django template tags and variables from a line."""
    # Remove {# comments #}
    line = re.sub(r'\{#.*?#\}', '', line)
    # Remove inline {% blocktrans %}...{% endblocktrans %} (content is translated)
    line = re.sub(
        r'\{%\s*blocktrans.*?%\}.*?\{%\s*endblocktrans\s*%\}', '', line
    )
    # Remove inline {% trans "..." %} blocks entirely (already translated)
    line = re.sub(r'\{%\s*trans\s+.*?%\}', '', line)
    # Remove remaining {% template tags %}
    line = re.sub(r'\{%.*?%\}', '', line)
    # Remove {{ variables }}
    line = re.sub(r'\{\{.*?\}\}', '', line)
    return line


def strip_html_tags(line):
    """Remove HTML tags, keeping inner text. Handles unclosed tags on the line."""
    # Remove complete tags
    line = re.sub(r'<[^>]+>', ' ', line)
    # Remove unclosed tags (tag starts but no > on this line — multi-line HTML)
    line = re.sub(r'<\w[^>]*$', ' ', line)
    # Remove orphan closing fragments (continuation of a multi-line tag)
    line = re.sub(r'^[^<]*?>', ' ', line)
    return line


def strip_html_entities(line):
    """Remove HTML entities like &amp; &rarr; &#9888; etc."""
    return re.sub(r'&[#\w]+;', ' ', line)


def is_inside_trans_block(lines, line_idx):
    """
    Check if the given line is inside a {% blocktrans %} ... {% endblocktrans %} block.
    Simple heuristic: scan backwards for an unclosed blocktrans.
    """
    depth = 0
    for i in range(line_idx, -1, -1):
        if '{% endblocktrans %}' in lines[i] or '{%endblocktrans%}' in lines[i]:
            depth -= 1
        if '{% blocktrans' in lines[i] or '{%blocktrans' in lines[i]:
            depth += 1
            if depth > 0:
                return True
    return False


def is_inside_comment_block(lines, line_idx):
    """Check if line is inside {% comment %} ... {% endcomment %}."""
    depth = 0
    for i in range(line_idx, -1, -1):
        if '{% endcomment %}' in lines[i]:
            depth -= 1
        if '{% comment' in lines[i]:
            depth += 1
            if depth > 0:
                return True
    return False


def is_inside_non_text_block(lines, line_idx):
    """
    Check if line is inside a <style>, <script>, <pre>, <!-- -->, or
    {% block styles %} block.  These contain CSS/JS/code/comments,
    not translatable text.
    """
    in_style = False
    in_script = False
    in_html_comment = False
    in_pre = False
    in_block_styles = False

    for i in range(0, line_idx + 1):
        line = lines[i]
        line_lower = line.lower()

        # Track HTML comments (multi-line)
        if '<!--' in line and '-->' not in line:
            in_html_comment = True
        if '-->' in line:
            in_html_comment = False

        # Track <style> blocks
        if '<style' in line_lower:
            in_style = True
        if '</style>' in line_lower:
            in_style = False

        # Track <script> blocks
        if '<script' in line_lower:
            in_script = True
        if '</script>' in line_lower:
            in_script = False

        # Track <pre> blocks (code examples, not translatable)
        if '<pre' in line_lower:
            in_pre = True
        if '</pre>' in line_lower:
            in_pre = False

        # Track {% block styles %} ... {% endblock %} (CSS injected
        # into a parent <style> tag via template inheritance)
        if re.search(r'\{%\s*block\s+styles\b', line):
            in_block_styles = True
        if in_block_styles and re.search(r'\{%\s*endblock\b', line):
            in_block_styles = False

    return in_style or in_script or in_html_comment or in_pre or in_block_styles


def should_skip(text):
    """Return True if this text fragment should not be flagged."""
    text = text.strip()

    if len(text) < MIN_LENGTH:
        return True

    if text in ALLOWLIST:
        return True

    for pattern in SKIP_PATTERNS:
        if re.match(pattern, text):
            return True

    return False


def is_inside_html_tag(lines, line_idx):
    """
    Check if line is a continuation of a multi-line HTML tag.
    e.g. <button type="button"
                  class="outline"     <-- inside an HTML tag
                  id="foo">           <-- ends the tag
    """
    in_tag = False
    for i in range(0, line_idx):
        line = lines[i]
        j = 0
        while j < len(line):
            ch = line[j]
            if ch == '<' and not in_tag:
                in_tag = True
            elif ch == '>' and in_tag:
                in_tag = False
            elif ch == '{' and j + 1 < len(line) and line[j + 1] in ('%', '{'):
                close = '%}' if line[j + 1] == '%' else '}}'
                end = line.find(close, j + 2)
                if end != -1:
                    j = end + len(close)
                    continue
            j += 1
    return in_tag


def has_i18n_load(lines):
    """Check if the template loads the i18n template tag library."""
    for line in lines:
        if re.search(r'\{%\s*load\s+.*\bi18n\b', line):
            return True
    return False


def extract_text_fragments(line):
    """
    Extract visible text fragments from a template line after stripping
    template tags and HTML. Returns a list of non-empty strings.
    """
    cleaned = strip_template_tags(line)
    cleaned = strip_html_tags(cleaned)
    cleaned = strip_html_entities(cleaned)
    # Split on whitespace and rejoin to normalize, then split on
    # boundaries where text might be separate phrases
    fragments = re.split(r'\s{2,}', cleaned)
    return [f.strip() for f in fragments if f.strip()]


def scan_template(filepath, verbose=False):
    """
    Scan a single template file for untranslated strings.
    Returns a list of (line_number, text, confidence) tuples.
    """
    findings = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (UnicodeDecodeError, OSError):
        return findings

    raw_lines = [l.rstrip('\n') for l in lines]

    for idx, line in enumerate(raw_lines):
        line_num = idx + 1

        # Skip lines inside <style>, <script>, or multi-line HTML comments
        if is_inside_non_text_block(raw_lines, idx):
            continue

        # Skip lines that are continuations of multi-line HTML tags
        if is_inside_html_tag(raw_lines, idx):
            continue

        # Skip single-line HTML comments
        if '<!--' in line and '-->' in line:
            line = re.sub(r'<!--.*?-->', '', line)
        elif '<!--' in line:
            continue

        # Skip lines inside blocktrans blocks
        if is_inside_trans_block(raw_lines, idx):
            continue

        # Skip lines inside comment blocks
        if is_inside_comment_block(raw_lines, idx):
            continue

        # Skip lines that are purely template logic
        stripped = line.strip()
        if stripped.startswith('{%') and stripped.endswith('%}'):
            continue
        if stripped.startswith('{{') and stripped.endswith('}}'):
            continue

        fragments = extract_text_fragments(line)

        for text in fragments:
            if should_skip(text):
                continue

            # Determine confidence
            # High: looks like a proper English phrase (2+ words, has letters)
            word_count = len(text.split())
            has_letters = bool(re.search(r'[a-zA-Z]', text))

            if not has_letters:
                continue

            if word_count >= 2:
                confidence = "HIGH"
            elif len(text) >= 5 and text[0].isupper():
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

            if not verbose and confidence == "LOW":
                continue

            findings.append((line_num, text, confidence))

    return findings


def generate_trans_hint(text):
    """Generate a suggested {% trans %} wrapping for the text."""
    # Escape any quotes in the text
    escaped = text.replace('"', '\\"')
    return f'{{% trans "{escaped}" %}}'


def main():
    parser = argparse.ArgumentParser(
        description="Find untranslated strings in Django templates."
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Show counts per file instead of individual strings."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Include low-confidence matches (single short words, etc.)."
    )
    parser.add_argument(
        "--fix-hints", action="store_true",
        help="Show suggested {% trans %} wrapping for each finding."
    )
    parser.add_argument(
        "--path", default=None,
        help="Scan a specific template file or directory."
    )
    args = parser.parse_args()

    # Find the templates directory
    project_root = Path(__file__).parent.parent.resolve()
    if args.path:
        scan_path = Path(args.path).resolve()
        if scan_path.is_file():
            template_files = [scan_path]
        else:
            template_files = sorted(scan_path.rglob('*.html'))
    else:
        templates_dir = project_root / 'templates'
        if not templates_dir.exists():
            print("ERROR: templates/ directory not found.")
            return 1
        template_files = sorted(templates_dir.rglob('*.html'))

    if not template_files:
        print("No template files found.")
        return 0

    total_findings = 0
    files_with_findings = 0
    files_missing_i18n_load = []

    print(f"\nScanning {len(template_files)} template(s) for untranslated strings...")
    print("=" * 65)

    for filepath in template_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (UnicodeDecodeError, OSError):
            continue

        # Check if template loads i18n
        if not has_i18n_load(lines):
            # Check if it extends a base that might load i18n
            has_extends = any(re.search(r'\{%\s*extends\b', l) for l in lines)
            has_text = False
            for l in lines:
                frags = extract_text_fragments(l.rstrip('\n'))
                for t in frags:
                    if not should_skip(t) and re.search(r'[a-zA-Z]', t):
                        has_text = True
                        break
                if has_text:
                    break
            if has_text and not has_extends:
                files_missing_i18n_load.append(filepath)

        findings = scan_template(filepath, verbose=args.verbose)

        if not findings:
            continue

        files_with_findings += 1
        total_findings += len(findings)

        rel_path = filepath.relative_to(project_root)

        if args.summary:
            high = sum(1 for _, _, c in findings if c == "HIGH")
            med = sum(1 for _, _, c in findings if c == "MEDIUM")
            low = sum(1 for _, _, c in findings if c == "LOW")
            parts = []
            if high:
                parts.append(f"{high} high")
            if med:
                parts.append(f"{med} medium")
            if low:
                parts.append(f"{low} low")
            print(f"  {rel_path}: {', '.join(parts)}")
        else:
            print(f"\n  {rel_path}")
            print(f"  {'-' * len(str(rel_path))}")
            for line_num, text, confidence in findings:
                marker = {"HIGH": "!!!", "MEDIUM": " ! ", "LOW": " . "}[confidence]
                print(f"    {marker} Line {line_num}: \"{text}\"")
                if args.fix_hints:
                    hint = generate_trans_hint(text)
                    print(f"         -> {hint}")

    # Summary
    print(f"\n{'=' * 65}")
    print(f"  Files scanned:  {len(template_files)}")
    print(f"  Files flagged:  {files_with_findings}")
    print(f"  Strings found:  {total_findings}")

    if files_missing_i18n_load:
        print(f"\n  Templates missing {{% load i18n %}} (and not extending another template):")
        for fp in files_missing_i18n_load:
            print(f"    - {fp.relative_to(project_root)}")

    if total_findings > 0:
        print(f"\n  TIP: Use --fix-hints to see suggested {{% trans %}} wrappings.")
        print(f"  TIP: Use --verbose to include low-confidence matches.\n")
        return 1

    print(f"\n  No untranslated strings detected.\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
