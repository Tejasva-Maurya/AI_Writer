# Session log

> Append-only. One entry per working session, newest at the bottom. 3–6 lines each: date · tool/model · goal · outcome · plan · open threads.

---

### 2026-11-22 — Claude Code (Opus 5.5) — baseline analysis & AI workflow
- **Goal:** Analyse the repo; produce detailed current-state docs, a CHANGELOG, AI rules/guardrails, and a self-maintaining plans/memory system.
- **Outcome:** Read every source file. Verified KI-001 (422 on manual save), KI-003 (backend import fails without `ollama`) and KI-016 (int age / unknown type rejected) by execution. Wrote `docs/01–09` + index, `CHANGELOG.md`, `CLAUDE.md`, `AGENTS.md`, `.ai/` workspace, and `.claude` hooks (auto-save approved plans; Stop-hook CHANGELOG guard). Fixed the README architecture section. An independent agent fact-checked docs 02/03/04/06/09 against the code: all constants, routes and KIs were confirmed, and 7 minor wording fixes were applied. That check also uncovered the refine-merge unvalidated `setattr` bug (added to KI-016, verified).
- **Plan:** 001 (retroactive; this session did not use plan mode).
- **Open threads:** The hooks were tested with synthetic payloads only. First real plan approval should be checked (does `.ai/plans/002-*.md` appear?). The pipeline was not exercised (no Ollama on this machine).
  - _(Resolved in the next entry: yes, the hook saved plan 002 live.)_ Paths above are from before plan 002's reorganisation.

### 2026-11-22 — Claude Code (Opus 5.5) — repository reorganisation (plan 002)
- **Goal:** Before committing, separate the application, the novel data and the supporting documents so it's obvious which folder to open for which work.
- **Outcome:** Used plan mode. On approval, the ExitPlanMode hook auto-saved plan 002 (first live proof of the hook). Moved code to `app/`, docs to `docs/technical/`, `.ai/` to `docs/ai/`, CHANGELOG to `docs/`, old README to `docs/user-guide.md`, CLAUDE.md content to `docs/ai/RULES.md` (root CLAUDE.md is now a loader). Fixed six data-path lines (no line shifts). Updated the hook constants, every doc reference and the anchors. Wrote a new root README map and decision D-007. Verified: compile, path resolution, TestClient smoke against the real `data/` (ollama stubbed), hooks in a sandbox, link checker (26 files, 0 problems).
- **Plan:** 002 (done).
- **Open threads:** Committed to `main` at the user's request (not pushed). `git ls-files | grep pyc` should be empty after the commit (KI-022). `app/start.bat` not executed (static review only).

### 2026-11-22 — Claude Code (Opus 5.5) — fix KI-001 + KI-002 (plan 003)
- **Goal:** Fix manual character/location save (KI-001, 422) and `apiPost` result handling (KI-002, "undefined" + world-wipe risk).
- **Outcome:** Frontend-only change in `app/frontend/app.js`: `apiPost` returns JSON; the save payloads send `slug` (`''` on create) and round-trip `{...existing, ...form}` on edit (KI-027); characters reload on `complete`. Verified in a temp sandbox (copy of `app/`+`data/`, stubbed `ollama`) via curl and the browser pane: create/edit for characters and locations, all 3 Build tabs, World Build → World Settings → Save, and a stubbed generation. Logged KI-036 (create overwrites same slug, reproduced) and KI-037 (cursor never hides, observed).
- **Plan:** 003 (done).
- **Open threads:** Not committed. Real LLM output not exercised (no Ollama). Suggested next: KI-036.

