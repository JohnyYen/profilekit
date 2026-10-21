"""Component discovery — one enumeration source, resolved by entry point.

This module exists because of a defect that shipped. ``cli.py`` held a dict of
generation targets, commented as the "single source of truth", while
``generate_all.py`` kept a parallel list. They diverged:
``profile generate all`` silently skipped the portfolio data sync that
``generate_all`` ran, the README documented behavior that did not happen, and
CI's freshness gate never caught it because it drove the path missing the
step.

Two hardcoded lists cannot be kept in sync by discipline. So there is one
enumeration source, and adding a component is a registration rather than an
edit to this package:

```toml
[project.entry-points."profilekit.generators"]
my-target = "my_package.my_module:main"
```

Kinds are enforced rather than advisory, through separate entry-point groups.
``generate`` resolves only ``profilekit.generators`` and ``publish`` only
``profilekit.publishers``, so a component that writes outside the output
directory cannot be reached from the generate path at all. That is the
structural half of the generator/publisher boundary; the other half is the
test asserting no generator writes outside its output directory.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from importlib import metadata
from typing import Any, cast

GENERATOR_GROUP = "profilekit.generators"
PUBLISHER_GROUP = "profilekit.publishers"

KNOWN_GROUPS = (GENERATOR_GROUP, PUBLISHER_GROUP)


class RegistryError(Exception):
    """Raised when a component cannot be discovered or loaded."""

    exit_code = 1


def _entry_points_for(group: str) -> Iterable[Any]:
    """Return the entry points registered under *group*.

    Isolated so tests can install a fake set without touching installed
    distribution metadata.
    """
    return metadata.entry_points(group=group)


def _provenance(entry_point: Any) -> str:
    """Say where *entry_point* came from: its distribution, else its module path."""
    dist = getattr(entry_point, "dist", None)
    dist_name = getattr(dist, "name", None)
    if dist_name:
        return f"distribution {dist_name!r}"
    return f"module {getattr(entry_point, 'value', '<unknown>')!r}"


def _discover(group: str) -> dict[str, Any]:
    """Return the entry points under *group* by name, without loading any.

    Sorted by name, so run order is deterministic — an unstable order would
    churn generated output between runs for no reason.

    Two distributions registering the same name is an error, not a choice.
    Keying a dict by name used to let the last one silently win, so one
    component vanished from every command with nothing said about it.
    """
    if group not in KNOWN_GROUPS:
        known = ", ".join(KNOWN_GROUPS)
        raise RegistryError(f"unknown component group {group!r}; known groups are: {known}")

    discovered: dict[str, Any] = {}
    for entry_point in sorted(_entry_points_for(group), key=lambda ep: ep.name):
        previous = discovered.get(entry_point.name)
        if previous is not None:
            raise RegistryError(
                f"component {entry_point.name!r} in group {group!r} is registered twice: "
                f"by {_provenance(previous)} and by {_provenance(entry_point)}"
            )
        discovered[entry_point.name] = entry_point
    return discovered


def _load(group: str, entry_point: Any) -> Callable[..., Any]:
    """Import one entry point, naming it if that fails.

    A third-party generator with a broken dependency should say which one it
    is, not surface an opaque traceback from inside the loader.
    """
    try:
        loaded = entry_point.load()
    except Exception as exc:  # noqa: BLE001 — name the culprit, then re-raise
        raise RegistryError(
            f"component {entry_point.name!r} in group {group!r} failed to load: {exc}"
        ) from exc

    if not callable(loaded):
        raise RegistryError(f"component {entry_point.name!r} in group {group!r} is not callable")
    return cast("Callable[..., Any]", loaded)


def components(group: str) -> dict[str, Callable[..., Any]]:
    """Load every component registered under *group*, keyed by name.

    Insertion order follows the sorted entry-point names. A component that
    fails to import is reported by name.
    """
    return {name: _load(group, ep) for name, ep in _discover(group).items()}


def generators() -> dict[str, Callable[..., Any]]:
    """Return the registered generators: data in, artifacts in the output dir."""
    return components(GENERATOR_GROUP)


def publishers() -> dict[str, Callable[..., Any]]:
    """Return the registered publishers: artifacts out to a destination."""
    return components(PUBLISHER_GROUP)


__all__ = [
    "GENERATOR_GROUP",
    "KNOWN_GROUPS",
    "PUBLISHER_GROUP",
    "RegistryError",
    "components",
    "generators",
    "publishers",
]
