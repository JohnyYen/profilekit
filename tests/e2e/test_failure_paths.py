"""The ways the installed CLI is supposed to fail, driven from outside.

`test_adopter_journey.py` covers the path a stranger takes when everything
works. This file covers what they meet when something does not: data that
fails its schema, a project directory that already holds data, a destination
that is broken or misnamed, a credential that is absent, and an output tree
that no longer matches what is committed.

Each of these is promised by a spec or a docstring, and each is easy to get
right inside the process and wrong at the process boundary — an exit code
that is swallowed, a message that goes to the wrong stream, a traceback where
a sentence was promised. So they run against the installed wheel, like the
journey does, rather than calling the functions directly.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.e2e.conftest import _run
from tests.e2e.test_adopter_journey import EXPECTED_ARTIFACTS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _edit_about(project: Path, **changes: object) -> None:
    """Apply *changes* to `data/about.json`; a value of `None` deletes the key."""
    path = project / "data" / "about.json"
    about = json.loads(path.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is None:
            about.pop(key)
        else:
            about[key] = value
    _write_json(path, about)


def _line_for(stdout: str, destination: str) -> str:
    """Return the publish-table row for *destination*, failing if it is absent."""
    rows = [line for line in stdout.splitlines() if line.split(" ", 1)[0] == destination]
    assert rows, f"no row for destination {destination!r} in:\n{stdout}"
    return rows[0]


def _git(project: Path, *args: str) -> None:
    """Run git in *project* with no user or system configuration, checked.

    `HOME` points into the project and `GIT_CONFIG_NOSYSTEM` is set so a
    developer's own configuration — commit signing, hooks, a default branch —
    cannot make the setup fail or behave differently from CI.
    """
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(project),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    result = _run(
        [
            "git",
            "-c",
            "user.name=e2e",
            "-c",
            "user.email=e2e@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=project,
        env=env,
    )
    assert result.returncode == 0, f"git {' '.join(args)} failed:\n{result.stderr}"


@pytest.fixture
def committed_project(empty_project: Path, run_profile) -> Path:
    """A generated project whose whole tree is committed to a fresh repository."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")

    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)
    _git(empty_project, "init", "--quiet")
    _git(empty_project, "add", "--all")
    _git(empty_project, "commit", "--quiet", "--message", "initial")
    return empty_project


# ---------------------------------------------------------------------------
# init over existing data
# ---------------------------------------------------------------------------


def test_init_refuses_to_overwrite_data_without_a_config(empty_project: Path, profile) -> None:
    """Data with no `profile.toml` next to it is still somebody's data.

    The config-file guard alone would let `init` proceed here and replace the
    user's `about.json` with the example person's.
    """
    data = empty_project / "data"
    data.mkdir()
    sentinel = '{"username": "mine, not the example"}\n'
    (data / "about.json").write_text(sentinel, encoding="utf-8")

    # Unchecked on purpose: this call failing is the assertion.
    result = profile("init", cwd=empty_project)

    assert result.returncode == 1
    assert "refusing to overwrite" in result.stderr
    assert "about.json" in result.stderr
    assert (data / "about.json").read_text(encoding="utf-8") == sentinel
    assert not (empty_project / "profile.toml").exists(), "init wrote before refusing"
    assert sorted(p.name for p in data.iterdir()) == ["about.json"], (
        "init wrote example data before refusing"
    )


# ---------------------------------------------------------------------------
# Invalid data
# ---------------------------------------------------------------------------


def test_validate_names_the_file_and_field_of_a_wrong_type(
    empty_project: Path, profile, run_profile
) -> None:
    run_profile("init", cwd=empty_project)
    _edit_about(empty_project, headline=42)

    result = profile("validate", cwd=empty_project)

    assert result.returncode == 1
    assert "about.json at headline" in result.stdout
    assert "FAILED" in result.stdout


