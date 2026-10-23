"""The generator/publisher boundary, enforced structurally.

A *generator* transforms canonical data into artifacts and writes them to the
one output directory it was told about. Anything that writes to a destination
outside that directory is a *publisher*, and belongs behind
``profile publish`` with its own capability and credential model.

These tests exist because the boundary was previously violated in a way that
shipped: ``generate_portfolio_data`` wrote into ``apps/portfolio/app/data/``
from the generate path, on a hardcoded path that callers could not redirect.
"""

import hashlib
import shutil
from pathlib import Path

import pytest

import profilekit.generate_cv as cv
import profilekit.generate_github_readme as github_readme
import profilekit.generate_linkedin as linkedin
import profilekit.generate_portfolio as portfolio
from profilekit import registry
from profilekit.context import discover_project

GENERATOR_MODULES = (github_readme, linkedin, portfolio, cv)

FIXTURE_PROJECT = Path(__file__).resolve().parent / "fixtures" / "project"

#: Registry name -> (module, the exact artifact set it writes into output_dir).
#: The manifest is absent on purpose: the CLI writes it, not a generator.
EXPECTED_ARTIFACTS = {
    "github-readme": (github_readme, {"github-readme.md"}),
    "linkedin": (linkedin, {"linkedin.md"}),
    "portfolio": (portfolio, {"portfolio.md"}),
    "cv": (cv, {"cv.md", "cv.yml"}),
}


def _file_digests(root: Path) -> dict[Path, str]:
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


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


def test_every_built_in_generator_has_a_declared_artifact_set() -> None:
    """A new built-in generator must state what it writes, or the test below skips it."""
    assert set(registry.generators()) == set(EXPECTED_ARTIFACTS)


@pytest.mark.parametrize("name", sorted(EXPECTED_ARTIFACTS))
def test_each_generator_writes_exactly_its_artifacts_and_nothing_else(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One generator, one fresh output directory, one exact file set.

    Running each generator alone means a single stray or misnamed file is
    attributed to the generator that wrote it instead of being lost in the
    union. The project is a sandbox copy and the working directory is the
    sandbox, so a write that escapes to the project root, its data, or a
    cwd-relative path lands in ``tmp_path`` and is caught.
    """
    module, expected = EXPECTED_ARTIFACTS[name]
    project = tmp_path / "project"
    shutil.copytree(FIXTURE_PROJECT, project)
    output_dir = tmp_path / "output"
    monkeypatch.chdir(tmp_path)

    before = _file_digests(tmp_path)
    module.main(discover_project(explicit=project), output_dir=output_dir)
    after = _file_digests(tmp_path)

    written = {p.relative_to(output_dir).as_posix() for p in after if output_dir in p.parents}
    assert written == expected, f"{name} wrote {sorted(written)}, expected {sorted(expected)}"

    escaped = sorted(
        str(p.relative_to(tmp_path))
        for p, digest in after.items()
        if output_dir not in p.parents and before.get(p) != digest
    )
    assert not escaped, f"{name} wrote outside the output directory: {escaped}"


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

    # Names may coincide across groups (`linkedin` is both an artifact and a
    # destination); what must not coincide is the implementation behind them.
    assert not set(registry.generators().values()) & set(registry.publishers().values())