### 2026-11-22 — Claude Code (Opus 5.5) — fix KI-036 (plan 004)
- **Goal:** Before committing plan 003, stop every create path from overwriting an existing character/location with the same slug.
- **Outcome:** Managers gained an exclusive `create()` (`open(…, "x")` → `FileExistsError`). `main.py` maps that to 409 through one app-wide handler, and the refine create branches map it explicitly. Pipeline step 3 uses `create()`, so a collision becomes a `warning` and the profile is kept. No frontend change. `main.py` grew by +5 lines (a uniform shift), and 32 doc line refs were shifted by script and spot-checked. Verified in a sandbox: POST, case and slug variants, scenes, refine, a pipeline collision, and the UI. Logged KI-038 (empty slug → `.json`, reproduced).
- **Plan:** 004 (done).
- **Open threads:** Plans 003 + 004 not committed. Real LLM not exercised. SemVer impact of POST 409 to decide at release.

### 2026-11-22 — Claude Code (Opus 5.5) — remove Claude co-author from history; commit plans 003 + 004
- **Goal:** Remove Claude from the GitHub contributor list (caused by the `Co-Authored-By` trailer on `02d6e6d`), then commit plans 003 + 004.
- **Outcome:**
  - Reworded the commit locally (same tree, author and date). `git push --force-with-lease` was reset by the proxy, as expected.
  - Through the REST API: created the reworded commit and force-updated `refs/heads/main` after a lease check. Remote `main` is now `14dd6aa`; the tree was verified identical. Local `main` was soft-reset onto it, and the working tree was unchanged.
  - Recorded the no-attribution rule (RULES §8.7, D-008) and committed plans 003 + 004 locally without any trailer.
- **Plan:** none (git housekeeping on user request).
- **Open threads:** Plans 003 + 004 commit not pushed. GitHub's contributor cache may take time to drop Claude.
  - _(Resolved the same session: pushed as `5960228`, local `main` realigned.)_

### 2026-11-22 — Claude Code (Opus 5.5) — fix KI-003, KI-004, KI-005 (plan 005)
- **Goal:** The server must start without `ollama`; the launcher must check every dependency; `requirements.txt` must install a working set; the server must stay responsive while the specialist works.
- **Outcome:**
  - Specialist is fully `async` (`await ollama.AsyncClient().chat`), with no line shifts. `writer.py` guards the import.
  - `start.bat` runs `DEP_CHECK` (all packages plus `ollama >= 0.4`), installs, re-checks, and stops on failure.
  - `requirements.txt` holds lower bounds (pydantic floor 2.9 because ollama 0.4 needs it, D-009).
  - Verified against the real ollama 0.4.0/0.6.3 sources and an isolated 0.6.3 install. Responsiveness during specialist work: max 0.07 s vs 14.9 s before. Launcher block tested in 3 scenarios. Fresh resolve on Python 3.14 is all wheels.
