"""Behavior pinned down by mutation testing of ``profilekit.publish``.

Each test kills mutants that survived the baseline run (see
``docs/quality/mutation-baseline.md``). The themes: the publish ledger's
on-disk format and its atomic write, which signal decides ``unchanged``, what
gets recorded in the ledger after a run, and the exact text an operator reads
in the results table.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from profilekit import publish, safe_io
from profilekit.context import ProjectContext
from profilekit.publish import (
    Destination,
    destinations,
    ledger_path,
    plan_digest,
    publish_destination,
    read_state,
    write_state,
)
from profilekit.publishers import Artifact, PublishPlan, PublishResult
from profilekit.registry import RegistryError

FIXTURE_DATA = Path(__file__).resolve().parent / "fixtures" / "project" / "data"


@pytest.fixture
def ctx(tmp_path: Path) -> ProjectContext:
    root = tmp_path / "project"
    shutil.copytree(FIXTURE_DATA, root / "data")
    (root / "output").mkdir()
    (root / "output" / "linkedin.md").write_text("# LinkedIn copy\n", encoding="utf-8")
    return ProjectContext.for_root(root)


def _run(ctx: ProjectContext, destination: Destination, **kwargs: Any) -> PublishResult:
    options: dict[str, Any] = {"execute": False, "state": {}, "require_credentials": False}
    options.update(kwargs)
    return publish_destination(ctx, destination, **options)


SITE = Destination("site", "filesystem", {"kind": "filesystem", "destination": "app/data"})
LINKEDIN = Destination("linkedin", "manual", {"kind": "manual", "artifacts": ["linkedin.md"]})


# ---------------------------------------------------------------------------
# Destinations
# ---------------------------------------------------------------------------


def test_a_destination_without_a_kind_has_an_empty_kind(tmp_path: Path) -> None:
    ctx = ProjectContext.for_root(tmp_path, config={"publishers": {"site": {"destination": "x"}}})

    assert destinations(ctx) == [Destination("site", "", {"destination": "x"})]


def test_unknown_kind_error_names_destination_kind_and_builtins(ctx: ProjectContext) -> None:
    with pytest.raises(RegistryError) as excinfo:
        _run(ctx, Destination("site", "ftp", {"kind": "ftp"}))

    assert str(excinfo.value) == (
        "destination 'site' declares unknown kind 'ftp'; built-in kinds are: filesystem, manual"
    )


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------


def test_ledger_is_sorted_two_space_json_with_trailing_newline(ctx: ProjectContext) -> None:
    path = write_state(ctx, {"zeta": "2", "alpha": "1"})

    assert path == ctx.root / ".profilekit" / "publish-state.json"
    assert path.read_text(encoding="utf-8") == '{\n  "alpha": "1",\n  "zeta": "2"\n}\n'


def test_ledger_write_creates_missing_parent_directories(tmp_path: Path) -> None:
    ctx = ProjectContext.for_root(tmp_path / "not" / "yet" / "there")

    write_state(ctx, {"site": "abc"})

    assert read_state(ctx) == {"site": "abc"}


def test_ledger_is_written_through_a_temporary_file_beside_it(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rename is only atomic within one directory, so the temp file lives there.

    The first write creates the ledger exclusively; only replacing an existing
    ledger goes through a temporary file, so the ledger is written twice.
    """
    seen: list[Path] = []
    real_replace = os.replace

    def spy(src: str, dst: object) -> None:
        seen.append(Path(src))
        real_replace(src, dst)

    write_state(ctx, {"site": "old"})
    monkeypatch.setattr(safe_io.os, "replace", spy)

    path = write_state(ctx, {"site": "abc"})

    (temp,) = seen
    assert temp.parent == path.parent
    assert temp.name.startswith(".publish-state.json.")
    assert temp.name.endswith(".tmp")
    assert read_state(ctx) == {"site": "abc"}
    assert sorted(p.name for p in path.parent.iterdir()) == ["publish-state.json"]


