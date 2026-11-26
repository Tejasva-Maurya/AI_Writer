# 09 — Known Issues & Technical Debt

> **Baseline:** v1.0.0, analysed 2026-11-22 by reading every source file. Items marked **Verified ✔** were also checked by execution (Pydantic validation against the real models, import test, sandbox runs).
> **Statuses are kept current.** Last updated 2026-11-26, through plan 022. The Summary splits **Open** from **Fixed**; fixed issues also carry **✅ Fixed** in their details heading.
> **IDs are permanent.** Reference them in plans (`docs/ai/plans/`), commits and CHANGELOG entries, e.g. "Fixed: KI-001". When an issue is fixed, move its row to the **Fixed** table, set **Status** to `Fixed in Unreleased [plan NNN]` (renamed to `Fixed in vX.Y.Z` at release), and add `· ✅ Fixed …` to its details heading. Never delete a row or a details section.

Severity: **High** = broken feature or data loss · **Medium** = wrong behaviour, a risk, or a significant limitation · **Low** = cosmetic, dead code, or minor.

## Summary

**At a glance:** 0 open · 40 fixed in v2.0.0 (KI-001 to KI-040) · 4 fixed in Unreleased (KI-041 to KI-044).

### Open (0)

None. A new defect gets the next ID, KI-045.

### Fixed (44)

Kept for history (IDs are permanent). The titles describe the defect as it was.

| ID | Sev | Area | Title | Status |
|---|---|---|---|---|
| KI-001 | High | Frontend↔API | Manual character/location create & edit always fail (422: missing `slug`) ✔ | Fixed in v2.0.0 [plan 003] |
| KI-002 | High | Frontend | `apiPost` returns `Response`; refine handlers treat it as JSON. World modal can wipe world settings | Fixed in v2.0.0 [plan 003] |
| KI-003 | High | Setup | Server fails to start without `ollama`; `app/start.bat` only checks `fastapi` ✔ | Fixed in v2.0.0 [plan 005] |
| KI-004 | High | Setup | `app/requirements.txt` pins are stale/incompatible (ollama 0.3.3 vs ≥0.4 API; pydantic 2.7.1 vs Py3.13+; httpx missing) | Fixed in v2.0.0 [plan 005] |
| KI-005 | Medium | Backend | Synchronous `ollama.chat` blocks the event loop during specialist calls | Fixed in v2.0.0 [plan 005] |
| KI-006 | Medium | Frontend | `Alt+S` opens Settings without loading models, so empty model names can be saved | Fixed in v2.0.0 [plan 006] |
| KI-007 | Medium | Frontend | Settings save resets `total_chapters`/`created_at` | Fixed in v2.0.0 [plan 006] |
| KI-008 | Medium | Frontend/Pipeline | Next chapter number = count+1 (not max+1), so gaps cause overwrites | Fixed in v2.0.0 [plan 006] |
| KI-009 | Medium | Data | Inconsistent slugs (LLM-provided, verbatim) lead to duplicates and odd filenames | Fixed in v2.0.0 [plan 007] |
| KI-010 | Medium | Security | Slugs used as filenames without validation; CORS `*` on an unauthenticated API | Fixed in v2.0.0 [plan 007] |
| KI-011 | Medium | Security/Frontend | Unescaped `innerHTML` in world snapshot and model browser | Fixed in v2.0.0 [plan 007] |
| KI-012 | Low | Pipeline | Step 5 `predict_updates` result unused (an LLM call made only to unload VRAM) | Fixed in v2.0.0 [plan 008] |
| KI-013 | Low | Pipeline | `scene_updates`, `scene_profiles`, `novel_meta` arg ignored; scenes never evolve | Fixed in v2.0.0 [plan 008] |
| KI-014 | Medium | Pipeline | Post-write summariser sees only the first 3000 chars of the chapter | Fixed in v2.0.0 [plan 008] |
| KI-015 | Low | Pipeline | `estimated_chapters > 1` crashes when the LLM returns a string | Fixed in v2.0.0 [plan 009] |
| KI-016 | Medium | Pipeline/Backend | LLM output that fails validation (type enum, int age, missing slug) silently drops entities; refine *merge* saves invalid values unvalidated, so the entity becomes unloadable; prompt template biases `type: main` ✔ | Fixed in v2.0.0 [plan 009] |
| KI-017 | Low | Backend | Export writes into `data/`; titles with illegal filename chars fail ✔ | Fixed in v2.0.0 [plan 015] |
| KI-018 | Low | Frontend | `warning` SSE events have no handler (silently dropped) | Fixed in v2.0.0 [plan 009] |
| KI-019 | Medium | Backend | Model pull reports `success` even when Ollama returned an error ✔ | Fixed in v2.0.0 [plan 010] |
| KI-020 | Low | Backend | "Installed" detection matches any tag of the same model family ✔ | Fixed in v2.0.0 [plan 012] |
| KI-021 | Low | Frontend | API base URL hard-coded to `http://127.0.0.1:8000/api` | Fixed in v2.0.0 [plan 007] |
| KI-022 | Low | Repo | `__pycache__/*.pyc` (cpython-313) committed despite `.gitignore` | Fixed in v2.0.0 [plan 002] (no `.pyc` tracked on `main`, verified 2026-11-22) |
| KI-023 | Low | Docs/UI | README architecture section wrong; UI copy promises "Shift+click" model selection | Fixed in v2.0.0 [plan 001] (README) and [plan 014] (UI copy, user-guide model recommendation) |
| KI-024 | Low | Frontend | Pipeline panel fade/error styles never reset between runs ✔ | Fixed in v2.0.0 [plan 011] |
| KI-025 | Medium | Quality | No tests, no linting, no CI, no logging ✔ | Fixed in v2.0.0 [plan 016] |
| KI-026 | Low | Data | Non-atomic writes; corrupt files silently skipped ✔ | Fixed in v2.0.0 [plan 016] |
| KI-027 | Medium | Frontend | Edit modals do full replace, so chapter tracking fields reset to 1 (once KI-001 is fixed) | Fixed in v2.0.0 [plan 003] (UI round-trips all fields; the PUT API stays a full replace) |
| KI-028 | Low | Frontend | Frontend fallback specialist model (`gemma3:12b`) ≠ backend default (`phi4-mini:3.8b`) ✔ | Fixed in v2.0.0 [plan 012] |
| KI-029 | Low | Backend | Refine endpoints keep the specialist resident in VRAM indefinitely (`keep_alive=-1`) ✔ | Fixed in v2.0.0 [plan 013] |
| KI-030 | Low | Repo | Sample/user data committed in `data/`; `total_chapters: 1` with no chapters | Fixed in v2.0.0 [plan 017] (`data/` untracked and git-ignored; older commits still contain it) |
| KI-031 | Medium | Backend | No concurrency guard or cancel for generations ✔ | Fixed in v2.0.0 [plan 010] |
| KI-032 | Low | Frontend | Minor UI glitches (Full View tags empty after generation; first chunk containing `\n\n` delayed; Alt shortcuts fail with Caps Lock) ✔ | Fixed in v2.0.0 [plan 013] |
| KI-033 | Low | Config | `OLLAMA_HOST` affects generation but not model list/pull (hard-coded URLs) ✔ | Fixed in v2.0.0 [plan 015] |
| KI-034 | Low | Docs | "Fully offline" claim, but fonts load from Google Fonts ✔ | Fixed in v2.0.0 [plan 014] (fonts self-hosted) |
| KI-035 | Low | Frontend | Desktop-only layout (no responsive CSS) | Fixed in v2.0.0 [plan 017] (CSS media queries) |
| KI-036 | Medium | Backend | Create silently overwrites an existing character/location with the same derived slug (no 409) ✔ | Fixed in v2.0.0 [plan 004] |
| KI-037 | Low | Frontend | Streaming text cursor `▍` never hides (CSS `display: inline` overrides `[hidden]`) ✔ | Fixed in v2.0.0 [plan 011] |
| KI-038 | Low | Backend | A name without letters/digits (e.g. `???`) gets an empty slug: saved as `.json`, and its card can't be edited or deleted ✔ | Fixed in v2.0.0 [plan 007] |
| KI-039 | Low | Frontend | Multi-chapter notice never hides (CSS `display: flex` overrides `[hidden]`) ✔ | Fixed in v2.0.0 [plan 011] |
| KI-040 | High | Backend | `main.py` does not parse on Python 3.11 (backslash inside an f-string expression, from plan 015) ✔ | Fixed in v2.0.0 [plan 016] |
| KI-041 | Medium | Pipeline | A failure in step 7 (summary) loses the chapter that was just written ✔ | Fixed in Unreleased [plan 019] |
| KI-042 | Medium | Pipeline/Backend | Profile and world edits saved while step 7 or a world refine runs are overwritten (a deleted profile is written back) ✔ | Fixed in Unreleased [plan 020] |
| KI-043 | Medium | Pipeline | Regenerating an earlier chapter lists the later chapters (and the old version) in "STORY SO FAR" ✔ | Fixed in Unreleased [plan 022] |
| KI-044 | Medium | Pipeline | Regenerating an earlier chapter rolls profiles back (last seen, arc notes, level, relationships, location significance) ✔ | Fixed in Unreleased [plan 022] |

