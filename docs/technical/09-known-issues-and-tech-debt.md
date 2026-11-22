# 09 — Known Issues & Technical Debt

> **Baseline:** v1.0.0, analysed 2026-11-22 by reading every source file. Items marked **Verified ✔** were also checked by execution (Pydantic validation against the real models, import test).
> **IDs are permanent.** Reference them in plans (`docs/ai/plans/`), commits and CHANGELOG entries, e.g. "Fixed: KI-001". When an issue is fixed, set its **Status** to `Fixed in vX.Y.Z` (do not delete the row).

Severity: **High** = broken feature or data loss · **Medium** = wrong behaviour, a risk, or a significant limitation · **Low** = cosmetic, dead code, or minor.

## Summary

| ID | Sev | Area | Title | Status |
|---|---|---|---|---|
| KI-001 | High | Frontend↔API | Manual character/location create & edit always fail (422: missing `slug`) ✔ | Fixed in Unreleased [plan 003] |
| KI-002 | High | Frontend | `apiPost` returns `Response`; refine handlers treat it as JSON. World modal can wipe world settings | Fixed in Unreleased [plan 003] |
| KI-003 | High | Setup | Server fails to start without `ollama`; `app/start.bat` only checks `fastapi` ✔ | Open |
| KI-004 | High | Setup | `app/requirements.txt` pins are stale/incompatible (ollama 0.3.3 vs ≥0.4 API; pydantic 2.7.1 vs Py3.13+; httpx missing) | Open |
| KI-005 | Medium | Backend | Synchronous `ollama.chat` blocks the event loop during specialist calls | Open |
| KI-006 | Medium | Frontend | `Alt+S` opens Settings without loading models, so empty model names can be saved | Open |
| KI-007 | Medium | Frontend | Settings save resets `total_chapters`/`created_at` | Open |
| KI-008 | Medium | Frontend/Pipeline | Next chapter number = count+1 (not max+1), so gaps cause overwrites | Open |
| KI-009 | Medium | Data | Inconsistent slugs (LLM-provided, verbatim) lead to duplicates and odd filenames | Open |
| KI-010 | Medium | Security | Slugs used as filenames without validation; CORS `*` on an unauthenticated API | Open |
| KI-011 | Medium | Security/Frontend | Unescaped `innerHTML` in world snapshot and model browser | Open |
| KI-012 | Low | Pipeline | Step 5 `predict_updates` result unused (an LLM call made only to unload VRAM) | Open |
| KI-013 | Low | Pipeline | `scene_updates`, `scene_profiles`, `novel_meta` arg ignored; scenes never evolve | Open |
| KI-014 | Medium | Pipeline | Post-write summariser sees only the first 3000 chars of the chapter | Open |
| KI-015 | Low | Pipeline | `estimated_chapters > 1` crashes when the LLM returns a string | Open |
| KI-016 | Medium | Pipeline/Backend | LLM output that fails validation (type enum, int age, missing slug) silently drops entities; refine *merge* saves invalid values unvalidated, so the entity becomes unloadable; prompt template biases `type: main` ✔ | Open |
| KI-017 | Low | Backend | Export writes into `data/`; titles with illegal filename chars fail | Open |
| KI-018 | Low | Frontend | `warning` SSE events have no handler (silently dropped) | Open |
| KI-019 | Medium | Backend | Model pull reports `success` even when Ollama returned an error | Open |
| KI-020 | Low | Backend | "Installed" detection matches any tag of the same model family | Open |
| KI-021 | Low | Frontend | API base URL hard-coded to `http://127.0.0.1:8000/api` | Open |
| KI-022 | Low | Repo | `__pycache__/*.pyc` (cpython-313) committed despite `.gitignore` | Resolved by plan 002 once the move is committed (Unreleased) |
| KI-023 | Low | Docs/UI | README architecture section wrong; UI copy promises "Shift+click" model selection | README part fixed in Unreleased; UI copy open |
| KI-024 | Low | Frontend | Pipeline panel fade/error styles never reset between runs | Open |
| KI-025 | Medium | Quality | No tests, no linting, no CI, no logging | Open |
| KI-026 | Low | Data | Non-atomic writes; corrupt files silently skipped | Open |
| KI-027 | Medium | Frontend | Edit modals do full replace, so chapter tracking fields reset to 1 (once KI-001 is fixed) | Fixed in Unreleased [plan 003] (UI round-trips all fields; the PUT API stays a full replace) |
| KI-028 | Low | Frontend | Frontend fallback specialist model (`gemma3:12b`) ≠ backend default (`phi4-mini:3.8b`) | Open |
| KI-029 | Low | Backend | Refine endpoints keep the specialist resident in VRAM indefinitely (`keep_alive=-1`) | Open |
| KI-030 | Low | Repo | Sample/user data committed in `data/`; `total_chapters: 1` with no chapters | Open |
| KI-031 | Medium | Backend | No concurrency guard or cancel for generations | Open |
| KI-032 | Low | Frontend | Minor UI glitches (Full View tags empty after generation; first chunk containing `\n\n` delayed; Alt shortcuts fail with Caps Lock) | Open |
| KI-033 | Low | Config | `OLLAMA_HOST` affects generation but not model list/pull (hard-coded URLs) | Open |
| KI-034 | Low | Docs | "Fully offline" claim, but fonts load from Google Fonts | Open |
| KI-035 | Low | Frontend | Desktop-only layout (no responsive CSS) | Open (design limitation) |
| KI-036 | Medium | Backend | Create silently overwrites an existing character/location with the same derived slug (no 409) ✔ | Fixed in Unreleased [plan 004] |
| KI-037 | Low | Frontend | Streaming text cursor `▍` never hides (CSS `display: inline` overrides `[hidden]`) ✔ | Open |
| KI-038 | Low | Backend | A name without letters/digits (e.g. `???`) gets an empty slug: saved as `.json`, and its card can't be edited or deleted ✔ | Open |

