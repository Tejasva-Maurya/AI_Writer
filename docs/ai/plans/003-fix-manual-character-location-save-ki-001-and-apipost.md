---
id: 003
title: "Fix manual character/location save (KI-001) and apiPost result handling (KI-002)"
status: done
approved: 2026-11-22T21:28:57+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 3dd66132adfdd624e3fec1f058a352ec49d0dc6b45b76c93e497b8873c1fd3d8
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Fix manual character/location save (KI-001) and apiPost result handling (KI-002)

## Context
The user asked to fix the two High-severity frontend defects first:
- **KI-001**: the **+ New Character / + New Location** modals, card **Edit**, profile **Edit** and `Alt+N` always fail with HTTP 422, because the payload has no `slug`, which `Character`/`Scene` require.
- **KI-002**: `apiPost` returns the raw `Response`, while `apiGet`/`apiPut` return JSON. The three Build tabs therefore show "Created: undefined". After a World Build, `state.world` holds a `Response` object, so opening **World Settings** and pressing Save **overwrites `world_settings.json` with blanks** (data loss).

Fixing KI-001 makes Edit work for the first time. That exposes two data-loss paths, which this plan closes in the same change:
- **KI-027**: edit is a full replace. Fields the modal doesn't show (`first_appeared_chapter`, `last_seen_chapter`) would reset to 1.
- **Stale state**: step 7 of the pipeline updates characters on disk, but the frontend never reloads them after a generation. An Edit opened after a chapter would write the old values back.

**Done means:** manual create and edit of characters and locations save; edits keep the fields the modal doesn't show; the Build tabs show the real name; World Build followed by a World Settings save keeps the world.

## Evidence (read this session)
- `app/frontend/app.js:125-136`: `apiPost` returns `res`. It has exactly 5 callers (grep): `:752-753` and `:882-883` check `res.ok`; `:1528`, `:1575` and `:1614` use the value as parsed data. `generateChapter` and `pullModel` call `fetch` directly, so this change doesn't affect them.
- `app.js:727-741` (`saveCharacter`) and `:862-871` (`saveScene`) build the payload without `slug`. `app/backend/models.py:13` and `:32` make `slug` required.
- The server already handles an empty slug: `main.py:72-73` and `:105-106` derive it from the name on create, and `main.py:84` and `:117` force the slug from the URL on PUT.
- KI-027: the modal never sends the chapter-tracking fields, so the model defaults of 1 apply (`models.py:25-26`, `:39`).
- Stale state: `chapter_pipeline.py:212-232` updates arc notes, abilities, cultivation level, relationships and `last_seen_chapter` on disk. The `complete` handler reloads only the chapters (`app.js:528`), and the edit modal is filled from `state.characters` (`app.js:698`).

## Approach: change only `app/frontend/app.js`, no API or model change
Making `slug` default to `""` in `models.py` (KI-001 option b) was rejected. LLM output that omits a slug would then pass validation in pipeline step 3 (`chapter_pipeline.py:80`) and in refine create (`main.py:329/356`), and be saved as `data/characters/.json`. The frontend fix keeps the API, the data and the event contract unchanged.

## Steps (all in `app/frontend/app.js`)
1. **KI-002.** `apiPost` returns `res.json()`, like `apiGet` and `apiPut`. In `saveCharacter` and `saveScene`, replace `const res = await apiPost(…); if (!res.ok) throw …` with `await apiPost(…)`. `apiPost` already throws on any non-2xx status. The refine handlers then work unchanged.
2. **KI-001 + KI-027 in `saveCharacter`.** Find the existing record with `state.characters.find(c => c.slug === state._editingCharSlug)`, or use `null` on create. Build the payload as `{ ...existing, slug: state._editingCharSlug || '', name, …form fields }`.
   - Create sends `slug: ''`, and the server derives it from the name.
   - Edit carries every field the modal doesn't show.
3. **Same in `saveScene`**, using `state._editingSceneSlug` and `state.scenes`.
4. **Stale-state guard.** In the `generateChapter` `complete` handler, change `await loadChapters();` to `await Promise.all([loadChapters(), loadCharacters()]);`. Scenes are left out because the pipeline never updates existing scenes (KI-013), and new scenes already trigger a reload.

