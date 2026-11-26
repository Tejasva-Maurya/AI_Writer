import json
import re
from pathlib import Path
from typing import List, Optional
from models import Scene
from managers.storage import read_all, write_json

# A slug is a filename stem: letters/digits of any script, "_" and "-" only. No dots, slashes or backslashes (KI-010).
_SLUG_RE = re.compile(r"[\w-]+")


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "scenes"  # <repo>/data (outside app/)


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s)
    return s.strip("_")


def is_valid_slug(slug) -> bool:
    return isinstance(slug, str) and bool(_SLUG_RE.fullmatch(slug))


def _path(slug: str) -> Path:
    if not is_valid_slug(slug):
        raise ValueError(f"Invalid scene slug: {slug!r}")
    return _data_dir() / f"{slug}.json"


def ensure_dir():
    _data_dir().mkdir(parents=True, exist_ok=True)


def get_all() -> List[Scene]:
    ensure_dir()
    scenes = read_all(_data_dir(), "scenes", lambda d: Scene(**d))  # unreadable files are logged (KI-026)
    return sorted(scenes, key=lambda s: s.name)


def get_by_slug(slug: str) -> Optional[Scene]:
    if not is_valid_slug(slug):
        return None
    ensure_dir()
    path = _path(slug)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return Scene(**json.load(f))
    return None


def save(scene: Scene):
    ensure_dir()
    write_json(_path(scene.slug), scene.model_dump())  # atomic replace (KI-026)


def delete(slug: str) -> bool:
    if not is_valid_slug(slug):
        return False
    path = _path(slug)
    if path.exists():
        path.unlink()
        return True
    return False


def make_slug(name: str) -> str:
    return _slugify(name)


def create(scene: Scene):
    """Save a new scene. Never overwrites: raises FileExistsError if the slug, or an equivalent one
    (same letters ignoring case, "-" vs "_"), is taken (KI-036, KI-009)."""
    path = _path(scene.slug)
    ensure_dir()
    key = _slugify(scene.slug)
    clash = next((f.stem for f in _data_dir().glob("*.json") if _slugify(f.stem) == key), None)
    if clash is not None:
        raise FileExistsError(f"Scene '{clash}' already exists")
    try:
        write_json(path, scene.model_dump(), exclusive=True)  # atomic, never replaces (KI-026)
    except FileExistsError:
        raise FileExistsError(f"Scene '{scene.slug}' already exists") from None