---

## Details

### KI-001 — Manual character/location create & edit always fail (HTTP 422) · High · Verified ✔
- **Status: Fixed in Unreleased [plan 003].** Fix option (a): `saveCharacter`/`saveScene` now send `slug: state._editing…Slug || ''`, so the server derives the slug on create and takes the path slug on edit. The API contract is unchanged (a body without `slug` still gets 422). Verified in a sandbox through the UI and with curl. The evidence below describes the v1.0.0 code.
- **Evidence:** `saveCharacter` builds the payload without `slug` (`app/frontend/app.js:727-741`); `saveScene` likewise (`app.js:862-871`). `Character.slug` and `Scene.slug` are required (`app/backend/models.py:13`, `:32`). Validating that exact payload shape raises `character.slug Field required`. The fallback `if not char.slug` in `main.py:72`/`:105` never runs, because validation fails first. PUT fails the same way: the body is validated before the handler runs.
- **Impact:** The **+ New Character / + New Location** buttons, card **Edit**, `Alt+N` and profile **Edit** all fail with a toast "Failed to save … 422".
- **Fix options:** (a) the frontend sends `slug: state._editingCharSlug || ''`; or (b) make `slug: str = ""` in the models (safer, fixes all clients), keeping the server-side derivation. Do the same for scenes. Combine with KI-027.

### KI-002 — Refine handlers mishandle `apiPost` result; world wipe · High
- **Status: Fixed in Unreleased [plan 003].** `apiPost` now returns `res.json()` like the other helpers. `saveCharacter`/`saveScene` no longer check `res.ok` (`apiPost` already throws on non-2xx). Verified in a sandbox: the Build tabs show the real name, and World Build → World Settings → Save keeps the merged values. The evidence below describes the v1.0.0 code.
- **Evidence:** `apiPost` returns `res` (`app.js:135`), while `apiGet`/`apiPut` return JSON. `refineCharacter` (`:1528`), `refineScene` (`:1575`) and `refineWorld` (`:1614`) use the return value as parsed data.
- **Impact:** The status reads "Created: undefined". `state.world` becomes a `Response`, so the world snapshot shows "No world settings yet". **Opening World Settings and saving afterwards overwrites `world_settings.json` with empty values (data loss).**
- **Fix:** make `apiPost` return `res.json()`, and update the two callers that check `res.ok` (`saveCharacter`/`saveScene`). Or add `await res.json()` in the refine handlers.

