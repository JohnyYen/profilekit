"""Behavior pinned down by mutation testing of ``profilekit.validate``.

``profile validate`` is read by a person fixing their data, so its report is
the product: the table, the error lines, the warnings on stderr, and which
data each reachability probe is handed. Each test kills mutants that survived
the baseline run (see ``docs/quality/mutation-baseline.md``).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from profilekit import icons, links, validate
from profilekit.context import ProjectContext

FIXTURE_DATA = Path(__file__).resolve().parent / "fixtures" / "project" / "data"

BANNER = "=" * 60 + "\nProfile Data Validation\n" + "=" * 60 + "\n\n"
HEADER = f"{'File':<30} {'Status':<10}\n" + "-" * 40 + "\n"


def _row(name: str, status: str) -> str:
    return f"{name:<30} {status:<10}\n"


@pytest.fixture
def ctx(tmp_path: Path) -> ProjectContext:
    shutil.copytree(FIXTURE_DATA, tmp_path / "data")
    return ProjectContext.for_root(tmp_path)


@pytest.fixture
def probes(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[tuple[Any, ...]]]:
    """Replace the network probes with spies that record what they were given."""
    calls: dict[str, list[tuple[Any, ...]]] = {"icons": [], "links": []}

    def check_icons(skills: Any) -> list[str]:
        calls["icons"].append((skills,))
        return ["icon probe"]

    def check_links(projects: Any, social: Any) -> list[str]:
        calls["links"].append((projects, social))
        return ["link probe"]

    monkeypatch.setattr(icons, "check_icons", check_icons)
    monkeypatch.setattr(links, "check_links", check_links)
    return calls


def _data(ctx: ProjectContext, name: str) -> Any:
    return json.loads((ctx.data_dir / name).read_text(encoding="utf-8"))


def _rewrite(ctx: ProjectContext, name: str, payload: Any) -> None:
    (ctx.data_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def test_a_valid_project_prints_the_full_report(
    ctx: ProjectContext, probes: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    assert validate.main(ctx) == 0

    out, err = capsys.readouterr()
    rows = "".join(_row(name, "PASS") for name in validate.REQUIRED_FILES)
    assert out == BANNER + HEADER + rows + "\nAll validations passed!\n"
    assert err == "WARNING (icon): icon probe\nWARNING (link): link probe\n"


def test_probes_receive_the_parsed_data_files(ctx: ProjectContext, probes: dict) -> None:
    validate.main(ctx)

    assert probes["icons"] == [(_data(ctx, "skills.json"),)]
    assert probes["links"] == [(_data(ctx, "projects.json"), _data(ctx, "social.json"))]


def test_a_failed_file_is_reported_and_withheld_from_the_probes(
    ctx: ProjectContext, probes: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    social = _data(ctx, "social.json")
    social["github"] = 7
    _rewrite(ctx, "social.json", social)
    _rewrite(ctx, "skills.json", [])

    assert validate.main(ctx) == 1

    out, _ = capsys.readouterr()
    assert (
        _row("social.json", "FAIL") + "  ERROR: social.json at github: 7 is not of type 'string'\n"
        in out
    )
    assert _row("about.json", "PASS") + _row("social.json", "FAIL") in out
    assert _row("skills.json", "FAIL") + "  ERROR: skills.json: [] is not of type 'object'\n" in out
    assert out.endswith("\nSome validations FAILED!\n")
    assert probes["icons"] == []
    assert probes["links"] == [(_data(ctx, "projects.json"), {})]


def test_failed_projects_are_withheld_as_an_empty_list(ctx: ProjectContext, probes: dict) -> None:
    _rewrite(ctx, "projects.json", {"not": "a list"})

    validate.main(ctx)

    assert probes["links"] == [([], _data(ctx, "social.json"))]


def test_unmatched_and_excess_highlights_are_warned_about(
    ctx: ProjectContext, probes: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    about = _data(ctx, "about.json")
    about["portfolioHighlights"] = ["Note G", *[f"Ghost {i}" for i in range(6)]]
    _rewrite(ctx, "about.json", about)

    assert validate.main(ctx) == 0

    err = capsys.readouterr().err
    assert "WARNING: portfolioHighlights has 7 entries; only 6 are recommended.\n" in err
    assert (
        "WARNING: portfolioHighlights: 'Ghost 0' does not match any project in projects.json.\n"
        in err
    )
    assert "'Note G'" not in err


def test_six_highlights_are_within_the_recommendation() -> None:
    about = {"portfolioHighlights": [f"P{i}" for i in range(6)]}
    projects = [{"name": f"P{i}"} for i in range(6)]

    assert validate.validate_portfolio_highlights(about, projects) == []


def test_highlights_are_not_checked_when_projects_failed(
    ctx: ProjectContext, probes: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    about = _data(ctx, "about.json")
    about["portfolioHighlights"] = ["Ghost"]
    _rewrite(ctx, "about.json", about)
    _rewrite(ctx, "projects.json", {"not": "a list"})

    validate.main(ctx)

    assert "portfolioHighlights" not in capsys.readouterr().err


def test_a_crashing_highlight_check_becomes_a_warning(
    ctx: ProjectContext,
    probes: dict,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(about: Any, projects: Any) -> list[str]:
        raise KeyError("name")

    monkeypatch.setattr(validate, "validate_portfolio_highlights", boom)

    assert validate.main(ctx) == 0

    err = capsys.readouterr().err
    assert err.startswith("WARNING: Could not validate portfolioHighlights: 'name'\n")


def test_highlight_check_receives_both_parsed_files(
    ctx: ProjectContext, probes: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        validate, "validate_portfolio_highlights", lambda a, p: seen.append((a, p)) or []
    )

    validate.main(ctx)

    assert seen == [(_data(ctx, "about.json"), _data(ctx, "projects.json"))]


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------


def test_an_unmapped_file_looks_for_a_schema_named_after_it(ctx: ProjectContext) -> None:
    passed, errors = validate.validate_file("hobbies.json", ctx)

    assert passed is False
    assert errors == [
        f"Schema file not found: {validate.packaged_schemas() / 'hobbies.schema.json'}"
    ]


def test_a_missing_data_file_is_named(ctx: ProjectContext) -> None:
    (ctx.data_dir / "about.json").unlink()

    assert validate.validate_file("about.json", ctx) == (
        False,
        [f"Data file not found: {ctx.data_dir / 'about.json'}"],
    )


def test_undecodable_data_is_reported_as_unreadable(ctx: ProjectContext) -> None:
    (ctx.data_dir / "about.json").write_bytes(b'{"username": "\xff"}')

    passed, errors = validate.validate_file("about.json", ctx)

    assert passed is False
    assert len(errors) == 1
    assert errors[0].startswith("about.json: cannot read: 'utf-8' codec can't decode byte 0xff")


def test_errors_are_sorted_and_located(ctx: ProjectContext) -> None:
    """Sorted, so the report is stable; jsonschema itself yields `linkedin` first."""
    _rewrite(ctx, "social.json", {"github": 7})

    passed, errors = validate.validate_file("social.json", ctx)

    assert passed is False
    assert errors == [
        "social.json: 'email' is a required property",
        "social.json: 'linkedin' is a required property",
        "social.json at github: 7 is not of type 'string'",
    ]


def test_nested_error_locations_are_dotted(ctx: ProjectContext) -> None:
    about = _data(ctx, "about.json")
    about["currentFocus"] = [{"title": "t", "description": 5}]
    _rewrite(ctx, "about.json", about)

    _, errors = validate.validate_file("about.json", ctx)

    assert errors == ["about.json at currentFocus.0.description: 5 is not of type 'string'"]


def test_highlights_are_checked_when_only_about_and_projects_pass(
    ctx: ProjectContext, probes: dict, capsys: pytest.CaptureFixture[str]
) -> None:
    about = _data(ctx, "about.json")
    about["portfolioHighlights"] = ["Ghost"]
    _rewrite(ctx, "about.json", about)
    for name in ("social.json", "experience.json", "education.json", "skills.json"):
        _rewrite(ctx, name, 42)

    assert validate.main(ctx) == 1

    assert "WARNING: portfolioHighlights: 'Ghost' does not match" in capsys.readouterr().err
