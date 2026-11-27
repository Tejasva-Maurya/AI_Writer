"""Older versions of a regenerated chapter (plan 025, D-020): approving a regeneration keeps the text it replaces, the
newest 5 per chapter, which can be read, restored and deleted through /api/chapters/{n}/versions."""
import json

import pytest

import main
from managers import chapter_manager, draft_manager, version_manager
from models import Chapter, Draft


def _seed(n, text, title=None):
    chapter_manager.save_chapter(Chapter(chapter_number=n, title=title or f"Zz Title {n}", plot_input="zz",
                                         full_text=text, word_count=len(text.split())))


def _approve(client, n, text):
    draft_manager.save(Draft(chapter_number=n, plot_input="zz again", full_text=text))
    r = client.post("/api/draft/approve", json={})
    assert r.status_code == 200, r.text


def _versions(client, n=1):
    r = client.get(f"/api/chapters/{n}/versions")
    assert r.status_code == 200
    return r.json()


def _text(client, version_id, n=1):
    return client.get(f"/api/chapters/{n}/versions/{version_id}").json()["full_text"]


# ── Keeping the replaced text ──────────────────────────────────
def test_approving_a_regeneration_keeps_the_old_text(client):
    _seed(1, "Zz old text.", "Zz Old")
    _approve(client, 1, "Zz new text.")
    assert chapter_manager.get_chapter(1).full_text == "Zz new text."
    [listed] = _versions(client)
    assert (listed["chapter_number"], listed["title"], listed["full_text"]) == (1, "Zz Old", "")  # the list has no text
    assert listed["replaced_at"] and version_manager.is_valid_id(listed["version_id"])
    full = client.get(f"/api/chapters/1/versions/{listed['version_id']}").json()
    assert (full["full_text"], full["word_count"]) == ("Zz old text.", 3)


def test_one_click_regeneration_through_the_api_keeps_the_old_text(client, fake_ollama):
    _seed(1, "Zz old text.")
    fake_ollama.chunks = ["Zz brand new text."]
    assert client.post("/api/generate-chapter", json={"plot": "zz", "chapter_number": 1}).status_code == 200
    assert chapter_manager.get_chapter(1).full_text == "Zz brand new text."
    [listed] = _versions(client)
    assert _text(client, listed["version_id"]) == "Zz old text."


def test_a_new_chapter_or_the_same_text_keeps_no_version(client):
    _approve(client, 1, "Zz first text.")  # chapter 1 is new: nothing replaced
    _approve(client, 1, "Zz first text.")  # the same text again (a retry): nothing to keep
    assert _versions(client) == []


def test_only_the_newest_five_are_kept(client):
    _seed(1, "Zz text 0.")
    for i in range(1, 7):
        _approve(client, 1, f"Zz text {i}.")
    ids = [v["version_id"] for v in _versions(client)]
    assert len(ids) == version_manager.KEEP == 5
    assert ids == sorted(ids, reverse=True)  # newest first
    assert [_text(client, i) for i in ids] == [f"Zz text {i}." for i in (5, 4, 3, 2, 1)]  # text 0 was the oldest


# ── Delete ─────────────────────────────────────────────────────
def test_delete_a_version(client):
    _seed(1, "Zz old.")
    _approve(client, 1, "Zz new.")
    [listed] = _versions(client)
    url = f"/api/chapters/1/versions/{listed['version_id']}"
    assert client.delete(url).json() == {"success": True}
    assert client.delete(url).status_code == 404
    assert client.get(url).status_code == 404
    assert _versions(client) == []
    assert chapter_manager.get_chapter(1).full_text == "Zz new."  # the chapter itself is untouched


@pytest.mark.parametrize("version_id", ["20261127-120000-000000", "zz", "2026-11-27", "20261127-120000-000000.json"])
def test_unknown_or_invalid_version_is_404(client, version_id):
    _seed(1, "Zz text.")
    assert client.get(f"/api/chapters/1/versions/{version_id}").status_code == 404
    assert client.delete(f"/api/chapters/1/versions/{version_id}").status_code == 404
    assert client.post(f"/api/chapters/1/versions/{version_id}/restore").status_code == 404


def test_chapter_number_below_one_has_no_versions(client):
    assert _versions(client, 0) == []
    assert client.get("/api/chapters/0/versions/20261127-120000-000000").status_code == 404


# ── Restore ────────────────────────────────────────────────────
def test_restore_swaps_the_texts(client, data_dir):
    _seed(1, "Zz old.", "Zz Old")
    _approve(client, 1, "Zz new.")
    [old] = _versions(client)
    r = client.post(f"/api/chapters/1/versions/{old['version_id']}/restore")
    assert r.status_code == 200
    body = r.json()
    assert (body["chapter"]["full_text"], body["chapter"]["title"]) == ("Zz old.", "Zz Old")
    saved = json.loads((data_dir / "chapters" / "001.json").read_text(encoding="utf-8"))
    assert saved["full_text"] == "Zz old." and set(saved) == set(Chapter.model_fields)  # a plain chapter again
    [kept] = _versions(client)
    assert kept["version_id"] == body["kept_version"] != old["version_id"]
    assert _text(client, kept["version_id"]) == "Zz new."  # the replaced text is kept too


def test_restoring_the_oldest_of_five_loses_nothing(client):
    _seed(1, "Zz text 0.")
    for i in range(1, 6):
        _approve(client, 1, f"Zz text {i}.")  # versions 4..0, chapter = text 5
    oldest = _versions(client)[-1]
    assert _text(client, oldest["version_id"]) == "Zz text 0."
    assert client.post(f"/api/chapters/1/versions/{oldest['version_id']}/restore").status_code == 200
    assert chapter_manager.get_chapter(1).full_text == "Zz text 0."
    assert sorted(_text(client, v["version_id"]) for v in _versions(client)) == [f"Zz text {i}." for i in range(1, 6)]


def test_restore_waits_for_a_running_job(client):
    _seed(1, "Zz old.")
    _approve(client, 1, "Zz new.")
    [old] = _versions(client)
    main._job["kind"] = "approve"
    try:
        r = client.post(f"/api/chapters/1/versions/{old['version_id']}/restore")
    finally:
        main._job["kind"] = None
    assert r.status_code == 409
    assert chapter_manager.get_chapter(1).full_text == "Zz new." and len(_versions(client)) == 1


# ── Safety ─────────────────────────────────────────────────────
def test_a_failed_archive_keeps_the_draft_and_the_chapter(client, monkeypatch):
    _seed(1, "Zz old.")

    def disk_full(chapter, prune_old=True):
        raise OSError("disk full")

    monkeypatch.setattr(version_manager, "archive", disk_full)
    draft_manager.save(Draft(chapter_number=1, plot_input="zz", full_text="Zz new."))
    r = client.post("/api/draft/approve", json={})
    assert r.status_code == 500 and "draft is kept" in r.json()["detail"]
    assert chapter_manager.get_chapter(1).full_text == "Zz old."  # never overwritten without its copy
    assert draft_manager.load().full_text == "Zz new."
