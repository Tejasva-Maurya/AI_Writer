"""The 7-step pipeline through POST /api/generate-chapter, with the fake ollama (KI-015, KI-025, KI-041, D-011,
plan 019)."""
import json
import logging

from conftest import sse_events
from managers import character_manager, draft_manager, scene_manager
from models import Character, NovelMeta, Scene

SPECIALIST = NovelMeta().specialist_model
WRITER = NovelMeta().writer_model


def _generate(client, plot="zz test: the storm", **extra):
    r = client.post("/api/generate-chapter", json={"plot": plot, **extra})
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


# ── Drafts (plan 019) ──────────────────────────────────────────
def test_review_mode_keeps_a_draft_and_skips_step_7(client, data_dir, fake_ollama):
    events = _generate(client, review=True)
    draft_event = events[-1]
    assert draft_event["type"] == "draft_complete" and draft_event["chapter_number"] == 1
    assert draft_event["full_text"] == "".join(fake_ollama.chunks)
    assert 7 not in {e.get("step") for e in events if e["type"] == "status"}
    assert not any(e["type"] == "complete" for e in events)

    assert not (data_dir / "chapters" / "001.json").exists()  # nothing saved as a chapter yet
    draft = draft_manager.load()
    assert draft.chapter_number == 1 and draft.plot_input == "zz test: the storm"
    assert draft.full_text == draft_event["full_text"]
    # Step 5 unloads the specialist; nothing loads it again until the draft is approved (D-011)
    assert fake_ollama.calls[-2:] == [("generate", SPECIALIST, 0), ("chat-stream", WRITER, 300)]


def test_one_click_mode_saves_the_chapter_and_removes_the_draft(client, data_dir):
    assert _generate(client)[-1]["type"] == "complete"
    assert (data_dir / "chapters" / "001.json").exists()
    assert draft_manager.load() is None


def test_failed_summary_keeps_the_written_chapter_as_a_draft(client, data_dir, fake_ollama):
    """KI-041: a step-7 failure used to lose the chapter."""
    fake_ollama.json_replies = [{}, {}, ConnectionError("Ollama went away")]  # analyze, resolve, then step 7 fails
    events = _generate(client)
    error = events[-1]
    assert error["type"] == "error" and error.get("draft_saved") is True
    assert "kept as a draft" in error["message"]
    assert not (data_dir / "chapters" / "001.json").exists()
    assert draft_manager.load().full_text == "".join(fake_ollama.chunks)


def test_step_3_profiles_are_recorded_on_the_draft(client, fake_ollama):
    fake_ollama.json_replies = [
        {"entity_mentions": {"characters": ["Zz New"], "locations": ["Zz Cave"]}},
        {"characters": [{"name": "Zz New", "slug": "zz_new", "status": "new", "importance": "primary"}],
         "scenes": [{"name": "Zz Cave", "slug": "zz_cave", "status": "new", "importance": "main"}]},
        {"characters": [{"name": "Zz New"}], "scenes": [{"name": "Zz Cave"}]},
    ]
    event = _generate(client, review=True)[-1]
    assert event["new_characters"] == ["zz_new"] and event["new_scenes"] == ["zz_cave"]
    draft = draft_manager.load()
    assert draft.new_characters == ["zz_new"] and draft.characters_featured == ["zz_new"]


def test_tagged_entities_reach_the_context_even_when_the_specialist_misses_them(client, fake_ollama):
    character_manager.save(Character(name="Zz Hero", slug="zz_hero", personality="Zz stubborn"))
    scene_manager.save(Scene(name="Zz Peak", slug="zz_peak", description="Zz windy summit"))
    fake_ollama.json_replies = [{}, {}]  # the specialist finds no entities at all
    event = _generate(client, review=True, tagged_characters=["zz_hero", "zz_ghost", "../x"],
                      tagged_scenes=["zz_peak"])[-1]
    assert event["characters"] == ["zz_hero"] and event["scenes"] == ["zz_peak"]  # unknown tags are ignored
    assert draft_manager.load().characters_featured == ["zz_hero"]


def test_tagged_character_gets_the_full_profile_in_the_writer_prompt(client, fake_ollama, monkeypatch):
    from agents import writer
    seen = {}
    original = writer.stream_chapter

    async def spy(master_prompt, plot, chapter_number, model):
        seen["prompt"] = master_prompt
        async for item in original(master_prompt, plot, chapter_number, model):
            yield item

    monkeypatch.setattr(writer, "stream_chapter", spy)
    character_manager.save(Character(name="Zz Hero", slug="zz_hero", personality="Zz stubborn"))
    fake_ollama.json_replies = [{}, {"characters": [{"name": "Zz Hero", "slug": "zz_hero", "status": "existing",
                                                      "importance": "secondary"}], "scenes": []}]
    _generate(client, review=True, tagged_characters=["zz_hero"])
    assert "=== PRIMARY CHARACTERS ===" in seen["prompt"] and "Zz stubborn" in seen["prompt"]
