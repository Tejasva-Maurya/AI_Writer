"""Regenerating an earlier chapter (API chapter_number with later chapters on disk): the writer's prompt keeps later
chapters out of the past, and step 7 doesn't roll the profiles back (plan 022, KI-043, KI-044)."""
import json

from managers import chapter_manager, character_manager, draft_manager, scene_manager
from models import Chapter, Character, Draft, Scene, WorldSettings
from pipeline.context_builder import build_master_prompt

LATER = "=== LATER IN THE STORY ==="


def _seed_chapters(numbers):
    for n in numbers:
        chapter_manager.save_chapter(Chapter(
            chapter_number=n, title=f"Zz Title {n}", full_text=f"Zz text of chapter {n}.",
            micro_summary=f"Zz micro {n}", short_summary=f"Zz short {n}", full_summary=f"Zz full {n}"))


def _spy_writer_prompt(monkeypatch):
    from agents import writer
    seen = {}
    original = writer.stream_chapter

    async def spy(master_prompt, plot, chapter_number, model):
        seen["prompt"] = master_prompt
        async for item in original(master_prompt, plot, chapter_number, model):
            yield item

    monkeypatch.setattr(writer, "stream_chapter", spy)
    return seen


# ── The writer's prompt (KI-043) ───────────────────────────────
def test_regenerated_chapter_sees_later_chapters_only_as_later(client, monkeypatch):
    _seed_chapters(range(1, 6))
    seen = _spy_writer_prompt(monkeypatch)
    r = client.post("/api/generate-chapter", json={"plot": "zz retell chapter 3", "chapter_number": 3, "review": True})
    assert r.status_code == 200

    prompt = seen["prompt"]
    past, _, later = prompt.partition(LATER)
    story = past.split("=== STORY SO FAR ===")[1]
    assert "Zz full 1" in story and "Zz text of chapter 2." in story  # the chapters before, tiered as before
    assert "Chapter 4" not in story and "Chapter 5" not in story  # later chapters are not "so far"
    assert "Chapter 3" not in prompt  # the old version of the chapter being rewritten is left out
    assert "do not reveal" in later and "Zz micro 4" in later and "Zz micro 5" in later


def test_a_new_chapter_gets_the_same_prompt_as_before(client, monkeypatch):
    _seed_chapters([1, 2])
    seen = _spy_writer_prompt(monkeypatch)
    assert client.post("/api/generate-chapter", json={"plot": "zz next", "review": True}).status_code == 200
    prompt = seen["prompt"]
    assert LATER not in prompt
    assert prompt.endswith("=== STORY SO FAR ===\nChapter 1 — Zz Title 1:\nZz full 1\n\n"
                           "Chapter 2 — Zz Title 2 (recent ending):\nZz text of chapter 2.")


def test_master_prompt_skip_and_later_tiers():
    chapters = [Chapter(chapter_number=n, micro_summary=f"Zz micro {n}") for n in (1, 2, 3)]
    prompt = build_master_prompt(WorldSettings(), {}, {}, chapters, {}, {}, {"1": "micro", "2": "skip", "3": "later"})
    past, _, later = prompt.partition(LATER)
    assert "Chapter 1: Zz micro 1" in past and "Zz micro 2" not in prompt
    assert "Zz micro 3" not in past and later.rstrip().endswith("Chapter 3: Zz micro 3")
    # A chapter without a tier still counts as a micro summary of the past (backward compatible)
    assert build_master_prompt(WorldSettings(), {}, {}, chapters[:1], {}, {}, {}) == \
        "=== STORY SO FAR ===\nChapter 1: Zz micro 1"


# ── Step 7 (KI-044) ────────────────────────────────────────────
def test_regenerated_earlier_chapter_does_not_roll_profiles_back(client, fake_ollama, data_dir):
    _seed_chapters(range(1, 6))
    character_manager.save(Character(
        name="Zz Hero", slug="zz_hero", arc_notes="Zz arc after chapter 5", cultivation_level="Zz Core",
        relationships={"Zz Rival": "Zz enemies by chapter 5"}, abilities=["Zz sword"], last_seen_chapter=5))
    scene_manager.save(Scene(name="Zz Peak", slug="zz_peak", significance="Zz where chapter 5 ends"))
    draft_manager.save(Draft(chapter_number=3, plot_input="zz", full_text="Zz new chapter 3 text.",
                             characters_featured=["zz_hero"], scenes_featured=["zz_peak"]))
    fake_ollama.json_replies = [{
        "chapter_title": "Zz New 3",
        "character_updates": {"zz_hero": {"arc_notes": "Zz arc in chapter 3", "cultivation_level": "Zz Qi",
                                          "new_abilities": ["Zz shield"],
                                          "relationship_updates": {"Zz Rival": "Zz friends in chapter 3"}}},
        "scene_updates": {"zz_peak": {"new_significance": "Zz chapter 3 meaning"}},
    }]
    r = client.post("/api/draft/approve", json={})
    assert r.status_code == 200

    hero = character_manager.get_by_slug("zz_hero")
    assert hero.last_seen_chapter == 5
    assert (hero.arc_notes, hero.cultivation_level, hero.relationships) == \
        ("Zz arc after chapter 5", "Zz Core", {"Zz Rival": "Zz enemies by chapter 5"})
    assert hero.abilities == ["Zz sword", "Zz shield"]  # a new ability is still added
    assert scene_manager.get_by_slug("zz_peak").significance == "Zz where chapter 5 ends"
    assert any("comes before chapter 5" in w for w in r.json()["warnings"])

    saved = json.loads((data_dir / "chapters" / "003.json").read_text(encoding="utf-8"))
    assert (saved["full_text"], saved["title"]) == ("Zz new chapter 3 text.", "Zz New 3")  # still overwritten


def test_last_seen_never_moves_backwards(client, fake_ollama):
    """A featured character without an update (the second loop in step 7) also keeps its later last_seen."""
    _seed_chapters(range(1, 6))
    character_manager.save(Character(name="Zz Side", slug="zz_side", last_seen_chapter=4))
    draft_manager.save(Draft(chapter_number=2, plot_input="zz", full_text="Zz text.", characters_featured=["zz_side"]))
    fake_ollama.json_replies = [{"chapter_title": "Zz"}]
    assert client.post("/api/draft/approve", json={}).status_code == 200
    assert character_manager.get_by_slug("zz_side").last_seen_chapter == 4
