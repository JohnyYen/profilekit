"""The filesystem publisher and its path-safety guard.

A publisher writes outside the output directory by definition, so its
destination is the one piece of configuration an attacker — or a careless
edit — can turn into an arbitrary-write primitive. The destination is
therefore resolved against the project root and rejected before any write,
not after.

Threat matrix row 1 (documentation-like destination paths) is covered by
``test_rejects_*`` below.
"""

import json
from pathlib import Path

import pytest

from profilekit.context import ProjectContext
from profilekit.publishers.filesystem import FilesystemPublisher, UnsafeDestinationError

CANONICAL = {
    "about.json": {
        "username": "Ada Lovelace",
        "tagline": "Analytical Engine enthusiast",
        "description": "Writes algorithms for machines that do not exist yet.",
        "currentFocus": [{"title": "Note G", "description": "The first program."}],
        "whatIBuild": ["Algorithms"],
        "learningJourney": "Translating Menabrea, then exceeding him.",
    },
    "social.json": {"github": "https://github.com/example", "email": "ada@example.test"},
    "skills.json": {"categories": [{"label": "Math", "details": ["Analysis"]}]},
    "projects.json": [
        {
            "name": "Note G",
            "description": "Bernoulli numbers",
            "tech": "Analytical Engine",
            "url": "https://example.test/note-g",
        }
    ],
}


@pytest.fixture
def project(tmp_path: Path) -> ProjectContext:
    """A sandboxed project root with canonical data and a destination inside it."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for filename, payload in CANONICAL.items():
        (data_dir / filename).write_text(json.dumps(payload), encoding="utf-8")
    return ProjectContext.for_root(tmp_path, data_dir=data_dir)


def _destinations_written(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.json") if p.is_file() and p.parent.name != "data")


# ---------------------------------------------------------------------------
# Path safety — every rejection must happen before anything is written
# ---------------------------------------------------------------------------


def test_rejects_parent_directory_escape(project: ProjectContext) -> None:
    publisher = FilesystemPublisher()
    with pytest.raises(UnsafeDestinationError):
        publisher.plan(project, {"destination": "../../etc"})
    assert not _destinations_written(project.root)


def test_rejects_absolute_destination(project: ProjectContext, tmp_path: Path) -> None:
    publisher = FilesystemPublisher()
    outside = tmp_path.parent / "outside-target"
    with pytest.raises(UnsafeDestinationError):
        publisher.plan(project, {"destination": str(outside)})
    assert not outside.exists()


def test_rejects_symlink_escape(project: ProjectContext, tmp_path: Path) -> None:
    """A destination inside the root that resolves outside it is still an escape."""
    outside = tmp_path.parent / f"outside-{tmp_path.name}"
    outside.mkdir(exist_ok=True)
    link = project.root / "sneaky"
    link.symlink_to(outside, target_is_directory=True)

    publisher = FilesystemPublisher()
    with pytest.raises(UnsafeDestinationError):
        publisher.plan(project, {"destination": "sneaky"})
    assert not list(outside.iterdir()), "publisher wrote through a symlink escape"


@pytest.mark.parametrize("destination", [".", "", "data", "data/nested", "output", "output/site"])
def test_rejects_destinations_that_would_overwrite_project_inputs_or_outputs(
    project: ProjectContext, destination: str
) -> None:
    """The root, the canonical data dir and the output dir are never a destination.

    Publishing into ``data/`` would replace canonical ``about.json`` with its
    six-key published subset — silent data loss that no later run can undo.
    """
    canonical = (project.data_dir / "about.json").read_bytes()

    publisher = FilesystemPublisher()
    with pytest.raises(UnsafeDestinationError, match="destination"):
        publisher.plan(project, {"destination": destination})

    assert (project.data_dir / "about.json").read_bytes() == canonical
    assert not project.output_dir.exists()


def test_a_custom_data_dir_is_protected_wherever_it_lives(tmp_path: Path) -> None:
    """Protection follows the context's data dir, not the literal name ``data``."""
    data_dir = tmp_path / "profile"
    data_dir.mkdir()
    for filename, payload in CANONICAL.items():
        (data_dir / filename).write_text(json.dumps(payload), encoding="utf-8")
    ctx = ProjectContext.for_root(tmp_path, data_dir=data_dir)

    with pytest.raises(UnsafeDestinationError, match="profile"):
        FilesystemPublisher().plan(ctx, {"destination": "profile"})


# ---------------------------------------------------------------------------
# plan() is read-only; publish() is the only thing that writes
# ---------------------------------------------------------------------------


def test_plan_writes_nothing(project: ProjectContext) -> None:
    """Dry-run is the default, so plan() must never touch the destination."""
    publisher = FilesystemPublisher()
    plan = publisher.plan(project, {"destination": "apps/portfolio/app/data"})

    assert plan.capability == "push"
    assert not _destinations_written(project.root)


def test_publish_writes_the_four_app_data_files(project: ProjectContext) -> None:
    publisher = FilesystemPublisher()
    cfg = {"destination": "apps/portfolio/app/data"}
    result = publisher.publish(project, publisher.plan(project, cfg))

    destination = project.root / "apps" / "portfolio" / "app" / "data"
    written = sorted(p.name for p in destination.glob("*.json"))
    assert written == ["about.json", "projects.json", "skills.json", "social.json"]
    assert result.status == "published"


def test_publish_is_idempotent(project: ProjectContext) -> None:
    """Re-publishing identical content reports unchanged rather than rewriting."""
    publisher = FilesystemPublisher()
    cfg = {"destination": "apps/portfolio/app/data"}
    publisher.publish(project, publisher.plan(project, cfg))

    second = publisher.plan(project, cfg)
    assert second.changes == ()
    assert publisher.publish(project, second).status == "unchanged"


def test_plan_reports_drift_when_destination_is_stale(project: ProjectContext) -> None:
    publisher = FilesystemPublisher()
    cfg = {"destination": "apps/portfolio/app/data"}
    publisher.publish(project, publisher.plan(project, cfg))

    stale = project.root / "apps" / "portfolio" / "app" / "data" / "about.json"
    stale.write_text('{"username": "someone else"}\n', encoding="utf-8")

    assert publisher.plan(project, cfg).changes == ("about.json",)
