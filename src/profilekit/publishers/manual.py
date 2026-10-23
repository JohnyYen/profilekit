"""The ``manual`` publisher — for destinations with no write path.

Some platforms expose no programmatic way to update what you want to update.
LinkedIn is the example this project was built around: it offers no write
access to profile fields — headline, about, experience — without
partner-level API approval.

The honest response is not to pretend. A ``manual`` destination emits its
artifact, reports ``pending-manual``, and tells the operator exactly what is
left to do. It never reports ``published``.

That distinction matters more than it looks. A publish layer that reports
success for work it did not perform is worse than one that cannot publish at
all: the operator stops checking, the profile silently goes stale, and nobody
finds out until someone reads the outdated page. Capability is declared by the
kind, not by configuration, so this cannot be switched off by a project that
wishes otherwise.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from profilekit.config import ConfigError
from profilekit.context import ProjectContext
from profilekit.publishers import (
    Artifact,
    Capability,
    PublishPlan,
    PublishResult,
)


class ManualPublisher:
    """Emits artifacts for a destination a human has to update by hand."""

    kind: str = "manual"
    capability: Capability = "manual"
    reads_destination: bool = False

    def plan(self, ctx: ProjectContext, cfg: Mapping[str, object]) -> PublishPlan:
        """Collect the artifacts a human will need, from the output directory."""
        names = _artifact_names(cfg, destination=str(cfg.get("destination", "manual")))
        artifacts: list[Artifact] = []
        missing: list[str] = []

        for name in names:
            path = ctx.output_dir / name
            if path.is_file():
                artifacts.append(Artifact(name, path.read_text(encoding="utf-8")))
            else:
                missing.append(name)

        if missing:
            raise FileNotFoundError(
                f"manual destination lists artifacts that have not been generated: "
                f"{', '.join(missing)}"
            )

        return PublishPlan(
            destination=str(cfg.get("destination", "manual")),
            capability=self.capability,
            resolved_path=ctx.output_dir,
            artifacts=tuple(artifacts),
            # Always "changed": there is no way to read the remote side, so
            # claiming it is current would be a guess.
            changes=tuple(a.name for a in artifacts),
        )

    def publish(self, ctx: ProjectContext, plan: PublishPlan) -> PublishResult:
        """Report the pending action. Never reports a publish that did not happen."""
        names = ", ".join(artifact.name for artifact in plan.artifacts)
        return PublishResult(
            destination=plan.destination,
            status="pending-manual",
            detail=f"{plan.destination} has no write API available to this tool",
            action_required=(
                f"copy {names} from {plan.resolved_path} into {plan.destination} by hand"
            ),
        )


def validate_artifacts(cfg: Mapping[str, object], *, destination: str) -> None:
    """Check the shape of a manual destination's ``artifacts`` declaration.

    Shape only: whether the files were generated is checked when planning. A
    string or a list holding a non-string used to be read as "no artifacts",
    and the destination then asked a human to copy nothing. Raises
    :class:`ConfigError` naming the destination and the offending field.
    """
    if "artifacts" not in cfg:
        return
    declared = cfg["artifacts"]
    if not isinstance(declared, list):
        raise ConfigError(
            f"destination {destination!r}: artifacts must be a list of file names, "
            f"got {type(declared).__name__}"
        )
    for index, item in enumerate(declared):
        if not isinstance(item, str):
            raise ConfigError(
                f"destination {destination!r}: artifacts[{index}] must be a file name, "
                f"got {type(item).__name__}"
            )


def _artifact_names(cfg: Mapping[str, object], *, destination: str) -> Sequence[str]:
    validate_artifacts(cfg, destination=destination)
    declared = cfg.get("artifacts")
    return tuple(declared) if isinstance(declared, list) else ()


def publish_entry_point(
    ctx: ProjectContext,
    cfg: Mapping[str, object] | None = None,
    credentials: Mapping[str, object] | None = None,
) -> PublishResult:
    """Registry entry point: plan, then report the pending action.

    Registered as the ``linkedin`` publisher. profilekit itself never calls
    it: ``publish._load_publisher`` maps this entry point to
    :class:`ManualPublisher` so the destination keeps its ``manual``
    capability. It stays callable for code outside the package that loads the
    entry point directly.
    """
    publisher = ManualPublisher()
    return publisher.publish(ctx, publisher.plan(ctx, cfg or {}))


__all__ = ["ManualPublisher", "publish_entry_point"]
