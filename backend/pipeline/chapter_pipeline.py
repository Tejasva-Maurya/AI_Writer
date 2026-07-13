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

from models import Chapter, Character, Scene, NovelMeta
from managers import character_manager, scene_manager, world_manager, chapter_manager, novel_meta_manager
from agents import specialist, writer
from pipeline.context_builder import build_master_prompt


def _sse(event_type: str, **kwargs) -> str:
    """Format a Server-Sent Event string."""
    data = {"type": event_type, **kwargs}
    return f"data: {json.dumps(data)}\n\n"


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
        analysis = specialist.analyze_plot(plot, novel_meta.model_dump(), spec_model)
        tone = analysis.get("tone", "action")
        estimated_chapters = analysis.get("estimated_chapters", 1)
        entity_mentions = analysis.get("entity_mentions", {"characters": [], "locations": []})

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

        resolution = specialist.resolve_entities(entity_mentions, existing_chars, existing_scenes, spec_model)
        resolved_chars = resolution.get("characters", [])
        resolved_scenes = resolution.get("scenes", [])

        new_char_names = [c["name"] for c in resolved_chars if c.get("status") == "new"]
        new_scene_names = [s["name"] for s in resolved_scenes if s.get("status") == "new"]
        yield _sse("status", step=2, message=f"Found {len(new_char_names)} new characters, {len(new_scene_names)} new locations")

        # ── STEP 3: PROFILE NEW ENTITIES ────────────────────────────
        if new_char_names or new_scene_names:
            yield _sse("status", step=3, message=f"Creating profiles for {len(new_char_names)} new characters and {len(new_scene_names)} new locations...")
            world = world_manager.load()
            profiles = specialist.profile_new_entities(new_char_names, new_scene_names, plot, world, tone, chapter_number, spec_model)

            for char_data in profiles.get("characters", []):
                try:
                    char = Character(**char_data)
                    character_manager.save(char)
                    yield _sse("new_character", name=char.name, slug=char.slug)
                except Exception as e:
                    yield _sse("warning", message=f"Could not save character profile: {e}")

            for scene_data in profiles.get("scenes", []):
                try:
                    scene = Scene(**scene_data)
                    scene_manager.save(scene)
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
        chapters_brief = [{"chapter_number": c.chapter_number} for c in all_chapters]

        involved_chars_for_selection = [
            {"name": c.get("name"), "slug": c.get("slug"), "importance": c.get("importance", "secondary")}
            for c in resolved_chars if c.get("slug") in chars_dict
        ]
        involved_scenes_for_selection = [
            {"name": s.get("name"), "slug": s.get("slug"), "importance": s.get("importance", "background")}
            for s in resolved_scenes if s.get("slug") in scenes_dict
        ]

        # Fallback: if specialist didn't set well, use simple rules
        if involved_chars_for_selection or involved_scenes_for_selection:
            context_selection = specialist.select_context(
                involved_chars_for_selection, involved_scenes_for_selection,
                chapters_brief, plot, chapter_number, spec_model
            )
        else:
            context_selection = {"character_detail": {}, "scene_detail": {}, "chapter_tiers": {}}

        # Ensure all resolved chars/scenes have a detail level (fallback)
        char_detail = context_selection.get("character_detail", {})
        scene_detail = context_selection.get("scene_detail", {})
        for c in resolved_chars:
            slug = c.get("slug", "")
            if slug not in char_detail:
                char_detail[slug] = "full" if c.get("importance") == "primary" else "compressed"
        for s in resolved_scenes:
            slug = s.get("slug", "")
            if slug not in scene_detail:
                scene_detail[slug] = "full" if s.get("importance") == "main" else "skip"

        # Compute chapter tiers using hardcoded rules as fallback
        chapter_tiers = context_selection.get("chapter_tiers", {})
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

        # ── STEP 5: PREDICT UPDATES (releases specialist VRAM) ───────
        yield _sse("status", step=5, message="Preparing for writing... (releasing specialist model)")
        primary_chars = [c.get("slug") for c in resolved_chars if c.get("importance") == "primary"]
        main_scenes = [s.get("slug") for s in resolved_scenes if s.get("importance") == "main"]
        # This call uses keep_alive=0 — UNLOADS specialist from VRAM
        update_predictions = specialist.predict_updates(plot, primary_chars, main_scenes, spec_model)
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

        post_data = specialist.post_write_update(full_text, featured_char_profiles, [], spec_model)

        # Save chapter
        chapter = Chapter(
            chapter_number=chapter_number,
            title=post_data.get("chapter_title", f"Chapter {chapter_number}"),
            plot_input=plot,
            full_text=full_text,
            micro_summary=post_data.get("micro_summary", ""),
            short_summary=post_data.get("short_summary", ""),
            full_summary=post_data.get("full_summary", ""),
            characters_featured=primary_chars,
            scenes_featured=featured_scene_slugs,
            word_count=word_count,
            created_at=datetime.now().isoformat()
        )
        chapter_manager.save_chapter(chapter)

        # Update character profiles
        char_updates = post_data.get("character_updates", {})
        for slug, updates in char_updates.items():
            if slug in chars_dict:
                char = chars_dict[slug]
                char.last_seen_chapter = chapter_number
                if updates.get("arc_notes"):
                    char.arc_notes = updates["arc_notes"]
                if updates.get("cultivation_level"):
                    char.cultivation_level = updates["cultivation_level"]
                if updates.get("new_abilities"):
                    char.abilities = list(set(char.abilities + updates["new_abilities"]))
                if updates.get("relationship_updates"):
                    char.relationships.update(updates["relationship_updates"])
                character_manager.save(char)

        # Update last_seen for all featured chars not already updated
        for slug in primary_chars:
            if slug in chars_dict and slug not in char_updates:
                char = chars_dict[slug]
                char.last_seen_chapter = chapter_number
                character_manager.save(char)

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
