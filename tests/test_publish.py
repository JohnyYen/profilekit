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
import os
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


@pytest.mark.parametrize(
    "damage",
    ["invalid-json", "invalid-utf8", "unreadable"],
)
def test_a_corrupt_ledger_does_not_block_publishing(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, damage: str
) -> None:
    """Worst case is one redundant publish, which beats refusing to run.

    Ignoring the ledger is still reported, so a persistently broken ledger —
    and the redundant publishes it causes — does not go unnoticed.
    """
    _publish(project, "--execute")
    ledger = project / publish.STATE_DIR / publish.STATE_FILENAME
    if damage == "invalid-json":
        ledger.write_text("{not json", encoding="utf-8")
    elif damage == "invalid-utf8":
        ledger.write_bytes(b'{"site": "\xff\xfe"}')
    else:
        real_read_text = Path.read_text

        def deny_ledger(self: Path, *args: object, **kwargs: object) -> str:
            if self == ledger:
                raise PermissionError(13, "Permission denied", str(self))
            return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", deny_ledger)
    (project / "app" / "data" / "about.json").write_text("{}\n", encoding="utf-8")
    capsys.readouterr()

    rc = _publish(project, "--execute")
    out = capsys.readouterr()

    assert rc == 0
    site_line = next(line for line in out.out.splitlines() if line.startswith("site"))
    assert "published" in site_line
    assert f"warning: ignoring unreadable publish ledger {ledger}" in out.err
    assert "Traceback" not in out.out + out.err


def test_a_ledger_write_failure_keeps_the_results_and_fails(
    project: Path, capsys: pytest.CaptureFixture
) -> None:
    """Destinations already ran; losing their results to a traceback hides what happened."""
    # A file where the ledger directory belongs makes the write raise OSError.
    (project / publish.STATE_DIR).write_text("in the way\n", encoding="utf-8")

    rc = _publish(project, "--execute")
    out = capsys.readouterr()

    assert rc == 1
    site_line = next(line for line in out.out.splitlines() if line.startswith("site"))
    assert "published" in site_line, "the results table must survive a ledger failure"
    assert "could not write the publish ledger" in out.err
    assert str(project / publish.STATE_DIR / publish.STATE_FILENAME) in out.err
    assert "Traceback" not in out.out + out.err


