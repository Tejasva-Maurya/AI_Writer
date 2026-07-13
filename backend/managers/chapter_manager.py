import json
from pathlib import Path
from typing import List, Optional
from models import Chapter


def _data_dir() -> Path:
    return Path(__file__).parent.parent.parent / "data" / "chapters"


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
    path = _data_dir() / f"{chapter.chapter_number:03d}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chapter.model_dump(), f, indent=2, ensure_ascii=False)


def get_all(include_text: bool = False) -> List[Chapter]:
    ensure_dir()
    chapters = []
    for f in sorted(_data_dir().glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
                if not include_text:
                    data["full_text"] = ""  # strip full text for listing
                chapters.append(Chapter(**data))
        except Exception:
            pass
    return sorted(chapters, key=lambda c: c.chapter_number)


def get_next_number() -> int:
    chapters = get_all()
    if not chapters:
        return 1
    return max(c.chapter_number for c in chapters) + 1


def get_recent_n(n: int, include_text: bool = False) -> List[Chapter]:
    all_ch = get_all(include_text=True)  # always need summaries
    return all_ch[-(n):] if len(all_ch) >= n else all_ch
