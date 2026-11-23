"""
Chapter Pipeline — orchestrates the full 7-step multi-agent writing process.
Emits Server-Sent Events (SSE) throughout for real-time UI updates.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Chapter, Character, Scene, NovelMeta, as_int, as_str_list, as_text
from managers import character_manager, scene_manager, world_manager, chapter_manager, novel_meta_manager
from agents import specialist, writer
from pipeline.context_builder import build_master_prompt


def _sse(event_type: str, **kwargs) -> str:
    """Format a Server-Sent Event string."""
    data = {"type": event_type, **kwargs}
    return f"data: {json.dumps(data)}\n\n"


def _canonical_entities(entries, existing, make_slug) -> list:
    """Map the specialist's step-2 matches onto real slugs (KI-009). An entry whose slug or name matches an existing
    entity (ignoring case, "-" vs "_" and punctuation) becomes "existing" with that entity's slug; anything else is
    "new" with a server-derived slug. Entries without a usable name, and repeats, are dropped."""
    known = {}
    for e in existing:
        known.setdefault(make_slug(e.name), e.slug)
    for e in existing:
        known[make_slug(e.slug)] = e.slug  # a slug match wins over a name match
    out, seen = [], set()
    for item in entries if isinstance(entries, list) else []:
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not make_slug(name):
            continue
        raw = item.get("slug") if isinstance(item.get("slug"), str) else ""
        slug = known.get(make_slug(raw)) or known.get(make_slug(name))
        entry = {**item, "slug": slug or make_slug(name), "status": "existing" if slug else "new"}
        if entry["slug"] not in seen:
            seen.add(entry["slug"])
            out.append(entry)
    return out


async def run_pipeline(plot: str, chapter_number: int, novel_meta: NovelMeta) -> AsyncGenerator[str, None]:
    """
    Full 7-step pipeline. Yields SSE-formatted strings.
    Steps:
      1. Analyze plot
      2. Resolve entities
      3. Profile new entities (conditional)
      4. Select context
      5. Predict updates
      [VRAM switch: specialist unloads, writer loads]
      6. Write chapter (streaming)
      7. Post-write: summarize + update profiles
    """
    spec_model = novel_meta.specialist_model
    write_model = novel_meta.writer_model
    full_text = ""

    try:
        # ── STEP 1: ANALYZE PLOT ──────────────────────────────────────
        yield _sse("status", step=1, message="Analyzing plot...")
        analysis = await specialist.analyze_plot(plot, spec_model)
        # The specialist's values may have the wrong type: coerce them (KI-015)
        tone = as_text(analysis.get("tone")).strip() or "action"
        estimated_chapters = as_int(analysis.get("estimated_chapters"), 1)
        mentions = analysis.get("entity_mentions")
        mentions = mentions if isinstance(mentions, dict) else {}
        entity_mentions = {"characters": as_str_list(mentions.get("characters")),
                           "locations": as_str_list(mentions.get("locations"))}

        if estimated_chapters > 1:
            yield _sse("multi_chapter", estimated=estimated_chapters,
                       message=f"Plot may span {estimated_chapters} chapters. Writing Chapter {chapter_number} now.")

        yield _sse("status", step=1, message=f"Plot analyzed. Tone: {tone}. Entities found: {len(entity_mentions.get('characters', []) + entity_mentions.get('locations', []))}")

        # ── STEP 2: ENTITY RESOLUTION ────────────────────────────────
        yield _sse("status", step=2, message="Resolving characters and scenes...")
        all_chars = character_manager.get_all()
        all_scenes = scene_manager.get_all()
        existing_chars = [{"name": c.name, "slug": c.slug} for c in all_chars]
        existing_scenes = [{"name": s.name, "slug": s.slug} for s in all_scenes]

        resolution = await specialist.resolve_entities(entity_mentions, existing_chars, existing_scenes, spec_model)
        resolved_chars = _canonical_entities(resolution.get("characters"), all_chars, character_manager.make_slug)
        resolved_scenes = _canonical_entities(resolution.get("scenes"), all_scenes, scene_manager.make_slug)

        new_char_names = [c["name"] for c in resolved_chars if c.get("status") == "new"]
        new_scene_names = [s["name"] for s in resolved_scenes if s.get("status") == "new"]
        yield _sse("status", step=2, message=f"Found {len(new_char_names)} new characters, {len(new_scene_names)} new locations")

        # ── STEP 3: PROFILE NEW ENTITIES ────────────────────────────
        if new_char_names or new_scene_names:
            yield _sse("status", step=3, message=f"Creating profiles for {len(new_char_names)} new characters and {len(new_scene_names)} new locations...")
            world = world_manager.load()
            profiles = await specialist.profile_new_entities(new_char_names, new_scene_names, plot, world, tone, chapter_number, spec_model)

            profiled_chars = profiles.get("characters")
            profiled_scenes = profiles.get("scenes")
            for char_data in profiled_chars if isinstance(profiled_chars, list) else []:
                if not isinstance(char_data, dict):
                    continue
                try:
                    char = Character(**{**char_data, "slug": character_manager.make_slug(str(char_data.get("name") or ""))})
                    character_manager.create(char)
                    yield _sse("new_character", name=char.name, slug=char.slug)
                except Exception as e:
                    yield _sse("warning", message=f"Could not save character profile: {e}")

            for scene_data in profiled_scenes if isinstance(profiled_scenes, list) else []:
                if not isinstance(scene_data, dict):
                    continue
                try:
                    scene = Scene(**{**scene_data, "slug": scene_manager.make_slug(str(scene_data.get("name") or ""))})
                    scene_manager.create(scene)
                    yield _sse("new_scene", name=scene.name, slug=scene.slug)
                except Exception as e:
                    yield _sse("warning", message=f"Could not save scene profile: {e}")
        else:
            yield _sse("status", step=3, message="No new entities to profile")

        # Reload updated data
        all_chars = character_manager.get_all()
        all_scenes = scene_manager.get_all()
        chars_dict = {c.slug: c for c in all_chars}
        scenes_dict = {s.slug: s for s in all_scenes}

        # ── STEP 4: SMART CONTEXT SELECTION ─────────────────────────
        yield _sse("status", step=4, message="Optimizing context...")
        all_chapters = chapter_manager.get_all(include_text=True)

        # Deterministic rules (no LLM call): the old select_context prompt only restated them (KI-013)
        char_detail = {}
        scene_detail = {}
        for c in resolved_chars:
            slug = c.get("slug", "")
            if slug not in char_detail:
                char_detail[slug] = "full" if c.get("importance") == "primary" else "compressed"
        for s in resolved_scenes:
            slug = s.get("slug", "")
            if slug not in scene_detail:
                scene_detail[slug] = "full" if s.get("importance") == "main" else "skip"

        # Chapter tiers by distance from the chapter being written
        chapter_tiers = {}
        for ch in all_chapters:
            n = ch.chapter_number
            key = str(n)
            if key not in chapter_tiers:
                diff = chapter_number - n
                if diff == 1:
                    chapter_tiers[key] = "full_text"
                elif 2 <= diff <= 4:
                    chapter_tiers[key] = "full"
                elif 5 <= diff <= 8:
                    chapter_tiers[key] = "short"
                else:
                    chapter_tiers[key] = "micro"

        yield _sse("status", step=4, message=f"Context optimized: {sum(1 for v in char_detail.values() if v == 'full')} full profiles, {len(chapter_tiers)} chapter summaries")

        # ── STEP 5: RELEASE SPECIALIST VRAM ───────────────────────────
        yield _sse("status", step=5, message="Preparing for writing... (releasing specialist model)")
        primary_chars = [c.get("slug") for c in resolved_chars if c.get("importance") == "primary"]
        main_scenes = [s.get("slug") for s in resolved_scenes if s.get("importance") == "main"]
        try:
            await specialist.unload(spec_model)  # explicit unload, no generation (KI-012)
        except Exception as e:
            yield _sse("warning", message=f"Could not unload the specialist model: {e}")
        yield _sse("status", step=5, message="Specialist agent released. Loading writer model...")

        # ── BUILD MASTER PROMPT ───────────────────────────────────────
        world = world_manager.load()
        master_prompt = build_master_prompt(
            world=world,
            characters=chars_dict,
            scenes=scenes_dict,
            chapters=all_chapters,
            character_detail=char_detail,
            scene_detail=scene_detail,
            chapter_tiers=chapter_tiers
        )

        # ── STEP 6: WRITE CHAPTER (streaming) ────────────────────────
        yield _sse("status", step=6, message="Writing chapter...")
        async for event_type, content in writer.stream_chapter(master_prompt, plot, chapter_number, write_model):
            if event_type == "token":
                full_text += content
                yield _sse("token", content=content)
            elif event_type == "error":
                yield _sse("error", message=f"Writer error: {content}")
                return

        word_count = len(full_text.split())
        yield _sse("status", step=6, message=f"Chapter written: {word_count} words")

        # ── STEP 7: POST-WRITE UPDATE ─────────────────────────────────
        yield _sse("status", step=7, message="Summarizing and updating character records...")
        featured_char_profiles = [chars_dict[slug].model_dump() for slug in primary_chars if slug in chars_dict]
        featured_scene_slugs = main_scenes
        featured_scene_profiles = [scenes_dict[slug].model_dump() for slug in main_scenes if slug in scenes_dict]

        post_data = await specialist.post_write_update(full_text, featured_char_profiles, featured_scene_profiles, spec_model)

        # Save chapter (summary values are coerced to text, so a wrong type can't lose the written chapter, KI-015)
        chapter = Chapter(
            chapter_number=chapter_number,
            title=as_text(post_data.get("chapter_title")).strip() or f"Chapter {chapter_number}",
            plot_input=plot,
            full_text=full_text,
            micro_summary=as_text(post_data.get("micro_summary")),
            short_summary=as_text(post_data.get("short_summary")),
            full_summary=as_text(post_data.get("full_summary")),
            characters_featured=primary_chars,
            scenes_featured=featured_scene_slugs,
            word_count=word_count,
            created_at=datetime.now().isoformat()
        )
        chapter_manager.save_chapter(chapter)

        # Update character profiles: each change is validated (and coerced) by the model before saving (KI-015/KI-016)
        char_updates = post_data.get("character_updates")
        char_updates = char_updates if isinstance(char_updates, dict) else {}
        for slug, updates in char_updates.items():
            if slug not in chars_dict:
                continue
            updates = updates if isinstance(updates, dict) else {}
            char = chars_dict[slug]
            changes = {"last_seen_chapter": chapter_number}
            if updates.get("arc_notes"):
                changes["arc_notes"] = updates["arc_notes"]
            if updates.get("cultivation_level"):
                changes["cultivation_level"] = updates["cultivation_level"]
            new_abilities = as_str_list(updates.get("new_abilities"))
            if new_abilities:
                changes["abilities"] = list(dict.fromkeys(char.abilities + new_abilities))
            if isinstance(updates.get("relationship_updates"), dict):
                changes["relationships"] = {**char.relationships, **updates["relationship_updates"]}
            try:
                updated = Character(**{**char.model_dump(), **changes})
                chars_dict[slug] = updated
                character_manager.save(updated)
            except Exception as e:
                yield _sse("warning", message=f"Could not update character '{slug}': {e}")

        # Update last_seen for all featured chars not already updated (including ones whose update was rejected)
        for slug in primary_chars:
            if slug in chars_dict and chars_dict[slug].last_seen_chapter != chapter_number:
                char = chars_dict[slug]
                char.last_seen_chapter = chapter_number
                character_manager.save(char)

        # Update featured locations (KI-013): only a non-empty text significance, only for scenes in this chapter
        scene_updates = post_data.get("scene_updates")
        for slug, updates in (scene_updates.items() if isinstance(scene_updates, dict) else []):
            significance = updates.get("new_significance") if isinstance(updates, dict) else None
            if slug in main_scenes and slug in scenes_dict and isinstance(significance, str) and significance.strip():
                scene = scenes_dict[slug]
                scene.significance = significance.strip()
                scene_manager.save(scene)

        # Update novel meta
        meta = novel_meta_manager.load()
        meta.total_chapters = max(meta.total_chapters, chapter_number)
        novel_meta_manager.save(meta)

        yield _sse("complete",
                   chapter_number=chapter_number,
                   title=chapter.title,
                   word_count=word_count,
                   characters=primary_chars,
                   scenes=featured_scene_slugs,
                   micro_summary=chapter.micro_summary)

    except Exception as e:
        import traceback
        yield _sse("error", message=f"Pipeline error: {str(e)}", detail=traceback.format_exc())
