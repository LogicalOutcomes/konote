#!/usr/bin/env python
"""
Update translations in one step: extract, validate, compile, and commit.

Runs the full translation workflow so you don't have to remember
the individual commands or their order:

    1. Extract strings from templates/code  (makemessages)
    2. Validate .po files for errors         (validate_translations.py)
    3. Compile .po -> .mo                    (compilemessages)
    4. Verify translations load correctly     (check_translations)
    5. Commit the changes to git             (git add + commit)

Usage:
    python scripts/update_translations.py              # Full workflow
    python scripts/update_translations.py --no-commit  # Skip the git commit
    python scripts/update_translations.py --lang fr    # Target language (default: fr)
    python scripts/update_translations.py --dry-run    # Show what would happen
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd, description, dry_run=False):
    """
    Run a shell command and return (success, output).
    Prints status and output as it goes.
    """
    print(f"\n{'-' * 55}")
    print(f"  Step: {description}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'-' * 55}")

    if dry_run:
        print("  [DRY RUN] Skipped.")
        return True, ""

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = result.stdout.strip()
        errors = result.stderr.strip()

        if output:
            for line in output.split('\n'):
                print(f"  {line}")
        if errors:
            for line in errors.split('\n'):
                print(f"  {line}")

        if result.returncode != 0:
            print(f"\n  FAILED (exit code {result.returncode})")
            return False, output + "\n" + errors

        print(f"  OK")
        return True, output + "\n" + errors

    except subprocess.TimeoutExpired:
        print(f"  FAILED (timed out after 120 seconds)")
        return False, "Command timed out"
    except FileNotFoundError as e:
        print(f"  FAILED (command not found: {e})")
        return False, str(e)


def check_prerequisites():
    """Verify required tools and files exist."""
    issues = []

    # Check manage.py exists
    manage_py = PROJECT_ROOT / "manage.py"
    if not manage_py.exists():
        issues.append("manage.py not found — are you in the project root?")

    # Check locale directory exists
    locale_dir = PROJECT_ROOT / "locale"
    if not locale_dir.exists():
        issues.append("locale/ directory not found — run makemessages first to create it.")

    # Check validate_translations.py exists
    validate_script = PROJECT_ROOT / "scripts" / "validate_translations.py"
    if not validate_script.exists():
        issues.append("scripts/validate_translations.py not found.")

    # Check git is available
    try:
        subprocess.run(
            ["git", "status"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append("git is not available or not a git repository.")

    return issues


def check_for_changes():
    """Check if there are translation file changes to commit."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "locale/"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(
        description="Update translations: extract, validate, compile, and commit."
    )
    parser.add_argument(
        "--lang", default="fr",
        help="Target language code (default: fr)."
    )
    parser.add_argument(
        "--no-commit", action="store_true",
        help="Skip the git commit step."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what commands would run without executing them."
    )
    parser.add_argument(
        "--skip-extract", action="store_true",
        help="Skip makemessages (useful if you only changed .po manually)."
    )
    args = parser.parse_args()

    print(f"\nKoNote Translation Update")
    print(f"{'=' * 55}")
    print(f"  Language:   {args.lang}")
    print(f"  Commit:     {'no' if args.no_commit else 'yes'}")
    print(f"  Dry run:    {'yes' if args.dry_run else 'no'}")

    # Check prerequisites
    issues = check_prerequisites()
    if issues:
        print(f"\n  Prerequisites check FAILED:")
        for issue in issues:
            print(f"    - {issue}")
        return 1

    print(f"\n  Prerequisites: OK")

    steps_completed = 0
    total_steps = 5 if not args.no_commit else 4
    if args.skip_extract:
        total_steps -= 1

    # Step 1: Extract strings (makemessages)
    if not args.skip_extract:
        ok, _ = run_command(
            ["python", "manage.py", "makemessages", "-l", args.lang, "--no-location"],
            f"Extract translatable strings (makemessages -l {args.lang})",
            dry_run=args.dry_run,
        )
        if not ok:
            print(f"\n  String extraction failed. Fix the errors above and try again.")
            return 1
        steps_completed += 1

    # Step 2: Validate .po files
    ok, _ = run_command(
        ["python", "scripts/validate_translations.py"],
        "Validate .po files (check for duplicates)",
        dry_run=args.dry_run,
    )
    if not ok:
        print(f"\n  Validation failed. Fix the duplicate entries listed above, then re-run.")
        return 1
    steps_completed += 1

    # Step 3: Compile .mo files
    ok, _ = run_command(
        ["python", "manage.py", "compilemessages"],
        "Compile translations (.po -> .mo)",
        dry_run=args.dry_run,
    )
    if not ok:
        print(f"\n  Compilation failed. Check the .po file for syntax errors.")
        return 1
    steps_completed += 1

    # Step 4: Verify translations load correctly
    ok, _ = run_command(
        ["python", "manage.py", "check_translations", "--lang", args.lang],
        f"Verify {args.lang} translations load correctly",
        dry_run=args.dry_run,
    )
    if not ok:
        print(f"\n  Translation check failed. The .mo file may be corrupted.")
        print(f"  Try running compilemessages again.")
        return 1
    steps_completed += 1

    # Step 5: Git commit
    if not args.no_commit:
        if args.dry_run:
            print(f"\n{'-' * 55}")
            print(f"  Step: Commit translation files to git")
            print(f"  [DRY RUN] Would commit locale/ changes.")
            print(f"{'-' * 55}")
            steps_completed += 1
        else:
            if not check_for_changes():
                print(f"\n  No translation file changes to commit.")
                steps_completed += 1
            else:
                # Stage locale files
                ok, _ = run_command(
                    ["git", "add", "locale/"],
                    "Stage translation files",
                )
                if not ok:
                    print(f"\n  Failed to stage files.")
                    return 1

                # Commit
                ok, _ = run_command(
                    ["git", "commit", "-m",
                     f"Update {args.lang} translations\n\n"
                     f"Extracted, validated, and compiled translation files.\n\n"
                     f"Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"],
                    "Commit translation files",
                )
                if not ok:
                    print(f"\n  Git commit failed. Check the output above.")
                    return 1
                steps_completed += 1

    # Done!
    print(f"\n{'=' * 55}")
    print(f"  DONE: {steps_completed}/{total_steps} steps completed successfully.")
    print(f"{'=' * 55}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
