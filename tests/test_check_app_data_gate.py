"""``profile check`` must gate published destinations, not only ``output/``.

This gate exists because of a specific regression risk. Reclassifying the
portfolio data sync as a publisher removes it from the generate path, and the
CI freshness gate only diffs ``output/``. Without this check, drift in
``apps/portfolio/app/data/`` would become *less* protected after the
refactor than it was before it — the destination would simply stop being
looked at by anything.

So ``check`` runs every filesystem destination's ``plan()`` — a dry run, which
writes nothing — and fails when a destination does not match canonical data.
"""

import json
import shutil
from pathlib import Path

import pytest

from profilekit import cli
from profilekit.publishers import PublisherContext

ROOT_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project root with real canonical data and a current published destination."""
    shutil.copytree(ROOT_DIR / "data", tmp_path / "data")

    monkeypatch.setattr(cli.validate, "main", lambda: 0)
    monkeypatch.setattr(cli, "_git_output_is_clean", lambda: True)
    monkeypatch.setattr(
        cli,
        "_project_context",
        lambda: PublisherContext(root=tmp_path, data_dir=tmp_path / "data"),
    )
    # Generators are exercised elsewhere; this gate is about destinations.
    monkeypatch.setattr(cli, "cmd_generate", lambda target: 0)
    return tmp_path


def _publish_destination(sandbox: Path) -> Path:
    from profilekit.publishers.filesystem import FilesystemPublisher

    publisher = FilesystemPublisher()
    ctx = PublisherContext(root=sandbox, data_dir=sandbox / "data")
    plan = publisher.plan(ctx, {})
    publisher.publish(ctx, plan)
    return plan.resolved_path


def test_check_passes_when_published_destination_is_current(sandbox: Path) -> None:
    _publish_destination(sandbox)
    assert cli.main(["check"]) == 0


def test_check_detects_app_data_drift(sandbox: Path, capsys: pytest.CaptureFixture) -> None:
    """A stale destination must fail the gate and name what drifted."""
    destination = _publish_destination(sandbox)
    stale = destination / "about.json"
    stale.write_text(json.dumps({"username": "stale"}) + "\n", encoding="utf-8")

    assert cli.main(["check"]) != 0
    assert "about.json" in capsys.readouterr().err


def test_check_detects_a_never_published_destination(
    sandbox: Path, capsys: pytest.CaptureFixture
) -> None:
    """A destination that was never written is drift, not an absence to ignore."""
    assert cli.main(["check"]) != 0
    assert "about.json" in capsys.readouterr().err


def test_check_does_not_write_to_the_destination(sandbox: Path) -> None:
    """The gate is a dry run: it must detect drift without repairing it."""
    destination = _publish_destination(sandbox)
    stale = destination / "about.json"
    stale_content = json.dumps({"username": "stale"}) + "\n"
    stale.write_text(stale_content, encoding="utf-8")

    cli.main(["check"])

    assert stale.read_text(encoding="utf-8") == stale_content, (
        "check repaired the destination instead of reporting it"
    )
