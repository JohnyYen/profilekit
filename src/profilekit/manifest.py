"""The versioned output contract.

A consumer writing a frontend against these artifacts needs two things: a way
to know the shape it is reading, and a promise about when that shape changes.
Without both, every consumer is coupled to whatever the generators happened to
emit on the day they integrated — and the maintainer cannot change anything
without silently breaking strangers.

Two mechanisms, because one is not enough:

JSON artifacts carry a top-level ``schemaVersion``, which is the natural place
for it — a consumer reading the file already has the number in hand.

Markdown and YAML artifacts cannot carry a field, so ``output/manifest.json``
is the version index for **every** artifact in ``output/``, JSON or not. It
also carries a content digest per artifact, so a consumer can detect changes
without diffing content. It does not cover publish destinations: a
``filesystem`` destination gets a manifest of its own (``build_published``),
and publish idempotency comes from ``plan().changes`` and the publish ledger,
not from this file.

**No timestamp.** Design decision D6 specified a ``generatedAt`` field. It is
deliberately omitted: the manifest is a committed artifact, and a wall-clock
value inside a file that is version-controlled and diffed destroys the
byte-identical freshness guarantee R6 established — every regeneration would
report drift while telling nobody anything about content. Provenance belongs
to the publish layer, which records when it published, not to a generated
file. The digests already answer "is this the same output?" precisely.

Compatibility policy
--------------------

``schemaVersion`` is a single integer per artifact — not a semver triple —
because the only question a consumer asks is "can I still read this?".

Adding an **optional** field does not bump it. That preserves the
use-if-present-else-fallback rule this project already follows, and a version
that bumps on every addition trains consumers to ignore the number, which is
worse than having no number at all.

Removing a field, retyping one, or newly requiring an existing one does bump
it. Each of those breaks a consumer that was reading the previous shape.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from profilekit.context import ProjectContext

from profilekit.safe_io import write_file

#: The current output-contract version. One integer, bumped only by a
#: breaking change as defined in this module's docstring.
SCHEMA_VERSION = 1

MANIFEST_FILENAME = "manifest.json"

#: Which generator produces which artifact, for the manifest index.
ARTIFACT_GENERATORS = {
    "github-readme.md": "github-readme",
    "linkedin.md": "linkedin",
    "portfolio.md": "portfolio",
    "cv.yml": "cv",
    "cv.md": "cv",
}


def digest_file(path: Path) -> str:
    """Return the sha256 of *path*'s bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_text(text: str) -> str:
    """Return the sha256 of *text* encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(output_dir: Path) -> dict[str, Any]:
    """Build the manifest index for every artifact in *output_dir*.

    An artifact is a regular, non-hidden, non-symlink file directly inside
    *output_dir*.
    Hidden files (a leading ``.``) are skipped: ``.gitkeep``, editor swap
    files and ``.DS_Store`` are tooling noise, and indexing them made the
    committed contract depend on whose machine last ran the generators.

    Names outside :data:`ARTIFACT_GENERATORS` are still indexed, with
    generator ``"unknown"``. Generators do not declare what they write, so a
    third-party generator's artifact is only recognisable as a visible file
    in the output directory; dropping unknown names would leave plugin output
    outside the contract.

    Symlinks are skipped, wherever they point. Generators never create one,
    and the filesystem publisher refuses to follow one, so a link in the
    output directory is not an artifact; following it would put a file from
    outside the project into the committed contract. Skipping (rather than
    failing the run) matches how other foreign entries, such as dotfiles,
    are treated: the manifest describes what the generators wrote.

    The manifest never indexes itself: its own digest would change every time
    it was written, which makes it useless as a comparison reference.

    Artifact entries are sorted by name, and the manifest carries no
    timestamp, so two runs over identical data produce a byte-identical file.
    """
    artifacts: list[dict[str, Any]] = []
    if not output_dir.is_dir():
        return {"schemaVersion": SCHEMA_VERSION, "artifacts": artifacts}

    for path in sorted(output_dir.glob("*")):
        if (
            path.is_symlink()
            or not path.is_file()
            or path.name.startswith(".")
            or path.name == MANIFEST_FILENAME
        ):
            continue
        artifacts.append(
            {
                "name": path.name,
                "generator": ARTIFACT_GENERATORS.get(path.name, "unknown"),
                "schemaVersion": SCHEMA_VERSION,
                "sha256": digest_file(path),
                "bytes": path.stat().st_size,
            }
        )

    return {"schemaVersion": SCHEMA_VERSION, "artifacts": artifacts}


def write(ctx: ProjectContext) -> Path:
    """Write ``manifest.json`` into the context's output directory."""
    index = build(ctx.output_dir)
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    return write_file(
        ctx.output_dir / MANIFEST_FILENAME,
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        root=ctx.output_dir,
        overwrite=True,
    )


