"""The journey a stranger takes, driven against an installed package.

This is the test the project most needed and did not have. Everything else in
the suite imports `profilekit` from the checkout, where `src/` is importable
and the repository root is the working directory. Those two conveniences hide
the defects that make a package unusable to everyone except its author.

Two such defects shipped during development and neither was visible to the
unit suite:

- The JSON Schemas were not declared as package data, so an installed CLI
  could not find them.
- A stale `*.egg-info` at the repository root shadowed the real distribution
  metadata, so entry-point discovery enumerated nothing.

So these tests build the wheel, install it into an interpreter that has never
heard of this repository, and run the commands the README promises — in a
directory that is not the checkout, with no `PYTHONPATH` and no inherited
configuration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.conftest import REPO_ROOT

# Reachability probes talk to skillicons.dev and every project URL. They are a
# real feature but not what this file tests, and depending on third-party
# uptime would turn a packaging test into a flake.
OFFLINE = {"SKIP_ICON_CHECK": "1", "SKIP_LINK_CHECK": "1"}

EXPECTED_ARTIFACTS = [
    "cv.md",
    "cv.yml",
    "github-readme.md",
    "linkedin.md",
    "manifest.json",
    "portfolio.md",
]


# ---------------------------------------------------------------------------
# The install itself
# ---------------------------------------------------------------------------


def test_the_console_scripts_exist(installed: Path) -> None:
    """Both entry points must resolve from the install, not from the checkout."""
    for name in ("profile", "profilekit"):
        assert (installed / name).exists(), f"{name} console script missing"


def test_the_package_is_importable_without_the_checkout(
    installed: Path, empty_project: Path, profile
) -> None:
    """A smoke test on the import itself, before any command runs."""
    result = profile("--help", cwd=empty_project)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "generate" in result.stdout


def test_the_packaged_schemas_resolve_from_the_install(venv_python, empty_project: Path) -> None:
    """The defect this catches: schemas that only exist in the repository.

    An installed CLI has no checkout to read `schemas/` from, so they must
    travel inside the distribution.

    Run through the isolated interpreter rather than a bare subprocess. The
    first version inherited the caller's environment, and with `PYTHONPATH`
    pointing at `src/` it passed while the schemas were missing from the
    wheel — passing for the exact defect it exists to catch. Verified by
    mutation.
    """
    expected = sorted(p.name for p in (REPO_ROOT / "src/profilekit/schemas").glob("*.schema.json"))

    result = venv_python(
        "import importlib.resources as r;"
        "d = r.files('profilekit.schemas');"
        "print(' '.join(sorted(p.name for p in d.iterdir() if p.name.endswith('.json'))))",
        cwd=empty_project,
    )

    assert result.returncode == 0, f"schemas unreachable from the install:\n{result.stderr}"
    shipped = result.stdout.split()
    # Compared against the real set rather than a magic threshold, so dropping
    # one schema fails instead of staying under an arbitrary bar.
    assert shipped == expected, f"wheel ships {shipped}, source has {expected}"


def test_entry_points_are_discovered_from_the_install(venv_python, empty_project: Path) -> None:
    """The defect this catches: metadata that resolves only in the checkout.

    A stale `*.egg-info` at the repository root once shadowed the real
    distribution, so `entry_points()` returned the first match and found no
    component groups at all. An installed package has no such file to shadow it.
    """
    result = venv_python(
        "from profilekit import registry;"
        "print(','.join(sorted(registry.generators())));"
        "print(','.join(sorted(registry.publishers())))",
        cwd=empty_project,
    )

    assert result.returncode == 0, f"registry unreachable:\n{result.stderr}"
    generators, publishers = result.stdout.strip().splitlines()
    assert generators == "cv,github-readme,linkedin,portfolio"
    assert "portfolio-data" in publishers


# ---------------------------------------------------------------------------
# No project: fail, do not guess
# ---------------------------------------------------------------------------


def test_a_command_outside_a_project_exits_two(empty_project: Path, profile) -> None:
    """A tool that guesses writes generated files where nobody asked."""
    result = profile("validate", cwd=empty_project, env_extra=OFFLINE)

    assert result.returncode == 2
    assert "profile init" in result.stderr, "the error must say how to fix it"
    assert str(empty_project) in result.stderr, "the error must say where it looked"


def test_nothing_resolves_to_the_installed_package_directory(
    empty_project: Path, profile, installed: Path, run_profile
) -> None:
    """The regression the whole discovery mechanism exists to prevent."""
    # Unchecked on purpose: exiting non-zero is the expected outcome.
    result = profile("generate", cwd=empty_project)

    assert result.returncode == 2
    assert "site-packages" not in result.stdout + result.stderr
    assert not list(empty_project.rglob("*.md")), "nothing should have been written"


# ---------------------------------------------------------------------------
# The journey the README promises
# ---------------------------------------------------------------------------


def test_init_then_validate_then_generate(empty_project: Path, profile, run_profile) -> None:
    """The three commands the quick start names, in order, from nothing."""
    init = run_profile("init", cwd=empty_project)
    assert init.returncode == 0, f"init failed:\n{init.stderr}"
    assert (empty_project / "profile.toml").is_file()

    validate = profile("validate", cwd=empty_project, env_extra=OFFLINE)
    assert validate.returncode == 0, f"the scaffold failed its own validator:\n{validate.stdout}"

    generate = run_profile("generate", cwd=empty_project)
    assert generate.returncode == 0, f"generate failed:\n{generate.stderr}"

    produced = sorted(p.name for p in (empty_project / "output").glob("*"))
    assert produced == EXPECTED_ARTIFACTS


def test_the_scaffold_carries_no_maintainer_identity(
    empty_project: Path, profile, run_profile
) -> None:
    """A new project must not arrive with somebody else's name in it."""
    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)

    # Imported rather than repeated: the deny-list lives in one place so the
    # guards cannot drift, and so this file does not itself become a hit for
    # the PII sweep that scans test material.
    from tests.test_no_real_pii import DENY_LIST as markers

    offenders = []
    for path in empty_project.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        offenders += [f"{path.name}: {m}" for m in markers if m in text]

    assert not offenders, f"scaffold leaks maintainer identity: {offenders}"


