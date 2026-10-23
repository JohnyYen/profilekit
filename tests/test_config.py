"""``profile.toml`` parsing and validation.

Two rules pull in opposite directions on purpose:

- An **unknown top-level section is an error.** A typo like ``[path]`` for
  ``[paths]`` would otherwise be silently ignored and the tool would quietly
  use defaults, which is the worst possible outcome — the user's configuration
  appears accepted and does nothing.
- An **unknown key inside a ``[generators.X]`` table passes through.** Each
  generator owns the validation of its own options, and a third-party
  generator registered by entry point must be configurable without the core
  knowing its option names.
"""

from pathlib import Path

import pytest

from profilekit.config import (
    KNOWN_SECTIONS,
    ConfigError,
    load_config,
    validate_config,
)
from profilekit.context import discover_project


def _write(root: Path, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "profile.toml").write_text(body, encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Unknown sections fail loudly
# ---------------------------------------------------------------------------


def test_unknown_top_level_section_is_an_error(tmp_path: Path) -> None:
    root = _write(tmp_path / "p", '[project]\nconfig_version = 1\n\n[pathz]\ndata = "d"\n')
    with pytest.raises(ConfigError) as exc_info:
        load_config(root / "profile.toml")
    assert "pathz" in str(exc_info.value)


def test_a_near_miss_section_name_is_an_error_not_a_silent_default(tmp_path: Path) -> None:
    """``[path]`` instead of ``[paths]`` must not be quietly ignored."""
    root = _write(tmp_path / "p", '[project]\nconfig_version = 1\n\n[path]\noutput = "dist"\n')
    with pytest.raises(ConfigError):
        load_config(root / "profile.toml")


def test_every_known_section_is_accepted(tmp_path: Path) -> None:
    body = "[project]\nconfig_version = 1\n\n" + "".join(
        f"[{section}]\n" for section in KNOWN_SECTIONS if section != "project"
    )
    root = _write(tmp_path / "p", body)
    assert load_config(root / "profile.toml") is not None


def test_unknown_generator_option_passes_through(tmp_path: Path) -> None:
    """A generator owns its own options; the core must not gatekeep them."""
    root = _write(
        tmp_path / "p",
        "[project]\nconfig_version = 1\n\n"
        '[generators.github-readme]\nsome_future_option = "value"\n',
    )
    ctx = discover_project(explicit=root)
    assert ctx.generator_options("github-readme")["some_future_option"] == "value"


# ---------------------------------------------------------------------------
# Version and shape
# ---------------------------------------------------------------------------


def test_missing_config_version_is_an_error(tmp_path: Path) -> None:
    root = _write(tmp_path / "p", "[project]\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config(root / "profile.toml")
    assert "config_version" in str(exc_info.value)


def test_unsupported_config_version_is_an_error(tmp_path: Path) -> None:
    """A future format must fail with a readable message, not a stack trace."""
    root = _write(tmp_path / "p", "[project]\nconfig_version = 99\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config(root / "profile.toml")
    assert "99" in str(exc_info.value)


def test_invalid_toml_reports_the_file(tmp_path: Path) -> None:
    root = _write(tmp_path / "p", "[project\nconfig_version = 1\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config(root / "profile.toml")
    assert "profile.toml" in str(exc_info.value)


def test_section_must_be_a_table(tmp_path: Path) -> None:
    """A bare key before the first header is top-level, and `paths` must be a table."""
    root = _write(tmp_path / "p", 'paths = "not-a-table"\n\n[project]\nconfig_version = 1\n')
    with pytest.raises(ConfigError) as exc_info:
        load_config(root / "profile.toml")
    assert "paths" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Paths honored end to end
# ---------------------------------------------------------------------------


def test_profile_toml_overrides_paths(tmp_path: Path) -> None:
    root = _write(
        tmp_path / "p",
        "[project]\nconfig_version = 1\n\n"
        '[paths]\ndata = "canonical"\noutput = "dist"\nassets = "media"\nschemas = "sch"\n',
    )
    ctx = discover_project(explicit=root)

    assert ctx.data_dir == root.resolve() / "canonical"
    assert ctx.output_dir == root.resolve() / "dist"
    assert ctx.assets_dir == root.resolve() / "media"
    assert ctx.schemas_dir == root.resolve() / "sch"


def test_publisher_destinations_are_exposed(tmp_path: Path) -> None:
    root = _write(
        tmp_path / "p",
        "[project]\nconfig_version = 1\n\n"
        '[publishers.portfolio-data]\nkind = "filesystem"\n'
        'destination = "apps/portfolio/app/data"\n\n'
        '[publishers.linkedin]\nkind = "manual"\n',
    )
    destinations = discover_project(explicit=root).publisher_destinations()

    assert destinations["portfolio-data"]["kind"] == "filesystem"
    assert destinations["portfolio-data"]["destination"] == "apps/portfolio/app/data"
    assert destinations["linkedin"]["kind"] == "manual"


def test_a_non_table_publisher_entry_is_an_error_naming_it(tmp_path: Path) -> None:
    """`site = "oops"` under [publishers] is a typo, not "no destinations"."""
    root = _write(
        tmp_path / "p",
        '[project]\nconfig_version = 1\n\n[publishers]\nsite = "oops"\n',
    )
    with pytest.raises(ConfigError) as exc_info:
        load_config(root / "profile.toml")
    message = str(exc_info.value)
    assert "[publishers.site]" in message
    assert "must be a table" in message
    assert "str" in message


def test_a_non_table_publisher_entry_fails_publish_with_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from profilekit import cli

    root = _write(
        tmp_path / "p",
        '[project]\nconfig_version = 1\n\n[publishers]\nsite = "oops"\n',
    )
    rc = cli.main(["--project", str(root), "publish"])
    captured = capsys.readouterr()

    assert rc == 2
    assert "[publishers.site] must be a table" in captured.err
    assert "no publish destinations declared" not in captured.out
    assert "Traceback" not in captured.err + captured.out


def test_validate_config_is_usable_on_an_in_memory_mapping() -> None:
    """Validation is separable from file IO so callers can check a dict."""
    validate_config({"project": {"config_version": 1}}, source="<memory>")
    with pytest.raises(ConfigError):
        validate_config({"project": {"config_version": 1}, "nope": {}}, source="<memory>")
