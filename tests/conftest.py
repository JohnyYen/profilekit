"""Shared pytest fixtures for the profilekit test suite."""

import subprocess
import warnings
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the tests/fixtures/ directory."""
    return FIXTURES_DIR


def make_about(overrides: dict | None = None) -> dict:
    """Return a minimal valid about dict merged with overrides."""
    base = {
        "username": "testuser",
        "tagline": "Test tagline",
        "description": "Test description.",
    }
    if overrides:
        base.update(overrides)
    return base


def make_projects(names: list[str] | None = None) -> list[dict]:
    """Return a list of project dicts with only the name field."""
    if names is None:
        names = []
    return [{"name": n} for n in names]


# ---------------------------------------------------------------------------
# Session guard: the suite must not modify the repository it is testing
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


def _tracked_tree_state() -> str | None:
    """Return git's view of the tracked working tree.

    Returns ``None`` — not an empty string — when git cannot answer. A clean
    tree and an unavailable git both produce empty output, so collapsing them
    would let the guard pass vacuously in exactly the environment where it
    cannot see anything.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    return result.stdout if result.returncode == 0 else None


@pytest.fixture(scope="session", autouse=True)
def _repository_is_not_modified_by_the_suite():
    """Fail the session if running the tests changed a tracked file.

    Tests that write into the repository make every ``git status`` after a run
    ambiguous: real work and test residue become indistinguishable, and
    generated-artifact drift gets laundered into "I ran the tests". Several
    suites here used to do exactly that.

    Warns instead of failing outside a git checkout, so an installed-package
    consumer can still run the tests.
    """
    before = _tracked_tree_state()
    yield
    after = _tracked_tree_state()

    if before is None or after is None:
        warnings.warn(
            "repository-modification guard skipped: git is unavailable",
            RuntimeWarning,
            stacklevel=1,
        )
        return

    if before != after:
        added = sorted(set(after.splitlines()) - set(before.splitlines()))
        raise AssertionError(
            "the test suite modified tracked files; tests must write only to "
            "tmp_path:\n  " + "\n  ".join(added)
        )


@pytest.fixture(autouse=True)
def _suite_runs_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip network reachability probes by default, for every test.

    `profile validate` probes skillicons.dev and every project URL. Those
    probes are a feature, but a test suite that depends on third-party uptime
    is a flake generator: a 403 from someone else's CDN should never turn a
    local commit red.

    Tests that specifically exercise the probes mock `urlopen` and override
    these variables themselves, which works because a test body runs after
    its fixtures.
    """
    monkeypatch.setenv("SKIP_ICON_CHECK", "1")
    monkeypatch.setenv("SKIP_LINK_CHECK", "1")
