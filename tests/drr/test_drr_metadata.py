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

# An enforcement entry may optionally declare `status: implemented` to assert
# that its referenced file (pytest entries) or rule (codeowner paths) exists
# today. Unset or `status: planned` means the enforcement is declared but not
# yet built -- that's expected during the restructure rollout.
PERMITTED_STATUSES = {"implemented", "planned"}


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
        status = entry.get("status")
        if status is not None:
            assert status in PERMITTED_STATUSES, (
                f"{path.name} enforcement[{idx}] has unknown status {status!r}. "
                "Permitted: " + ", ".join(sorted(PERMITTED_STATUSES))
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
    """A principle doc must not carry DRR-only front-matter keys or roles."""
    fm = _parse_front_matter(path)
    if fm is None:
        pytest.skip(f"{path.name} has no front-matter")
    forbidden = [key for key in ("drr", "enforcement") if key in fm]
    assert not forbidden, (
        f"{path.name} is in tasks/principles/ but carries prescriptive "
        f"front-matter keys: {forbidden}. Move the content to a DRR in "
        "tasks/design-rationale/ or drop the keys."
    )
    assert fm.get("role") != "drr", (
        f"{path.name} is in tasks/principles/ but has role: drr. "
        "Prescriptive docs belong in tasks/design-rationale/."
    )


def _enforcement_paths(path: pathlib.Path) -> list[tuple[int, str, str, dict]]:
    """Return (index, kind, spec, entry) for every path/file spec declared
    in this DRR's enforcement block. `kind` is one of:

    - "pytest-file": the `file:` field of a pytest-type entry
    - "codeowner-path": one element of the `paths:` list on a codeowner entry

    Glob patterns (anything containing * or **) are included; the caller
    decides whether to stat them.
    """
    fm = _parse_front_matter(path)
    if fm is None or "drr" not in fm:
        return []
    out: list[tuple[int, str, str, dict]] = []
    for idx, entry in enumerate(fm.get("enforcement") or []):
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "pytest" and entry.get("file"):
            out.append((idx, "pytest-file", entry["file"], entry))
        if entry.get("type") == "codeowner":
            for spec in entry.get("paths") or []:
                out.append((idx, "codeowner-path", spec, entry))
    return out


def _all_enforcement_paths() -> list[tuple[pathlib.Path, int, str, str, dict]]:
    records: list[tuple[pathlib.Path, int, str, str, dict]] = []
    for drr_path in _drr_files():
        for idx, kind, spec, entry in _enforcement_paths(drr_path):
            records.append((drr_path, idx, kind, spec, entry))
    return records


@pytest.mark.parametrize(
    ("drr_path", "idx", "kind", "spec", "entry"),
    _all_enforcement_paths(),
    ids=lambda v: v.name if isinstance(v, pathlib.Path) else str(v),
)
def test_drr_enforcement_paths_exist(
    drr_path: pathlib.Path,
    idx: int,
    kind: str,
    spec: str,
    entry: dict,
) -> None:
    """Every non-glob path named in a DRR enforcement block must resolve.

    Glob patterns (containing * or **) are skipped because they may match
    nothing today and something tomorrow -- that's their purpose. Literal
    paths, in contrast, must always resolve: they are the canonical codefox
    the DRR is anchoring on. Invented paths are the single biggest defect
    this whole restructure was hired to prevent, so this check is the
    tripwire that makes sure they stay gone.

    An entry with `status: implemented` is required to resolve; an entry
    without a status (implicitly planned) is held to the same rule for
    codeowner paths (those files must exist today, because CODEOWNERS is
    a repo convention the enforcement rule applies against immediately),
    but pytest-file entries declared planned are allowed to not exist yet.
    """
    if "*" in spec:
        pytest.skip(f"glob pattern — intentionally not stat'd: {spec}")
    status = entry.get("status") or "planned"
    if kind == "pytest-file" and status == "planned":
        pytest.skip(
            f"{drr_path.name} enforcement[{idx}] is planned — {spec} "
            "not required to exist yet"
        )
    resolved = REPO_ROOT / spec.rstrip("/")
    assert resolved.exists(), (
        f"{drr_path.name} enforcement[{idx}] ({kind}) names a path that "
        f"does not exist: {spec} (resolved to {resolved}). Either create "
        "the file, fix the path, or mark the entry `status: planned`."
    )
