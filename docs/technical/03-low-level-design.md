# 03 — Low-Level Design (LLD)

> **Applies to:** v1.0.0 + [Unreleased]. **Last verified against code:** 2026-11-23.
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
| Python imports | Flat imports relative to `app/backend/` (`from models import Character`, `from managers import character_manager`). `sys.path` is patched in `main.py:14` and `chapter_pipeline.py:12`, and all data/frontend paths are built from `__file__`. The only working-directory dependency is uvicorn's module lookup: `uvicorn main:app` needs CWD = `app/backend/` (or `--app-dir app/backend`). |
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
| `NovelMeta` | `title="Untitled Novel"`, `genre=""`, `author=""`, `total_chapters: int=0`, `writer_model="gemma3:12b"`, `specialist_model="phi4-mini:3.8b"`, `created_at=""` | `created_at` is never set by any code path. |
| `GenerateChapterRequest` | `plot: str`, `chapter_number: Optional[int]=None` | |
| `UpdateCharacterRequest` | `character: Character` | Used for both POST and PUT. |
| `UpdateSceneRequest` | `scene: Scene` | |
| `UpdateWorldRequest` | `settings: WorldSettings` | |
| `UpdateNovelMetaRequest` | `meta: NovelMeta` | |
| `RefineRequest` *(defined in `main.py:372`)* | `description: str`, `name: Optional[str]=None`, `existing_slug: Optional[str]=None` | |

### 2.2 `app/backend/main.py`