def read(output_dir: Path) -> object | None:
    """Read the manifest from *output_dir*, or ``None`` when absent.

    The parsed JSON is returned unvalidated, typed as ``object``: its shape is
    only known after a caller checks it against ``manifest.schema.json``.
    """
    path = output_dir / MANIFEST_FILENAME
    if not path.is_file():
        return None
    parsed: object = json.loads(path.read_text(encoding="utf-8"))
    return parsed


def build_published(files: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """Build the manifest a filesystem publisher writes next to its files.

    *files* are ``(name, content)`` pairs as they will be written. The output
    manifest above indexes ``output/``; nothing in a publish destination
    carried a version, so a consumer of the array-shaped ``projects.json`` had
    no way to read one. This index is that version, beside the file itself.

    Same determinism rules as :func:`build`: entries sorted by name, no
    timestamp, and never an entry for the manifest itself.
    """
    entries = [
        {
            "name": name,
            "schemaVersion": SCHEMA_VERSION,
            "sha256": digest_text(content),
            "bytes": len(content.encode("utf-8")),
        }
        for name, content in sorted(files)
        if name != MANIFEST_FILENAME
    ]
    return {"schemaVersion": SCHEMA_VERSION, "files": entries}


def digest_mismatches(directory: Path, entries: Iterable[Mapping[str, Any]]) -> list[str]:
    """Describe every entry whose file in *directory* is missing or differs.

    Entry names must already be validated as plain file names: this joins
    them onto *directory* as-is.
    """
    problems: list[str] = []
    for entry in entries:
        path = directory / entry["name"]
        if not path.is_file():
            problems.append(f"lists missing file {entry['name']}")
        elif digest_file(path) != entry["sha256"]:
            problems.append(f"digest for {entry['name']} does not match its content")
    return problems


def stamp(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return *payload* with the contract version as its first key.

    First so the field is visible at the top of the file. A consumer opening
    the artifact should not have to scroll to learn what it is reading.
    """
    return {"schemaVersion": SCHEMA_VERSION, **payload}


# ---------------------------------------------------------------------------
# Compatibility checking
# ---------------------------------------------------------------------------


def _properties(schema: Mapping[str, Any]) -> dict[str, Any]:
    props = schema.get("properties")
    return dict(props) if isinstance(props, dict) else {}


def _required(schema: Mapping[str, Any]) -> set[str]:
    required = schema.get("required")
    return set(required) if isinstance(required, list) else set()


def is_backward_compatible(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    """Report whether *after* can still be read by a consumer of *before*.

    Compatible: adding an optional property.

    Breaking: removing a property, changing its declared type, newly requiring
    a property that was optional, or requiring a property that did not exist.
    Each of those breaks a consumer that was reading the previous shape — and
    the last one is the subtle case, because the property itself is additive
    while the requirement is not.
    """
    before_props, after_props = _properties(before), _properties(after)

    for name, spec in before_props.items():
        if name not in after_props:
            return False
        if spec.get("type") != after_props[name].get("type"):
            return False

    newly_required = _required(after) - _required(before)
    return not newly_required


__all__ = [
    "ARTIFACT_GENERATORS",
    "MANIFEST_FILENAME",
    "SCHEMA_VERSION",
    "build",
    "build_published",
    "digest_file",
    "digest_mismatches",
    "digest_text",
    "is_backward_compatible",
    "read",
    "stamp",
    "write",
]
