"""The 7-step pipeline through POST /api/generate-chapter, with the fake ollama (KI-015, KI-025, D-011)."""
import json
import logging

from conftest import sse_events
from managers import character_manager
from models import Character, NovelMeta

SPECIALIST = NovelMeta().specialist_model
WRITER = NovelMeta().writer_model


def _generate(client, plot="zz test: the storm"):
    r = client.post("/api/generate-chapter", json={"plot": plot})
    assert r.status_code == 200
    return sse_events(r.text)


def test_full_run_saves_the_chapter(client, data_dir, fake_ollama):
    events = _generate(client)
    steps = sorted({e["step"] for e in events if e["type"] == "status"})
    assert steps == [1, 2, 3, 4, 5, 6, 7]
    assert "".join(e["content"] for e in events if e["type"] == "token") == "".join(fake_ollama.chunks)
    complete = events[-1]
    assert complete["type"] == "complete" and complete["chapter_number"] == 1

    saved = json.loads((data_dir / "chapters" / "001.json").read_text(encoding="utf-8"))
    assert saved["full_text"].startswith("The storm broke") and saved["plot_input"] == "zz test: the storm"
    assert client.get("/api/chapters").json()[0]["chapter_number"] == 1


def test_keep_alive_choreography(client, fake_ollama):
    """Steps 1-2 keep the specialist for 5 minutes, step 5 unloads it, step 7 unloads again (D-011)."""
    _generate(client)
    assert fake_ollama.calls == [
        ("chat", SPECIALIST, 300),        # step 1 analyze
        ("chat", SPECIALIST, 300),        # step 2 resolve (step 3 skipped: no new entities)
        ("generate", SPECIALIST, 0),      # step 5 unload, nothing generated
        ("chat-stream", WRITER, 300),     # step 6 writer
        ("chat", SPECIALIST, 0),          # step 7 summary + unload
    ]


def test_featured_characters_reach_the_chapter_and_the_complete_event(client, data_dir, fake_ollama):
    character_manager.save(Character(name="Zz Hero", slug="zz_hero"))
    fake_ollama.json_replies = [
        {"tone": "tense", "estimated_chapters": 1, "entity_mentions": {"characters": ["Zz Hero"], "locations": []}},
        {"characters": [{"name": "Zz Hero", "slug": "zz_hero", "status": "existing", "importance": "primary"}],
         "scenes": []},
    ]
    complete = _generate(client)[-1]
    assert complete["characters"] == ["zz_hero"]
    saved = json.loads((data_dir / "chapters" / "001.json").read_text(encoding="utf-8"))
    assert saved["characters_featured"] == ["zz_hero"]


def test_wrong_typed_specialist_output_does_not_crash(client, fake_ollama):
    fake_ollama.json_replies = [{"estimated_chapters": "2", "entity_mentions": ["not", "a", "dict"]}]
    events = _generate(client)
    multi = [e for e in events if e["type"] == "multi_chapter"]
    assert multi and multi[0]["estimated"] == 2
    assert events[-1]["type"] == "complete"


def test_pipeline_warnings_are_logged(client, fake_ollama, caplog):
    fake_ollama.generate_error = RuntimeError("unload failed")
    with caplog.at_level(logging.WARNING, logger="pipeline.chapter_pipeline"):
        events = _generate(client)
    warnings = [e["message"] for e in events if e["type"] == "warning"]
    assert any("Could not unload the specialist model" in w for w in warnings)
    assert any("Could not unload the specialist model" in r.getMessage() for r in caplog.records)
    assert events[-1]["type"] == "complete"  # a failed unload doesn't stop the chapter