| Symbol | Lines | Behaviour |
|---|---|---|
| `app = FastAPI(title="AI Novel Writer", version="1.0.0")` | 30 | **Version source of truth** (keep in sync with CHANGELOG). |
| `TrustedHostMiddleware` | 34 | Accepts only `Host: 127.0.0.1` or `localhost` (any port); other hosts get **400**. Blocks DNS rebinding. There is **no CORS middleware**: the UI calls `/api` on its own origin, so other websites can't call the API (KI-010, plan 007). |
| `file_exists_handler` | 37-39 | App-wide `FileExistsError` → **409** `{"detail": …}` (a manager's `create()` conflict, KI-036). |
| `FRONTEND_DIR` + `/static` mount | 42-44 | Mounts `app/frontend/` at `/static` if it exists (not used by `index.html`). |
| `serve_index()` `GET /` | 47-52 | Reads and returns `index.html` on every request (so HTML edits need no restart). |
| `serve_css()` `GET /style.css`, `serve_js()` `GET /app.js` | 55-62 | `FileResponse`. |
| Character routes | 66-96 | `get_characters`; `create_character` (slug = `make_slug(slug or name)`, **422** if empty, **409** if taken); `update_character` (404 if missing or invalid slug, forces the path slug); `delete_character` (404 if missing or invalid slug). |
| Scene routes | 100-130 | Mirror of the character routes. |
| World routes | 134-142 | `GET` load, `PUT` save (full replace). |
| Chapter routes | 146-157 | `list_chapters` → `get_all(include_text=False)` (no `response_model`). `get_chapter(number)` → 404 if missing. |
| `_generation`, `_CANCELLED_EVENT`, `_generation_running()` | 162-168 | Holder of the one running generation task (`{"task": None}` until the first run), the SSE line sent when it is cancelled, and "is it still running" (plan 010, KI-031). |
| `generate_chapter` | 171-207 | **409** if a generation is running. Otherwise runs `run_pipeline` in an `asyncio.Task` (`produce()`) that feeds an `asyncio.Queue`; the SSE response (`event_stream()`) yields from the queue and cancels the task in its `finally` (client disconnect). See 02-W3.2. |
| `cancel_generation()` `POST /api/generate-chapter/cancel` | 210-217 | Cancels the running task and waits up to 5 s for it to end. Returns `{"cancelled": true}`, or `{"cancelled": false}` when nothing was running. |
| Novel-meta routes | 221-229 | `GET` load, `PUT` save (full replace). |
| `export_novel(fmt)` | 233-255 | `txt`/`md` only (400 otherwise). Writes into `data/` and returns a `FileResponse`. |
| `health()` | 259-261 | `{"status":"ok","timestamp": ISO}`. |
| `RECOMMENDED_MODELS` | 265-272 | 6 entries: `gemma3:12b`, `llama3.1:8b`, `mistral-nemo:12b`, `phi4-mini:3.8b`, `qwen2.5:7b`, `deepseek-r1:7b`, each with `size/quality/note`. |
| `_model_key(name)` | 275-277 | Compare key for model names: adds `:latest` when the last path segment has no tag (a registry host's `:port` is not a tag), as Ollama does (plan 012, KI-020). |
| `get_models()` | 280-307 | `httpx` GET `http://localhost:11434/api/tags` (5 s). Returns `{installed[], recommended[] (+installed flag), ollama_running, ollama_error}`. A recommended model is `installed` only if its `_model_key` equals one of the installed models' keys: an exact match, not the family prefix (plan 012, KI-020). |
| `pull_model(body: dict)` | 310-368 | Untyped body. `model` is required (400). Streams Ollama `/api/pull` progress as SSE. Ends with `success` only after Ollama's own `success` line; a non-200 status, an `{"error": …}` line or a missing confirmation ends with `error` (plan 010, KI-019). |
| `RefineRequest` | 372-375 | Request body of the three refine routes. |
| `refine_character` / `refine_scene` | 378-447 | See 02-W4. Lazy `from agents import specialist`. Create derives the slug from the profile name (never the LLM's slug), **422** if empty, **409** if taken. |
| `refine_world` | 450-477 | See 02-W5. |
| `__main__` | 480-482 | `uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)`. |

### 2.3 `app/backend/managers/*`

All five managers follow the same pattern. Directories are created lazily by `ensure_dir()` (characters, scenes, chapters) or by `save()` (`p.parent.mkdir`, for world/meta).

| Module | Functions | Details |
|---|---|---|
| `character_manager` | `get_all() -> List[Character]` (sorted by `name`; **unreadable or invalid files are silently skipped**), `is_valid_slug(slug)` (`[\w-]+`: letters/digits of any script, `_`, `-`; never `.`, `/`, `\` or empty, KI-010), `_path(slug)` (raises `ValueError` for an invalid slug; every file access goes through it), `get_by_slug(slug) -> Optional[Character]` (`None` for an invalid slug), `save(char)` (upsert: always overwrites; used by PUT, refine merge, step 7), `create(char)` (refuses a slug equivalent to an existing file stem, i.e. same `_slugify` result, so `elder-wu` blocks `elder_wu`; then exclusive `open(…, "x")`: never overwrites, raises `FileExistsError("Character '<existing stem>' already exists")`; used by POST, refine create, step 3), `delete(slug) -> bool` (`False` for an invalid slug), `get_as_dict() -> Dict[slug, Character]` *(unused)*, `make_slug(name)` | `_slugify`: lowercase → strip → remove `[^\w\s-]` → collapse `[\s_-]+` to `_` → strip `_`. Example: `"Xiao Fan"` → `xiao_fan`. |
| `scene_manager` | identical API for `Scene` | identical `_slugify` (duplicated code). |
| `chapter_manager` | `get_chapter(number)`, `save_chapter(chapter)`, `get_all(include_text=False)` (blanks `full_text` when False; skips bad files; sorted by number), `get_next_number()` (max+1, or 1), `get_recent_n(n, include_text)` *(unused; ignores `include_text`)* | Filename `f"{n:03d}.json"`. Chapters ≥ 1000 get 4-digit names, which still sort correctly because `get_all` sorts by number, not filename. |
| `world_manager` | `load() -> WorldSettings` (defaults if missing), `save(settings)` | `data/world_settings.json` |
| `novel_meta_manager` | `load() -> NovelMeta`, `save(meta)` | `data/novel_meta.json` |

Writes are **not atomic** (direct `open(..., "w")`). A crash mid-write can leave a truncated file, which `get_all()` then silently skips.

### 2.4 `app/backend/agents/specialist.py`

Module-level: `try: import ollama` / `except ImportError: ollama = None`. All functions except `_extract_json` are **`async def`** and must be awaited (plan 005, KI-005).

| Function | Signature | Purpose | keep_alive |
|---|---|---|---|
| `_extract_json` | `(text: str) -> Dict` | 1) `json.loads` the whole text. 2) First fenced code block (any language tag; `json` is optional in the regex, `specialist.py:25`). 3) Greedy first-`{`-to-last-`}` match. Else `{}`. Never raises. | — |
| `_call` | `async (model, system, user, keep_alive=-1) -> Dict` | `await ollama.AsyncClient().chat(model, messages=[system,user], keep_alive, format="json", options={"num_ctx": 8192, "temperature": 0.1})` → `_extract_json(response.message.content)`, returned only if it is a dict, else `{}` (plan 009, KI-015). `format="json"` is Ollama's JSON mode (KI-016). Raises `RuntimeError("ollama Python package not installed: run pip install -r app/requirements.txt")` if `ollama` is missing. Non-blocking: other requests are served meanwhile (before plan 005 it used the sync `ollama.chat`, which froze the server, KI-005). One client per call, like the writer. | param |
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

=== STORY SO FAR ===                (every chapter on disk, ascending; tier from chapter_tiers, default "micro")
Chapter n — Title (recent ending):  ← full_text tier: last 400 words
Chapter n — Title:\n{full_summary|short|micro}   ← full
Chapter n — Title: {short|micro}                   ← short
Chapter n — Title: {micro}                         ← micro
```

Iteration order of characters and scenes follows the insertion order of the `*_detail` dicts (LLM order first, then fallback additions).

### 2.7 `app/backend/pipeline/chapter_pipeline.py`

`_canonical_entities(entries, existing, make_slug)` (plan 007, KI-009) post-processes the step-2 result for characters and scenes: an entry whose slug or name normalises (`make_slug`) to an existing entity's slug or name becomes `existing` with that entity's **real** slug; anything else becomes `new` with `slug = make_slug(name)`. Non-dict entries, entries without a usable name, and repeats are dropped. Step 3 then saves each profile under `make_slug(profile name)`, never the LLM's slug.

- `_sse(event_type, **kwargs) -> str` → `f"data: {json.dumps({'type': event_type, **kwargs})}\n\n"`.
- `async def run_pipeline(plot, chapter_number, novel_meta) -> AsyncGenerator[str]`. Step logic is documented in [02 §W3.3](02-workflows.md#w33-pipeline-steps-appbackendpipelinechapter_pipelinepy).
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
- No JSON-mode / `format="json"` option is passed to Ollama, although Ollama supports it. This is a candidate improvement.

## 4. Frontend

### 4.1 Files and structure

| File | Structure |
|---|---|
| `index.html` | `<header>` (brand, inline-editable title, chapter badge, Settings, Export dropdown) → `<main class="app-layout">` with: left `<aside>` **CHARACTERS** (Main Cast / Supporting lists), center `<section>` (4 **mode tabs** + 4 mode panels, pipeline panel with 7 steps, output panel, multi-chapter notice, history bar), right `<aside>` **LOCATIONS** (+ New Location, World Settings). Six modals: `modal-character`, `modal-scene`, `modal-world`, `modal-settings`, `modal-chapter`, `modal-profile`. Toast container. Script `app.js` loaded at end of body (no `defer`/module). |
| `app.js` | One global script, no modules. Sections in order: state → DOM cache → init → API helpers → loaders/renderers (meta, characters, scenes, world, chapters) → chapter view → `generateChapter` → SSE parser → pipeline UI → character modal → scene modal → world modal → settings modal → chapter view modal → export → modal system → tag input → relationship editor → title edit → toasts → `escHtml` → static bindings → keyboard shortcuts → connection check → boot → **mode switcher** → world snapshot → existing-entity dropdowns → refine (char/scene/world) → **model browser** → second `DOMContentLoaded`. The part from "mode switcher" on was evidently appended later; it is a separate binding block. |
| `style.css` | Sections: fonts, `:root` tokens, reset, scrollbar, selection, animated background orbs, glass panel, header, app layout, sidebars, cards, center panel, pipeline, output, history bar, modals, form elements, tag input, toasts, animations (16 `@keyframes`), error/loading states, utilities, mode tabs, build panels, world snapshot, model browser. **No `@media` queries**, so the layout is desktop-only. |

### 4.2 Global state (`app.js:11-34`)

```js
state = {
  characters: [], scenes: [], world: {}, chapters: [], novelMeta: {},
  currentChapter: null,      // full Chapter from GET /chapters/{n}, or {chapter_number,title,word_count,characters_featured,scenes_featured} after generation
  isGenerating: false,       // this tab's lock; the server also allows only one generation (409, plan 010)
  activeModal: null,         // id of the open modal overlay
  _abilities, _habits, _inhabitants, _genreTags, _professions, _hierarchy, _factions: [],  // tag-input stores
  _relationships: {},        // relationship editor store
  _profileContext: null,     // {type, slug} of the profile modal
  _editingCharSlug: null, _editingSceneSlug: null,   // null = create mode
  // activeMode is set dynamically by switchMode() (not declared here)
}
```

Constant `API = '/api'` (`app.js:6`): same origin as the page, so it works whether the UI is opened as `127.0.0.1` or `localhost`, and the server needs no CORS (KI-010/KI-021, fixed in plan 007).

### 4.3 API helpers (`app.js:120-156`)

| Helper | Returns | Error behaviour |
|---|---|---|
| `apiGet(path)` | parsed JSON | throws `GET … failed: status` |
| `apiPost(path, body)` | parsed JSON | throws with response text |
| `apiPut(path, body)` | parsed JSON | throws with response text |
| `apiDelete(path)` | parsed JSON | throws |

> All four helpers return parsed JSON and throw on a non-2xx status, so callers don't check `res.ok`. In v1.0.0 `apiPost` returned the raw `Response`, which caused KI-002 (fixed by plan 003). `generateChapter` and `pullModel` call `fetch` directly, because they read an SSE stream.

### 4.4 Function catalogue

| Area | Functions |
|---|---|
| Boot | `init`, `checkConnection`, `bindStaticEvents`, `bindModeTabs` |
| Loaders / renderers | `loadNovelMeta`/`renderNovelMeta`, `loadCharacters`/`renderCharacters`, `loadScenes`/`renderScenes`, `loadWorld`, `loadChapters`/`renderChapterHistory`/`updateChapterHint`/`nextChapterNumber` (highest `chapter_number` + 1, the backend's rule), `renderCardList`, `createEntityCard` |
| Chapter output | `viewChapter`, `showChapterOutput`, `formatChapterText` (splits on `\n\n+`, one `<p>` per paragraph via `textContent`) |
| Generation | `generateChapter` (its SSE handler map shows `warning` events as warning toasts, plan 009, KI-018; a cancelled `error` resets the steps and shows an info toast; a non-2xx response shows the server's `detail`, e.g. the 409, plan 010), `cancelGeneration` (posts `/generate-chapter/cancel`; the button is shown only while generating), `parseSSEStream` (buffered line splitting, ignores malformed lines and `[DONE]`), `resetPipeline` (also cancels the pending fade and clears the previous run's opacity and red step styles, plan 011, KI-024), `activatePipelineStep`, `completePipelineStep`, `completePipeline` (fades the panel to 0.4 opacity after 2 s; the timer id is kept in `_pipelineFadeTimer`), `updateProgress`, `setStepError` (inline red border/background on the active step), `addNewEntityTag` |
| Character | `openCharacterModal(slug?)`, `saveCharacter` (create sends `slug: ''` and the server derives it; edit sends `{...existing, ...form}` so the fields the modal doesn't show are kept), `deleteCharacter`, `viewCharacterProfile` |
| Scene | `openSceneModal(slug?)`, `saveScene` (same payload rules as `saveCharacter`), `deleteScene`, `viewSceneProfile` |
| World / settings | `openWorldModal`, `saveWorld`, `openSettingsModal` (fills the model selects from `state.novelMeta`, then `loadModels()` → `populateModelSelects` + `renderModelBrowser`), `saveSettings` (sends `{...state.novelMeta, …form}`; an empty select keeps the stored model), `renderWorldSnapshot` (⚠ unescaped `innerHTML`) |
| Chapter modal | `openChapterViewModal` |
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

### 4.6 Streaming paragraph algorithm (`token` handler, `app.js:491-527`)

- `streamedText` accumulates text since the last paragraph break. `currentParagraph` is the `<p>` being filled.
- A chunk **without** `\n\n` is appended to `currentParagraph.textContent` (a `<p>` is created on first use).
- A chunk **with** `\n\n` → split the accumulated `streamedText` on `\n\n`. The first part finalises the current `<p>`, middle parts become new `<p>`s, and the last part starts a new current `<p>`.
- Edge cases: a single `\n` stays inside the paragraph (rendered as a space). If the first chunk already contains `\n\n`, the handler first creates the paragraph and then splits, so that text shows at once (plan 013; before, an `if (currentParagraph)` guard held it back until a later chunk with `\n\n`, KI-032).
- The cursor element `#text-cursor` is re-appended at the end after every token, with `scrollIntoView({block:'nearest'})`.

### 4.7 Design system (CSS tokens, `style.css:8-61`)

| Token group | Values |
|---|---|
| Background / panels | `--bg #080b14`, `--panel-bg rgba(12,17,35,.85)`, `--panel-bg-solid #0c1123`, `--glass-blur blur(20px)` |
| Accents | `--purple #8a4fff` (characters / primary), `--gold #f5c842` (locations), `--mint #4fffb0` (world / success), `--error #ff4f6a`, plus `*-dim`/`*-mid` alpha variants and `--gradient-purple/gold/dark` |
| Text | `--text-primary #e8eaf6`, `--text-secondary #7c83a0`, `--text-muted #4a5178` |
| Fonts | `--font-display 'Cinzel'`, `--font-body 'Crimson Pro'`, `--font-mono 'JetBrains Mono'` |
| Layout | `--sidebar-w 280px`, `--header-h 64px`, radii `6/12/18/24px` |
| Effects | `--glow-purple/gold/mint/text`, `--transition all .3s cubic-bezier(.4,0,.2,1)` |

Layout: fixed header (64 px), then `.app-layout` as a fixed flex row filling the rest of the viewport: left sidebar (280 px), flexible center, right sidebar (280 px). Colour semantics: **purple = characters, gold = locations, mint = world**.

## 5. Error-handling strategy by layer

| Layer | Strategy | Gaps |
|---|---|---|
| Managers | Reads of single items raise on corrupt JSON. `get_all()` swallows every exception per file. | No logging, so corrupted files disappear silently from the UI. |
| Specialist | Never raises on bad JSON (`{}`); raises on transport errors. | Type errors surface later in the pipeline. |
| Writer | Converts any exception into an `error` tuple. | — |
| Pipeline | Global try/except → `error` SSE with traceback. | Partial writes (step-3 profiles) are not rolled back. |
| Routes | `HTTPException` 400/404/500. Pydantic 422 on invalid bodies. **409** from the app-wide `FileExistsError` handler (`file_exists_handler`, right after the `TrustedHostMiddleware` setup in `main.py`), which catches a manager's `create()` conflict, and from `generate_chapter` while another generation runs (plan 010). Refine create maps the same error to 409 explicitly. Nothing else raises `FileExistsError` (all `mkdir` calls use `exist_ok=True`). | No logging. Refine endpoints wrap model construction but not the LLM call (transport errors → 500 with default message). |
| Frontend | try/catch around each action → toast. Loaders fall back to empty state. A cancelled generation is an info toast, not an error (plan 010). | Errors go only to toasts and `console.error`. (`warning` SSE events are shown since plan 009; the pipeline panel's fade and error styles are reset at each run since plan 011.) |

There is **no logging framework**. The only diagnostics are uvicorn access logs in the backend window, SSE `error.detail` tracebacks (not shown in the UI) and browser `console.*`.

## 6. Dead / unused code

| Item | Location |
|---|---|
| `character_manager.get_as_dict`, `scene_manager.get_as_dict` | managers |
| `chapter_manager.get_recent_n` | `chapter_manager.py:53` |
| `featured_scene_slugs` alias | `chapter_pipeline.py:207` |
| `/static` mount | `main.py:43-44` |
| `state._profileContext` (written, never read) | `app.js` |
| Unused imports: `Dict` (main.py), `Character`, `Scene` (specialist.py, only the names appear inside prompt strings), `Optional` (context_builder.py) | various |
