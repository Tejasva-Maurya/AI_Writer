# 03 — Low-Level Design (LLD)

> **Applies to:** v2.0.0 + [Unreleased] (plans 019–024). **Last verified against code:** 2026-11-24 (§2.1 `GenerateChapterRequest` and §4 regenerate mode: 2026-11-27, plan 024).
> Function signatures are copied from the source. Line numbers are v1.0.0 and drift over time; search by function name.

Contents
1. [Conventions used across the codebase](#1-conventions-used-across-the-codebase)
2. [Backend modules](#2-backend-modules)
3. [LLM prompt catalogue](#3-llm-prompt-catalogue)
4. [Frontend](#4-frontend)
5. [Error-handling strategy by layer](#5-error-handling-strategy-by-layer)
6. [Dead / unused code](#6-dead--unused-code)

---

## 1. Conventions used across the codebase

| Topic | Convention |
|---|---|
| Python imports | Flat imports relative to `app/backend/` (`from models import Character`, `from managers import character_manager`). `sys.path` is patched in `main.py:19` and `chapter_pipeline.py:13`, and all data/frontend paths are built from `__file__`. The only working-directory dependency is uvicorn's module lookup: `uvicorn main:app` needs CWD = `app/backend/` (or `--app-dir app/backend`). |
| Models | Pydantic v2 `BaseModel`. Serialise with `.model_dump()`. Request bodies are **wrapper objects** (`{"character": {...}}`, `{"scene": {...}}`, `{"settings": {...}}`, `{"meta": {...}}`). |
| Persistence | One manager module per entity. Each manager owns its path helper (`_data_dir()` / `_path()`), and the path is computed from `__file__` (three levels up → repo root → `data/`). JSON is written with `indent=2, ensure_ascii=False`, UTF-8. |
| Identity | `slug` = filename stem. Characters/scenes: `data/<kind>/{slug}.json`. Chapters: `data/chapters/{number:03d}.json`. |
| Route handlers | All `async def`. Errors are raised as `HTTPException(status, detail)`. |
| Streaming | SSE strings `data: {json}\n\n` produced by async generators and wrapped in `StreamingResponse`. |
| LLM output | Specialist prompts demand JSON-only output. `_extract_json` tolerates fences and surrounding prose. |
| Frontend | Single global `state` object, `DOM` cache, `$()`/`$$()` helpers, `escHtml()` for any interpolated `innerHTML`. Code sections are separated by banner comments. |
| CSS | Design tokens in `:root` custom properties. BEM-ish kebab-case class names. State classes such as `.active`, `.step-is-active`, `.step-is-done`, `.visible`, `.editing`. |

## 2. Backend modules

### 2.1 `app/backend/models.py`

| Class | Fields (type = default) | Notes |
|---|---|---|
| `CharacterType(str, Enum)` | `MAIN="main"`, `TEMPORARY="temporary"` | Input is mapped by `as_character_type`: "main"/"main character"/"protagonist" (any case) → `main`, everything else → `temporary`. |
| `Character` | `name: str` (required), `slug: str` (**required**), `type: CharacterType = TEMPORARY`, `age: Optional[str]=None`, `appearance=""`, `personality=""`, `speech_style=""`, `abilities: List[str]=[]`, `cultivation_level: Optional[str]=None`, `backstory=""`, `relationships: Dict[str,str]={}`, `habits: List[str]=[]`, `arc_notes=""`, `first_appeared_chapter: int=1`, `last_seen_chapter: int=1`, `micro_summary=""` | Values are coerced before validation (`models.py` helpers, plan 009): text fields accept numbers, lists (`"a, b"`) and dicts (`"k: v"`), `None` → `""`; `age`/`cultivation_level` `None`/`"null"`/`"none"` → null, numbers → text; list fields accept a single string or mixed items; `relationships` values → text; chapter numbers accept numeric text, anything else → 1; `type` reading "main" (any case) → `main`, anything else → `temporary`. `name`/`slug` stay required. `validate_assignment=True`, so attribute assignment is validated too. Before plan 009, an int `age` or a `type` like `"supporting"` failed validation (KI-016). |
| `Scene` | `name` (req), `slug` (**req**), `scene_type=""`, `description=""`, `atmosphere=""`, `textures=""`, `known_inhabitants: List[str]=[]`, `significance=""`, `first_appeared_chapter: int=1`, `micro_summary=""` | Same coercion and `validate_assignment` as `Character`. |
| `WorldSettings` | `world_name=""`, `genre_tags=[]`, `magic_system=""`, `cultivation_system=""`, `professions=[]`, `hierarchy_levels=[]`, `factions=[]`, `rules_of_the_world=""`, `lore_notes=""` | All optional. Text and list fields are coerced like `Character`'s. |
| `Chapter` | `chapter_number: int` (req), `title=""`, `plot_input=""`, `full_text=""`, `micro_summary=""`, `short_summary=""`, `full_summary=""`, `characters_featured: List[str]=[]` (slugs), `scenes_featured: List[str]=[]` (slugs), `word_count: int=0`, `created_at=""` (ISO string) | |
| `NovelMeta` | `title="Untitled Novel"`, `genre=""`, `author=""`, `total_chapters: int=0`, `writer_model="gemma3:12b"`, `specialist_model="phi4-mini:3.8b"`, `created_at=""`, `review_drafts: bool=True` | `created_at` is never set by any code path. `review_drafts` (plan 019) is the UI's "Review each chapter as a draft" setting; the UI sends it as `review` with each generation. |
| `Draft` | `chapter_number: int` (req), `plot_input=""`, `full_text=""`, `title=""`, `characters_featured: List[str]=[]`, `scenes_featured: List[str]=[]`, `new_characters: List[str]=[]`, `new_scenes: List[str]=[]` (slugs step 3 created), `created_at=""`, `updated_at=""` | The chapter waiting for review, `data/draft.json` (plan 019). `title` empty = the specialist suggests one at approval. |
| `GenerateChapterRequest` | `plot: str`, `chapter_number: Optional[int]=Field(None, ge=1)`, `review: bool=False`, `tagged_characters: List[str]=[]`, `tagged_scenes: List[str]=[]` | `review` stops after step 6 with a draft; the tags are slugs picked with `@` (plan 019). An existing `chapter_number` regenerates that chapter; below 1 is a 422 (plan 024, KI-045: before, `-1` was saved as `chapters/-01.json`). |
| `UpdateDraftRequest` | `full_text: str`, `title=""` | `PUT /api/draft` (plan 019). |
| `RewriteRequest` | `before=""`, `passage: str`, `after=""`, `instruction: str` | `POST /api/draft/rewrite`. Text pieces, not offsets: JS selection offsets count UTF-16 units, Python indexes code points (plan 019). |
| `ApproveDraftRequest` | `full_text: Optional[str]=None`, `title: Optional[str]=None` | `POST /api/draft/approve`; `None` keeps the saved value (plan 019). |
| `UpdateCharacterRequest` | `character: Character` | Used for both POST and PUT. |
| `UpdateSceneRequest` | `scene: Scene` | |
| `UpdateWorldRequest` | `settings: WorldSettings` | |
| `UpdateNovelMetaRequest` | `meta: NovelMeta` | |
| `RefineRequest` *(defined in `main.py:422`)* | `description: str`, `name: Optional[str]=None`, `existing_slug: Optional[str]=None` | |

### 2.2 `app/backend/main.py`

| Symbol | Lines | Behaviour |
|---|---|---|
| `app = FastAPI(title="AI Novel Writer", version="2.0.0")` | 39 | **Version source of truth** (keep in sync with CHANGELOG). |
| `logging.basicConfig`, `log` | 36-37 | Console logging for the app's modules at INFO (plan 016, KI-025); uvicorn keeps its own loggers. `pull_model` logs each failed pull; a cancelled generation is logged at INFO. |
| `TrustedHostMiddleware` | 43 | Accepts only `Host: 127.0.0.1` or `localhost` (any port); other hosts get **400**. Blocks DNS rebinding. There is **no CORS middleware**: the UI calls `/api` on its own origin, so other websites can't call the API (KI-010, plan 007). |
| `file_exists_handler` | 46-48 | App-wide `FileExistsError` → **409** `{"detail": …}` (a manager's `create()` conflict, KI-036). |
| `FRONTEND_DIR` + `/static` mount | 51-53 | Mounts `app/frontend/` at `/static` if it exists. `index.html` loads the self-hosted fonts through it (`/static/fonts/fonts.css` and its woff2 files, plan 014). |
| `serve_index()` `GET /` | 56-61 | Reads and returns `index.html` on every request (so HTML edits need no restart). |
| `serve_css()` `GET /style.css`, `serve_js()` `GET /app.js` | 64-71 | `FileResponse`. |
| Character routes | 75-105 | `get_characters`; `create_character` (slug = `make_slug(slug or name)`, **422** if empty, **409** if taken); `update_character` (404 if missing or invalid slug, forces the path slug); `delete_character` (404 if missing or invalid slug). |
| Scene routes | 109-139 | Mirror of the character routes. |
| World routes | 143-151 | `GET` load, `PUT` save (full replace). |
| Chapter routes | 155-166 | `list_chapters` → `get_all(include_text=False)` (no `response_model`). `get_chapter(number)` → 404 if missing. |
| `_generation`, `_job`, `_CANCELLED_EVENT`, `_JOB_BUSY`, `_generation_running()`, `_busy_reason()`, `_llm_job(kind)` | after the chapter routes | Holder of the one running generation task (`{"task": None}` until the first run), the kind of LLM job running outside it (`"approve"`/`"rewrite"`, plan 019; `"refine"`, plan 020), the SSE line sent when a generation is cancelled, and the 409 message for the current job, or `None` when idle (plan 010, KI-031; one LLM job at a time since plan 019). `_llm_job(kind)` is a context manager: **409** if busy, else it claims the slot for its body and always releases it; the check and the claim have no `await` between them (plan 020). |
| `generate_chapter` | | **409** while any LLM job runs, or while a draft waits (plan 019). Otherwise runs `run_pipeline(…, review, tagged_characters, tagged_scenes)` in an `asyncio.Task` (`produce()`) that feeds an `asyncio.Queue`; the SSE response (`event_stream()`) yields from the queue and cancels the task in its `finally` (client disconnect). See 02-W3.2. |
| `cancel_generation()` `POST /api/generate-chapter/cancel` | | Sets `_cancel["by_user"] = True` (so the text written so far is discarded, plan 023), cancels the running generation task and waits up to 5 s for it to end. Returns `{"cancelled": true}`, or `{"cancelled": false}` when nothing was running. Approve and rewrite can't be cancelled. |
| `_cancel` | | `{"by_user": False}`, reset by `generate_chapter`. It passes `keep_partial_on_cancel=lambda: not _cancel["by_user"]` to `run_pipeline`, so a closed tab (the stream's own `task.cancel()`) keeps the partial chapter and an explicit Cancel doesn't (D-018). |
| Draft routes (plan 019) | `── DRAFT` section | `_require_draft()` (**404** "No draft is waiting for review"). `get_draft` → the draft or `null`. `update_draft` saves `full_text` and the stripped `title` (**409** during an approval). `delete_draft` (**409** during an approval, **404** if none). `rewrite_draft_passage` (**409** busy, **404**, **422** empty passage or instruction; `with _llm_job("rewrite")` around `writer.revise_passage`; **500** if the writer fails or returns nothing) → `{"replacement"}`. `approve_draft` (**409** busy, **404**, **422** empty text; saves the sent text and title, `with _llm_job("approve")` around `finalize_chapter`; **500** keeps the draft) → `{"chapter", "warnings"}`, warnings logged. See 02-W11. |
| Novel-meta routes | 231-239 | `GET` load, `PUT` save (full replace). |
| `_export_filename(title, fmt)` | 243-248 | Download name: spaces and Windows-forbidden characters → `_`, trailing dots/spaces dropped, `novel` if no letter or digit is left (plan 015, KI-017). |
| `export_novel(fmt)` | 251-274 | `txt`/`md` only (400 otherwise). Returns the text from memory (`Response`, `Content-Disposition: attachment` built like `FileResponse`'s); writes nothing to disk (plan 015, KI-017; before, it wrote into `data/`). |
| `health()` | 278-280 | `{"status":"ok","timestamp": ISO}`. |
| `RECOMMENDED_MODELS` | 284-291 | 6 entries: `gemma3:12b`, `llama3.1:8b`, `mistral-nemo:12b`, `phi4-mini:3.8b`, `qwen2.5:7b`, `deepseek-r1:7b`, each with `size/quality/note`. |
| `_model_key(name)` | 294-296 | Compare key for model names: adds `:latest` when the last path segment has no tag (a registry host's `:port` is not a tag), as Ollama does (plan 012, KI-020). |
| `_ollama_base_url(host)`, `OLLAMA_BASE_URL` | 299-320, 323 | `OLLAMA_HOST` → base URL, a port of ollama-python's `_parse_host` (default `http://127.0.0.1:11434`), read once at startup, so the model list and pull reach the same server as generation (plan 015, KI-033). |
| `get_models()` | 326-353 | `httpx` GET `{OLLAMA_BASE_URL}/api/tags` (5 s); `ollama_error` names the address. Returns `{installed[], recommended[] (+installed flag), ollama_running, ollama_error}`. A recommended model is `installed` only if its `_model_key` equals one of the installed models' keys: an exact match, not the family prefix (plan 012, KI-020). |
| `pull_model(body: dict)` | 356-418 | Untyped body. `model` is required (400). Streams `{OLLAMA_BASE_URL}/api/pull` progress as SSE. Ends with `success` only after Ollama's own `success` line; a non-200 status, an `{"error": …}` line or a missing confirmation ends with `error` (plan 010, KI-019). |
| `RefineRequest` | 422-425 | Request body of the three refine routes. |
| `refine_character` / `refine_scene` | | See 02-W4. Lazy `from agents import specialist`. The specialist call runs `with _llm_job("refine")` (**409** while another LLM job runs, plan 020). The existing profile is read after the call. Create derives the slug from the profile name (never the LLM's slug), **422** if empty, **409** if taken. |
| `refine_world` | | See 02-W5. Same job guard; merges into the world re-read after the call (KI-042, plan 020). |
| `__main__` | 530-532 | `uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)`. |

### 2.3 `app/backend/managers/*`

All six managers follow the same pattern. Directories are created lazily by `ensure_dir()` (characters, scenes, chapters) or by `storage.write_json` (for world/meta/draft). Every write and every listing goes through `managers/storage.py` (plan 016, KI-026).

| Module | Functions | Details |
|---|---|---|
| `character_manager` | `get_all() -> List[Character]` (sorted by `name`; unreadable or invalid files are skipped **and logged**, via `storage.read_all`), `is_valid_slug(slug)` (`[\w-]+`: letters/digits of any script, `_`, `-`; never `.`, `/`, `\` or empty, KI-010), `_path(slug)` (raises `ValueError` for an invalid slug; every file access goes through it), `get_by_slug(slug) -> Optional[Character]` (`None` for an invalid slug), `save(char)` (upsert: always overwrites; used by PUT, refine merge, step 7), `create(char)` (refuses a slug equivalent to an existing file stem, i.e. same `_slugify` result, so `elder-wu` blocks `elder_wu`; then an atomic exclusive write, `storage.write_json(exclusive=True)`: never overwrites, raises `FileExistsError("Character '<existing stem>' already exists")`; used by POST, refine create, step 3), `delete(slug) -> bool` (`False` for an invalid slug), `make_slug(name)` (the unused `get_as_dict` was removed in plan 021) | `_slugify`: lowercase → strip → remove `[^\w\s-]` → collapse `[\s_-]+` to `_` → strip `_`. Example: `"Xiao Fan"` → `xiao_fan`. |
| `scene_manager` | identical API for `Scene` | identical `_slugify` (duplicated code). |
| `chapter_manager` | `get_chapter(number)`, `save_chapter(chapter)`, `get_all(include_text=False)` (blanks `full_text` when False; skips and logs bad files; sorted by number), `get_next_number()` (max+1, or 1). (The unused `get_recent_n` was removed in plan 021.) | Filename `f"{n:03d}.json"`. Chapters ≥ 1000 get 4-digit names, which still sort correctly because `get_all` sorts by number, not filename. |
| `world_manager` | `load() -> WorldSettings` (defaults if missing), `save(settings)` | `data/world_settings.json` |
| `novel_meta_manager` | `load() -> NovelMeta`, `save(meta)` | `data/novel_meta.json` |
| `draft_manager` | `load() -> Optional[Draft]` (`None` if missing; an unreadable or invalid file is logged and treated as no draft, so it can't block every generation), `save(draft)`, `delete() -> bool` | `data/draft.json`: one chapter waiting for review (plan 019). Written after step 6, deleted as the last action of step 7 or on discard. |
| `storage` | `write_json(path, data, *, exclusive=False)`, `read_all(folder, label, build)` | The managers' shared file helpers (plan 016, KI-026); see below. |

**Writes are atomic** (plan 016, KI-026). `write_json` serialises first (UTF-8, `indent=2`, the same bytes as before), writes a temp file `.<stem>.<random>.tmp` in the same folder, `fsync`s it, then moves it into place.
- Saves use `os.replace`. `create()` uses `os.link`, which is atomic and fails if the name is taken; on filesystems without hard links it falls back to an exclusive `open(…, "x")`.
- The temp file is always removed, so a crash or full disk mid-write leaves the old file intact.
- `read_all` loads every `*.json` and logs `WARNING Skipped unreadable <folder>/<file>: <error>` for each file it can't read or validate.
- Before plan 016, saves wrote in place (a crash left a truncated file) and `get_all()` skipped such files silently.

### 2.4 `app/backend/agents/specialist.py`

Module-level: `try: import ollama` / `except ImportError: ollama = None`. All functions except `_extract_json` are **`async def`** and must be awaited (plan 005, KI-005).

| Function | Signature | Purpose | keep_alive |
|---|---|---|---|
| `_extract_json` | `(text: str) -> Dict` | 1) `json.loads` the whole text. 2) First fenced code block (any language tag; `json` is optional in the regex, `specialist.py:28`). 3) Greedy first-`{`-to-last-`}` match. Else `{}`. Never raises. | — |
| `_call` | `async (model, system, user, keep_alive=300) -> Dict` | `await ollama.AsyncClient().chat(model, messages=[system,user], keep_alive, format="json", options={"num_ctx": 8192, "temperature": 0.1})` → `_extract_json(response.message.content)`, returned only if it is a dict, else `{}` (plan 009, KI-015). A reply without a JSON object is logged as a warning with its first 200 characters (plan 016). `format="json"` is Ollama's JSON mode (KI-016). Raises `RuntimeError("ollama Python package not installed: run pip install -r app/requirements.txt")` if `ollama` is missing. Non-blocking: other requests are served meanwhile (before plan 005 it used the sync `ollama.chat`, which froze the server, KI-005). One client per call, like the writer. | param |
| `analyze_plot` | `(plot, model)` | Step 1 (the unused `novel_meta` argument was removed in plan 008) | 300 |
| `resolve_entities` | `(entity_mentions, existing_chars, existing_scenes, model)` | Step 2 | 300 |
| `profile_new_entities` | `(new_chars, new_scenes, plot, world, tone, chapter_number, model)` | Step 3. Returns early `{"characters":[],"scenes":[]}` when both lists are empty. | 300 |
| `_chapter_excerpt` | `(text, budget=5000) -> str` | What the summariser sees (KI-014): the whole chapter if its estimated size (¼ token per ASCII char, 1 per other char, so CJK counts safely) fits `budget`; otherwise the opening (40 %) + `[… middle of the chapter omitted …]` + the ending (60 %). | — |
| `unload` | `(model) -> None` | Step 5: `AsyncClient().generate(model=model, keep_alive=0)`, Ollama's unload request (body `{model, stream:false, keep_alive:0}`, verified with ollama 0.4.0 and 0.6.3); generates nothing (KI-012) | **0** |
| `post_write_update` | `(chapter_text, char_profiles, scene_profiles, model)` | Step 7: whole chapter via `_chapter_excerpt`, character and scene briefs | **0** |
| `refine_character` | `(description, name, world, model)` | Character Build | 300 |
| `refine_scene` | `(description, name, world, model)` | Scene Build | 300 |
| `refine_world` | `(description, existing_world, model)` | World Build | 300 |

### 2.5 `app/backend/agents/writer.py`

- `WRITER_SYSTEM` (`:11-26`): "master light novel author" persona. Requirements: sensory detail, internal monologue, subtext in dialogue, pacing *tension → action → reflection → new tension*, a chapter-ending hook, show-don't-tell, anime-influenced light-novel prose, **~2000 words**, third-person limited unless the world settings say otherwise, **no chapter numbers/titles/meta-commentary**, start the narrative immediately.
- `async def stream_chapter(master_prompt, plot, chapter_number, model) -> AsyncGenerator[Tuple[str,str]]`
  - User prompt = `master_prompt` + `=== YOUR WRITING TASK ===` + chapter number + plot + instructions ("approximately 2000 words … end with a compelling hook. Begin writing now:").
  - `ollama.AsyncClient().chat(..., stream=True, keep_alive=300, options={"num_ctx": 32768, "temperature": 0.8, "top_p": 0.9})`.
  - Yields `("token", chunk.message.content)` for each non-empty chunk. Any exception → yields `("error", str(e))` once.
- `import ollama` is guarded like the specialist's (`try/except ImportError` → `ollama = None`), so the server starts without the package. `stream_chapter` then yields one `("error", "ollama Python package not installed: …")` and stops. (Unguarded in v1.0.0: KI-003, fixed in plan 005.)
- `REVISE_SYSTEM`: "master light novel editor" persona (plan 019). Rewrite one marked passage by the author's instruction; keep style, tense, point of view and names; fit between the surrounding text; output only the new passage.
- `async def revise_passage(before, passage, after, instruction, plot, model) -> str` (plan 019, `POST /api/draft/rewrite`):
  - User prompt = `CHAPTER PLOT`, `=== TEXT BEFORE THE PASSAGE ===` (the last 12,000 characters of `before`), `=== PASSAGE TO REWRITE ===`, `=== TEXT AFTER THE PASSAGE ===` (the first 6,000 characters of `after`), `=== AUTHOR'S INSTRUCTION ===`.
  - `ollama.AsyncClient().chat(..., keep_alive=300, options={"num_ctx": 32768, "temperature": 0.7, "top_p": 0.9})`, not streamed. Same context as the writer, so the chapter isn't cut by Ollama's small default context.
  - The reply is stripped and a surrounding ``` fence (with an optional language tag) is removed (`_clean_passage`).
  - Raises on failure, including `RuntimeError` when `ollama` is missing. The route turns that into a 500, so an error text never replaces chapter text.

### 2.6 `app/backend/pipeline/context_builder.py`

`build_master_prompt(world, characters, scenes, chapters, character_detail, scene_detail, chapter_tiers) -> str` joins the non-empty sections below with blank lines, in this order:

```text
=== WORLD SETTINGS ===
World: …                     (each line only if the field is non-empty)
Genre: a, b
Cultivation System: …
Magic System: …
Hierarchy (low→high): L1, L2, …
Professions: …
Factions: …
World Rules: …
Lore Notes: …

=== PRIMARY CHARACTERS ===          (character_detail == "full")
NAME: …
Age: … / Level: … / Appearance: … / Personality: … / Speech: … /
Abilities: … / Habits: … / Backstory: … / Relationships: k: v; … / Current Arc: …

=== SECONDARY CHARACTERS ===        (character_detail == "compressed")
{name} ({type}): {micro_summary or personality[:80]}

=== LOCATIONS ===                   (scene_detail == "full")
LOCATION: … / Type / Description / Atmosphere / Textures/Sensory / Significance / Inhabitants

=== STORY SO FAR ===                (chapters on disk, ascending; tier from chapter_tiers, default "micro")
Chapter n — Title (recent ending):  ← full_text tier: last 400 words
Chapter n — Title:\n{full_summary|short|micro}   ← full
Chapter n — Title: {short|micro}                   ← short
Chapter n — Title: {micro}                         ← micro
                                    (tier "skip": left out; the old version of a chapter being regenerated)

=== LATER IN THE STORY ===          (tier "later" only, i.e. an earlier chapter is regenerated; plan 022)
These chapters come after the one you are writing and are already written. Keep this chapter consistent
with them, but do not reveal, anticipate or foreshadow their events.
Chapter n — Title: {micro}
```

Without `skip`/`later` tiers (every new chapter) the prompt is exactly as before plan 022 (KI-043).

Iteration order of characters and scenes follows the insertion order of the `*_detail` dicts (LLM order first, then fallback additions).

### 2.7 `app/backend/pipeline/chapter_pipeline.py`

`_canonical_entities(entries, existing, make_slug)` (plan 007, KI-009) post-processes the step-2 result for characters and scenes: an entry whose slug or name normalises (`make_slug`) to an existing entity's slug or name becomes `existing` with that entity's **real** slug; anything else becomes `new` with `slug = make_slug(name)`. Non-dict entries, entries without a usable name, and repeats are dropped. Step 3 then saves each profile under `make_slug(profile name)`, never the LLM's slug.

`_apply_tags(resolved, tagged, existing, importance)` (plan 019) runs after `_canonical_entities`: each tagged slug that exists becomes `existing` with `importance` (`"primary"` for characters, `"main"` for scenes), added to the list if the specialist missed it; unknown or non-string slugs are logged at INFO and ignored.

- `_sse(event_type, **kwargs) -> str` → `f"data: {json.dumps({'type': event_type, **kwargs})}\n\n"`. `warning` and `error` events are also written to the server log (errors with their traceback detail; plan 016).
- `async def run_pipeline(plot, chapter_number, novel_meta, review=False, tagged_characters=None, tagged_scenes=None, keep_partial_on_cancel=None) -> AsyncGenerator[str]`. Step logic is documented in [02 §W3.3](02-workflows.md#w33-pipeline-steps-appbackendpipelinechapter_pipelinepy). After step 6 it saves a `Draft`; with `review` it then emits `draft_complete` and returns, otherwise it calls `finalize_chapter`.
  - **Step 6 stopping halfway** (plan 023):
    - On a writer `error` with text written, it saves that text as the draft (`_save_draft`) and emits `error` with `draft_saved: true`.
    - On `CancelledError` with text written, it saves the draft only if `keep_partial_on_cancel` is given and returns true, then **re-raises**. The cancel is never swallowed: a failed save is logged (`log.exception`), not raised.
    - Saving is synchronous, so it is safe while cancelling.
- `_save_draft(chapter_number, plot, full_text, primary_chars, main_scenes, created_chars, created_scenes) -> Draft` builds and saves the draft. Three places use it: after step 6, on a writer error, on a cancel that keeps the text.
- `async def finalize_chapter(draft, spec_model) -> Tuple[Chapter, List[str]]` (plan 019) is step 7 for a draft, shared by the one-click pipeline and `POST /api/draft/approve`.
  1. Reads characters and scenes from disk.
  2. Awaits `post_write_update` (its only `await`). If that raises, the draft stays (KI-041). Then it reads characters and scenes from disk **again**, so an edit or deletion saved during the call is respected (KI-042, plan 020).
  3. Saves the chapter (the draft's title wins over the suggested one) and applies the validated character, scene and meta updates. These run without pausing, so a cancel can't stop them halfway.
     - `last_seen_chapter` only moves forward (`max`).
     - When chapters after this one exist (`last_later`, an earlier chapter was regenerated), it skips arc notes, levels, relationships and scene significance, keeps adding new abilities, and returns a warning saying so (KI-044, plan 022).
  4. Deletes the draft last.
  5. Returns the chapter and the warning messages; the caller emits or logs them.
- Local data structures:
  - `resolved_chars` / `resolved_scenes`: lists of `{name, slug, status, importance}` taken from the LLM as-is.
  - `chars_dict` / `scenes_dict`: `{slug: model}` after the step-3 reload.
  - `char_detail` / `scene_detail` / `chapter_tiers`: see context_builder.
  - `primary_chars` / `main_scenes`: slug lists. They become `characters_featured` / `scenes_featured` on the chapter.
- Whole body is wrapped in `try/except Exception` → `error` event with `traceback.format_exc()`.

## 3. LLM prompt catalogue

All specialist calls use the system message "…Output ONLY valid JSON…" and a user message that embeds a literal JSON template. Expected output shapes:

| Call | Expected JSON (abridged) | Consumed fields | Enumerations requested |
|---|---|---|---|
| `analyze_plot` | `{estimated_chapters:int, tone, pacing, entity_mentions:{characters[],locations[]}, key_events[], chapter_focus}` | `tone`, `estimated_chapters`, `entity_mentions` | tone ∈ action/dark/romantic/comedic/tense/mysterious/epic |
| `resolve_entities` | `{characters:[{name,slug,status,importance}], scenes:[…]}` | all | status ∈ existing/new. Char importance ∈ primary/secondary. Scene importance ∈ main/background. Asks for **snake_case** slugs for new entities. |
| `profile_new_entities` | `{characters:[Character…], scenes:[Scene…]}` | all → `Character(**)`/`Scene(**)` (coerced; non-list / non-dict entries skipped) | The template defaults to `"type": "temporary"` with the rule "main only for a central, recurring character" and `"age": "age as text, or null"` (plan 009; before, it hard-coded `"main"` and `"17"`, KI-016). |
| `post_write_update` | `{chapter_title, micro_summary (15-20 words), short_summary (80-100), full_summary (180-220), character_updates:{slug:{arc_notes, cultivation_level, new_abilities[], relationship_updates{}}}, scene_updates:{slug:{new_significance}}}` | all (`scene_updates` only for featured scenes, non-empty text) | Prompt has `CHARACTER PROFILES` and `SCENE PROFILES` blocks and the `CHAPTER TEXT:` excerpt. |
| `refine_character` | full `Character` shape (`first_appeared_chapter: 0`, `last_seen_chapter: 0`) | all | — |
| `refine_scene` | full `Scene` shape | all | scene_type hint list |
| `refine_world` | full `WorldSettings` shape, untouched fields empty | all | — |

Prompt-engineering notes:
- Low temperature (0.1) plus explicit templates. The models used are small, so output may be partial or contain invalid enum values. Every consumer uses `.get()` with defaults.
- Every specialist call passes `format="json"` (Ollama's JSON mode, since plan 009).

Writer prompts (plain text, not JSON):
| Call | Output | Notes |
|---|---|---|
| `stream_chapter` | ~2000 words of prose, streamed | `WRITER_SYSTEM` + master prompt + writing task (§2.5) |
| `revise_passage` (plan 019) | only the replacement passage | `REVISE_SYSTEM` + plot + text before / passage / text after + instruction (§2.5). Temperature 0.7 (writer: 0.8) |

## 4. Frontend

### 4.1 Files and structure

| File | Structure |
|---|---|
| `index.html` | `<header>` (brand, inline-editable title, chapter badge, Settings, Export dropdown) → `<main class="app-layout">` with: left `<aside>` **CHARACTERS** (Main Cast / Supporting lists), center `<section>` (4 **mode tabs** + 4 mode panels, the plot panel holding the `#mention-list` listbox for @-mentions and the `#regenerate-notice` (plan 024), pipeline panel with 7 steps, output panel with **⟳ Regenerate** `#btn-regenerate-chapter` next to Full View (plan 024), the reading area `#output-body` and the draft panel `#draft-panel` (editor, rewrite row, selection hint, title, Discard, Approve; plan 019), multi-chapter notice, history bar), right `<aside>` **LOCATIONS** (+ New Location, World Settings). Six modals: `modal-character`, `modal-scene`, `modal-world`, `modal-settings` (with the **Review each chapter as a draft** checkbox), `modal-chapter` (with the **Prompt used** `<details>` and **⟳ Regenerate this chapter** `#btn-view-regenerate`, plan 024), `modal-profile`. Toast container. Script `app.js` loaded at end of body (no `defer`/module). |
| `app.js` | One global script, no modules. Sections in order: state → DOM cache → init → API helpers → loaders/renderers (meta, characters, scenes, world, chapters) → chapter view → `generateChapter` → **draft review** (plan 019) → SSE parser → pipeline UI → character modal → scene modal → world modal → settings modal → chapter view modal → export → modal system → tag input → relationship editor → title edit → toasts → `escHtml` → static bindings → keyboard shortcuts → connection check → boot → **mode switcher** → world snapshot → existing-entity dropdowns → refine (char/scene/world) → **model browser** → second `DOMContentLoaded` → **@-mentions** (plan 019). The part from "mode switcher" on was evidently appended later; it is a separate binding block. |
| `fonts/` | `fonts.css` (27 `@font-face` rules for Cinzel, Crimson Pro and JetBrains Mono, all subsets, `src` under `/static/fonts/`), the 14 woff2 files they point to, and the three SIL OFL licences. Linked first in `index.html`; served by the `/static` mount. Regeneration steps are in the `fonts.css` header (plan 014, KI-034). |
| `style.css` | Sections: fonts (a pointer to `fonts/fonts.css`; the Google `@import` was removed in plan 014), `:root` tokens, reset, scrollbar, selection, animated background orbs, glass panel, header, app layout, sidebars, cards, center panel, pipeline, output, history bar, modals, form elements, tag input, toasts, animations (16 `@keyframes`), error/loading states, utilities, mode tabs, build panels, world snapshot, model browser, responsive layout. The responsive section (plan 017, KI-035) holds the only `@media` queries, at 1200, 900 and 600 px (§4.7). |

### 4.2 Global state (`app.js:11-34`)

```js
state = {
  characters: [], scenes: [], world: {}, chapters: [], novelMeta: {},
  currentChapter: null,      // full Chapter from GET /chapters/{n} or approval, or {chapter_number,title,word_count,characters_featured,scenes_featured,plot_input} after a one-click generation
  draft: null,               // the Draft waiting for review (GET /api/draft), null when none (plan 019)
  regenerate: null,          // {chapter_number, title} while the plot box writes a new version of a saved chapter (plan 024)
  isGenerating: false,       // this tab's lock; the server also allows only one generation (409, plan 010)
  activeModal: null,         // id of the open modal overlay
  _mentions: [],             // entities picked with @ in the plot box: {kind: 'character'|'scene', slug, name} (plan 019)
  _abilities, _habits, _inhabitants, _genreTags, _professions, _hierarchy, _factions: [],  // tag-input stores
  _relationships: {},        // relationship editor store
  _editingCharSlug: null, _editingSceneSlug: null,   // null = create mode
}
// (The write-only keys _profileContext and activeMode were removed in plan 021.)
```

Constant `API = '/api'` (`app.js:6`): same origin as the page, so it works whether the UI is opened as `127.0.0.1` or `localhost`, and the server needs no CORS (KI-010/KI-021, fixed in plan 007).

### 4.3 API helpers (`app.js:120-156`)

| Helper | Returns | Error behaviour |
|---|---|---|
| `apiGet(path)` | parsed JSON | throws `GET … failed: status` |
| `apiPost(path, body)` | parsed JSON | throws with response text |
| `apiPut(path, body, options={})` | parsed JSON | throws with response text. `options.keepalive` lets the request finish while the page closes (the draft's last autosave, plan 019) |
| `apiDelete(path)` | parsed JSON | throws |

> All four helpers return parsed JSON and throw on a non-2xx status, so callers don't check `res.ok`. In v1.0.0 `apiPost` returned the raw `Response`, which caused KI-002 (fixed by plan 003). `generateChapter` and `pullModel` call `fetch` directly, because they read an SSE stream.
> Since plan 019 the thrown `Error` (built by `apiError`) also carries `status` (the HTTP status) and `detail` (the server's `detail` message when it is a string); `errorText(e)` returns `detail`, or the message, for toasts. The messages themselves are unchanged.

### 4.4 Function catalogue

| Area | Functions |
|---|---|
| Boot | `init`, `checkConnection`, `bindStaticEvents`, `bindModeTabs` |
| Loaders / renderers | `loadNovelMeta`/`renderNovelMeta`, `loadCharacters`/`renderCharacters`, `loadScenes`/`renderScenes`, `loadWorld`, `loadChapters`/`renderChapterHistory`/`updateChapterHint`/`nextChapterNumber` (highest `chapter_number` + 1, the backend's rule), `renderCardList`, `createEntityCard` |
| Chapter output | `viewChapter` (opens the Full View instead while a draft waits), `showChapterOutput`, `formatChapterText` (splits on `\n\n+`, one `<p>` per paragraph via `textContent`) |
| Draft review (plan 019) | `loadDraft` (`GET /api/draft`; opens a draft, toast if it was not shown), `showDraft`, `hideDraft`, `setDraftSaveStatus`, `setDraftBusy` (read-only editor and disabled controls while the AI works), `updateDraftCounts` (word count + selection hint), `draftBody`, `scheduleDraftSave` (1 s debounce), `saveDraftNow` (chained `PUT /api/draft`), `rewriteSelection` (`POST /api/draft/rewrite` with `before/passage/after`, `setRangeText(…, 'select')`), `undoRewrite` (stack of `{before, after}`), `discardDraft(question?)` (`DELETE /api/draft`, then offers to delete the profiles the draft created; returns whether no draft is left), `approveDraft` (`POST /api/draft/approve`), `showAwaitingApproval`, `showApprovalStep`, `draftAsChapter` (the draft for the Full View), `bindDraftEvents`, `countWords` |
| @-mentions (plan 019) | `initMentions`, `mentionCandidates(query)` (starts-with, then word-starts-with, then contains; max 8), `updateMentions` (`MENTION_RE`, Unicode-aware), `renderMentions` (escaped), `placeMentions` + `caretPosition` (mirror element), `pickMention`, `closeMentions`, `taggedEntities(plot)` (slugs still named in the plot and still existing) |
| Generation | `generateChapter` (its SSE handler map shows `warning` events as warning toasts, plan 009, KI-018; a cancelled `error` resets the steps and shows an info toast; a non-2xx response shows the server's `detail`, e.g. the 409, plan 010), `cancelGeneration` (posts `/generate-chapter/cancel`; the button is shown only while generating), `parseSSEStream` (buffered line splitting, ignores malformed lines and `[DONE]`), `resetPipeline` (also cancels the pending fade and clears the previous run's opacity and red step styles, plan 011, KI-024), `activatePipelineStep`, `completePipelineStep`, `completePipeline` (fades the panel to 0.4 opacity after 2 s; the timer id is kept in `_pipelineFadeTimer`), `updateProgress`, `setStepError` (inline red border/background on the active step), `addNewEntityTag` |
| Character | `openCharacterModal(slug?)`, `saveCharacter` (create sends `slug: ''` and the server derives it; edit sends `{...existing, ...form}` so the fields the modal doesn't show are kept), `deleteCharacter`, `viewCharacterProfile` |
| Scene | `openSceneModal(slug?)`, `saveScene` (same payload rules as `saveCharacter`), `deleteScene`, `viewSceneProfile` |
| World / settings | `openWorldModal`, `saveWorld`, `openSettingsModal` (fills the model selects from `state.novelMeta`, then `loadModels()` → `populateModelSelects` + `renderModelBrowser`), `saveSettings` (sends `{...state.novelMeta, …form}`; an empty select keeps the stored model), `renderWorldSnapshot` (⚠ unescaped `innerHTML`) |
| Chapter modal | `openChapterViewModal(ch = state.currentChapter)` (a draft or a history chapter can be passed; fills the **Prompt used** box from `plot_input`; shows **⟳ Regenerate this chapter** for a saved chapter, not for `draftAsChapter()`'s `is_draft`), `reusePrompt` (plan 019) |
| Regenerate (plan 024, W13) | `startRegeneration(n)` (prompt of saved chapter *n* into the plot box, `state.regenerate`), `stopRegeneration`, `updateRegenerateUi` (notice, Generate label, hint), `generateLabel`, `replacesSavedChapter(draft)`, `draftHeading(draft)` (the output title of a draft that replaces a saved chapter). `generateChapter` sends `chapter_number` and `review: true` in this mode; `showDraft` ends it; `approveDraft` asks before replacing a saved chapter |
| Export | `exportNovel(format)` |
| Modal system | `openModal(id)` (closes any other open modal, locks body scroll, focuses the first input), `closeModal(id)` |
| Components | `initTagInput(inputId, displayId, initialTags, stateKey)` (Enter or `,` adds a tag, Backspace on empty input removes the last; the input is cloned to drop old listeners), `renderTags`, `renderRelationships` |
| Misc | `initTitleEdit`, `showToast(message, type='info', duration=4000)` (types: success/error/info/warning), `escHtml` |
| Modes | `switchMode(mode)` (`MODES = ['plot','character','scene','world']`; toggles `hidden` on panels; world → snapshot; character/scene → fills the "Update Existing" dropdowns), `populateExistingCharDropdown`, `populateExistingSceneDropdown` |
| Refine | `refineCharacter`, `refineScene`, `refineWorld` |
| Models | `loadModels(force)` (cached in `_cachedModels`), `populateModelSelects` (⚠ unescaped), `renderModelBrowser` (⚠ unescaped; re-renders itself on Set Writer/Specialist), `pullModel` (own SSE loop; element IDs derived as `pb-/pf-/ps-` + name with `:` and `.` → `_`), `refreshModels` |

### 4.5 Event bindings & shortcuts

| Binding | Where | Action |
|---|---|---|
| `#btn-generate` click, `Ctrl+Enter` in `#plot-input` | `bindStaticEvents` | `generateChapter()` |
| `#btn-cancel-generate` click (visible only while generating) | `bindStaticEvents` | `cancelGeneration()` (plan 010) |
| Global `Alt+G` / `Alt+N` / `Alt+S` / `Alt+W` | `app.js:1443-1465` | Generate / new character / settings (loads models like the button since plan 006) / world settings. The key is lower-cased first, so they also work with Caps Lock or Shift (plan 013, KI-032). |
| `Escape` | `bindStaticEvents` | Close the active modal |
| Click on an overlay background, `.modal-close`, or `.btn-cancel[data-modal]` | delegated on `document` | Close modal |
| Click anywhere | `document` | Close the export dropdown |
| `#btn-settings` click | `bindStaticEvents` | `openSettingsModal` (which also loads the models; the old second listener was removed in plan 006) |
| `@` in `#plot-input`, then `↑`/`↓`, `Enter`/`Tab`, `Esc`, click | `initMentions` | Open, move in, insert from, close the @-mention list (plan 019). Only while the list is open; `Ctrl`/`Alt` combinations pass through, so `Ctrl+Enter` still generates |
| `Enter` in `#draft-instruction`, `#btn-draft-rewrite` | `bindDraftEvents` | `rewriteSelection()` (plan 019) |
| Typing in `#draft-editor` / `#draft-title` | `bindDraftEvents` | Autosave after 1 s; `pagehide` sends a pending change with `keepalive` |
| `#btn-draft-undo`, `#btn-draft-discard`, `#btn-draft-approve` | `bindDraftEvents` | `undoRewrite`, `discardDraft`, `approveDraft` |
| `#btn-view-full`, `#btn-reuse-prompt` | `bindStaticEvents` | Full View of the chapter or the draft; `reusePrompt` |
| `#btn-regenerate-chapter`, `#btn-view-regenerate`, `#btn-regenerate-stop` | `bindStaticEvents` | `startRegeneration` for the shown / viewed chapter; `stopRegeneration` (plan 024) |

### 4.6 Streaming paragraph algorithm (`token` handler, `app.js:491-527`)

- `streamedText` accumulates text since the last paragraph break. `currentParagraph` is the `<p>` being filled.
- A chunk **without** `\n\n` is appended to `currentParagraph.textContent` (a `<p>` is created on first use).
- A chunk **with** `\n\n` → split the accumulated `streamedText` on `\n\n`. The first part finalises the current `<p>`, middle parts become new `<p>`s, and the last part starts a new current `<p>`.
- Edge cases: a single `\n` stays inside the paragraph (rendered as a space). If the first chunk already contains `\n\n`, the handler first creates the paragraph and then splits, so that text shows at once (plan 013; before, an `if (currentParagraph)` guard held it back until a later chunk with `\n\n`, KI-032).
- The cursor element `#text-cursor` is re-appended at the end after every token, with `scrollIntoView({block:'nearest'})`.

### 4.7 Design system (CSS tokens, `style.css:7-60`)

| Token group | Values |
|---|---|
| Background / panels | `--bg #080b14`, `--panel-bg rgba(12,17,35,.85)`, `--panel-bg-solid #0c1123`, `--glass-blur blur(20px)` |
| Accents | `--purple #8a4fff` (characters / primary), `--gold #f5c842` (locations), `--mint #4fffb0` (world / success), `--error #ff4f6a`, plus `*-dim`/`*-mid` alpha variants and `--gradient-purple/gold/dark` |
| Text | `--text-primary #e8eaf6`, `--text-secondary #7c83a0`, `--text-muted #4a5178` |
| Fonts | `--font-display 'Cinzel'`, `--font-body 'Crimson Pro'`, `--font-mono 'JetBrains Mono'` |
| Layout | `--sidebar-w 280px`, `--header-h 64px`, radii `6/12/18/24px` |
| Effects | `--glow-purple/gold/mint/text`, `--transition all .3s cubic-bezier(.4,0,.2,1)` |

Layout: fixed header (64 px), then `.app-layout` as a fixed flex row filling the rest of the viewport: left sidebar (280 px), flexible center, right sidebar (280 px).

**Responsive breakpoints** (the last section of `style.css`, plan 017, KI-035; CSS only):
- **≤ 1200 px:** `--sidebar-w` becomes 230 px.
- **≤ 900 px:** `.app-layout` becomes a scrolling column. `.center-panel` gets `order: -1`, so the writer comes first, then the two sidebars at full width; `.sidebar-scroll` is capped at `40vh`. The pipeline uses 4 columns, `.form-grid-2` one, and modals are capped at `92vh`.
- **≤ 600 px:** the header text labels are hidden (icon-only buttons), the pipeline uses 2 columns, and the mode tabs and Generate row wrap.
- These rules set no `display` on elements the JS toggles with `hidden` (the KI-037 trap).

Colour semantics: **purple = characters, gold = locations, mint = world**.

## 5. Error-handling strategy by layer

| Layer | Strategy | Gaps |
|---|---|---|
| Managers | Reads of single items raise on corrupt JSON. `get_all()` skips a file it can't read and logs a warning naming it. Writes are atomic (plan 016). | A skipped file is visible only in the server console, not in the UI. |
| Specialist | Never raises on bad JSON (`{}`); raises on transport errors. | Type errors surface later in the pipeline. |
| Writer | Converts any exception into an `error` tuple. | — |
| Pipeline | Global try/except → `error` SSE with traceback. The written chapter is saved as a draft before step 7, and a step-7 failure keeps it (`error.draft_saved`, plan 019, KI-041). | Partial writes (step-3 profiles) are not rolled back; discarding a draft offers to delete them. |
| Routes | `HTTPException` 400/404/500. Pydantic 422 on invalid bodies. **409** from the app-wide `FileExistsError` handler (`file_exists_handler`, right after the `TrustedHostMiddleware` setup in `main.py`), which catches a manager's `create()` conflict, and from `generate_chapter` while another generation runs (plan 010). Since plan 019 also from generate, approve and rewrite while another LLM job runs (and the three refine routes since plan 020), from generate while a draft waits, and from draft edit/discard during an approval. Refine create maps the same error to 409 explicitly. Nothing else raises `FileExistsError` (all `mkdir` calls use `exist_ok=True`). | Refine endpoints wrap model construction but not the LLM call (transport errors → 500 with default message). |
| Frontend | try/catch around each action → toast. Loaders fall back to empty state. A cancelled generation is an info toast, not an error (plan 010). | Errors go only to toasts and `console.error`. (`warning` SSE events are shown since plan 009; the pipeline panel's fade and error styles are reset at each run since plan 011.) |

**Logging** (plan 016, KI-025): `main.py` sets up console logging at INFO.
- **Logged:** skipped data files, pipeline warnings and errors (with tracebacks), specialist replies without JSON, failed model pulls and cancelled generations.
- **Other diagnostics:** uvicorn's access log, SSE `error.detail` and the browser console.

**Tests** (plan 016): `app/tests/` (pytest) covers the API, storage, the pipeline with a fake `ollama`, the draft routes (`test_draft.py`, plan 019), the refine routes and the job guard (`test_refine.py`, plan 020), regenerating an earlier chapter (`test_regenerate.py`, plan 022; chapter numbers below 1, plan 024, KI-045), chapters stopped halfway (`test_partial.py`, plan 023: the fake stream can raise or block, `conftest.BLOCK`) and the pure helpers. The fixtures redirect every manager to a temp folder and fail the run if the real `data/` changes, including a file created and deleted again during the run (folder mtimes, plan 019). Run it with `py -m pytest app/tests`, and lint with `py -m ruff check app` (07 §7).

## 6. Dead / unused code

**None known** (checked 2026-11-26, plan 021). How it was checked:
- **Python:** every `def` in `app/backend` that is referenced only once in `app/` is a FastAPI route or the exception handler (registered by decorators).
- **Frontend:** no JS function in `app.js` is referenced only once (`app.js` + `index.html`), and every `DOM` cache key is used. No `state.<key>` is assigned without ever being read.
- **Imports:** `py -m ruff check app` (rule F401, unused imports) is clean.

Plan 021 removed what the previous inventory listed: `character_manager.get_as_dict`, `scene_manager.get_as_dict`, `chapter_manager.get_recent_n`, and the write-only `state._profileContext` and `state.activeMode`. Two old rows were not dead code at all:
- The `/static` mount serves the self-hosted fonts (plan 014).
- The listed unused imports had already been removed in plan 016.
