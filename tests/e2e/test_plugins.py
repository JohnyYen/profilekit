"""Third-party components, discovered from their own installed distribution.

The registry's promise is that adding a generator or publisher is a
registration in *another* package's metadata, not an edit to this one. The
unit suite can only fake that with a patched entry-point list. This file
installs a real second distribution next to the wheel and drives the console
script, so discovery goes through `importlib.metadata` exactly as it would for
a stranger's plugin.

The plugin wheels are assembled with `zipfile` rather than a build backend.
A backend would need its own isolated environment and therefore the network,
which is not what is under test; a wheel is a zip with a fixed layout, and
pip installing it is the part that matters.

The working plugin goes into its own virtual environment, so the session
`installed` environment the rest of the suite shares never sees it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import venv
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.e2e.conftest import (
    BIN_DIR_NAME,
    EXE_SUFFIX,
    OFFLINE_ENV,
    _child_env,
    _run,
)

PLUGIN_MODULE = '''\
"""A minimal third-party profilekit plugin."""

from pathlib import Path


def generate(ctx):
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    (ctx.output_dir / "plugin-card.txt").write_text("plugin card\\n", encoding="utf-8")


def push(ctx, cfg=None, credentials=None):
    from profilekit.publishers import PublishResult

    target = ctx.root / str(cfg["destination"])
    target.mkdir(parents=True, exist_ok=True)
    (target / "pushed.txt").write_text("pushed\\n", encoding="utf-8")
    return PublishResult(destination=str(cfg["destination"]), status="published", detail="pushed")
'''

PLUGIN_ENTRY_POINTS = """\
[profilekit.generators]
plugin-card = profilekit_e2e_plugin:generate

[profilekit.publishers]
e2e-push = profilekit_e2e_plugin:push
"""

BROKEN_MODULE = '''\
"""A plugin whose own dependency is not installed."""

import profilekit_e2e_missing_dependency  # noqa: F401


def generate(ctx):
    raise AssertionError("never reached")
'''

BROKEN_ENTRY_POINTS = """\
[profilekit.generators]
broken-card = profilekit_e2e_broken:generate
"""

PLUGIN_CONFIG = """\
[project]
config_version = 1

[publishers.remote]
kind = "e2e-push"
destination = "pushed-here"
"""


def _record_line(arcname: str, payload: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
    return f"{arcname},sha256={digest},{len(payload)}"


def _build_wheel(out_dir: Path, module: str, source: str, entry_points: str) -> Path:
    """Assemble a pure-Python wheel holding one module and its entry points."""
    dist = module
    version = "0.1.0"
    info = f"{dist}-{version}.dist-info"
    files = {
        f"{module}.py": source,
        f"{info}/METADATA": (
            f"Metadata-Version: 2.1\nName: {dist.replace('_', '-')}\nVersion: {version}\n"
        ),
        f"{info}/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: profilekit-e2e\n"
            "Root-Is-Purelib: true\nTag: py3-none-any\n"
        ),
        f"{info}/entry_points.txt": entry_points,
    }

    wheel_path = out_dir / f"{dist}-{version}-py3-none-any.whl"
    records = []
    with zipfile.ZipFile(wheel_path, "w") as archive:
        for arcname, text in files.items():
            payload = text.encode("utf-8")
            archive.writestr(arcname, payload)
            records.append(_record_line(arcname, payload))
        records.append(f"{info}/RECORD,,")
        archive.writestr(f"{info}/RECORD", "\n".join(records) + "\n")
    return wheel_path


@pytest.fixture(scope="module")
def plugin_env(wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A virtualenv holding the profilekit wheel and the plugin; return its bin dir."""
    wheels = tmp_path_factory.mktemp("plugin-wheels")
    plugin_wheel = _build_wheel(wheels, "profilekit_e2e_plugin", PLUGIN_MODULE, PLUGIN_ENTRY_POINTS)

    env_dir = tmp_path_factory.mktemp("plugin-venv")
    venv.create(env_dir, with_pip=True, clear=True)
    bin_dir = env_dir / BIN_DIR_NAME

    result = _run(
        [str(bin_dir / f"pip{EXE_SUFFIX}"), "install", "--quiet", str(wheel), str(plugin_wheel)],
        timeout=600,
    )
    assert result.returncode == 0, f"install failed:\n{result.stdout}\n{result.stderr}"
    return bin_dir


