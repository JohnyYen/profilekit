"""``profile init`` — scaffolding a new project.

This command is the whole on-ramp for a third party. If it does not work in an
empty directory, the package is not usable by anyone but its author.

The example data it writes must contain **no real identity**. A scaffold
seeded with the maintainer's name, email, or handles would ship one person's
details into every new project, and the first thing a user would do is
discover their CV says someone else's name.
"""

import json
from pathlib import Path

import pytest

from profilekit import cli
from profilekit.context import CONFIG_FILENAME, discover_project

# Identity that must never appear in a scaffolded project.
MAINTAINER_MARKERS = (
    "johny",
    "pedraza",
    "johnyyen",
    "bernalsuarez",
    "+53",
)


def _init(target: Path) -> int:
    return cli.main(["init", str(target)])


def test_init_in_empty_directory(tmp_path: Path) -> None:
    """A bare directory becomes a working project."""
    assert _init(tmp_path) == 0

    assert (tmp_path / CONFIG_FILENAME).is_file()
    data_dir = tmp_path / "data"
    assert data_dir.is_dir()

    written = sorted(p.name for p in data_dir.glob("*.json"))
    assert written, "init must scaffold example data"


def test_scaffolded_project_is_discoverable(tmp_path: Path) -> None:
    """What init writes must satisfy discovery and config validation."""
    _init(tmp_path)
    ctx = discover_project(explicit=tmp_path)

    assert ctx.root == tmp_path.resolve()
    assert ctx.data_dir == tmp_path.resolve() / "data"


def test_scaffolded_data_validates(tmp_path: Path) -> None:
    """The example data must pass `profile validate` as written.

    A scaffold that fails its own validator teaches the user that the tool is
    broken before they have changed anything.
    """
    _init(tmp_path)
    assert cli.main(["--project", str(tmp_path), "validate"]) == 0


def test_scaffolded_project_generates(tmp_path: Path) -> None:
    """`generate` must succeed on the scaffold, end to end."""
    _init(tmp_path)
    assert cli.main(["--project", str(tmp_path), "generate"]) == 0

    produced = sorted(p.name for p in (tmp_path / "output").glob("*"))
    assert "github-readme.md" in produced
    assert "linkedin.md" in produced


def test_scaffold_contains_no_maintainer_identity(tmp_path: Path) -> None:
    """The critical one: no real person's details in a fresh project."""
    _init(tmp_path)

    offenders: list[str] = []
    for path in tmp_path.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in MAINTAINER_MARKERS:
            if marker in text:
                offenders.append(f"{path.relative_to(tmp_path)}: {marker!r}")

    assert not offenders, f"scaffold leaks maintainer identity: {offenders}"


def test_init_refuses_to_overwrite_an_existing_project(tmp_path: Path) -> None:
    """Re-running init must not silently clobber a user's configuration."""
    assert _init(tmp_path) == 0
    config = tmp_path / CONFIG_FILENAME
    config.write_text(
        '[project]\nconfig_version = 1\n\n[paths]\noutput = "mine"\n', encoding="utf-8"
    )

    assert _init(tmp_path) != 0
    assert "mine" in config.read_text(encoding="utf-8"), "init overwrote existing config"


def test_init_creates_a_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "new" / "project"
    assert _init(target) == 0
    assert (target / CONFIG_FILENAME).is_file()


def test_init_defaults_to_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no argument, init scaffolds where the user is standing."""
    monkeypatch.chdir(tmp_path)
    assert cli.main(["init"]) == 0
    assert (tmp_path / CONFIG_FILENAME).is_file()


def test_example_data_is_valid_json(tmp_path: Path) -> None:
    _init(tmp_path)
    for path in (tmp_path / "data").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
