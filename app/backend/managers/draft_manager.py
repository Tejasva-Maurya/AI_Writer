import json
import logging
from pathlib import Path
from typing import Optional
from models import Draft
from managers.storage import write_json

# One chapter draft waiting for review (plan 019). It exists only between writing (step 6) and approval or discard.
log = logging.getLogger(__name__)


def _path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "draft.json"  # <repo>/data (outside app/)


def load() -> Optional[Draft]:
    p = _path()
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return Draft(**json.load(f))
    except Exception as e:  # logged, like storage.read_all: a broken file must not block every generation
        log.warning("Skipped unreadable draft %s: %s: %s", p.name, type(e).__name__, e)
        return None


def save(draft: Draft):
    write_json(_path(), draft.model_dump())  # atomic replace (KI-026)


def delete() -> bool:
    p = _path()
    if p.exists():
        p.unlink()
        return True
    return False
