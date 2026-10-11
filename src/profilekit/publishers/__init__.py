"""Publisher protocol — artifact to destination.

A *generator* turns canonical data into artifacts and writes them inside the
output directory it was given. A *publisher* takes it from there and carries
content to a destination the project does not own: another directory, a remote
repository, a platform API.

The two differ in kind, not degree. A generator is pure, needs no network and
no credentials, and is golden-testable. A publisher has side effects outside
the project, so it declares what it is capable of, resolves credentials
explicitly, plans before it acts, and reports honestly when it cannot act at
all.

Capabilities are declared by the publisher kind, never by configuration:

``push``
    The destination can be written programmatically.
``manual``
    The destination has no write path available to this tool. Such a publisher
    emits its artifact and reports ``pending-manual`` with a non-null
    ``action_required``. It MUST NOT report ``published`` — reporting success
    for a publish that did not happen is worse than reporting nothing.

This module defines the contract. ``profile publish`` wiring, credential
injection, and the destination registry arrive with the publication layer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from profilekit.context import ProjectContext

Capability = Literal["push", "manual"]
Status = Literal["published", "unchanged", "pending-manual", "skipped", "failed"]

# Credentials are injected by the core, never read from os.environ by a
# publisher. The filesystem publisher needs none; the mapping stays empty.
CredentialSet = Mapping[str, str]


@dataclass(frozen=True)
class Artifact:
    """One unit of content bound for a destination."""

    name: str
    content: str


@dataclass(frozen=True)
class PublishPlan:
    """What a publisher would do, computed without doing it.

    ``changes`` lists the artifact names whose destination content differs from
    what would be written. An empty ``changes`` means the destination is already
    current and ``publish()`` has nothing to do.
    """

    destination: str
    capability: Capability
    resolved_path: Path
    artifacts: Sequence[Artifact] = field(default_factory=tuple)
    changes: Sequence[str] = field(default_factory=tuple)
    remote_digest: str | None = None


@dataclass(frozen=True)
class PublishResult:
    """What a publisher actually did.

    ``action_required`` is non-null only when a human has to finish the job —
    which is the whole point of the ``manual`` capability.
    """

    destination: str
    status: Status
    detail: str
    action_required: str | None = None


class Publisher(Protocol):
    """The contract every publisher satisfies."""

    kind: str
    capability: Capability

    def plan(self, ctx: ProjectContext, cfg: Mapping[str, object]) -> PublishPlan:
        """Compute what publishing would do. MUST NOT write anything."""
        ...

    def publish(self, ctx: ProjectContext, plan: PublishPlan) -> PublishResult:
        """Carry out *plan*. Only reached when the caller opted in to writing."""
        ...


__all__ = [
    "Artifact",
    "Capability",
    "CredentialSet",
    "PublishPlan",
    "PublishResult",
    "Publisher",
    "ProjectContext",
    "Status",
]
