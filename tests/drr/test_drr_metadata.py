"""Meta-invariant check for Design Rationale Records (DRRs) and Principles.

Enforces the split promised in tasks/design-rationale/README.md and
tasks/principles/README.md:

- Every file in tasks/design-rationale/ (excluding README and legacy
  foundation-*.md stubs) MUST have an `enforcement:` front-matter block
  with at least one entry. Principles are not prescriptive; DRRs are.
- No DRR may carry `role: principle` in its front-matter (principles
  belong in tasks/principles/).
- No file in tasks/principles/ may carry `drr:` or `enforcement:`
  front-matter keys (principles are non-prescriptive by definition).

This test is the only thing that makes the README's "CI uses this to gate
PRs" sentence true.
"""
from __future__ import annotations

import pathlib
import re

import pytest
import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DRR_DIR = REPO_ROOT / "tasks" / "design-rationale"
PRINCIPLES_DIR = REPO_ROOT / "tasks" / "principles"

# Legacy foundation docs stay in tasks/design-rationale/ until GK approves the
# restructure (see tasks/design-rationale/README.md "Deprecated foundation
# documents"). They are principles, not DRRs, and must not be required to
# carry an enforcement block.
LEGACY_FOUNDATION_PREFIX = "foundation-"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

PERMITTED_ENFORCEMENT_TYPES = {
    "django-system-check",
    "pytest",
    "semgrep",
    "pre-commit-hook",
    "codeowner",
    "llm-review",
    "judgment-only",
}


def _parse_front_matter(path: pathlib.Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return None
    return yaml.safe_load(match.group(1)) or {}


def _drr_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for entry in sorted(DRR_DIR.glob("*.md")):
        if entry.name == "README.md":
            continue
        if entry.name.startswith(LEGACY_FOUNDATION_PREFIX):
            continue
        files.append(entry)
    return files


def _principle_files() -> list[pathlib.Path]:
    if not PRINCIPLES_DIR.exists():
        return []
    return [p for p in sorted(PRINCIPLES_DIR.glob("*.md")) if p.name != "README.md"]


@pytest.mark.parametrize("path", _drr_files(), ids=lambda p: p.name)
def test_drr_has_enforcement_block(path: pathlib.Path) -> None:
    """Every new-format DRR must declare an enforcement block with entries."""
    fm = _parse_front_matter(path)
    if fm is None or "drr" not in fm:
        pytest.skip(f"{path.name} predates the DRR front-matter format")

    enforcement = fm.get("enforcement")
    assert enforcement is not None, (
        f"{path.name} has `drr:` front-matter but is missing the required "
        "`enforcement:` block. Every prescriptive DRR must declare how CI "
        "catches violations."
    )
    assert isinstance(enforcement, list) and enforcement, (
        f"{path.name} has an empty `enforcement:` block. Declare at least "
        "one entry from: " + ", ".join(sorted(PERMITTED_ENFORCEMENT_TYPES))
    )

    for idx, entry in enumerate(enforcement):
        assert isinstance(entry, dict), (
            f"{path.name} enforcement[{idx}] is not a mapping: {entry!r}"
        )
        entry_type = entry.get("type")
        assert entry_type in PERMITTED_ENFORCEMENT_TYPES, (
            f"{path.name} enforcement[{idx}] has unknown type {entry_type!r}. "
            "Permitted types: " + ", ".join(sorted(PERMITTED_ENFORCEMENT_TYPES))
        )
        assert entry.get("description"), (
            f"{path.name} enforcement[{idx}] ({entry_type}) has no description."
        )


@pytest.mark.parametrize("path", _drr_files(), ids=lambda p: p.name)
def test_drr_is_not_role_principle(path: pathlib.Path) -> None:
    """A DRR in tasks/design-rationale/ must not be labelled as a principle."""
    fm = _parse_front_matter(path)
    if fm is None:
        pytest.skip(f"{path.name} has no front-matter")
    assert fm.get("role") != "principle", (
        f"{path.name} is in tasks/design-rationale/ but has role: principle. "
        "Principles belong in tasks/principles/."
    )


@pytest.mark.parametrize("path", _principle_files(), ids=lambda p: p.name)
def test_principle_has_no_prescriptive_keys(path: pathlib.Path) -> None:
    """A principle doc must not carry DRR-only front-matter keys."""
    fm = _parse_front_matter(path)
    if fm is None:
        return
    forbidden = [key for key in ("drr", "enforcement") if key in fm]
    assert not forbidden, (
        f"{path.name} is in tasks/principles/ but carries prescriptive "
        f"front-matter keys: {forbidden}. Move the content to a DRR in "
        "tasks/design-rationale/ or drop the keys."
    )
