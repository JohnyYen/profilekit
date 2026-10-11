#!/usr/bin/env python3
"""Convenience runner — executes all profile generators in sequence.

NOTE: output/github-readme.md is the deploy source for the JohnyYen/JohnyYen
GitHub profile README.  It must be manually copied (or deployed via CI step)
to that repository.  Automation of that step is out of scope for this change.
"""

import sys
from pathlib import Path

# Bootstrap sys.path so that ``python src/profilekit/generate_all.py`` (script
# mode) can import the ``profilekit`` package. src-layout nests the package
# one level deeper than before (src/profilekit vs. generators), so this
# still reaches ``src/`` — the directory that must be on sys.path for the
# package to resolve. When run as a module via ``python -m
# profilekit.generate_all``, Python already adds the right directory to
# sys.path, so this guard is a no-op in that case.
_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import profilekit.generate_cv as cv
import profilekit.generate_github_readme as github_readme
import profilekit.generate_linkedin as linkedin
import profilekit.generate_portfolio as portfolio
from profilekit.context import ProjectContext, discover_project


def main(ctx: ProjectContext | None = None):
    ctx = ctx or discover_project()

    github_readme.main(ctx)
    linkedin.main(ctx)
    portfolio.main(ctx)
    cv.main(ctx)

    output_files = [
        ctx.output_dir / "github-readme.md",
        ctx.output_dir / "linkedin.md",
        ctx.output_dir / "portfolio.md",
        ctx.output_dir / "cv.md",
        ctx.output_dir / "cv.yml",
    ]
    print("\nGenerated output files:")
    for f in output_files:
        print(f"  {f}")

    print(
        "\nPortfolio app data is published, not generated: "
        "run `profile publish` (gated by `profile check`)."
    )


if __name__ == "__main__":
    main()
