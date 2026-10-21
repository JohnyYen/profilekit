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
from profilekit.manifest import SCHEMA_VERSION
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


def test_rejects_a_symlinked_artifact_pointing_outside_the_root(
    project: ProjectContext, tmp_path: Path
) -> None:
    """A safe destination directory can still hold a symlink planted per file."""
    outside = tmp_path.parent / f"outside-{tmp_path.name}.json"
    outside.write_text("untouched\n", encoding="utf-8")
    destination = project.root / "site"
    destination.mkdir()
    (destination / "about.json").symlink_to(outside)

    publisher = FilesystemPublisher()
    with pytest.raises(UnsafeDestinationError, match="about.json"):
        publisher.plan(project, {"destination": "site"})
    assert outside.read_text(encoding="utf-8") == "untouched\n"


def test_rejects_a_symlinked_artifact_pointing_at_canonical_data(
    project: ProjectContext,
) -> None:
    """A symlink that stays inside the root is still refused: it leaves the destination."""
    canonical = (project.data_dir / "about.json").read_bytes()
    destination = project.root / "site"
    destination.mkdir()
    (destination / "about.json").symlink_to(project.data_dir / "about.json")

    publisher = FilesystemPublisher()
    with pytest.raises(UnsafeDestinationError, match="about.json"):
        publisher.plan(project, {"destination": "site"})
    assert (project.data_dir / "about.json").read_bytes() == canonical


def test_publish_rechecks_every_artifact_before_the_first_write(
    project: ProjectContext, tmp_path: Path
) -> None:
    """A symlink planted between plan() and publish() fails the whole destination.

    ``projects.json`` is written last, so checking per write would already have
    written the other three files; nothing may be written at all.
    """
    outside = tmp_path.parent / f"outside-{tmp_path.name}.json"
    outside.write_text("untouched\n", encoding="utf-8")
    publisher = FilesystemPublisher()
    plan = publisher.plan(project, {"destination": "site"})
    assert "projects.json" in plan.changes

    destination = project.root / "site"
    destination.mkdir()
    (destination / "projects.json").symlink_to(outside)

    with pytest.raises(UnsafeDestinationError, match="projects.json"):
        publisher.publish(project, plan)
    assert outside.read_text(encoding="utf-8") == "untouched\n"
    assert sorted(p.name for p in destination.iterdir()) == ["projects.json"]


# ---------------------------------------------------------------------------
# plan() is read-only; publish() is the only thing that writes
# ---------------------------------------------------------------------------


def test_plan_writes_nothing(project: ProjectContext) -> None:
    """Dry-run is the default, so plan() must never touch the destination."""
    publisher = FilesystemPublisher()
    plan = publisher.plan(project, {"destination": "apps/portfolio/app/data"})

    assert plan.capability == "push"
    assert not _destinations_written(project.root)


def test_publish_writes_the_four_app_data_files_and_their_manifest(
    project: ProjectContext,
) -> None:
    publisher = FilesystemPublisher()
    cfg = {"destination": "apps/portfolio/app/data"}
    result = publisher.publish(project, publisher.plan(project, cfg))

    destination = project.root / "apps" / "portfolio" / "app" / "data"
    written = sorted(p.name for p in destination.glob("*.json"))
    assert written == [
        "about.json",
        "manifest.json",
        "projects.json",
        "skills.json",
        "social.json",
    ]
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


# ---------------------------------------------------------------------------
# The destination manifest — where an array-shaped file's version lives
# ---------------------------------------------------------------------------

PUBLISHED_FILES = ["about.json", "projects.json", "skills.json", "social.json"]


def _publish(project: ProjectContext, destination: str = "site") -> Path:
    publisher = FilesystemPublisher()
    publisher.publish(project, publisher.plan(project, {"destination": destination}))
    return project.root / destination


def test_the_destination_manifest_versions_every_published_file(
    project: ProjectContext,
) -> None:
    """``projects.json`` is an array: the destination manifest is its only version."""
    import hashlib

    destination = _publish(project)
    index = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))

    assert index["schemaVersion"] == SCHEMA_VERSION
    entries = {entry["name"]: entry for entry in index["files"]}
    assert sorted(entries) == PUBLISHED_FILES, "the manifest must not index itself"
    for name, entry in entries.items():
        raw = (destination / name).read_bytes()
        assert entry["schemaVersion"] == SCHEMA_VERSION
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest(), name
        assert entry["bytes"] == len(raw), name


def test_the_destination_manifest_is_byte_identical_across_destinations(
    project: ProjectContext,
) -> None:
    """No timestamp and sorted entries: identical data gives identical bytes."""
    first = (_publish(project, "one") / "manifest.json").read_bytes()
    second = (_publish(project, "two") / "manifest.json").read_bytes()

    assert first == second
    names = [entry["name"] for entry in json.loads(first)["files"]]
    assert names == sorted(names)


def test_a_missing_destination_manifest_is_drift(project: ProjectContext) -> None:
    """A destination published before the manifest existed must be republished."""
    destination = _publish(project)
    (destination / "manifest.json").unlink()

    assert FilesystemPublisher().plan(project, {"destination": "site"}).changes == (
        "manifest.json",
    )


def test_rejects_a_symlinked_destination_manifest(project: ProjectContext, tmp_path: Path) -> None:
    outside = tmp_path.parent / f"outside-{tmp_path.name}-manifest.json"
    outside.write_text("untouched\n", encoding="utf-8")
    destination = project.root / "site"
    destination.mkdir()
    (destination / "manifest.json").symlink_to(outside)

    with pytest.raises(UnsafeDestinationError, match="manifest.json"):
        FilesystemPublisher().plan(project, {"destination": "site"})
    assert outside.read_text(encoding="utf-8") == "untouched\n"


def test_publish_rechecks_the_manifest_before_the_first_write(
    project: ProjectContext, tmp_path: Path
) -> None:
    """A symlinked manifest planted after plan() stops every write, not just its own."""
    outside = tmp_path.parent / f"outside-{tmp_path.name}-manifest.json"
    outside.write_text("untouched\n", encoding="utf-8")
    publisher = FilesystemPublisher()
    plan = publisher.plan(project, {"destination": "site"})
    assert "manifest.json" in plan.changes

    destination = project.root / "site"
    destination.mkdir()
    (destination / "manifest.json").symlink_to(outside)

    with pytest.raises(UnsafeDestinationError, match="manifest.json"):
        publisher.publish(project, plan)
    assert outside.read_text(encoding="utf-8") == "untouched\n"
    assert sorted(p.name for p in destination.iterdir()) == ["manifest.json"]