def test_validate_names_a_missing_required_field(empty_project: Path, profile, run_profile) -> None:
    run_profile("init", cwd=empty_project)
    _edit_about(empty_project, tagline=None)

    result = profile("validate", cwd=empty_project)

    assert result.returncode == 1
    assert "about.json" in result.stdout
    assert "'tagline' is a required property" in result.stdout
    assert "FAILED" in result.stdout


def test_generate_on_malformed_json_fails_without_a_traceback(
    empty_project: Path, profile, run_profile
) -> None:
    """generator-robustness: a parse error is a message, not a stack dump."""
    run_profile("init", cwd=empty_project)
    (empty_project / "data" / "about.json").write_text("{not json", encoding="utf-8")

    result = profile("generate", cwd=empty_project)

    assert result.returncode == 1
    assert "Traceback" not in result.stdout + result.stderr
    assert "line 1" in result.stderr, "the message must locate the parse error"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "defect: generators read data with raw json.load, so the parse error "
        "is reported as `generator 'cv' failed: Expecting ...` without naming "
        "the file, which generator-robustness requires"
    ),
)
def test_generate_on_malformed_json_names_the_file(
    empty_project: Path, profile, run_profile
) -> None:
    run_profile("init", cwd=empty_project)
    (empty_project / "data" / "about.json").write_text("{not json", encoding="utf-8")

    result = profile("generate", cwd=empty_project)

    assert result.returncode == 1
    assert "about.json" in result.stderr


@pytest.mark.xfail(
    strict=True,
    reason=(
        "defect: validate.main loads skills.json for the icon probe (and "
        "projects/social for the link probe) outside any error handling, so "
        "malformed JSON there raises JSONDecodeError as a traceback even with "
        "the probes skipped"
    ),
)
def test_validate_on_malformed_skills_json_fails_without_a_traceback(
    empty_project: Path, profile, run_profile
) -> None:
    run_profile("init", cwd=empty_project)
    (empty_project / "data" / "skills.json").write_text("{not json", encoding="utf-8")

    result = profile("validate", cwd=empty_project)

    assert result.returncode == 1
    assert "Traceback" not in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# check against a git repository
# ---------------------------------------------------------------------------


def test_check_passes_on_a_clean_committed_tree(committed_project: Path, profile) -> None:
    result = profile("check", cwd=committed_project)

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "output/ up to date" in result.stdout


def test_check_fails_when_data_changed_but_output_was_not_committed(
    committed_project: Path, profile
) -> None:
    """The freshness gate's reason to exist: data edited, artifacts not."""
    # `headline` rather than `tagline`: the scaffold sets both and every
    # generator prefers `headline`, so editing `tagline` changes no artifact
    # and the gate would rightly pass.
    _edit_about(committed_project, headline="A headline the committed output does not carry")

    result = profile("check", cwd=committed_project)

    assert result.returncode == 1
    assert "output/ is stale" in result.stderr


def test_check_fails_on_a_committed_manifest_with_a_tampered_digest(
    committed_project: Path, profile
) -> None:
    """A committed manifest that lies about its artifacts is caught.

    `check` regenerates before it inspects the manifest, so the digest
    comparison inside `_manifest_is_valid` never sees a tampered file — the
    regenerated manifest replaces it. What catches a tampered *committed*
    manifest is the freshness gate, which is what this asserts.
    """
    path = committed_project / "output" / "manifest.json"
    index = json.loads(path.read_text(encoding="utf-8"))
    index["artifacts"][0]["sha256"] = "0" * 64
    _write_json(path, index)
    _git(committed_project, "commit", "--quiet", "--all", "--message", "tamper")

    result = profile("check", cwd=committed_project)

    assert result.returncode == 1
    assert "output/ is stale" in result.stderr


