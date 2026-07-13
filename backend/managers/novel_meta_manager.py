import json
from pathlib import Path
from models import NovelMeta


def _path() -> Path:
    return Path(__file__).parent.parent.parent / "data" / "novel_meta.json"


def load() -> NovelMeta:
    p = _path()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return NovelMeta(**json.load(f))
    return NovelMeta()


def save(meta: NovelMeta):
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(meta.model_dump(), f, indent=2, ensure_ascii=False)
