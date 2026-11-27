import re
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from typing import Annotated, Optional, List, Dict
from enum import Enum


# ── Coercion of LLM output (and of files saved by older versions) ──
# The specialist model often returns the right value with the wrong type (an int age, a string for a list,
# "supporting" for the type). These helpers turn such values into valid ones instead of rejecting the whole entity
# (KI-015, KI-016). Values that are already valid pass through unchanged.

def as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (list, tuple, set)):
        return ", ".join(t for t in (as_text(x).strip() for x in v) if t)
    if isinstance(v, dict):
        return "; ".join(f"{as_text(k)}: {as_text(x)}" for k, x in v.items())
    return str(v)


def as_required_text(v):
    return v if v is None else as_text(v)  # None stays invalid: a name or slug is never invented


def as_optional_text(v) -> Optional[str]:
    if v is None or (isinstance(v, str) and v.strip().lower() in ("null", "none")):
        return None
    return as_text(v)


def as_str_list(v) -> List[str]:
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return [x if isinstance(x, str) else as_text(x) for x in v if x is not None and as_text(x).strip()]
    text = as_text(v)
    return [text] if text.strip() else []


def as_str_dict(v) -> Dict[str, str]:
    if not isinstance(v, dict):
        return {}
    return {as_text(k): as_text(x) for k, x in v.items() if as_text(k).strip()}


def as_int(v, default: int) -> int:
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str) and re.fullmatch(r"\s*-?\d+\s*", v):
        return int(v)
    return default


def as_character_type(v):
    if isinstance(v, CharacterType):
        return v
    return "main" if as_text(v).strip().lower() in ("main", "main character", "protagonist") else "temporary"


Text = Annotated[str, BeforeValidator(as_text)]
RequiredText = Annotated[str, BeforeValidator(as_required_text)]
OptionalText = Annotated[Optional[str], BeforeValidator(as_optional_text)]
StrList = Annotated[List[str], BeforeValidator(as_str_list)]
StrDict = Annotated[Dict[str, str], BeforeValidator(as_str_dict)]
ChapterNumber = Annotated[int, BeforeValidator(lambda v: as_int(v, 1))]


class CharacterType(str, Enum):
    MAIN = "main"
    TEMPORARY = "temporary"


class Character(BaseModel):
    model_config = ConfigDict(validate_assignment=True)  # setattr is validated and coerced too (KI-016)

    name: RequiredText
    slug: RequiredText
    type: Annotated[CharacterType, BeforeValidator(as_character_type)] = CharacterType.TEMPORARY
    age: OptionalText = None
    appearance: Text = ""
    personality: Text = ""
    speech_style: Text = ""
    abilities: StrList = Field(default_factory=list)
    cultivation_level: OptionalText = None
    backstory: Text = ""
    relationships: StrDict = Field(default_factory=dict)
    habits: StrList = Field(default_factory=list)
    arc_notes: Text = ""
    first_appeared_chapter: ChapterNumber = 1
    last_seen_chapter: ChapterNumber = 1
    micro_summary: Text = ""


class Scene(BaseModel):
    model_config = ConfigDict(validate_assignment=True)  # setattr is validated and coerced too (KI-016)

    name: RequiredText
    slug: RequiredText
    scene_type: Text = ""
    description: Text = ""
    atmosphere: Text = ""
    textures: Text = ""
    known_inhabitants: StrList = Field(default_factory=list)
    significance: Text = ""
    first_appeared_chapter: ChapterNumber = 1
    micro_summary: Text = ""


class WorldSettings(BaseModel):
    world_name: Text = ""
    genre_tags: StrList = Field(default_factory=list)
    magic_system: Text = ""
    cultivation_system: Text = ""
    professions: StrList = Field(default_factory=list)
    hierarchy_levels: StrList = Field(default_factory=list)
    factions: StrList = Field(default_factory=list)
    rules_of_the_world: Text = ""
    lore_notes: Text = ""


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
    review_drafts: bool = True  # the UI generates drafts to review before saving (plan 019)


class Draft(BaseModel):
    """A written chapter waiting for review: data/draft.json, one at a time (plan 019). Approving it runs step 7."""
    chapter_number: int
    plot_input: str = ""
    full_text: str = ""
    title: str = ""  # optional title from the author; empty = the specialist suggests one
    characters_featured: List[str] = Field(default_factory=list)
    scenes_featured: List[str] = Field(default_factory=list)
    new_characters: List[str] = Field(default_factory=list)  # slugs step 3 created for this draft
    new_scenes: List[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class GenerateChapterRequest(BaseModel):
    plot: str
    chapter_number: Optional[int] = Field(default=None, ge=1)  # an existing number regenerates it; < 1 → 422 (KI-045)
    review: bool = False  # True: stop after writing and keep the chapter as a draft (plan 019)
    tagged_characters: List[str] = Field(default_factory=list)  # slugs picked with @ in the plot box
    tagged_scenes: List[str] = Field(default_factory=list)


class UpdateDraftRequest(BaseModel):
    full_text: str
    title: str = ""


class RewriteRequest(BaseModel):
    # The editor's text split around the selection. Sent as text, not offsets: JS counts UTF-16 units, Python code points
    before: str = ""
    passage: str
    after: str = ""
    instruction: str


class ApproveDraftRequest(BaseModel):
    full_text: Optional[str] = None  # the final text; None keeps the saved draft text
    title: Optional[str] = None


class UpdateCharacterRequest(BaseModel):
    character: Character


class UpdateSceneRequest(BaseModel):
    scene: Scene


class UpdateWorldRequest(BaseModel):
    settings: WorldSettings


class UpdateNovelMetaRequest(BaseModel):
    meta: NovelMeta
