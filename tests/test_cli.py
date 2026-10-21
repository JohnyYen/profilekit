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

#: The registry runs targets in sorted entry-point name order.
TARGET_ORDER = ["cv", "github-readme", "linkedin", "portfolio"]

MINIMAL_PROJECT = "[project]\nconfig_version = 1\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal discoverable project; commands act on this, never on the repo."""
    (tmp_path / "profile.toml").write_text(MINIMAL_PROJECT, encoding="utf-8")
    return tmp_path


class _EntryPoint:
    """Stand-in for an importlib.metadata entry point; records every load."""

    loads: list[str]

    def __init__(self, name: str, value: object, loads: list[str]) -> None:
        self.name = name
        self.value = f"fake_module:{name}"
        self.dist = None
        self._value = value
        self.loads = loads

    def load(self) -> object:
        self.loads.append(self.name)
        if isinstance(self._value, BaseException):
            raise self._value
        return self._value


def _install_generators(monkeypatch, generators: dict[str, object]) -> list[str]:
    """Register *generators* as fake entry points; return the log of loads.

    A value that is an exception is raised on load, like a plugin whose own
    import fails.
    """
    loads: list[str] = []
    entry_points = [_EntryPoint(name, value, loads) for name, value in generators.items()]
    monkeypatch.setattr(
        cli.registry,
        "_entry_points_for",
        lambda group: entry_points if group == cli.registry.GENERATOR_GROUP else [],
    )
    return loads


@pytest.fixture
def spies(monkeypatch, project: Path):
    """Register call-recording generators; return the call log."""
    calls: list[str] = []

    def make_spy(name: str):
        def _spy(ctx):
            calls.append(name)

        return _spy

    _install_generators(monkeypatch, {name: make_spy(name) for name in TARGET_ORDER})
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

    def boom(ctx):
        raise RuntimeError("kaboom")

    _install_generators(monkeypatch, {"cv": boom})
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


# --- broken plugins --------------------------------------------------------


def _with_a_broken_plugin(monkeypatch) -> tuple[list[str], list[str]]:
    calls: list[str] = []
    loads = _install_generators(
        monkeypatch,
        {
            "broken-card": ImportError("No module named 'missing_dependency'"),
            "cv": lambda ctx: calls.append("cv"),
        },
    )
    return calls, loads


def test_list_names_targets_without_importing_them(project, monkeypatch, capsys):
    """`list` reads names from metadata; a broken plugin cannot break it."""
    _calls, loads = _with_a_broken_plugin(monkeypatch)

    rc = _run(project, "list")
    out = capsys.readouterr()

    assert rc == 0, out.err
    assert out.out.split() == ["broken-card", "cv"]
    assert loads == [], "listing must not import any component"


def test_generating_one_target_ignores_an_unrelated_broken_plugin(project, monkeypatch, capsys):
    calls, loads = _with_a_broken_plugin(monkeypatch)

    rc = _run(project, "generate", "cv")
    out = capsys.readouterr()

    assert rc == 0, out.err
    assert calls == ["cv"]
    assert loads == ["cv"], "only the selected target may be imported"


@pytest.mark.parametrize("argv", [("generate", "all"), ("generate", "broken-card")])
def test_a_broken_plugin_fails_the_commands_that_need_it(project, monkeypatch, capsys, argv):
    calls, _loads = _with_a_broken_plugin(monkeypatch)

    rc = _run(project, *argv)
    out = capsys.readouterr()

    assert rc == 1
    assert "component 'broken-card' in group 'profilekit.generators' failed to load" in out.err
    assert "missing_dependency" in out.err
    assert "Traceback" not in out.err + out.out
    assert calls == [], "no generator may run when the set it needs cannot load"
    assert not (project / "output" / "manifest.json").exists()


# --- empty registry ----------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [("generate",), ("generate", "all"), ("generate", "cv"), ("list",)],
    ids=["generate", "generate-all", "generate-one", "list"],
)
def test_empty_generator_registry_fails_loudly(project, monkeypatch, capsys, argv):
    """No registered generators is a broken install, never a silent success.

    With no entry points, `generate all` used to write only the manifest and
    exit 0, and `list` printed nothing and exit 0.
    """
    _install_generators(monkeypatch, {})
    rc = _run(project, *argv)
    out = capsys.readouterr()
    assert rc == 1
    assert "no generators are registered" in out.err
    assert "reinstall profilekit" in out.err
    assert "Traceback" not in out.err + out.out
    assert not (project / "output" / "manifest.json").exists(), "No manifest may be written"


def test_duplicate_generator_names_fail_without_a_traceback(project, monkeypatch, capsys):
    """Two distributions registering one name is reported, not silently shadowed."""

    class _EntryPoint:
        def __init__(self, dist: str) -> None:
            self.name = "cv"
            self.value = f"{dist.replace('-', '_')}:main"
            self.dist = type("_Dist", (), {"name": dist})()

        def load(self):
            raise AssertionError("a duplicate must be rejected before loading")

    monkeypatch.setattr(
        cli.registry,
        "_entry_points_for",
        lambda group: [_EntryPoint("first-dist"), _EntryPoint("second-dist")],
    )

    rc = _run(project, "generate", "all")
    out = capsys.readouterr()
    assert rc == 1
    assert "'cv'" in out.err
    assert "first-dist" in out.err and "second-dist" in out.err
    assert "Traceback" not in out.err + out.out
    assert not (project / "output" / "manifest.json").exists()


# --- no path overrides -------------------------------------------------------


@pytest.mark.parametrize("sub", ["generate", "validate", "check", "list"])
def test_no_path_override_flags(sub, capsys):
    """No subcommand exposes --data-dir/--output-dir in this change."""
    with pytest.raises(SystemExit):
        cli.main([sub, "--help"])
    help_text = capsys.readouterr().out
    assert "--data-dir" not in help_text
    assert "--output-dir" not in help_text


# --- offline flag ------------------------------------------------------------


def test_offline_flag_sets_the_skip_variables(project, monkeypatch, spies):
    """The flag must have an observable effect, not just appear in a hook entry.

    The only assertion covering `--offline` was that the literal string
    appeared in the pre-commit config, which proves nothing about behaviour.
    """
    import os

    monkeypatch.delenv("SKIP_ICON_CHECK", raising=False)
    monkeypatch.delenv("SKIP_LINK_CHECK", raising=False)

    cli.main(["--project", str(project), "--offline", "list"])

    assert os.environ.get("SKIP_ICON_CHECK") == "1"
    assert os.environ.get("SKIP_LINK_CHECK") == "1"


def test_without_the_offline_flag_nothing_is_set(project, monkeypatch, spies):
    """The flag must be the only thing that sets them, or it proves nothing."""
    import os

    monkeypatch.delenv("SKIP_ICON_CHECK", raising=False)
    monkeypatch.delenv("SKIP_LINK_CHECK", raising=False)

    cli.main(["--project", str(project), "list"])

    assert os.environ.get("SKIP_ICON_CHECK") is None
    assert os.environ.get("SKIP_LINK_CHECK") is None
