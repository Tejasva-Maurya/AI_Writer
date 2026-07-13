"""
AI Novel Writer — FastAPI Backend
Run from AI_Writer/backend/ with: uvicorn main:app --host 127.0.0.1 --port 8000
"""
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    Character, Scene, WorldSettings, Chapter, NovelMeta,
    GenerateChapterRequest, UpdateCharacterRequest, UpdateSceneRequest,
    UpdateWorldRequest, UpdateNovelMetaRequest
)
from managers import character_manager, scene_manager, world_manager, chapter_manager, novel_meta_manager
from pipeline.chapter_pipeline import run_pipeline

app = FastAPI(title="AI Novel Writer", version="1.0.0")

# CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Frontend not found</h1>")


@app.get("/style.css")
async def serve_css():
    return FileResponse(str(FRONTEND_DIR / "style.css"))


@app.get("/app.js")
async def serve_js():
    return FileResponse(str(FRONTEND_DIR / "app.js"))


# ── CHARACTERS ────────────────────────────────────────────────
@app.get("/api/characters", response_model=List[Character])
async def get_characters():
    return character_manager.get_all()


@app.post("/api/characters", response_model=Character)
async def create_character(req: UpdateCharacterRequest):
    char = req.character
    if not char.slug:
        char.slug = character_manager.make_slug(char.name)
    character_manager.save(char)
    return char


@app.put("/api/characters/{slug}", response_model=Character)
async def update_character(slug: str, req: UpdateCharacterRequest):
    existing = character_manager.get_by_slug(slug)
    if not existing:
        raise HTTPException(404, f"Character '{slug}' not found")
    char = req.character
    char.slug = slug
    character_manager.save(char)
    return char


@app.delete("/api/characters/{slug}")
async def delete_character(slug: str):
    if not character_manager.delete(slug):
        raise HTTPException(404, f"Character '{slug}' not found")
    return {"success": True}


# ── SCENES ────────────────────────────────────────────────────
@app.get("/api/scenes", response_model=List[Scene])
async def get_scenes():
    return scene_manager.get_all()


@app.post("/api/scenes", response_model=Scene)
async def create_scene(req: UpdateSceneRequest):
    scene = req.scene
    if not scene.slug:
        scene.slug = scene_manager.make_slug(scene.name)
    scene_manager.save(scene)
    return scene


@app.put("/api/scenes/{slug}", response_model=Scene)
async def update_scene(slug: str, req: UpdateSceneRequest):
    existing = scene_manager.get_by_slug(slug)
    if not existing:
        raise HTTPException(404, f"Scene '{slug}' not found")
    scene = req.scene
    scene.slug = slug
    scene_manager.save(scene)
    return scene


@app.delete("/api/scenes/{slug}")
async def delete_scene(slug: str):
    if not scene_manager.delete(slug):
        raise HTTPException(404, f"Scene '{slug}' not found")
    return {"success": True}


# ── WORLD SETTINGS ────────────────────────────────────────────
@app.get("/api/world", response_model=WorldSettings)
async def get_world():
    return world_manager.load()


@app.put("/api/world", response_model=WorldSettings)
async def update_world(req: UpdateWorldRequest):
    world_manager.save(req.settings)
    return req.settings


# ── CHAPTERS ──────────────────────────────────────────────────
@app.get("/api/chapters")
async def list_chapters():
    chapters = chapter_manager.get_all(include_text=False)
    return chapters


@app.get("/api/chapters/{number}", response_model=Chapter)
async def get_chapter(number: int):
    chapter = chapter_manager.get_chapter(number)
    if not chapter:
        raise HTTPException(404, f"Chapter {number} not found")
    return chapter


# ── GENERATE CHAPTER (SSE) ────────────────────────────────────
@app.post("/api/generate-chapter")
async def generate_chapter(req: GenerateChapterRequest):
    meta = novel_meta_manager.load()
    chapter_number = req.chapter_number or chapter_manager.get_next_number()

    async def event_stream():
        async for sse_event in run_pipeline(req.plot, chapter_number, meta):
            yield sse_event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ── NOVEL META ────────────────────────────────────────────────
@app.get("/api/novel-meta", response_model=NovelMeta)
async def get_novel_meta():
    return novel_meta_manager.load()


@app.put("/api/novel-meta", response_model=NovelMeta)
async def update_novel_meta(req: UpdateNovelMetaRequest):
    novel_meta_manager.save(req.meta)
    return req.meta


# ── EXPORT ────────────────────────────────────────────────────
@app.get("/api/export/{fmt}")
async def export_novel(fmt: str):
    if fmt not in ("txt", "md"):
        raise HTTPException(400, "Format must be 'txt' or 'md'")
    chapters = chapter_manager.get_all(include_text=True)
    meta = novel_meta_manager.load()
    lines = []
    if fmt == "md":
        lines.append(f"# {meta.title}\n")
    else:
        lines.append(f"{meta.title}\n{'=' * len(meta.title)}\n")
    for ch in sorted(chapters, key=lambda c: c.chapter_number):
        if fmt == "md":
            lines.append(f"## Chapter {ch.chapter_number}: {ch.title}\n")
        else:
            lines.append(f"\nChapter {ch.chapter_number}: {ch.title}\n" + "-" * 40 + "\n")
        lines.append(ch.full_text + "\n")
    content = "\n".join(lines)
    filename = f"{meta.title.replace(' ', '_')}.{fmt}"
    # Write to data dir and serve
    tmp = Path(__file__).parent.parent / "data" / filename
    tmp.write_text(content, encoding="utf-8")
    return FileResponse(str(tmp), filename=filename)