---

## Details

### KI-001 — Manual character/location create & edit always fail (HTTP 422) · High · Verified ✔ · ✅ Fixed in v2.0.0 (plan 003)
- **Status: Fixed in v2.0.0 [plan 003].** Fix option (a): `saveCharacter`/`saveScene` now send `slug: state._editing…Slug || ''`, so the server derives the slug on create and takes the path slug on edit. The API contract is unchanged (a body without `slug` still gets 422). Verified in a sandbox through the UI and with curl. The evidence below describes the v1.0.0 code.
- **Evidence:** `saveCharacter` builds the payload without `slug` (`app/frontend/app.js:727-741`); `saveScene` likewise (`app.js:862-871`). `Character.slug` and `Scene.slug` are required (`app/backend/models.py:13`, `:32`). Validating that exact payload shape raises `character.slug Field required`. The fallback `if not char.slug` in `main.py:72`/`:105` never runs, because validation fails first. PUT fails the same way: the body is validated before the handler runs.
- **Impact:** The **+ New Character / + New Location** buttons, card **Edit**, `Alt+N` and profile **Edit** all fail with a toast "Failed to save … 422".
- **Fix options:** (a) the frontend sends `slug: state._editingCharSlug || ''`; or (b) make `slug: str = ""` in the models (safer, fixes all clients), keeping the server-side derivation. Do the same for scenes. Combine with KI-027.

### KI-002 — Refine handlers mishandle `apiPost` result; world wipe · High · ✅ Fixed in v2.0.0 (plan 003)
- **Status: Fixed in v2.0.0 [plan 003].** `apiPost` now returns `res.json()` like the other helpers. `saveCharacter`/`saveScene` no longer check `res.ok` (`apiPost` already throws on non-2xx). Verified in a sandbox: the Build tabs show the real name, and World Build → World Settings → Save keeps the merged values. The evidence below describes the v1.0.0 code.
- **Evidence:** `apiPost` returns `res` (`app.js:135`), while `apiGet`/`apiPut` return JSON. `refineCharacter` (`:1528`), `refineScene` (`:1575`) and `refineWorld` (`:1614`) use the return value as parsed data.
- **Impact:** The status reads "Created: undefined". `state.world` becomes a `Response`, so the world snapshot shows "No world settings yet". **Opening World Settings and saving afterwards overwrites `world_settings.json` with empty values (data loss).**
- **Fix:** make `apiPost` return `res.json()`, and update the two callers that check `res.ok` (`saveCharacter`/`saveScene`). Or add `await res.json()` in the refine handlers.

### KI-003 — Server fails to start without `ollama`; launcher check too narrow · High · Verified ✔ · ✅ Fixed in v2.0.0 (plan 005)
- **Status: Fixed in v2.0.0 [plan 005].** `agents/writer.py` guards the import like the specialist, and `stream_chapter` yields a clear error when the package is missing. `app/start.bat` runs `DEP_CHECK` (all runtime packages plus `ollama >= 0.4`), installs or upgrades on failure, re-checks, and stops with the manual command if it still fails. Verified: `import main` succeeds without `ollama` (the committed code raised `ModuleNotFoundError`); the server answers `/api/health`; generation ends with "ollama Python package not installed: run pip install -r app/requirements.txt". The launcher block was tested with no ollama, ollama 0.6.3 and ollama 0.3.3. The evidence below describes the v1.0.0 code.
- **Evidence:** `app/backend/agents/writer.py:5` does `import ollama` unguarded. `import main` → `ModuleNotFoundError: No module named 'ollama'` (reproduced 2026-11-22 on Python 3.14 with FastAPI installed). `app/start.bat:39` probes only `import fastapi`.
- **Fix:** have `app/start.bat` probe all required modules (`import fastapi, uvicorn, pydantic, httpx, ollama`), and/or guard the import in `writer.py` like `specialist.py` does, yielding a clear error event.

### KI-004 — Stale / incompatible dependency pins · High · ✅ Fixed in v2.0.0 (plan 005)
- **Status: Fixed in v2.0.0 [plan 005].** `app/requirements.txt` now holds lower bounds: `fastapi>=0.111`, `uvicorn[standard]>=0.30`, `pydantic>=2.9,<3`, `httpx>=0.27`, `ollama>=0.4,<1` (policy D-009). The pydantic floor is **2.9**, not the 2.7 suggested below, because `ollama==0.4.0` itself requires `pydantic>=2.9` (read from the 0.4.0 wheel). `aiofiles` and `python-multipart` are removed. Verified: the 0.4.0 and 0.6.3 sources both provide `AsyncClient.chat(...) -> ChatResponse`; the app runs with ollama 0.6.3; a fresh install on Python 3.14.5 resolves 23 packages, all wheels. The evidence below describes the v1.0.0 file.
- **Evidence:** The code uses attribute access on Ollama responses (`specialist.py:54` `response.message.content`, `writer.py:59` `chunk.message.content`). ollama-python introduced typed (attribute-accessible) responses in 0.4.0; 0.3.x returns plain dicts. `app/requirements.txt` pins `ollama==0.3.3`. `pydantic==2.7.1` predates Python 3.13 wheels, yet the committed bytecode is cpython-313. `httpx` is imported in `main.py:7` but not listed. `aiofiles` and `python-multipart` are unused.
- **Note:** The 0.3.3 incompatibility follows from the ollama-python API history and was not executed here (ollama is not installed on the analysis machine).
- **Fix:** replace with tested lower bounds, e.g. `fastapi>=0.111`, `uvicorn[standard]>=0.30`, `pydantic>=2.7,<3`, `httpx>=0.27`, `ollama>=0.4,<1`. Drop the unused packages. Document the tested Python versions.

### KI-005 — Event loop blocked by synchronous specialist calls · Medium · ✅ Fixed in v2.0.0 (plan 005)
- **Status: Fixed in v2.0.0 [plan 005]** (by the second option below). Every specialist function is `async def` and uses `await ollama.AsyncClient().chat(...)`; the 6 pipeline calls and 3 refine routes await them. Verified with a stub whose specialist call takes 4 s: during a generation plus a refine, 20 requests to `/api/health` and `/api/characters` took at most 0.07 s (the committed code took 14.9 s). The evidence below describes the v1.0.0 code.
- **Evidence:** `specialist._call` uses `ollama.chat` (sync) and is called from the async generator `run_pipeline` and from async refine routes.
- **Impact:** While a specialist call runs (seconds to minutes), the server cannot answer any request (UI reloads, health, model list).
- **Fix:** `await asyncio.to_thread(specialist.fn, …)` at the call sites, or switch the specialist to `ollama.AsyncClient`.

