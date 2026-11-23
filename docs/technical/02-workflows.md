# 02 — Workflows

> **Applies to:** v1.0.0. **Last verified against code:** 2026-11-22.
> Line references (`file:line`) point to v1.0.0 and will drift as code changes. Re-verify before relying on them.

This document describes every end-to-end flow in the application: what triggers it, which components take part, what data is read and written, and how failures behave.

| # | Workflow | Trigger |
|---|---|---|
| W1 | [Application launch](#w1--application-launch-appstartbat) | Double-click `app/start.bat` |
| W2 | [Frontend boot](#w2--frontend-boot) | Browser loads `/` |
| W3 | [Chapter generation (7-step pipeline)](#w3--chapter-generation-the-7-step-pipeline) | **▶ Generate Chapter**, `Ctrl+Enter`, `Alt+G` |
| W4 | [Character / Scene build (refine)](#w4--character--scene-build-refine) | **Refine & Save** buttons |
| W5 | [World build (refine + merge)](#w5--world-build-refine--merge) | **Integrate into World Settings** |
| W6 | [Manual CRUD of characters / locations](#w6--manual-crud-characters--locations) | Sidebar **+ New**, card **Edit/Delete** |
| W7 | [World settings & novel settings editing](#w7--world-settings--novel-settings-editing) | **World Settings**, **⚙ Settings**, title click |
| W8 | [Model management (list / select / pull)](#w8--model-management) | Opening Settings, **Refresh**, **Pull** |
| W9 | [Chapter history & reader](#w9--chapter-history--full-view-reader) | History pill, **⛶ Full View** |
| W10 | [Export](#w10--export) | **📤 Export → .txt / .md** |

---

## W1 — Application launch (`app/start.bat`)

```mermaid
flowchart TD
    A[Double-click app/start.bat] --> B{"py --version OK?"}
    B -- yes --> P[PYTHON_EXE=py]
    B -- no --> C{"python --version OK?"}
    C -- yes --> Q[PYTHON_EXE=python]
    C -- no --> X1["[ERROR] Python not found → pause, exit 1"]
    P & Q --> D{"DEP_CHECK OK?<br/>(fastapi, uvicorn, pydantic, httpx, ollama ≥ 0.4)"}
    D -- no --> E["pip install -r app/requirements.txt -q"]
    E --> D2{"DEP_CHECK OK now?"}
    D2 -- no --> X3["[ERROR] still missing → print manual pip command, pause, exit 1"]
    D2 -- yes --> G{"app/backend/main.py exists?"}
    D -- yes --> F["[OK] Dependencies ready"]
    F --> G
    G -- no --> X2["[ERROR] Not found → pause, exit 1"]
    G -- yes --> H["start /min /d backend\\ python -m uvicorn main:app --host 127.0.0.1 --port 8000<br/>(window: NovelForge-Backend)"]
    H --> I["Poll GET /api/health every 2 s (max 15 tries ≈ 30 s)"]
    I -- 200 --> J["[OK] Server is up!"]
    I -- 15 failures --> K["[WARN] slow to start, open anyway"]
    J & K --> L["start http://127.0.0.1:8000"]
    L --> M[Launcher waits for a key press, then closes; the backend window keeps running]
```

Notes:
- The dependency check (`DEP_CHECK`, `app/start.bat:40`) imports every runtime package and requires `ollama` ≥ 0.4, so a missing or too-old package triggers `pip install -r` (which also upgrades). If the packages are still missing afterwards (no network, pip error), the launcher stops with the manual command instead of starting a broken server. In v1.0.0 it probed only `fastapi` (KI-003, fixed in plan 005).
- Even without `ollama`, the backend itself now starts (the import is optional). Generation and the Build tabs then fail with "ollama Python package not installed: run pip install -r app/requirements.txt".
- To stop the app, close the minimised **NovelForge-Backend** window. The launcher has no stop command.

## W2 — Frontend boot

1. `GET /` → `serve_index()` reads `app/frontend/index.html` and returns it (`main.py:46-51`). The page then loads `/style.css` and `/app.js` through dedicated routes (`main.py:54-61`).
2. `DOMContentLoaded` listener #1 (`app.js:1438`):
   1. `checkConnection()` → `fetch /api/novel-meta` with a 3 s timeout. On a network failure it shows the toast *"⚠ Cannot connect to backend…"* for 8 s.
   2. `init()` → `bindStaticEvents()`, then runs these in parallel with `Promise.allSettled`: `loadNovelMeta`, `loadCharacters`, `loadScenes`, `loadWorld`, `loadChapters`. Then `updateChapterHint()`.
3. `DOMContentLoaded` listener #2 (`app.js:1877`) binds the mode tabs, the three refine buttons and **Refresh models**. (Until plan 006 it also added a second **⚙ Settings** click listener that loaded the models; `openSettingsModal` now does that itself.)
4. Each loader stores its result in `state.*` and renders: sidebars (character/scene cards), header title, chapter count badge, history pills, "CHAPTER N" label.
5. If a loader fails it logs `console.warn` and falls back to empty data. The UI stays usable.

## W3 — Chapter generation (the 7-step pipeline)

### W3.1 Trigger (frontend: `generateChapter()`, `app.js:420-562`)

1. Validates that the plot textarea is not empty and that no generation is running (`state.isGenerating`).
2. Disables the button, resets and shows the pipeline panel, hides the old output and the multi-chapter notice.
3. `POST`s `/api/generate-chapter` with `{plot}` only. The backend numbers the chapter itself (`get_next_number()`: highest existing number + 1, read from disk), so a gap or a stale page can't overwrite a chapter. The UI shows `nextChapterNumber()` (the same rule over `state.chapters`) while streaming and takes the real number from the `complete` event. (Before plan 006 it sent `count + 1`, which overwrote chapters after a gap: KI-008.)
4. Reads the response body as a stream and parses SSE `data:` lines (`parseSSEStream`, `app.js:567-606`). Each JSON event is dispatched by its `type` (see W3.4).

### W3.2 Backend entry (`main.py:160-177`)

- Loads `NovelMeta` from `data/novel_meta.json` to get the model names.
- `chapter_number = req.chapter_number or chapter_manager.get_next_number()`. The frontend always sends a number, so the backend fallback is effectively unused.
- Returns `StreamingResponse(run_pipeline(...), media_type="text/event-stream")` with headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive`.

### W3.3 Pipeline steps (`app/backend/pipeline/chapter_pipeline.py`)

| Step | UI label | Code | LLM call (model, keep_alive) | Input | Output / side effects | SSE emitted |
|---|---|---|---|---|---|---|
| 1 | Analyze Plot | `:67-78` | `specialist.analyze_plot` (spec, -1) | plot | `tone`, `estimated_chapters`, `entity_mentions{characters[],locations[]}`, `key_events`, `chapter_focus` (only tone, estimated_chapters, entity_mentions are used) | `status{step:1}` ×2. `multi_chapter` if `estimated_chapters > 1` |
| 2 | Extract Entities | `:80-93` | `specialist.resolve_entities` (spec, -1) | mentions + all existing `{name, slug}` pairs | `characters[]`/`scenes[]` with `{name, slug, status: existing\|new, importance}` The result is then canonicalised server-side (`_canonical_entities`, plan 007): matches by slug or name (ignoring case and `-`/`_`) become `existing` with the real slug, everything else `new` with `slug = make_slug(name)`; nameless entries and repeats are dropped. | `status{step:2}` ×2 |
| 3 | Build Profiles | `:95-117` | `specialist.profile_new_entities` (spec, -1). **Skipped when nothing is new** | new names, plot, world brief, tone, chapter number | Creates `Character`/`Scene` objects with `slug = make_slug(profile name)` (never the LLM's slug) and **creates their files** in `data/` with `create()`, which never overwrites (also not an equivalent slug). A slug that already exists keeps the existing profile. | `status{step:3}`, `new_character{name,slug}`, `new_scene{name,slug}`, `warning{message}` on validation failure or an existing slug |
| — | (reload) | `:119-123` | — | — | Re-reads all characters and scenes into `chars_dict` / `scenes_dict` keyed by slug | — |
| 4 | Optimize Context | `:125-176` | `specialist.select_context` (spec, -1). **Skipped when no resolved entity exists on disk** | involved entities with importance, chapter numbers, plot | `character_detail{slug: full\|compressed\|skip}`, `scene_detail{slug: full\|skip}`, `chapter_tiers{"n": tier}`. Missing keys are filled by hard-coded fallback rules (below) | `status{step:4}` ×2 |
| 5 | Prepare Model | `:178-184` | `specialist.predict_updates` (spec, **0 → unloads specialist**) | plot, primary char slugs, main scene slugs | Result stored in `update_predictions` and **never used** (KI-012) | `status{step:5}` ×2 |
| — | (prompt) | `:186-196` | — | world + dicts + chapters + detail maps | `master_prompt` string (see [03 §2.6](03-low-level-design.md#26-appbackendpipelinecontext_builderpy)) | — |
| 6 | Write Chapter | `:198-209` | `writer.stream_chapter` (writer, 300 s, streaming) | master prompt, plot, chapter number | Tokens are appended to `full_text`. `word_count = len(full_text.split())` | `status{step:6}`, many `token{content}`, then `status{step:6}` "Chapter written: N words". `error` → **pipeline returns early, nothing saved** |
| 7 | Summarize & Save | `:211-268` | `specialist.post_write_update` (spec, **0**) | **first 3000 chars** of the chapter (KI-014), primary character briefs | Saves `data/chapters/NNN.json`. Updates character `last_seen_chapter`, `arc_notes`, `cultivation_level`, `abilities` (set-union), `relationships` (dict update). Updates `novel_meta.total_chapters = max(old, n)` | `status{step:7}`, `complete{…}` |
| ✖ | — | `:270-272` | — | any uncaught exception | Nothing further is saved. **Profiles already created in step 3 stay on disk.** | `error{message, detail: traceback}` |

#### Fallback rules (always applied after step 4)

- **Characters:** `importance == "primary"` → `full`, otherwise → `compressed` (`:151-154`).
- **Scenes:** `importance == "main"` → `full`, otherwise → `skip` (`:155-158`).
- **Chapter tiers**, relative to the chapter being written `N`, for each existing chapter `n` (`:161-174`):

| `N − n` | Tier | What goes into the prompt |
|---|---|---|
| 1 | `full_text` | Last 400 words of that chapter's text (`context_builder.py:83-87`) |
| 2–4 | `full` | `full_summary` (falls back to short, then micro) |
| 5–8 | `short` | `short_summary` (falls back to micro) |
| ≥ 9, or ≤ 0 (e.g. regenerating an earlier chapter) | `micro` | `micro_summary` |

> When regenerating chapter *k* with chapters after *k* already on disk, those **later** chapters are also included in "STORY SO FAR" (as `micro`, because `N − n ≤ 0`). The current chapter's old version is included too.

#### Post-write character update rules (`:234-255`)

For every slug in `post_data.character_updates` that exists:
`last_seen_chapter = N`. Non-empty `arc_notes` replaces the old value. Non-empty `cultivation_level` replaces the old value. `new_abilities` is merged as a set (**order is lost**). `relationship_updates` is merged into the relationships dict. Then the character is saved.
Primary characters with no update entry still get `last_seen_chapter = N`.
`scene_updates` returned by the LLM are **ignored** (KI-013).

### W3.4 SSE event contract (backend → frontend)

| `type` | Payload fields | Emitted at | Frontend handler (`app.js:465-550`) |
|---|---|---|---|
| `status` | `step` (1–7), `message` | Start/end of each step | Marks the previous step done, the current one active, writes `message` to the step log, sets progress = step/7 |
| `multi_chapter` | `estimated`, `message` | Step 1 if estimated > 1 | Shows the notice panel + warning toast |
| `new_character` | `name`, `slug` | Step 3 per saved character | Adds an entity tag, reloads characters after 300 ms, shows a toast |
| `new_scene` | `name`, `slug` | Step 3 per saved scene | Same, for scenes |
| `warning` | `message` | Step 3 profile validation failure | **No handler: silently ignored** (KI-018) |
| `token` | `content` | Step 6, per chunk | Appends to the current `<p>`. Splits paragraphs on `\n\n`. Moves the blinking cursor |
| `error` | `message`, `detail?` | Writer error or uncaught exception | Error toast, hides the cursor, paints the active step red |
| `complete` | `chapter_number`, `title`, `word_count`, `characters[]`, `scenes[]`, `micro_summary` | End of step 7 | Marks all steps done, sets title and word count, `state.currentChapter = {chapter_number,title,word_count}`, sets the badge from `chapter_number`, reloads chapters, characters **and novel meta** (step 7 updated profiles and `total_chapters` on disk; the Edit and Settings modals read that state), clears the plot textarea, success toast |

Wire format: each event is one line `data: {json}\n\n` (`chapter_pipeline.py:20-23`). No `event:` or `id:` fields are used.

### W3.5 Sequence diagram

```mermaid
sequenceDiagram
    autonumber
    participant UI as Browser (app.js)
    participant API as FastAPI main.py
    participant PL as chapter_pipeline
    participant SP as specialist (sync)
    participant WR as writer (async)
    participant OL as Ollama
    participant FS as data/ (managers)

    UI->>API: POST /api/generate-chapter {plot, chapter_number}
    API->>FS: novel_meta_manager.load()
    API-->>UI: 200 text/event-stream (StreamingResponse)
    API->>PL: run_pipeline(plot, n, meta)
    PL-->>UI: status step 1
    PL->>SP: analyze_plot
    SP->>OL: chat(spec, keep_alive=-1)
    OL-->>SP: JSON text
    PL-->>UI: status step 1 (tone, entity count) [+ multi_chapter]
    PL->>FS: list characters & scenes
    PL->>SP: resolve_entities
    SP->>OL: chat
    PL-->>UI: status step 2
    alt new entities
        PL->>SP: profile_new_entities
        SP->>OL: chat
        PL->>FS: save new Character/Scene JSON
        PL-->>UI: new_character / new_scene (warning on failure)
    end
    PL->>FS: reload characters, scenes, all chapters (with text)
    opt involved entities exist
        PL->>SP: select_context
        SP->>OL: chat
    end
    PL-->>UI: status step 4
    PL->>SP: predict_updates (keep_alive=0)
    SP->>OL: chat → specialist unloaded
    PL-->>UI: status step 5
    PL->>PL: build_master_prompt()
    PL-->>UI: status step 6
    PL->>WR: stream_chapter
    WR->>OL: AsyncClient.chat(stream, keep_alive=300)
    loop tokens
        OL-->>WR: chunk
        WR-->>PL: ("token", text)
        PL-->>UI: token
    end
    PL-->>UI: status step 6 (word count)
    PL-->>UI: status step 7
    PL->>SP: post_write_update(first 3000 chars, keep_alive=0)
    SP->>OL: chat
    PL->>FS: save chapters/NNN.json, update characters, update novel_meta
    PL-->>UI: complete
    UI->>API: GET /api/chapters (refresh history)
```

### W3.6 Failure behaviour summary

| Failure | Result |
|---|---|
| Ollama not running / model missing during steps 1–5 or 7 | Exception → `error` event "Pipeline error: …" with traceback. Nothing saved, except profiles already written in step 3. |
| Specialist returns non-JSON | `_extract_json` returns `{}`. Downstream `.get()` defaults apply: tone "action", no entities, empty summaries. Generation continues with less context. |
| Specialist returns a wrong type (e.g. `"estimated_chapters": "2"`) | `TypeError` on `>` comparison → whole pipeline aborts (KI-015). |
| New entity JSON fails Pydantic validation (e.g. `type: "supporting"`) | `warning` event (ignored by the UI). Entity not saved. Pipeline continues. |
| A "new" entity's profile reuses an existing slug (the specialist missed the match in step 2) | `warning` event "Could not save character profile: Character 'x' already exists". The existing profile is kept unchanged and still used for context. Pipeline continues. (Before plan 004 it was overwritten, KI-036.) |
| Writer error | `error` event "Writer error: …". Pipeline returns **before saving**. Streamed text is lost on the server; the browser still shows it. |
| Browser tab closed mid-stream | Starlette stops iterating the generator. Whatever was not yet saved is lost. |

## W4 — Character / Scene build (refine)

Frontend: `refineCharacter()` (`app.js:1529-1571`) / `refineScene()` (`app.js:1576-1616`).
Backend: `refine_character` (`main.py:310-339`) / `refine_scene` (`main.py:342-369`).

```mermaid
sequenceDiagram
    participant UI as Character/Scene Build tab
    participant API as /api/refine/character|scene
    participant SP as specialist.refine_*
    participant FS as managers
    UI->>API: POST {description, name?, existing_slug?}
    API->>FS: load novel_meta (specialist model), world
    API->>SP: refine_character(description, name, world, model)
    SP-->>API: dict (profile JSON) or {}
    alt result empty
        API-->>UI: 500 "Failed to generate … profile"
    else existing_slug given and found
        API->>API: copy every truthy field except slug/name/first_appeared_chapter onto existing
        API->>FS: save(existing)
        API-->>UI: 200 merged profile
    else create
        API->>API: Character(**result)  (LLM-provided slug used verbatim)
        API->>FS: create(new)  (exclusive, never overwrites)
        API-->>UI: 200 new profile (500 if validation fails, 409 if the slug exists)
    end
    UI->>UI: status + toast "Created/Updated: name" (apiPost returns parsed JSON)
    UI->>API: GET /api/characters|scenes (sidebar reload)
```

Merge semantics for "Update Existing":
- **Overwrites** each field for which the LLM returned a truthy value. Lists such as `abilities` are **replaced**, not merged.
- The existing `slug`, `name` and `first_appeared_chapter` are always kept.
- ⚠ Values are assigned with `setattr` and **not validated** (no `validate_assignment` on the models). An invalid LLM value (e.g. `type:"supporting"`, `age:17`) is written to disk, after which the file no longer loads: the entity disappears from the sidebar and later edits/merges of it return 500 (verified, KI-016).
- Refine calls use `keep_alive=-1`, so the specialist **stays loaded in VRAM** afterwards (until a generation unloads it or Ollama restarts).

## W5 — World build (refine + merge)

Frontend `refineWorld()` (`app.js:1621-1653`) → `POST /api/refine/world` (`main.py:372-396`).

1. The specialist (`specialist.refine_world`) gets a brief of the current world (name, genres, cultivation, magic, hierarchy) and the author's description. It returns the full `WorldSettings` shape, with only the fields that the description touches filled in.
2. Merge into the existing world (`main.py:382-394`):
   - **List fields** (`genre_tags`, `professions`, `hierarchy_levels`, `factions`): append each truthy item that is not already present (exact-string dedupe, order kept).
   - **String fields:** replaced when the new value is non-empty.
   - Unknown keys are ignored.
3. Saves `data/world_settings.json` and returns the merged world.
4. The frontend stores the returned world in `state.world` and redraws the snapshot, so the World Settings modal opens with the merged values. (In v1.0.0 it stored the raw `Response`, so saving the modal afterwards wiped the world. KI-002, fixed by plan 003.)

## W6 — Manual CRUD (characters / locations)

| Action | UI | Request | Backend behaviour |
|---|---|---|---|
| Create | **+ New Character / + New Location** → modal → Save | `POST /api/characters` `{character:{slug:"", …}}` / `POST /api/scenes` `{scene:{slug:"", …}}` | Stores `make_slug(slug or name)` (lowercase, `_` separators; letters of any script kept). **422** if that is empty (e.g. `???`). **409** if that slug, or an equivalent one (`elder-wu` vs `elder_wu`), already exists. The UI shows the error and keeps the modal open, so the user can rename. |
| Edit | Card **Edit** (or profile modal **Edit**) → Save | `PUT /api/characters/{slug}` / `PUT /api/scenes/{slug}` with `{...existing record from state, ...form fields}` | 404 if the file is missing. Forces `slug` = path slug. **Full replace** of the file, but the UI sends every field, so the ones the modal doesn't show (`first_appeared_chapter`, `last_seen_chapter`) are kept. |
| Delete | Card **Delete** → `confirm()` | `DELETE /api/characters/{slug}` / `/api/scenes/{slug}` | Deletes the file. 404 if missing. |
| View | Click card / **View** | (no request: uses `state`) | Read-only profile modal. |

> History: in v1.0.0, Create and Edit both failed with HTTP 422, because the payload had no `slug` (KI-001). Plan 003 fixed this in the frontend, together with the reset of the chapter-tracking fields on edit (KI-027). The API contract is unchanged: `slug` is still a required body field.

## W7 — World settings & novel settings editing

- **World Settings modal** (`openWorldModal`/`saveWorld`, `app.js:972-1019`): fills the form from `state.world` and saves with `PUT /api/world {settings}` (full replace).
- **Novel Settings modal** (`openSettingsModal`/`saveSettings`, `app.js:1024-1064`): title, genre, author, writer model, specialist model → `PUT /api/novel-meta {meta}`. The body is `{...state.novelMeta, …form}`, so `total_chapters` and `created_at` are kept, and an empty model select falls back to the stored model. `state.novelMeta` is reloaded after every generation, so the count is current. Opening the modal (button or **Alt+S**) fills the model lists at once and refreshes them from Ollama (see W8). (KI-006/KI-007, fixed in plan 006.)
- **Inline title edit** (`initTitleEdit`, `app.js:1245-1284`): click the title, type, then Enter or blur → `PUT /api/novel-meta` with `{...state.novelMeta, title}`. This keeps the other fields. Escape cancels.

## W8 — Model management

1. Opening **⚙ Settings** (button or **Alt+S**: both call `openSettingsModal`) first fills both `<select>`s with the current models, then `loadModels()` → `GET /api/models` (cached in `_cachedModels` until **↻ Refresh**) refreshes the lists and the model browser, keeping any choice made meanwhile.
2. Backend (`main.py:234-263`) calls `GET http://localhost:11434/api/tags` (5 s timeout) and annotates `RECOMMENDED_MODELS` with an `installed` flag.
   ⚠ "Installed" matches **any tag in the same family**, so `gemma3:4b` installed marks `gemma3:12b` as installed (KI-020).
3. The UI fills both `<select>`s (installed models + current selections, the latter tagged "(not installed)") and renders the model browser cards with **Set Writer / Set Specialist** (installed) or **⬇ Pull** (not installed).
4. **Pull** → `POST /api/models/pull {model}` → the backend streams `POST /api/pull` from Ollama, re-emitting `data: {status, percent, total, completed}`, then `{status:"success", model}` or `{status:"error", message}`.
   ⚠ Ollama error lines (`{"error": …}`) and HTTP error statuses are not detected, so a failed pull can still end with `success` (KI-019).
5. Selecting a model only changes the `<select>`. It is saved when the user clicks **Save Settings**.

## W9 — Chapter history & Full View reader

- The history bar shows one pill per chapter from `GET /api/chapters` (summaries only; `full_text` is blanked by the server).
- Clicking a pill → `GET /api/chapters/{n}` → `showChapterOutput()` renders the paragraphs and highlights the pill.
- **⛶ Full View** → `openChapterViewModal()`. It copies the output area's HTML (or formats `full_text`, or fetches the chapter) and shows the featured character/scene **slugs** as tags.
  Right after a generation, `state.currentChapter` only holds `{chapter_number, title, word_count}`, so the featured tags are empty until the chapter is reopened from history.

## W10 — Export

1. `exportNovel(fmt)` creates a temporary `<a href="/api/export/{fmt}">` and clicks it.
2. Backend (`main.py:193-215`) loads all chapters with text, sorted by number, and builds:
   - **md:** `# {title}` then `## Chapter {n}: {title}` + text per chapter.
   - **txt:** `{title}` + `====` underline, then `Chapter {n}: {title}` + 40 dashes + text.
3. Writes the result to `data/{title with spaces→_}.{fmt}` (a side effect that stays on disk), then returns it as a `FileResponse` download.
   A title with characters that are invalid in Windows filenames (`: ? * " < > |`) makes the export fail (KI-017).
