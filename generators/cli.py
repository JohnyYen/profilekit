#!/usr/bin/env python3
"""Unified command-line interface for the profile-data generators.

Thin orchestration layer over the existing generator ``main()`` functions — it
adds no generation logic, so it can never drift from direct module invocation.
Runnable as a module (``python -m generators.cli``) or, once installed, as the
``profile`` console script.
"""

import argparse
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

# Bootstrap sys.path so ``python generators/cli.py`` (script mode) can import the
# ``generators`` package.  Under ``python -m generators.cli`` this is a no-op.
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

import generators.generate_cv as cv  # noqa: E402
import generators.generate_github_readme as github_readme  # noqa: E402
import generators.generate_linkedin as linkedin  # noqa: E402
import generators.generate_portfolio as portfolio  # noqa: E402
from generators import validate  # noqa: E402

ROOT_DIR = _ROOT_DIR
OUTPUT_DIR = ROOT_DIR / "output"

# Single source of truth for generation targets and their run order.  Insertion
# order matches ``generators.generate_all`` and is preserved by ``dict``.
GENERATORS: dict[str, Callable[[], object]] = {
    "github-readme": github_readme.main,
    "linkedin": linkedin.main,
    "portfolio": portfolio.main,
    "cv": cv.main,
}


def _git_output_is_clean() -> bool:
    """Return True when ``output/`` has no uncommitted drift.

    Mirrors the CI freshness gate: ``git diff --exit-code -- output/`` exits 0
    when the working tree matches the index/HEAD for that path.
    """
    result = subprocess.run(
        ["git", "diff", "--exit-code", "--", "output/"],
        cwd=ROOT_DIR,
    )
    return result.returncode == 0


def cmd_generate(target: str) -> int:
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
            run()
        except Exception as exc:  # noqa: BLE001 — surface which target failed
            print(f"error: generator '{name}' failed: {exc}", file=sys.stderr)
            return 1
    return 0


def cmd_validate() -> int:
    """Delegate to ``generators.validate.main()`` and return its exit code."""
    return validate.main()


def cmd_check() -> int:
    """Local CI-parity gate: validate, regenerate all, then check output freshness."""
    rc = cmd_validate()
    if rc != 0:
        return rc

    rc = cmd_generate("all")
    if rc != 0:
        return rc

    if not _git_output_is_clean():
        print(
            "error: output/ is stale — regenerated content differs from the "
            "committed tree (run `git diff -- output/`)",
            file=sys.stderr,
        )
        return 1

    print("check passed: data valid and output/ up to date")
    return 0


def cmd_list() -> int:
    """Print the available generation targets."""
    for name in GENERATORS:
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser with one subparser per subcommand."""
    parser = argparse.ArgumentParser(
        prog="profile",
        description="Manage the profile-data generators.",
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
    gen.set_defaults(func=lambda args: cmd_generate(args.target))

    val = sub.add_parser("validate", help="Validate data/ against schemas/.")
    val.set_defaults(func=lambda args: cmd_validate())

    chk = sub.add_parser("check", help="Validate, regenerate, and verify output freshness.")
    chk.set_defaults(func=lambda args: cmd_check())

    lst = sub.add_parser("list", help="List available generation targets.")
    lst.set_defaults(func=lambda args: cmd_list())

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and dispatch to the selected subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.func is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
