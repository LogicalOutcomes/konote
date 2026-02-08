"""
Bidirectional QA ticket sync (QA-T14).

Parses commit messages for QA ticket references (e.g. "QA: BLOCKER-1"
or "Fixes QA: BUG-3, BUG-4") and updates the corresponding issues in
the konote-qa-scenarios repo.

For each ticket ID found:
  - If an issue with that label exists: adds a comment (idempotent).
  - If no issue exists: creates one with the 'fixed-in-web' label.

Requires the 'gh' CLI (pre-installed in GitHub Actions).
Uses only Python stdlib — no pip dependencies.
"""

import json
import os
import re
import subprocess
import sys

QA_REPO = "gilliankerr/konote-qa-scenarios"

# Match ticket IDs after "QA:" — supports BLOCKER-1, BUG-3, IMPROVE-2, FIX-1
TICKET_PATTERN = re.compile(r"\b((?:BLOCKER|BUG|IMPROVE|FIX)-\d+)\b")


def parse_ticket_ids(message: str) -> list[str]:
    """Extract QA ticket IDs from a commit message.

    Looks for 'QA:' anywhere in the message, then extracts all ticket IDs
    that follow it (on the same line or subsequent lines).

    Examples:
        "Fixes QA: BLOCKER-1"          -> ["BLOCKER-1"]
        "QA: BUG-3, BUG-4"             -> ["BUG-3", "BUG-4"]
        "QA: IMPROVE-2 fixed"           -> ["IMPROVE-2"]
        "No QA reference here"          -> []
    """
    # Find the position of "QA:" — only look at text after it
    qa_pos = message.upper().find("QA:")
    if qa_pos == -1:
        return []

    after_qa = message[qa_pos:]
    tickets = TICKET_PATTERN.findall(after_qa)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for ticket in tickets:
        if ticket not in seen:
            seen.add(ticket)
            unique.append(ticket)

    return unique


def gh(args: list[str], token: str) -> subprocess.CompletedProcess:
    """Run a gh CLI command with authentication."""
    env = {**os.environ, "GH_TOKEN": token}
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def find_issue_by_label(ticket_id: str, token: str) -> int | None:
    """Search for an open issue in the QA repo with a matching label.

    Returns the issue number if found, None otherwise.
    """
    result = gh(
        [
            "issue", "list",
            "--repo", QA_REPO,
            "--label", ticket_id,
            "--state", "all",
            "--json", "number",
            "--limit", "1",
        ],
        token,
    )

    if result.returncode != 0:
        print(f"  Warning: gh issue list failed: {result.stderr.strip()}")
        return None

    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    if issues:
        return issues[0]["number"]
    return None


def issue_already_has_comment(issue_number: int, commit_sha: str, token: str) -> bool:
    """Check whether an issue already has a comment mentioning this commit.

    Ensures idempotency — running twice for the same commit won't
    create duplicate comments.
    """
    result = gh(
        [
            "issue", "view",
            str(issue_number),
            "--repo", QA_REPO,
            "--json", "comments",
        ],
        token,
    )

    if result.returncode != 0:
        # If we can't check, err on the side of not duplicating
        print(f"  Warning: couldn't check existing comments: {result.stderr.strip()}")
        return False

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False

    for comment in data.get("comments", []):
        if commit_sha in comment.get("body", ""):
            return True

    return False


def add_comment(issue_number: int, commit_sha: str, commit_url: str, token: str) -> bool:
    """Add a comment to an existing issue noting the fix."""
    body = f"Fixed in konote-web commit {commit_sha}: {commit_url}"
    result = gh(
        [
            "issue", "comment",
            str(issue_number),
            "--repo", QA_REPO,
            "--body", body,
        ],
        token,
    )

    if result.returncode != 0:
        print(f"  Error adding comment: {result.stderr.strip()}")
        return False
    return True


def create_issue(ticket_id: str, commit_sha: str, commit_url: str, token: str) -> bool:
    """Create a new issue in the QA repo for a ticket with no existing issue."""
    title = f"QA: {ticket_id} fixed in konote-web"
    body = f"Fixed in konote-web commit {commit_sha}: {commit_url}"
    result = gh(
        [
            "issue", "create",
            "--repo", QA_REPO,
            "--title", title,
            "--body", body,
            "--label", "fixed-in-web",
            "--label", ticket_id,
        ],
        token,
    )

    if result.returncode != 0:
        print(f"  Error creating issue: {result.stderr.strip()}")
        return False

    # Print the URL of the new issue
    issue_url = result.stdout.strip()
    if issue_url:
        print(f"  Created issue: {issue_url}")
    return True


def main() -> None:
    token = os.environ.get("GH_TOKEN", "")
    commit_message = os.environ.get("COMMIT_MESSAGE", "")
    commit_sha = os.environ.get("COMMIT_SHA", "")
    commit_url = os.environ.get("COMMIT_URL", "")

    if not token:
        print("Warning: GH_TOKEN not set — skipping QA ticket sync.")
        sys.exit(0)

    if not commit_message:
        print("Warning: COMMIT_MESSAGE not set — nothing to parse.")
        sys.exit(0)

    print(f"Commit: {commit_sha[:8]}")
    print(f"Message: {commit_message.splitlines()[0]}")

    ticket_ids = parse_ticket_ids(commit_message)

    if not ticket_ids:
        print("No QA ticket IDs found in commit message.")
        sys.exit(0)

    print(f"Found ticket IDs: {', '.join(ticket_ids)}")
    print()

    errors = 0

    for ticket_id in ticket_ids:
        print(f"Processing {ticket_id}...")

        issue_number = find_issue_by_label(ticket_id, token)

        if issue_number is not None:
            print(f"  Found existing issue #{issue_number}")

            if issue_already_has_comment(issue_number, commit_sha, token):
                print(f"  Comment for {commit_sha[:8]} already exists — skipping.")
                continue

            if add_comment(issue_number, commit_sha, commit_url, token):
                print(f"  Added comment to #{issue_number}")
            else:
                errors += 1
        else:
            print(f"  No existing issue found — creating one.")
            if create_issue(ticket_id, commit_sha, commit_url, token):
                print(f"  Created new issue for {ticket_id}")
            else:
                errors += 1

    print()
    if errors:
        print(f"Completed with {errors} error(s).")
        sys.exit(1)
    else:
        print("All tickets synced successfully.")


if __name__ == "__main__":
    main()
