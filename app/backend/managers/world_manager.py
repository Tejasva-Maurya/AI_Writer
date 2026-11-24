import json
from pathlib import Path
from models import WorldSettings
from managers.storage import write_json


def _path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "world_settings.json"  # <repo>/data (outside app/)


def load() -> WorldSettings:
    p = _path()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return WorldSettings(**json.load(f))
    return WorldSettings()


def save(settings: WorldSettings):
    write_json(_path(), settings.model_dump())  # atomic replace (KI-026)
