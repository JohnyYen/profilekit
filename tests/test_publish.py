"""The publication layer: dry-run, honesty, idempotency, isolation.

Each property here exists because the obvious alternative is dangerous:

- Writing by default would make an accidental publish the easy mistake.
- A `manual` destination reporting success would let a profile silently go
  stale while the operator stopped checking.
- Republishing unchanged content makes a destination's history look busy when
  nothing happened.
- Aborting on the first failure turns one platform's outage into a total
  failure, even though the destinations are independent.
- Treating an absent credential as fatal would break the default experience
  for the `filesystem` and `manual` kinds, which need none.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from profilekit import cli, manifest, publish
from profilekit.context import discover_project

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PROJECT = REPO_ROOT / "tests" / "fixtures" / "project"

CONFIG = """\
[project]
config_version = 1

[publishers.site]
kind = "filesystem"
destination = "app/data"

[publishers.linkedin]
kind = "manual"
artifacts = ["linkedin.md"]
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(FIXTURE_PROJECT, target)
    (target / "profile.toml").write_text(CONFIG, encoding="utf-8")

    ctx = discover_project(explicit=target)
    from profilekit import registry

    for run in registry.generators().values():
        run(ctx)
    manifest.write(ctx)
    return target


def _publish(project: Path, *argv: str) -> int:
    return cli.main(["--project", str(project), "publish", *argv])


# ---------------------------------------------------------------------------
# Dry run is the default
# ---------------------------------------------------------------------------


def test_dry_run_is_the_default_and_writes_nothing(project: Path) -> None:
    assert _publish(project) == 0
    assert not (project / "app" / "data").exists(), "a dry run must not write"


def test_execute_is_required_to_write(project: Path) -> None:
    assert _publish(project, "--execute") == 0
    written = sorted(p.name for p in (project / "app" / "data").glob("*.json"))
    assert written == ["about.json", "projects.json", "skills.json", "social.json"]


def test_dry_run_says_it_published_nothing(project: Path, capsys: pytest.CaptureFixture) -> None:
    _publish(project)
    assert "nothing was published" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# A manual destination never claims success
# ---------------------------------------------------------------------------


def test_manual_never_reports_published(project: Path, capsys: pytest.CaptureFixture) -> None:
    _publish(project, "--execute")
    out = capsys.readouterr().out

    manual_line = next(line for line in out.splitlines() if line.startswith("linkedin"))
    assert "pending-manual" in manual_line
    assert "published" not in manual_line


def test_manual_states_the_pending_action(project: Path, capsys: pytest.CaptureFixture) -> None:
    """Reporting a pending state without saying what to do is not much better."""
    _publish(project, "--execute")
    out = capsys.readouterr().out

    assert "linkedin.md" in out
    assert "by hand" in out


def test_manual_capability_is_not_configurable(project: Path) -> None:
    """Capability is declared by the kind: a project cannot wish it away."""
    from profilekit.publishers.manual import ManualPublisher

    assert ManualPublisher.capability == "manual"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_unchanged_destination_is_not_rewritten(
    project: Path, capsys: pytest.CaptureFixture
) -> None:
    _publish(project, "--execute")
    capsys.readouterr()

    _publish(project, "--execute")
    out = capsys.readouterr().out

    site_line = next(line for line in out.splitlines() if line.startswith("site"))
    assert "unchanged" in site_line


def test_changed_content_republishes(project: Path, capsys: pytest.CaptureFixture) -> None:
    _publish(project, "--execute")
    capsys.readouterr()

    target = project / "app" / "data" / "about.json"
    target.write_text(json.dumps({"username": "stale"}) + "\n", encoding="utf-8")

    _publish(project, "--execute")
    site_line = next(
        line for line in capsys.readouterr().out.splitlines() if line.startswith("site")
    )
    assert "published" in site_line


def test_the_ledger_is_local_and_gitignored(project: Path) -> None:
    _publish(project, "--execute")
    ledger = project / publish.STATE_DIR / publish.STATE_FILENAME
    assert ledger.is_file()

    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".profilekit/" in ignore, "the ledger records one machine's runs; it must not be shared"


def test_a_corrupt_ledger_does_not_block_publishing(project: Path) -> None:
    """Worst case is one redundant publish, which beats refusing to run."""
    _publish(project, "--execute")
    ledger = project / publish.STATE_DIR / publish.STATE_FILENAME
    ledger.write_text("{not json", encoding="utf-8")

    assert _publish(project, "--execute") == 0


