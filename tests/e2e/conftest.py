"""Shared machinery for the end-to-end suite.

These tests exercise the package the way a stranger does: build the
distribution, install it into an interpreter that knows nothing about this
checkout, and drive the console script.

That distinction is the whole point. A working checkout hides a specific class
of defect — package data that was never declared, an entry point that resolves
only because `src/` happens to be importable, a module that works because the
repository root is the current directory. This project shipped two of those
during development: the JSON Schemas were not packaged, and a stale
`*.egg-info` at the repository root shadowed the real distribution metadata so
entry-point discovery found nothing. Neither was visible to the unit suite.

The build and install happen once per session, because they cost seconds and
nothing in them varies per test.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(argv: list[str], cwd: Path | None = None, env: dict[str, str] | None = None):
    """Run a command and return the completed process, never raising on failure.

    Tests assert on the result so a failure reports the command's own stderr
    rather than an opaque CalledProcessError.
    """
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


#: Build artifacts that make a build reuse earlier output. setuptools copies
#: staged files out of `build/lib`, so a file removed from the package
#: declarations still lands in a new wheel while that directory survives — and
#: a stale `*.egg-info` shadows the real distribution metadata, which is how
#: entry-point discovery silently found nothing during development.
STALE_BUILD_ARTIFACTS = ("build", "src/profilekit.egg-info", "profilekit.egg-info")


def _clear_stale_build_artifacts() -> None:
    for relative in STALE_BUILD_ARTIFACTS:
        shutil.rmtree(REPO_ROOT / relative, ignore_errors=True)


@pytest.fixture(scope="session")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the distribution from clean and return the wheel path.

    Built into a temporary directory rather than the repository's `dist/`, so
    running the suite leaves no artifacts behind — a property the unit suite's
    session guard also enforces.

    Stale build directories are cleared first. Without that, this suite can
    validate a wheel assembled from previously staged files: removing the
    schemas from both `pyproject.toml` and `MANIFEST.in` still produced a wheel
    containing them, because `build/lib` held copies from an earlier run. An
    end-to-end suite testing a stale artifact is the exact failure mode it
    exists to prevent.
    """
    _clear_stale_build_artifacts()
    out = tmp_path_factory.mktemp("dist")
    result = _run([sys.executable, "-m", "build", "--wheel", "--outdir", str(out)], cwd=REPO_ROOT)

    if result.returncode != 0:
        # `build` is not a declared dependency; fall back to uv, which is how
        # this project builds in CI.
        result = _run(["uv", "build", "--wheel", "--out-dir", str(out)], cwd=REPO_ROOT)

    wheels = sorted(out.glob("*.whl"))
    assert result.returncode == 0 and wheels, (
        f"could not build a wheel.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return wheels[-1]


@pytest.fixture(scope="session")
def installed(wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Install the wheel into a fresh virtual environment; return its bin dir.

    `--no-build-isolation` is deliberately absent and the environment includes
    pip, because this must behave like an ordinary user install.
    """
    env_dir = tmp_path_factory.mktemp("venv")
    venv.create(env_dir, with_pip=True, clear=True)

    bin_dir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    pip = bin_dir / ("pip.exe" if os.name == "nt" else "pip")

    result = _run([str(pip), "install", "--quiet", str(wheel)])
    assert result.returncode == 0, f"install failed:\n{result.stderr}"

    return bin_dir


@pytest.fixture
def profile(installed: Path):
    """Return a callable that runs the installed `profile` console script.

    The environment is deliberately minimal: no `PYTHONPATH`, no inherited
    `PROFILEKIT_PROJECT`. A test that passes only because the checkout leaked
    into the environment proves nothing about an installed package.
    """
    executable = installed / ("profile.exe" if os.name == "nt" else "profile")

    def _profile(*args: str, cwd: Path, env_extra: dict[str, str] | None = None):
        env = {
            "PATH": f"{installed}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "HOME": str(cwd),
        }
        if env_extra:
            env.update(env_extra)
        return _run([str(executable), *args], cwd=cwd, env=env)

    return _profile


@pytest.fixture
def empty_project(tmp_path: Path) -> Iterator[Path]:
    """A directory with nothing in it, outside the repository."""
    target = tmp_path / "somewhere-else"
    target.mkdir()
    yield target
    shutil.rmtree(target, ignore_errors=True)
