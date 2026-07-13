"""
Specialist Agent — phi4-mini:3.8b
Handles extraction, entity resolution, profiling, context selection, and post-write updates.
All calls return structured JSON. Last call per session uses keep_alive=0 to free VRAM.
"""
import json
import re
from typing import Dict, Any, List, Optional
from models import Character, Scene, WorldSettings

try:
    import ollama
except ImportError:
    ollama = None


def _extract_json(text: str) -> Dict:
    """Robustly extract JSON from LLM output that may contain extra text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try to find JSON block in markdown
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
    # Try to find first { ... } block
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return {}


def _call(model: str, system: str, user: str, keep_alive: int = -1) -> Dict:
    """Make a single ollama call and parse JSON response."""
    if ollama is None:
        raise RuntimeError("ollama library not installed")
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        keep_alive=keep_alive,
        options={"num_ctx": 8192, "temperature": 0.1}
    )
    content = response.message.content
    return _extract_json(content)


def analyze_plot(plot: str, novel_meta: dict, model: str) -> Dict:
    system = """You are a precise JSON generator for a light novel story analyzer.
Output ONLY valid JSON with no markdown fences, no explanation, no extra text."""
    user = f"""Analyze this chapter plot and return ONLY this exact JSON:
{{
  "estimated_chapters": 1,
  "tone": "action",
  "pacing": "medium",
  "entity_mentions": {{
    "characters": [],
    "locations": []
  }},
  "key_events": [],
  "chapter_focus": "one sentence about the chapter focus"
}}

Rules:
- estimated_chapters: 1 unless plot clearly spans multiple chapters
- tone: action|dark|romantic|comedic|tense|mysterious|epic
- entity_mentions: extract ALL character names and location names mentioned
- key_events: 2-4 main plot events

Plot: {plot}"""
    return _call(model, system, user)


def resolve_entities(entity_mentions: Dict, existing_chars: List[Dict], existing_scenes: List[Dict], model: str) -> Dict:
    system = """You are a JSON database resolver for a novel management system.
Output ONLY valid JSON with no markdown, no explanation."""
    user = f"""Match entities from a story plot to an existing database.

EXISTING CHARACTERS (name, slug pairs):
{json.dumps(existing_chars, indent=2)}

EXISTING SCENES (name, slug pairs):
{json.dumps(existing_scenes, indent=2)}

ENTITIES TO RESOLVE:
Characters mentioned: {json.dumps(entity_mentions.get('characters', []))}
Locations mentioned: {json.dumps(entity_mentions.get('locations', []))}

For each entity:
- If it matches an existing entry (use fuzzy matching, ignore case and spaces): status="existing", use existing slug
- If it is new: status="new", create a snake_case slug
- importance for characters: "primary" (active participant) or "secondary" (mentioned)
- importance for scenes: "main" (primary action location) or "background" (passing mention)

Return ONLY this JSON:
{{
  "characters": [
    {{"name": "name", "slug": "slug", "status": "existing", "importance": "primary"}}
  ],
  "scenes": [
    {{"name": "name", "slug": "slug", "status": "existing", "importance": "main"}}
  ]
}}"""
    return _call(model, system, user)


def profile_new_entities(new_chars: List[str], new_scenes: List[str], plot: str, world: WorldSettings, tone: str, chapter_number: int, model: str) -> Dict:
    if not new_chars and not new_scenes:
        return {"characters": [], "scenes": []}
    world_brief = f"World: {world.world_name}. Genre: {', '.join(world.genre_tags)}. Cultivation: {world.cultivation_system}. Magic: {world.magic_system}."
    system = """You are a world-builder and character designer for a light novel.
Create detailed, consistent profiles that fit the world. Output ONLY valid JSON."""
    user = f"""Create profiles for new characters and scenes that appear in this plot.

WORLD CONTEXT: {world_brief}
CHAPTER PLOT: {plot}
STORY TONE: {tone}
FIRST APPEARED: Chapter {chapter_number}

NEW CHARACTERS TO PROFILE: {json.dumps(new_chars)}
NEW SCENES TO PROFILE: {json.dumps(new_scenes)}

