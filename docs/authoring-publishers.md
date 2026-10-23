# Writing a publisher

A publisher carries generated artifacts somewhere the project does not own: a
directory outside it, a remote repository, a platform API.

That makes it the dangerous half of the pipeline. A generator writes one
directory and can be re-run freely; a publisher has side effects you cannot
take back. The protocol exists to make those effects deliberate.

## The contract

Two phases, always:

```python
from collections.abc import Mapping

from profilekit.context import ProjectContext
from profilekit.publishers import Artifact, Capability, PublishPlan, PublishResult


class MyPublisher:
    kind: str = "my-kind"
    capability: Capability = "push"
    reads_destination: bool = True

    def plan(self, ctx: ProjectContext, cfg: Mapping[str, object]) -> PublishPlan:
        """Compute what publishing would do. MUST NOT write anything."""

    def publish(self, ctx: ProjectContext, plan: PublishPlan) -> PublishResult:
        """Carry out the plan. Only reached when the caller opted in."""
```

`plan()` is called on every run. `publish()` is called only with
`--execute`. Dry run is the default because an accidental publish is the
mistake worth designing against.

**`plan()` must not write.** Not a temp file in the destination, not a
"harmless" marker. It runs when the user explicitly asked for nothing to
happen.

## Declaring capability

```python
capability: Capability = "push"  # the destination can be written
capability: Capability = "manual"  # no write path exists
```

A `manual` publisher returns `pending-manual` with a non-null
`action_required`, and **may never return `published`**.

In a dry run the core reports a `push` destination as `would-publish` and a
`manual` one as `pending-manual`, without calling `publish()`. `skipped` means
only that the destination cannot publish on this machine — a declared
credential is absent — so a dry run and a missing secret never share a label.

This is not a formality. A publish layer that reports success for work it did
not perform is worse than one that cannot publish at all: the operator stops
checking, the destination silently goes stale, and nobody finds out until
someone reads the outdated page. LinkedIn is the case this was built for — no
write access to profile fields without partner-level approval — so the honest
answer is to emit the artifact and say what is left to do.

Capability is declared by the kind, not by configuration, so a project cannot
override it.

## Declaring whether you can see your destination

```python
reads_destination: bool = True  # plan() can read the current state
reads_destination: bool = False  # it cannot
```

This decides which staleness signal is trusted. If you can read your
destination, `plan().changes` is authoritative. If you cannot, the core falls
back to a local ledger of what this machine last published.

Declare `False` when unsure. The failure modes are asymmetric: a wrong `True`
skips a republish that was needed, which looks like success. A wrong `False`
causes one redundant publish, which is merely wasteful.

> This was a real bug here. The core consulted the ledger for a publisher that
> could read its own destination, so a destination that drifted *after* a
> successful publish still matched the ledger and was reported unchanged —
> skipping exactly the republish that was needed.

## Credentials

Never read the environment. Declare what you need and receive it:

```toml
[publishers.my-dest]
kind = "my-kind"

[publishers.my-dest.credential]
token = "MY_SERVICE_TOKEN"
```

The core resolves those into a `CredentialSet` of `Secret` objects and injects
them. A `Secret`'s `repr`, `str`, and `__format__` are all redacted; reading
the value takes an explicit `.reveal()`.

That redaction is not paranoia about `print(token)` — nobody writes that on
purpose. It is about `repr()` on a dict during debugging, f-string
interpolation in a log line, and the automatic repr of local variables that
Python puts in a traceback. A token logged once in CI lives in that log far
longer than the token itself.

Reading `os.environ` directly would also make your access invisible: the point
of declaring credentials in configuration is that a user can audit what a
publisher can see.

A missing credential is `skipped` and exit 0 by default — an unset variable is
a configuration state, not a crash — and `--require-credentials` escalates it
to `failed` (exit 1) for CI.

A malformed declaration is different: a `credential` that is not a table, or an
entry whose value is not a non-empty variable name, is a configuration error.
`profile publish` refuses the whole run with exit 2 and names the destination
and the field, with or without `--require-credentials` — no environment could
make that destination publish, so reporting it as `skipped` would hide a broken
`profile.toml`.

## Idempotency

Compute a digest of what you would write and compare it. Republishing
identical content wastes a round trip at best; at worst it makes a
destination's history look busy when nothing happened.

Return `unchanged` rather than re-writing.

## Failing

Raise. The core wraps every destination in its own handler, records the
failure as `failed`, and continues to the next one — destinations are independent, and
aborting the run would turn one platform's outage into a total failure. The
exit code is non-zero if anything failed, so CI still notices.

Make the message name what went wrong and what to do. It will be read in a CI
log by someone without your context.

## Registering

```toml
[project.entry-points."profilekit.publishers"]
my-kind = "my_package.my_module:publish_entry_point"
```

```python
def publish_entry_point(ctx, cfg=None) -> PublishResult:
    publisher = MyPublisher()
    return publisher.publish(ctx, publisher.plan(ctx, cfg or {}))
```

The registry hands every component a uniform callable, so the two-phase
protocol stays internal to your implementation.

Do not name your entry point `filesystem` or `manual`: those kinds are
built in. A destination declaring a kind that is both built in and
registered by another distribution fails with an error naming both, rather
than silently using one of them.

## Path safety

If your destination is a filesystem path from configuration, it is an
arbitrary-write primitive until you constrain it. Resolve it against the
project root and reject what escapes — **before** producing any content:

```python
from profilekit.publishers.filesystem import resolve_destination

resolved = resolve_destination(ctx.root, cfg["destination"])
```

Resolve first, then validate. Checking the literal path before resolving it
lets a symlinked directory inside the project tunnel straight out.
