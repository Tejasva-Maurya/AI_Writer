import json
import re
from pathlib import Path
from typing import List, Optional, Dict
from models import Scene


def _data_dir() -> Path:
    return Path(__file__).parent.parent.parent / "data" / "scenes"


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s)
    return s.strip("_")


def ensure_dir():
    _data_dir().mkdir(parents=True, exist_ok=True)


def get_all() -> List[Scene]:
    ensure_dir()
    scenes = []
    for f in _data_dir().glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                scenes.append(Scene(**json.load(fp)))
        except Exception:
            pass
    return sorted(scenes, key=lambda s: s.name)


def get_by_slug(slug: str) -> Optional[Scene]:
    ensure_dir()
    path = _data_dir() / f"{slug}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return Scene(**json.load(f))
    return None


def save(scene: Scene):
    ensure_dir()
    path = _data_dir() / f"{scene.slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scene.model_dump(), f, indent=2, ensure_ascii=False)


def delete(slug: str) -> bool:
    path = _data_dir() / f"{slug}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def get_as_dict() -> Dict[str, Scene]:
    return {s.slug: s for s in get_all()}


def make_slug(name: str) -> str:
    return _slugify(name)
