#!/usr/bin/env python3
"""Convenience runner — executes all profile generators in sequence.

NOTE: output/github-readme.md is the deploy source for the JohnyYen/JohnyYen
GitHub profile README.  It must be manually copied (or deployed via CI step)
to that repository.  Automation of that step is out of scope for this change.
"""

import sys
from pathlib import Path

# Bootstrap sys.path so that ``python generators/generate_all.py`` (script
# mode) can import the ``generators`` package.  When run as a module via
# ``python -m generators.generate_all``, Python already adds the project root
# to sys.path, so this guard is a no-op in that case.
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

import generators.generate_github_readme as github_readme
import generators.generate_linkedin as linkedin
import generators.generate_portfolio as portfolio
import generators.generate_cv as cv

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = ROOT_DIR / "output"


def main():
    github_readme.main()
    linkedin.main()
    portfolio.main()
    cv.main()

    output_files = [
        OUTPUT_DIR / "github-readme.md",
        OUTPUT_DIR / "linkedin.md",
        OUTPUT_DIR / "portfolio.md",
        OUTPUT_DIR / "cv.md",
        OUTPUT_DIR / "cv.yml",
    ]
    print("\nGenerated output files:")
    for f in output_files:
        print(f"  {f}")


if __name__ == "__main__":
    main()
