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
        names = _artifact_names(cfg)
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


def _artifact_names(cfg: Mapping[str, object]) -> Sequence[str]:
    declared = cfg.get("artifacts")
    if isinstance(declared, list) and all(isinstance(item, str) for item in declared):
        return tuple(declared)
    return ()


def publish_entry_point(
    ctx: ProjectContext, cfg: Mapping[str, object] | None = None
) -> PublishResult:
    """Registry entry point: plan, then report the pending action."""
    publisher = ManualPublisher()
    return publisher.publish(ctx, publisher.plan(ctx, cfg or {}))


__all__ = ["ManualPublisher", "publish_entry_point"]
