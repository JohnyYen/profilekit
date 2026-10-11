"""Repository hygiene that a published package has to get right.

Two things here, both found by the review gate rather than by the hygiene
sweep that was supposed to catch them.

**File modes.** A spurious executable bit is a signal problem, not a cosmetic
one: it tells readers and tools that a document is a program. On a package
other people install, that signal is wrong in a way that outlives the commit.

**The reference consumer's README.** `apps/portfolio/` is the owner's own
portfolio, kept in the repository as a worked example of consuming the output
contract — not as part of the distributed package. Leaving the
`create-next-app` boilerplate in place tells an adopter nothing and implies
the directory is scaffolding rather than a deliberate reference.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Suffixes that are never executable. A `.md` file with the bit set is wrong
#: regardless of what it contains.
NON_EXECUTABLE_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".css",
    ".svg",
    ".yaml",
    ".yml",
    ".ico",
    ".toml",
    ".lock",
    ".gif",
    ".png",
}

NON_EXECUTABLE_NAMES = {".gitignore", ".gitattributes"}

PORTFOLIO_README = REPO_ROOT / "apps" / "portfolio" / "README.md"


def _tracked_modes() -> list[tuple[str, str]]:
    """Return (mode, path) for every tracked file, or [] outside a checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "-s"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []

    entries = []
    for line in result.stdout.splitlines():
        fields = line.split("\t", 1)
        if len(fields) != 2:
            continue
        entries.append((fields[0].split()[0], fields[1]))
    return entries


def test_there_are_tracked_files_to_check() -> None:
    """Guard the guard: an empty listing would let the mode check pass vacuously.

    Skips with a reason when git cannot answer — an sdist, a tarball, or a
    container that trips git's dubious-ownership check are all legitimate
    places to run the suite, and failing there would say nothing useful.
    """
    tracked = _tracked_modes()
    if not tracked:
        pytest.skip("not a usable git checkout: file modes cannot be inspected")

    # This repository tracks a few hundred files; a listing in the single
    # digits would mean git answered with something unexpected.
    assert len(tracked) > 50, f"git listed only {len(tracked)} tracked files"


def test_no_stray_executable_bits() -> None:
    """No file whose type cannot be executed may be mode 100755."""
    tracked = _tracked_modes()
    if not tracked:
        pytest.skip("not a usable git checkout: file modes cannot be inspected")

    offenders = [
        path
        for mode, path in tracked
        if mode == "100755"
        and (
            Path(path).suffix in NON_EXECUTABLE_SUFFIXES or Path(path).name in NON_EXECUTABLE_NAMES
        )
    ]

    assert not offenders, (
        f"{len(offenders)} tracked files carry an executable bit they cannot use: "
        f"{offenders[:10]}{'…' if len(offenders) > 10 else ''}. "
        "Clear them on disk with `chmod -x <path>` — `git update-index "
        "--chmod=-x` only touches the index and is undone by the next `git add`."
    )


# ---------------------------------------------------------------------------
# The reference consumer explains itself
# ---------------------------------------------------------------------------


def test_portfolio_readme_exists() -> None:
    assert PORTFOLIO_README.is_file()


def test_portfolio_readme_is_not_boilerplate() -> None:
    """create-next-app text tells an adopter nothing about why this exists."""
    text = PORTFOLIO_README.read_text(encoding="utf-8")

    for marker in ("bootstrapped with", "create-next-app", "Learn More"):
        assert marker not in text, f"leftover boilerplate: {marker!r}"


def test_portfolio_readme_states_its_reference_role() -> None:
    lowered = PORTFOLIO_README.read_text(encoding="utf-8").lower()

    assert "reference" in lowered, "the README must say this is a reference implementation"
    assert "not" in lowered and "distribut" in lowered, (
        "the README must say it is not part of the distributed package"
    )


def test_portfolio_readme_points_at_the_data_contract() -> None:
    """An adopter reading this should be sent to the contract, not to the code."""
    text = PORTFOLIO_README.read_text(encoding="utf-8")
    assert "data-contract" in text


# ---------------------------------------------------------------------------
# No developer's home directory in tracked content
# ---------------------------------------------------------------------------

#: An absolute path under a home directory. Matches the path itself, not a
#: document that merely names the pattern — a file describing this very check
#: has to be able to quote what it searches for.
HOME_PATH = re.compile(r"/home/[a-z_][a-z0-9_-]*/[A-Za-z0-9_.-]+/")

#: Files whose subject *is* this check, and which therefore quote the pattern.
PATTERN_DOCS = (
    "openspec/changes/2026-09-09-open-source-release/",
    "tests/test_repo_hygiene.py",
)


def test_no_absolute_home_paths_in_tracked_content() -> None:
    """A published repository must not carry anyone's home directory layout.

    An earlier check in this change ran `git ls-files | rg '/home/...'`, which
    greps *filenames* only and reported clean while two archived reports
    carried the maintainer's full checkout path in their content.
    """
    tracked = _tracked_modes()
    if not tracked:
        pytest.skip("not a usable git checkout: tracked content cannot be inspected")

    offenders: list[str] = []
    for _mode, path in tracked:
        if path.startswith(PATTERN_DOCS):
            continue
        full = REPO_ROOT / path
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if HOME_PATH.search(text):
            offenders.append(path)

    assert not offenders, (
        f"tracked files contain an absolute home path: {offenders}. "
        "Use a repository-relative path instead."
    )
