"""Behavior pinned down by mutation testing of ``profilekit.registry``.

A registry error is what a user sees when a third-party plugin is broken or
misregistered, so its message is the diagnosis. Each test kills mutants that
survived the baseline run (see ``docs/quality/mutation-baseline.md``).
"""

from __future__ import annotations

import pytest

from profilekit import registry
from profilekit.registry import GENERATOR_GROUP, RegistryError


class _BareEntryPoint:
    """An entry point exposing only ``name`` and ``load``, with no dist or value."""

    def __init__(self, name: str, loaded: object) -> None:
        self.name = name
        self._loaded = loaded

    def load(self) -> object:
        if isinstance(self._loaded, BaseException):
            raise self._loaded
        return self._loaded


def _install(monkeypatch: pytest.MonkeyPatch, *entry_points: object) -> None:
    monkeypatch.setattr(registry, "_entry_points_for", lambda group: list(entry_points))


def test_unknown_group_error_lists_the_known_groups() -> None:
    with pytest.raises(RegistryError) as excinfo:
        registry.names("profilekit.widgets")

    assert str(excinfo.value) == (
        "unknown component group 'profilekit.widgets'; known groups are: "
        "profilekit.generators, profilekit.publishers"
    )


def test_duplicate_without_metadata_still_reports_both_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        monkeypatch,
        _BareEntryPoint("readme", lambda ctx: None),
        _BareEntryPoint("readme", lambda ctx: None),
    )

    with pytest.raises(RegistryError) as excinfo:
        registry.names(GENERATOR_GROUP)

    assert str(excinfo.value) == (
        "component 'readme' in group 'profilekit.generators' is registered twice: "
        "by module '<unknown>' and by module '<unknown>'"
    )


def test_a_non_callable_component_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _BareEntryPoint("readme", "not callable"))

    with pytest.raises(RegistryError) as excinfo:
        registry.component(GENERATOR_GROUP, "readme")

    assert str(excinfo.value) == (
        "component 'readme' in group 'profilekit.generators' is not callable"
    )


def test_loading_every_component_names_the_group_of_a_broken_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, _BareEntryPoint("readme", ImportError("no module named yaml")))

    with pytest.raises(RegistryError) as excinfo:
        registry.generators()

    assert str(excinfo.value) == (
        "component 'readme' in group 'profilekit.generators' failed to load: no module named yaml"
    )
