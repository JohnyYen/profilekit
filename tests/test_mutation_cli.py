"""Behavior pinned down by mutation testing of ``profilekit.cli``.

The CLI is where every failure becomes an exit code and one line on stderr, so
both are part of its contract. Each test kills mutants that survived the
baseline run (see ``docs/quality/mutation-baseline.md``): the freshness gate
against a real git repository, the publish table and its target selection,
manifest and published-artifact errors, ``init`` messages, and parser wiring.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from profilekit import cli, publish
from profilekit.context import discover_project

FIXTURE_PROJECT = Path(__file__).resolve().parent / "fixtures" / "project"

CONFIG = """\
[project]
config_version = 1

[generators.cv]
current_date = "2026-07-30"
"""

PUBLISHERS = """
[publishers.site]
kind = "filesystem"
destination = "app/data"

[publishers.linkedin]
kind = "manual"
artifacts = ["linkedin.md"]
"""


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_ICON_CHECK", "1")
    monkeypatch.setenv("SKIP_LINK_CHECK", "1")


def _project(tmp_path: Path, config: str = CONFIG) -> Path:
    root = tmp_path / "project"
    shutil.copytree(FIXTURE_PROJECT, root)
    (root / "profile.toml").write_text(config, encoding="utf-8")
    return root


def _main(root: Path, *argv: str) -> int:
    return cli.main(["--project", str(root), *argv])


def _git(root: Path, *argv: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            *argv,
        ],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A project committed to its own git repository with fresh output."""
    if shutil.which("git") is None:
        pytest.skip("git is not available")
    root = _project(tmp_path)
    assert _main(root, "generate") == 0
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


# ---------------------------------------------------------------------------
# check: the git freshness gate
# ---------------------------------------------------------------------------


def test_check_passes_in_a_fresh_repository(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _main(repo, "check") == 0

    out = capsys.readouterr().out
    assert out.endswith("check passed: data valid, output/ up to date, destinations current\n")
    assert "notice: git freshness check skipped" not in out


def test_check_ignores_uncommitted_changes_outside_output(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "notes.txt").write_text("scratch\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "notes")
    (repo / "notes.txt").write_text("edited\n", encoding="utf-8")

    assert _main(repo, "check") == 0


def test_check_fails_when_regenerated_output_differs_from_the_commit(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    about = json.loads((repo / "data" / "about.json").read_text(encoding="utf-8"))
    about["username"] = "Someone Else"
    (repo / "data" / "about.json").write_text(json.dumps(about), encoding="utf-8")

    assert _main(repo, "check") == 1

    assert capsys.readouterr().err.endswith(
        "error: output/ is stale — regenerated content differs from the "
        "committed tree (run `git diff -- output/`)\n"
    )


def test_check_without_git_says_freshness_was_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)

    assert _main(root, "check") == 0

    out = capsys.readouterr().out
    assert (
        f"notice: git freshness check skipped — {root} is not a git repository, "
        "or git is unavailable\n"
    ) in out
    assert out.endswith(
        "check passed: data valid, output/ freshness skipped, destinations current\n"
    )


def test_check_names_a_stale_destination_and_the_fix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS.split("[publishers.linkedin]")[0])

    assert _main(root, "check") == 1

    err = capsys.readouterr().err
    assert err == (
        "error: published destination is stale — app/data: about.json, social.json, "
        "skills.json, projects.json, manifest.json\n"
        "error: run `profile publish --execute` and commit the result\n"
    )


def test_check_stops_at_invalid_data(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "data" / "about.json").write_text("[]", encoding="utf-8")

    assert _main(root, "check") == 1
    assert not (root / "output").exists()


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


def test_unknown_generate_target_lists_the_choices(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)

    assert _main(root, "generate", "pdf") == 2

    assert capsys.readouterr().err == (
        "error: unknown target 'pdf' (choose from: all, cv, github-readme, linkedin, portfolio)\n"
    )


def test_generate_all_reports_the_manifest_it_wrote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)

    assert _main(root, "generate") == 0

    assert capsys.readouterr().out.endswith(f"Wrote {root / 'output' / 'manifest.json'}\n")


