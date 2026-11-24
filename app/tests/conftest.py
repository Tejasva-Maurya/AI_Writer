"""
Test setup (KI-025). Run from the repo root: py -m pytest app/tests
- app/backend goes on sys.path (the backend uses flat imports).
- A recording fake `ollama` module is installed before any app import, so no Ollama server is needed.
- Every manager is redirected to a temp folder for each test, and the run fails if the real data/ changed.
"""
import json
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
REAL_DATA = Path(__file__).resolve().parents[2] / "data"
sys.path.insert(0, str(BACKEND))


# ── Fake ollama ────────────────────────────────────────────────
class FakeOllama:
    """Records every call as (kind, model, keep_alive). Non-streamed chat replies come from `json_replies`
    (in order, then `default_json`); a streamed chat yields `chunks`."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = []
        self.json_replies = []
        self.default_json = {}
        self.chunks = ["The storm broke over the lab.", "\n\nXiao Fan looked up."]
        self.generate_error = None  # set to an exception to make the step-5 unload fail

    def next_reply(self) -> str:
        reply = self.json_replies.pop(0) if self.json_replies else self.default_json
        return reply if isinstance(reply, str) else json.dumps(reply)


FAKE = FakeOllama()


class _Message:
    def __init__(self, content):
        self.content = content


class _Response:
    def __init__(self, content):
        self.message = _Message(content)


class _AsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, model=None, messages=None, stream=False, keep_alive=None, **kwargs):
        FAKE.calls.append(("chat-stream" if stream else "chat", model, keep_alive))
        if stream:
            async def tokens():
                for chunk in FAKE.chunks:
                    yield _Response(chunk)
            return tokens()
        return _Response(FAKE.next_reply())

    async def generate(self, model=None, keep_alive=None, **kwargs):
        FAKE.calls.append(("generate", model, keep_alive))
        if FAKE.generate_error:
            raise FAKE.generate_error


_fake_module = types.ModuleType("ollama")
_fake_module.AsyncClient = _AsyncClient
sys.modules["ollama"] = _fake_module  # must happen before the agents are imported


# ── Fixtures ───────────────────────────────────────────────────
def _snapshot(folder: Path) -> dict:
    if not folder.exists():
        return {}
    return {str(p.relative_to(folder)): (p.stat().st_size, p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()}


@pytest.fixture(scope="session", autouse=True)
def real_data_untouched():
    """Safety net: the user's novel in data/ must be exactly the same after the run."""
    before = _snapshot(REAL_DATA)
    yield
    assert _snapshot(REAL_DATA) == before, "the test run changed the real data/ folder"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Point every manager at an empty temp data folder (add new managers here)."""
    from managers import chapter_manager, character_manager, novel_meta_manager, scene_manager, world_manager

    root = tmp_path / "data"
    monkeypatch.setattr(character_manager, "_data_dir", lambda: root / "characters")
    monkeypatch.setattr(scene_manager, "_data_dir", lambda: root / "scenes")
    monkeypatch.setattr(chapter_manager, "_data_dir", lambda: root / "chapters")
    monkeypatch.setattr(world_manager, "_path", lambda: root / "world_settings.json")
    monkeypatch.setattr(novel_meta_manager, "_path", lambda: root / "novel_meta.json")
    FAKE.reset()
    return root


@pytest.fixture
def fake_ollama():
    return FAKE


@pytest.fixture
def client():
    """TestClient on 127.0.0.1: TrustedHostMiddleware rejects the default "testserver" host."""
    from fastapi.testclient import TestClient

    import main

    main._generation["task"] = None
    with TestClient(main.app, base_url="http://127.0.0.1") as test_client:
        yield test_client
    main._generation["task"] = None


def sse_events(body: str) -> list:
    """Parse an SSE response body into a list of event dicts."""
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