### KI-003 — Server fails to start without `ollama`; launcher check too narrow · High · Verified ✔
- **Evidence:** `app/backend/agents/writer.py:5` does `import ollama` unguarded. `import main` → `ModuleNotFoundError: No module named 'ollama'` (reproduced 2026-11-22 on Python 3.14 with FastAPI installed). `app/start.bat:39` probes only `import fastapi`.
- **Fix:** have `app/start.bat` probe all required modules (`import fastapi, uvicorn, pydantic, httpx, ollama`), and/or guard the import in `writer.py` like `specialist.py` does, yielding a clear error event.

### KI-004 — Stale / incompatible dependency pins · High
- **Evidence:** The code uses attribute access on Ollama responses (`specialist.py:54` `response.message.content`, `writer.py:59` `chunk.message.content`). ollama-python introduced typed (attribute-accessible) responses in 0.4.0; 0.3.x returns plain dicts. `app/requirements.txt` pins `ollama==0.3.3`. `pydantic==2.7.1` predates Python 3.13 wheels, yet the committed bytecode is cpython-313. `httpx` is imported in `main.py:7` but not listed. `aiofiles` and `python-multipart` are unused.
- **Note:** The 0.3.3 incompatibility follows from the ollama-python API history and was not executed here (ollama is not installed on the analysis machine).
- **Fix:** replace with tested lower bounds, e.g. `fastapi>=0.111`, `uvicorn[standard]>=0.30`, `pydantic>=2.7,<3`, `httpx>=0.27`, `ollama>=0.4,<1`. Drop the unused packages. Document the tested Python versions.

### KI-005 — Event loop blocked by synchronous specialist calls · Medium
- **Evidence:** `specialist._call` uses `ollama.chat` (sync) and is called from the async generator `run_pipeline` and from async refine routes.
- **Impact:** While a specialist call runs (seconds to minutes), the server cannot answer any request (UI reloads, health, model list).
- **Fix:** `await asyncio.to_thread(specialist.fn, …)` at the call sites, or switch the specialist to `ollama.AsyncClient`.

### KI-006 — `Alt+S` Settings without model list · Medium
- **Evidence:** Model loading is attached only to the `#btn-settings` click (`app.js:1878-1887`). `Alt+S` calls `openSettingsModal()` directly (`:1400-1403`). On an empty `<select>`, setting `.value` has no effect, so `saveSettings` sends `""` for both models.
- **Fix:** move the model loading into `openSettingsModal()`.

### KI-007 — Settings save resets counters · Medium
- **Evidence:** `saveSettings` (`app.js:1029-1035`) omits `total_chapters`/`created_at`, so the Pydantic defaults (0, "") are persisted by a full-replace PUT.
- **Fix:** send `{...state.novelMeta, ...formValues}` (as `initTitleEdit` already does).

### KI-008 — Chapter number from count instead of max · Medium
- **Evidence:** `generateChapter` sends `state.chapters.length + 1` (`app.js:436`); the hint uses the same rule (`:358`). The backend's correct `get_next_number()` (max+1) is bypassed because a number is always sent.
- **Fix:** omit `chapter_number` (let the backend decide) or compute max+1. Consider refusing to overwrite unless an explicit "regenerate" flag is set.

### KI-009 — Inconsistent slugs · Medium
- **Evidence:** `make_slug` gives `snake_case` (`character_manager.py:12-16`). Prompts ask the LLM for snake_case slugs, but LLM slugs are saved verbatim (`chapter_pipeline.py:80`, `main.py:334`/`:361`). The sample data has the hyphenated `xiao-fan-scientist-inventor`.
- **Impact:** duplicates; filenames containing arbitrary characters; resolution depends on LLM fuzzy matching.
- **Fix:** always derive or sanitise slugs server-side (`make_slug(name)`), and de-duplicate against existing names before creating.

### KI-010 — Unvalidated slugs as filenames; open CORS · Medium (security)
- **Evidence:** `_data_dir() / f"{slug}.json"` in managers. The slug comes from URL paths, request bodies or LLM output. On Windows, a backslash in a slug is a path separator for `pathlib`. CORS `allow_origins=["*"]` (`main.py:32-37`) with no authentication means any website open in the browser can call these endpoints, including DELETE.
- **Status of exploitability:** not exercised. Risk assessed from code.
- **Fix:** validate slugs against `^[a-z0-9_-]+$` (or ensure `resolved_path.parent == data_dir`). Restrict CORS to the app's own origin.

