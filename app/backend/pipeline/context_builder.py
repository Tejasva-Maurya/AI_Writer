"""
Context Builder — assembles the master prompt for the writer agent.
Implements tiered chapter memory and smart context selection.
"""
from typing import List, Dict, Optional
from models import Character, Scene, WorldSettings, Chapter


def _world_brief(world: WorldSettings) -> str:
    lines = []
    if world.world_name:
        lines.append(f"World: {world.world_name}")
    if world.genre_tags:
        lines.append(f"Genre: {', '.join(world.genre_tags)}")
    if world.cultivation_system:
        lines.append(f"Cultivation System: {world.cultivation_system}")
    if world.magic_system:
        lines.append(f"Magic System: {world.magic_system}")
    if world.hierarchy_levels:
        lines.append(f"Hierarchy (low→high): {', '.join(world.hierarchy_levels)}")
    if world.professions:
        lines.append(f"Professions: {', '.join(world.professions)}")
    if world.factions:
        lines.append(f"Factions: {', '.join(world.factions)}")
    if world.rules_of_the_world:
        lines.append(f"World Rules: {world.rules_of_the_world}")
    if world.lore_notes:
        lines.append(f"Lore Notes: {world.lore_notes}")
    return "\n".join(lines)


def _char_full(char: Character) -> str:
    parts = [f"NAME: {char.name}"]
    if char.age:
        parts.append(f"Age: {char.age}")
    if char.cultivation_level:
        parts.append(f"Level: {char.cultivation_level}")
    if char.appearance:
        parts.append(f"Appearance: {char.appearance}")
    if char.personality:
        parts.append(f"Personality: {char.personality}")
    if char.speech_style:
        parts.append(f"Speech: {char.speech_style}")
    if char.abilities:
        parts.append(f"Abilities: {', '.join(char.abilities)}")
    if char.habits:
        parts.append(f"Habits: {', '.join(char.habits)}")
    if char.backstory:
        parts.append(f"Backstory: {char.backstory}")
    if char.relationships:
        rel_str = "; ".join(f"{k}: {v}" for k, v in char.relationships.items())
        parts.append(f"Relationships: {rel_str}")
    if char.arc_notes:
        parts.append(f"Current Arc: {char.arc_notes}")
    return "\n".join(parts)


def _char_compressed(char: Character) -> str:
    return f"{char.name} ({char.type.value}): {char.micro_summary or char.personality[:80]}"


def _scene_full(scene: Scene) -> str:
    parts = [f"LOCATION: {scene.name}"]
    if scene.scene_type:
        parts.append(f"Type: {scene.scene_type}")
    if scene.description:
        parts.append(f"Description: {scene.description}")
    if scene.atmosphere:
        parts.append(f"Atmosphere: {scene.atmosphere}")
    if scene.textures:
        parts.append(f"Textures/Sensory: {scene.textures}")
    if scene.significance:
        parts.append(f"Significance: {scene.significance}")
    if scene.known_inhabitants:
        parts.append(f"Inhabitants: {', '.join(scene.known_inhabitants)}")
    return "\n".join(parts)


def _chapter_summary(chapter: Chapter, tier: str) -> str:
    ch_label = f"Chapter {chapter.chapter_number}"
    if chapter.title:
        ch_label += f" — {chapter.title}"
    if tier == "full_text":
        # Last ~400 words of full text
        words = chapter.full_text.split()
        text = " ".join(words[-400:]) if len(words) > 400 else chapter.full_text
        return f"{ch_label} (recent ending):\n{text}"
    elif tier == "full":
        return f"{ch_label}:\n{chapter.full_summary or chapter.short_summary or chapter.micro_summary}"
    elif tier == "short":
        return f"{ch_label}: {chapter.short_summary or chapter.micro_summary}"
    else:  # micro
        return f"{ch_label}: {chapter.micro_summary}"


def build_master_prompt(
    world: WorldSettings,
    characters: Dict[str, Character],
    scenes: Dict[str, Scene],
    chapters: List[Chapter],
    character_detail: Dict[str, str],  # slug → full|compressed|skip
    scene_detail: Dict[str, str],      # slug → full|skip
    chapter_tiers: Dict[str, str]      # str(chapter_num) → tier
) -> str:
    sections = []

    # World Section
    world_text = _world_brief(world)
    if world_text.strip():
        sections.append(f"=== WORLD SETTINGS ===\n{world_text}")

    # Characters
    full_chars, compressed_chars = [], []
    for slug, detail in character_detail.items():
        if slug in characters:
            char = characters[slug]
            if detail == "full":
                full_chars.append(_char_full(char))
            elif detail == "compressed":
                compressed_chars.append(_char_compressed(char))

    if full_chars:
        sections.append("=== PRIMARY CHARACTERS ===\n" + "\n\n".join(full_chars))
    if compressed_chars:
        sections.append("=== SECONDARY CHARACTERS ===\n" + "\n".join(compressed_chars))

    # Scenes
    full_scenes = []
    for slug, detail in scene_detail.items():
        if slug in scenes and detail == "full":
            full_scenes.append(_scene_full(scenes[slug]))

    if full_scenes:
        sections.append("=== LOCATIONS ===\n" + "\n\n".join(full_scenes))

    # Chapter History
    if chapters:
        history_parts = []
        for chapter in sorted(chapters, key=lambda c: c.chapter_number):
            tier = chapter_tiers.get(str(chapter.chapter_number), "micro")
            history_parts.append(_chapter_summary(chapter, tier))
        if history_parts:
            sections.append("=== STORY SO FAR ===\n" + "\n\n".join(history_parts))

    return "\n\n".join(sections)
