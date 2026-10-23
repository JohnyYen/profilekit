"""The one place profilekit writes files.

Every file the package writes — generated output, the output manifest,
scaffolded project files, published artifacts, the publish ledger — goes
through :func:`write_file`. Each of those writers once had its own bug of the
same class: ``init`` overwrote existing data, ``publish`` could target the
canonical data directory, a symlinked artifact was written through, and the
ledger write was not atomic. Each was fixed where it happened; this module is
the fix for the class. ``tests/test_architecture_writes.py`` fails if any
other module writes a file directly.

The guarantees, in the order they are checked:

* A path that is a symlink is refused, wherever it points. Writing follows
  symlinks; replacing one would silently change what the link meant.
* A path whose directory resolves outside *root* is refused, so a symlinked
  directory cannot tunnel a write out of the tree the caller owns.
* An existing file is only replaced when the caller passes
  ``overwrite=True``; anything that is not a regular file is never replaced.
* The content is written as bytes (text is encoded as UTF-8), so newlines are
  never translated and digests are identical on every platform.
* An overwrite goes to a temporary file in the same directory, is flushed to
  disk, then replaces the target in one ``os.replace``: a reader sees the old
  file or the new one, never a truncated one. A new file is created
  exclusively, so a file that appears concurrently is not clobbered either.
  Either way, a failure removes whatever this call created.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import stat
from pathlib import Path

# Not every platform has these flags; where one is missing, the explicit
# checks below still apply.
_BINARY = getattr(os, "O_BINARY", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _BINARY | _NOFOLLOW
_DEFAULT_MODE = 0o666  # narrowed by the process umask, as open() would do


class UnsafeWriteError(OSError):
    """Raised when a write is refused because it would be unsafe.

    An ``OSError`` so that every caller already handling a failed write
    reports a refusal the same way, without a new ``except`` clause.
    """


def write_file(path: Path, data: bytes | str, *, root: Path, overwrite: bool) -> Path:
    """Write *data* to *path*, which must stay inside *root*; return *path*.

    Raises:
        UnsafeWriteError: *path* is a symlink, resolves outside *root*, is not
            a regular file, or exists and *overwrite* is false.
        OSError: the write itself failed; nothing this call created is left.
    """
    path = Path(path)
    payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    target = _checked_target(path, Path(root))

    if overwrite and target.exists():
        _replace(target, payload, mode=stat.S_IMODE(target.stat().st_mode))
    else:
        _create(target, payload)
    return path


def _checked_target(path: Path, root: Path) -> Path:
    if path.is_symlink():
        raise UnsafeWriteError(f"refusing to write through a symlink: {path}")
    if path.name in ("", ".", ".."):
        raise UnsafeWriteError(f"refusing to write to a directory: {path}")

    resolved_root = root.resolve()
    directory = path.parent.resolve()
    if directory != resolved_root and resolved_root not in directory.parents:
        raise UnsafeWriteError(
            f"refusing to write outside {resolved_root}: {path} -> {directory / path.name}"
        )

    target = directory / path.name
    if target.exists() and not target.is_file():
        raise UnsafeWriteError(f"refusing to replace what is not a regular file: {path}")
    return target


def _create(target: Path, payload: bytes) -> None:
    try:
        fd = os.open(target, _CREATE_FLAGS, _DEFAULT_MODE)
    except FileExistsError:
        raise UnsafeWriteError(f"refusing to overwrite existing file: {target}") from None
    _fill(fd, payload, created=target)


def _replace(target: Path, payload: bytes, *, mode: int) -> None:
    tmp = target.with_name(f".{target.name}.{secrets.token_hex(8)}.tmp")
    fd = os.open(tmp, _CREATE_FLAGS, _DEFAULT_MODE)
    try:
        os.chmod(tmp, mode)
        _fill(fd, payload, created=tmp)
        os.replace(tmp, target)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()
        raise


def _fill(fd: int, payload: bytes, *, created: Path) -> None:
    """Write *payload* to *fd* and flush it to disk; on failure remove *created*."""
    try:
        try:
            view = memoryview(payload)
            while view:
                view = view[os.write(fd, view) :]
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            created.unlink()
        raise


__all__ = ["UnsafeWriteError", "write_file"]