### KI-006 — `Alt+S` Settings without model list · Medium · ✅ Fixed in v2.0.0 (plan 006)
- **Status: Fixed in v2.0.0 [plan 006].** `openSettingsModal` fills both model selects from `state.novelMeta` immediately, then refreshes them (and the model browser) from `loadModels()`. The button and `Alt+S` share this path, and the second `#btn-settings` listener is gone. `saveSettings` falls back to the stored model if a select is empty. Verified in a sandbox: after `Alt+S` both selects held the current models, the browser rendered, and Save kept both names; the button path made no duplicate `/api/models` call. The evidence below describes the v1.0.0 code.
- **Evidence:** Model loading is attached only to the `#btn-settings` click (`app.js:1878-1887`). `Alt+S` calls `openSettingsModal()` directly (`:1400-1403`). On an empty `<select>`, setting `.value` has no effect, so `saveSettings` sends `""` for both models.
- **Fix:** move the model loading into `openSettingsModal()`.

### KI-007 — Settings save resets counters · Medium · ✅ Fixed in v2.0.0 (plan 006)
- **Status: Fixed in v2.0.0 [plan 006].** `saveSettings` sends `{...state.novelMeta, …form}`, and the `complete` handler reloads novel meta, so neither Settings nor the inline title edit can write back an old `total_chapters`. Verified in a sandbox: Settings save and title edit kept `total_chapters` 7 and `created_at`; after a generation raised the count from 3 to 4, a Settings save kept 4. The evidence below describes the v1.0.0 code.
- **Evidence:** `saveSettings` (`app.js:1029-1035`) omits `total_chapters`/`created_at`, so the Pydantic defaults (0, "") are persisted by a full-replace PUT.
- **Fix:** send `{...state.novelMeta, ...formValues}` (as `initTitleEdit` already does).

### KI-008 — Chapter number from count instead of max · Medium · ✅ Fixed in v2.0.0 (plan 006)
- **Status: Fixed in v2.0.0 [plan 006]** (first option below). The UI no longer sends `chapter_number`; the backend uses `get_next_number()` (highest on disk + 1). `nextChapterNumber()` gives the same rule for the hint and the streaming badge, and the badge is set from the `complete` event. API callers can still pass an explicit number to regenerate. Verified in a sandbox with chapters 1 and 3: the hint said 4, the request body was `{plot}` only, `004.json` was created and `003.json` stayed byte-identical. The evidence below describes the v1.0.0 code.
- **Evidence:** `generateChapter` sends `state.chapters.length + 1` (`app.js:436`); the hint uses the same rule (`:358`). The backend's correct `get_next_number()` (max+1) is bypassed because a number is always sent.
- **Fix:** omit `chapter_number` (let the backend decide) or compute max+1. Consider refusing to overwrite unless an explicit "regenerate" flag is set.

### KI-009 — Inconsistent slugs · Medium · ✅ Fixed in v2.0.0 (plan 007)
- **Status: Fixed in v2.0.0 [plan 007].** Every slug the server writes is `make_slug(...)`: POST uses `make_slug(slug or name)`, refine create and pipeline step 3 use `make_slug(profile name)`, never the LLM's slug. Step 2 is canonicalised by `_canonical_entities`: a match by slug or name (ignoring case, `-`/`_` and punctuation) becomes `existing` with the real slug; nameless entries and repeats are dropped. `create()` also refuses a slug equivalent to an existing file stem (409). Verified with a stub that resolved the existing `xiao-fan-scientist-inventor` as "new" `xiao_fan_scientist_inventor`: the committed code created a duplicate file plus `Zz-New-Hero!.json`; the fixed code created only `zz_new_hero`, refused the duplicate profile with a warning, and stored the real slugs in the chapter. A nameless step-2 entry crashed the committed pipeline (`KeyError: 'name'`); the fixed one completes. Existing hyphenated files stay valid. The evidence below describes the v1.0.0 code.
- **Evidence:** `make_slug` gives `snake_case` (`character_manager.py:12-16`). Prompts ask the LLM for snake_case slugs, but LLM slugs are saved verbatim (`chapter_pipeline.py:80`, `main.py:334`/`:361`). The sample data has the hyphenated `xiao-fan-scientist-inventor`.
- **Impact:** duplicates; filenames containing arbitrary characters; resolution depends on LLM fuzzy matching.
- **Fix:** always derive or sanitise slugs server-side (`make_slug(name)`), and de-duplicate against existing names before creating.

### KI-010 — Unvalidated slugs as filenames; open CORS · Medium (security) · ✅ Fixed in v2.0.0 (plan 007)
- **Status: Fixed in v2.0.0 [plan 007].**
  - **Exploit confirmed before the fix** (sandbox copy, 2026-11-23): `DELETE /api/characters/..%5Cnovel_meta` and `DELETE /api/scenes/..%5Cworld_settings` returned 200 and **deleted `data/novel_meta.json` and `data/world_settings.json`**. With CORS `*`, any website open in the browser could have sent them.
  - Managers: every file access goes through `_path(slug)`, which accepts only `[\w-]+` (letters/digits of any script, `_`, `-`); `get_by_slug`/`delete` treat anything else as not found. Now 404, files intact; `..%5C..%5Cx`, `a.b`, `x%2Fy` and a backslash PUT are 404 too.
  - `main.py`: `CORSMiddleware` removed and the UI calls the same-origin `/api` (KI-021). A preflight from `evil.example` now gets 405 with no allow-origin header (was 200 with `*`). A cross-site `text/plain` POST is rejected by FastAPI (no write). `TrustedHostMiddleware` allows only `127.0.0.1`/`localhost`: `Host: evil.example` (DNS rebinding) now gets 400 (was 200).
  - The evidence below describes the v1.0.0 code.
- **Evidence:** `_data_dir() / f"{slug}.json"` in managers. The slug comes from URL paths, request bodies or LLM output. On Windows, a backslash in a slug is a path separator for `pathlib`. CORS `allow_origins=["*"]` (`main.py:32-37`) with no authentication means any website open in the browser can call these endpoints, including DELETE.
- **Status of exploitability:** not exercised. Risk assessed from code.
- **Fix:** validate slugs against `^[a-z0-9_-]+$` (or ensure `resolved_path.parent == data_dir`). Restrict CORS to the app's own origin.

### KI-011 — Unescaped HTML injection points · Medium (security) · ✅ Fixed in v2.0.0 (plan 007)
- **Status: Fixed in v2.0.0 [plan 007].** `renderWorldSnapshot`, `populateModelSelects` and `renderModelBrowser` escape every interpolated value with `escHtml()` (world fields after truncation; model names in text, `value`, `data-model` and the `pb-/pf-/ps-` ids). Verified in the browser pane: `<img onerror>`, `<svg onload>`, `<script>` and `<b>` payloads in world fields, the stored writer model and a fake Ollama model list all rendered as literal text, with no injected elements and no handlers run; **Set Writer** still worked through the escaped `data-model`. The evidence below describes the v1.0.0 code.
- **Evidence:** `renderWorldSnapshot` interpolates world fields into `innerHTML` (`app.js:1481-1490`). `populateModelSelects` (`:1688`) and `renderModelBrowser` (`:1747-1766`) interpolate model names. World fields can come from LLM output.
- **Fix:** wrap the values with `escHtml()`, or build the nodes with `textContent`.

### KI-012 — Unused `predict_updates` call · Low · ✅ Fixed in v2.0.0 (plan 008)
- **Status: Fixed in v2.0.0 [plan 008].** Step 5 calls `specialist.unload(model)` = `AsyncClient().generate(model=model, keep_alive=0)`, Ollama's unload request; `predict_updates` is removed. Verified with the real ollama client (0.4.0 and 0.6.3) against a logging fake Ollama: the request body is exactly `{"model": …, "stream": false, "keep_alive": 0}` (no prompt, nothing generated). In a full run, the committed code made 6 chat generations per chapter, the fixed code 4 plus that unload. A failing unload becomes a `warning` event and the chapter still completes. Not verified: a real Ollama freeing VRAM (no Ollama/GPU here). The evidence below describes the pre-fix code.
- **Evidence:** `update_predictions` (`chapter_pipeline.py:183`) is never read. The call exists to send `keep_alive=0`.
- **Fix:** replace with an explicit unload (`ollama.generate(model, keep_alive=0)` with an empty prompt, or `ollama.chat(..., keep_alive=0)` with a minimal message). This saves one full LLM round trip per chapter.

