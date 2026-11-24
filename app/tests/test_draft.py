"""Draft review: the /api/draft routes, the one-job-at-a-time guard and approval (plan 019, KI-041)."""
import json
import types

import pytest

import main
from managers import character_manager, draft_manager, novel_meta_manager
from models import Character, Draft, NovelMeta

WRITER = NovelMeta().writer_model


def _draft(**fields) -> Draft:
    draft = Draft(**{"chapter_number": 1, "plot_input": "zz plot", "full_text": "Zz first.\n\nZz second.", **fields})
    draft_manager.save(draft)
    return draft


# ── Read, edit, discard ────────────────────────────────────────
def test_no_draft(client):
    r = client.get("/api/draft")
    assert r.status_code == 200 and r.json() is None  # a normal state, not an error
    assert client.put("/api/draft", json={"full_text": "x"}).status_code == 404
    assert client.delete("/api/draft").status_code == 404
    assert client.post("/api/draft/approve", json={}).status_code == 404
    rewrite = {"passage": "x", "instruction": "darker"}
    assert client.post("/api/draft/rewrite", json=rewrite).status_code == 404


def test_edit_and_discard(client):
    _draft()
    r = client.put("/api/draft", json={"full_text": "Zz edited.", "title": "  Zz Title  "})
    assert r.status_code == 200 and r.json()["title"] == "Zz Title" and r.json()["updated_at"]
    assert client.get("/api/draft").json()["full_text"] == "Zz edited."
    assert client.delete("/api/draft").json() == {"success": True}
    assert draft_manager.load() is None


def test_unreadable_draft_counts_as_none(client, data_dir, caplog):
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "draft.json").write_text("{broken", encoding="utf-8")
    assert client.get("/api/draft").json() is None
    assert any("draft.json" in r.getMessage() for r in caplog.records)


def test_generate_is_blocked_while_a_draft_waits(client):
    _draft(chapter_number=4)
    r = client.post("/api/generate-chapter", json={"plot": "zz next"})
    assert r.status_code == 409 and "draft of chapter 4" in r.json()["detail"]


# ── Rewrite ────────────────────────────────────────────────────
def test_rewrite_returns_the_replacement_and_keeps_the_context(client, fake_ollama):
    _draft()
    fake_ollama.json_replies = ["```\nZz darker second.\n```"]
    r = client.post("/api/draft/rewrite", json={"before": "Zz first.\n\n", "passage": "Zz second.", "after": "",
                                                 "instruction": "  make it darker "})
    assert r.status_code == 200 and r.json() == {"replacement": "Zz darker second."}
    assert fake_ollama.calls == [("chat", WRITER, 300)]
    assert fake_ollama.chat_options[-1]["num_ctx"] == 32768  # the whole draft fits; Ollama's default would cut it
    prompt = fake_ollama.chat_messages[-1][1]["content"]
    assert "Zz first." in prompt and "Zz second." in prompt and "make it darker" in prompt and "zz plot" in prompt
    assert draft_manager.load().full_text == "Zz first.\n\nZz second."  # the editor applies it, not the server


@pytest.mark.parametrize("body", [
    {"passage": "   ", "instruction": "darker"},
    {"passage": "Zz second.", "instruction": " "},
])
def test_rewrite_needs_a_passage_and_an_instruction(client, body):
    _draft()
    assert client.post("/api/draft/rewrite", json=body).status_code == 422


def test_rewrite_failure_is_an_error_not_text(client, fake_ollama):
    _draft()
    fake_ollama.json_replies = [ConnectionError("writer gone")]
    r = client.post("/api/draft/rewrite", json={"passage": "Zz second.", "instruction": "darker"})
    assert r.status_code == 500 and "writer gone" in r.json()["detail"]
    assert main._job["kind"] is None  # the guard is released


def test_empty_rewrite_is_an_error(client, fake_ollama):
    _draft()
    fake_ollama.json_replies = ["   "]
    assert client.post("/api/draft/rewrite", json={"passage": "Zz second.", "instruction": "darker"}).status_code == 500