## Contract / data impact
**None.** Routes, payload shapes, status codes, event types and Pydantic fields are unchanged. The UI now sends `slug`, which is already part of the documented `Character`/`Scene` shape. Files in `data/` keep the same format.

## Docs to update (RULES §6)
- `docs/CHANGELOG.md` → `[Unreleased]` → **Fixed**:
  - KI-001: manual save works
  - KI-002: Build tabs show the real name, and World Build no longer leaves a broken copy that can wipe the world
  - KI-027: edits keep chapter tracking, and characters reload after a generation
  - Each line tagged `[plan 003]`.
- `docs/technical/09`:
  - KI-001, KI-002 and KI-027 → `Fixed in Unreleased [plan 003]`, in both the summary table and the detail sections.
  - Add **KI-036**: "Create silently overwrites an existing character/location with the same derived slug (no 409)". It is now reachable from the UI. Log it only after reproducing it in the sandbox. Not fixed here.
- `docs/technical/08`: rewrite A5, A6 and A7 as "fixed". Keep the advice on restoring a world file wiped under 1.0.0. Don't renumber.
- `docs/technical/07`: remove the ⚠ workaround notes (§ quick start lines 89-90, characters line 131, locations line 137).
- `docs/technical/02`:
  - W4: diagram line 223
  - W5: step 4
  - W6: the ⚠ notes become "edit round-trips all fields"
  - W3: mention the character reload on `complete`
- `docs/technical/03` §4: the `apiPost` row and the note under it.
- `docs/technical/04`: the 422 note at line 67.
- `docs/technical/01`: the example in the line-32 warning.
- **Line references:** recompute every `app.js:N` reference after line 720 in docs 02, 03, 06 and 09 from the edited file, by grepping the function names. About 25 references shift by +2 or +4. Plans and the session log are history and are not changed.
- `docs/ai/RULES.md` §3: in the `app.js` row, drop the "`apiPost` returns a raw Response" note.
- `docs/ai/memory/`:
  - `gotchas.md`: remove the `apiPost` entry. Reword the `slug` entry: still required by the API, and the UI now sends `''` on create.
  - `project-state.md`: active plan, next up.
  - `session-log.md`: new entry.
- Plan 003: set `in-progress`, keep the execution log, then set `done` with an outcome, and run `reindex`.

## Verification
1. `node --check app/frontend/app.js`.
2. **Sandbox, so the real `data/` is never touched:**
   - Use `mktemp -d` and copy `app/` and `data/` into it. The managers resolve `parents[3]/data`, which then points at the sandbox copy.
   - Put a stub `ollama` module in a separate temp folder on `PYTHONPATH`:
     - `chat()` returns canned JSON for the character, scene and world refine prompts, and `{}` otherwise.
     - `AsyncClient().chat(stream=True)` yields a few text chunks.
   - Confirm port 8000 is free; the frontend hard-codes it (KI-021).
   - Start `py -m uvicorn main:app --host 127.0.0.1 --port 8000` from the sandbox `app/backend` in the background.
3. **API checks with curl:**
   - POST `/api/characters` with the new payload (`slug:""`) returns 200 and creates a `zz_test_…json` file.
   - The old payload with no `slug` still returns 422, which shows the contract is unchanged.
   - PUT keeps the round-tripped fields.
   - The same three checks for scenes.
   - POST the same name twice to confirm the overwrite (evidence for KI-036).
4. **UI in the browser pane.** A temporary `.claude/launch.json` attaches to `http://127.0.0.1:8000` and is deleted afterwards. Check that:
   - New Character saves.
   - Edit keeps the chapter numbers after I set first/last chapter to 3/5 in the sandbox file.
   - New Location and Edit Location both save.
   - Character Build and Scene Build show "Created: <name>".
   - After a World Build, the snapshot shows data, the World Settings modal is pre-filled, and Save keeps the values in the sandbox `world_settings.json`.
   - Generate Chapter (stubbed writer) reaches `complete`, and the network log shows a `GET /api/characters` reload.
   - The browser console shows no errors.
5. **Cleanup:**
   - Stop the server.
   - Delete the sandbox, the stub and `launch.json`.
   - `git status` shows only `app/frontend/app.js` and docs.
   - `git status --porcelain data/` is empty.
