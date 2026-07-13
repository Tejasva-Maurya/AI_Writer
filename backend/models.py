from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class CharacterType(str, Enum):
    MAIN = "main"
    TEMPORARY = "temporary"


class Character(BaseModel):
    name: str
    slug: str
    type: CharacterType = CharacterType.TEMPORARY
    age: Optional[str] = None
    appearance: str = ""
    personality: str = ""
    speech_style: str = ""
    abilities: List[str] = Field(default_factory=list)
    cultivation_level: Optional[str] = None
    backstory: str = ""
    relationships: Dict[str, str] = Field(default_factory=dict)
    habits: List[str] = Field(default_factory=list)
    arc_notes: str = ""
    first_appeared_chapter: int = 1
    last_seen_chapter: int = 1
    micro_summary: str = ""


class Scene(BaseModel):
    name: str
    slug: str
    scene_type: str = ""
    description: str = ""
    atmosphere: str = ""
    textures: str = ""
    known_inhabitants: List[str] = Field(default_factory=list)
    significance: str = ""
    first_appeared_chapter: int = 1
    micro_summary: str = ""


class WorldSettings(BaseModel):
    world_name: str = ""
    genre_tags: List[str] = Field(default_factory=list)
    magic_system: str = ""
    cultivation_system: str = ""
    professions: List[str] = Field(default_factory=list)
    hierarchy_levels: List[str] = Field(default_factory=list)
    factions: List[str] = Field(default_factory=list)
    rules_of_the_world: str = ""
    lore_notes: str = ""


class Chapter(BaseModel):
    chapter_number: int
    title: str = ""
    plot_input: str = ""
    full_text: str = ""
    micro_summary: str = ""
    short_summary: str = ""
    full_summary: str = ""
    characters_featured: List[str] = Field(default_factory=list)
    scenes_featured: List[str] = Field(default_factory=list)
    word_count: int = 0
    created_at: str = ""


class NovelMeta(BaseModel):
    title: str = "Untitled Novel"
    genre: str = ""
    author: str = ""
    total_chapters: int = 0
    writer_model: str = "gemma3:12b"
    specialist_model: str = "phi4-mini:3.8b"
    created_at: str = ""


class GenerateChapterRequest(BaseModel):
    plot: str
    chapter_number: Optional[int] = None


class UpdateCharacterRequest(BaseModel):
    character: Character


class UpdateSceneRequest(BaseModel):
    scene: Scene


class UpdateWorldRequest(BaseModel):
    settings: WorldSettings


class UpdateNovelMetaRequest(BaseModel):
    meta: NovelMeta
