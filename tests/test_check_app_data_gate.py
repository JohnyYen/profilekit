"""``profile check`` must gate published destinations, not only ``output/``.

This gate exists because of a specific regression risk. Reclassifying the
portfolio data sync as a publisher removes it from the generate path, and the
CI freshness gate only diffs ``output/``. Without this check, drift in a
published destination would become *less* protected after the refactor than
before it — the destination would simply stop being looked at by anything.

So ``check`` runs every filesystem destination's ``plan()`` — a dry run, which
writes nothing — and fails when a destination does not match canonical data.

These tests drive the real CLI over a real project rather than monkeypatching
private helpers: ``profile --project <dir> check``. That is only possible
because the project is now discovered from the caller instead of from
``__file__``.
"""

import json
import shutil
from pathlib import Path

import pytest

from profilekit import cli
from profilekit.context import ProjectContext
from profilekit.publishers.filesystem import FilesystemPublisher

REPO_ROOT = Path(__file__).resolve().parent.parent

PROJECT_CONFIG = """\
[project]
config_version = 1

[publishers.portfolio-data]
kind = "filesystem"
destination = "app/data"
"""


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real project declaring a filesystem destination, with canonical data."""
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    (tmp_path / "profile.toml").write_text(PROJECT_CONFIG, encoding="utf-8")

    # Validation and generation are exercised by their own suites; this gate is
    # about destinations, so hold those two steps constant.
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)
    return tmp_path


def _publish_destination(sandbox: Path) -> Path:
    """Bring the declared destination up to date, the way `profile publish` will."""
    publisher = FilesystemPublisher()
    ctx = ProjectContext.for_root(sandbox)
    plan = publisher.plan(ctx, {"destination": "app/data"})
    publisher.publish(ctx, plan)
    return plan.resolved_path


def _check(sandbox: Path) -> int:
    return cli.main(["--project", str(sandbox), "check"])


def test_check_passes_when_published_destination_is_current(sandbox: Path) -> None:
    _publish_destination(sandbox)
    assert _check(sandbox) == 0


def test_check_detects_app_data_drift(sandbox: Path, capsys: pytest.CaptureFixture) -> None:
    """A stale destination must fail the gate and name what drifted."""
    destination = _publish_destination(sandbox)
    (destination / "about.json").write_text(
        json.dumps({"username": "stale"}) + "\n", encoding="utf-8"
    )

    assert _check(sandbox) != 0
    assert "about.json" in capsys.readouterr().err


def test_check_detects_a_never_published_destination(
    sandbox: Path, capsys: pytest.CaptureFixture
) -> None:
    """A destination that was never written is drift, not an absence to ignore."""
    assert _check(sandbox) != 0
    assert "about.json" in capsys.readouterr().err


def test_check_does_not_write_to_the_destination(sandbox: Path) -> None:
    """The gate is a dry run: it must detect drift without repairing it."""
    destination = _publish_destination(sandbox)
    stale = destination / "about.json"
    stale_content = json.dumps({"username": "stale"}) + "\n"
    stale.write_text(stale_content, encoding="utf-8")

    _check(sandbox)

    assert stale.read_text(encoding="utf-8") == stale_content, (
        "check repaired the destination instead of reporting it"
    )


def test_check_ignores_manual_destinations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `manual` destination has no filesystem plan, so it cannot gate the build."""
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    (tmp_path / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[publishers.linkedin]\nkind = "manual"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli.validate, "main", lambda ctx: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda ctx: True)
    monkeypatch.setattr(cli, "cmd_generate", lambda target, ctx: 0)

    assert cli.main(["--project", str(tmp_path), "check"]) == 0


def test_missing_project_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A directory that is not a project fails loudly instead of guessing one."""
    assert cli.main(["--project", str(tmp_path), "check"]) == 2
    assert "profile init" in capsys.readouterr().err
