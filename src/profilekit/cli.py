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
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

import profilekit.generate_cv as cv
import profilekit.generate_github_readme as github_readme
import profilekit.generate_linkedin as linkedin
import profilekit.generate_portfolio as portfolio
from profilekit import validate
from profilekit.config import ConfigError
from profilekit.context import ProjectContext, ProjectNotFoundError, discover_project
from profilekit.publishers.filesystem import FilesystemPublisher
from profilekit.scaffold import ScaffoldError, init_project

# Generation targets and their run order. Publishers are deliberately absent:
# ``generate`` only invokes generators. R7 replaces this literal and the
# parallel list in ``profilekit.generate_all`` with one entry-point registry.
GENERATORS: dict[str, Callable[..., object]] = {
    "github-readme": github_readme.main,
    "linkedin": linkedin.main,
    "portfolio": portfolio.main,
    "cv": cv.main,
}


def _git_output_is_clean(ctx: ProjectContext) -> bool:
    """Return True when the output directory has no uncommitted drift.

    Mirrors the CI freshness gate. The repository is selected with ``git -C``
    against the resolved project root rather than inherited from the process
    working directory, so the command cannot accidentally interrogate whatever
    repository the user happened to be standing in. Argument vector only —
    never ``shell=True``.
    """
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
    """Run one generator, or all of them (``target == "all"``), in order."""
    if target == "all":
        selected = list(GENERATORS.items())
    elif target in GENERATORS:
        selected = [(target, GENERATORS[target])]
    else:
        valid = ", ".join(["all", *GENERATORS])
        print(f"error: unknown target '{target}' (choose from: {valid})", file=sys.stderr)
        return 2

    for name, run in selected:
        try:
            run(ctx)
        except Exception as exc:  # noqa: BLE001 — surface which target failed
            print(f"error: generator '{name}' failed: {exc}", file=sys.stderr)
            return 1
    return 0


def cmd_validate(ctx: ProjectContext) -> int:
    """Delegate to ``profilekit.validate.main()`` and return its exit code."""
    return validate.main(ctx)


def cmd_check(ctx: ProjectContext) -> int:
    """Local CI-parity gate: validate, regenerate, then verify nothing is stale."""
    rc = cmd_validate(ctx)
    if rc != 0:
        return rc

    rc = cmd_generate("all", ctx)
    if rc != 0:
        return rc

    if not _git_output_is_clean(ctx):
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

    print("check passed: data valid, output/ up to date, destinations current")
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
    """Print the available generation targets."""
    for name in GENERATORS:
        print(name)
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
        help="Target to generate: all (default), " + ", ".join(GENERATORS),
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
