import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from models import Chapter, ChapterVersion
from managers.storage import read_all, write_json

# Older versions of a chapter (plan 025): the text a regenerated chapter replaced, in
# data/chapter_versions/{n:03d}-{version_id}.json. Only the newest KEEP per chapter are kept.
log = logging.getLogger(__name__)
KEEP = 5  # versions per chapter: keeping a 6th deletes the oldest (D-020)
_ID_RE = re.compile(r"\d{8}-\d{6}-\d{6}")  # YYYYMMDD-HHMMSS-ffffff, when it was replaced: sorts chronologically


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "chapter_versions"  # <repo>/data (outside app/)


def is_valid_id(version_id) -> bool:
    return isinstance(version_id, str) and bool(_ID_RE.fullmatch(version_id))


def _path(number: int, version_id: str) -> Path:
    # Only a positive number and a strict id reach the file system, never a request string as such (KI-010)
    if not isinstance(number, int) or number < 1:
        raise ValueError(f"Invalid chapter number: {number!r}")
    if not is_valid_id(version_id):
        raise ValueError(f"Invalid version id: {version_id!r}")
    return _data_dir() / f"{number:03d}-{version_id}.json"


def archive(chapter: Chapter, prune_old: bool = True) -> ChapterVersion:
    """Keep chapter as an older version. Never replaces a file: a taken id moves on by a microsecond."""
    now = datetime.now()
    while True:
        version_id = now.strftime("%Y%m%d-%H%M%S-%f")
        version = ChapterVersion(**{**chapter.model_dump(), "version_id": version_id, "replaced_at": now.isoformat()})
        try:
            write_json(_path(chapter.chapter_number, version_id), version.model_dump(), exclusive=True)
            break
        except FileExistsError:
            now += timedelta(microseconds=1)
    if prune_old:
        prune(chapter.chapter_number)
    return version


def get_all(number: int, include_text: bool = False) -> List[ChapterVersion]:
    """The chapter's older versions, newest first. Unreadable files are logged and skipped (KI-026)."""
    if not isinstance(number, int) or number < 1:
        return []
    build = (lambda d: ChapterVersion(**d)) if include_text else (lambda d: ChapterVersion(**{**d, "full_text": ""}))
    versions = read_all(_data_dir(), "chapter_versions", build, pattern=f"{number:03d}-*.json")
    return sorted(versions, key=lambda v: v.version_id, reverse=True)


def get(number: int, version_id: str) -> Optional[ChapterVersion]:
    path = _path(number, version_id)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return ChapterVersion(**json.load(f))


def delete(number: int, version_id: str) -> bool:
    path = _path(number, version_id)
    if path.exists():
        path.unlink()
        return True
    return False


def prune(number: int) -> List[str]:
    """Delete all but the newest KEEP versions of the chapter. Returns the deleted ids."""
    dropped = [v.version_id for v in get_all(number)[KEEP:] if is_valid_id(v.version_id)]
    for version_id in dropped:
        delete(number, version_id)
        log.info("Deleted the oldest kept version %s of chapter %d (only the newest %d are kept)",
                 version_id, number, KEEP)
    return dropped