def test_check_skips_freshness_when_git_is_absent_but_dot_git_exists(
    empty_project: Path, profile, run_profile, installed: Path
) -> None:
    """A repository on disk is not a git binary on PATH.

    PATH is reduced to the virtualenv's own bin directory. The console script
    still starts because its shebang names the interpreter by absolute path,
    and `git` is no longer resolvable.
    """
    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)
    (empty_project / ".git").mkdir()

    result = profile("check", cwd=empty_project, env_extra={"PATH": str(installed)})

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "git freshness check skipped" in result.stdout
    assert "output/ freshness skipped" in result.stdout


# ---------------------------------------------------------------------------
# Publishing failures
# ---------------------------------------------------------------------------


CREDENTIAL_CONFIG = """\
[project]
config_version = 1

[publishers.site]
kind = "filesystem"
destination = "site/data"

[publishers.site.credential]
token = "PROFILEKIT_E2E_ABSENT_TOKEN"
"""


@pytest.fixture
def project_needing_a_credential(empty_project: Path, run_profile) -> Path:
    run_profile("init", cwd=empty_project)
    (empty_project / "profile.toml").write_text(CREDENTIAL_CONFIG, encoding="utf-8")
    run_profile("generate", cwd=empty_project)
    return empty_project


def test_an_absent_credential_skips_the_destination(
    project_needing_a_credential: Path, profile
) -> None:
    """An absent secret is a configuration state, not an error."""
    result = profile("publish", "--execute", cwd=project_needing_a_credential)

    assert result.returncode == 0, result.stderr
    row = _line_for(result.stdout, "site")
    assert "skipped" in row
    assert "PROFILEKIT_E2E_ABSENT_TOKEN" in row
    assert not (project_needing_a_credential / "site").exists()


def test_require_credentials_turns_an_absent_credential_into_a_failure(
    project_needing_a_credential: Path, profile
) -> None:
    """CI must not mistake a silently skipped publish for a successful one."""
    result = profile(
        "publish", "--execute", "--require-credentials", cwd=project_needing_a_credential
    )

    assert result.returncode == 1
    row = _line_for(result.stdout, "site")
    assert "failed" in row
    assert "PROFILEKIT_E2E_ABSENT_TOKEN" in row
    assert not (project_needing_a_credential / "site").exists()