Return ONLY this JSON structure:
{{
  "characters": [
    {{
      "name": "Full Name",
      "slug": "snake_case_slug",
      "type": "main",
      "age": "17",
      "appearance": "2-3 sentence description",
      "personality": "2-3 sentence description",
      "speech_style": "how they talk and communicate",
      "abilities": ["ability1"],
      "cultivation_level": "level or null",
      "backstory": "brief backstory",
      "relationships": {{}},
      "habits": ["habit1"],
      "arc_notes": "initial arc direction",
      "first_appeared_chapter": {chapter_number},
      "last_seen_chapter": {chapter_number},
      "micro_summary": "10 word summary of who they are"
    }}
  ],
  "scenes": [
    {{
      "name": "Full Scene Name",
      "slug": "snake_case_slug",
      "scene_type": "outdoor",
      "description": "3-4 sentence description",
      "atmosphere": "mood and feel",
      "textures": "visual and sensory details",
      "known_inhabitants": [],
      "significance": "why this place matters",
      "first_appeared_chapter": {chapter_number},
      "micro_summary": "10 word summary"
    }}
  ]
}}"""
    return _call(model, system, user)


def select_context(involved_chars: List[Dict], involved_scenes: List[Dict], all_chapters: List[Dict], plot: str, current_chapter: int, model: str) -> Dict:
    system = """You are a context optimization system for an AI story writer.
Decide what information to include. Output ONLY valid JSON."""
    char_list = [{"slug": c["slug"], "name": c["name"], "importance": c["importance"]} for c in involved_chars]
    scene_list = [{"slug": s["slug"], "name": s["name"], "importance": s["importance"]} for s in involved_scenes]
    chapter_nums = [c["chapter_number"] for c in all_chapters]
    user = f"""Optimize context for writing chapter {current_chapter}.

PLOT SUMMARY: {plot}

INVOLVED CHARACTERS: {json.dumps(char_list)}
INVOLVED SCENES: {json.dumps(scene_list)}
AVAILABLE CHAPTER NUMBERS: {json.dumps(chapter_nums)}

Decide detail level for each entity and summary tier for each chapter.

Rules for characters:
- importance=primary → "full"
- importance=secondary → "compressed"

Rules for scenes:
- importance=main → "full"
- importance=background → "skip"

Rules for chapter tiers (relative to current chapter {current_chapter}):
- ch = current-1 → "full_text"
- ch in [current-4, current-2] → "full"
- ch in [current-8, current-5] → "short"
- older → "micro"

Return ONLY this JSON:
{{
  "character_detail": {{
    "slug": "full|compressed|skip"
  }},
  "scene_detail": {{
    "slug": "full|skip"
  }},
  "chapter_tiers": {{
    "1": "micro"
  }}
}}"""
    return _call(model, system, user)


def predict_updates(plot: str, primary_chars: List[str], main_scenes: List[str], model: str) -> Dict:
    system = """You are a story continuity tracker. Predict what will change. Output ONLY valid JSON."""
    user = f"""Based on this plot, predict which characters and scenes will have updated information after this chapter.

PLOT: {plot}
PRIMARY CHARACTERS (slugs): {json.dumps(primary_chars)}
MAIN SCENES (slugs): {json.dumps(main_scenes)}

Return ONLY this JSON:
{{
  "characters_to_update": ["slug1"],
  "scenes_to_update": ["slug1"]
}}"""
    # keep_alive=0 to unload specialist from VRAM before writer loads
    return _call(model, system, user, keep_alive=0)


def post_write_update(chapter_text: str, char_profiles: List[Dict], scene_profiles: List[Dict], model: str) -> Dict:
    system = """You are a story summarizer and continuity tracker for a light novel.
Generate summaries and track character/scene changes. Output ONLY valid JSON."""
    chars_brief = [{"slug": c.get("slug"), "name": c.get("name"), "arc_notes": c.get("arc_notes", "")} for c in char_profiles]
    user = f"""Summarize this chapter and update character/scene records.

CHARACTER PROFILES (before this chapter):
{json.dumps(chars_brief, indent=2)}

CHAPTER TEXT (first 3000 chars):
{chapter_text[:3000]}