def test_llm_jobs_run_one_at_a_time(client):
    _draft()
    main._generation["task"] = types.SimpleNamespace(done=lambda: False)  # a generation is "running"
    assert client.post("/api/draft/rewrite", json={"passage": "x", "instruction": "y"}).status_code == 409
    assert client.post("/api/draft/approve", json={}).status_code == 409
    main._generation["task"] = None

    main._job["kind"] = "approve"
    assert client.post("/api/generate-chapter", json={"plot": "zz"}).status_code == 409
    assert client.put("/api/draft", json={"full_text": "x"}).status_code == 409
    assert client.delete("/api/draft").status_code == 409
    main._job["kind"] = "rewrite"
    r = client.post("/api/draft/approve", json={})
    assert r.status_code == 409 and "rewritten" in r.json()["detail"]


# ── Approve ────────────────────────────────────────────────────
def test_approve_saves_the_final_text_and_runs_step_7(client, data_dir, fake_ollama):
    character_manager.save(Character(name="Zz Hero", slug="zz_hero", abilities=["sword"]))
    _draft(chapter_number=2, characters_featured=["zz_hero"])
    fake_ollama.json_replies = [{
        "chapter_title": "Zz Suggested", "micro_summary": "Zz micro",
        "character_updates": {"zz_hero": {"arc_notes": "Zz grows", "new_abilities": ["shield", "sword"]}},
    }]
    r = client.post("/api/draft/approve", json={"full_text": "Zz final words here.", "title": " "})
    assert r.status_code == 200
    chapter = r.json()["chapter"]
    assert chapter["title"] == "Zz Suggested" and chapter["full_text"] == "Zz final words here."
    assert chapter["word_count"] == 4 and chapter["plot_input"] == "zz plot" and chapter["micro_summary"] == "Zz micro"
    assert r.json()["warnings"] == []

    saved = json.loads((data_dir / "chapters" / "002.json").read_text(encoding="utf-8"))
    assert saved["full_text"] == "Zz final words here." and saved["characters_featured"] == ["zz_hero"]
    hero = character_manager.get_by_slug("zz_hero")
    assert hero.last_seen_chapter == 2 and hero.arc_notes == "Zz grows" and hero.abilities == ["sword", "shield"]
    assert novel_meta_manager.load().total_chapters == 2
    assert draft_manager.load() is None
    assert fake_ollama.calls == [("chat", NovelMeta().specialist_model, 0)]  # step 7 unloads the specialist


def test_approve_uses_the_authors_title(client, fake_ollama):
    _draft()
    fake_ollama.json_replies = [{"chapter_title": "Zz Suggested"}]
    assert client.post("/api/draft/approve", json={"title": "Zz Mine"}).json()["chapter"]["title"] == "Zz Mine"


def test_approve_rejects_an_empty_draft(client):
    _draft()
    assert client.post("/api/draft/approve", json={"full_text": "  \n "}).status_code == 422
    assert draft_manager.load().full_text == "Zz first.\n\nZz second."  # nothing replaced


def test_failed_approval_keeps_the_draft_with_the_edits(client, data_dir, fake_ollama):
    _draft()
    fake_ollama.json_replies = [ConnectionError("specialist gone")]
    r = client.post("/api/draft/approve", json={"full_text": "Zz edited final."})
    assert r.status_code == 500 and "draft is kept" in r.json()["detail"]
    assert draft_manager.load().full_text == "Zz edited final."
    assert not (data_dir / "chapters").exists() or not any((data_dir / "chapters").iterdir())
    assert main._job["kind"] is None


def test_review_drafts_setting_round_trips(client):
    meta = client.get("/api/novel-meta").json()
    assert meta["review_drafts"] is True  # default, also for files written before plan 019
    meta["review_drafts"] = False
    client.put("/api/novel-meta", json={"meta": meta})
    assert client.get("/api/novel-meta").json()["review_drafts"] is False


def test_review_draft_then_approve_end_to_end(client, data_dir):
    r = client.post("/api/generate-chapter", json={"plot": "zz end to end", "review": True})
    assert r.status_code == 200 and not (data_dir / "chapters" / "001.json").exists()
    approved = client.post("/api/draft/approve", json={})
    assert approved.status_code == 200 and approved.json()["chapter"]["plot_input"] == "zz end to end"
    assert [c["chapter_number"] for c in client.get("/api/chapters").json()] == [1]
    assert client.get("/api/draft").json() is None
