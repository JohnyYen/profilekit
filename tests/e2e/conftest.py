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

Three properties make that premise hold, and each was wrong in the first
version of this file:

**The build happens outside the checkout.** The sources are copied to a
temporary tree and built there. An in-tree build writes `build/` and
`*.egg-info` into the developer's working copy, and setuptools then stages
files through `build/lib` — so a declaration removed from `pyproject.toml`
still reaches a new wheel from the previous run's stage. The first version
deleted those directories instead, which is both destructive on someone's
checkout and still left them recreated afterwards.

**Child processes get a controlled environment, never an inherited one.** With
`PYTHONPATH` inherited, `import profilekit` resolves from the checkout and
every test passes for the exact defect it exists to catch. Proven: with the
schemas removed from the package declarations and `PYTHONPATH` pointing at
`src/`, the packaging test passed.

**Setup commands are checked.** `init` and `generate` are setup for most tests
here, and discarding their exit codes makes assertions pass on an empty tree —
two empty directories compare equal, and a scan over nothing finds nothing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: Everything the build backend needs, and nothing else. Copying rather than
#: building in place keeps the developer's checkout untouched and guarantees no
#: staged output from an earlier run can leak into the wheel.
SOURCES_TO_COPY = ("src", "pyproject.toml", "MANIFEST.in", "README.md", "LICENSE")

#: Reachability probes talk to third-party hosts. They are a real feature but
#: not what this suite tests, and depending on someone else's uptime would turn
#: a packaging test into a flake.
OFFLINE_ENV = {"SKIP_ICON_CHECK": "1", "SKIP_LINK_CHECK": "1"}

BIN_DIR_NAME = "Scripts" if os.name == "nt" else "bin"
EXE_SUFFIX = ".exe" if os.name == "nt" else ""