- **Not verifiable here:** real LLM output. Ollama isn't installed, so the pipeline runs only against the stub.

## Risks & rollback
- Changing what `apiPost` returns affects every caller. All 5 are covered above.
- The `...existing` spread sends whatever the browser holds. Stale data is covered by the reload after a generation. Refine already reloads after each call. Two open tabs could still conflict, which is the separate concurrency issue KI-031.
- KI-036 (overwrite on create) is out of scope. It is logged and offered as the next fix.
- **Rollback:** revert `app/frontend/app.js` (one file) and the doc edits. Nothing in `data/` changes.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 003]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **Comments.** Added a one-line comment above each payload explaining the spread and the slug, plus a short trailing comment on the `complete` reload. The shift for later `app.js` lines is therefore +3/+6, not +2/+4. Every living-doc reference was recomputed (22 refs in docs 02, 03, 06, 09, plus the "1890 LOC" count in doc 01).
- **Browser pane.** It can't attach to a URL on this install. `.claude/launch.json` instead pointed `py` at a temp launcher script, kept with the stub outside the repo, that served the sandbox. Both were deleted afterwards.
- **KI-037.** Found during UI verification (the `▍` cursor never hides). Pre-existing CSS, unrelated to this change. Logged as KI-037, not fixed.

## Outcome
**Shipped** (uncommitted). Only `app/frontend/app.js` changed:
- `apiPost` returns `res.json()`.
- `saveCharacter`/`saveScene` send `slug` (`''` on create), spread the existing record on edit, and no longer check `res.ok`.
- The `generateChapter` `complete` handler reloads chapters **and characters**.
- No backend, API, event or data-schema change.

**KIs fixed:**
- KI-001
- KI-002
- KI-027, on the UI side; `PUT` stays a full replace for other clients.

**New KIs:**
- KI-036 (Medium, reproduced): POST create silently overwrites an existing entity with the same slug.
- KI-037 (Low, observed): the text cursor never hides.

**CHANGELOG:** three `[Unreleased]` → **Fixed** lines, for KI-001, KI-002 and KI-027.

**Docs updated:**
- `docs/technical/01`, `02` (W3.4, W4, W5, W6), `03` §4.3/§4.4, `04`, `06` (line refs only), `07` §4/§5.3/§5.4, `08` A5–A7, `09`
- `docs/ai/RULES.md` §3
- `docs/ai/memory/`: `gotchas.md`, `project-state.md`, `session-log.md`

**Verification** (2026-11-22):
1. `node --check app/frontend/app.js` passed.
2. Sandbox: a temp copy of `app/` + `data/`, served by uvicorn on `127.0.0.1:8000`. A stub `ollama` returned canned refine JSON and streamed 3 fake chapter tokens.
3. curl:
   - The new create shape returned 200, with slug `zz_test_hero` derived from the name.
   - The old shape without `slug` still returned 422 (contract unchanged).
   - PUT with the round-tripped record kept first/last = 3/5.
   - Scenes behaved the same (kept `first_appeared_chapter` = 4).
   - KI-036 reproduced: a second POST with the same name replaced the edited record.
4. Browser pane:
   - Card **Edit** kept 3/5 and saved the new arc notes (PUT 200).
   - **+ New Character** and **+ New Location** created `zz_test_ui_new` / `zz_test_ui_place`.
   - Location **Edit** kept `first_appeared_chapter` = 4.
   - Character and Scene Build showed "✓ Created: Zz Test Refined Hero / Place".
   - World Build merged the stub values into the snapshot; the World Settings modal opened pre-filled; Save kept `genre_tags`/`factions` on disk.
   - Generate Chapter finished all 7 steps, with `GET /api/chapters` and `GET /api/characters` after `complete`.
   - The console had no warnings or errors.
5. Cleanup:
   - The sandbox, stub, launcher and `.claude/launch.json` were deleted, and port 8000 is free.
   - `git status --porcelain data/` is empty: the real novel was never touched.

**Not verified:** real LLM output (no Ollama on this machine).

**Follow-ups:** KI-036 (409 on create) is the natural next fix. KI-037 is a one-line CSS fix.
