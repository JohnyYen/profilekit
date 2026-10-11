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

import subprocess
from pathlib import Path

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
    """Guard the guard: an empty listing would pass while proving nothing."""
    assert len(_tracked_modes()) > 50


def test_no_stray_executable_bits() -> None:
    """No file whose type cannot be executed may be mode 100755."""
    offenders = [
        path
        for mode, path in _tracked_modes()
        if mode == "100755"
        and (Path(path).suffix in NON_EXECUTABLE_SUFFIXES or Path(path).name in NON_EXECUTABLE_NAMES)
    ]

    assert not offenders, (
        f"{len(offenders)} tracked files carry an executable bit they cannot use: "
        f"{offenders[:10]}{'…' if len(offenders) > 10 else ''}. "
        "Clear them with `git update-index --chmod=-x <path>`."
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
