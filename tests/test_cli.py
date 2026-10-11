"""Tests for the unified CLI (profilekit.cli).

All tests are side-effect free: the generator registry, validate.main, and the
git-diff helper are monkeypatched so no output files are written and git is
never invoked.

Every command resolves a project first, so these drive the CLI against a
throwaway project declared in a temporary directory via ``--project``.
"""

from pathlib import Path

import pytest

import profilekit.cli as cli

TARGET_ORDER = ["github-readme", "linkedin", "portfolio", "cv"]

MINIMAL_PROJECT = "[project]\nconfig_version = 1\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal discoverable project; commands act on this, never on the repo."""
    (tmp_path / "profile.toml").write_text(MINIMAL_PROJECT, encoding="utf-8")
    return tmp_path


@pytest.fixture
def spies(monkeypatch, project: Path):
    """Replace cli.GENERATORS with call-recording spies; return the call log."""
    calls: list[str] = []

    def make_spy(name: str):
        def _spy(ctx):
            calls.append(name)

        return _spy

    registry = {name: make_spy(name) for name in TARGET_ORDER}
    monkeypatch.setattr(cli, "GENERATORS", registry)
    return calls


def _run(project: Path, *argv: str) -> int:
    """Invoke the CLI against *project* rather than the current directory."""
    return cli.main(["--project", str(project), *argv])


# --- no subcommand -----------------------------------------------------------


def test_no_subcommand_returns_nonzero(capsys):
    """Invoking the CLI with no subcommand prints usage and exits non-zero."""
    rc = cli.main([])
    assert rc != 0, "No subcommand should be a non-zero exit"
    err = capsys.readouterr().err + capsys.readouterr().out
    assert "usage" in err.lower(), "Usage help should be printed when no subcommand is given"


# --- generate ----------------------------------------------------------------


def test_generate_default_runs_all_in_order(spies, project):
    """`generate` with no target runs every generator once, in generate_all order."""
    rc = _run(project, "generate")
    assert rc == 0
    assert spies == TARGET_ORDER, f"Expected order {TARGET_ORDER} but got {spies}"


def test_generate_all_explicit_runs_all_in_order(spies, project):
    """`generate all` behaves identically to `generate`."""
    rc = _run(project, "generate", "all")
    assert rc == 0
    assert spies == TARGET_ORDER


def test_generate_single_target_runs_only_that_one(spies, project):
    """`generate cv` runs only the cv generator."""
    rc = _run(project, "generate", "cv")
    assert rc == 0
    assert spies == ["cv"], f"Only cv should run, got {spies}"


def test_generate_unknown_target_errors(spies, project, capsys):
    """An unknown target exits non-zero and names the offending target."""
    rc = _run(project, "generate", "bogus")
    assert rc != 0
    combined = capsys.readouterr()
    assert "bogus" in (combined.err + combined.out), "Error output should name the invalid target"
    assert spies == [], "No generator should run for an unknown target"


def test_generate_failure_propagates(project, monkeypatch, capsys):
    """If a generator raises, generate exits non-zero and names the failing target."""

    def boom():
        raise RuntimeError("kaboom")

    monkeypatch.setattr(cli, "GENERATORS", {"cv": boom})
    rc = _run(project, "generate", "cv")
    assert rc != 0
    out = capsys.readouterr()
    assert "cv" in (out.err + out.out), "Failure output should identify the failing target"


# --- validate ----------------------------------------------------------------


@pytest.mark.parametrize("code", [0, 1])
def test_validate_propagates_exit_code(project, monkeypatch, code):
    """`validate` returns whatever profilekit.validate.main() returns."""
    monkeypatch.setattr(cli.validate, "main", lambda ctx: code)
    assert _run(project, "validate") == code


# --- check -------------------------------------------------------------------


def test_check_passes_when_valid_and_clean(spies, project, monkeypatch):
    """check returns 0 when validation passes, generation runs, and git is clean."""
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    rc = _run(project, "check")
    assert rc == 0
    assert spies == TARGET_ORDER, "check should regenerate all outputs before diffing"


def test_check_fails_on_output_drift(spies, project, monkeypatch):
    """check returns non-zero when the output tree has drifted."""
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: False)
    assert _run(project, "check") != 0


def test_check_fails_early_on_invalid_data(spies, project, monkeypatch):
    """check short-circuits on validation failure without regenerating."""
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 1)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    rc = _run(project, "check")
    assert rc != 0
    assert spies == [], "Generators must not run when validation fails"


# --- list --------------------------------------------------------------------


def test_list_prints_all_targets(spies, project, capsys):
    """`list` prints every target name and exits zero."""
    rc = _run(project, "list")
    assert rc == 0
    out = capsys.readouterr().out
    for name in TARGET_ORDER:
        assert name in out, f"{name} should appear in list output"


# --- no path overrides -------------------------------------------------------


@pytest.mark.parametrize("sub", ["generate", "validate", "check", "list"])
def test_no_path_override_flags(sub, capsys):
    """No subcommand exposes --data-dir/--output-dir in this change."""
    with pytest.raises(SystemExit):
        cli.main([sub, "--help"])
    help_text = capsys.readouterr().out
    assert "--data-dir" not in help_text
    assert "--output-dir" not in help_text