def test_a_present_credential_lets_the_destination_publish(
    project_needing_a_credential: Path, profile
) -> None:
    """The control for the two tests above: the variable is what decides."""
    result = profile(
        "publish",
        "--execute",
        "--require-credentials",
        cwd=project_needing_a_credential,
        env_extra={"PROFILEKIT_E2E_ABSENT_TOKEN": "not-a-real-token"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "published" in _line_for(result.stdout, "site")
    assert "not-a-real-token" not in result.stdout + result.stderr
    assert (project_needing_a_credential / "site" / "data" / "about.json").is_file()


MIXED_DESTINATIONS_CONFIG = """\
[project]
config_version = 1

[publishers.broken]
kind = "no-such-kind"

[publishers.site]
kind = "filesystem"
destination = "site/data"

[publishers.linkedin]
kind = "manual"
artifacts = ["linkedin.md"]
"""


@pytest.fixture
def project_with_a_broken_destination(empty_project: Path, run_profile) -> Path:
    run_profile("init", cwd=empty_project)
    (empty_project / "profile.toml").write_text(MIXED_DESTINATIONS_CONFIG, encoding="utf-8")
    run_profile("generate", cwd=empty_project)
    return empty_project


def test_one_failing_destination_does_not_block_the_others(
    project_with_a_broken_destination: Path, profile
) -> None:
    """The broken destination is declared first, so isolation is what lets the rest run."""
    project = project_with_a_broken_destination
    result = profile("publish", "--execute", cwd=project)

    assert result.returncode == 1, "a failed destination must still fail the run"

    broken = _line_for(result.stdout, "broken")
    assert "failed" in broken
    assert "no-such-kind" in broken

    assert "published" in _line_for(result.stdout, "site")
    written = sorted(p.name for p in (project / "site" / "data").glob("*.json"))
    assert written == ["about.json", "projects.json", "skills.json", "social.json"]

    assert "pending-manual" in _line_for(result.stdout, "linkedin")


def test_an_unknown_destination_name_lists_the_declared_ones(
    project_with_a_broken_destination: Path, profile
) -> None:
    result = profile("publish", "sight", "--execute", cwd=project_with_a_broken_destination)

    assert result.returncode == 2
    assert "unknown destination 'sight'" in result.stderr
    assert "declared: broken, site, linkedin" in result.stderr
    assert not (project_with_a_broken_destination / "site").exists()


# ---------------------------------------------------------------------------
# Where the project is, and where the output goes
# ---------------------------------------------------------------------------


def test_generate_from_a_subdirectory_targets_the_project_root(
    empty_project: Path, run_profile
) -> None:
    run_profile("init", cwd=empty_project)
    deep = empty_project / "notes" / "deep"
    deep.mkdir(parents=True)

    run_profile("generate", cwd=deep)

    produced = sorted(p.name for p in (empty_project / "output").glob("*"))
    assert produced == EXPECTED_ARTIFACTS
    stray = [p for p in (empty_project / "notes").rglob("*") if p.is_file()]
    assert not stray, f"generation wrote under the working directory: {stray}"
    assert not (deep / "output").exists()


def test_output_dir_and_project_flags_from_another_directory(
    empty_project: Path, run_profile, tmp_path: Path
) -> None:
    """A caller-owned, not-yet-existing output path is created, not refused."""
    run_profile("init", cwd=empty_project)
    elsewhere = tmp_path / "caller"
    elsewhere.mkdir()
    target = elsewhere / "build" / "nested" / "artifacts"

    run_profile(
        "--project",
        str(empty_project),
        "--output-dir",
        str(target),
        "generate",
        cwd=elsewhere,
    )

    assert sorted(p.name for p in target.glob("*")) == EXPECTED_ARTIFACTS
    assert not (empty_project / "output").exists()
    assert not (elsewhere / "output").exists()


# ---------------------------------------------------------------------------
# The published contract's version markers
# ---------------------------------------------------------------------------


SITE_CONFIG = """\
[project]
config_version = 1

[publishers.site]
kind = "filesystem"
destination = "site/data"
"""


@pytest.fixture
def published_site(empty_project: Path, run_profile) -> Path:
    run_profile("init", cwd=empty_project)
    (empty_project / "profile.toml").write_text(SITE_CONFIG, encoding="utf-8")
    run_profile("generate", cwd=empty_project)
    run_profile("publish", "--execute", cwd=empty_project)
    return empty_project


def test_object_shaped_published_files_carry_an_integer_schema_version(
    published_site: Path,
) -> None:
    """output-data-contract: an object artifact carries its version inline."""
    data = published_site / "site" / "data"
    manifest = json.loads((published_site / "output" / "manifest.json").read_text())

    for name in ("about.json", "social.json", "skills.json"):
        payload = json.loads((data / name).read_text(encoding="utf-8"))
        assert isinstance(payload, dict), f"{name} is no longer an object"
        version = payload.get("schemaVersion")
        # `bool` is an `int` subclass; `true` is not a version.
        assert type(version) is int and version >= 1, f"{name} schemaVersion: {version!r}"
        assert version == manifest["schemaVersion"], (
            f"{name} declares version {version}, the manifest {manifest['schemaVersion']}"
        )

    assert isinstance(json.loads((data / "projects.json").read_text()), list)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "possible defect: output-data-contract says output/manifest.json SHALL "
        "carry the version for the array-shaped projects.json, but the manifest "
        "indexes only output/ and so has no entry for projects.json; only the "
        "file-wide top-level schemaVersion exists"
    ),
)
def test_the_manifest_carries_a_version_entry_for_projects_json(published_site: Path) -> None:
    manifest = json.loads((published_site / "output" / "manifest.json").read_text())
    entries = {entry["name"]: entry for entry in manifest["artifacts"]}

    assert "projects.json" in entries
    assert entries["projects.json"]["schemaVersion"] >= 1