def test_check_passes_on_a_fresh_project(empty_project: Path, profile, run_profile) -> None:
    """`check` must be satisfiable immediately, not only after manual work."""
    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)

    result = profile("check", cwd=empty_project, env_extra=OFFLINE)
    assert result.returncode == 0, f"check failed on a fresh project:\n{result.stdout}"


def test_check_degrades_without_git(empty_project: Path, profile, run_profile) -> None:
    """A fresh project is not a repository, and must not need to be."""
    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)

    result = profile("check", cwd=empty_project, env_extra=OFFLINE)
    combined = result.stdout + result.stderr

    assert result.returncode == 0
    assert "skipped" in combined.lower(), "the gate must say it could not check freshness"
    assert not (empty_project / ".git").exists(), "check must not create a repository"


def test_generation_is_byte_identical_across_runs(
    empty_project: Path, profile, run_profile
) -> None:
    """Committed artifacts are only useful if regenerating them is stable."""
    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)

    first = {p.name: p.read_bytes() for p in (empty_project / "output").glob("*")}
    run_profile("generate", cwd=empty_project)
    second = {p.name: p.read_bytes() for p in (empty_project / "output").glob("*")}

    assert first == second


def test_generation_writes_nothing_outside_the_output_directory(
    empty_project: Path, profile, run_profile
) -> None:
    """The generator/publisher boundary, observed from outside the process."""
    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)

    output = empty_project / "output"
    escaped = [
        p
        for p in empty_project.rglob("*")
        if p.is_file() and output not in p.parents and p.suffix in {".md", ".yml"}
    ]
    assert not escaped, f"generation wrote outside output/: {escaped}"


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------


