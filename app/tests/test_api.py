"""HTTP API: CRUD, slugs and host checks, novel meta, export, model list and pull (KI-010, KI-017, KI-019, KI-020,
KI-033, KI-036)."""
import types

import httpx
import pytest

import main
from conftest import sse_events
from managers import chapter_manager
from models import Chapter


@pytest.fixture
def ollama_http(monkeypatch):
    """Send the backend's httpx calls to Ollama through state["handler"] (set by the test); record the URLs."""
    state = {"handler": None, "urls": []}
    real_async_client = httpx.AsyncClient

    def handler(request):
        state["urls"].append(str(request.url))
        return state["handler"](request)

    def make_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(main.httpx, "AsyncClient", make_client)
    return state


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_foreign_host_is_rejected(client):
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_character_crud_and_conflicts(client, data_dir):
    r = client.post("/api/characters", json={"character": {"name": "Elder Wu", "slug": ""}})
    assert r.status_code == 200 and r.json()["slug"] == "elder_wu"

    r = client.post("/api/characters", json={"character": {"name": "elder-wu", "slug": ""}})
    assert r.status_code == 409 and "already exists" in r.json()["detail"]

    r = client.put("/api/characters/elder_wu", json={"character": {"name": "Elder Wu", "slug": "other", "age": 70}})
    assert r.status_code == 200 and r.json()["slug"] == "elder_wu" and r.json()["age"] == "70"

    assert [c["slug"] for c in client.get("/api/characters").json()] == ["elder_wu"]
    assert client.delete("/api/characters/elder_wu").status_code == 200
    assert client.delete("/api/characters/elder_wu").status_code == 404
    assert client.post("/api/characters", json={"character": {"name": "???", "slug": ""}}).status_code == 422


def test_scene_create(client):
    r = client.post("/api/scenes", json={"scene": {"name": "Azure Cave", "slug": ""}})
    assert r.status_code == 200 and r.json()["slug"] == "azure_cave"
    assert client.post("/api/scenes", json={"scene": {"name": "azure cave", "slug": ""}}).status_code == 409


def test_path_traversal_slug_touches_nothing(client, data_dir):
    meta = client.get("/api/novel-meta").json()
    client.put("/api/novel-meta", json={"meta": meta})
    assert (data_dir / "novel_meta.json").exists()
    assert client.delete("/api/characters/..%5Cnovel_meta").status_code == 404
    assert client.get("/api/characters/..%5Cnovel_meta").status_code in (404, 405)
    assert (data_dir / "novel_meta.json").exists()


def test_novel_meta_round_trip_keeps_every_field(client):
    meta = client.get("/api/novel-meta").json()
    meta.update(title="林凡传奇", total_chapters=3, created_at="2026-01-01T00:00:00")
    assert client.put("/api/novel-meta", json={"meta": meta}).status_code == 200
    assert client.get("/api/novel-meta").json() == meta


def test_export_serves_from_memory_with_safe_name(client, data_dir):
    meta = client.get("/api/novel-meta").json()
    meta["title"] = "Test: A/B?"
    client.put("/api/novel-meta", json={"meta": meta})
    chapter_manager.save_chapter(Chapter(chapter_number=1, title="One", full_text="It began."))
    before = sorted(p.relative_to(data_dir).as_posix() for p in data_dir.rglob("*") if p.is_file())

    r = client.get("/api/export/txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert r.headers["content-disposition"] == 'attachment; filename="Test__A_B_.txt"'
    assert "Chapter 1: One" in r.text and "It began." in r.text and "\r" not in r.text

    md = client.get("/api/export/md")
    assert md.status_code == 200 and md.text.startswith("# Test: A/B?")
    assert client.get("/api/export/pdf").status_code == 400
    after = sorted(p.relative_to(data_dir).as_posix() for p in data_dir.rglob("*") if p.is_file())
    assert after == before  # nothing written (KI-017)


def test_cancel_when_idle(client):
    assert client.post("/api/generate-chapter/cancel").json() == {"cancelled": False}


def test_second_generation_gets_409(client):
    main._generation["task"] = types.SimpleNamespace(done=lambda: False)  # a generation is "running"
    r = client.post("/api/generate-chapter", json={"plot": "zz test"})
    assert r.status_code == 409 and "already being generated" in r.json()["detail"]


def test_models_installed_is_exact(client, ollama_http):
    ollama_http["handler"] = lambda request: httpx.Response(
        200, json={"models": [{"name": "gemma3:4b"}, {"name": "phi4-mini:3.8b"}]})
    data = client.get("/api/models").json()
    assert data["ollama_running"] is True
    assert data["installed"] == ["gemma3:4b", "phi4-mini:3.8b"]
    assert [m["name"] for m in data["recommended"] if m["installed"]] == ["phi4-mini:3.8b"]
    assert ollama_http["urls"] == [f"{main.OLLAMA_BASE_URL}/api/tags"]


def test_models_unreachable_names_the_address(client, ollama_http):
    def refuse(request):
        raise httpx.ConnectError("All connection attempts failed", request=request)

    ollama_http["handler"] = refuse
    data = client.get("/api/models").json()
    assert data["ollama_running"] is False and data["installed"] == []
    assert main.OLLAMA_BASE_URL in data["ollama_error"]


PROGRESS = b'{"status": "pulling manifest"}\n{"status": "pulling abc", "total": 100, "completed": 50}\n'


@pytest.mark.parametrize("response,expected", [
    (lambda: httpx.Response(200, content=PROGRESS + b'{"status": "success"}\n'), ("success", None)),
    (lambda: httpx.Response(404, json={"error": "pull model manifest: file does not exist"}),
     ("error", "Ollama returned 404: pull model manifest: file does not exist")),
    (lambda: httpx.Response(200, content=PROGRESS + b'{"error": "max retries exceeded"}\n'),
     ("error", "max retries exceeded")),
    (lambda: httpx.Response(200, content=PROGRESS), ("error", "Ollama ended the download without confirming success")),
], ids=["success", "http-404", "error-line", "truncated"])
def test_pull_reports_success_only_when_ollama_confirms(client, ollama_http, caplog, response, expected):
    ollama_http["handler"] = lambda request: response()
    events = sse_events(client.post("/api/models/pull", json={"model": "zz-model:1b"}).text)
    status, message = expected
    assert events[-1]["status"] == status
    assert sum(e["status"] in ("success", "error") for e in events) == 1
    if message:
        assert events[-1]["message"] == message
        assert any("zz-model:1b" in r.getMessage() and message in r.getMessage() for r in caplog.records)
    assert ollama_http["urls"] == [f"{main.OLLAMA_BASE_URL}/api/pull"]


def test_pull_requires_a_model_name(client):
    assert client.post("/api/models/pull", json={}).status_code == 400