### KI-013 — Ignored outputs and parameters · Low · ✅ Fixed in v2.0.0 (plan 008)
- **Status: Fixed in v2.0.0 [plan 008].** Step 7 passes the featured scenes' profiles to `post_write_update` (new `SCENE PROFILES` block) and applies `scene_updates`: a featured (main) scene's `significance` is replaced by a non-empty text `new_significance`; non-dict values and non-featured slugs are ignored. `analyze_plot` lost its unused `novel_meta` argument. Step 4 is deterministic: the `select_context` LLM call, which only restated the rules the code applied anyway, is removed. Verified in a full run: the featured scene's significance was updated on disk, an update for a scene not in the chapter was ignored, and a string `scene_updates` changed nothing. The evidence below describes the pre-fix code.
- `post_write_update(..., scene_profiles=[])` is always empty and unused. The LLM's `scene_updates` are never applied (`chapter_pipeline.py:216+`). The `novel_meta` arg of `analyze_plot` is unused. `select_context` largely duplicates the hard-coded fallback rules.

### KI-014 — Summaries based on the first 3000 characters only · Medium · ✅ Fixed in v2.0.0 (plan 008)
- **Status: Fixed in v2.0.0 [plan 008].** `_chapter_excerpt` sends the whole chapter when its estimated size fits ~5000 tokens (¼ token per ASCII char, 1 per other char; the specialist's `num_ctx` is 8192); otherwise the opening (40 %) + `[… middle of the chapter omitted …]` + the ending (60 %), so the ending hook is always included. Verified: a ~2000-word English chapter goes through whole (~3000 tokens); ~7000-word English and 12k-char CJK chapters become opening + ending at ~5000 tokens with the last sentence present. In a full run the summariser prompt contained the chapter's final sentence (committed code: 3979 chars, no ending). The evidence below describes the pre-fix code.
- **Evidence:** `specialist.py:245` `chapter_text[:3000]`. A ~2000-word chapter is ~11–12k characters, so roughly the last ¾, **including the ending hook**, is never summarised, although the prompt asks for an "ending hook" in `full_summary`.
- **Impact:** continuity relies on summaries of chapter openings only.
- **Fix:** pass the full text (the specialist's `num_ctx` is 8192, which fits ~2000 words), or the head plus the tail.

### KI-015 — Type-unsafe LLM fields · Low · ✅ Fixed in v2.0.0 (plan 009)
- **Status: Fixed in v2.0.0 [plan 009].** `_call` always returns a dict. Step 1 coerces `estimated_chapters` (numeric text → int, else 1), `tone` and `entity_mentions` (string lists only). Step 3 iterates only lists of dicts. Step 7 coerces the title and summaries to text (empty title → `Chapter N`) and processes `character_updates` only as dicts. Verified against the committed code with a hostile stub: an analysis that is a JSON list (old: `'list' object has no attribute 'get'`), `estimated_chapters: "2"` (old: `'>' not supported`), and a post-write reply with `chapter_title: null` and list/number summaries (old: **the chapter streamed and was then lost**, `4 validation errors for Chapter`). The fixed code completes all three and saves the chapter. The evidence below describes the pre-fix code.
- **Evidence:** `if estimated_chapters > 1` (`chapter_pipeline.py:74`) raises a `TypeError` for `"2"`/`null`, which aborts the whole pipeline. Similar latent risks: `.get()` results used as lists or dicts without type checks.
- **Fix:** coerce or validate specialist outputs (small Pydantic models per call, or helper coercers).

### KI-016 — Entities silently dropped on validation failure · Medium · Verified ✔ · ✅ Fixed in v2.0.0 (plan 009)
- **Status: Fixed in v2.0.0 [plan 009].** `models.py` coerces wrong-typed values for Character, Scene and WorldSettings (`type` → main/temporary, numbers → text, a string → a one-item list, numeric chapter text → int, …) and Character/Scene use `validate_assignment`. Refine merges validate the merged record before saving (500 and no save if it still fails) and ignore unknown fields; step 7 validates character updates and sends a `warning` on failure. Specialist calls use `format="json"`; the step-3 template defaults to `temporary`. Verified: a refine merge with `type: "supporting"`, `age: 17` made the committed code's character vanish (and its PUT return 500); the fixed code saves `temporary`/`"17"` and the character stays listed and editable. A file saved with wrong types by an older version is skipped by the committed code and listed by the fixed one. A profile with `type: "supporting"`, `age: 17`, `abilities: "flying"` is created instead of dropped. The real `data/` files round-trip unchanged. The evidence below describes the pre-fix code.
- **Evidence:** `Character(type="supporting")` and `Character(age=17)` both raise (verified). In step 3 these become `warning` events, which the UI ignores (KI-018). In the refine **create** branch they become HTTP 500 (`main.py:334-339`, `356-360`). **Worse, in the refine *merge* branch** (`existing_slug` found), values are applied with `setattr` (`main.py:327`, `:357`) without validation (no `validate_assignment`), so the invalid value is **saved** and the endpoint returns 200. The file then fails to load: `get_all()` silently skips it (the entity vanishes from the sidebar) and `get_by_slug()` raises (later PUT/merge → 500). Reproduced: `setattr(c, "type", "supporting")` then `model_dump()` then re-construct → `ValidationError`. The step-3 template hard-codes `"type": "main"` (`specialist.py:139`), so auto-discovered characters skew to MAIN CAST.
- **Fix:** normalise LLM output before construction (map unknown types → `temporary`, `str()` the age, derive a missing slug). Pass `format="json"` to Ollama.

### KI-017 — Export side effects · Low · ✅ Fixed in v2.0.0 (plan 015)
- **Status: Fixed in v2.0.0 [plan 015].** `export_novel` (`main.py:243-266`) returns the text from memory (`Response` with `Content-Disposition: attachment`, built as Starlette's `FileResponse` does) and writes nothing to `data/`. `_export_filename` (`main.py:237-240`) turns spaces and characters Windows forbids into `_`, strips trailing dots and spaces, and falls back to `novel`.
  - Verified old vs new on sandbox copies, with titles `Untitled Novel`, `Test: A/B?` and `林凡传奇`:
    - Old rewrote or created `data/<title>.txt|md` on every export and returned 500 for `Test: A/B?`.
    - New returned 200 for all, with the same headers, and left `data/` untouched.
    - The text is identical apart from line endings: old wrote the file in Windows text mode, so downloads had CRLF; new sends LF on every OS.
  - Existing `data/*.txt|md` exports from older versions stay where they are (user data); delete them by hand if unwanted.
  - The evidence below describes the pre-fix code.
- `main.py:251-255` writes `data/{title}.{fmt}` and leaves it there (e.g. `data/Untitled_Novel.txt`). Characters illegal in Windows filenames cause failures. **Fix:** stream from memory (`Response(content, headers={"Content-Disposition": …})`) and sanitise the filename.

### KI-018 — `warning` SSE ignored · Low · ✅ Fixed in v2.0.0 (plan 009)
- **Status: Fixed in v2.0.0 [plan 009].** `generateChapter`'s handler map has a `warning` entry: a warning toast (6 s) plus `console.warn`. Verified in the browser pane: a failed step-5 unload showed "⚠ Could not unload the specialist model: …" and the chapter still completed. The evidence below describes the pre-fix code.
- The pipeline emits `warning` (`chapter_pipeline.py:107,115`), but `generateChapter`'s handler map has no `warning` key. **Fix:** add a handler that shows a warning toast or step log.

### KI-019 — False-success model pulls · Medium · ✅ Fixed in v2.0.0 (plan 010)
- **Status: Fixed in v2.0.0 [plan 010].** `pull_model` (`main.py:306-364`) turns a non-200 response into `{"status": "error", "message": "Ollama returned <code>: <Ollama's error>"}`, stops at the first `{"error": …}` line, and ends with `success` only after Ollama's own `{"status": "success"}`. A stream that ends without it reports "Ollama ended the download without confirming success". Verified against a fake Ollama: the old code reported `success` for an HTTP 404, an error line and a truncated stream; the new code reports each as an error, and Settings shows "Pull failed: …". The evidence below describes the pre-fix code.
- `pull_model` neither checks `resp.status_code` nor detects `{"error": …}` lines. After the loop it always yields `success` (`main.py:273-294`). **Fix:** check the status, detect the `error` key, and only emit success after a final `{"status":"success"}` from Ollama.

### KI-020 — Family-prefix "installed" detection · Low · ✅ Fixed in v2.0.0 (plan 012)
- **Status: Fixed in v2.0.0 [plan 012].** `get_models()` (`main.py:280-307`) flags a recommended model as installed only when Ollama lists that exact model. Names are compared through `_model_key()` (`main.py:275-277`): a name without a tag counts as `:latest`, as Ollama treats it, and a registry host's `:port` is not a tag.
  - Verified against a fake Ollama listing `gemma3:4b`, `llama3.1:latest`, `phi4-mini:3.8b` and `mistral-nemo:12b-instruct-2407-q4_0`: the old code flagged `gemma3:12b`, `llama3.1:8b`, `mistral-nemo:12b` and `phi4-mini:3.8b`; the new code flags only `phi4-mini:3.8b`.
  - In Settings the three wrongly flagged entries now offer **⬇ Pull**, and the installed tags still appear as their own "Installed" entries.
  - The evidence below describes the pre-fix code.
- `main.py:292-295`: `inst.startswith(family + ":")` marks every tag of a family as installed. **Fix:** exact match (also treat `name` ≡ `name:latest`).

### KI-021 — Hard-coded API base · Low · ✅ Fixed in v2.0.0 (plan 007)
- **Status: Fixed in v2.0.0 [plan 007]** (as part of KI-010). `const API = '/api'`: same origin, so the UI works as `127.0.0.1:8000` and `localhost:8000` and the server needs no CORS. Verified: the UI loaded and worked from `http://localhost:8000`. The evidence below describes the v1.0.0 code.
- `app.js:6`. **Fix:** `const API = '/api'` (same origin). This also removes the need for CORS.

### KI-022 — Committed bytecode · Low · ✅ Fixed in v2.0.0 (plan 002)
- **Status: Fixed in v2.0.0 [plan 002].** Verified 2026-11-22: after the plan 002 commit, `git ls-tree -r origin/main` lists no `.pyc` file. The pre-existing local `cpython-313` caches are untracked and ignored.
- At v1.0.0, 14 `.pyc` files under `backend/__pycache__`, `backend/agents/__pycache__`, `backend/managers/__pycache__` and `backend/pipeline/__pycache__` were tracked (committed before `.gitignore` existed).
- **Resolution (plan 002):** the folders moved with the code into `app/backend/…/__pycache__`, where `.gitignore` (`__pycache__/`) excludes them. When the reorganisation is committed, git records the old tracked copies as deleted and never adds the new ones. No `git rm` needed. Verify after the commit with `git ls-files | grep pyc` (expect nothing).

### KI-023 — Documentation/UI copy drift · Low · ✅ Fixed in v2.0.0 (plans 001, 014)
- **Status: Fixed in v2.0.0.** The README part was fixed in plan 001. Plan 014 fixed the rest:
  - The model-browser subtitle now reads "Use Set Writer / Set Specialist on an installed model, or ⬇ Pull to download one." (`index.html:764`), describing the real buttons. Verified in the browser.
  - The user guide's Step 2 and "Recommended setup" recommend the defaults (`gemma3:12b` writer, `phi4-mini:3.8b` specialist) instead of `gemma3:12b` for both.
  - The evidence below describes the pre-fix state.
- README "Architecture" listed non-existent `storage.py`, `pipeline.py`, `ollama.py`, `data/world.json` and "JSON/SQLite" storage → **corrected in v2.0.0**.
- Still open: the Settings model browser subtitle says "Click a model to set as writer. Shift+click to set as specialist." (`index.html:766`), but only explicit buttons exist. The README recommends `gemma3:12b` for both roles while the default specialist is `phi4-mini:3.8b` (a recommendation, not an error).

### KI-024 — Pipeline UI state not reset · Low · ✅ Fixed in v2.0.0 (plan 011)
- **Status: Fixed in v2.0.0 [plan 011].** `resetPipeline()` (`app.js:643-660`) cancels `completePipeline()`'s pending fade (`_pipelineFadeTimer`, `app.js:641`), clears the panel's inline `opacity`, and clears each step's inline `borderColor`/`background`. It runs at the start of every generation and on cancel. Verified in the browser, old vs new with a stub:
  - The run after a completed one: old stayed at opacity 0.4, new was at full opacity.
  - A run started 0.5 s after the previous completion: old was dimmed 2 s later, new was not.
  - The run after a failed one: old kept `step-1` red, new cleared it.
  - The evidence below describes the pre-fix code.
- `completePipeline` sets `opacity: 0.4` (`app.js:694`). `setStepError` sets inline red border/background (`:709-710`). `resetPipeline` clears neither. **Fix:** reset `style.opacity`, `borderColor` and `background` in `resetPipeline`.

### KI-025 — No tests / lint / CI / logging · Medium · ✅ Fixed in v2.0.0 (plan 016)
- **Status: Fixed in v2.0.0 [plan 016]** (tooling chosen by the user, decision D-013).
  - **Tests:** `app/tests/` holds 71 pytest tests (API, storage, pipeline, helpers).
    - They use FastAPI's `TestClient` on `127.0.0.1` and a recording fake `ollama`, and redirect every manager to a temp folder.
    - A session guard fails the run if the real `data/` changes.
    - Run with `py -m pytest app/tests`.
  - **Lint:** ruff, pinned to the classic bug-finding rules in `app/pyproject.toml`; run `py -m ruff check app`.
    - It found five unused imports and one real bug (KI-040), all fixed.
    - Dev tools are in `app/requirements-dev.txt`, separate from the app's requirements.
  - **CI:** `.github/workflows/ci.yml` runs lint, tests and `node --check` on Ubuntu and Windows, with Python 3.11 and 3.14, on every push and pull request.
  - **Logging:** console logging is configured in `main.py`. Warnings and errors are logged for skipped data files, pipeline `warning`/`error` events, non-JSON specialist replies, failed model pulls and cancelled generations.
  - **Verified:**
    - 71 passed locally (pytest 9.2.0, ruff 0.17.6, Python 3.14.5).
    - With the storage helper swapped for the old in-place writer, 3 storage tests fail as intended.
    - First CI run (2026-11-24) green on all four jobs: Ubuntu and Windows × Python 3.11 and 3.14 (https://github.com/Tejasva-Maurya/AI_Writer/actions/runs/45352941763).
  - The evidence below describes the pre-fix state.
- No test files, no linters, no CI workflows. No `logging` usage (`except: pass` in managers hides errors). **Suggested start:** pytest + FastAPI `TestClient` with a stubbed `ollama` module; `ruff`; a `logging` config writing to the console.

### KI-026 — Non-atomic writes; silent skips · Low · ✅ Fixed in v2.0.0 (plan 016)
- **Status: Fixed in v2.0.0 [plan 016].** `managers/storage.py`:
  - **`write_json`** writes a temp file in the same folder (fsync), then `os.replace`s it into place. For `create()` it uses `os.link`, which is atomic and never replaces; without hard links it falls back to an exclusive open. The bytes are the same as before.
  - **`read_all`** logs `Skipped unreadable <folder>/<file>: <error>` instead of skipping silently.
  - All five managers use them; their function names are unchanged.
  - **Verified on sandbox copies, old vs new, with a crash simulated mid-save:**
    - Old left the character file half-written (189 of 377 bytes), and `get_all()` silently dropped it.
    - New kept the file intact and listed, and left no temp file.
    - A corrupt file was skipped silently on old; new logged `WARNING managers.storage: Skipped unreadable characters/zz_test_broken.json: JSONDecodeError: …`, also in the server console.
  - The evidence below describes the pre-fix code.
- Managers write in place. A crash mid-write corrupts the file, and `get_all()` then hides it. **Fix:** write to a temp file + `os.replace`, and log skipped files.

### KI-027 — Edit = full replace loses untracked fields · Medium · ✅ Fixed in v2.0.0 (plan 003)
- **Status: Fixed in v2.0.0 [plan 003]** (UI side, by round-tripping all fields). On edit, `saveCharacter`/`saveScene` send `{...existing, ...form}`, where `existing` is the record in `state`. To keep `state.characters` fresh, the `generateChapter` `complete` handler now also reloads characters, because step 7 updates their profiles on disk. `PUT` is still a full replace for other API clients. Verified in a sandbox: edits kept `first/last` = 3/5 and `first_appeared_chapter` = 4.
- The character modal sends neither `first_appeared_chapter` nor `last_seen_chapter`, so once KI-001 is fixed they will reset to 1 on every edit. Same for the scene's `first_appeared_chapter`. **Fix:** merge the payload into the existing record server-side (PATCH semantics), or round-trip all fields.

### KI-028 — Fallback specialist mismatch · Low · ✅ Fixed in v2.0.0 (plan 012)
- **Status: Fixed in v2.0.0 [plan 012].** The `loadNovelMeta()` fallback (`app.js:167-174`) uses `specialist_model: 'phi4-mini:3.8b'`, the backend default. Verified in the browser with `/api/novel-meta` made to fail: old `gemma3:12b`, new `phi4-mini:3.8b`; the writer stays `gemma3:12b` on both. The evidence below describes the pre-fix code.
- `app.js:173` (`loadNovelMeta`, used when the backend is unreachable) falls back to `gemma3:12b` for the specialist (the second fallback, in `openSettingsModal`, was removed in plan 006); the backend default is `phi4-mini:3.8b` (`models.py:148`).

### KI-029 — Specialist stays resident after refine · Low · ✅ Fixed in v2.0.0 (plan 013)
- **Status: Fixed in v2.0.0 [plan 013].** `specialist._call()` defaults to `keep_alive=300` (`specialist.py:41`), the writer's value, chosen by the user (decision D-011).
  - It applies to the three refine calls and to pipeline steps 1–3, so a generation that fails or is cancelled before step 5 no longer pins the specialist in VRAM either.
  - Step 5 (`unload`) and step 7 (`post_write_update`) still send `0`.
  - Verified with the real ollama 0.6.3 client against a logging fake Ollama: old sent `keep_alive=-1` for refine character/scene/world and steps 1–2; new sends `300`. Both send `0` for the unload and step 7.
  - The evidence below describes the pre-fix code.
- Refine endpoints call `_call` with the default `keep_alive=-1`. **Fix:** use `0` or a finite value (e.g. `120`) for refine calls.

### KI-030 — User/sample data in VCS · Low · ✅ Fixed in v2.0.0 (plan 017)
- **Status: Fixed in v2.0.0 [plan 017].** `data/` is no longer tracked (user decision; D-014).
  - `.gitignore:3` ignores `/data/`. `git rm -r --cached data/` removed the 5 tracked files from the index only; they stay on disk. The files: `novel_meta.json`, `world_settings.json`, one character, one location and the old export `Untitled_Novel.txt`.
  - **No history rewrite:** commits up to plan 016 still contain those 5 files.
  - **No seed folder is needed.** The managers create their folders when first used (`ensure_dir`), and the meta and world loaders return defaults when the file is missing (`novel_meta_manager.py:13-16`).
  - **`total_chapters: 1` with no chapters** is the user's own data and was left alone. It is harmless: the header badge counts chapter files (`app.js:327`), and so does the next chapter number (`chapter_manager.py:42`).
  - **Verified:**
    - SHA-256, size and mtime of every file in `data/` were identical before and after.
    - `git check-ignore -v data/novel_meta.json` names `.gitignore:3:/data/`, and a probe file created in `data/` never appeared in `git status`.
    - A copy of `app/` with no `data/` answered novel-meta, characters, scenes, chapters, world and the txt export with 200 and defaults. Its first `POST /api/characters` created `data/characters/`.
  - Git no longer backs up the novel: copy `data/` yourself (07 §6).
  - The evidence below describes the pre-fix state.
- `data/` holds personal novel content plus an export file, and `novel_meta.total_chapters` is 1 with no chapters. **Fix:** ignore `data/` (keep a `data.sample/` or seed on first run).

### KI-031 — No concurrency guard / cancellation · Medium · ✅ Fixed in v2.0.0 (plan 010)
- **Status: Fixed in v2.0.0 [plan 010].**
  - **One at a time:** `generate_chapter` (`main.py:171-207`) runs the pipeline as one `asyncio.Task` held in `_generation`. While it runs, a second request gets **409** "A chapter is already being generated. Wait for it to finish or cancel it."
  - **Cancel:** `POST /api/generate-chapter/cancel` (`main.py:210-217`) cancels it; the stream ends with `error {"message": "Generation cancelled", "cancelled": true}`. The UI has a **✕ Cancel** button next to **Generate**.
  - **Closing the tab** still stops the generation and releases the guard.
  - **Verified (stubbed ollama):**
    - Old code: two overlapping generations both returned 200 and both completed as chapter 1, so one overwrote the other.
    - New code: the second request got 409. Cancel ended the stream within 0.1 s and saved no chapter, and the next generation was accepted. A client that disconnected after 2 s left no chapter, and nothing was still running.
  - The evidence below describes the pre-fix code.
- Two tabs (or API clients) can generate the same chapter at once. Writes race and can overwrite each other. There is no cancel button. Closing the tab aborts the stream and loses unsaved work. **Fix:** a server-side lock per novel, plus a cancel endpoint or `AbortController` in the UI.

### KI-032 — Minor UI glitches · Low · ✅ Fixed in v2.0.0 (plan 013)
- **Status: Fixed in v2.0.0 [plan 013]**, all three. Verified in the browser, old vs new with a stub:
  - **Full View tags:** the `complete` handler now keeps `characters_featured`/`scenes_featured` from the event's `characters`/`scenes` (`app.js:535-541`). Full View right after a generation showed no tags on old; on new it showed the same character and location slugs as the chapter reopened from History.
  - **First chunk with `\n\n`:** the `token` handler creates the first paragraph before splitting (`app.js:498-501`). Text 0.6 s into a stream whose first chunk was `"Opening line.\n\nSecond"`: old empty, new "Opening line." + "Second". The final paragraphs are identical.
  - **Shortcuts:** they compare `e.key.toLowerCase()` (`app.js:1444`). Alt+`S` and Alt+`W` (upper case, as with Caps Lock or Shift) opened nothing on old and Settings/World on new; Alt+`s` works on both.
  - The evidence below describes the pre-fix code.
- After generation, `state.currentChapter` lacks `characters_featured`/`scenes_featured`, so Full View tags are empty (`app.js:533-537`).
- If the very first token chunk contains `\n\n`, its text is held back by the `app.js:498` guard. It appears only when a later chunk containing `\n\n` arrives (lost from the live view if none does). The saved text is unaffected.
- Alt shortcuts compare `e.key === 'g'` etc. (lower case only), so they fail with Caps Lock or Shift.

### KI-033 — Partial `OLLAMA_HOST` support · Low · ✅ Fixed in v2.0.0 (plan 015)
- **Status: Fixed in v2.0.0 [plan 015].** `OLLAMA_BASE_URL` (`main.py:315`) is `_ollama_base_url(os.getenv("OLLAMA_HOST"))`, a port of ollama-python's `_parse_host` (`main.py:291-312`); the model list and pull use it (`main.py:325, 361`).
  - It was identical to the library's parser for all 35 inputs tested (its 30 doctest cases plus 5 more). The default is `http://127.0.0.1:11434`, as for generation.
  - When Ollama is unreachable, `ollama_error` and the Settings status line name the address tried.
  - Verified with `OLLAMA_HOST=127.0.0.1:11999` and a fake Ollama there: old reported Ollama unreachable and the pull failed (it called `:11434`); new listed the fake's models and the pull succeeded.
  - The evidence below describes the pre-fix code.
- ollama-python honours `OLLAMA_HOST`, but `main.py:287,323` hard-code `http://localhost:11434`.

### KI-034 — "Fully offline" claim · Low · ✅ Fixed in v2.0.0 (plan 014)
- **Status: Fixed in v2.0.0 [plan 014].** The fonts are self-hosted, so the "fully offline" claim is now true (user decision; D-012).
  - `app/frontend/fonts/` holds the 14 woff2 files Google served for these families (all subsets, 247 KB), `fonts.css` with the same 27 `@font-face` rules pointing at `/static/fonts/`, and the three SIL OFL licences.
  - `index.html` links `/static/fonts/fonts.css` instead of Google (`index.html:9`), and `style.css` lost its `@import`.
  - Verified in the browser, old vs new: old requested `fonts.googleapis.com`; new made no request outside `127.0.0.1`. The same six font faces loaded on both, from `/static/fonts/` on new. All 14 files are served as `font/woff2`.
  - The evidence below describes the pre-fix code.
- Google Fonts are loaded **twice**: `<link>` tags in `index.html:9-11` and an `@import` in `style.css:6`. The app works offline with fallback fonts. Either self-host the fonts (change both files) or soften the README claim.

### KI-035 — Desktop-only layout · Low (design limitation) · ✅ Fixed in v2.0.0 (plan 017)
- **Status: Fixed in v2.0.0 [plan 017].** A CSS-only *Responsive layout* section ends `style.css` (`style.css:2385-2439`), as the user chose. No HTML or JS changed.
  - **≤ 1200 px:** 230 px sidebars; the header's brand and actions may shrink.
  - **≤ 900 px:** one scrolling column, with the writer first, then Characters, then Locations (each list scrolls inside a card at most 40% of the window high).
    - The pipeline uses 4 columns and forms use one.
    - Modals fit the window, and a long title ends with "…".
  - **≤ 600 px:** icon-only header buttons (they keep their `title` and `aria-label`), 2 pipeline columns, wrapping mode tabs and Generate row, full-width toasts.
  - Above 1200 px nothing changes.
  - **Verified in the browser pane, old vs new:**
    - **375×812:** old squeezed the writer to 40 px, and the page and the header overflowed sideways. New: the writer is 370 px wide with the sidebars below it, nothing overflows, and Settings fits.
    - **768×1024:** writer 208 → 762 px; sidebars below; 4 pipeline columns.
    - **1100×800:** writer 540 → 640 px and sidebars 280 → 230 px, still side by side.
    - **1400×900:** every element has the same position and size (only the animated background orbs and the button shimmer differ).
    - The console stayed clean. A real phone or touch device was not tested.
  - The evidence below describes the pre-fix code.
- `style.css` has no `@media` rules. Fixed 280 px sidebars make narrow windows unusable.

### KI-036 — Create silently overwrites an existing entity with the same slug · Medium · Verified ✔ · ✅ Fixed in v2.0.0 (plan 004)
- **Status: Fixed in v2.0.0 [plan 004].**
  - `character_manager.create()` / `scene_manager.create()` open the file with mode `"x"` (exclusive create). They never overwrite and raise `FileExistsError("Character 'x' already exists")`.
  - A `FileExistsError` handler in `main.py` turns this into **409** for `POST /api/characters` and `/api/scenes`. The refine create branches return 409 explicitly.
  - Pipeline step 3 keeps the existing profile and emits a `warning`.
  - Verified in a sandbox: same name, slug-equivalent name, case-only slug, scenes, refine create, a pipeline collision, and the UI (toast, modal stays open).
  - The evidence below describes the pre-fix code.
- **Evidence:** `create_character`/`create_scene` (`main.py:69-75`, `:102-108`) derive the slug when it is empty, then call `save()` without checking whether `data/…/{slug}.json` already exists. The refine *create* branch (`main.py:328-331`, `:355-358`) and pipeline step 3 (`chapter_pipeline.py:78-92`) save LLM-provided slugs the same way. `docs/technical/04` already documents the overwrite.
- **Reproduced 2026-11-22 [plan 003]:** POST `/api/characters` with `name: "Zz Test Hero"` after the existing `zz_test_hero` had been edited returned 200 and replaced the whole record (type, arc notes, chapters 3/5 → 1/1). Since KI-001 is fixed, this is reachable from **+ New Character** / **+ New Location** whenever a new name slugifies to an existing slug.
- **Fix:** return **409** from POST when the slug exists (and show the message in the UI), or append a numeric suffix. Apply the same check in refine create and pipeline step 3 (where it should fall back to "existing").

### KI-037 — Streaming text cursor never hides · Low · Verified ✔ · ✅ Fixed in v2.0.0 (plan 011)
- **Status: Fixed in v2.0.0 [plan 011].** `.text-cursor[hidden] { display: none; }` (`style.css:1197`). Verified in the browser, old vs new: after a completed run the cursor's computed `display` was `inline` on old and `none` on new. Viewing a past chapter on a fresh page showed the same difference. While text streams it is `inline` on both. The evidence below describes the pre-fix code.
- **Evidence:** `.text-cursor { display: inline; }` (`style.css:1191-1192`) overrides the browser's `[hidden] { display: none }`. `DOM.textCursor.hidden = true` (`app.js:529`, `:402`) therefore has no effect, and the blinking `▍` stays after a chapter completes and when a past chapter is viewed. Observed 2026-11-22 [plan 003]: `hidden === true` while the computed `display` was `inline`.
- **Fix:** add `.text-cursor[hidden] { display: none; }` next to the rule (the same pattern as `.modal-overlay[hidden]`, `style.css:1301`).

### KI-038 — Names without letters or digits produce an empty slug · Low · Verified ✔ · ✅ Fixed in v2.0.0 (plan 007)
- **Status: Fixed in v2.0.0 [plan 007]** (as part of KI-009/KI-010). POST derives `make_slug(slug or name)` and returns **422** "name must contain at least one letter or digit" when that is empty; the managers never write an empty slug. Verified: `???` and `!!!` → 422, no `.json` created; `林凡` → `林凡.json` and `Élodie Brontë` → `élodie_brontë` (any-script names still work). An old `.json` must still be deleted by hand. The evidence below describes the pre-fix code.
- **Evidence:** `_slugify` (`character_manager.py:12-16`, same in `scene_manager.py`) removes every character outside `[\w\s-]`, so a name like `???` or `!!!` becomes `""`. `POST /api/characters` then saves `data/characters/.json` (200) and lists it with slug `""`. The card's **Edit**/**Delete** call `/api/characters/` with an empty path segment, which FastAPI answers with a 307 redirect, so the entity can't be edited or deleted from the UI. Emoji-only names behave the same way (`\w` is Unicode-aware, so CJK/Latin names are fine).
- **Reproduced 2026-11-22 [plan 004]:** the first `???` was saved as `.json`; a second (`!!!`) got 409 `Character '' already exists` (since KI-036's fix).
- **Workaround:** delete `data/characters/.json` (or `data/scenes/.json`) by hand.
- **Fix:** in POST (and refine create / pipeline step 3), reject an empty slug after derivation with 422 ("name needs at least one letter or digit"), or derive a fallback such as `character_<n>`.

### KI-039 — Multi-chapter notice never hides · Low · Verified ✔ · ✅ Fixed in v2.0.0 (plan 011)
- **Status: Fixed in v2.0.0 [plan 011].** `.multi-chapter-notice[hidden] { display: none; }` (`style.css:1210`). Verified in the browser, old vs new:
  - On load, old showed the notice; new hid it.
  - After a run with `estimated_chapters: 2`, both showed it.
  - In the next run, old still showed it; new hid it.
  - The evidence below describes the pre-fix code.
- **Evidence:** `.multi-chapter-notice { display: flex; }` (`style.css:1199`) overrides the browser's `[hidden] { display: none }`, the same trap as KI-037.
  - The notice "This plot may span multiple chapters" (`index.html:457`, `hidden` in the markup) was visible from page load. `DOM.multiChapterNotice.hidden = true` at the start of each run (`app.js:439`) had no effect, so it showed whether or not a `multi_chapter` event was sent.
  - Found 2026-11-23 [plan 011]: a page audit listed `#text-cursor` and `#multi-chapter-notice` as the only elements with `hidden` set whose computed `display` wasn't `none`. Plan 010's UI screenshots showed the notice although the stub never sent `multi_chapter`.
- **Fix:** add `.multi-chapter-notice[hidden] { display: none; }` next to the rule.

### KI-040 — `main.py` does not parse on Python 3.11 · High · Verified ✔ · ✅ Fixed in v2.0.0 (plan 016)
- **Status: Fixed in v2.0.0 [plan 016].** `_export_filename` now computes the fallback name before the f-string (`main.py:243-248`).
  - ruff (target `py311`) passes, and CI runs the suite on Python 3.11.
  - The evidence below describes the plan 015 code.
- **Evidence:**
  - Plan 015's `_export_filename` returned `f"{stem if re.search(r'[^\W_]', stem) else 'novel'}.{fmt}"`.
  - A backslash inside an f-string expression is allowed only from Python 3.12 (PEP 701). On Python 3.11, the stated minimum, `main.py` raises `SyntaxError` at import, so the server does not start.
  - Not caught then because the dev machine runs Python 3.14 and there was no linter or CI.
  - Found 2026-11-24 [plan 016] by ruff: `invalid-syntax: Cannot use an escape sequence (backslash) in f-strings on Python 3.11`.
  - Present in commit `fa4332b` on `main` (2026-11-24) until plan 016.
- **Fix:** move the conditional out of the f-string.

### KI-041 — A failure in step 7 loses the chapter that was just written · Medium · Verified ✔ · ✅ Fixed in Unreleased (plan 019)
- **Status: Fixed in Unreleased [plan 019].** The pipeline saves the written chapter as `data/draft.json` right after step 6, before step 7 runs. `finalize_chapter()` deletes the draft only as its last action.
  - A failed summary now ends with `error` + `draft_saved: true` ("Summary failed: … The chapter is kept as a draft: approve it to try again."). The UI opens the draft, and **Approve & save** retries step 7.
  - Tested in `test_pipeline.py::test_failed_summary_keeps_the_written_chapter_as_a_draft` and `test_draft.py::test_failed_approval_keeps_the_draft_with_the_edits`. Checked in the UI with a stub `ollama` whose step-7 call fails.
  - The evidence below describes the 2.0.0 code.
- **Evidence:**
  - In `run_pipeline` (2.0.0), step 7 awaited `specialist.post_write_update(...)` (`chapter_pipeline.py:217`), and the chapter was saved only afterwards (`chapter_manager.save_chapter`, `:233`).
  - Any exception from that call (Ollama stopped or restarted, the specialist model not pulled, out of memory) reached the generic `except Exception` (`:289-291`), which only emitted `error`.
  - The ~2,000 words streamed in step 6 existed only in memory and in the browser's display, so they were lost: the chapter wasn't saved, and the UI had no way to keep it.
  - Found 2026-11-24 [plan 019] by reading the code while porting the `improvement` branch, whose split pipeline would have had the same gap.
- **Fix:** persist the text before step 7 (the draft) and delete it only after the chapter is saved.

### KI-042 — Edits saved while step 7 or a world refine runs are overwritten · Medium · Verified ✔ · ✅ Fixed in Unreleased (plan 020)
- **Status: Fixed in Unreleased [plan 020].**
  - `finalize_chapter()` reads characters and scenes again right after the summary call, and applies its updates to those copies.
  - `refine_world` merges into the world re-read after its specialist call.
  - Nothing after those awaits yields, so no other request can interleave before the saves.
  - The Build-tab refines also joined the one-LLM-job guard (409), so a refine can no longer overlap a summary at all.
  - Tested in `test_refine.py`: `test_edits_made_during_the_summary_are_kept`, `test_a_profile_deleted_during_the_summary_stays_deleted` and `test_world_edit_made_during_a_world_refine_is_kept`. All three failed on the old code with the symptoms below.
  - The evidence below describes the code before plan 020.
- **Evidence (read-before-await, write-after):**
  - `finalize_chapter` loaded every character and scene (`chapter_pipeline.py:85-86`), awaited `post_write_update` (`:90`, seconds; a minute or more on CPU), then saved each featured profile as *the copy read before the call* plus the step-7 changes.
  - So an **Edit** or an **Update Existing** refine of a featured character/location saved during the summary was reverted.
  - A profile **deleted** during it was written back: the old copy was saved again under its slug.
  - `refine_world` loaded the world (`main.py:611`), awaited the specialist (`:612`), and saved its merge of that old copy (`:616-632`). A World Settings save made during the call was lost.
  - `refine_character`/`refine_scene` were not affected: they read the existing profile after the call.
  - Found 2026-11-24 [plan 020] while adding the refine routes to the job guard. The guard alone couldn't fix it, because manual saves aren't LLM jobs.
- **Fix:** re-read after the await; the pre-await copies only feed the prompts.

### KI-043 — A regenerated earlier chapter is told that later chapters already happened · Medium · Verified ✔ · ✅ Fixed in Unreleased (plan 022)
- **Status: Fixed in Unreleased [plan 022].**
  - Step 4 gives the chapter being rewritten the tier `skip` (left out) and every later chapter the tier `later`.
  - `build_master_prompt` lists the `later` chapters (micro summaries) in their own `=== LATER IN THE STORY ===` section, with "keep this chapter consistent with them, but do not reveal, anticipate or foreshadow their events".
  - A new chapter's prompt is unchanged.
  - Tested in `test_regenerate.py`: `test_regenerated_chapter_sees_later_chapters_only_as_later` and `test_master_prompt_skip_and_later_tiers` (both failed on the old code); `test_a_new_chapter_gets_the_same_prompt_as_before` pins the normal prompt.
  - The evidence below describes the code before plan 022.
- **Evidence:**
  - Step 4 (`chapter_pipeline.py:276-289`) mapped every chapter with `N − n ≤ 0` to `micro`.
  - `build_master_prompt` (`context_builder.py:136-143`) listed all chapters, ascending, under `=== STORY SO FAR ===`.
  - So regenerating chapter 3 of 10 (API `chapter_number: 3`) put chapters 4–10 into the "story so far" and showed the writer the old chapter 3's summary.
  - The behaviour was documented as a caveat in 02 W3.3 and listed as a plan 019 follow-up, but had no KI.
- **Fix:** split the chapters into before / this one / after.

### KI-044 — Regenerating an earlier chapter rolls character and location profiles back · Medium · Verified ✔ · ✅ Fixed in Unreleased (plan 022)
- **Status: Fixed in Unreleased [plan 022].**
  - `finalize_chapter()` sets `last_seen_chapter = max(current, N)`.
  - When chapters after N exist, it doesn't apply `arc_notes`, `cultivation_level`, `relationship_updates` or a location's `new_significance`. It still adds new abilities, and returns a warning naming the later chapter.
  - Tested in `test_regenerate.py`: `test_regenerated_earlier_chapter_does_not_roll_profiles_back` and `test_last_seen_never_moves_backwards`. Both failed on the old code: `last_seen` went 5 → 3 and 4 → 2, and the arc notes were overwritten.
  - The evidence below describes the code before plan 022.
- **Evidence:**
  - Step 7 set `last_seen_chapter = N` for every updated or featured character (`chapter_pipeline.py:122`, `:139-144`).
  - It also replaced arc notes, cultivation level and relationship descriptions (`:123-131`) and a location's significance (`:146-153`) with what the summary of chapter N said.
  - After regenerating chapter 3 of 10, a character last seen in chapter 10 showed "Ch. 1 — 3", and their level and arc were back at chapter 3's.
  - Found 2026-11-26 [plan 022] while fixing KI-043.
- **Fix:** never move `last_seen` backwards; take state updates only from the newest chapter.