# ---------------------------------------------------------------------------
# The output manifest and published artifacts
# ---------------------------------------------------------------------------


def test_missing_output_manifest_says_how_to_create_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = discover_project(explicit=_project(tmp_path))

    assert cli._check_output_manifest(ctx) == 1

    assert capsys.readouterr().err == (
        "error: output/manifest.json is missing — run `profile generate`\n"
    )


def test_malformed_output_manifest_errors_are_located(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = discover_project(explicit=_project(tmp_path))
    ctx.output_dir.mkdir()
    (ctx.output_dir / "manifest.json").write_text(
        json.dumps({"schemaVersion": 1, "artifacts": [{"name": 5}], "extra": True}),
        encoding="utf-8",
    )

    assert cli._check_output_manifest(ctx) == 1

    err = capsys.readouterr().err.splitlines()
    assert err, "a malformed manifest must be reported"
    assert all(line.startswith("error: manifest.json: ") for line in err)
    assert any(line.startswith("error: manifest.json: artifacts.0") for line in err)
    assert err == sorted(err, key=lambda line: line.split(": ", 3)[3])


def _published(tmp_path: Path) -> tuple[Path, Path]:
    root = _project(tmp_path, CONFIG + PUBLISHERS)
    assert _main(root, "generate") == 0
    assert _main(root, "publish", "site", "--execute") == 0
    return root, root / "app" / "data"


def test_published_artifacts_that_are_valid_pass(tmp_path: Path) -> None:
    root, _ = _published(tmp_path)

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 0


def test_an_invalid_published_artifact_is_reported_with_its_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, destination = _published(tmp_path)
    capsys.readouterr()
    (destination / "social.json").write_text(json.dumps([]), encoding="utf-8")

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 1

    assert capsys.readouterr().err == (
        "error: published social.json: <root>: [] is not of type 'object'\n"
    )


def test_a_tampered_published_file_fails_its_digest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, destination = _published(tmp_path)
    capsys.readouterr()
    projects = json.loads((destination / "projects.json").read_text(encoding="utf-8"))
    (destination / "projects.json").write_text(json.dumps(projects), encoding="utf-8")

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 1

    assert capsys.readouterr().err == (
        "error: published manifest.json digest for projects.json does not match its content\n"
    )


def test_a_partly_published_destination_validates_what_is_there(tmp_path: Path) -> None:
    root, destination = _published(tmp_path)
    (destination / "about.json").unlink()
    (destination / "manifest.json").unlink()

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 0


def test_an_unpublished_destination_is_skipped(tmp_path: Path) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS)

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 0


def test_a_destination_without_a_path_is_not_validated_against_the_root(
    tmp_path: Path,
) -> None:
    """With no `destination`, the project root itself must not be read as one."""
    root = _project(tmp_path, CONFIG + '\n[publishers.site]\nkind = "filesystem"\n')
    (root / "about.json").write_text("[]", encoding="utf-8")

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 1


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


def test_publish_without_destinations_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)

    assert _main(root, "publish") == 0

    assert capsys.readouterr().out == "no publish destinations declared in profile.toml\n"


def test_publishing_one_target_runs_only_that_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS)
    assert _main(root, "generate") == 0
    capsys.readouterr()

    assert _main(root, "publish", "linkedin") == 0

    out = capsys.readouterr().out
    assert "linkedin  pending-manual  dry run — would write: linkedin.md\n" in out
    assert "site" not in out


def test_unknown_publish_target_lists_the_declared_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS)

    assert _main(root, "publish", "mastodon") == 2

    assert capsys.readouterr().err == (
        "error: unknown destination 'mastodon' (declared: site, linkedin)\n"
    )


def test_a_malformed_credential_declaration_refuses_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS + 'credential = "TOKEN"\n')

    assert _main(root, "publish") == 2

    assert capsys.readouterr().err == (
        "error: destination 'linkedin': credential must be a table of "
        'name = "ENV_VAR" entries, got str\n'
    )


