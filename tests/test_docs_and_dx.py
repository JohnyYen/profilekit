"""Documentation and developer-experience invariants.

Docs rot silently. A README that promises a command that no longer exists, or
links a file that was never written, is worse than no README: it costs a reader
their trust before they have run anything.

These tests pin the promises that matter for adoption — that the entry path is
documented before the maintainer's own data, that every linked doc exists, and
that contributing does not require one specific installer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
DOCS = REPO_ROOT / "docs"
PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# The README is for adopters first
# ---------------------------------------------------------------------------


def test_readme_covers_the_entry_path() -> None:
    text = _readme()
    for command in (
        "pip install profilekit",
        "profile init",
        "profile generate",
        "profile publish",
    ):
        assert command in text, f"the README must show {command!r}"


def test_readme_frames_the_tool_before_the_maintainers_data() -> None:
    """An adopter must reach install and usage before the owner's profile.

    The previous README opened by describing whose profile this is, which told
    a visitor the project was one person's repository rather than something
    they could use.
    """
    text = _readme()
    install_at = text.index("pip install profilekit")
    personal_at = min(
        (
            text.index(marker)
            for marker in ("maintainer's real profile", "apps/portfolio/")
            if marker in text
        ),
        default=len(text),
    )

    assert install_at < personal_at, (
        "installation must appear before the maintainer's own data is discussed"
    )


def test_readme_explains_the_dry_run_default() -> None:
    """A surprising default has to be stated, or it is a trap rather than a guard."""
    text = _readme()
    assert "dry run" in text.lower()


def test_readme_states_the_license() -> None:
    assert "MIT" in _readme()


# ---------------------------------------------------------------------------
# Every linked document exists
# ---------------------------------------------------------------------------


def test_every_relative_link_in_the_readme_resolves() -> None:
    """A broken link costs a reader their trust before they run anything."""
    broken = []
    for target in re.findall(r"\]\(([^)]+)\)", _readme()):
        if target.startswith(("http://", "https://", "#")):
            continue
        if not (REPO_ROOT / target.split("#")[0]).exists():
            broken.append(target)

    assert not broken, f"README links to missing files: {broken}"


@pytest.mark.parametrize(
    "name",
    ["data-contract.md", "authoring-generators.md", "authoring-publishers.md"],
)
def test_docs_dir_covers_contract_and_authoring(name: str) -> None:
    assert (DOCS / name).is_file(), f"docs/{name} is referenced and must exist"


def test_the_contract_doc_states_the_versioning_rule() -> None:
    """A contract without a compatibility promise is not a contract."""
    text = (DOCS / "data-contract.md").read_text(encoding="utf-8")

    assert "schemaVersion" in text
    assert "optional" in text.lower(), "the additive rule must be stated"
    assert "breaking" in text.lower() or "bump" in text.lower()


def test_the_authoring_docs_state_the_boundary() -> None:
    """The generator/publisher split is the one thing an author must grasp."""
    generators = (DOCS / "authoring-generators.md").read_text(encoding="utf-8").lower()
    publishers = (DOCS / "authoring-publishers.md").read_text(encoding="utf-8").lower()

    assert "publisher" in generators, "the generator guide must point at the boundary"
    assert "plan" in publishers
    assert "publish" in publishers
    assert "manual" in publishers, "the manual capability must be documented"


# ---------------------------------------------------------------------------
# Contributing does not require one specific installer
# ---------------------------------------------------------------------------


def test_hooks_run_without_uv() -> None:
    """A contributor who installed with pip must not hit a hook failure.

    The previous configuration shelled out to `uv run`, so the first commit
    from a pip-based environment failed with no obvious cause.
    """
    config = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))

    offenders = []
    for repo in config["repos"]:
        for hook in repo["hooks"]:
            entry = hook.get("entry", "")
            if "uv run" in entry or entry.startswith("uv "):
                offenders.append(hook["id"])

    assert not offenders, f"hooks must not require uv: {offenders}"


def test_hooks_do_not_depend_on_the_network_for_data_checks() -> None:
    """A commit must work offline and not depend on third-party uptime.

    Three mechanisms were tried and two were wrong, so this asserts the one
    that works for each hook rather than a shape:

    - A hook-level `env:` mapping is not a key pre-commit supports. It warns
      and ignores it, so the variables never reach the process — and a test
      asserting on `env` passed while the behaviour was broken.
    - An `env VAR=1 …` prefix does reach the process, but `env` is POSIX-only,
      so a Windows contributor gets a launch failure on every commit.
    - So: the CLI hook passes `--offline`, and the test suite pins itself
      offline in conftest.
    """
    config = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    local = next(repo for repo in config["repos"] if repo["repo"] == "local")

    for hook in local["hooks"]:
        assert "env" not in hook, (
            f"{hook['id']}: a hook-level `env:` mapping is silently ignored by pre-commit"
        )
        entry = hook["entry"]
        assert not entry.startswith("env "), (
            f"{hook['id']}: an `env` prefix is POSIX-only and fails on native Windows"
        )

    cli_hook = next(h for h in local["hooks"] if h["id"] == "profile-check")
    assert "--offline" in cli_hook["entry"], (
        "the CLI hook must disable reachability probes with --offline"
    )

    # The pytest hook needs no flag: conftest pins the whole suite offline.
    # Asserted against the live environment, not the conftest source — a
    # substring scan would pass on a comment or a deleted assignment that left
    # the names behind, which is the same vacuity this file keeps finding.
    import os

    assert os.environ.get("SKIP_ICON_CHECK") == "1", (
        "the suite must pin itself offline; the pytest hook sets nothing"
    )
    assert os.environ.get("SKIP_LINK_CHECK") == "1", (
        "the suite must pin itself offline; the pytest hook sets nothing"
    )


def test_contributing_documents_the_hook_install() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "pre-commit install" in contributing


def test_the_contract_doc_covers_every_published_schema() -> None:
    """A schema nobody is told about is not part of a contract.

    The doc previously named only the manifest schema, so a consumer had no
    way to know the four published shapes could be validated at all.
    """
    from profilekit import cli

    text = (DOCS / "data-contract.md").read_text(encoding="utf-8")

    for schema_name in cli.PUBLISHED_SCHEMAS.values():
        assert schema_name in text, f"{schema_name} is undocumented"
    assert "manifest.schema.json" in text


def test_the_contract_doc_distinguishes_input_from_output_schemas() -> None:
    """Validating published output against the input schemas hides dropped fields."""
    text = (DOCS / "data-contract.md").read_text(encoding="utf-8").lower()

    assert "input" in text, "the doc must explain why the input schemas are the wrong ones to use"
    assert "permissive" in text, (
        "the doc must explain why the input schemas are the wrong ones to use"
    )
