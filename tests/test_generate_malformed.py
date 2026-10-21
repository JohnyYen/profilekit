"""`profile generate` on a data file that is not JSON names that file.

generator-robustness requires the message to identify the file and the parse
error location. Generators load data through `utils.load_json`, so this runs
the real CLI dispatch over a scaffolded project rather than a stub.
"""

from __future__ import annotations

from pathlib import Path

import profilekit.cli as cli
from profilekit.scaffold import init_project


def test_generate_names_the_malformed_file_and_its_location(tmp_path: Path, capsys) -> None:
    init_project(tmp_path)
    (tmp_path / "data" / "experience.json").write_text("[\n  {,\n]", encoding="utf-8")

    code = cli.main(["--project", str(tmp_path), "generate"])

    err = capsys.readouterr().err
    assert code == 1
    assert "experience.json: JSON parse error at line 2 column 4" in err
    assert "Traceback" not in err
