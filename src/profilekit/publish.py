"""The publication layer — artifacts out to destinations.

Four properties shape this module, and each exists because the obvious
alternative is dangerous.

**Dry-run is the default.** ``plan()`` runs; ``publish()`` does not, unless
the caller passes ``--execute``. Publishing is outward-facing and not reliably
reversible — a pushed commit, a posted update, an overwritten file in someone
else's directory. Opting in to writing is cheap; discovering you wrote by
accident is not.

**Idempotency.** A publisher that can read its destination (a local
directory) reports what differs in ``plan().changes``; for one that cannot,
the plan's content digest is compared against a ledger of what was last
published. An unchanged destination reports ``unchanged`` and is not
written. Republishing identical content wastes a
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
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from profilekit import manifest, registry
from profilekit.context import ProjectContext
from profilekit.publishers import Capability, Publisher, PublishPlan, PublishResult, Status
from profilekit.safe_io import write_file
from profilekit.secrets import CredentialSet, MissingCredentialError, resolve
from profilekit.secrets import validate_declaration as validate_credentials

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


def ledger_path(ctx: ProjectContext) -> Path:
    """Return where the publish ledger lives for *ctx*."""
    return ctx.root / STATE_DIR / STATE_FILENAME


def read_state(ctx: ProjectContext) -> dict[str, str]:
    """Read the publish ledger: destination name to last-published digest.

    The ledger is local and gitignored. It records what *this machine* last
    published, which is the only thing it can honestly know — a shared ledger
    would claim knowledge of other people's runs.
    """
    path = ledger_path(ctx)
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        # A corrupt or unreadable ledger must not block publishing. The worst
        # case is one redundant publish, which is strictly better than
        # refusing to run. ValueError covers both JSONDecodeError and
        # UnicodeDecodeError. Said out loud, so a ledger that stays broken —
        # and republishes every run — does not go unnoticed.
        print(
            f"warning: ignoring unreadable publish ledger {path}: {exc} — "
            "every destination is treated as changed",
            file=sys.stderr,
        )
        return {}
    return {str(k): str(v) for k, v in loaded.items()} if isinstance(loaded, dict) else {}


def write_state(ctx: ProjectContext, state: Mapping[str, str]) -> Path:
    """Persist the publish ledger atomically.

    :func:`profilekit.safe_io.write_file` replaces the ledger through a
    temporary file in its own directory and one ``os.replace``, so an
    interrupted write leaves the previous ledger intact rather than a
    truncated one.

    Raises ``OSError`` when the ledger cannot be written; the temporary file
    is removed first.
    """
    path = ledger_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(sorted(state.items())), indent=2) + "\n"
    return write_file(path, payload, root=path.parent, overwrite=True)


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

    A missing credential and an unchanged or dry-run destination come back as
    a result, not an exception. Anything else can raise: an unknown or broken
    publisher kind (``_load_publisher``), and whatever the publisher's own
    ``plan()`` or ``publish()`` raises. The caller wraps each call in its own
    ``try/except`` so one destination's failure cannot hide the others.
    """
    publisher = _load_publisher(destination)

    try:
        credentials = resolve(destination.config, destination=destination.name)
    except MissingCredentialError as exc:
        status: Status = "failed" if require_credentials else "skipped"
        return PublishResult(
            destination=destination.name,
            status=status,
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
    # The core injects credentials onto every publisher. `Publisher` does not
    # declare the attribute because the built-in kinds need none, so the
    # assignment is outside the protocol by design.
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
            status="pending-manual" if plan.capability == "manual" else "would-publish",
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


def validate_declaration(destination: Destination) -> None:
    """Shape-check one destination's configuration before anything publishes.

    Raises :class:`~profilekit.config.ConfigError` for a malformed credential
    declaration or, on a manual destination, a malformed ``artifacts`` list.
    A destination whose publisher cannot be resolved is left alone here: that
    is reported for it alone when it runs, without stopping the others.
    """
    from profilekit.publishers.manual import ManualPublisher, validate_artifacts

    validate_credentials(destination.config, destination=destination.name)
    try:
        publisher = _load_publisher(destination)
    except registry.RegistryError:
        return
    if isinstance(publisher, ManualPublisher):
        validate_artifacts(destination.config, destination=destination.name)


def _load_publisher(destination: Destination) -> Publisher:
    """Return the publisher implementation for a destination's kind."""
    from profilekit.publishers.filesystem import FilesystemPublisher
    from profilekit.publishers.manual import ManualPublisher

    builtin: dict[str, Callable[[], Publisher]] = {
        "filesystem": FilesystemPublisher,
        "manual": ManualPublisher,
    }
    if destination.kind in builtin:
        _refuse_a_shadowed_plugin(destination)
        return builtin[destination.kind]()

    # An out-of-tree adapter registers itself as a publisher entry point. Its
    # kind is its registered name. Only that one is imported, so an unrelated
    # broken plugin cannot fail this destination.
    if destination.kind in registry.names(registry.PUBLISHER_GROUP):
        adapter = registry.component(registry.PUBLISHER_GROUP, destination.kind)
        # The package registers its own publishers as entry points too. Those
        # resolve to their native classes: the generic wrapper would label a
        # manual destination `push` and report a write only a human can make.
        native = _native_publishers().get(adapter)
        if native is not None:
            return native()
        return _AdapterPublisher(adapter, destination.kind)

    raise registry.RegistryError(
        f"destination {destination.name!r} declares unknown kind {destination.kind!r}; "
        f"built-in kinds are: {', '.join(sorted(builtin))}"
    )


#: The distribution allowed to register publisher entry points named after
#: a built-in kind: the package itself.
_OWN_DISTRIBUTION = "profilekit"


def _refuse_a_shadowed_plugin(destination: Destination) -> None:
    """Fail when a third-party plugin registers a built-in kind's name.

    The built-in used to win without a word, so the plugin never ran and
    nothing said which implementation a destination actually used. The
    ambiguity is the operator's to resolve, so it is refused, not guessed.
    Only names are read: the plugin is never imported.
    """
    group = registry.PUBLISHER_GROUP
    if destination.kind not in registry.names(group):
        return
    if registry.distribution(group, destination.kind) == _OWN_DISTRIBUTION:
        return
    raise registry.RegistryError(
        f"destination {destination.name!r} declares kind {destination.kind!r}, which is "
        f"both a built-in publisher and a plugin registered by "
        f"{registry.provenance(group, destination.kind)}; rename the plugin's entry point "
        f"or uninstall it"
    )


def _native_publishers() -> dict[Callable[..., Any], Callable[[], Publisher]]:
    """Map the package's own publisher entry points to their classes."""
    from profilekit.publishers import filesystem, manual

    return {
        filesystem.publish_entry_point: filesystem.FilesystemPublisher,
        manual.publish_entry_point: manual.ManualPublisher,
    }


class _AdapterPublisher:
    """Wraps a registered entry point in the two-phase publisher protocol."""

    def __init__(self, entry_point: Callable[..., PublishResult], kind: str) -> None:
        self._entry_point = entry_point
        self.kind = kind
        self.capability: Capability = "push"
        # An out-of-tree adapter is assumed unable to read its destination.
        # Guessing the other way would skip republishes it actually needs.
        self.reads_destination = False
        self.credentials: CredentialSet = CredentialSet({})
        self._cfg: Mapping[str, object] = {}

    def plan(self, ctx: ProjectContext, cfg: Mapping[str, object]) -> PublishPlan:
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

    def publish(self, ctx: ProjectContext, plan: PublishPlan) -> PublishResult:
        """Invoke the entry point, passing what its signature actually names.

        Widening the call from ``(ctx)`` to ``(ctx, cfg, credentials)`` is a
        contract change for anything already written to the narrower form, so
        the extras are passed **by keyword** and only when the callable
        declares them.

        Counting positional parameters — the obvious approach, and the one
        tried first — is wrong in both directions. An adapter written as
        ``def push(ctx, timeout=30)`` counts as two positionals and would have
        received the config mapping in its ``timeout`` slot: wrong data,
        silently. One written as ``def push(ctx, *, cfg=None)`` counts as one
        and would never have received the config at all. Keyword passing has
        neither failure: a parameter named ``timeout`` cannot be mistaken for
        ``cfg``.

        A genuine mismatch still raises, and ``cmd_publish`` records it as
        this destination's own failure rather than aborting the run — the
        per-destination isolation holds.
        """
        import inspect

        extras: dict[str, Any] = {"cfg": self._cfg, "credentials": self.credentials}

        try:
            parameters = inspect.signature(self._entry_point).parameters
        except (TypeError, ValueError):
            # A builtin or C-implemented callable exposes no signature. Assume
            # the current contract; a mismatch surfaces as this destination's
            # failure, which is caught per destination.
            return self._entry_point(ctx, **extras)

        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
            accepted = extras
        else:
            accepted = {
                name: value
                for name, value in extras.items()
                if name in parameters
                and parameters[name].kind is not inspect.Parameter.POSITIONAL_ONLY
            }

        return self._entry_point(ctx, **accepted)


__all__ = [
    "STATE_FILENAME",
    "Destination",
    "destinations",
    "ledger_path",
    "plan_digest",
    "publish_destination",
    "read_state",
    "write_state",
]