# ── HEALTH ────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── OLLAMA MODEL MANAGEMENT ───────────────────────────────────
RECOMMENDED_MODELS = [
    {"name": "gemma3:12b",       "size": "~7 GB",   "quality": "Best",  "note": "Recommended writer"},
    {"name": "llama3.1:8b",     "size": "~5 GB",   "quality": "Great", "note": "Fast, good quality"},
    {"name": "mistral-nemo:12b","size": "~7 GB",   "quality": "Great", "note": "Stable, no repetition"},
    {"name": "phi4-mini:3.8b",  "size": "~2.3 GB", "quality": "Good",  "note": "Specialist + low-end writer"},
    {"name": "qwen2.5:7b",      "size": "~4.7 GB", "quality": "Great", "note": "Creative writing"},
    {"name": "deepseek-r1:7b",  "size": "~4.7 GB", "quality": "Good",  "note": "Strong reasoning"},
]

@app.get("/api/models")
async def get_models():
    """Fetch installed Ollama models and return with recommendations."""
    installed = []
    ollama_error = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                installed = [m["name"] for m in data.get("models", [])]
    except Exception as e:
        ollama_error = f"Cannot reach Ollama: {e}"

    # Annotate recommended models with installed status
    recommended = []
    for rec in RECOMMENDED_MODELS:
        rec_copy = dict(rec)
        rec_copy["installed"] = any(
            inst == rec["name"] or inst.startswith(rec["name"].split(":")[0] + ":")
            for inst in installed
        )
        recommended.append(rec_copy)

    return {
        "installed": installed,
        "recommended": recommended,
        "ollama_running": ollama_error is None,
        "ollama_error": ollama_error
    }


@app.post("/api/models/pull")
async def pull_model(body: dict):
    """Pull a model from Ollama with SSE progress streaming."""
    model_name = body.get("model", "")
    if not model_name:
        raise HTTPException(400, "model name required")

    async def stream_pull():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    "http://localhost:11434/api/pull",
                    json={"name": model_name, "stream": True}
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.strip():
                            try:
                                progress = json.loads(line)
                                status = progress.get("status", "")
                                total = progress.get("total", 0)
                                completed = progress.get("completed", 0)
                                pct = int((completed / total) * 100) if total > 0 else 0
                                yield f"data: {json.dumps({'status': status, 'percent': pct, 'total': total, 'completed': completed})}\n\n"
                            except Exception:
                                pass
            yield f"data: {json.dumps({'status': 'success', 'model': model_name})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_pull(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── REFINEMENT ENDPOINTS (Mode: Character/Scene/World Building) ──
class RefineRequest(BaseModel):
    description: str
    name: Optional[str] = None
    existing_slug: Optional[str] = None


@app.post("/api/refine/character")
async def refine_character(req: RefineRequest):
    """Refine a rough character description into a structured profile."""
    from agents import specialist
    meta = novel_meta_manager.load()
    world = world_manager.load()
    result = specialist.refine_character(req.description, req.name, world, meta.specialist_model)
    if not result:
        raise HTTPException(500, "Failed to generate character profile")
    # Merge with existing if slug provided
    existing = None
    if req.existing_slug:
        existing = character_manager.get_by_slug(req.existing_slug)
    if existing:
        # Merge: only update non-empty fields from result
        for field, value in result.items():
            if value and field not in ("slug", "name", "first_appeared_chapter"):
                setattr(existing, field, value)
        character_manager.save(existing)
        return existing
    else:
        try:
            char = Character(**result)
            character_manager.save(char)
            return char
        except Exception as e:
            raise HTTPException(500, f"Could not create character: {e}")


@app.post("/api/refine/scene")
async def refine_scene(req: RefineRequest):
    """Refine a rough scene/location description into a structured profile."""
    from agents import specialist
    meta = novel_meta_manager.load()
    world = world_manager.load()
    result = specialist.refine_scene(req.description, req.name, world, meta.specialist_model)
    if not result:
        raise HTTPException(500, "Failed to generate scene profile")
    existing = None
    if req.existing_slug:
        existing = scene_manager.get_by_slug(req.existing_slug)
    if existing:
        for field, value in result.items():
            if value and field not in ("slug", "name", "first_appeared_chapter"):
                setattr(existing, field, value)
        scene_manager.save(existing)
        return existing
    else:
        try:
            scene = Scene(**result)
            scene_manager.save(scene)
            return scene
        except Exception as e:
            raise HTTPException(500, f"Could not create scene: {e}")


@app.post("/api/refine/world")
async def refine_world(req: RefineRequest):
    """Refine a rough world description and merge into world settings."""
    from agents import specialist
    meta = novel_meta_manager.load()
    world = world_manager.load()
    result = specialist.refine_world(req.description, world, meta.specialist_model)
    if not result:
        raise HTTPException(500, "Failed to refine world description")
    # Merge result into existing world settings
    world_dict = world.model_dump()
    for key, value in result.items():
        if key in world_dict:
            if isinstance(value, list) and isinstance(world_dict[key], list):
                # Merge lists (deduplicate)
                existing_list = world_dict[key]
                for item in value:
                    if item and item not in existing_list:
                        existing_list.append(item)
                world_dict[key] = existing_list
            elif value:  # Only overwrite if new value is non-empty
                world_dict[key] = value
    updated_world = WorldSettings(**world_dict)
    world_manager.save(updated_world)
    return updated_world


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
