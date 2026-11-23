---
id: 006
title: "Fix Settings via Alt+S, Settings save resets, and next chapter number (KI-006, KI-007, KI-008)"
status: done
approved: 2026-11-23T12:49:08+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 0210cc96a7e2b7b753bdab48ed8eb466fd59abcbe09fd330c6391e3223f3038b
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Fix Settings via Alt+S, Settings save resets, and next chapter number (KI-006, KI-007, KI-008)

## Context
The user asked to fix KI-006, KI-007 and KI-008. All three are in the frontend (`app/frontend/app.js`), and two of them can lose or corrupt data:
- **KI-006:** Ollama models load only through a *second* click listener on ⚙ Settings (`app.js:1876-1887`). `Alt+S` (`:1400`) calls `openSettingsModal()` directly, so both model dropdowns stay empty. `openSettingsModal` (`:1023-1024`) sets `.value` on empty `<select>`s, which has no effect, so **Save writes empty model names** and the next generation fails with "model is required".
- **KI-007:** `saveSettings` (`:1028-1035`) sends only title, genre, author and the two models. `PUT /api/novel-meta` is a full replace, so **`total_chapters` resets to 0 and `created_at` to ""**.
  - A plain "send `{...state.novelMeta}`" fix is not enough. The pipeline updates `total_chapters` on disk after each chapter (`chapter_pipeline.py:236`), but the page never reloads novel meta. Saving after a generation would write back the old count.
  - The inline title edit (`initTitleEdit`, `:1252`) already spreads `state.novelMeta`, so it has this stale-count problem today.
- **KI-008:** `generateChapter` sends `chapter_number = state.chapters.length + 1` (`:436-437`), and the hint uses the same rule (`:358`). With a gap (chapters 1 and 3 exist), it sends 3 and **overwrites chapter 3**. The backend already does it right when no number is sent: `main.py:165` → `chapter_manager.get_next_number()` = highest + 1 (`chapter_manager.py:46-50`).

**Done means:**
- Settings opened by button or `Alt+S` always shows the model lists.
- Saving Settings or renaming the title never changes `total_chapters`/`created_at`, including after a generation.
- A new chapter always gets highest + 1 and never overwrites an existing one.

