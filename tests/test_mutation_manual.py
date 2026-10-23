"""Behavior pinned down by mutation testing of ``profilekit.publishers.manual``.

A manual destination is the one place the tool hands work to a human, so what
it tells that human is its whole output. Each test kills mutants that survived
the baseline run (see ``docs/quality/mutation-baseline.md``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from profilekit.config import ConfigError
from profilekit.context import ProjectContext
from profilekit.publishers import Artifact, PublishPlan, PublishResult
from profilekit.publishers.manual import ManualPublisher, publish_entry_point


@pytest.fixture
def ctx(tmp_path: Path) -> ProjectContext:
    context = ProjectContext.for_root(tmp_path)
    context.output_dir.mkdir()
    (context.output_dir / "linkedin.md").write_text("headline\n", encoding="utf-8")
    (context.output_dir / "cv.md").write_text("cv\n", encoding="utf-8")
    return context


def test_plan_collects_declared_artifacts_from_the_output_directory(ctx: ProjectContext) -> None:
    plan = ManualPublisher().plan(ctx, {"artifacts": ["linkedin.md", "cv.md"]})

    assert plan == PublishPlan(
        destination="manual",
        capability="manual",
        resolved_path=ctx.output_dir,
        artifacts=(Artifact("linkedin.md", "headline\n"), Artifact("cv.md", "cv\n")),
        changes=("linkedin.md", "cv.md"),
    )


def test_plan_uses_the_configured_destination_label(ctx: ProjectContext) -> None:
    plan = ManualPublisher().plan(ctx, {"destination": "LinkedIn", "artifacts": ["cv.md"]})

    assert plan.destination == "LinkedIn"


def test_missing_artifacts_are_all_named(ctx: ProjectContext) -> None:
    cfg = {"artifacts": ["linkedin.md", "gone.md", "also-gone.md"]}

    with pytest.raises(FileNotFoundError) as excinfo:
        ManualPublisher().plan(ctx, cfg)

    assert str(excinfo.value) == (
        "manual destination lists artifacts that have not been generated: gone.md, also-gone.md"
    )


def test_a_destination_that_declares_no_artifacts_plans_none(ctx: ProjectContext) -> None:
    plan = ManualPublisher().plan(ctx, {})

    assert plan.artifacts == ()
    assert plan.changes == ()


@pytest.mark.parametrize(
    ("declared", "complaint"),
    [
        ("linkedin.md", "artifacts must be a list of file names, got str"),
        (["linkedin.md", 3], "artifacts[1] must be a file name, got int"),
    ],
)
def test_a_malformed_artifact_list_is_not_silently_ignored(
    ctx: ProjectContext, declared: object, complaint: str
) -> None:
    """A malformed list is a configuration error, not "copy nothing by hand"."""
    with pytest.raises(ConfigError) as exc_info:
        publish_entry_point(ctx, {"destination": "LinkedIn", "artifacts": declared})

    assert str(exc_info.value) == f"destination 'LinkedIn': {complaint}"


def test_publish_tells_the_human_exactly_what_to_copy_and_where(ctx: ProjectContext) -> None:
    publisher = ManualPublisher()
    plan = publisher.plan(ctx, {"destination": "LinkedIn", "artifacts": ["linkedin.md", "cv.md"]})

    result = publisher.publish(ctx, plan)

    assert result == PublishResult(
        destination="LinkedIn",
        status="pending-manual",
        detail="LinkedIn has no write API available to this tool",
        action_required=f"copy linkedin.md, cv.md from {ctx.output_dir} into LinkedIn by hand",
    )


def test_entry_point_reports_the_pending_action(ctx: ProjectContext) -> None:
    result = publish_entry_point(ctx, {"artifacts": ["cv.md"]}, credentials={})

    assert result == PublishResult(
        destination="manual",
        status="pending-manual",
        detail="manual has no write API available to this tool",
        action_required=f"copy cv.md from {ctx.output_dir} into manual by hand",
    )


def test_entry_point_without_config_still_reports_pending_manual(ctx: ProjectContext) -> None:
    result = publish_entry_point(ctx)

    assert result.status == "pending-manual"
    assert result.detail == "manual has no write API available to this tool"
