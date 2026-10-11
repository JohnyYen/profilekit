"""``generate_all`` in both invocation modes, without touching the real tree.

The previous version of this file ran the pipeline from the repository root,
which meant running the test suite rewrote the committed ``output/`` and the
portfolio's ``app/data/``. A suite that mutates the repository it is testing
makes every `git status` after a test run ambiguous, and quietly launders
generated-artifact drift into "I ran the tests".

So these drive a throwaway copy of the fixture project and assert the real
tree is untouched afterwards.
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "project"

#: Directories the suite must never write into.
PROTECTED = (
    REPO_ROOT / "output",
    REPO_ROOT / "apps" / "portfolio" / "app" / "data",
)


def _tree_digest(root: Path) -> str:
    """A content digest of every file under *root*, stable across runs."""
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
def protected_digests() -> dict[Path, str]:
    """Snapshot the directories that must survive the test unchanged."""
    return {path: _tree_digest(path) for path in PROTECTED if path.exists()}


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


def test_module_invocation_exits_zero(project: Path) -> None:
    """``python -m profilekit.generate_all`` must succeed."""
    result = _run([sys.executable, "-m", "profilekit.generate_all"], project)
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_script_invocation_exits_zero(project: Path) -> None:
    """Direct script execution must still work, via the sys.path bootstrap."""
    script = REPO_ROOT / "src" / "profilekit" / "generate_all.py"
    result = _run([sys.executable, str(script)], project)
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_generate_all_writes_every_artifact(project: Path) -> None:
    result = _run([sys.executable, "-m", "profilekit.generate_all"], project)
    assert result.returncode == 0, result.stderr

    produced = sorted(p.name for p in (project / "output").glob("*"))
    assert produced == ["cv.md", "cv.yml", "github-readme.md", "linkedin.md", "portfolio.md"]


def test_generate_all_does_not_publish(project: Path) -> None:
    """Generation must not write a published destination — that is `publish`."""
    _run([sys.executable, "-m", "profilekit.generate_all"], project)

    escaped = [
        p
        for p in (project).rglob("*")
        if p.is_file() and (project / "output") not in p.parents and p.suffix in {".md", ".yml"}
    ]
    assert not escaped, f"generation wrote artifacts outside output/: {escaped}"


def test_the_real_tree_is_untouched(project: Path, protected_digests: dict[Path, str]) -> None:
    """The guard that the previous version of this file needed and lacked."""
    _run([sys.executable, "-m", "profilekit.generate_all"], project)

    drifted = [
        str(path.relative_to(REPO_ROOT))
        for path, before in protected_digests.items()
        if _tree_digest(path) != before
    ]
    assert not drifted, f"running the suite modified the repository: {drifted}"
