"""One registry, discovered by entry point — the end of the divergence bug.

This exists because of a defect that shipped. `cli.py` held a dict of
generation targets, commented as the "single source of truth", while
`generate_all.py` kept a parallel list. They diverged: `profile generate all`
silently skipped the portfolio data sync that `generate_all` ran, the README
documented the behavior that did not happen, and CI's freshness gate never
noticed because it drove the path that was missing the step.

Two hardcoded lists cannot be kept in sync by discipline. The fix is
structural: there is one enumeration source, and adding a component is a
registration rather than an edit to the core.

Kinds are enforced, not advisory. `generate` runs only generators and
`publish` runs only publishers, so a component that writes outside the output
directory cannot be reached from the generate path at all.
"""

from __future__ import annotations

import pytest

from profilekit import registry


class _FakeEntryPoint:
    """Stand-in for an importlib.metadata entry point."""

    def __init__(self, name: str, value: object, group: str) -> None:
        self.name = name
        self.group = group
        self._value = value

    def load(self) -> object:
        return self._value


def _noop(ctx: object) -> None:
    return None


@pytest.fixture
def fake_entry_points(monkeypatch: pytest.MonkeyPatch):
    """Install a fake entry-point set; returns a register-one callable."""
    installed: list[_FakeEntryPoint] = []

    def select(group: str) -> list[_FakeEntryPoint]:
        return [ep for ep in installed if ep.group == group]

    monkeypatch.setattr(registry, "_entry_points_for", select)

    def add(name: str, group: str, value: object = _noop) -> None:
        installed.append(_FakeEntryPoint(name, value, group))

    return add


# ---------------------------------------------------------------------------
# One source of truth
# ---------------------------------------------------------------------------


def test_generators_come_from_the_registry_only() -> None:
    """The real package must register its generators as entry points."""
    names = sorted(registry.generators())
    assert names == ["cv", "github-readme", "linkedin", "portfolio"]


def test_publishers_come_from_the_registry_only() -> None:
    assert "portfolio-data" in registry.publishers()


def test_no_module_keeps_a_parallel_list() -> None:
    """The structural guarantee: no second enumeration exists to drift.

    `cli.GENERATORS` and `generate_all`'s list were the two that diverged.
    Neither may come back.
    """
    from profilekit import cli

    assert not hasattr(cli, "GENERATORS"), (
        "cli must derive targets from the registry, not hold its own dict"
    )

    with pytest.raises(ImportError):
        import profilekit.generate_all  # noqa: F401


def test_new_component_needs_no_core_edit(fake_entry_points) -> None:
    """Registering a generator must be enough — no file in the core changes."""
    fake_entry_points("acme-site", registry.GENERATOR_GROUP)

    assert "acme-site" in registry.generators()


def test_new_publisher_needs_no_core_edit(fake_entry_points) -> None:
    fake_entry_points("acme-cdn", registry.PUBLISHER_GROUP)

    assert "acme-cdn" in registry.publishers()


# ---------------------------------------------------------------------------
# Kinds are enforced
# ---------------------------------------------------------------------------


def test_generate_excludes_publishers(fake_entry_points) -> None:
    """A publisher must be unreachable from the generate path."""
    fake_entry_points("a-generator", registry.GENERATOR_GROUP)
    fake_entry_points("a-publisher", registry.PUBLISHER_GROUP)

    assert "a-publisher" not in registry.generators()
    assert "a-generator" not in registry.publishers()


def test_unknown_kind_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unrecognised group name must fail loudly, not be silently invoked."""
    with pytest.raises(registry.RegistryError):
        registry.components("profilekit.not-a-real-group")


def test_a_component_that_fails_to_load_is_reported_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken third-party entry point must name itself, not crash opaquely."""

    class _Broken:
        name = "broken"
        group = registry.GENERATOR_GROUP

        def load(self):
            raise RuntimeError("bad import")

    monkeypatch.setattr(
        registry,
        "_entry_points_for",
        lambda group: [_Broken()] if group == registry.GENERATOR_GROUP else [],
    )

    with pytest.raises(registry.RegistryError) as exc_info:
        registry.generators()

    assert "broken" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Regression: the divergence cannot recur
# ---------------------------------------------------------------------------


def test_divergence_regression_generate_and_publish_share_one_source() -> None:
    """Both commands resolve from the same registry, for what each owns.

    The original bug was two enumerations answering the same question
    differently. With one source, the only way a component can be missing
    from a command is if it is not registered for that command's kind.
    """
    generators = registry.generators()
    publishers = registry.publishers()

    assert set(generators).isdisjoint(publishers), (
        "a component must be a generator or a publisher, never both"
    )
    assert "portfolio-data" in publishers
    assert "portfolio-data" not in generators


def test_registry_order_is_stable() -> None:
    """Run order must be deterministic, or output churns between runs."""
    assert list(registry.generators()) == list(registry.generators())