def test_publish_rows_actions_and_dry_run_footer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS)
    assert _main(root, "generate") == 0
    capsys.readouterr()

    assert _main(root, "publish") == 0

    rows = capsys.readouterr().out.split("\n", 1)[1]
    assert rows == (
        "site      would-publish   dry run — would write: about.json, social.json, "
        "skills.json, projects.json, manifest.json\n"
        "                          -> re-run with --execute to publish\n"
        "linkedin  pending-manual  dry run — would write: linkedin.md\n"
        "                          -> re-run with --execute to publish\n"
        "\n"
        "dry run: nothing was published. Re-run with --execute to publish.\n"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "defect: the DESTINATION column is sized from destination names only, so "
        "when every name is shorter than the 11-character header it runs into "
        "STATUS ('DESTINATIONSTATUS') and the header no longer lines up with the rows"
    ),
)
def test_publish_header_stays_separate_for_short_destination_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS)
    assert _main(root, "generate") == 0
    capsys.readouterr()

    _main(root, "publish")

    header, first_row = capsys.readouterr().out.splitlines()[:2]
    assert header.startswith("DESTINATION ")
    assert header.index("STATUS") == first_row.index("would-publish")


def test_publish_table_widens_for_long_destination_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = CONFIG + '\n[publishers.portfolio-site-data]\nkind = "filesystem"\ndestination = "d"\n'
    root = _project(tmp_path, config)
    capsys.readouterr()

    _main(root, "publish")

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "DESTINATION          STATUS          DETAIL"
    assert lines[1].startswith("portfolio-site-data  would-publish   dry run")
    assert lines[2] == " " * 37 + "-> re-run with --execute to publish"


def test_an_unwritable_ledger_is_a_warning_and_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path, CONFIG + PUBLISHERS)
    assert _main(root, "generate") == 0

    def refuse(ctx: object, state: object) -> Path:
        raise OSError("read-only file system")

    monkeypatch.setattr(publish, "write_state", refuse)
    capsys.readouterr()

    assert _main(root, "publish", "--execute") == 1

    ledger = root / ".profilekit" / "publish-state.json"
    assert capsys.readouterr().err == (
        f"warning: could not write the publish ledger {ledger}: read-only file system — "
        "the next run may republish unchanged destinations\n"
    )


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def test_init_lists_what_it_created_and_what_to_do_next(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["init", str(tmp_path / "new")]) == 0

    out = capsys.readouterr().out
    assert out.startswith(f"created {tmp_path / 'new' / 'profile.toml'}\n")
    assert f"created {tmp_path / 'new' / 'data' / 'about.json'}\n" in out
    assert out.endswith(
        "\nNext: edit data/*.json, then run `profile validate` and `profile generate`.\n"
    )


def test_init_over_a_project_reports_the_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "profile.toml").write_text("", encoding="utf-8")

    assert cli.main(["init", str(tmp_path)]) == 1

    captured = capsys.readouterr()
    assert captured.err == (
        f"error: {tmp_path / 'profile.toml'} already exists; "
        "this directory is already a profilekit project\n"
    )
    assert captured.out == ""


def test_init_into_an_unwritable_place_reports_an_os_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("", encoding="utf-8")
    target = blocker / "project"

    assert cli.main(["init", str(target)]) == 1

    captured = capsys.readouterr()
    assert captured.err.startswith(f"error: cannot scaffold {target}: ")
    assert captured.out == ""


# ---------------------------------------------------------------------------
# Parser wiring
# ---------------------------------------------------------------------------


def test_usage_names_the_profile_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 2

    assert capsys.readouterr().err.startswith("usage: profile ")


def test_offline_is_a_flag_that_skips_network_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SKIP_ICON_CHECK")
    monkeypatch.delenv("SKIP_LINK_CHECK")
    root = _project(tmp_path)

    assert cli.main(["--offline", "--project", str(root), "list"]) == 0

    assert os.environ["SKIP_ICON_CHECK"] == "1"
    assert os.environ["SKIP_LINK_CHECK"] == "1"


