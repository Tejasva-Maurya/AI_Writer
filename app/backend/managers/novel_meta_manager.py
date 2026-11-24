import json
from pathlib import Path
from models import NovelMeta
from managers.storage import write_json


def _path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "novel_meta.json"  # <repo>/data (outside app/)


def load() -> NovelMeta:
    p = _path()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return NovelMeta(**json.load(f))
    return NovelMeta()


def save(meta: NovelMeta):
    write_json(_path(), meta.model_dump())  # atomic replace (KI-026)
