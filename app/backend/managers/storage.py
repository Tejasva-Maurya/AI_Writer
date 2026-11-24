"""
Shared file helpers for the managers (KI-026).
write_json replaces a file all-or-nothing, so a crash or a full disk mid-write can no longer leave a truncated JSON
file. read_all logs every file it cannot load instead of skipping it silently.
"""
import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, List, TypeVar

log = logging.getLogger(__name__)
T = TypeVar("T")


def write_json(path: Path, data, *, exclusive: bool = False) -> None:
    """Write data as UTF-8 JSON (indent=2, same bytes as before) via a temp file in the same folder, then move it
    into place. exclusive=True never replaces an existing file: FileExistsError if the name is taken (create())."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if not exclusive:
            os.replace(tmp, path)  # atomic
            return
        try:
            os.link(tmp, path)  # atomic, and fails with FileExistsError if the name is taken
        except FileExistsError:
            raise
        except OSError:  # no hard links on this filesystem (e.g. FAT, some network drives): exclusive, not atomic
            with open(path, "x", encoding="utf-8") as f:
                f.write(text)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)


def read_all(folder: Path, label: str, build: Callable[[dict], T]) -> List[T]:
    """Load every *.json in folder with build(data). A file that cannot be read or validated is skipped and logged."""
    items = []
    for f in sorted(folder.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                items.append(build(json.load(fp)))
        except Exception as e:
            log.warning("Skipped unreadable %s/%s: %s: %s", label, f.name, type(e).__name__, e)
    return items
