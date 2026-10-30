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
#: ``would-publish`` is a dry run of a push destination: it would write on
#: ``--execute``. ``skipped`` is reserved for a destination that cannot publish
#: on this machine (a missing credential), so the two never share a label.
#: What publishing does with a destination file edited outside profilekit.
OnConflict = Literal["refuse", "overwrite"]
Status = Literal["published", "unchanged", "would-publish", "pending-manual", "skipped", "failed"]

# Credentials are injected by the core, never read from os.environ by a
# publisher. The filesystem publisher needs none; the mapping stays empty.
CredentialSet = Mapping[str, str]


@dataclass(frozen=True)
class Artifact:
    """One unit of content bound for a destination.

    ``content`` is text. A publisher that carries a file which is not text —
    an image in another repository — sets ``data`` to its raw bytes instead and
    leaves ``content`` empty. :meth:`encoded` is what gets written and digested
    either way, and for text it is exactly ``content`` as UTF-8, so digests of
    text artifacts do not depend on which field held them.
    """

    name: str
    content: str
    data: bytes | None = None

    def encoded(self) -> bytes:
        """Return the bytes this artifact stands for."""
        return self.data if self.data is not None else self.content.encode("utf-8")


@dataclass(frozen=True)
class PublishPlan:
    """What a publisher would do, computed without doing it.

    ``changes`` lists the artifact names whose destination content differs from
    what would be written. An empty ``changes`` means the destination is already
    current and ``publish()`` has nothing to do.

    ``remote_digest`` identifies the destination state the plan was computed
    against, when the publisher has one (a commit, for a git repository).
    """

    destination: str
    capability: Capability
    resolved_path: Path
    artifacts: Sequence[Artifact] = field(default_factory=tuple)
    changes: Sequence[str] = field(default_factory=tuple)
    remote_digest: str | None = None
    #: What the destination holds now, per artifact name: the SHA-256 of its
    #: bytes, or ``None`` when the artifact does not exist there yet. A
    #: publisher that can read its destination sets it to opt in to the core's
    #: manual-edit guard; ``None`` leaves the guard off.
    destination_digests: Mapping[str, str | None] | None = None
    #: What each artifact becomes at the destination once published, as a
    #: SHA-256, when the destination transforms content on write (git's
    #: line-ending normalisation, a clean filter). The core records these in
    #: the ledger so a later comparison with ``destination_digests`` is like
    #: with like. ``None``, or a missing name, means the artifact's own bytes.
    published_digests: Mapping[str, str] | None = None
    #: What the guard does with a destination file edited outside profilekit
    #: since it was last published: ``refuse`` the publish, or ``overwrite``.
    on_conflict: OnConflict = "refuse"


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

    #: Whether ``plan()`` can read the destination's current state.
    #:
    #: True for a local directory. False for anything this tool cannot
    #: inspect — a platform with no read API, or a human-updated page. The
    #: distinction decides which staleness signal is authoritative: a
    #: publisher that can read back trusts its own plan, and one that cannot
    #: falls back to the local ledger of what it last published.
    reads_destination: bool

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
    "OnConflict",
    "PublishPlan",
    "PublishResult",
    "Publisher",
    "ProjectContext",
    "Status",
]
