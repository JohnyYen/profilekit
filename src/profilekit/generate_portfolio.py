#!/usr/bin/env python3
"""Generate a portfolio markdown page from canonical profile data."""

import sys
from pathlib import Path

from profilekit.context import ProjectContext, discover_project
from profilekit.utils import load_json, run, what_i_build, write_output


def compute_portfolio_projects(projects: list, highlights: list | None) -> list:
    """Return the ordered project list based on portfolioHighlights.

    - highlights is None or empty -> return all projects in source order.
    - highlights is non-empty -> return only projects whose name is in
      highlights, ordered by the highlights list.  Unmatched highlight names
      emit a warning to stderr and are skipped.
    """
    if not highlights:
        return list(projects)

    project_by_name = {p["name"]: p for p in projects}
    result = []
    for name in highlights:
        if name in project_by_name:
            result.append(project_by_name[name])
        else:
            print(
                f"WARNING: portfolioHighlights entry '{name}' does not match "
                "any project name. Skipping.",
                file=sys.stderr,
            )
    return result


def render_portfolio(about: dict, projects: list) -> str:
    """Render a portfolio markdown string from about metadata and a project list."""
    lines = [
        "# Portfolio",
        "",
        about.get("description", ""),
        "",
    ]

    # "What I build" section — uses platform variant when available
    portfolio_build_items = what_i_build(about, "portfolio")
    if portfolio_build_items:
        lines.append("## What I Build")
        lines.append("")
        for item in portfolio_build_items:
            lines.append(f"- {item}")
        lines.append("")

    for project in projects:
        lines.append(f"## {project['name']}")
        lines.append("")
        lines.append(project.get("description", ""))
        lines.append("")

        tech = project.get("tech", "")
        if tech:
            lines.append(f"**Tech:** {tech}")
            lines.append("")

        url = project.get("url", "")
        if url:
            lines.append(f"[View Project]({url})")
            lines.append("")

        for highlight in project.get("highlights", []):
            lines.append(f"- {highlight}")
        if project.get("highlights"):
            lines.append("")

    return "\n".join(lines)


def main(ctx: ProjectContext | None = None, output_dir: Path | None = None) -> None:
    """Compose the portfolio highlights and write them to portfolio.md.

    ``ctx`` carries the project's resolved directories. Passing ``None``
    discovers the project from the working directory, which is what the CLI
    does; tests construct a context over a temporary directory instead of
    monkeypatching module globals.

    ``output_dir`` overrides the context's output directory. A generator
    writes only where it was told, which is what keeps it a generator and
    not a publisher.
    """
    ctx = ctx or discover_project()
    out_dir = output_dir or ctx.output_dir

    about = load_json("about.json", ctx.data_dir)
    projects = load_json("projects.json", ctx.data_dir)

    selected = compute_portfolio_projects(projects, about.get("portfolioHighlights"))
    output = render_portfolio(about, selected)
    output_path = write_output(output, out_dir, "portfolio.md")
    print(f"Generated portfolio.md at {output_path}")


if __name__ == "__main__":
    run(main)
