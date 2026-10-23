"""End-to-end generation through the CLI, without touching the real tree.

This file used to test ``profilekit.generate_all``, a convenience runner that
kept its own list of generators alongside the one in ``cli.py``. The two
diverged in production, so the module is gone and the registry is the single
enumeration source. What remains worth testing is the property the old module
was standing in for: the whole pipeline runs, writes every artifact, and
writes nothing anywhere else.

The previous version ran from the repository root, so running the suite
rewrote the committed ``output/`` and the portfolio's ``app/data/``. These
drive a throwaway copy of the fixture project and assert the real tree is
untouched afterwards. ``conftest`` enforces the same property for the whole
session.
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "project"

EXPECTED_ARTIFACTS = [
    "cv.md",
    "cv.yml",
    "github-readme.md",
    "linkedin.md",
    "manifest.json",
    "portfolio.md",
]

#: Directories the suite must never write into.
PROTECTED = (
    REPO_ROOT / "output",
    REPO_ROOT / "apps" / "portfolio" / "app" / "data",
)


def _tree_digest(root: Path) -> str | None:
    """A content digest of every file under *root*, stable across runs.

    ``None`` means *root* does not exist. Recording absence instead of
    skipping the directory keeps the guard meaningful in a checkout where a
    protected directory has not been created yet: a write that creates it
    changes ``None`` into a digest and is reported as drift.
    """
    if not root.exists():
        return None
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A writable copy of the fictional fixture project."""
    target = tmp_path / "project"
    shutil.copytree(FIXTURE_PROJECT, target)
    return target


@pytest.fixture
def protected_digests() -> dict[Path, str | None]:
    """Snapshot the directories that must survive the test unchanged.

    Every protected directory is snapshotted, present or not, so none of
    them can drop out of the comparison.
    """
    return {path: _tree_digest(path) for path in PROTECTED}


def _file_digests(root: Path, *, exclude: Path) -> dict[Path, str]:
    """Map every file under *root*, outside *exclude*, to its content digest."""
    return {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and exclude not in path.parents
    }


def _run(argv: list[str], project: Path) -> subprocess.CompletedProcess:
    """Run *argv* against *project*, selected by environment, never by cwd.

    ``cwd`` is the project too, so a bug that reads the working directory
    instead of the configured project still lands inside the sandbox rather
    than in the repository.
    """
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        cwd=str(project),
        env={
            "PATH": "/usr/bin:/bin",
            "PROFILEKIT_PROJECT": str(project),
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "SKIP_ICON_CHECK": "1",
            "SKIP_LINK_CHECK": "1",
        },
    )


def _generate(project: Path) -> subprocess.CompletedProcess:
    return _run([sys.executable, "-m", "profilekit.cli", "generate"], project)


def test_generate_all_exits_zero(project: Path) -> None:
    result = _generate(project)
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_generate_all_writes_every_artifact(project: Path) -> None:
    result = _generate(project)
    assert result.returncode == 0, result.stderr

    produced = sorted(p.name for p in (project / "output").glob("*"))
    assert produced == EXPECTED_ARTIFACTS


def test_generation_writes_nothing_outside_the_output_directory(project: Path) -> None:
    """Generation must not write a published destination — that is `publish`.

    Every file outside ``output/`` is compared by content, whatever its
    extension: a generator that wrote a published ``.json`` file, or
    rewrote an input in place, escapes the boundary just as much as one that
    wrote Markdown.
    """
    output_dir = project / "output"
    before = _file_digests(project, exclude=output_dir)
    assert before, "the fixture project has no inputs — the comparison proves nothing"

    result = _generate(project)
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    after = _file_digests(project, exclude=output_dir)
    created = sorted(str(p.relative_to(project)) for p in after.keys() - before.keys())
    changed = sorted(
        str(p.relative_to(project)) for p in before.keys() & after.keys() if before[p] != after[p]
    )
    assert not created, f"generation wrote files outside output/: {created}"
    assert not changed, f"generation modified files outside output/: {changed}"


def test_the_real_tree_is_untouched(
    project: Path, protected_digests: dict[Path, str | None]
) -> None:
    """The guard the previous version of this file needed and lacked."""
    result = _generate(project)
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    drifted = [
        str(path.relative_to(REPO_ROOT))
        for path, before in protected_digests.items()
        if _tree_digest(path) != before
    ]
    assert not drifted, f"running the suite modified the repository: {drifted}"


def test_the_deleted_convenience_runner_is_gone(project: Path) -> None:
    """``generate_all`` held the second list that caused the divergence bug."""
    result = _run([sys.executable, "-m", "profilekit.generate_all"], project)
    assert result.returncode != 0, "profilekit.generate_all must no longer exist"
