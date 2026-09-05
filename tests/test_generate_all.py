"""Subprocess-level tests for generate_all.py dual invocation modes.

Both ``python generators/generate_all.py`` (script mode) and
``python -m generators.generate_all`` (module mode) must exit 0 when
invoked from the repository root.
"""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _run(args: list[str]) -> subprocess.CompletedProcess:
    """Run a command from the project root; capture stdout+stderr."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )


def test_generate_all_script_exits_zero():
    """``python generators/generate_all.py`` must exit 0 (no shell=True)."""
    result = _run([sys.executable, "generators/generate_all.py"])
    assert result.returncode == 0, (
        f"Script invocation exited {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_generate_all_module_exits_zero():
    """``python -m generators.generate_all`` must exit 0 (no shell=True)."""
    result = _run([sys.executable, "-m", "generators.generate_all"])
    assert result.returncode == 0, (
        f"Module invocation exited {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
