#!/usr/bin/env python3
"""Unified command-line interface for profilekit.

A thin orchestration layer over the generators and publishers — it adds no
generation logic, so it cannot drift from direct module invocation. Runnable as
a module (``python -m profilekit.cli``) or, once installed, as the ``profile``
console script.

Every command resolves a :class:`~profilekit.context.ProjectContext` first and
threads it through. Nothing here derives a path from ``__file__``: the project
comes from the caller's world, so an installed CLI acts on the user's project
rather than on its own installation directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from profilekit import manifest, registry, validate
from profilekit.config import ConfigError
from profilekit.context import ProjectContext, ProjectNotFoundError, discover_project
from profilekit.publishers.filesystem import FilesystemPublisher
from profilekit.scaffold import ScaffoldError, init_project


def _git_output_is_clean(ctx: ProjectContext) -> bool | None:
    """Report whether the output directory has uncommitted drift.

    Returns True when clean, False when drifted, and ``None`` when the
    question could not be answered — there is no repository, or no ``git`` on
    PATH.

    Two hazards are handled deliberately. **Selection**: the repository is
    chosen with ``git -C`` against the resolved project root instead of being
    inherited from the process working directory, so the probe cannot be
    pointed at whatever repository the caller's shell happens to be sitting
    in. **Availability**: an installed CLI gets run in directories that are
    not repositories, by people who may not have git at all. Hard-failing
    there would make the gate unusable for exactly the audience this package
    is published for.

    Read-only by construction: ``diff`` only. It never stages, commits,
    amends, or initialises anything, and it never claims the tree is clean
    when it could not look.
    """
    if not (ctx.root / ".git").exists():
        return None

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ctx.root),
                "diff",
                "--exit-code",
                "--",
                str(ctx.output_dir),
            ],
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None

    return result.returncode == 0


def filesystem_destinations(ctx: ProjectContext) -> list[Mapping[str, object]]:
    """Return the ``filesystem``-kind destinations declared by the project.

    R7 replaces this with entry-point registry discovery. Until then it reads
    the same ``[publishers.*]`` tables the publish layer will, so the gate in
    ``check`` cannot silently lose a destination the project declared.
    """
    return [cfg for cfg in ctx.publisher_destinations().values() if cfg.get("kind") == "filesystem"]


def _stale_published_destinations(ctx: ProjectContext) -> list[str]:
    """Return a description of every filesystem destination that has drifted.

    A dry run: it calls ``plan()`` only, so it detects drift without repairing
    it. Repairing here would hide exactly the problem this gate exists to
    surface.
    """
    publisher = FilesystemPublisher()
    stale: list[str] = []

    for cfg in filesystem_destinations(ctx):
        plan = publisher.plan(ctx, cfg)
        if plan.changes:
            stale.append(f"{plan.destination}: {', '.join(plan.changes)}")
    return stale


def cmd_generate(target: str, ctx: ProjectContext) -> int:
    """Run one generator, or all of them (``target == "all"``), in order.

    Targets come from the registry, which is the only enumeration source.
    Publishers are in a different entry-point group, so none can be reached
    from here regardless of what a project declares.
    """
    try:
        available = registry.generators()
    except registry.RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    if target == "all":
        selected = list(available.items())
    elif target in available:
        selected = [(target, available[target])]
    else:
        valid = ", ".join(["all", *available])
        print(f"error: unknown target '{target}' (choose from: {valid})", file=sys.stderr)
        return 2

    for name, run in selected:
        try:
            run(ctx)
        except Exception as exc:  # noqa: BLE001 — surface which target failed
            print(f"error: generator '{name}' failed: {exc}", file=sys.stderr)
            return 1

    if target == "all":
        # The manifest indexes the whole output set, so it is only meaningful
        # after every generator has run. Writing it after a single target
        # would index a partially regenerated tree.
        path = manifest.write(ctx)
        print(f"Wrote {path}")
    return 0


def cmd_validate(ctx: ProjectContext) -> int:
    """Delegate to ``profilekit.validate.main()`` and return its exit code."""
    return validate.main(ctx)


def _manifest_is_valid(ctx: ProjectContext) -> int:
    """Validate the output manifest against its packaged schema.

    The manifest is the contract third parties read, so a malformed one is a
    broken promise rather than a cosmetic problem. Checked here so it cannot
    be published in that state.
    """
    import jsonschema  # noqa: PLC0415 — only needed on this path

    index = manifest.read(ctx.output_dir)
    if index is None:
        print(
            "error: output/manifest.json is missing — run `profile generate`",
            file=sys.stderr,
        )
        return 1

    schema_source = validate.schemas_dir(ctx) / "manifest.schema.json"
    schema = json.loads(schema_source.read_text(encoding="utf-8"))

    errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(index), key=str)
    if errors:
        for error in errors:
            path = ".".join(str(part) for part in error.absolute_path) or "<root>"
            print(f"error: manifest.json: {path}: {error.message}", file=sys.stderr)
        return 1

    # Digests are the publish layer's idempotency reference, so a stale one
    # would make `publish` skip a destination that actually needs writing.
    for entry in index["artifacts"]:
        artifact = ctx.output_dir / entry["name"]
        if not artifact.is_file():
            print(f"error: manifest.json lists missing artifact {entry['name']}", file=sys.stderr)
            return 1
        if manifest.digest_file(artifact) != entry["sha256"]:
            print(
                f"error: manifest.json digest for {entry['name']} does not match its content",
                file=sys.stderr,
            )
            return 1

    return 0


def cmd_check(ctx: ProjectContext) -> int:
    """Local CI-parity gate: validate, regenerate, then verify nothing is stale."""
    rc = cmd_validate(ctx)
    if rc != 0:
        return rc

    rc = cmd_generate("all", ctx)
    if rc != 0:
        return rc

    git_state = _git_output_is_clean(ctx)
    if git_state is None:
        # No repository, or no git binary. Say so rather than reporting a
        # result that was never measured. R3's output manifest will give this
        # branch a content reference to compare against.
        print(
            "notice: git freshness check skipped — "
            f"{ctx.root} is not a git repository, or git is unavailable"
        )
    elif not git_state:
        print(
            "error: output/ is stale — regenerated content differs from the "
            "committed tree (run `git diff -- output/`)",
            file=sys.stderr,
        )
        return 1

    # Published destinations are not covered by the output/ diff: the generate
    # path never touches them. Without this probe, destination drift would be
    # gated by nothing at all.
    stale = _stale_published_destinations(ctx)
    if stale:
        for entry in stale:
            print(f"error: published destination is stale — {entry}", file=sys.stderr)
        print(
            "error: run `profile publish --execute` and commit the result",
            file=sys.stderr,
        )
        return 1

    rc = _manifest_is_valid(ctx)
    if rc != 0:
        return rc

    freshness = "output/ up to date" if git_state else "output/ freshness skipped"
    print(f"check passed: data valid, {freshness}, destinations current")
    return 0


def cmd_init(target: Path) -> int:
    """Scaffold a new project at *target*.

    Runs before project discovery, because its job is to create the project
    that discovery looks for.
    """
    try:
        written = init_project(target)
    except ScaffoldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except OSError as exc:
        print(f"error: cannot scaffold {target}: {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(f"created {path}")
    print("\nNext: edit data/*.json, then run `profile validate` and `profile generate`.")
    return 0


def cmd_list(ctx: ProjectContext) -> int:
    """Print the registered generation targets and publish destinations."""
    try:
        for name in registry.generators():
            print(name)
    except registry.RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser with one subparser per subcommand."""
    parser = argparse.ArgumentParser(
        prog="profile",
        description="Turn structured profile data into generated artifacts.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help="Project directory (highest precedence; overrides PROFILEKIT_PROJECT).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Override the project's canonical data directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Override the project's generated-artifact directory.",
    )
    parser.set_defaults(func=None)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    gen = sub.add_parser("generate", help="Run one generator or all of them.")
    gen.add_argument(
        "target",
        nargs="?",
        default="all",
        help="Target to generate: 'all' (default), or a registered target (see `profile list`).",
    )
    gen.set_defaults(func=lambda args, ctx: cmd_generate(args.target, ctx))

    val = sub.add_parser("validate", help="Validate the data directory against the schemas.")
    val.set_defaults(func=lambda args, ctx: cmd_validate(ctx))

    chk = sub.add_parser("check", help="Validate, regenerate, and verify nothing is stale.")
    chk.set_defaults(func=lambda args, ctx: cmd_check(ctx))

    lst = sub.add_parser("list", help="List available generation targets.")
    lst.set_defaults(func=lambda args, ctx: cmd_list(ctx))

    ini = sub.add_parser("init", help="Scaffold a new project with example data.")
    ini.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=None,
        help="Where to create the project (default: the working directory).",
    )
    # `init` creates the project that discovery looks for, so it must not
    # require one to already exist.
    ini.set_defaults(func=None, init=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse *argv*, resolve the project, and dispatch to the subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "init", False):
        return cmd_init(args.directory or args.project or Path.cwd())

    if args.func is None:
        parser.print_help(sys.stderr)
        return 2

    try:
        ctx = discover_project(
            explicit=args.project,
            data_dir=args.data_dir,
            output_dir=args.output_dir,
        )
    except (ProjectNotFoundError, ConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    return args.func(args, ctx)


if __name__ == "__main__":
    sys.exit(main())
