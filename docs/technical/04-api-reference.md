# 04 — API Reference

> **Applies to:** v2.0.0 + [Unreleased] (plan 019: draft routes, generate fields). **Last verified against code:** 2026-11-24.
> Base URL: `http://127.0.0.1:8000`. All `/api/*` bodies are JSON unless marked **SSE**. No authentication. **Same-origin only**: there is no CORS, so browsers block calls from other websites, and the `Host` header must be `127.0.0.1` or `localhost` (otherwise **400**). Scripts and curl on this machine are unaffected (plan 007, KI-010).
> FastAPI's auto-generated docs are also available while the server runs: **`/docs`** (Swagger UI) and **`/redoc`**. They are authoritative for request schemas.

## Endpoint index

| Method | Path | Purpose | Frontend caller |
|---|---|---|---|
| GET | `/` | App HTML | browser |
| GET | `/style.css`, `/app.js` | Static assets | `index.html` |
| GET | `/static/{file}` | Static mount of `app/frontend/` (unused) | — |
| GET | `/api/health` | Liveness | `app/start.bat` |
| GET | `/api/novel-meta` | Read novel metadata | `loadNovelMeta`, `checkConnection` |
| PUT | `/api/novel-meta` | Replace novel metadata | `saveSettings`, `initTitleEdit` |
| GET | `/api/characters` | List characters | `loadCharacters` |
| POST | `/api/characters` | Create character | `saveCharacter` (create) |
| PUT | `/api/characters/{slug}` | Replace character | `saveCharacter` (edit) |
| DELETE | `/api/characters/{slug}` | Delete character | `deleteCharacter` |
| GET | `/api/scenes` | List scenes | `loadScenes` |
| POST | `/api/scenes` | Create scene | `saveScene` (create) |
| PUT | `/api/scenes/{slug}` | Replace scene | `saveScene` (edit) |
| DELETE | `/api/scenes/{slug}` | Delete scene | `deleteScene` |
| GET | `/api/world` | Read world settings | `loadWorld` |
| PUT | `/api/world` | Replace world settings | `saveWorld` |
| GET | `/api/chapters` | List chapters (no text) | `loadChapters` |
| GET | `/api/chapters/{number}` | Get one chapter (with text) | `viewChapter`, `openChapterViewModal` |
| POST | `/api/generate-chapter` | **SSE** run the 7-step pipeline (one at a time), or steps 1–6 into a draft | `generateChapter` |
| POST | `/api/generate-chapter/cancel` | Stop the running generation | `cancelGeneration` |
| GET | `/api/draft` | The chapter draft waiting for review, or `null` | `loadDraft` |
| PUT | `/api/draft` | Save the draft's text and title | `saveDraftNow` (autosave) |
| DELETE | `/api/draft` | Discard the draft | `discardDraft` |
| POST | `/api/draft/rewrite` | LLM: rewrite a selected passage of the draft | `rewriteSelection` |
| POST | `/api/draft/approve` | Run step 7 on the draft and save it as a chapter | `approveDraft` |
| POST | `/api/refine/character` | LLM: description → character (create or merge) | `refineCharacter` |
| POST | `/api/refine/scene` | LLM: description → scene (create or merge) | `refineScene` |
| POST | `/api/refine/world` | LLM: description → merged world settings | `refineWorld` |
| GET | `/api/models` | Installed + recommended Ollama models | `loadModels` |
| POST | `/api/models/pull` | **SSE** pull a model through Ollama | `pullModel` |
| GET | `/api/export/{fmt}` | Download the novel as `txt` or `md` | `exportNovel` |

