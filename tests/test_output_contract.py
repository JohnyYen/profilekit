"""Output directory contract (restructure-to-monorepo, spec Req: Output contract).

The restructure must not change the generated-artifact names consumed by
external deploy targets. output/ remains the sole artifact destination.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

EXPECTED_ARTIFACTS = {
    "github-readme.md",
    "linkedin.md",
    "portfolio.md",
    "cv.md",
    "cv.yml",
}


def test_output_contains_expected_artifacts():
    assert OUTPUT.is_dir(), "output/ must exist as the artifact destination"
    present = {p.name for p in OUTPUT.iterdir() if p.is_file()}
    missing = EXPECTED_ARTIFACTS - present
    assert not missing, f"output/ missing expected artifacts: {sorted(missing)}"