### KI-011 — Unescaped HTML injection points · Medium (security)
- **Evidence:** `renderWorldSnapshot` interpolates world fields into `innerHTML` (`app.js:1468-1477`). `populateModelSelects` (`:1675`) and `renderModelBrowser` (`:1734-1753`) interpolate model names. World fields can come from LLM output.
- **Fix:** wrap the values with `escHtml()`, or build the nodes with `textContent`.

### KI-012 — Unused `predict_updates` call · Low
- **Evidence:** `update_predictions` (`chapter_pipeline.py:160`) is never read. The call exists to send `keep_alive=0`.
- **Fix:** replace with an explicit unload (`ollama.generate(model, keep_alive=0)` with an empty prompt, or `ollama.chat(..., keep_alive=0)` with a minimal message). This saves one full LLM round trip per chapter.

### KI-013 — Ignored outputs and parameters · Low
- `post_write_update(..., scene_profiles=[])` is always empty and unused. The LLM's `scene_updates` are never applied (`chapter_pipeline.py:193+`). The `novel_meta` arg of `analyze_plot` is unused. `select_context` largely duplicates the hard-coded fallback rules.

### KI-014 — Summaries based on the first 3000 characters only · Medium
- **Evidence:** `specialist.py:245` `chapter_text[:3000]`. A ~2000-word chapter is ~11–12k characters, so roughly the last ¾, **including the ending hook**, is never summarised, although the prompt asks for an "ending hook" in `full_summary`.
- **Impact:** continuity relies on summaries of chapter openings only.
- **Fix:** pass the full text (the specialist's `num_ctx` is 8192, which fits ~2000 words), or the head plus the tail.

### KI-015 — Type-unsafe LLM fields · Low
- **Evidence:** `if estimated_chapters > 1` (`chapter_pipeline.py:51`) raises a `TypeError` for `"2"`/`null`, which aborts the whole pipeline. Similar latent risks: `.get()` results used as lists or dicts without type checks.
- **Fix:** coerce or validate specialist outputs (small Pydantic models per call, or helper coercers).

### KI-016 — Entities silently dropped on validation failure · Medium · Verified ✔
- **Evidence:** `Character(type="supporting")` and `Character(age=17)` both raise (verified). In step 3 these become `warning` events, which the UI ignores (KI-018). In the refine **create** branch they become HTTP 500 (`main.py:333-338`, `356-360`). **Worse, in the refine *merge* branch** (`existing_slug` found), values are applied with `setattr` (`main.py:329`, `:356`) without validation (no `validate_assignment`), so the invalid value is **saved** and the endpoint returns 200. The file then fails to load: `get_all()` silently skips it (the entity vanishes from the sidebar) and `get_by_slug()` raises (later PUT/merge → 500). Reproduced: `setattr(c, "type", "supporting")` then `model_dump()` then re-construct → `ValidationError`. The step-3 template hard-codes `"type": "main"` (`specialist.py:139`), so auto-discovered characters skew to MAIN CAST.
- **Fix:** normalise LLM output before construction (map unknown types → `temporary`, `str()` the age, derive a missing slug). Pass `format="json"` to Ollama.

### KI-017 — Export side effects · Low
- `main.py:213-217` writes `data/{title}.{fmt}` and leaves it there (e.g. `data/Untitled_Novel.txt`). Characters illegal in Windows filenames cause failures. **Fix:** stream from memory (`Response(content, headers={"Content-Disposition": …})`) and sanitise the filename.

### KI-018 — `warning` SSE ignored · Low
- The pipeline emits `warning` (`chapter_pipeline.py:84,92`), but `generateChapter`'s handler map has no `warning` key. **Fix:** add a handler that shows a warning toast or step log.

### KI-019 — False-success model pulls · Medium
- `pull_model` neither checks `resp.status_code` nor detects `{"error": …}` lines. After the loop it always yields `success` (`main.py:275-296`). **Fix:** check the status, detect the `error` key, and only emit success after a final `{"status":"success"}` from Ollama.

### KI-020 — Family-prefix "installed" detection · Low
- `main.py:254-257`: `inst.startswith(family + ":")` marks every tag of a family as installed. **Fix:** exact match (also treat `name` ≡ `name:latest`).

### KI-021 — Hard-coded API base · Low
- `app.js:6`. **Fix:** `const API = '/api'` (same origin). This also removes the need for CORS.

### KI-022 — Committed bytecode · Low
- At v1.0.0, 14 `.pyc` files under `backend/__pycache__`, `backend/agents/__pycache__`, `backend/managers/__pycache__` and `backend/pipeline/__pycache__` were tracked (committed before `.gitignore` existed).
- **Resolution (plan 002):** the folders moved with the code into `app/backend/…/__pycache__`, where `.gitignore` (`__pycache__/`) excludes them. When the reorganisation is committed, git records the old tracked copies as deleted and never adds the new ones. No `git rm` needed. Verify after the commit with `git ls-files | grep pyc` (expect nothing).

### KI-023 — Documentation/UI copy drift · Low
- README "Architecture" listed non-existent `storage.py`, `pipeline.py`, `ollama.py`, `data/world.json` and "JSON/SQLite" storage → **corrected in [Unreleased]**.
- Still open: the Settings model browser subtitle says "Click a model to set as writer. Shift+click to set as specialist." (`index.html:765`), but only explicit buttons exist. The README recommends `gemma3:12b` for both roles while the default specialist is `phi4-mini:3.8b` (a recommendation, not an error).

### KI-024 — Pipeline UI state not reset · Low
- `completePipeline` sets `opacity: 0.4` (`app.js:658`). `setStepError` sets inline red border/background (`:673-674`). `resetPipeline` clears neither. **Fix:** reset `style.opacity`, `borderColor` and `background` in `resetPipeline`.

### KI-025 — No tests / lint / CI / logging · Medium
- No test files, no linters, no CI workflows. No `logging` usage (`except: pass` in managers hides errors). **Suggested start:** pytest + FastAPI `TestClient` with a stubbed `ollama` module; `ruff`; a `logging` config writing to the console.

### KI-026 — Non-atomic writes; silent skips · Low
- Managers write in place. A crash mid-write corrupts the file, and `get_all()` then hides it. **Fix:** write to a temp file + `os.replace`, and log skipped files.

### KI-027 — Edit = full replace loses untracked fields · Medium
- **Status: Fixed in Unreleased [plan 003]** (UI side, by round-tripping all fields). On edit, `saveCharacter`/`saveScene` send `{...existing, ...form}`, where `existing` is the record in `state`. To keep `state.characters` fresh, the `generateChapter` `complete` handler now also reloads characters, because step 7 updates their profiles on disk. `PUT` is still a full replace for other API clients. Verified in a sandbox: edits kept `first/last` = 3/5 and `first_appeared_chapter` = 4.
- The character modal sends neither `first_appeared_chapter` nor `last_seen_chapter`, so once KI-001 is fixed they will reset to 1 on every edit. Same for the scene's `first_appeared_chapter`. **Fix:** merge the payload into the existing record server-side (PATCH semantics), or round-trip all fields.

### KI-028 — Fallback specialist mismatch · Low
- `app.js:172` and `:1024` fall back to `gemma3:12b` for the specialist; the backend default is `phi4-mini:3.8b` (`models.py:75`).

### KI-029 — Specialist stays resident after refine · Low
- Refine endpoints call `_call` with the default `keep_alive=-1`. **Fix:** use `0` or a finite value (e.g. `120`) for refine calls.

### KI-030 — User/sample data in VCS · Low
- `data/` holds personal novel content plus an export file, and `novel_meta.total_chapters` is 1 with no chapters. **Fix:** ignore `data/` (keep a `data.sample/` or seed on first run).

### KI-031 — No concurrency guard / cancellation · Medium
- Two tabs (or API clients) can generate the same chapter at once. Writes race and can overwrite each other. There is no cancel button. Closing the tab aborts the stream and loses unsaved work. **Fix:** a server-side lock per novel, plus a cancel endpoint or `AbortController` in the UI.

### KI-032 — Minor UI glitches · Low
- After generation, `state.currentChapter` lacks `characters_featured`/`scenes_featured`, so Full View tags are empty (`app.js:523-527`).
- If the very first token chunk contains `\n\n`, its text is held back by the `app.js:489` guard. It appears only when a later chunk containing `\n\n` arrives (lost from the live view if none does). The saved text is unaffected.
- Alt shortcuts compare `e.key === 'g'` etc. (lower case only), so they fail with Caps Lock or Shift.

### KI-033 — Partial `OLLAMA_HOST` support · Low
- ollama-python honours `OLLAMA_HOST`, but `main.py:243,280` hard-code `http://localhost:11434`.

### KI-034 — "Fully offline" claim · Low
- Google Fonts are loaded **twice**: `<link>` tags in `index.html:9-11` and an `@import` in `style.css:6`. The app works offline with fallback fonts. Either self-host the fonts (change both files) or soften the README claim.

### KI-035 — Desktop-only layout · Low (design limitation)
- `style.css` has no `@media` rules. Fixed 280 px sidebars make narrow windows unusable.

### KI-036 — Create silently overwrites an existing entity with the same slug · Medium · Verified ✔
- **Status: Fixed in Unreleased [plan 004].**
  - `character_manager.create()` / `scene_manager.create()` open the file with mode `"x"` (exclusive create). They never overwrite and raise `FileExistsError("Character 'x' already exists")`.
  - A `FileExistsError` handler in `main.py` turns this into **409** for `POST /api/characters` and `/api/scenes`. The refine create branches return 409 explicitly.
  - Pipeline step 3 keeps the existing profile and emits a `warning`.
  - Verified in a sandbox: same name, slug-equivalent name, case-only slug, scenes, refine create, a pipeline collision, and the UI (toast, modal stays open).
  - The evidence below describes the pre-fix code.
- **Evidence:** `create_character`/`create_scene` (`main.py:69-75`, `:102-108`) derive the slug when it is empty, then call `save()` without checking whether `data/…/{slug}.json` already exists. The refine *create* branch (`main.py:328-331`, `:355-358`) and pipeline step 3 (`chapter_pipeline.py:78-92`) save LLM-provided slugs the same way. `docs/technical/04` already documents the overwrite.
- **Reproduced 2026-11-22 [plan 003]:** POST `/api/characters` with `name: "Zz Test Hero"` after the existing `zz_test_hero` had been edited returned 200 and replaced the whole record (type, arc notes, chapters 3/5 → 1/1). Since KI-001 is fixed, this is reachable from **+ New Character** / **+ New Location** whenever a new name slugifies to an existing slug.
- **Fix:** return **409** from POST when the slug exists (and show the message in the UI), or append a numeric suffix. Apply the same check in refine create and pipeline step 3 (where it should fall back to "existing").

### KI-037 — Streaming text cursor never hides · Low · Verified ✔
- **Evidence:** `.text-cursor { display: inline; }` (`style.css:1189-1190`) overrides the browser's `[hidden] { display: none }`. `DOM.textCursor.hidden = true` (`app.js:520`, `:396`) therefore has no effect, and the blinking `▍` stays after a chapter completes and when a past chapter is viewed. Observed 2026-11-22 [plan 003]: `hidden === true` while the computed `display` was `inline`.
- **Fix:** add `.text-cursor[hidden] { display: none; }` next to the rule (the same pattern as `.modal-overlay[hidden]`, `style.css:1299`).

### KI-038 — Names without letters or digits produce an empty slug · Low · Verified ✔
- **Evidence:** `_slugify` (`character_manager.py:12-16`, same in `scene_manager.py`) removes every character outside `[\w\s-]`, so a name like `???` or `!!!` becomes `""`. `POST /api/characters` then saves `data/characters/.json` (200) and lists it with slug `""`. The card's **Edit**/**Delete** call `/api/characters/` with an empty path segment, which FastAPI answers with a 307 redirect, so the entity can't be edited or deleted from the UI. Emoji-only names behave the same way (`\w` is Unicode-aware, so CJK/Latin names are fine).
- **Reproduced 2026-11-22 [plan 004]:** the first `???` was saved as `.json`; a second (`!!!`) got 409 `Character '' already exists` (since KI-036's fix).
- **Workaround:** delete `data/characters/.json` (or `data/scenes/.json`) by hand.
- **Fix:** in POST (and refine create / pipeline step 3), reject an empty slug after derivation with 422 ("name needs at least one letter or digit"), or derive a fallback such as `character_<n>`.
