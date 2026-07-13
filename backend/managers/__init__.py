# managers package — expose all sub-managers via relative imports
from . import character_manager, scene_manager, world_manager, chapter_manager, novel_meta_manager

__all__ = [
    "character_manager",
    "scene_manager",
    "world_manager",
    "chapter_manager",
    "novel_meta_manager",
]
