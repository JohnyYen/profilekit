"""Behavior pinned down by mutation testing of ``profilekit.publishers.filesystem``.

Each test kills mutants that survived the baseline run (see
``docs/quality/mutation-baseline.md``): the refusal messages of the path-safety
checks, the exact bytes a frontend reads, the defaults of optional project
fields, and the result text of a publish.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from profilekit.context import ProjectContext
from profilekit.publishers.filesystem import (
    DEFAULT_DESTINATION,
    FilesystemPublisher,
    UnsafeDestinationError,
    artifact_path,
    build_artifacts,
    publish_entry_point,
    resolve_destination,
)

ABOUT = {
    "username": "José Núñez",
    "tagline": "Builds things",
    "description": "Lives in Málaga.",
    "currentFocus": [],
    "whatIBuild": ["Tools"],
    "learningJourney": "Rust",
    "email": "not-published@example.com",
}


@pytest.fixture
def ctx(tmp_path: Path) -> ProjectContext:
    root = tmp_path / "project"
    data = root / "data"
    data.mkdir(parents=True)
    files = {
        "about.json": ABOUT,
        "social.json": {"github": "https://github.com/example"},
        "skills.json": {"categories": []},
        "projects.json": [
            {"name": "Café", "start_date": "2020-01"},
            {"name": "Full", "description": "D", "tech": "Python", "url": "https://x.dev"},
        ],
    }
    for name, payload in files.items():
        (data / name).write_text(json.dumps(payload), encoding="utf-8")
    return ProjectContext.for_root(root)


def _artifact(ctx: ProjectContext, name: str) -> str:
    return next(a.content for a in build_artifacts(ctx) if a.name == name)


# ---------------------------------------------------------------------------
# Path safety: the refusal says what was refused and why
# ---------------------------------------------------------------------------


def test_absolute_destination_refusal_names_the_path(tmp_path: Path) -> None:
    absolute = str(tmp_path / "elsewhere")

    with pytest.raises(UnsafeDestinationError) as excinfo:
        resolve_destination(tmp_path, absolute)

    assert str(excinfo.value) == (
        f"destination must be relative to the project root, got absolute path: {absolute}"
    )


def test_escaping_destination_refusal_shows_where_it_resolved(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    with pytest.raises(UnsafeDestinationError) as excinfo:
        resolve_destination(root, "../outside")

    assert str(excinfo.value) == (
        f"destination escapes the project root: ../outside -> {(tmp_path / 'outside').resolve()}"
    )


def test_artifact_in_a_redirected_directory_is_refused(tmp_path: Path) -> None:
    """A destination swapped for a symlink after planning no longer contains its artifacts."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)

    with pytest.raises(UnsafeDestinationError) as excinfo:
        artifact_path(link, "about.json")

    assert str(excinfo.value) == (
        f"artifact resolves outside the destination: {link / 'about.json'} -> "
        f"{(real / 'about.json').resolve()}"
    )


# ---------------------------------------------------------------------------
# What a frontend reads
# ---------------------------------------------------------------------------


def test_projects_get_empty_defaults_and_keep_present_fields(ctx: ProjectContext) -> None:
    assert json.loads(_artifact(ctx, "projects.json")) == [
        {"name": "Café", "description": "", "tech": "", "url": ""},
        {"name": "Full", "description": "D", "tech": "Python", "url": "https://x.dev"},
    ]


def test_artifacts_are_two_space_json_with_literal_unicode(ctx: ProjectContext) -> None:
    assert _artifact(ctx, "social.json") == (
        '{\n  "schemaVersion": 1,\n  "github": "https://github.com/example"\n}\n'
    )
    assert '"username": "José Núñez"' in _artifact(ctx, "about.json")
    assert _artifact(ctx, "projects.json").startswith('[\n  {\n    "name": "Café",\n')


# ---------------------------------------------------------------------------
# Plan and publish
# ---------------------------------------------------------------------------


def test_plan_without_a_destination_uses_the_default(ctx: ProjectContext) -> None:
    plan = FilesystemPublisher().plan(ctx, {})

    assert plan.destination == DEFAULT_DESTINATION
    assert plan.resolved_path == ctx.root / DEFAULT_DESTINATION


def test_plan_carries_the_configured_destination(ctx: ProjectContext) -> None:
    assert FilesystemPublisher().plan(ctx, {"destination": "site/data"}).destination == "site/data"


def test_publish_reports_how_many_files_it_wrote_and_where(ctx: ProjectContext) -> None:
    publisher = FilesystemPublisher()

    result = publisher.publish(ctx, publisher.plan(ctx, {"destination": "site/data"}))

    assert result.destination == "site/data"
    assert result.status == "published"
    assert result.detail == (
        "wrote 5 file(s) to site/data: about.json, social.json, skills.json, "
        "projects.json, manifest.json"
    )


def test_publishing_a_current_destination_reports_unchanged(ctx: ProjectContext) -> None:
    publisher = FilesystemPublisher()
    publisher.publish(ctx, publisher.plan(ctx, {"destination": "site/data"}))

    result = publisher.publish(ctx, publisher.plan(ctx, {"destination": "site/data"}))

    assert (result.destination, result.status, result.detail) == (
        "site/data",
        "unchanged",
        "destination already matches canonical data",
    )


def test_entry_point_plans_and_writes_to_the_default_destination(ctx: ProjectContext) -> None:
    result = publish_entry_point(ctx)

    assert result.status == "published"
    assert result.destination == DEFAULT_DESTINATION
    written = ctx.root / DEFAULT_DESTINATION
    assert sorted(p.name for p in written.iterdir()) == [
        "about.json",
        "manifest.json",
        "projects.json",
        "skills.json",
        "social.json",
    ]


def test_entry_point_honours_the_configured_destination(ctx: ProjectContext) -> None:
    result = publish_entry_point(ctx, {"destination": "site/data"}, credentials={})

    assert result.destination == "site/data"
    assert (ctx.root / "site" / "data" / "about.json").is_file()
