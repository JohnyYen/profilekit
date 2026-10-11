"""The publication layer — artifacts out to destinations.

Four properties shape this module, and each exists because the obvious
alternative is dangerous.

**Dry-run is the default.** ``plan()`` runs; ``publish()`` does not, unless
the caller passes ``--execute``. Publishing is outward-facing and not reliably
reversible — a pushed commit, a posted update, an overwritten file in someone
else's directory. Opting in to writing is cheap; discovering you wrote by
accident is not.

**Idempotency.** ``plan()`` compares the current content digest against a
ledger of what was last published. An unchanged destination reports
``unchanged`` and is not written. Republishing identical content wastes a
round trip at best, and at worst makes a destination's history look busy when
nothing happened.

**Failure isolation.** Each destination runs inside its own ``try/except``.
One broken destination must not prevent the others from publishing: they are
independent, and aborting the run would turn one platform's outage into a
total failure. The exit code is non-zero if any destination failed, so CI
still notices.

**A core that needs no credentials.** The ``filesystem`` and ``manual`` kinds
require no token and no network, and they cover the destinations this project
actually has. A missing credential for some other destination is a ``skipped``
result and exit 0 by default — an absent secret is a configuration state, not
an error — and ``--require-credentials`` escalates it for CI, where a silently
skipped publish would be a problem.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from profilekit import manifest, registry
from profilekit.context import ProjectContext
from profilekit.publishers import PublishResult
from profilekit.secrets import CredentialSet, MissingCredentialError, resolve

STATE_DIR = ".profilekit"
STATE_FILENAME = "publish-state.json"


@dataclass(frozen=True)
class Destination:
    """One configured publish destination."""

    name: str
    kind: str
    config: Mapping[str, Any]


def destinations(ctx: ProjectContext) -> list[Destination]:
    """Return every destination declared by the project, in declaration order."""
    return [
        Destination(name=name, kind=str(cfg.get("kind", "")), config=cfg)
        for name, cfg in ctx.publisher_destinations().items()
    ]


def _state_path(ctx: ProjectContext) -> Path:
    return ctx.root / STATE_DIR / STATE_FILENAME


def read_state(ctx: ProjectContext) -> dict[str, str]:
    """Read the publish ledger: destination name to last-published digest.

    The ledger is local and gitignored. It records what *this machine* last
    published, which is the only thing it can honestly know — a shared ledger
    would claim knowledge of other people's runs.
    """
    path = _state_path(ctx)
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # A corrupt ledger must not block publishing. The worst case is one
        # redundant publish, which is strictly better than refusing to run.
        return {}
    return {str(k): str(v) for k, v in loaded.items()} if isinstance(loaded, dict) else {}


def write_state(ctx: ProjectContext, state: Mapping[str, str]) -> Path:
    """Persist the publish ledger."""
    path = _state_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(state.items())), indent=2) + "\n", encoding="utf-8")
    return path


def plan_digest(plan: Any) -> str | None:
    """Return a digest of everything a plan would write, or ``None``.

    Derived from artifact names and contents, so a reordering that changes
    nothing does not look like a change.

    ``None`` means the content is not knowable from the plan — an out-of-tree
    adapter manages its own payload and exposes no artifacts. Returning a
    digest of nothing would be far worse than returning nothing: the empty
    hash is constant, so after one publish the ledger would match forever and
    the destination would report ``unchanged`` no matter how much the data
    changed.
    """
    if not plan.artifacts:
        return None

    parts = []
    for artifact in sorted(plan.artifacts, key=lambda a: a.name):
        parts.append(artifact.name)
        parts.append(manifest.digest_text(artifact.content))
    return manifest.digest_text("\n".join(parts))


def publish_destination(
    ctx: ProjectContext,
    destination: Destination,
    *,
    execute: bool,
    state: dict[str, str],
    require_credentials: bool,
) -> PublishResult:
    """Plan, and conditionally publish, one destination.

    Returns a result rather than raising, so the caller can aggregate across
    destinations without one failure hiding the others.
    """
    publisher = _load_publisher(destination)

    try:
        credentials = resolve(destination.config, destination=destination.name)
    except MissingCredentialError as exc:
        status = "failed" if require_credentials else "skipped"
        return PublishResult(
            destination=destination.name,
            status=status,  # type: ignore[arg-type]
            detail=str(exc),
            action_required=(
                "set the declared environment variable, or drop --require-credentials"
                if require_credentials
                else None
            ),
        )

    # Label the plan with the declared name before anything reads it. A
    # publisher derives its destination from configuration, which may be a
    # path or absent entirely, so operator-facing text would otherwise name
    # something the project never declared.
    publisher.credentials = credentials  # type: ignore[attr-defined]
    plan = replace(publisher.plan(ctx, destination.config), destination=destination.name)
    digest = plan_digest(plan)

    # Which staleness signal is authoritative depends on whether the
    # publisher can see its destination.
    #
    # When it can — a local directory — `plan.changes` wins, and the ledger is
    # ignored. Consulting the ledger here would be a bug: a destination that
    # drifted after a successful publish still matches the ledger, so an
    # agreeing ledger would skip exactly the republish that is needed.
    #
    # When it cannot, there is nothing to compare against but the record of
    # what this machine last published.
    if getattr(publisher, "reads_destination", False):
        unchanged = not plan.changes
    elif digest is None:
        # No comparable content: publish every time. The failure modes are
        # asymmetric — a wrong skip looks like success and silently leaves the
        # destination stale, while a redundant publish is merely wasteful.
        unchanged = False
    else:
        unchanged = state.get(destination.name) == digest

    if unchanged:
        return PublishResult(
            destination=destination.name,
            status="unchanged",
            detail="destination already matches the current artifacts",
        )

    if not execute:
        changed = ", ".join(plan.changes) or "nothing"
        return PublishResult(
            destination=destination.name,
            status="pending-manual" if plan.capability == "manual" else "skipped",
            detail=f"dry run — would write: {changed}",
            action_required="re-run with --execute to publish",
        )

    result = publisher.publish(ctx, plan)
    if result.status == "published" and digest is not None:
        state[destination.name] = digest

    # The declared name is authoritative. A publisher derives its plan's
    # destination from configuration, which may be a path or absent entirely,
    # so results would otherwise be labelled inconsistently with the table
    # the operator is reading.
    return replace(result, destination=destination.name)


def _load_publisher(destination: Destination) -> Any:
    """Return the publisher implementation for a destination's kind."""
    from profilekit.publishers.filesystem import FilesystemPublisher
    from profilekit.publishers.manual import ManualPublisher

    builtin = {"filesystem": FilesystemPublisher, "manual": ManualPublisher}
    if destination.kind in builtin:
        return builtin[destination.kind]()

    # An out-of-tree adapter registers itself as a publisher entry point. Its
    # kind is its registered name.
    available = registry.publishers()
    if destination.kind in available:
        return _AdapterPublisher(available[destination.kind], destination.kind)

    raise registry.RegistryError(
        f"destination {destination.name!r} declares unknown kind {destination.kind!r}; "
        f"built-in kinds are: {', '.join(sorted(builtin))}"
    )


