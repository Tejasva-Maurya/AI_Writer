"""
Test setup (KI-025). Run from the repo root: py -m pytest app/tests
- app/backend goes on sys.path (the backend uses flat imports).
- A recording fake `ollama` module is installed before any app import, so no Ollama server is needed.
- Every manager is redirected to a temp folder for each test, and the run fails if the real data/ changed.
"""
import asyncio
import json
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
REAL_DATA = Path(__file__).resolve().parents[2] / "data"
sys.path.insert(0, str(BACKEND))


# ── Fake ollama ────────────────────────────────────────────────
BLOCK = object()  # in FakeOllama.chunks: the stream waits here until it is cancelled (a chapter still being written)


class FakeOllama:
    """Records every call as (kind, model, keep_alive). Non-streamed chat replies come from `json_replies`
    (in order, then `default_json`; an exception in the list is raised instead); a streamed chat yields `chunks`
    (an exception there is raised mid-stream, `BLOCK` waits until cancelled).
    `chat_options` keeps the `options` of every non-streamed chat, `chat_messages` its messages."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = []
        self.chat_options = []
        self.chat_messages = []
        self.json_replies = []
        self.default_json = {}
        self.chunks = ["The storm broke over the lab.", "\n\nXiao Fan looked up."]
        self.generate_error = None  # set to an exception to make the step-5 unload fail

    def next_reply(self) -> str:
        reply = self.json_replies.pop(0) if self.json_replies else self.default_json
        if isinstance(reply, BaseException):
            raise reply
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
                    if chunk is BLOCK:
                        await asyncio.Event().wait()  # never set: only a cancel ends it
                    elif isinstance(chunk, BaseException):
                        raise chunk
                    else:
                        yield _Response(chunk)
            return tokens()
        FAKE.chat_options.append(kwargs.get("options"))
        FAKE.chat_messages.append(messages)
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
    """Files by size and mtime, folders by mtime: a file created and deleted again during the run changes its folder's
    mtime, so a manager missing from data_dir is caught even when it cleans up after itself (plan 019)."""
    if not folder.exists():
        return {}
    snap = {".": ("dir", folder.stat().st_mtime_ns)}
    for p in folder.rglob("*"):
        stat = p.stat()
        snap[str(p.relative_to(folder))] = (stat.st_size, stat.st_mtime_ns) if p.is_file() else ("dir", stat.st_mtime_ns)
    return snap


@pytest.fixture(scope="session", autouse=True)
def real_data_untouched():
    """Safety net: the user's novel in data/ must be exactly the same after the run."""
    before = _snapshot(REAL_DATA)
    yield
    assert _snapshot(REAL_DATA) == before, "the test run changed the real data/ folder"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Point every manager at an empty temp data folder (add new managers here)."""
    from managers import (chapter_manager, character_manager, draft_manager, novel_meta_manager, scene_manager,
                          world_manager)

    root = tmp_path / "data"
    monkeypatch.setattr(character_manager, "_data_dir", lambda: root / "characters")
    monkeypatch.setattr(scene_manager, "_data_dir", lambda: root / "scenes")
    monkeypatch.setattr(chapter_manager, "_data_dir", lambda: root / "chapters")
    monkeypatch.setattr(world_manager, "_path", lambda: root / "world_settings.json")
    monkeypatch.setattr(novel_meta_manager, "_path", lambda: root / "novel_meta.json")
    monkeypatch.setattr(draft_manager, "_path", lambda: root / "draft.json")
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
    main._job["kind"] = None
    with TestClient(main.app, base_url="http://127.0.0.1") as test_client:
        yield test_client
    main._generation["task"] = None
    main._job["kind"] = None


def sse_events(body: str) -> list:
    """Parse an SSE response body into a list of event dicts."""
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
