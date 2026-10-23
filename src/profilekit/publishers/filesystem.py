"""Filesystem publisher — canonical data to a directory inside the project.

This is the publisher that carries canonical profile data into a frontend's
data directory. The in-repo portfolio app under ``apps/portfolio/app/data/`` is
one such destination, and the reference one, but the destination is
configuration: any consumer that reads the same four JSON shapes is a valid
target.

It needs no credentials and no network, which is why it ships in the package
rather than as an opt-in adapter.

Security note: the destination is the one value here that an edit to project
configuration can turn into an arbitrary-write primitive. It is resolved
against ``ctx.root`` and rejected *before* any content is produced — absolute
paths, parent-directory escapes, and symlinks pointing out of the project all
fail closed. Each artifact file is checked too, before it is read or written:
a symlink planted at ``<destination>/about.json`` is refused rather than
followed. So do destinations that would overwrite the project's own
inputs or outputs: the root itself, and anything at or inside the canonical
data directory or the generated output directory.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path

from profilekit.manifest import MANIFEST_FILENAME, build_published, stamp
from profilekit.publishers import (
    Artifact,
    Capability,
    ProjectContext,
    PublishPlan,
    PublishResult,
)
from profilekit.utils import load_json

DEFAULT_DESTINATION = "apps/portfolio/app/data"

_ABOUT_KEYS = (
    "username",
    "tagline",
    "description",
    "currentFocus",
    "whatIBuild",
    "learningJourney",
)


class UnsafeDestinationError(ValueError):
    """Raised when a configured destination is outside the project or overlaps it.

    Overlap means the project root itself, or a protected directory (canonical
    data, generated output) or anything inside one.
    """


def resolve_destination(root: Path, destination: str, protected: Iterable[Path] = ()) -> Path:
    """Resolve *destination* against *root*, refusing anything unsafe to write into.

    Rejects absolute paths and any relative path that — after following
    symlinks — lands outside *root*. Resolution happens first so that a
    symlinked directory inside the project cannot be used as a tunnel.

    It also rejects *root* itself and any path at or inside one of the
    *protected* directories: publishing there would overwrite the canonical
    data the artifacts are built from, or the generated output.
    """
    candidate = Path(destination)
    if candidate.is_absolute():
        raise UnsafeDestinationError(
            f"destination must be relative to the project root, got absolute path: {destination}"
        )

    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()

    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise UnsafeDestinationError(
            f"destination escapes the project root: {destination} -> {resolved}"
        )
    if resolved == resolved_root:
        raise UnsafeDestinationError(
            f"destination is the project root itself: {destination!r} -> {resolved}"
        )
    for directory in protected:
        guarded = directory.resolve()
        if resolved == guarded or guarded in resolved.parents:
            raise UnsafeDestinationError(
                f"destination would overwrite a project directory: {destination} -> "
                f"{resolved} is at or inside {guarded}"
            )
    return resolved


def artifact_path(directory: Path, name: str) -> Path:
    """Return the path of artifact *name* in *directory*, refusing a redirected file.

    *directory* is an already-resolved destination, compared as-is: if it has
    since been replaced by a symlink, its artifacts no longer resolve inside it
    and are refused. Reading or writing follows symlinks, so a symlink at the
    artifact path — wherever it points — is refused too.
    """
    path = directory / name
    if path.is_symlink():
        raise UnsafeDestinationError(f"artifact is a symlink, refusing to follow it: {path}")
    if path.resolve().parent != directory:
        raise UnsafeDestinationError(
            f"artifact resolves outside the destination: {path} -> {path.resolve()}"
        )
    return path


def build_about(about: Mapping[str, object]) -> dict[str, object]:
    """Return the 6-key subset of canonical about data consumed by a frontend."""
    return {key: about[key] for key in _ABOUT_KEYS}


def build_social(social: Mapping[str, object]) -> dict[str, object]:
    """Return a full passthrough copy of canonical social data."""
    return dict(social)


def build_skills(skills: Mapping[str, object]) -> dict[str, object]:
    """Return a full passthrough copy of canonical skills data."""
    return dict(skills)


def build_projects(projects: list[Mapping[str, object]]) -> list[dict[str, object]]:
    """Map canonical projects to a frontend's GitHub-fallback shape.

    Each entry is reduced to ``{name, description, tech, url}``; optional fields
    default to ``""`` when absent. Canonical-only fields (``start_date``,
    ``end_date``, ``highlights``) are dropped. Source order is preserved.
    """
    return [
        {
            "name": project["name"],
            "description": project.get("description", ""),
            "tech": project.get("tech", ""),
            "url": project.get("url", ""),
        }
        for project in projects
    ]


def _serialize(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_artifacts(ctx: ProjectContext) -> list[Artifact]:
    """Transform canonical data into the four JSON artifacts a frontend reads.

    A fifth, ``manifest.json``, indexes the four with their contract version
    and digest.
    """
    about = load_json("about.json", ctx.data_dir)
    social = load_json("social.json", ctx.data_dir)
    skills = load_json("skills.json", ctx.data_dir)
    projects = load_json("projects.json", ctx.data_dir)

    # Every published JSON object declares the contract version it satisfies,
    # so a consumer knows the shape it is reading without consulting the
    # manifest. `projects.json` is an array — a list has nowhere to put a
    # top-level field — so its version lives in the destination manifest,
    # written beside it and built from exactly these contents.
    artifacts = [
        Artifact("about.json", _serialize(stamp(build_about(about)))),
        Artifact("social.json", _serialize(stamp(build_social(social)))),
        Artifact("skills.json", _serialize(stamp(build_skills(skills)))),
        Artifact("projects.json", _serialize(build_projects(projects))),
    ]
    # Last, so a write that fails part-way never leaves a manifest vouching
    # for files that were not written.
    index = build_published((artifact.name, artifact.content) for artifact in artifacts)
    return [*artifacts, Artifact(MANIFEST_FILENAME, _serialize(index))]


class FilesystemPublisher:
    """Writes canonical profile data into a directory inside the project."""

    kind: str = "filesystem"
    capability: Capability = "push"
    reads_destination: bool = True

    def plan(self, ctx: ProjectContext, cfg: Mapping[str, object]) -> PublishPlan:
        """Compute the artifacts and the drift against the destination.

        Writes nothing. Path safety is enforced here, before any content is
        produced, so an unsafe destination cannot reach ``publish()`` at all.
        """
        destination = str(cfg.get("destination", DEFAULT_DESTINATION))
        resolved = resolve_destination(
            ctx.root, destination, protected=(ctx.data_dir, ctx.output_dir)
        )

        artifacts = build_artifacts(ctx)
        changes = [
            artifact.name
            for artifact in artifacts
            if self._differs(artifact_path(resolved, artifact.name), artifact.content)
        ]

        return PublishPlan(
            destination=destination,
            capability=self.capability,
            resolved_path=resolved,
            artifacts=tuple(artifacts),
            changes=tuple(changes),
        )

    def publish(self, ctx: ProjectContext, plan: PublishPlan) -> PublishResult:
        """Write every changed artifact into the planned destination."""
        if not plan.changes:
            return PublishResult(
                destination=plan.destination,
                status="unchanged",
                detail="destination already matches canonical data",
            )

        plan.resolved_path.mkdir(parents=True, exist_ok=True)
        # Re-check every target before the first write: the destination may
        # have changed since plan(), and a failure part-way through would
        # leave a partially published destination behind.
        targets = [
            (artifact_path(plan.resolved_path, artifact.name), artifact.content)
            for artifact in plan.artifacts
            if artifact.name in plan.changes
        ]
        for path, content in targets:
            # Bytes, not text: text mode would translate newlines on Windows
            # and every digest in the destination manifest would be wrong.
            path.write_bytes(content.encode("utf-8"))

        written = ", ".join(plan.changes)
        return PublishResult(
            destination=plan.destination,
            status="published",
            detail=f"wrote {len(plan.changes)} file(s) to {plan.destination}: {written}",
        )

    @staticmethod
    def _differs(path: Path, content: str) -> bool:
        if not path.is_file():
            return True
        # Compared as bytes, matching what publish() writes and what the
        # destination manifest's digests describe.
        return hashlib.sha256(path.read_bytes()).hexdigest() != _digest(content)


def publish_entry_point(
    ctx: ProjectContext,
    cfg: Mapping[str, object] | None = None,
    credentials: Mapping[str, object] | None = None,
) -> PublishResult:
    """Registry entry point: plan and publish in one call.

    The registry hands every component a uniform callable. Publishers keep
    their two-phase protocol internally — a plan is still computed before
    anything is written — but the registered surface is a single function so
    the loader does not need to know about kinds beyond its group.

    Registered as the ``portfolio-data`` publisher. profilekit itself never
    calls it: ``publish._load_publisher`` maps this entry point to
    :class:`FilesystemPublisher` so the destination keeps its native
    capability and staleness signal. It stays callable for code outside the
    package that loads the entry point directly.
    """
    publisher = FilesystemPublisher()
    return publisher.publish(ctx, publisher.plan(ctx, cfg or {}))
