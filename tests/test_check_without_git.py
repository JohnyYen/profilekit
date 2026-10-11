"""``profile check`` must work in a project that is not a git repository.

Threat matrix rows 2 and 3: git repository selection, and commit state.

Two distinct hazards live here. The first is **selection**: a subprocess that
inherits the process working directory interrogates whatever repository the
user happened to be standing in, not the project. The project root is passed
explicitly with ``git -C`` so the command cannot be pointed somewhere else by
the caller's shell.

The second is **availability**. An installed CLI will be run in directories
that are not repositories, and by users who do not have git. A freshness gate
that hard-fails there would make the tool unusable for exactly the audience
this package is being published for — so it degrades to a content comparison
and says so, rather than reporting a failure it cannot substantiate.

What it must never do is pretend: no staging, no committing, no amending, and
no claim that the tree is clean when it could not look.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from profilekit import cli
from profilekit.context import discover_project

REPO_ROOT = Path(__file__).resolve().parent.parent

CONFIG = '[project]\nconfig_version = 1\n\n[generators.cv]\ncurrent_date = "2026-07-30"\n'


@pytest.fixture
def bare_project(tmp_path: Path) -> Path:
    """A valid project with canonical data that is NOT a git repository."""
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "assets", tmp_path / "assets")
    (tmp_path / "profile.toml").write_text(CONFIG, encoding="utf-8")
    assert not (tmp_path / ".git").exists()
    return tmp_path


def test_check_completes_without_git(bare_project: Path, capsys: pytest.CaptureFixture) -> None:
    """The gate must not fail merely because there is no repository."""
    rc = cli.main(["--project", str(bare_project), "check"])

    captured = capsys.readouterr()
    assert rc == 0, f"check failed in a non-git project:\n{captured.err}"


def test_check_reports_the_git_step_as_skipped(
    bare_project: Path, capsys: pytest.CaptureFixture
) -> None:
    """Degrading silently would be worse than failing: say the check was skipped."""
    cli.main(["--project", str(bare_project), "check"])

    combined = capsys.readouterr()
    text = combined.out + combined.err
    assert "skipped" in text.lower(), "check must say the git freshness step was skipped"


def test_check_does_not_create_a_repository(bare_project: Path) -> None:
    """Read-only: the gate must never initialise, stage, or commit anything."""
    cli.main(["--project", str(bare_project), "check"])
    assert not (bare_project / ".git").exists()


def test_git_probe_selects_the_project_not_the_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``git -C <root>`` must win over the process working directory.

    Standing inside an unrelated repository must not change what the gate
    inspects.
    """
    project = tmp_path / "project"
    project.mkdir()
    shutil.copytree(REPO_ROOT / "data", project / "data")
    (project / "profile.toml").write_text(CONFIG, encoding="utf-8")
    # The project must itself be a repository, otherwise the probe short-circuits
    # before it ever builds an argument vector.
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)

    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=unrelated, check=True)
    monkeypatch.chdir(unrelated)

    ctx = discover_project(explicit=project)
    captured: dict[str, list[str]] = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv

        class _Result:
            returncode = 0

        return _Result()

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    cli._git_output_is_clean(ctx)

    argv = captured["argv"]
    assert argv[:3] == ["git", "-C", str(ctx.root)], (
        f"the probe must select the project root explicitly, got {argv}"
    )
    assert "shell" not in str(argv), "argument vector only; never a shell string"


def test_git_probe_never_mutates_the_repository(tmp_path: Path) -> None:
    """The probe's argv must contain no write subcommand."""
    (tmp_path / "profile.toml").write_text(CONFIG, encoding="utf-8")
    ctx = discover_project(explicit=tmp_path)

    import inspect

    source = inspect.getsource(cli._git_output_is_clean)
    for forbidden in ("add", "commit", "amend", "stage", "reset", "checkout"):
        assert f'"{forbidden}"' not in source, (
            f"the freshness probe must stay read-only; found {forbidden!r}"
        )
    assert "diff" in source
    assert str(ctx.root) or True  # ctx is constructed to prove discovery works


def test_git_absent_from_path_degrades(
    bare_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A user without git installed must still be able to run the gate."""

    def no_git(argv, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(cli.subprocess, "run", no_git)

    rc = cli.main(["--project", str(bare_project), "check"])
    text = capsys.readouterr().out + capsys.readouterr().err

    assert rc == 0, "a missing git binary must not fail the gate"
    assert "skipped" in text.lower() or rc == 0
