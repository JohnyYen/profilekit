"""Architecture rule: only ``profilekit.safe_io`` writes files.

Every unguarded write the project has shipped (init overwriting data, publish
targeting ``data/``, writing through a symlinked artifact, a non-atomic
ledger) was a direct call that bypassed a check. This test parses every
module in ``src/profilekit`` and fails on any file-writing call outside
``safe_io.py``, naming ``module:line``. ``mkdir`` is not a file write and is
allowed.

The scan is syntactic. ``Path.replace`` is not detected (``str.replace`` has
the same shape); ``os.replace`` is.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "profilekit"
ALLOWED = {SRC / "safe_io.py"}

# Methods whose call always writes or links a file (Path API).
_WRITING_METHODS = {"write_text", "write_bytes", "touch", "symlink_to", "hardlink_to", "rename"}
# Module-level functions that write, keyed by module.
_WRITING_FUNCTIONS = {
    "os": {
        "open",
        "fdopen",
        "write",
        "replace",
        "rename",
        "renames",
        "link",
        "symlink",
        "truncate",
        "ftruncate",
    },
    "shutil": {"copy", "copy2", "copyfile", "copyfileobj", "copytree", "move"},
    "tempfile": {"mkstemp", "NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile"},
    "json": {"dump"},
    "io": {"open"},
}


def _mode_writes(node: ast.Call, positional_index: int) -> bool:
    """True if this ``open`` call's mode writes, or cannot be proven read-only."""
    mode: ast.expr | None = None
    if len(node.args) > positional_index:
        mode = node.args[positional_index]
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return any(flag in mode.value for flag in "wax+")
    return True


def _violation(node: ast.AST) -> str | None:
    if isinstance(node, ast.ImportFrom) and node.module in _WRITING_FUNCTIONS:
        names = sorted(
            a.name for a in node.names if a.name in _WRITING_FUNCTIONS[node.module] | {"*"}
        )
        if names:
            return f"from {node.module} import {', '.join(names)}"
        return None
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name) and func.id == "open" and _mode_writes(node, 1):
        return "open() in a writing mode"
    if not isinstance(func, ast.Attribute):
        return None
    owner = func.value.id if isinstance(func.value, ast.Name) else None
    if owner in _WRITING_FUNCTIONS and func.attr in _WRITING_FUNCTIONS[owner]:
        return f"{owner}.{func.attr}()"
    if func.attr in _WRITING_METHODS:
        return f".{func.attr}()"
    if func.attr == "open" and owner not in _WRITING_FUNCTIONS and _mode_writes(node, 0):
        return ".open() in a writing mode"
    return None


def raw_writes(source: str, label: str) -> list[str]:
    """Return ``label:line: call`` for every file-writing call in *source*."""
    tree = ast.parse(source)
    return [
        f"{label}:{node.lineno}: {found}"
        for node in ast.walk(tree)
        if (found := _violation(node)) is not None
    ]


def test_no_module_writes_files_outside_safe_io() -> None:
    violations: list[str] = []
    for module in sorted(SRC.rglob("*.py")):
        if module in ALLOWED:
            continue
        label = module.relative_to(SRC.parent).as_posix()
        violations += raw_writes(module.read_text(encoding="utf-8"), label)

    assert not violations, (
        "file writes must go through profilekit.safe_io.write_file:\n" + "\n".join(violations)
    )


def test_the_scan_covers_the_package() -> None:
    modules = {p.name for p in SRC.rglob("*.py")}
    assert {"safe_io.py", "publish.py", "scaffold.py", "filesystem.py"} <= modules


@pytest.mark.parametrize(
    "snippet",
    [
        "path.write_text('x')",
        "path.write_bytes(b'x')",
        "path.touch()",
        "path.symlink_to(other)",
        "path.rename(other)",
        "open(p, 'w')",
        "open(p, mode='a')",
        "open(p, 'rb+')",
        "open(p, mode)",
        "path.open('w')",
        "path.open(mode='x')",
        "io.open(p)",
        "os.replace(a, b)",
        "os.rename(a, b)",
        "os.open(p, flags)",
        "os.fdopen(fd, 'w')",
        "os.write(fd, data)",
        "shutil.copy(a, b)",
        "shutil.move(a, b)",
        "tempfile.mkstemp()",
        "json.dump(obj, handle)",
        "from os import replace",
        "from shutil import copyfile",
    ],
)
def test_the_scan_detects(snippet: str) -> None:
    assert raw_writes(snippet, "m.py"), f"not detected: {snippet}"


@pytest.mark.parametrize(
    "snippet",
    [
        "open(p)",
        "open(p, 'rb')",
        "open(p, encoding='utf-8')",
        "path.open()",
        "path.open('r')",
        "path.read_text()",
        "path.mkdir(parents=True)",
        "json.dumps(obj)",
        "text.replace('a', 'b')",
        "urllib.request.urlopen(req)",
        "from os import environ",
    ],
)
def test_the_scan_allows(snippet: str) -> None:
    assert raw_writes(snippet, "m.py") == []
