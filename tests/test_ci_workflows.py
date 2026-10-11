"""CI workflow invariants, asserted as text.

Workflows are the one place in this repository where a mistake reaches the
outside world on its own. Three properties are worth pinning down in tests
rather than in review habits:

**Validation never publishes.** A gate that can also write to a destination is
no longer a gate: a run meant to tell you whether something is correct could
change the world instead. ``validate.yml`` must stay secret-free and
publish-free.

**Publishing is gated on output actually changing.** Running the publish job
on every commit makes it noise, and noise gets ignored or disabled.

**A missing secret skips, it does not fail.** A fork, or a contributor's
branch, has none of the maintainer's credentials. If an absent secret failed
the job, every fork's CI would be permanently red through no fault of its own.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

VALIDATE = WORKFLOWS / "validate.yml"
PUBLISH = WORKFLOWS / "publish.yml"
RELEASE = WORKFLOWS / "release.yml"


def _text(path: Path) -> str:
    assert path.is_file(), f"missing workflow: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def _yaml(path: Path) -> dict:
    return yaml.safe_load(_text(path))


def _triggers(path: Path) -> dict:
    """Return a workflow's trigger block.

    YAML 1.1 resolves the bare key ``on`` to the boolean ``True``, so
    ``config["on"]`` raises a KeyError on a perfectly valid workflow. GitHub
    reads the file as YAML 1.1 too, which is why the key is written bare.
    """
    config = _yaml(path)
    return config.get("on") or config[True]


# ---------------------------------------------------------------------------
# Validation never publishes
# ---------------------------------------------------------------------------


def test_validate_workflow_never_publishes() -> None:
    """A correctness gate must not be able to change the world."""
    text = _text(VALIDATE)

    assert "publish" not in text.lower(), (
        "validate.yml must not invoke publish: a gate that can write is not a gate"
    )


def test_validate_workflow_declares_no_secrets() -> None:
    text = _text(VALIDATE)
    assert "secrets." not in text, "validate.yml must stay secret-free"


def test_validate_workflow_has_no_write_permissions() -> None:
    """Default read-only: a validation run has nothing to write."""
    text = _text(VALIDATE)
    assert "contents: write" not in text


# ---------------------------------------------------------------------------
# Publishing is gated and opt-in
# ---------------------------------------------------------------------------


def test_publish_workflow_exists() -> None:
    assert PUBLISH.is_file()


def test_publish_is_gated_on_output_changing() -> None:
    """Running on every commit would make the job noise, and noise gets ignored."""
    push = _triggers(PUBLISH)["push"]

    assert push["branches"] == ["main"]
    assert any("output/" in path for path in push["paths"]), (
        "publish must trigger only when generated artifacts change"
    )


def test_publish_supports_a_manual_dry_run() -> None:
    """An operator must be able to see what would happen before it happens."""
    dispatch = _triggers(PUBLISH)["workflow_dispatch"]

    assert "execute" in dispatch["inputs"]
    assert dispatch["inputs"]["execute"]["default"] in (False, "false"), (
        "manual runs must default to a dry run"
    )


def test_publish_does_not_fail_on_a_missing_secret() -> None:
    """A fork has none of the maintainer's credentials.

    If an absent secret failed the job, every fork's CI would be permanently
    red through no fault of its own.
    """
    # Check executed lines only. The file explains in a comment *why* the flag
    # is absent, and a naive grep cannot tell prose from a command.
    commands = [line for line in _text(PUBLISH).splitlines() if "profile publish" in line]
    assert commands, "publish.yml must invoke the CLI"
    for line in commands:
        assert "--require-credentials" not in line, (
            "publish.yml must let a missing credential skip, not fail: a fork has "
            "none of the maintainer's secrets"
        )


def test_publish_runs_the_cli_not_an_inline_script() -> None:
    """The workflow must exercise the same code path a user runs locally."""
    text = _text(PUBLISH)
    assert "profile publish" in text or "profilekit.cli publish" in text


def test_publish_checks_before_it_plans() -> None:
    """Stale or invalid output must not reach a destination.

    Without this, a push whose output is stale could be published in parallel
    with the validation run that would have rejected it.
    """
    lines = [line.strip() for line in _text(PUBLISH).splitlines()]
    check_at = next(i for i, line in enumerate(lines) if "profile check" in line)
    publish_at = next(i for i, line in enumerate(lines) if "profile publish" in line)

    assert check_at < publish_at, "`profile check` must run before any publish step"


def test_a_push_cannot_execute_a_publish() -> None:
    """A filesystem write on a runner lands in a checkout that is thrown away.

    An earlier version executed on every push to main, which reported
    destinations as published while nothing durable changed. Publishing a
    filesystem destination happens locally and is then committed; CI verifies
    the two agree.
    """
    config = _yaml(PUBLISH)
    steps = config["jobs"]["verify"]["steps"]

    execute_steps = [s for s in steps if "--execute" in str(s.get("run", ""))]
    assert execute_steps, "the workflow must still offer a manual publish"

    for step in execute_steps:
        condition = str(step.get("if", ""))
        assert "workflow_dispatch" in condition, (
            "an --execute step must be reachable only by manual dispatch"
        )
        assert "push" not in condition, "a push must not execute a publish"


# ---------------------------------------------------------------------------
# Release is tag-triggered only
# ---------------------------------------------------------------------------


def test_release_workflow_exists() -> None:
    assert RELEASE.is_file()


def test_release_triggers_only_on_a_tag() -> None:
    """Publishing a package version is irreversible: a name and version are claimed."""
    push = _triggers(RELEASE)["push"]

    assert "tags" in push, "release must be tag-triggered"
    assert "branches" not in push, (
        "a push to main must never release: the version would be claimed by accident"
    )


def test_release_verifies_against_testpypi_first() -> None:
    """A version number cannot be reused, so rehearse before claiming it."""
    text = _text(RELEASE)
    assert "test.pypi.org" in text


def test_release_does_not_hardcode_a_token() -> None:
    text = _text(RELEASE)
    for marker in ("pypi-AgEI", "password:"):
        assert marker not in text, "credentials must come from secrets or OIDC"