def test_a_failed_ledger_write_reraises_the_original_error(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup of a temp file that is already gone must not mask the real failure."""
    original = OSError("disk went away")

    def vanish_then_fail(src: str, dst: object) -> None:
        Path(src).unlink()
        raise original

    write_state(ctx, {"site": "old"})
    monkeypatch.setattr(safe_io.os, "replace", vanish_then_fail)

    with pytest.raises(OSError, match="disk went away") as excinfo:
        write_state(ctx, {"site": "abc"})

    assert excinfo.value is original
    assert read_state(ctx) == {"site": "old"}


def test_ledger_values_and_keys_are_read_as_strings(ctx: ProjectContext) -> None:
    ledger_path(ctx).parent.mkdir()
    ledger_path(ctx).write_text(json.dumps({"site": 7}), encoding="utf-8")

    assert read_state(ctx) == {"site": "7"}


@pytest.mark.parametrize("payload", ["[1, 2]", '"text"', "3"])
def test_a_ledger_that_is_not_an_object_reads_as_empty(ctx: ProjectContext, payload: str) -> None:
    ledger_path(ctx).parent.mkdir()
    ledger_path(ctx).write_text(payload, encoding="utf-8")

    assert read_state(ctx) == {}


def test_a_corrupt_ledger_warning_says_everything_will_republish(
    ctx: ProjectContext, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger_path(ctx).parent.mkdir()
    ledger_path(ctx).write_text("{not json", encoding="utf-8")

    assert read_state(ctx) == {}
    err = capsys.readouterr().err
    assert err.startswith(f"warning: ignoring unreadable publish ledger {ledger_path(ctx)}: ")
    assert err.endswith(" — every destination is treated as changed\n")


def test_plan_digest_is_stable_across_releases() -> None:
    """The digest is persisted in ledgers; changing its formula republishes everything."""

    class _Plan:
        artifacts = (Artifact("b.json", "B"), Artifact("a.json", "A"))

    assert plan_digest(_Plan()) == (
        "b4985712f782130abdc0fbf70bbc007ccd9f757aa07cbacf615590cc422c7afa"
    )


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


def _with_credential(destination: Destination) -> Destination:
    config = {**destination.config, "credential": {"token": "PROFILEKIT_TEST_NO_SUCH_VAR"}}
    return Destination(destination.name, destination.kind, config)


def test_missing_credential_is_skipped_without_an_action(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PROFILEKIT_TEST_NO_SUCH_VAR", raising=False)

    result = _run(ctx, _with_credential(SITE))

    assert result == PublishResult(
        destination="site",
        status="skipped",
        detail="destination 'site': environment variable 'PROFILEKIT_TEST_NO_SUCH_VAR' "
        "is not set or is empty",
        action_required=None,
    )


def test_required_missing_credential_fails_and_says_how_to_fix_it(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PROFILEKIT_TEST_NO_SUCH_VAR", raising=False)

    result = _run(ctx, _with_credential(SITE), require_credentials=True)

    assert result.status == "failed"
    assert "'site'" in result.detail
    assert result.action_required == (
        "set the declared environment variable, or drop --require-credentials"
    )


# ---------------------------------------------------------------------------
# Dry run, unchanged, and the ledger after execute
# ---------------------------------------------------------------------------


def test_dry_run_detail_lists_every_change_and_how_to_publish(ctx: ProjectContext) -> None:
    result = _run(ctx, SITE)

    assert result == PublishResult(
        destination="site",
        status="would-publish",
        detail="dry run — would write: about.json, social.json, skills.json, "
        "projects.json, manifest.json",
        action_required="re-run with --execute to publish",
    )


def test_dry_run_with_no_comparable_content_says_nothing(ctx: ProjectContext) -> None:
    """A manual destination listing no artifacts has no digest, so it is never skipped."""
    empty = Destination("linkedin", "manual", {"kind": "manual", "artifacts": []})

    result = _run(ctx, empty)

    assert result.status == "pending-manual"
    assert result.detail == "dry run — would write: nothing"


def test_a_matching_ledger_entry_makes_a_non_reading_destination_unchanged(
    ctx: ProjectContext,
) -> None:
    first = _run(ctx, LINKEDIN)
    assert first.status == "pending-manual"

    plan = publish._load_publisher(LINKEDIN).plan(ctx, LINKEDIN.config)
    result = _run(ctx, LINKEDIN, state={"linkedin": plan_digest(plan)})

    assert result == PublishResult(
        destination="linkedin",
        status="unchanged",
        detail="destination already matches the current artifacts",
    )


def test_a_current_readable_destination_dry_runs_as_unchanged(ctx: ProjectContext) -> None:
    """A destination that can be read back is judged by its plan, before any write."""
    _run(ctx, SITE, execute=True)

    result = _run(ctx, SITE)

    assert result == PublishResult(
        destination="site",
        status="unchanged",
        detail="destination already matches the current artifacts",
    )


def test_a_ledger_entry_under_another_name_does_not_count(ctx: ProjectContext) -> None:
    plan = publish._load_publisher(LINKEDIN).plan(ctx, LINKEDIN.config)

    result = _run(ctx, LINKEDIN, state={"other": plan_digest(plan)})

    assert result.status == "pending-manual"


def test_a_published_destination_is_recorded_in_the_ledger_by_its_name(
    ctx: ProjectContext,
) -> None:
    state: dict[str, str] = {}
    plan = publish._load_publisher(SITE).plan(ctx, SITE.config)

    result = _run(ctx, SITE, execute=True, state=state)

    assert result.status == "published"
    assert state == {"site": plan_digest(plan)}


def test_publish_result_and_detail_use_the_declared_name(ctx: ProjectContext) -> None:
    result = _run(ctx, SITE, execute=True)

    assert result.destination == "site"
    assert result.detail == (
        "wrote 5 file(s) to site: about.json, social.json, skills.json, "
        "projects.json, manifest.json"
    )


def test_a_pending_manual_publish_is_not_recorded_in_the_ledger(ctx: ProjectContext) -> None:
    """Only a write that happened may be remembered as published."""
    state: dict[str, str] = {}

    result = _run(ctx, LINKEDIN, execute=True, state=state)

    assert result.status == "pending-manual"
    assert state == {}


class _BlindPublisher:
    """A publisher that never says whether it can read its destination."""

    capability = "push"

    def __init__(self) -> None:
        self.published = 0

    def plan(self, ctx: ProjectContext, cfg: object) -> PublishPlan:
        return PublishPlan(
            destination="blind",
            capability="push",
            resolved_path=ctx.root,
            artifacts=(Artifact("a.txt", "A"),),
            changes=(),
        )

    def publish(self, ctx: ProjectContext, plan: PublishPlan) -> PublishResult:
        self.published += 1
        return PublishResult(destination="blind", status="published", detail="sent")


def test_a_publisher_that_does_not_declare_read_back_falls_back_to_the_ledger(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Its empty ``changes`` must not be trusted: nothing says it looked."""
    blind = _BlindPublisher()
    monkeypatch.setattr(publish, "_load_publisher", lambda destination: blind)

    result = _run(ctx, Destination("blind", "blind", {}), execute=True)

    assert result.status == "published"
    assert blind.published == 1


# ---------------------------------------------------------------------------
# Out-of-tree adapters
# ---------------------------------------------------------------------------


class _EntryPoint:
    def __init__(self, name: str, value: object) -> None:
        self.name = name
        self.value = f"fake:{name}"
        self.dist = None
        self._value = value

    def load(self) -> object:
        return self._value


def _install(monkeypatch: pytest.MonkeyPatch, kind: str, implementation: object) -> None:
    entry_points = [_EntryPoint(kind, implementation)]
    monkeypatch.setattr(
        "profilekit.registry._entry_points_for",
        lambda group: entry_points if group == "profilekit.publishers" else [],
    )


def test_adapter_plan_defaults_its_destination_to_the_kind(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(monkeypatch, "webhook", lambda ctx: None)
    adapter = publish._load_publisher(Destination("hook", "webhook", {}))

    plan = adapter.plan(ctx, {})

    assert (adapter.kind, adapter.capability, adapter.reads_destination) == (
        "webhook",
        "push",
        False,
    )
    assert plan == PublishPlan(
        destination="webhook",
        capability="push",
        resolved_path=ctx.root,
        changes=("<adapter-managed>",),
    )
    assert adapter.plan(ctx, {"destination": "https://example.com"}).destination == (
        "https://example.com"
    )


def test_adapter_is_called_with_the_project_context(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[object, dict[str, Any]]] = []

    def push(context: ProjectContext, cfg: object = None) -> PublishResult:
        calls.append((context, {"cfg": cfg}))
        return PublishResult(destination="x", status="published", detail="ok")

    _install(monkeypatch, "webhook", push)
    destination = Destination("hook", "webhook", {"kind": "webhook", "url": "u"})

    result = _run(ctx, destination, execute=True)

    assert result.destination == "hook"
    assert calls == [(ctx, {"cfg": {"kind": "webhook", "url": "u"}})]


class _NoSignature:
    """A callable whose signature cannot be inspected, like many builtins."""

    __signature__ = "not a signature"

    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, Any]]] = []

    def __call__(self, ctx: object, **kwargs: Any) -> PublishResult:
        self.calls.append((ctx, kwargs))
        return PublishResult(destination="x", status="published", detail="ok")


def test_adapter_without_a_signature_gets_the_full_current_contract(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = _NoSignature()
    _install(monkeypatch, "opaque", adapter)
    destination = Destination("box", "opaque", {"kind": "opaque"})

    _run(ctx, destination, execute=True)

    ((called_ctx, kwargs),) = adapter.calls
    assert called_ctx is ctx
    assert kwargs == {"cfg": {"kind": "opaque"}, "credentials": {}}
