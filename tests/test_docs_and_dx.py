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
    assert "plan" in publishers and "publish" in publishers
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

    The switches have to be set inline in `entry`, not in a hook-level `env:`
    mapping. `env:` is not a key pre-commit supports — it warns about unknown
    keys and ignores them — so asserting on `env` would pass while the
    variables never reached the process. An earlier version of this test did
    exactly that, and the review caught it.
    """
    config = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    local = next(repo for repo in config["repos"] if repo["repo"] == "local")

    for hook in local["hooks"]:
        assert "env" not in hook, (
            f"{hook['id']}: a hook-level `env:` mapping is silently ignored by "
            "pre-commit; set the variables inline in `entry`"
        )
        entry = hook["entry"]
        for variable in ("SKIP_ICON_CHECK=1", "SKIP_LINK_CHECK=1"):
            assert variable in entry, f"{hook['id']} must set {variable} in its entry"


def test_contributing_documents_the_hook_install() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "pre-commit install" in contributing
