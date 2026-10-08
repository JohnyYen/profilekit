"""Path-scoped CI isolation (restructure-to-monorepo, spec Req: CI job isolation).

The hard invariant is TOOLCHAIN ISOLATION: a Python-scoped change must not
trigger the Node/portfolio build, and a portfolio-scoped change must not trigger
the Python data-validation job. The runner of each job (pip vs uv, extra
lint/type/coverage steps) is an implementation detail and is NOT asserted here.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

PYTHON_SCOPES = ["data/**", "src/**", "tests/**"]
PORTFOLIO_SCOPE = "apps/portfolio/**"


def _read(name: str) -> str:
    path = WORKFLOWS / name
    assert path.is_file(), f"missing workflow: {name}"
    return path.read_text(encoding="utf-8")


def test_python_workflow_scopes_python_paths_only():
    text = _read("validate.yml")
    for scope in PYTHON_SCOPES:
        assert scope in text, f"validate.yml must path-filter on {scope}"
    assert PORTFOLIO_SCOPE not in text, (
        "validate.yml must NOT trigger on apps/portfolio/** (toolchain isolation)"
    )


def test_portfolio_workflow_scopes_portfolio_only():
    text = _read("portfolio.yml")
    assert PORTFOLIO_SCOPE in text, "portfolio.yml must path-filter on apps/portfolio/**"
    for scope in PYTHON_SCOPES:
        assert scope not in text, f"portfolio.yml must NOT trigger on {scope} (toolchain isolation)"