DESTINATION_CONFIG = """\
[project]
config_version = 1

[publishers.site]
kind = "filesystem"
destination = "site/data"

[publishers.linkedin]
kind = "manual"
artifacts = ["linkedin.md"]
"""


@pytest.fixture
def project_with_destinations(empty_project: Path, profile, run_profile) -> Path:
    run_profile("init", cwd=empty_project)
    (empty_project / "profile.toml").write_text(DESTINATION_CONFIG, encoding="utf-8")
    run_profile("generate", cwd=empty_project)
    return empty_project


def test_publish_is_a_dry_run_by_default(project_with_destinations: Path, profile) -> None:
    """Writing is opt-in because publishing is not reliably reversible."""
    result = profile("publish", cwd=project_with_destinations, env_extra=OFFLINE)

    assert result.returncode == 0
    assert "nothing was published" in result.stdout
    assert not (project_with_destinations / "site").exists()


def test_execute_writes_the_destination(
    project_with_destinations: Path, profile, run_profile
) -> None:
    result = run_profile("publish", "--execute", cwd=project_with_destinations)
    assert result.returncode == 0, f"publish failed:\n{result.stderr}"

    written = sorted(p.name for p in (project_with_destinations / "site" / "data").glob("*.json"))
    assert written == ["about.json", "projects.json", "skills.json", "social.json"]


def test_a_manual_destination_never_reports_published(
    project_with_destinations: Path, profile, run_profile
) -> None:
    """A tool claiming a publish it did not perform lets a profile go stale."""
    result = run_profile("publish", "--execute", cwd=project_with_destinations)

    manual_line = next(line for line in result.stdout.splitlines() if line.startswith("linkedin"))
    assert "pending-manual" in manual_line
    assert "published" not in manual_line
    assert "by hand" in result.stdout


def test_republishing_unchanged_content_reports_unchanged(
    project_with_destinations: Path, profile, run_profile
) -> None:
    run_profile("publish", "--execute", cwd=project_with_destinations)
    result = run_profile("publish", "--execute", cwd=project_with_destinations)

    site_line = next(line for line in result.stdout.splitlines() if line.startswith("site"))
    assert "unchanged" in site_line


def test_check_detects_a_drifted_destination(
    project_with_destinations: Path, profile, run_profile
) -> None:
    """The gate that is the only thing covering a published destination."""
    run_profile("publish", "--execute", cwd=project_with_destinations)

    stale = project_with_destinations / "site" / "data" / "about.json"
    stale.write_text(json.dumps({"schemaVersion": 1, "username": "drifted"}) + "\n")

    result = profile("check", cwd=project_with_destinations, env_extra=OFFLINE)
    assert result.returncode != 0
    assert "about.json" in result.stderr


def test_check_does_not_repair_a_drifted_destination(
    project_with_destinations: Path, profile, run_profile
) -> None:
    """A gate that silently fixes what it finds hides the problem it exists for."""
    run_profile("publish", "--execute", cwd=project_with_destinations)

    stale = project_with_destinations / "site" / "data" / "about.json"
    content = json.dumps({"schemaVersion": 1, "username": "drifted"}) + "\n"
    stale.write_text(content)

    profile("check", cwd=project_with_destinations, env_extra=OFFLINE)
    assert stale.read_text() == content


# ---------------------------------------------------------------------------
# The published contract, read the way a consumer reads it
# ---------------------------------------------------------------------------


