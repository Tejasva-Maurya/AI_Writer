import json
import re
from pathlib import Path
from typing import List, Optional, Dict
from models import Character

# A slug is a filename stem: letters/digits of any script, "_" and "-" only. No dots, slashes or backslashes (KI-010).
_SLUG_RE = re.compile(r"[\w-]+")


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "characters"  # <repo>/data (outside app/)


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s)
    return s.strip("_")


def is_valid_slug(slug) -> bool:
    return isinstance(slug, str) and bool(_SLUG_RE.fullmatch(slug))


def _path(slug: str) -> Path:
    if not is_valid_slug(slug):
        raise ValueError(f"Invalid character slug: {slug!r}")
    return _data_dir() / f"{slug}.json"


def ensure_dir():
    _data_dir().mkdir(parents=True, exist_ok=True)


def get_all() -> List[Character]:
    ensure_dir()
    chars = []
    for f in _data_dir().glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                chars.append(Character(**json.load(fp)))
        except Exception:
            pass
    return sorted(chars, key=lambda c: c.name)


def get_by_slug(slug: str) -> Optional[Character]:
    if not is_valid_slug(slug):
        return None
    ensure_dir()
    path = _path(slug)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return Character(**json.load(f))
    return None


def save(char: Character):
    ensure_dir()
    path = _path(char.slug)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(char.model_dump(), f, indent=2, ensure_ascii=False)


def delete(slug: str) -> bool:
    if not is_valid_slug(slug):
        return False
    path = _path(slug)
    if path.exists():
        path.unlink()
        return True
    return False


def get_as_dict() -> Dict[str, Character]:
    return {c.slug: c for c in get_all()}


def make_slug(name: str) -> str:
    return _slugify(name)


def create(char: Character):
    """Save a new character. Never overwrites: raises FileExistsError if the slug, or an equivalent one
    (same letters ignoring case, "-" vs "_"), is taken (KI-036, KI-009)."""
    path = _path(char.slug)
    ensure_dir()
    key = _slugify(char.slug)
    clash = next((f.stem for f in _data_dir().glob("*.json") if _slugify(f.stem) == key), None)
    if clash is not None:
        raise FileExistsError(f"Character '{clash}' already exists")
    try:
        with open(path, "x", encoding="utf-8") as f:
            json.dump(char.model_dump(), f, indent=2, ensure_ascii=False)
    except FileExistsError:
        raise FileExistsError(f"Character '{char.slug}' already exists") from None