@pytest.fixture
def plugin_profile(plugin_env: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run the plugin environment's `profile` script, with the suite's minimal env."""
    executable = plugin_env / f"profile{EXE_SUFFIX}"

    def _profile(
        *args: str, cwd: Path, env_extra: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = _child_env(
            {"HOME": str(cwd), **OFFLINE_ENV, **(env_extra or {})}, path_prefix=plugin_env
        )
        return _run([str(executable), *args], cwd=cwd, env=env)

    return _profile


@pytest.fixture
def plugin_project(empty_project: Path, plugin_profile) -> Path:
    for args in (("init",), ("generate",)):
        result = plugin_profile(*args, cwd=empty_project)
        assert result.returncode == 0, f"setup failed: profile {args}\n{result.stderr}"
    (empty_project / "profile.toml").write_text(PLUGIN_CONFIG, encoding="utf-8")
    return empty_project


def test_a_plugin_generator_is_listed(plugin_project: Path, plugin_profile) -> None:
    result = plugin_profile("list", cwd=plugin_project)

    assert result.returncode == 0, result.stderr
    names = result.stdout.split()
    assert "plugin-card" in names
    assert "cv" in names, "a plugin must add to the built-ins, not replace them"


def test_a_plugin_generator_writes_its_artifact_and_is_indexed(
    plugin_project: Path, plugin_profile
) -> None:
    output = plugin_project / "output"
    assert (output / "plugin-card.txt").read_text(encoding="utf-8") == "plugin card\n"

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert "plugin-card.txt" in {entry["name"] for entry in manifest["artifacts"]}


def test_a_plugin_publisher_is_reported_in_a_dry_run(plugin_project: Path, plugin_profile) -> None:
    result = plugin_profile("publish", cwd=plugin_project)

    assert result.returncode == 0, result.stdout + result.stderr
    row = next(line for line in result.stdout.splitlines() if line.startswith("remote"))
    assert "<adapter-managed>" in row
    assert not (plugin_project / "pushed-here").exists(), "a dry run must not call the adapter"


def test_a_plugin_publisher_runs_on_execute(plugin_project: Path, plugin_profile) -> None:
    result = plugin_profile("publish", "--execute", cwd=plugin_project)

    assert result.returncode == 0, result.stdout + result.stderr
    row = next(line for line in result.stdout.splitlines() if line.startswith("remote"))
    assert "published" in row
    assert (plugin_project / "pushed-here" / "pushed.txt").is_file()


def test_a_plugin_that_fails_to_import_is_named(
    plugin_project: Path, plugin_profile, plugin_env: Path, tmp_path: Path
) -> None:
    """A broken third-party generator must say which one it is.

    Installed with `--target` into its own directory and made visible through
    `PYTHONPATH` for these invocations only, so the shared plugin environment
    is left as it was. That directory holds only the broken plugin;
    `profilekit` still resolves from the environment's site-packages.
    """
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    broken = _build_wheel(wheels, "profilekit_e2e_broken", BROKEN_MODULE, BROKEN_ENTRY_POINTS)
    target = tmp_path / "extra-site"

    install = _run(
        [
            str(plugin_env / f"pip{EXE_SUFFIX}"),
            "install",
            "--quiet",
            "--no-deps",
            "--target",
            str(target),
            str(broken),
        ]
    )
    assert install.returncode == 0, f"install failed:\n{install.stdout}\n{install.stderr}"

    extra = {"PYTHONPATH": str(target)}
    for command in ("generate", "list"):
        result = plugin_profile(command, cwd=plugin_project, env_extra=extra)

        assert result.returncode == 1, f"{command}: {result.stdout}\n{result.stderr}"
        assert "'broken-card'" in result.stderr
        assert "failed to load" in result.stderr
        assert "Traceback" not in result.stderr

    # The control: without the extra directory the same project works, so the
    # failure above came from the broken plugin and nothing else.
    assert plugin_profile("generate", cwd=plugin_project).returncode == 0