def test_published_artifacts_validate_against_the_packaged_schemas(
    project_with_destinations: Path, run_profile, venv_python
) -> None:
    """A consumer must be able to validate without a checkout of this project."""
    run_profile("publish", "--execute", cwd=project_with_destinations)

    script = """
import json, sys
import importlib.resources as r
import jsonschema
from pathlib import Path

schemas = r.files("profilekit.schemas")
pairs = {
    "about.json": "published-about.schema.json",
    "social.json": "published-social.schema.json",
    "skills.json": "published-skills.schema.json",
    "projects.json": "published-projects.schema.json",
}
data = Path(sys.argv[1])
for artifact, schema_name in pairs.items():
    schema = json.loads((schemas / schema_name).read_text())
    payload = json.loads((data / artifact).read_text())
    jsonschema.Draft7Validator(schema).validate(payload)
print("ok")
"""
    result = venv_python(
        script,
        str(project_with_destinations / "site" / "data"),
        cwd=project_with_destinations,
    )
    assert result.returncode == 0, f"published artifacts failed their schemas:\n{result.stderr}"


def test_the_manifest_indexes_every_artifact_with_a_matching_digest(
    empty_project: Path, profile, run_profile
) -> None:
    """The manifest is the contract reference for artifacts that carry no version."""
    import hashlib

    run_profile("init", cwd=empty_project)
    run_profile("generate", cwd=empty_project)

    output = empty_project / "output"
    index = json.loads((output / "manifest.json").read_text(encoding="utf-8"))

    assert index["schemaVersion"] >= 1
    assert "generatedAt" not in index, "a committed artifact must carry no wall-clock value"

    names = {entry["name"] for entry in index["artifacts"]}
    assert "manifest.json" not in names, "the manifest must not index itself"

    for entry in index["artifacts"]:
        artifact = output / entry["name"]
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        assert entry["sha256"] == digest, f"{entry['name']} digest does not match its content"
        assert entry["bytes"] == artifact.stat().st_size


def test_projects_json_stays_an_array(
    project_with_destinations: Path, profile, run_profile
) -> None:
    """Consumers index into it; wrapping it to carry a version would break them."""
    run_profile("publish", "--execute", cwd=project_with_destinations)

    payload = json.loads(
        (project_with_destinations / "site" / "data" / "projects.json").read_text(encoding="utf-8")
    )
    assert isinstance(payload, list)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_a_custom_output_directory_is_honored(empty_project: Path, profile, run_profile) -> None:
    run_profile("init", cwd=empty_project)
    (empty_project / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[paths]\noutput = "dist"\n', encoding="utf-8"
    )

    result = run_profile("generate", cwd=empty_project)
    assert result.returncode == 0, result.stderr
    assert (empty_project / "dist" / "github-readme.md").is_file()
    assert not (empty_project / "output").exists()


def test_an_unknown_config_section_fails_loudly(empty_project: Path, profile, run_profile) -> None:
    """Silence is the worst failure mode for configuration."""
    run_profile("init", cwd=empty_project)
    (empty_project / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[pathz]\noutput = "dist"\n', encoding="utf-8"
    )

    # Unchecked on purpose: rejecting the typo is what is under test.
    result = profile("generate", cwd=empty_project)
    assert result.returncode == 2
    assert "pathz" in result.stderr


def test_the_project_env_var_selects_the_project(
    empty_project: Path, profile, tmp_path: Path, run_profile
) -> None:
    """CI needs to point the tool at a project without changing directory."""
    run_profile("init", cwd=empty_project)

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = profile(
        "generate",
        cwd=elsewhere,
        env_extra={**OFFLINE, "PROFILEKIT_PROJECT": str(empty_project)},
    )

    assert result.returncode == 0, result.stderr
    assert (empty_project / "output" / "github-readme.md").is_file()


def test_init_refuses_to_overwrite_an_existing_project(
    empty_project: Path, profile, run_profile
) -> None:
    """Losing a user's configuration is worse than an error message."""
    run_profile("init", cwd=empty_project)
    (empty_project / "profile.toml").write_text(
        '[project]\nconfig_version = 1\n\n[paths]\noutput = "mine"\n', encoding="utf-8"
    )

    # Unchecked on purpose: this call failing *is* the assertion.
    result = profile("init", cwd=empty_project)

    assert result.returncode != 0
    assert "mine" in (empty_project / "profile.toml").read_text(), "init clobbered the config"