Common error shapes: FastAPI `HTTPException` → `{"detail": "message"}`. Validation errors → **422** with `{"detail": [ {loc, msg, type, …} ]}`. Create conflicts → **409** `{"detail": "Character 'x' already exists"}` (raised as `FileExistsError` by a manager's `create()` and mapped by an app-wide handler in `main.py`).

Character, scene and world bodies are **coerced** before validation (plan 009): e.g. `"age": 17` → `"17"`, `"type": "supporting"` → `"temporary"`, `"abilities": "fly"` → `["fly"]`. Only a missing/null `name` or `slug` (and malformed JSON) still gives 422. Rules: [05 §2](05-data-model-and-storage.md).

---

## Health

### `GET /api/health`
**200** `{"status": "ok", "timestamp": "2026-11-22T18:40:00.123456"}`

## Novel metadata

### `GET /api/novel-meta`
**200** `NovelMeta`:
```json
{"title":"Untitled Novel","genre":"","author":"","total_chapters":1,
 "writer_model":"gemma3:12b","specialist_model":"phi4-mini:3.8b","created_at":"","review_drafts":true}
```
Returns model defaults if `data/novel_meta.json` is missing. `review_drafts` (plan 019, default `true`) is the UI's "Review each chapter as a draft" setting; the server only stores it (the UI sends it as `review` when generating).

### `PUT /api/novel-meta`
Body: `{"meta": NovelMeta}`. Omitted fields take **model defaults**: a body without `total_chapters` resets it to 0.
**200** echoes `meta`. Full replace of `data/novel_meta.json`.

## Characters

### `GET /api/characters`
**200** `Character[]` sorted by `name`. Files that fail to parse are skipped, and each skip is logged on the server console (plan 016).

### `POST /api/characters`
Body: `{"character": Character}`. **`character.slug` is required by the schema** (send `""`). The server always stores `make_slug(slug or name)`: lowercase, punctuation removed, spaces/`-`/`_` → `_` (`"Elder Wu"` → `elder_wu`, `"Zz-Test-Two!"` → `zz_test_two`; letters of any script are kept, e.g. `林凡`). **422** `Character name must contain at least one letter or digit` if that is empty (KI-009/KI-038, plan 007).
**200** `Character`. **422** if `slug` is missing. (The v1.0.0 UI omitted it, KI-001. Since plan 003 the UI sends `""` on create.)
**409** `Character '{existing}' already exists` if a file with that slug, or an *equivalent* one (same letters ignoring case and `-`/`_`, e.g. existing `xiao-fan-scientist-inventor` vs new `Xiao Fan Scientist Inventor`), exists. Create never overwrites; use `PUT` to change an existing character. On Windows, a slug that differs only in case also conflicts. (Before plan 004 the existing file was silently overwritten, KI-036.)

### `PUT /api/characters/{slug}`
Body: `{"character": Character}` (body `slug` required but ignored; the path slug wins).
**200** `Character` · **404** `Character '{slug}' not found` (also for a slug that isn't `[\w-]+`, e.g. one containing `\` or `.`; such slugs never reach the file system, KI-010) · **422** invalid body.

### `DELETE /api/characters/{slug}`
**200** `{"success": true}` · **404** if missing.

Example:
```bash
curl -X POST http://127.0.0.1:8000/api/characters -H "Content-Type: application/json" \
  -d '{"character":{"name":"Elder Wu","slug":"","type":"temporary","micro_summary":"Strict outer-sect elder"}}'
```

## Scenes (locations)

Same contract as characters, with the body key `scene` and model `Scene`:
`GET /api/scenes` · `POST /api/scenes` (`{"scene": Scene}`) · `PUT /api/scenes/{slug}` · `DELETE /api/scenes/{slug}`. 404 messages say `Scene '{slug}' not found`. POST normalises the slug the same way (**422** `Location name must contain at least one letter or digit`) and returns **409** `Scene '{existing}' already exists` for a taken or equivalent slug.

## World settings

### `GET /api/world` → **200** `WorldSettings` (defaults if missing)
### `PUT /api/world`
Body: `{"settings": WorldSettings}` → **200** echoes settings. Full replace.

## Chapters

### `GET /api/chapters`
**200** `Chapter[]` sorted by `chapter_number`, with **`full_text` set to `""`** (summaries and metadata are kept). No `response_model` is declared.

### `GET /api/chapters/{number}`
**200** full `Chapter` including `full_text` · **404** `Chapter {n} not found` · **422** if `number` is not an int.

## Generation

### `POST /api/generate-chapter` — **SSE**
Body:
```json
{"plot": "Xiao Fan discovers a hidden technique in the cave…", "chapter_number": 3,
 "review": true, "tagged_characters": ["xiao_fan"], "tagged_scenes": ["azure_cave"]}
```
Only `plot` is required. Optional fields:
- `chapter_number` (default: highest existing + 1). Passing an existing number **overwrites** that chapter.
- `review` (default `false`, plan 019): stop after step 6, keep the chapter as the draft `data/draft.json`, and end with `draft_complete` instead of running step 7. Approve it with `POST /api/draft/approve`. Without `review` the pipeline runs to `complete` as before, but it also saves the draft after step 6 and deletes it in step 7. So if step 7 fails, the chapter is kept as a draft and the stream ends with `error` + `draft_saved: true` (KI-041).
- `tagged_characters` / `tagged_scenes` (default `[]`, plan 019): slugs the author picked with `@`. Each one that exists is treated as an existing primary character / main location in step 2, so the writer gets its full profile. Unknown slugs are ignored.

**One LLM job at a time** (plan 010, KI-031; plan 019): while a generation, a draft approval or a rewrite runs, a request gets **409** (`A chapter is already being generated. Wait for it to finish or cancel it.`, or the approval/rewrite message). The guard for generations is the running pipeline task itself, so it is released as soon as the generation completes, fails or is cancelled. If the client disconnects (tab closed, curl aborted), the generation is cancelled too, and nothing is saved unless step 6 finished (draft) or step 7 ran (chapter).

**One draft at a time** (plan 019): while `data/draft.json` exists, a request gets **409** `A draft of chapter N is waiting for review. Approve or discard it first.`

Response: `200`, `Content-Type: text/event-stream`, headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive`.
The body is a sequence of `data: {json}\n\n` lines. The full event contract is in [02 §W3.4](02-workflows.md#w34-sse-event-contract-backend--frontend). Example stream:

```text
data: {"type": "status", "step": 1, "message": "Analyzing plot..."}

data: {"type": "status", "step": 1, "message": "Plot analyzed. Tone: tense. Entities found: 3"}

data: {"type": "status", "step": 2, "message": "Resolving characters and scenes..."}

data: {"type": "new_character", "name": "Elder Wu", "slug": "elder_wu"}

data: {"type": "token", "content": "Thunder rolled across"}

data: {"type": "complete", "chapter_number": 3, "title": "The Hidden Scroll", "word_count": 2011,
       "characters": ["xiao_fan"], "scenes": ["azure_cave"], "micro_summary": "…"}
```
With `"review": true` the stream ends after step 6 with:
```text
data: {"type": "draft_complete", "chapter_number": 3, "full_text": "Thunder rolled across…", "word_count": 2011,
       "characters": ["xiao_fan"], "scenes": ["azure_cave"], "new_characters": ["elder_wu"], "new_scenes": []}
```
Errors **do not** change the HTTP status (it is already 200). They arrive as `{"type":"error","message":"…"}`. Uncaught pipeline exceptions and a failed step 7 add `"detail": "traceback…"`; a failed step 7 also adds `"draft_saved": true` (plan 019). Writer errors carry `message` only. A cancelled generation ends with `{"type": "error", "message": "Generation cancelled", "cancelled": true}`.

Consuming it from a shell:
```bash
curl -N -X POST http://127.0.0.1:8000/api/generate-chapter -H "Content-Type: application/json" -d '{"plot":"A storm hits the lab."}'
```

### `POST /api/generate-chapter/cancel`
No body. Cancels the running generation and waits up to 5 s for it to stop, so a new generation is accepted as soon as this returns (plan 010).
**200** `{"cancelled": true}` if a generation was running, `{"cancelled": false}` if none was. The generation's own stream then ends with the cancelled `error` event above. Profiles already created in step 3 stay. A generation cancelled during steps 1–6 saves nothing; one cancelled during step 7 leaves the draft. Draft approvals and rewrites can't be cancelled.

## Draft review (plan 019)

A draft is a written chapter waiting for review, stored in `data/draft.json` (one at a time). `Draft`:
```json
{"chapter_number": 3, "plot_input": "…", "full_text": "…", "title": "",
 "characters_featured": ["xiao_fan"], "scenes_featured": ["azure_cave"],
 "new_characters": ["elder_wu"], "new_scenes": [], "created_at": "ISO", "updated_at": "ISO"}
```
`new_characters` / `new_scenes` are the profiles step 3 created for this draft (the UI offers to delete them on discard).

### `GET /api/draft`
**200** `Draft`, or **200** `null` when no draft waits (a normal state, not an error). An unreadable file is logged and treated as no draft.

### `PUT /api/draft`
Body: `{"full_text": "…", "title": "…"}` (`title` optional, stripped; empty = the specialist suggests one at approval). Saves both and `updated_at`.
**200** `Draft` · **404** `No draft is waiting for review` · **409** while the draft is being approved.

### `DELETE /api/draft`
**200** `{"success": true}` · **404** if none · **409** while the draft is being approved. Profiles created in step 3 are not deleted.

### `POST /api/draft/rewrite`
Body: `{"before": "text before the selection", "passage": "the selection", "after": "text after it", "instruction": "make it angrier"}`. The editor sends the text pieces, not offsets (JavaScript and Python count string positions differently).
Calls the **writer** model (`writer.revise_passage`, `num_ctx` 32768, `temperature` 0.7, `keep_alive` 300) with the draft's plot, the surrounding text and the instruction. Nothing is saved: the client applies the replacement and autosaves.
**200** `{"replacement": "new passage"}` · **404** no draft · **409** while another LLM job runs · **422** `Select the passage to rewrite` / `Describe how the passage should change` · **500** `Rewrite failed: …` (Ollama error, or an empty reply).

### `POST /api/draft/approve`
Body: `{"full_text": "final text", "title": "optional"}`, both optional (`null` keeps the saved value).
Saves them into the draft, then runs step 7 (`finalize_chapter`):
1. Summarises the chapter with the specialist.
2. Saves `data/chapters/NNN.json`.
3. Updates the featured characters and locations and `total_chapters`.
4. Deletes the draft.

**200** `{"chapter": Chapter, "warnings": ["Could not update character 'x': …"]}` · **404** no draft · **409** while another LLM job runs · **422** `The draft is empty` · **500** `Could not finalize the chapter: … The draft is kept: approve it again to retry.` (the sent edits are kept).

## Refinement (LLM builders)

Common body (`RefineRequest`):
```json
{"description": "rough free text", "name": "optional name hint", "existing_slug": "optional slug to merge into"}
```
The response arrives when the specialist finishes (seconds to minutes). The call is awaited (async client), so the server keeps answering other requests meanwhile (KI-005, fixed in plan 005). The specialist stays loaded for 5 idle minutes afterwards (`keep_alive=300`, plan 013; was `-1`, forever, KI-029). If the `ollama` Python package is missing, these return **500**.

### `POST /api/refine/character`
- `existing_slug` given **and** found → truthy LLM fields overwrite the existing character, except `slug`, `name` and `first_appeared_chapter`. Saved. **200** merged `Character`.
  Only known fields are merged, and the merged record is validated (with the coercion described in [05](05-data-model-and-storage.md)) before saving. If it still fails, **500** `Could not merge character: …` and nothing is saved. (Before plan 009 the merge used `setattr` without validation, so an invalid value was saved and the character vanished, KI-016.) The same applies to scenes.
- Otherwise → `Character(**llm_result)` with `slug = make_slug(LLM name)` (never the LLM's slug, plan 007) → created → **200**. **422** if the profile has no usable name. If that slug is already taken → **409** `Could not create character: Character 'x' already exists`, and nothing is written (use **Update Existing** / `existing_slug` instead).
- **500** `Failed to generate character profile` (empty LLM result) · **500** `Could not create character: …` (validation failure that coercion can't fix, e.g. a missing name; `type:"supporting"` or an int `age` are coerced since plan 009). Transport errors (Ollama down) → **500** Internal Server Error.

### `POST /api/refine/scene`
Same as above for `Scene`.

### `POST /api/refine/world`
`name`/`existing_slug` are ignored. The merge rules (list union, non-empty string overwrite) are in [02 §W5](02-workflows.md#w5--world-build-refine--merge).
**200** merged `WorldSettings` · **500** `Failed to refine world description`.

## Model management

### `GET /api/models`
```json
{
  "installed": ["gemma3:12b", "phi4-mini:3.8b"],
  "recommended": [
    {"name":"gemma3:12b","size":"~7 GB","quality":"Best","note":"Recommended writer","installed":true},
    {"name":"llama3.1:8b","size":"~5 GB","quality":"Great","note":"Fast, good quality","installed":false}
  ],
  "ollama_running": true,
  "ollama_error": null
}
```
The backend asks `{OLLAMA_BASE_URL}/api/tags`: the `OLLAMA_HOST` environment variable, or `http://127.0.0.1:11434`, resolved exactly as ollama-python does for generation (plan 015, KI-033; before, list and pull always used `localhost:11434`). `POST /api/models/pull` uses the same address.
If Ollama is unreachable: `installed: []`, `ollama_running: false`, `ollama_error: "Cannot reach Ollama at http://127.0.0.1:11434: …"` (still **200**; the Settings status line shows this text).
`installed` on a recommended entry is true only if Ollama lists that exact model; a name without a tag counts as `:latest`. Before plan 012 any installed tag of the same family counted (e.g. `gemma3:4b` made `gemma3:12b` "installed", KI-020).

### `POST /api/models/pull` — **SSE**
Body `{"model": "llama3.1:8b"}` (**400** `model name required` if empty). The body is an untyped `dict`.
Events (no `type` field; keyed by `status`):
```text
data: {"status": "pulling manifest", "percent": 0, "total": 0, "completed": 0}
data: {"status": "pulling 8eeb52dfb3bb", "percent": 42, "total": 4920000000, "completed": 2066400000}
data: {"status": "success", "model": "llama3.1:8b"}
data: {"status": "error", "message": "…"}
```
The stream ends with exactly one `success` or `error` (plan 010, KI-019):
- `success` only after Ollama itself sends `{"status": "success"}`.
- `error` when Ollama answers with a non-200 status (`"Ollama returned 404: pull model manifest: file does not exist"`), sends an `{"error": …}` line (its text is the message), ends without confirming success (`"Ollama ended the download without confirming success"`), or can't be reached (the transport error text, e.g. `"All connection attempts failed"`).

Before plan 010 every pull ended with `success`, even a failed one.

## Export

### `GET /api/export/{fmt}`
`fmt` ∈ `txt` | `md` (**400** otherwise). **200** download: `text/plain` or `text/markdown` (`charset=utf-8`), with `Content-Disposition: attachment; filename="…"`, or `filename*=utf-8''…` for non-ASCII names.
Filename: the title with spaces and the characters Windows forbids (`< > : " / \ | ? *`) turned into `_`, trailing dots/spaces dropped, `novel` if nothing is left; e.g. `Test: A/B?` → `Test__A_B_.txt`.
The text is built in memory with LF line endings; nothing is written to disk (plan 015, KI-017; before, a copy was written to `data/`, and forbidden characters gave **500**).
