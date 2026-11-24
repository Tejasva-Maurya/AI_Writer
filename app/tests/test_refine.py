"""Build-tab refine routes: results, the one-LLM-job guard, and edits made during an AI call (plan 020, KI-042)."""
import types

import pytest

import main
from agents import specialist
from managers import character_manager, draft_manager, scene_manager, world_manager
from models import Character, Draft, Scene, WorldSettings

ROUTES = {
    "/api/refine/character": ("refine_character", {"name": "Zz Elder"}),
    "/api/refine/scene": ("refine_scene", {"name": "Zz Peak"}),
    "/api/refine/world": ("refine_world", {"factions": ["Zz Guild"]}),
}
BODY = {"description": "zz a stern old elder on a windy peak"}


# ── Results ────────────────────────────────────────────────────
def test_refine_creates_a_character_from_coerced_llm_output(client, fake_ollama, data_dir):
    fake_ollama.json_replies = [{"name": "Zz Elder Wu", "slug": "ignored", "age": 70, "type": "supporting"}]
    r = client.post("/api/refine/character", json=BODY)
    assert r.status_code == 200
    assert r.json()["slug"] == "zz_elder_wu" and r.json()["age"] == "70" and r.json()["type"] == "temporary"
    assert (data_dir / "characters" / "zz_elder_wu.json").exists()


def test_refine_merges_into_an_existing_scene(client, fake_ollama):
    scene_manager.save(Scene(name="Zz Peak", slug="zz_peak", description="Zz windy", atmosphere="Zz calm"))
    fake_ollama.json_replies = [{"name": "Other", "slug": "other", "atmosphere": "Zz stormy", "description": ""}]
    r = client.post("/api/refine/scene", json={**BODY, "existing_slug": "zz_peak"})
    assert r.status_code == 200
    peak = scene_manager.get_by_slug("zz_peak")
    assert (peak.name, peak.atmosphere, peak.description) == ("Zz Peak", "Zz stormy", "Zz windy")


def test_refine_world_appends_list_items(client, fake_ollama):
    world_manager.save(WorldSettings(world_name="Zz Realm", factions=["Zz Sect"]))
    fake_ollama.json_replies = [{"factions": "Zz Guild", "world_name": ""}]
    assert client.post("/api/refine/world", json=BODY).status_code == 200
    world = world_manager.load()
    assert world.factions == ["Zz Sect", "Zz Guild"] and world.world_name == "Zz Realm"


# ── One LLM job at a time ──────────────────────────────────────
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("busy", ["generation", "approve", "rewrite", "refine"])
def test_refine_waits_for_the_running_llm_job(client, fake_ollama, route, busy):
    if busy == "generation":
        main._generation["task"] = types.SimpleNamespace(done=lambda: False)  # a generation is "running"
    else:
        main._job["kind"] = busy
    r = client.post(route, json=BODY)
    assert r.status_code == 409 and r.json()["detail"]
    assert fake_ollama.calls == []  # the specialist was never called


@pytest.mark.parametrize("route", ROUTES)
def test_refine_holds_the_slot_while_the_specialist_works(client, monkeypatch, route):
    func, reply = ROUTES[route]
    seen = {}

    async def specialist_call(*args, **kwargs):
        seen["kind"], seen["reason"] = main._job["kind"], main._busy_reason()
        return reply

    monkeypatch.setattr(specialist, func, specialist_call)
    assert client.post(route, json=BODY).status_code == 200
    assert seen["kind"] == "refine" and "refined" in seen["reason"]  # any other LLM job would get this 409
    assert main._job["kind"] is None  # released


def test_refine_releases_the_slot_when_the_specialist_fails(client, monkeypatch):
    async def specialist_down(*args, **kwargs):
        raise ConnectionError("specialist gone")

    monkeypatch.setattr(specialist, "refine_character", specialist_down)
    with pytest.raises(ConnectionError):
        client.post("/api/refine/character", json=BODY)
    assert main._job["kind"] is None


def test_other_llm_jobs_wait_for_a_refine(client):
    draft_manager.save(Draft(chapter_number=1, plot_input="zz", full_text="Zz text."))
    main._job["kind"] = "refine"
    for path, body in [("/api/draft/approve", {}), ("/api/draft/rewrite", {"passage": "Zz", "instruction": "zz"})]:
        r = client.post(path, json=body)
        assert r.status_code == 409 and "refined" in r.json()["detail"]
    draft_manager.delete()
    r = client.post("/api/generate-chapter", json={"plot": "zz"})
    assert r.status_code == 409 and "refined" in r.json()["detail"]


# ── Edits made during an AI call are kept (KI-042) ─────────────
def test_edits_made_during_the_summary_are_kept(client, monkeypatch):
    character_manager.save(Character(name="Zz Hero", slug="zz_hero", personality="Zz calm"))
    scene_manager.save(Scene(name="Zz Peak", slug="zz_peak", description="Zz windy"))
    draft_manager.save(Draft(chapter_number=2, plot_input="zz", full_text="Zz text.",
                             characters_featured=["zz_hero"], scenes_featured=["zz_peak"]))

    async def summary_while_the_author_edits(*args, **kwargs):
        # The author saves both profiles (Edit modal or Update Existing) while the specialist works
        character_manager.save(Character(name="Zz Hero", slug="zz_hero", personality="Zz edited meanwhile"))
        scene_manager.save(Scene(name="Zz Peak", slug="zz_peak", description="Zz edited meanwhile"))
        return {"chapter_title": "Zz", "character_updates": {"zz_hero": {"arc_notes": "Zz grows"}},
                "scene_updates": {"zz_peak": {"new_significance": "Zz the duel"}}}

    monkeypatch.setattr(specialist, "post_write_update", summary_while_the_author_edits)
    assert client.post("/api/draft/approve", json={}).status_code == 200
    hero = character_manager.get_by_slug("zz_hero")
    assert (hero.personality, hero.arc_notes, hero.last_seen_chapter) == ("Zz edited meanwhile", "Zz grows", 2)
    peak = scene_manager.get_by_slug("zz_peak")
    assert (peak.description, peak.significance) == ("Zz edited meanwhile", "Zz the duel")


def test_a_profile_deleted_during_the_summary_stays_deleted(client, monkeypatch):
    character_manager.save(Character(name="Zz Hero", slug="zz_hero"))
    draft_manager.save(Draft(chapter_number=2, plot_input="zz", full_text="Zz text.", characters_featured=["zz_hero"]))

    async def summary_while_the_author_deletes(*args, **kwargs):
        character_manager.delete("zz_hero")
        return {"character_updates": {"zz_hero": {"arc_notes": "Zz grows"}}}

    monkeypatch.setattr(specialist, "post_write_update", summary_while_the_author_deletes)
    assert client.post("/api/draft/approve", json={}).status_code == 200
    assert character_manager.get_by_slug("zz_hero") is None  # not written back


def test_world_edit_made_during_a_world_refine_is_kept(client, monkeypatch):
    world_manager.save(WorldSettings(world_name="Zz Realm", factions=["Zz Sect"]))

    async def refine_while_the_author_edits(description, existing_world, model):
        world_manager.save(WorldSettings(world_name="Zz Realm", factions=["Zz Sect"], lore_notes="Zz typed meanwhile"))
        return {"factions": ["Zz Guild"]}

    monkeypatch.setattr(specialist, "refine_world", refine_while_the_author_edits)
    assert client.post("/api/refine/world", json=BODY).status_code == 200
    world = world_manager.load()
    assert world.lore_notes == "Zz typed meanwhile" and world.factions == ["Zz Sect", "Zz Guild"]