def _run(
    argv: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Run a command, returning the result rather than raising on failure.

    Callers assert on the result so a failure reports the command's own stderr
    instead of an opaque exception. A missing executable is converted into a
    failed result for the same reason — a bare FileNotFoundError from a
    fallback path would discard the original diagnostic.
    """
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"executable not found: {exc}")
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(argv, 124, "", f"timed out after {exc.timeout}s")


def _child_env(
    extra: dict[str, str] | None = None, path_prefix: Path | None = None
) -> dict[str, str]:
    """Build a minimal environment for a child process.

    Deliberately omits `PYTHONPATH` and `PROFILEKIT_PROJECT`: a test that only
    passes because the checkout leaked in through the environment proves
    nothing about an installed package.

    Variables the interpreter genuinely needs to start are carried over —
    `SYSTEMROOT` on Windows, where dropping it makes every invocation fail
    before reaching any code under test.
    """
    base_path = os.pathsep.join(
        filter(None, [str(path_prefix) if path_prefix else None, "/usr/bin", "/bin"])
    )
    env = {"PATH": base_path}

    for carry in ("SYSTEMROOT", "SystemRoot", "COMSPEC", "TEMP", "TMP"):
        if carry in os.environ:
            env[carry] = os.environ[carry]

    if extra:
        env.update(extra)
    return env


@pytest.fixture(scope="session")
def source_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of the sources, outside the checkout, for building from clean."""
    tree = tmp_path_factory.mktemp("sources")
    for name in SOURCES_TO_COPY:
        origin = REPO_ROOT / name
        if not origin.exists():
            continue
        target = tree / name
        if origin.is_dir():
            shutil.copytree(
                origin, target, ignore=shutil.ignore_patterns("*.egg-info", "__pycache__")
            )
        else:
            shutil.copy2(origin, target)
    return tree


@pytest.fixture(scope="session")
def wheel(source_tree: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the distribution from the copied tree and return the wheel path."""
    out = tmp_path_factory.mktemp("dist")

    attempts = [
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out)],
        ["uv", "build", "--wheel", "--out-dir", str(out)],
    ]
    failures = []
    for argv in attempts:
        result = _run(argv, cwd=source_tree, timeout=600)
        if result.returncode == 0:
            break
        # Keep every diagnostic. The first version overwrote the primary
        # failure with the fallback's, so a real packaging error was lost.
        failures.append(
            f"$ {' '.join(argv)}\nexit {result.returncode}\n{result.stdout}\n{result.stderr}"
        )

    wheels = sorted(out.glob("*.whl"))
    assert wheels, "could not build a wheel:\n\n" + "\n\n".join(failures)
    return wheels[-1]


@pytest.fixture(scope="session")
def installed(wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Install the wheel into a fresh virtual environment; return its bin dir."""
    env_dir = tmp_path_factory.mktemp("venv")
    venv.create(env_dir, with_pip=True, clear=True)

    bin_dir = env_dir / BIN_DIR_NAME
    pip = bin_dir / f"pip{EXE_SUFFIX}"

    result = _run([str(pip), "install", "--quiet", str(wheel)], timeout=600)
    assert result.returncode == 0, f"install failed:\n{result.stdout}\n{result.stderr}"

    return bin_dir


@pytest.fixture
def venv_python(installed: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run a snippet in the installed interpreter, isolated from this checkout.

    `-I` puts the interpreter in isolated mode: no user site directory and no
    `PYTHONPATH`. Combined with the minimal environment, an import that
    succeeds here succeeded because the distribution carries what it needs.
    """
    python = installed / f"python{EXE_SUFFIX}"

    def _python(code: str, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return _run([str(python), "-I", "-c", code, *args], cwd=cwd, env=_child_env())

    return _python


@pytest.fixture
def profile(installed: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run the installed `profile` console script against a given directory."""
    executable = installed / f"profile{EXE_SUFFIX}"

    def _profile(
        *args: str, cwd: Path, env_extra: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = _child_env(
            {"HOME": str(cwd), **OFFLINE_ENV, **(env_extra or {})}, path_prefix=installed
        )
        return _run([str(executable), *args], cwd=cwd, env=env)

    return _profile


@pytest.fixture
def run_profile(profile) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Like `profile`, but asserts the command succeeded.

    For setup steps. Discarding a setup command's exit code lets later
    assertions pass over an empty tree, which is how several tests in the first
    version of this suite could have passed while nothing ran.
    """

    def _run_profile(
        *args: str, cwd: Path, env_extra: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        result = profile(*args, cwd=cwd, env_extra=env_extra)
        assert result.returncode == 0, (
            f"setup command failed: profile {' '.join(args)}\n"
            f"exit {result.returncode}\n{result.stdout}\n{result.stderr}"
        )
        return result

    return _run_profile


@pytest.fixture
def empty_project(tmp_path: Path) -> Iterator[Path]:
    """A directory with nothing in it, outside the repository.

    Asserted to have no project and no repository above it: pytest's base temp
    directory is configurable, and one placed inside a checkout would make the
    discovery tests pass or fail for the wrong reason.
    """
    target = tmp_path / "somewhere-else"
    target.mkdir()

    for ancestor in (target, *target.parents):
        assert not (ancestor / "profile.toml").exists(), (
            f"an ancestor of the temp directory is already a project: {ancestor}"
        )
        assert not (ancestor / ".git").exists(), (
            f"an ancestor of the temp directory is a git repository: {ancestor}"
        )

    yield target
    shutil.rmtree(target, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def _checkout_is_not_modified_by_the_e2e_suite() -> Iterator[None]:
    """Fail if building or installing wrote into the working copy.

    The first version of this suite deleted `build/` and both `*.egg-info`
    directories from the real checkout and then built in place, recreating
    them — while its own docstring claimed it left no artifacts behind.
    """
    watched = ("build", "src/profilekit.egg-info", "profilekit.egg-info", "dist")
    before = {name: (REPO_ROOT / name).exists() for name in watched}

    yield

    appeared = [name for name in watched if (REPO_ROOT / name).exists() and not before[name]]
    assert not appeared, (
        f"the e2e suite created build artifacts in the checkout: {appeared}. "
        "Build from a copied source tree instead of in place."
    )