## Approach (all in `app/frontend/app.js`; no backend change)
1. **KI-006:** `openSettingsModal()` loads the models itself.
   - First, synchronously, `populateModelSelects(_cachedModels?.installed || [], m.writer_model, m.specialist_model)`, so the selects hold the current models immediately. The existing `populateModelSelects` (`:1657`) already adds current values even when not installed.
   - Then `loadModels().then(data => { populateModelSelects(data.installed || [], <current select values> || m…); renderModelBrowser(data); })`. This is the same pattern as `refreshModels` (`:1849`), so a choice the user makes meanwhile isn't overwritten.
   - Remove the second `#btn-settings` listener block (`:1876-1887`). One code path now serves the button and `Alt+S`.
   - The old hard-coded `|| 'gemma3:12b'` fallbacks in `openSettingsModal` go away, because the selects are filled from `state.novelMeta` (KI-028's other fallback in `loadNovelMeta` is untouched).
2. **KI-007:** `saveSettings` builds `meta = { ...state.novelMeta, title, genre, author, writer_model: <select> || state.novelMeta.writer_model, specialist_model: <select> || state.novelMeta.specialist_model }`. Every field the form doesn't show is round-tripped, and an empty select can never blank a model name.
3. **KI-007 (stale state):** the `generateChapter` `complete` handler reloads novel meta too: `Promise.all([loadChapters(), loadCharacters(), loadNovelMeta()])`. This also fixes the stale count for the title edit.
4. **KI-008:**
   - Add `nextChapterNumber()` = highest `chapter_number` in `state.chapters` + 1, mirroring `get_next_number()`. `updateChapterHint()` and the badge in `generateChapter` use it.
   - **The request no longer sends `chapter_number`** (`body = { plot }`). The backend picks highest + 1 from disk at request time, so a stale page (or a second tab) can't overwrite a chapter.
   - The `complete` handler sets the output badge from `data.chapter_number`, the number the backend actually used.
   - Explicit `chapter_number` (regenerate) stays available to API callers, as documented in 08.

## Contract / data impact
**None.**
- API: `chapter_number` was always optional (`models.py:81`); the UI just stops sending it.
- No SSE, schema or backend change.
- `data/novel_meta.json` simply stops losing fields.

## Docs to update (RULES §6)
- **`docs/technical/09`:** move KI-006, KI-007 and KI-008 to **Fixed** (`Fixed in Unreleased [plan 006]`), mark the headings ✅, add status lines, update the counts and the "through plan" line.
- **`docs/technical/02`:**
  - W3.1 step 3 (UI sends only `{plot}`; backend numbers highest + 1)
  - W3.4 `complete` row (also reloads novel meta; badge from event)
  - W7 (remove the ⚠ KI-006/007 notes)
  - W8 (models load whenever Settings opens)
- **`docs/technical/03` §4.4/§4.5:**
  - `openSettingsModal` loads models
  - one `#btn-settings` listener
  - drop the ⚠ on the `Alt+S` row
  - `nextChapterNumber`
- **`docs/technical/05`:** `total_chapters` row (no longer reset by Settings).
- **`docs/technical/07`:** first-run step 1 and the shortcut table (drop the ⚠ `Alt+S` notes).
- **`docs/technical/08`:**
  - A2 row "model name is empty": now only from older versions
  - A11 chapter numbers: highest + 1, no overwrite from the UI
- **Line references:** recompute `app.js:N` refs in 02, 03, 06 and 09 from the edited file by locating each function. Historical evidence in fixed KIs stays.
- **`docs/CHANGELOG.md` `[Unreleased]` → Fixed:** three lines `[plan 006] [KI-006/007/008]`.
- **`docs/ai/memory/`:** `project-state.md` (next up), `session-log.md`.
- **Plan 006:** status, execution log, outcome, then `reindex`.

## Verification
1. **JS syntax:** `node --check app/frontend/app.js`.
2. **Sandbox (as in plans 003–005):** a temp copy of `app/` + `data/`, plus an `ollama` stub (async specialist returns `{}`, the writer streams a few tokens). Served through the browser pane via a temp `.claude/launch.json` + launcher, both deleted afterwards. In the sandbox only, set `novel_meta.json` → `total_chapters: 7`, `created_at: "2026-01-01T00:00:00"`, and create chapter files `001.json` and `003.json` (gap at 2).
3. **KI-006:**
   - Reload the page and open Settings with **`Alt+S`** (dispatched `keydown`). Both selects must be non-empty and show the current models (Ollama is offline here, so marked "(not installed)"), and the model browser must render.
   - **Save** → `novel_meta.json` keeps both model names.
   - The button path also still works, with exactly **one** `GET /api/models` per open.
4. **KI-007:**
   - Change genre and save → `total_chapters` 7 and `created_at` unchanged.
   - Rename the title inline → the same.
   - After a stubbed generation, the pipeline sets `total_chapters`. Then a Settings save keeps the new value, and the network log shows `GET /api/novel-meta` after `complete`.
5. **KI-008:**
   - The hint shows "Chapter 4"; before, it would have been 3.
   - Generate → the request body has no `chapter_number`.
   - `004.json` is created, and the SHA-256 of `003.json` is unchanged. The badge and toast say Chapter 4.
6. **Console:** no errors.
7. **Cleanup:**
   - Stop the server.
   - Delete the sandbox, stub, launcher and `launch.json`.
   - `git status --porcelain data/` is empty.
- **Not verifiable:** real LLM output; behaviour with a running Ollama (the model list there comes from `/api/tags`, a code path this change doesn't touch).

## Risks & rollback
- **A race during Settings.** If Settings is saved during a generation, in the instant between the pipeline writing `total_chapters` and the page reloading meta, the old count could be written once. That needs both actions inside the same moment; the next generation corrects it (`max(old, n)`).
- **Display vs actual number.** The output badge shows the page's guess (highest + 1) while streaming. If another tab created a chapter meanwhile, the badge is corrected on `complete`. Nothing is overwritten either way.
- **Rollback:** revert `app/frontend/app.js` and the doc edits. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 006]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

## Outcome
**Deviations from the plan:**
- **`/api/models` call count.** Not "one per open": `loadModels()` caches its result, so the first open makes one call and later opens reuse the cache (unchanged behaviour). Verified: no duplicate call from the removed second listener.
- **Real button click.** The browser pane could not click ⚙ Settings (the header is off-screen in the narrow preview, KI-035), so the button path ran through its own click handler (`element.click()`).
- **Toast glyph.** The completion toast shows "✓ ✓" (icon plus a message starting with ✓). This predates the plan and was left as is.

**Shipped** (uncommitted). `app/frontend/app.js` only:
- `openSettingsModal` fills the model selects from `state.novelMeta`, then refreshes the selects and the model browser via `loadModels()`, keeping any choice made meanwhile. The second `#btn-settings` listener is removed. (KI-006)
- `saveSettings` sends `{...state.novelMeta, …form}`, with model fallbacks. The `generateChapter` `complete` handler reloads novel meta. (KI-007)
- New `nextChapterNumber()` (highest + 1) for the hint and the streaming badge. The request body is `{plot}`, so the backend numbers the chapter. The badge is set from `complete.chapter_number`. (KI-008)
- Line endings: still pure CRLF.

**Docs updated:**
- technical 02 (W2, W3.1, W3.4, W7, W8), 03 (§4.4, §4.5), 05, 06, 07, 08 (A2, A11), 09 (Fixed table, statuses, KI-028 detail)
- `app.js` line references remapped with `difflib`: 32 refs, plus 2 fixed by hand
- CHANGELOG (3 Fixed lines)
- memory: `project-state.md`, `session-log.md`

**Verification** (2026-11-23). Sandbox copy plus a stub `ollama`, through the browser pane. The sandbox had `total_chapters` 7, `created_at` set, and chapters 001 and 003.
1. `node --check` passed.
2. **Alt+S:** both selects were filled at once (`gemma3:12b` / `phi4-mini:3.8b`, marked "not installed" since Ollama is offline). The browser rendered 6 entries.
3. **Save:** kept both models, total 7 and `created_at`.
4. **Button path:** modal filled, browser rendered, no duplicate `/api/models` call.
5. **Inline title edit:** kept total 7 and `created_at`.
6. **Generation with the gap:** the hint said Chapter 4; the request body was `{"plot": …}`; `004.json` was created; `003.json` SHA-256 is unchanged; badge, toast and pills show Chapter 4; the hint moved to Chapter 5.
7. **Stale state:** with total 3 on disk at page load, the pipeline raised it to 4. `GET /api/novel-meta` followed `complete`, and the later Settings save kept 4.
8. **Console:** clean.
9. **Cleanup:** the sandbox, stub, launcher and `.claude/launch.json` were removed, port 8000 is free, and `data/` is untouched.

**Not verified:**
- real LLM output
- the model list with a running Ollama (`/api/tags`; code unchanged)

**Follow-ups:** none required. KI-028 (the `loadNovelMeta` fallback specialist `gemma3:12b`) remains open.