class _AdapterPublisher:
    """Wraps a registered entry point in the two-phase publisher protocol."""

    def __init__(self, entry_point: Any, kind: str) -> None:
        self._entry_point = entry_point
        self.kind = kind
        self.capability = "push"
        # An out-of-tree adapter is assumed unable to read its destination.
        # Guessing the other way would skip republishes it actually needs.
        self.reads_destination = False
        self.credentials: CredentialSet = CredentialSet({})
        self._cfg: Mapping[str, Any] = {}

    def plan(self, ctx: ProjectContext, cfg: Mapping[str, Any]) -> Any:
        from profilekit.publishers import PublishPlan

        self._cfg = cfg
        return PublishPlan(
            destination=str(cfg.get("destination", self.kind)),
            capability="push",
            resolved_path=ctx.root,
            # No artifacts: the adapter owns its payload, so `plan_digest`
            # returns None and this destination is never skipped on a stale
            # ledger entry.
            changes=("<adapter-managed>",),
        )

    def publish(self, ctx: ProjectContext, plan: Any) -> PublishResult:
        """Invoke the entry point with as much as its signature accepts.

        An earlier version called the entry point with the context alone, so a
        credentialed adapter received nothing it had declared and could only
        have worked by reading the environment itself — which is precisely
        what the credential model exists to prevent.

        Widening the call is a contract change for anything already written to
        the one-argument form, so the arity is inspected rather than assumed.
        Calling an older adapter with three arguments would raise an uncaught
        TypeError and abort the whole run, destroying the per-destination
        failure isolation this layer exists to provide.
        """
        import inspect

        try:
            parameters = inspect.signature(self._entry_point).parameters
        except (TypeError, ValueError):
            # A builtin or C-implemented callable exposes no signature. Assume
            # the current contract and let a genuine mismatch surface as this
            # destination's own failure.
            return self._entry_point(ctx, self._cfg, self.credentials)

        accepts_varargs = any(
            p.kind is inspect.Parameter.VAR_POSITIONAL for p in parameters.values()
        )
        positional = [
            p
            for p in parameters.values()
            if p.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]

        if accepts_varargs or len(positional) >= 3:
            return self._entry_point(ctx, self._cfg, self.credentials)
        if len(positional) == 2:
            return self._entry_point(ctx, self._cfg)
        return self._entry_point(ctx)


__all__ = [
    "STATE_FILENAME",
    "Destination",
    "destinations",
    "plan_digest",
    "publish_destination",
    "read_state",
    "write_state",
]