def test_an_interrupted_ledger_write_leaves_the_old_ledger_intact(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The ledger is replaced atomically: a failed write never truncates it."""
    _publish(project, "--execute")
    ledger = project / publish.STATE_DIR / publish.STATE_FILENAME
    before = ledger.read_bytes()
    (project / "app" / "data" / "about.json").write_text("{}\n", encoding="utf-8")
    capsys.readouterr()

    def interrupted(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", interrupted)
    rc = _publish(project, "--execute")
    out = capsys.readouterr()

    assert rc == 1
    assert "disk full" in out.err
    assert ledger.read_bytes() == before, "a failed write must not touch the existing ledger"
    leftovers = sorted(p.name for p in ledger.parent.iterdir())
    assert leftovers == [publish.STATE_FILENAME], f"temp files left behind: {leftovers}"


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


# ---------------------------------------------------------------------------
# Regression: an adapter must never be skipped on a stale ledger entry
# ---------------------------------------------------------------------------


def test_a_plan_with_no_artifacts_has_no_digest() -> None:
    """An unknowable payload must yield None, not the hash of nothing.

    The empty hash is a constant. Returning it meant that after one publish
    the ledger matched forever and an out-of-tree adapter reported `unchanged`
    no matter how much its data had changed — a silent, permanent skip that
    looked like success.
    """
    from pathlib import Path as _Path

    from profilekit.publishers import PublishPlan

    empty = PublishPlan(
        destination="d",
        capability="push",
        resolved_path=_Path("/tmp"),
        changes=("<adapter-managed>",),
    )
    assert publish.plan_digest(empty) is None


def test_an_adapter_destination_republishes_every_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A destination whose content cannot be compared must always publish."""
    calls: list[int] = []

    def adapter(ctx, cfg=None, credentials=None):
        calls.append(1)
        from profilekit.publishers import PublishResult as _R

        return _R(destination="acme", status="published", detail="sent")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[publishers.acme]\nkind = "acme-cdn"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": adapter})

    for _ in range(2):
        assert cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"]) == 0

    assert len(calls) == 2, "the adapter was skipped on its second run"


def test_an_adapter_receives_its_config_and_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Calling an adapter with the context alone defeats the credential model.

    An adapter that is handed nothing it declared could only work by reading
    the environment itself, which is exactly what injection exists to prevent.
    """
    seen: dict[str, object] = {}

    def adapter(ctx, cfg=None, credentials=None):
        seen["cfg"] = cfg
        seen["credentials"] = credentials
        from profilekit.publishers import PublishResult as _R

        return _R(destination="acme", status="published", detail="sent")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n"
        '[publishers.acme]\nkind = "acme-cdn"\nregion = "eu"\n\n'
        '[publishers.acme.credential]\ntoken = "ACME_TOKEN"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("ACME_TOKEN", "s3cret")
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": adapter})

    cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"])

    assert seen["cfg"]["region"] == "eu"  # type: ignore[index]
    assert seen["credentials"]["token"].reveal() == "s3cret"  # type: ignore[index]


def test_a_legacy_one_argument_adapter_still_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Widening the entry-point call must not break adapters already written.

    Calling a one-argument adapter with three would raise an uncaught
    TypeError and abort the whole run, which destroys the per-destination
    failure isolation this layer exists to provide.
    """
    seen: list[object] = []

    def legacy_adapter(ctx):
        seen.append(ctx)
        from profilekit.publishers import PublishResult as _R

        return _R(destination="acme", status="published", detail="sent")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[publishers.acme]\nkind = "acme-cdn"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": legacy_adapter})

    rc = cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"])

    assert rc == 0, "a legacy adapter must not fail the run"
    assert len(seen) == 1


def test_a_two_argument_adapter_receives_its_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def two_arg_adapter(ctx, cfg):
        seen["cfg"] = cfg
        from profilekit.publishers import PublishResult as _R

        return _R(destination="acme", status="published", detail="sent")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[publishers.acme]\nkind = "acme-cdn"\nregion = "eu"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": two_arg_adapter})

    assert cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"]) == 0
    assert seen["cfg"]["region"] == "eu"  # type: ignore[index]


def test_a_legacy_adapter_with_a_defaulted_parameter_keeps_its_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Extras are passed by keyword, so an unrelated parameter is never hijacked.

    Counting positional parameters — the first approach — classified
    `def push(ctx, timeout=30)` as the two-argument form and handed the config
    mapping to `timeout`. Wrong data, silently, which is worse than failing.
    """
    seen: dict[str, object] = {}

    def legacy_with_default(ctx, timeout=30):
        seen["timeout"] = timeout
        from profilekit.publishers import PublishResult as _R

        return _R(destination="acme", status="published", detail="sent")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[publishers.acme]\nkind = "acme-cdn"\nregion = "eu"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": legacy_with_default})

    assert cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"]) == 0
    assert seen["timeout"] == 30, "an unrelated parameter received the config mapping"


def test_a_keyword_only_adapter_still_receives_its_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other direction of the same bug: data silently withheld.

    Counting positionals classified `def push(ctx, *, cfg=None)` as the
    one-argument form, so it never received the config at all.
    """
    seen: dict[str, object] = {}

    def keyword_only(ctx, *, cfg=None, credentials=None):
        seen["cfg"] = cfg
        seen["credentials"] = credentials
        from profilekit.publishers import PublishResult as _R

        return _R(destination="acme", status="published", detail="sent")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[publishers.acme]\nkind = "acme-cdn"\nregion = "eu"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": keyword_only})

    assert cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"]) == 0
    assert seen["cfg"]["region"] == "eu"  # type: ignore[index]


def test_an_adapter_taking_var_keywords_receives_everything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def var_keywords(ctx, **kwargs):
        seen.update(kwargs)
        from profilekit.publishers import PublishResult as _R

        return _R(destination="acme", status="published", detail="sent")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[publishers.acme]\nkind = "acme-cdn"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": var_keywords})

    cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"])
    assert sorted(seen) == ["cfg", "credentials"]


def test_a_signature_mismatch_fails_only_its_own_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Per-destination isolation must survive a broken adapter contract."""

    def broken(ctx, required_extra):
        raise AssertionError("should not be reached")

    shutil.copytree(FIXTURE_PROJECT, tmp_path / "p")
    (tmp_path / "p" / "profile.toml").write_text(
        "[project]\nconfig_version = 1\n\n"
        '[publishers.acme]\nkind = "acme-cdn"\n\n'
        '[publishers.linkedin]\nkind = "manual"\nartifacts = []\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("profilekit.registry.publishers", lambda: {"acme-cdn": broken})

    rc = cli.main(["--project", str(tmp_path / "p"), "publish", "--execute"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "failed" in out
    assert "linkedin" in out, "the healthy destination must still be processed"
