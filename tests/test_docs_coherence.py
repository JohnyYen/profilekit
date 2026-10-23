"""Documentation must not describe behavior the code does not have.

Each test extracts one kind of claim from the user-facing docs and checks it
against the code: a ``profile`` invocation against the real argparse parser, a
publish status against the ``Status`` literal, a repository path against the
working tree, a ``profile.toml`` example against the config validator.

Install commands (``pip install profilekit``) are deliberately not checked:
the package is pre-release and the README states the intended install path.
"""

from __future__ import annotations

import argparse
import re
import shlex
import tomllib
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from profilekit import cli, registry
from profilekit.config import KNOWN_SECTIONS, ConfigError, validate_config
from profilekit.publishers import Status

ROOT = Path(__file__).resolve().parent.parent
DOCS = sorted(
    [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md"]
    + list((ROOT / "docs").glob("*.md"))
)
SCHEMAS_DIR = ROOT / "src" / "profilekit" / "schemas"


@dataclass(frozen=True)
class Claim:
    """One piece of text a doc presents as fact, with where it was found."""

    doc: Path
    line: int
    text: str

    @property
    def where(self) -> str:
        return f"{self.doc.relative_to(ROOT)}:{self.line}"


# --- extraction -------------------------------------------------------------

_FENCE = re.compile(r"^\s*```(\S*)")
_SPAN = re.compile(r"`([^`\n]+)`")
_LINK = re.compile(r"\]\(([^)\s]+)\)")


def _lines(doc: Path) -> Iterator[tuple[int, str, str | None]]:
    """Yield ``(line_number, text, fence_language)``; language is None outside fences."""
    language: str | None = None
    for number, text in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
        fence = _FENCE.match(text)
        if fence:
            language = None if language is not None else fence.group(1)
            continue
        yield number, text, language


def code_spans(doc: Path) -> Iterator[Claim]:
    """Inline backtick spans outside fenced blocks."""
    for number, text, language in _lines(doc):
        if language is None:
            for match in _SPAN.finditer(text):
                yield Claim(doc, number, match.group(1).strip())


def links(doc: Path) -> Iterator[Claim]:
    for number, text, language in _lines(doc):
        if language is None:
            for match in _LINK.finditer(text):
                yield Claim(doc, number, match.group(1))


def fenced_blocks(doc: Path, languages: set[str]) -> Iterator[Claim]:
    """Whole fenced blocks in one of *languages*, located at their first line."""
    start = 0
    body: list[str] = []
    current: str | None = None
    for number, text, language in _lines(doc):
        if language != current:
            if current in languages and body:
                yield Claim(doc, start, "\n".join(body))
            current, start, body = language, number, []
        if language is not None:
            body.append(text)
    if current in languages and body:
        yield Claim(doc, start, "\n".join(body))


def profile_invocations() -> Iterator[Claim]:
    """Every ``profile ...`` command line, from inline spans and shell blocks."""
    for doc in DOCS:
        for span in code_spans(doc):
            if span.text.startswith("profile "):
                yield span
        for block in fenced_blocks(doc, {"sh", "bash", "console", "shell"}):
            for offset, line in enumerate(block.text.splitlines()):
                command = line.split("#", 1)[0].strip().removeprefix("$ ")
                if command.startswith("profile "):
                    yield Claim(doc, block.line + offset, command)


# --- the parser as the source of truth --------------------------------------


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def _flags(parser: argparse.ArgumentParser) -> set[str]:
    return {flag for action in parser._actions for flag in action.option_strings}


def _flags_taking_a_value(parser: argparse.ArgumentParser) -> set[str]:
    return {
        flag for action in parser._actions if action.nargs != 0 for flag in action.option_strings
    }


PARSER = cli.build_parser()
SUBCOMMANDS = _subparsers(PARSER)
GLOBAL_FLAGS = _flags(PARSER)
ALL_FLAGS = GLOBAL_FLAGS.union(*(_flags(sub) for sub in SUBCOMMANDS.values()))

#: Flags named in the docs that belong to another tool, not to `profile`.
FOREIGN_FLAGS = {"--cov-fail-under"}  # pytest, in CONTRIBUTING.md


def _command_problems(claim: Claim) -> list[str]:
    """Return what is wrong with one documented ``profile`` invocation."""
    tokens = [t.strip("[]") for t in shlex.split(claim.text)[1:]]
    tokens = [t for t in tokens if t]
    # Global flags (and their values) may precede the subcommand.
    takes_value = _flags_taking_a_value(PARSER)
    while tokens and tokens[0].startswith("--"):
        flag = tokens.pop(0)
        if flag not in GLOBAL_FLAGS:
            return [f"unknown global flag {flag!r}; known: {sorted(GLOBAL_FLAGS)}"]
        if flag in takes_value and tokens:
            tokens.pop(0)
    if not tokens:
        return []
    name, rest = tokens[0], tokens[1:]
    if name not in SUBCOMMANDS:
        return [f"no subcommand {name!r}; the CLI has: {sorted(SUBCOMMANDS)}"]
    allowed = GLOBAL_FLAGS | _flags(SUBCOMMANDS[name])
    return [
        f"`profile {name}` has no flag {flag!r}; it accepts: {sorted(allowed)}"
        for flag in rest
        if flag.startswith("--") and flag.split("=", 1)[0] not in allowed
    ]


def test_documented_profile_commands_exist() -> None:
    claims = list(profile_invocations())
    assert claims, "extraction found no `profile` invocations; the extractor is broken"
    problems = [
        f"{claim.where}: `{claim.text}` -> {problem}"
        for claim in claims
        for problem in _command_problems(claim)
    ]
    assert not problems, "Docs name CLI commands or flags that do not exist:\n" + "\n".join(
        problems
    )


def test_standalone_documented_flags_exist() -> None:
    problems = [
        f"{span.where}: `{span.text}` -> no `profile` command accepts {flag!r}"
        for doc in DOCS
        for span in code_spans(doc)
        if span.text.startswith("--")
        for flag in [span.text.split()[0].split("=", 1)[0]]
        if flag not in ALL_FLAGS | FOREIGN_FLAGS
    ]
    assert not problems, "Docs name flags no command accepts:\n" + "\n".join(problems)


# --- publish statuses -------------------------------------------------------

STATUSES = set(typing.get_args(Status))
#: A backticked word reads as a publish status when it is a past participle
#: (`published`, `skipped`) or a hyphenated modal state (`would-publish`).
_STATUS_LIKE = re.compile(r"^(?:[a-z]+ed|(?:would|pending)-[a-z]+)$")


def test_documented_publish_statuses_exist() -> None:
    problems = [
        f"{span.where}: `{span.text}` reads as a publish status, but Status is {sorted(STATUSES)}"
        for doc in DOCS
        for span in code_spans(doc)
        if _STATUS_LIKE.match(span.text) and span.text not in STATUSES
    ]
    assert not problems, "Docs name publish statuses the code cannot return:\n" + "\n".join(
        problems
    )


def test_every_publish_status_is_documented() -> None:
    documented = {span.text for doc in (ROOT / "docs").glob("*.md") for span in code_spans(doc)}
    missing = sorted(STATUSES - documented)
    assert not missing, (
        f"Status values never named in backticks anywhere under docs/: {missing}. "
        "A status a user can see must be explained."
    )


# --- repository paths -------------------------------------------------------

#: Top-level directories of this repository. A span starting with one of them
#: is a claim about this checkout, not about a user's project.
_REPO_DIRS = ("src/", "docs/", "openspec/", "tests/", "apps/", ".github/")
_ROOT_FILE = re.compile(r"^(?:[A-Z][A-Z_]*\.md|LICENSE|pyproject\.toml)$")


def _path_claims() -> Iterator[tuple[Claim, Path]]:
    """Yield each path-like claim with the location it asserts exists."""
    for doc in DOCS:
        for span in code_spans(doc):
            text = span.text
            if " " in text:
                continue
            if text.startswith(_REPO_DIRS) or _ROOT_FILE.match(text):
                yield span, ROOT / text
            elif text.endswith(".schema.json"):
                yield span, SCHEMAS_DIR / text
        for link in links(doc):
            target = link.text.split("#", 1)[0]
            if target and "://" not in target and not target.startswith("mailto:"):
                yield link, doc.parent / target


def _exists(path: Path) -> bool:
    if any(ch in path.name for ch in "*?["):
        return any(path.parent.glob(path.name))
    return path.exists()


def test_documented_repository_paths_exist() -> None:
    claims = list(_path_claims())
    assert claims, "extraction found no paths; the extractor is broken"
    problems = [
        f"{claim.where}: `{claim.text}` -> {path.relative_to(ROOT)} does not exist"
        for claim, path in claims
        if not _exists(path)
    ]
    assert not problems, "Docs name paths that do not exist:\n" + "\n".join(problems)


# --- configuration examples -------------------------------------------------

BUILTIN_KINDS = {"filesystem", "manual"}
ENTRY_POINT_GROUPS = {registry.GENERATOR_GROUP, registry.PUBLISHER_GROUP}
#: `[paths]` keys the context resolves; derived from its source so a renamed
#: key cannot leave the docs behind.
PATH_KEYS = set(
    re.findall(
        r'paths\.get\("(\w+)"\)', (ROOT / "src/profilekit/context.py").read_text(encoding="utf-8")
    )
)


def _config_problems(
    doc: Path, document: dict[str, typing.Any], plugin_kinds: set[str]
) -> list[str]:
    entry_points = document.get("project", {}).get("entry-points")
    if entry_points is not None:  # a pyproject.toml fragment
        return [
            f"entry-point group {group!r} is not read by profilekit; "
            f"it reads {sorted(ENTRY_POINT_GROUPS)}"
            for group in entry_points
            if group not in ENTRY_POINT_GROUPS
        ]
    problems: list[str] = []
    config = {"project": {"config_version": 1}, **document}  # a profile.toml fragment
    try:
        validate_config(config, source=str(doc.relative_to(ROOT)))
    except ConfigError as exc:
        problems.append(str(exc))
    for name, table in document.get("publishers", {}).items():
        kind = table.get("kind")
        if kind not in BUILTIN_KINDS | plugin_kinds:
            problems.append(
                f"[publishers.{name}] kind {kind!r} is neither built in "
                f"({sorted(BUILTIN_KINDS)}) nor registered by an example in this doc"
            )
    problems += [
        f"[paths] has no key {key!r}; the context reads {sorted(PATH_KEYS)}"
        for key in document.get("paths", {})
        if key not in PATH_KEYS
    ]
    return problems


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: str(d.relative_to(ROOT)))
def test_documented_toml_examples_are_accepted(doc: Path) -> None:
    blocks = list(fenced_blocks(doc, {"toml"}))
    parsed = [(block, tomllib.loads(block.text)) for block in blocks]
    # A doc that registers a publisher entry point may then use it as a kind.
    plugin_kinds = {
        name
        for _, document in parsed
        for name in document.get("project", {})
        .get("entry-points", {})
        .get(registry.PUBLISHER_GROUP, {})
    }
    problems = [
        f"{block.where}: {problem}"
        for block, document in parsed
        for problem in _config_problems(doc, document, plugin_kinds)
    ]
    assert not problems, "Docs show configuration the code rejects:\n" + "\n".join(problems)


def test_documented_section_key_spans_exist() -> None:
    """Inline ``[paths] schemas`` style references name a real section and key."""
    pattern = re.compile(r"^\[(\w+)\] (\w+)$")
    problems = []
    for doc in DOCS:
        for span in code_spans(doc):
            match = pattern.match(span.text)
            if not match:
                continue
            section, key = match.groups()
            if section == "paths" and key not in PATH_KEYS:
                problems.append(f"{span.where}: `{span.text}` -> known keys {sorted(PATH_KEYS)}")
            elif section not in KNOWN_SECTIONS:
                problems.append(f"{span.where}: `{span.text}` -> no section [{section}]")
    assert not problems, "Docs name configuration keys that do not exist:\n" + "\n".join(problems)
