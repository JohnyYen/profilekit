"""The generator/publisher boundary, enforced structurally.

A *generator* transforms canonical data into artifacts and writes them to the
one output directory it was told about. Anything that writes to a destination
outside that directory is a *publisher*, and belongs behind
``profile publish`` with its own capability and credential model.

These tests exist because the boundary was previously violated in a way that
shipped: ``generate_portfolio_data`` wrote into ``apps/portfolio/app/data/``
from the generate path, on a hardcoded path that callers could not redirect.
"""

from pathlib import Path

import profilekit.generate_cv as cv
import profilekit.generate_github_readme as github_readme
import profilekit.generate_linkedin as linkedin
import profilekit.generate_portfolio as portfolio
from profilekit import registry

GENERATOR_MODULES = (github_readme, linkedin, portfolio, cv)


def _files_under(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def test_every_generator_accepts_an_explicit_output_dir() -> None:
    """Each generator's write destination must be caller-supplied, not fixed.

    A generator whose output path is a module constant cannot be redirected,
    which makes the boundary unenforceable and the generator untestable without
    monkeypatching private state.
    """
    for module in GENERATOR_MODULES:
        params = module.main.__code__.co_varnames[: module.main.__code__.co_argcount]
        assert "output_dir" in params, (
            f"{module.__name__}.main() must accept an explicit output_dir argument"
        )


def test_generators_write_only_inside_the_given_output_dir(tmp_path: Path) -> None:
    """Running every generator must leave no file outside the output directory.

    The sandbox root is wider than the output directory on purpose: any write
    that escapes lands in ``tmp_path`` but outside ``tmp_path/output``, and the
    assertion catches it.
    """
    output_dir = tmp_path / "output"

    for module in GENERATOR_MODULES:
        module.main(output_dir=output_dir)

    written = _files_under(tmp_path)
    assert written, "generators produced no files — the test proves nothing"

    escaped = [p for p in written if output_dir not in p.parents]
    assert not escaped, f"generators wrote outside the output directory: {escaped}"


def test_generate_path_contains_no_publishers() -> None:
    """``profile generate`` must not reach a destination-writing component.

    The registry is the only enumeration source for the generate path, so a
    publisher reachable from it is a boundary violation regardless of whether
    any individual generator behaves.
    """
    for name, entry in registry.generators().items():
        module_name = getattr(entry, "__module__", "")
        assert "publishers" not in module_name, (
            f"generate target {name!r} resolves to publisher module {module_name!r}"
        )

    assert set(registry.generators()).isdisjoint(registry.publishers())
