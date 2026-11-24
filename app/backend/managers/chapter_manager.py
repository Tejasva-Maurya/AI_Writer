import json
from pathlib import Path
from typing import List, Optional
from models import Chapter
from managers.storage import read_all, write_json


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "chapters"  # <repo>/data (outside app/)


def ensure_dir():
    _data_dir().mkdir(parents=True, exist_ok=True)


def get_chapter(number: int) -> Optional[Chapter]:
    ensure_dir()
    path = _data_dir() / f"{number:03d}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return Chapter(**json.load(f))
    return None


def save_chapter(chapter: Chapter):
    ensure_dir()
    write_json(_data_dir() / f"{chapter.chapter_number:03d}.json", chapter.model_dump())  # atomic replace (KI-026)


def get_all(include_text: bool = False) -> List[Chapter]:
    ensure_dir()
    # Unreadable files are logged (KI-026). Listings strip the full text.
    build = (lambda d: Chapter(**d)) if include_text else (lambda d: Chapter(**{**d, "full_text": ""}))
    chapters = read_all(_data_dir(), "chapters", build)
    return sorted(chapters, key=lambda c: c.chapter_number)


def get_next_number() -> int:
    chapters = get_all()
    if not chapters:
        return 1
    return max(c.chapter_number for c in chapters) + 1


def get_recent_n(n: int, include_text: bool = False) -> List[Chapter]:
    all_ch = get_all(include_text=True)  # always need summaries
    return all_ch[-(n):] if len(all_ch) >= n else all_ch