Return ONLY this JSON:
{{
  "chapter_title": "Suggested title",
  "micro_summary": "15-20 word summary of key event",
  "short_summary": "80-100 word summary of key events and character states",
  "full_summary": "180-220 word summary with scene details, dialogue beats, emotional arc, ending hook",
  "character_updates": {{
    "slug": {{
      "arc_notes": "updated arc notes",
      "cultivation_level": "updated level or null",
      "new_abilities": [],
      "relationship_updates": {{}}
    }}
  }},
  "scene_updates": {{
    "slug": {{
      "new_significance": ""
    }}
  }}
}}"""
    # keep_alive=0 to unload after post-write
    return _call(model, system, user, keep_alive=0)


def refine_character(description: str, name: Optional[str], world: WorldSettings, model: str) -> Dict:
    """Refine a rough character description into a structured character profile JSON."""
    world_brief = f"World: {world.world_name}. Genre: {', '.join(world.genre_tags)}. Cultivation: {world.cultivation_system}."
    system = """You are a character designer for a light novel. Given a rough, informal description of a character,
create a complete, well-structured character profile. Output ONLY valid JSON."""
    name_hint = f'Suggested name: "{name}"' if name else "Infer the character name from the description."
    user = f"""Create a complete character profile from this rough description.

{name_hint}
WORLD CONTEXT: {world_brief}

ROUGH DESCRIPTION:
{description}

Return ONLY this JSON (fill in all fields based on the description, using reasonable defaults for unspecified fields):
{{
  "name": "Full Character Name",
  "slug": "snake_case_slug",
  "type": "main",
  "age": "age as string",
  "appearance": "physical appearance details",
  "personality": "personality traits and behavior",
  "speech_style": "how they speak and communicate",
  "abilities": ["ability1", "ability2"],
  "cultivation_level": "current level or null",
  "backstory": "background and history",
  "relationships": {{}},
  "habits": ["habit1"],
  "arc_notes": "character arc direction",
  "first_appeared_chapter": 0,
  "last_seen_chapter": 0,
  "micro_summary": "one sentence who they are"
}}"""
    return _call(model, system, user)


def refine_scene(description: str, name: Optional[str], world: WorldSettings, model: str) -> Dict:
    """Refine a rough scene/location description into a structured scene profile JSON."""
    world_brief = f"World: {world.world_name}. Genre: {', '.join(world.genre_tags)}."
    system = """You are a world-builder for a light novel. Given a rough, informal description of a location,
create a complete, well-structured scene/location profile. Output ONLY valid JSON."""
    name_hint = f'Suggested name: "{name}"' if name else "Infer the location name from the description."
    user = f"""Create a complete scene/location profile from this rough description.

{name_hint}
WORLD CONTEXT: {world_brief}

ROUGH DESCRIPTION:
{description}

Return ONLY this JSON:
{{
  "name": "Full Location Name",
  "slug": "snake_case_slug",
  "scene_type": "indoor|outdoor|realm|dungeon|city|forest|mountain|etc",
  "description": "rich 3-4 sentence description",
  "atmosphere": "mood, feeling, emotional tone of the place",
  "textures": "visual and sensory details - what you see, hear, smell",
  "known_inhabitants": [],
  "significance": "why this place matters to the story",
  "first_appeared_chapter": 0,
  "micro_summary": "one sentence description"
}}"""
    return _call(model, system, user)


def refine_world(description: str, existing_world: WorldSettings, model: str) -> Dict:
    """Integrate a rough world-building description into the world settings structure."""
    current = f"""Current world: {existing_world.world_name or 'unnamed'}.
Genres: {', '.join(existing_world.genre_tags) or 'none set'}.
Cultivation: {existing_world.cultivation_system or 'none set'}.
Magic: {existing_world.magic_system or 'none set'}.
Hierarchy: {', '.join(existing_world.hierarchy_levels) or 'none set'}."""
    system = """You are a world-builder for a light novel. Given a rough description of some aspect of the world,
extract and structure the information to update the world settings. Output ONLY valid JSON."""
    user = f"""The author is describing an aspect of their story world. Extract and structure this information.

CURRENT WORLD SETTINGS:
{current}

AUTHOR'S DESCRIPTION:
{description}

Analyze what aspects of the world this description touches and return ONLY this JSON
(only include fields that the description provides info about; leave others as empty string or empty list):
{{
  "world_name": "",
  "genre_tags": [],
  "magic_system": "",
  "cultivation_system": "",
  "professions": [],
  "hierarchy_levels": [],
  "factions": [],
  "rules_of_the_world": "",
  "lore_notes": ""
}}"""
    return _call(model, system, user)
