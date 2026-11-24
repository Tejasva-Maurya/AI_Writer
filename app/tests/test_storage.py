"""Atomic writes and logged skips in the managers (KI-026)."""
import json
import logging

import pytest

from managers import chapter_manager, character_manager, novel_meta_manager, storage
from models import Chapter, Character, NovelMeta


def test_save_writes_json_and_leaves_no_temp_file(data_dir):
    character_manager.save(Character(name="Elder Wu", slug="elder_wu", age=70))
    folder = data_dir / "characters"
    assert [p.name for p in folder.iterdir()] == ["elder_wu.json"]
    assert json.loads((folder / "elder_wu.json").read_text(encoding="utf-8"))["age"] == "70"


def test_bytes_match_the_previous_writer(data_dir):
    """Same file content as the old open(path, "w") + json.dump, so existing files diff cleanly."""
    meta = NovelMeta(title="林凡传奇", genre="xianxia")
    novel_meta_manager.save(meta)
    legacy = data_dir / "legacy.json"
    with open(legacy, "w", encoding="utf-8") as f:
        json.dump(meta.model_dump(), f, indent=2, ensure_ascii=False)
    assert (data_dir / "novel_meta.json").read_bytes() == legacy.read_bytes()


def test_failure_before_the_move_keeps_the_old_file(data_dir, monkeypatch):
    """A crash or full disk mid-save used to truncate the file; now the old version survives."""
    character_manager.save(Character(name="Elder Wu", slug="elder_wu", age=70))
    path = data_dir / "characters" / "elder_wu.json"
    before = path.read_bytes()

    def disk_full(*args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(storage.os, "replace", disk_full)
    with pytest.raises(OSError):
        character_manager.save(Character(name="Elder Wu", slug="elder_wu", age=71))
    assert path.read_bytes() == before
    assert [p.name for p in path.parent.iterdir()] == ["elder_wu.json"]  # temp file removed


def test_create_never_replaces(data_dir):
    character_manager.create(Character(name="Elder Wu", slug="elder_wu", age=70))
    with pytest.raises(FileExistsError, match="already exists"):
        character_manager.create(Character(name="Elder Wu", slug="elder_wu", age=99))
    with pytest.raises(FileExistsError, match="already exists"):  # equivalent slug (KI-009)
        character_manager.create(Character(name="Elder-Wu", slug="Elder-Wu"))
    assert character_manager.get_by_slug("elder_wu").age == "70"
    assert [p.name for p in (data_dir / "characters").iterdir()] == ["elder_wu.json"]


def test_exclusive_write_without_hard_links_still_never_replaces(data_dir, monkeypatch):
    def no_hard_links(*args, **kwargs):
        raise OSError("hard links not supported")

    monkeypatch.setattr(storage.os, "link", no_hard_links)
    path = data_dir / "x.json"
    storage.write_json(path, {"v": 1}, exclusive=True)
    with pytest.raises(FileExistsError):
        storage.write_json(path, {"v": 2}, exclusive=True)
    assert json.loads(path.read_text(encoding="utf-8")) == {"v": 1}
    assert [p.name for p in data_dir.iterdir()] == ["x.json"]


def test_unreadable_files_are_logged_not_silently_dropped(data_dir, caplog):
    character_manager.save(Character(name="Elder Wu", slug="elder_wu"))
    folder = data_dir / "characters"
    (folder / "broken.json").write_text("{not json", encoding="utf-8")
    (folder / "nameless.json").write_text('{"slug": "nameless"}', encoding="utf-8")
    (folder / ".elder_wu.abc123.tmp").write_text("{}", encoding="utf-8")  # leftover temp file: ignored

    with caplog.at_level(logging.WARNING, logger="managers.storage"):
        chars = character_manager.get_all()

    assert [c.slug for c in chars] == ["elder_wu"]
    messages = [r.getMessage() for r in caplog.records]
    assert any("characters/broken.json" in m for m in messages)
    assert any("characters/nameless.json" in m for m in messages)
    assert not any(".tmp" in m for m in messages)


def test_chapter_listing_strips_text_and_logs_bad_files(data_dir, caplog):
    chapter_manager.save_chapter(Chapter(chapter_number=1, title="One", full_text="Full text"))
    (data_dir / "chapters" / "002.json").write_text("[]", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="managers.storage"):
        listing = chapter_manager.get_all()
    assert [(c.chapter_number, c.full_text) for c in listing] == [(1, "")]
    assert chapter_manager.get_all(include_text=True)[0].full_text == "Full text"
    assert any("chapters/002.json" in r.getMessage() for r in caplog.records)
    assert chapter_manager.get_next_number() == 2