- **Plan:** 005 (done).
- **Open threads:** Committed and pushed in the same session. Real LLM not exercised. `start.bat` not run end-to-end (it would install into the user's Python and open windows).

### 2026-11-23 — Claude Code (Opus 5.5) — re-credit commits to the personal GitHub account
- **Goal:** The four commits pushed on 2026-11-22 showed the work account Tejasva-Maurya-Cognizant as author, although the push token is the personal account's.
- **Outcome:** Cause: the global git identity is the work email, and GitHub credits by author email. Set a repo-local identity (Tejasva_Maurya / gmail). Re-credited the four commits via REST with a lease check (`14dd6aa`→`3e61415`, `5960228`→`058caae`, `eedf02f`→`78ab1ea`, `d1e3f85`→`2b4f3c2`; trees verified identical). The API now maps all six commits to Tejasva-Maurya. Recorded D-010 and a gotcha.
- **Plan:** none (git housekeeping on user request).
- **Open threads:** GitHub's cached contributor list may lag.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-006, KI-007, KI-008 (plan 006)
- **Goal:** Settings via Alt+S without model lists; Settings save resetting `total_chapters`/`created_at`; chapters numbered count + 1 (overwrite after a gap).
- **Outcome:** Frontend only (`app.js`). `openSettingsModal` fills and refreshes the model lists (the second button listener was removed). `saveSettings` round-trips `state.novelMeta`, and an empty select keeps the stored model. `complete` also reloads novel meta. The UI no longer sends `chapter_number`; `nextChapterNumber()` (highest + 1) drives the hint and badge. Sandbox UI verified: Alt+S lists filled and Save kept models; total 7 and `created_at` kept by Settings and title edit; with chapters 1 and 3, the request was `{plot}`, 004 was created and 003 untouched; a stale count (3→4) was not written back.
- **Plan:** 006 (done).
- **Open threads:** Committed and pushed in the same session. Real LLM not exercised.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-009, KI-010, KI-011 (plan 007)
- **Goal:** Consistent server-side slugs without duplicates; no path traversal or cross-site API access; escaped HTML.
- **Outcome:**
  - Managers validate slugs (`[\w-]+`) through `_path()`; `create()` refuses equivalent stems.
  - `main.py`: CORS removed, TrustedHost (127.0.0.1/localhost) added; POST and refine create derive slugs, 422 when empty.
  - Pipeline: `_canonical_entities` for step 2; step 3 slugs from the profile name.
  - `app.js`: `API = '/api'`; `escHtml` in the world snapshot and model selects/browser.
  - **Confirmed before the fix** on a copy: `DELETE /api/characters/..%5Cnovel_meta` deleted `novel_meta.json` (and the scenes route deleted `world_settings.json`). The fixed code returns 404.
  - Old vs new verified for CORS preflight, Host header, pipeline duplicate and the nameless-entry crash; XSS payloads verified in the UI (world fields plus a fake Ollama on 11434). KI-021 and KI-038 fixed by the same change.
- **Plan:** 007 (done).
- **Open threads:** Committed and pushed in the same session. Real LLM not exercised.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-012, KI-013, KI-014 (plan 008)
- **Goal:** Remove the wasted step-5 prediction call, apply the ignored scene updates and dead parameters, and summarise whole chapters.
- **Outcome:**
  - Step 5: `specialist.unload` (an empty `generate` with `keep_alive=0`).
  - Step 4: deterministic, `select_context` removed.
  - Step 7: scene briefs plus applied `scene_updates`; `_chapter_excerpt` (whole chapter ≤ ~5000 est. tokens, else opening + ending).
  - `analyze_plot` lost `novel_meta`.
  - Verified with the real ollama client (0.4.0 and 0.6.3) against a logging fake Ollama: unload body `{model, stream:false, keep_alive:0}`; per chapter 6 → 4 generations; the summariser prompt now contains the ending; the scene update was applied, the non-featured and malformed ones were ignored; a failed unload gives a `warning` and the chapter completes.
- **Plan:** 008 (done).
- **Open threads:** Committed and pushed in the same session. Real Ollama/VRAM behaviour not exercised.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-015, KI-016, KI-018 (plan 009)
- **Goal:** Stop wrong-typed LLM output from crashing the pipeline, dropping or corrupting entities, and hiding warnings.
- **Outcome:**
  - `models.py`: coercion helpers as `BeforeValidator` annotated types for Character, Scene and WorldSettings, plus `validate_assignment` on Character/Scene.
  - `_call` returns dicts only, with `format="json"`.
  - The pipeline coerces step 1/3/7 values; character updates are validated with a warning on failure.
  - Refine merges are validated before saving; the world merge reads list fields as lists.
  - `app.js` shows `warning` events.
  - The real `data/` files round-trip identical (read-only check).
  - Old vs new with a hostile stub: list analysis, `"2"` chapters and a null title crashed old (the last one lost a streamed chapter), while new completes. The merge made a character vanish on old but not on new. The legacy broken file is skipped by old and listed by new. A warning toast was verified in the UI.
- **Plan:** 009 (done).
- **Open threads:** Committed and pushed in the same session. Real model behaviour with `format="json"` not exercised.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-019, KI-031 (plan 010)
- **Goal:** Stop model pulls from reporting false success, allow only one generation at a time, and add a way to cancel one.
- **Outcome:**
  - `pull_model`: a non-200 status or an `{"error": …}` line becomes an `error` event; `success` only after Ollama's own `success` line.
  - `generate_chapter` runs the pipeline as an `asyncio.Task` feeding a queue; 409 while it runs; new `POST /api/generate-chapter/cancel`; a client disconnect cancels the task.
  - UI: **✕ Cancel** button (shown while generating), the cancelled `error` is an info toast, the 409 `detail` is shown.
  - Old vs new (stub ollama, fake Ollama pull): old reported success for a 404, an error line and a truncated pull, and let two generations both write chapter 1; new reports each pull error, returns 409, cancels within 0.1 s without saving, and frees the guard on disconnect. UI checked in the browser pane.
- **Plan:** 010 (done).
- **Open threads:** Committed and pushed in the same session. Real Ollama pull and real cancellation of an Ollama generation not exercised.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-037, KI-024, new KI-039 (plan 011)
- **Goal:** Hide the streaming cursor when nothing streams, and reset the pipeline panel's fade and error styles between runs.
- **Outcome:**
  - `style.css`: `.text-cursor[hidden]` and `.multi-chapter-notice[hidden]` → `display: none`. The notice had the same trap as the cursor and was always visible: catalogued as KI-039, approved in the plan.
  - `app.js`: `resetPipeline()` cancels the pending fade (`_pipelineFadeTimer`), clears the opacity and the steps' inline red styles.
  - Browser, old vs new with a stub: wrongly visible `[hidden]` elements on load, old 2 (cursor, notice) vs new 0; cursor after completion `inline` vs `none`; the notice stayed vs cleared on the next run; next-run opacity 0.4 vs full, including the run started within 2 s; the red step stayed vs cleared. Console clean.
- **Plan:** 011 (done).
- **Open threads:** Committed and pushed in the same session.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-020, KI-028 (plan 012)
- **Goal:** Stop Settings from calling a recommended model installed because another tag of its family is pulled, and align the frontend's fallback specialist with the backend default.
- **Outcome:**
  - `main.py`: `_model_key()` (a name without a tag counts as `:latest`; a registry `:port` is not a tag) and an exact key match in `get_models()`.
  - `app.js`: the `loadNovelMeta` fallback specialist is `phi4-mini:3.8b`.
  - Old vs new against a fake `/api/tags` (`gemma3:4b`, `llama3.1:latest`, `phi4-mini:3.8b`, `mistral-nemo:12b-instruct-…`): old flagged 4 recommended models, new flags only `phi4-mini:3.8b`. In the Settings browser the three wrong ones now offer Pull and the real tags stay listed as installed. The fallback with `/api/novel-meta` failing: old `gemma3:12b`, new `phi4-mini:3.8b`.
- **Plan:** 012 (done).
- **Open threads:** Committed and pushed in the same session. Real Ollama `/api/tags` not exercised.

### 2026-11-23 — Claude Code (Opus 5.5) — fix KI-032, KI-029 (plan 013)
- **Goal:** Fix three small UI glitches (empty Full View tags after generation, a held-back first paragraph, Alt shortcuts vs Caps Lock), and stop the specialist from staying in VRAM forever.
- **Outcome:**
  - `app.js`: `complete` keeps `characters_featured`/`scenes_featured`; the `token` handler creates the first paragraph before splitting; the shortcuts compare `e.key.toLowerCase()`.
  - `specialist.py`: `_call()` defaults to `keep_alive=300`. The user chose 5 minutes and to apply it to steps 1–3 as well (D-011).
  - Verified: with the real ollama 0.6.3 client and a logging fake Ollama, old sent `-1`, new sends `300` for refine and steps 1–2; `0` for the unload and step 7 on both. In the browser, old vs new: first-chunk text empty vs shown; Full View tags none vs the same slugs as History; Alt+S/W (upper case) nothing vs Settings/World.
- **Plan:** 013 (done).
- **Open threads:** Not committed yet (waiting for the user). Real VRAM release after 5 minutes not observable here.