# ---------------------------------------------------------------------------
# Failure isolation
# ---------------------------------------------------------------------------


def test_one_failure_does_not_abort_the_others(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A broken destination must not prevent the healthy ones from reporting."""
    original = publish.publish_destination

    def selective(ctx, destination, **kwargs):
        if destination.name == "site":
            raise RuntimeError("destination exploded")
        return original(ctx, destination, **kwargs)

    monkeypatch.setattr(cli.publish, "publish_destination", selective)

    rc = _publish(project, "--execute")
    out = capsys.readouterr().out

    assert rc == 1, "a failure must be visible in the exit code"
    assert "failed" in out
    assert "linkedin" in out, "the healthy destination must still be processed"


def test_failure_names_the_exception_type(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def boom(ctx, destination, **kwargs):
        raise ValueError("bad config")

    monkeypatch.setattr(cli.publish, "publish_destination", boom)
    _publish(project, "--execute")

    assert "ValueError" in capsys.readouterr().out


def test_pending_manual_alone_exits_zero(project: Path) -> None:
    """A pending manual action is not a failure; it is work for a human."""
    assert _publish(project, "linkedin", "--execute") == 0


# ---------------------------------------------------------------------------
# A core that needs no credentials
# ---------------------------------------------------------------------------


def test_no_credentials_completes_without_a_fatal_error(project: Path) -> None:
    """The built-in kinds must work with no secrets configured at all."""
    assert _publish(project, "--execute") == 0


def test_missing_credential_is_skipped_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    target = tmp_path / "p"
    shutil.copytree(FIXTURE_PROJECT, target)
    (target / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n"
        '[publishers.remote]\nkind = "filesystem"\ndestination = "out"\n\n'
        '[publishers.remote.credential]\ntoken = "ABSENT_TOKEN_VAR"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("ABSENT_TOKEN_VAR", raising=False)

    rc = cli.main(["--project", str(target), "publish", "--execute"])
    out = capsys.readouterr().out

    assert rc == 0, "an absent secret is a configuration state, not an error"
    assert "skipped" in out


def test_require_credentials_escalates_to_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CI needs the opposite default: a silently skipped publish is a problem."""
    target = tmp_path / "p"
    shutil.copytree(FIXTURE_PROJECT, target)
    (target / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n"
        '[publishers.remote]\nkind = "filesystem"\ndestination = "out"\n\n'
        '[publishers.remote.credential]\ntoken = "ABSENT_TOKEN_VAR"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("ABSENT_TOKEN_VAR", raising=False)

    rc = cli.main(["--project", str(target), "publish", "--execute", "--require-credentials"])
    assert rc == 1


def test_a_project_with_no_destinations_is_not_an_error(tmp_path: Path) -> None:
    target = tmp_path / "p"
    shutil.copytree(FIXTURE_PROJECT, target)
    (target / "profile.toml").write_text("[project]\nconfig_version = 1\n", encoding="utf-8")

    assert cli.main(["--project", str(target), "publish"]) == 0


def test_unknown_destination_kind_fails_that_destination_only(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    target = tmp_path / "p"
    shutil.copytree(FIXTURE_PROJECT, target)
    (target / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n"
        '[publishers.weird]\nkind = "not-a-kind"\n\n'
        '[publishers.linkedin]\nkind = "manual"\nartifacts = []\n',
        encoding="utf-8",
    )

    rc = cli.main(["--project", str(target), "publish", "--execute"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "linkedin" in out, "the valid destination must still be processed"


# ---------------------------------------------------------------------------
# The core declares no network dependency
# ---------------------------------------------------------------------------


def test_core_declares_zero_network_dependencies() -> None:
    """`filesystem` and `manual` need no network, so the core must not pull one in."""
    import tomllib

    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        config = tomllib.load(handle)

    declared = config["project"]["dependencies"]
    network_packages = {"requests", "httpx", "urllib3", "aiohttp", "boto3", "paramiko"}

    offenders = [
        dep for dep in declared if dep.split(">=")[0].split("==")[0].strip() in network_packages
    ]
    assert not offenders, (
        f"the core must stay network-free; credentialed adapters ship separately: {offenders}"
    )
