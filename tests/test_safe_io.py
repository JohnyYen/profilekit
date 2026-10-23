"""The safe-write helper: every refusal, and the atomicity guarantee."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from profilekit import safe_io
from profilekit.safe_io import UnsafeWriteError, write_file


def _leftovers(directory: Path, keep: set[str]) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p.name not in keep)


# --- writing -------------------------------------------------------------


def test_creates_a_new_file(tmp_path: Path) -> None:
    path = write_file(tmp_path / "out.txt", "hello\n", root=tmp_path, overwrite=False)

    assert path == tmp_path / "out.txt"
    assert path.read_bytes() == b"hello\n"


def test_text_is_written_as_utf8_bytes_without_newline_translation(tmp_path: Path) -> None:
    write_file(tmp_path / "out.txt", "café\nline\r\n", root=tmp_path, overwrite=False)

    assert (tmp_path / "out.txt").read_bytes() == "café\nline\r\n".encode()


def test_bytes_are_written_unchanged(tmp_path: Path) -> None:
    write_file(tmp_path / "out.bin", b"\x00\xff\n", root=tmp_path, overwrite=False)

    assert (tmp_path / "out.bin").read_bytes() == b"\x00\xff\n"


def test_overwrite_replaces_existing_content(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_bytes(b"old")

    write_file(target, "new", root=tmp_path, overwrite=True)

    assert target.read_bytes() == b"new"


def test_writes_into_a_subdirectory_of_root(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()

    write_file(tmp_path / "sub" / "out.txt", "x", root=tmp_path, overwrite=False)

    assert (tmp_path / "sub" / "out.txt").read_bytes() == b"x"


def test_new_file_honors_the_umask(tmp_path: Path) -> None:
    previous = os.umask(0o022)
    try:
        write_file(tmp_path / "a.txt", "x", root=tmp_path, overwrite=False)
        write_file(tmp_path / "b.txt", "x", root=tmp_path, overwrite=True)
    finally:
        os.umask(previous)

    assert stat.S_IMODE((tmp_path / "a.txt").stat().st_mode) == 0o644
    assert stat.S_IMODE((tmp_path / "b.txt").stat().st_mode) == 0o644


def test_overwrite_preserves_the_existing_mode(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_bytes(b"old")
    target.chmod(0o640)

    write_file(target, "new", root=tmp_path, overwrite=True)

    assert stat.S_IMODE(target.stat().st_mode) == 0o640


# --- refusals ------------------------------------------------------------


def test_refuses_to_overwrite_without_permission(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    target.write_bytes(b"precious")

    with pytest.raises(UnsafeWriteError, match="refusing to overwrite existing file"):
        write_file(target, "clobber", root=tmp_path, overwrite=False)

    assert target.read_bytes() == b"precious"
    assert _leftovers(tmp_path, {"data.json"}) == []


@pytest.mark.parametrize("overwrite", [False, True])
def test_refuses_a_symlink_inside_root(tmp_path: Path, overwrite: bool) -> None:
    real = tmp_path / "real.txt"
    real.write_bytes(b"untouched")
    link = tmp_path / "link.txt"
    link.symlink_to(real)

    with pytest.raises(UnsafeWriteError, match="symlink"):
        write_file(link, "x", root=tmp_path, overwrite=overwrite)

    assert real.read_bytes() == b"untouched"
    assert link.is_symlink()


@pytest.mark.parametrize("overwrite", [False, True])
def test_refuses_a_symlink_pointing_outside_root(tmp_path: Path, overwrite: bool) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "victim.txt"
    outside.write_bytes(b"untouched")
    (root / "out.txt").symlink_to(outside)

    with pytest.raises(UnsafeWriteError, match="symlink"):
        write_file(root / "out.txt", "x", root=root, overwrite=overwrite)

    assert outside.read_bytes() == b"untouched"


def test_refuses_a_dangling_symlink(tmp_path: Path) -> None:
    link = tmp_path / "out.txt"
    link.symlink_to(tmp_path / "missing.txt")

    with pytest.raises(UnsafeWriteError, match="symlink"):
        write_file(link, "x", root=tmp_path, overwrite=True)

    assert not (tmp_path / "missing.txt").exists()


def test_refuses_a_parent_directory_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(UnsafeWriteError, match="outside"):
        write_file(root / ".." / "escaped.txt", "x", root=root, overwrite=True)

    assert not (tmp_path / "escaped.txt").exists()


def test_refuses_a_symlinked_directory_that_leaves_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / "tunnel").symlink_to(elsewhere, target_is_directory=True)

    with pytest.raises(UnsafeWriteError, match="outside"):
        write_file(root / "tunnel" / "out.txt", "x", root=root, overwrite=True)

    assert list(elsewhere.iterdir()) == []


def test_refuses_the_root_itself(tmp_path: Path) -> None:
    with pytest.raises(UnsafeWriteError):
        write_file(tmp_path, "x", root=tmp_path, overwrite=True)


def test_refuses_a_directory(tmp_path: Path) -> None:
    (tmp_path / "dir").mkdir()

    with pytest.raises(UnsafeWriteError, match="not a regular file"):
        write_file(tmp_path / "dir", "x", root=tmp_path, overwrite=True)


def test_refusal_is_an_oserror(tmp_path: Path) -> None:
    # Callers that already handle OSError (the CLI's ledger and init paths)
    # report a refusal without new except clauses.
    assert issubclass(UnsafeWriteError, OSError)


# --- atomicity -----------------------------------------------------------


def test_failed_replace_keeps_the_previous_file_and_no_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "ledger.json"
    target.write_bytes(b"previous")

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(safe_io.os, "replace", boom)

    with pytest.raises(OSError, match="disk full"):
        write_file(target, "next", root=tmp_path, overwrite=True)

    assert target.read_bytes() == b"previous"
    assert _leftovers(tmp_path, {"ledger.json"}) == []


@pytest.mark.parametrize("overwrite", [False, True])
def test_failed_write_leaves_nothing_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, overwrite: bool
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("io error")

    monkeypatch.setattr(safe_io.os, "fsync", boom)

    with pytest.raises(OSError, match="io error"):
        write_file(tmp_path / "out.txt", "content", root=tmp_path, overwrite=overwrite)

    assert _leftovers(tmp_path, set()) == []


def test_content_is_fsynced_before_it_becomes_visible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "out.txt"
    target.write_bytes(b"old")
    events: list[str] = []
    real_fsync, real_replace = os.fsync, os.replace

    def fsync(fd: int) -> None:
        events.append("fsync")
        real_fsync(fd)

    def replace(src: str, dst: str | Path) -> None:
        events.append("replace")
        real_replace(src, dst)

    monkeypatch.setattr(safe_io.os, "fsync", fsync)
    monkeypatch.setattr(safe_io.os, "replace", replace)

    write_file(target, "new", root=tmp_path, overwrite=True)

    assert events[:2] == ["fsync", "replace"]
    assert target.read_bytes() == b"new"
