import json
from pathlib import Path
from models import WorldSettings


def _path() -> Path:
    return Path(__file__).parent.parent.parent / "data" / "world_settings.json"


def load() -> WorldSettings:
    p = _path()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return WorldSettings(**json.load(f))
    return WorldSettings()


def save(settings: WorldSettings):
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2, ensure_ascii=False)