def test_validate_uses_the_explicit_project_not_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv("PROFILEKIT_PROJECT", raising=False)

    assert _main(root, "validate") == 0


def test_a_missing_artifact_does_not_end_validation_of_the_others(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, destination = _published(tmp_path)
    capsys.readouterr()
    # Without the manifest, only the schema pass can notice the broken file.
    (destination / "about.json").unlink()
    (destination / "manifest.json").unlink()
    (destination / "social.json").write_text(json.dumps([]), encoding="utf-8")

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 1
    assert "error: published social.json: <root>" in capsys.readouterr().err


def test_an_unpublished_destination_does_not_end_validation_of_the_next(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = CONFIG + '\n[publishers.draft]\nkind = "filesystem"\ndestination = "draft/data"\n'
    root = _project(tmp_path, config + PUBLISHERS)
    assert _main(root, "generate") == 0
    assert _main(root, "publish", "site", "--execute") == 0
    (root / "app" / "data" / "social.json").write_text(json.dumps([]), encoding="utf-8")

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 1


def test_a_nested_published_error_has_a_dotted_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, destination = _published(tmp_path)
    capsys.readouterr()
    projects = json.loads((destination / "projects.json").read_text(encoding="utf-8"))
    projects[0]["name"] = 5
    (destination / "projects.json").write_text(json.dumps(projects), encoding="utf-8")

    assert cli._published_artifacts_are_valid(discover_project(explicit=root)) == 1

    assert "error: published projects.json: 0.name: 5 is not of type 'string'\n" in (
        capsys.readouterr().err
    )


def test_check_validates_the_explicit_project_not_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv("PROFILEKIT_PROJECT", raising=False)

    assert _main(root, "check") == 0


def test_output_dir_flag_redirects_generation(tmp_path: Path) -> None:
    root = _project(tmp_path)
    target = tmp_path / "build"

    assert _main(root, "--output-dir", str(target), "generate", "linkedin") == 0

    assert (target / "linkedin.md").is_file()
    assert not (root / "output").exists()


def test_data_dir_flag_selects_the_data_to_validate(tmp_path: Path) -> None:
    root = _project(tmp_path)
    shutil.move(root / "data", tmp_path / "moved-data")

    assert _main(root, "validate") == 1
    assert _main(root, "--data-dir", str(tmp_path / "moved-data"), "validate") == 0


# ---------------------------------------------------------------------------
# --help: the CLI's own documentation of every command and option
# ---------------------------------------------------------------------------

HELP = {
    (): [
        "usage: profile [-h] [--offline] [--project DIR] [--data-dir DIR] [--output-dir DIR]",
        "Turn structured profile data into generated artifacts.",
        "generate Run one generator or all of them.",
        "validate Validate the data directory against the schemas.",
        "check Validate, regenerate, and verify nothing is stale.",
        "list List available generation targets.",
        "publish Publish artifacts to configured destinations.",
        "init Scaffold a new project with example data.",
        "--offline Skip network reachability probes for icons and links.",
        "--project DIR Project directory (highest precedence; overrides PROFILEKIT_PROJECT).",
        "--data-dir DIR Override the project's canonical data directory.",
        "--output-dir DIR Override the project's generated-artifact directory.",
    ],
    ("generate",): [
        "target Target to generate: 'all' (default), or a registered target (see `profile list`).",
    ],
    ("publish",): [
        "target Destination to publish: 'all' (default) or a declared name.",
        "--execute Actually publish. Without this, publish performs a dry run.",
        "--require-credentials Treat a missing credential as a failure instead of "
        "skipping the destination.",
    ],
    ("init",): [
        "directory Where to create the project (default: the working directory).",
    ],
}


@pytest.mark.parametrize("command", list(HELP), ids=lambda c: " ".join(c) or "profile")
def test_help_documents_every_command_and_option(
    command: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main([*command, "--help"])

    assert excinfo.value.code == 0
    # Whitespace-normalised: argparse wraps and aligns columns by terminal width.
    text = " ".join(capsys.readouterr().out.split())
    for line in HELP[command]:
        assert line in text
