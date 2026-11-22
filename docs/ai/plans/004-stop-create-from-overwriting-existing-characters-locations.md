---
id: 004
title: "Stop create from overwriting existing characters/locations (KI-036)"
status: done
approved: 2026-11-22T22:04:04+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 88b824af4aa771df97516877838f8356fbc46a0d4de07a72b5d06f7e05ef6ea8
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Stop create from overwriting existing characters/locations (KI-036)

## Context
Plan 003 made **+ New Character / + New Location** work, which made KI-036 reachable from the UI. If a new name slugifies to an existing slug (`"Elder Wu"` and `"elder  wu"` both give `elder_wu`), `POST` silently **replaces the whole existing record**. I reproduced this in plan 003's sandbox: type, arc notes and chapters 3/5 were all lost.

Two other create paths have the same flaw:
- **Refine create** (Build tab without "Update Existing"), using the LLM's slug.
- **Pipeline step 3**, when the specialist calls an existing entity "new" and its profile reuses an existing slug. This would wipe arc notes, abilities and relationships that earlier chapters built up.

The user asked to fix KI-036 before committing plan 003.

**Done means:** no create path can overwrite an existing file.
- The API answers **409 Conflict** with a readable `detail`.
- The UI shows the error and keeps the form open, so the user can rename.
- The pipeline keeps the existing profile and emits a `warning`.
- Edit (`PUT`) and refine **Update Existing** are unchanged.

## Evidence (read this session)
- `main.py:69-75` and `:102-108` derive the slug when it is empty, then call `save()` without any existence check.
- Refine create: `main.py:327-333` and `:354-360` (`Character(**result)` → `save` inside `try/except Exception` → 500).
- Pipeline step 3: `chapter_pipeline.py:78-92` calls `save()` inside `try/except Exception` → `warning` SSE.
- Managers: `save()` opens with `"w"`, which always overwrites (`character_manager.py:44-48`, `scene_manager.py:44-48`). Existing pattern: `delete(slug) -> bool`, which `main.py:91` turns into `HTTPException(404)`.
- The frontend needs no change. `apiPost` throws on any non-2xx status (`app.js:131-134`). `saveCharacter`/`saveScene` show the toast and keep the modal open, because `closeModal` sits inside `try`. The refine handlers show `✗ Error: …`.

## Approach
1. **Managers get `create(entity)`**, appended at the end of `character_manager.py` and `scene_manager.py`, so no line numbers shift.
   - It opens the file with mode **`"x"`** (exclusive create). That is atomic, never overwrites, and also catches case-only collisions on Windows.
   - On `FileExistsError` it re-raises `FileExistsError("Character '<slug>' already exists")`, without the absolute path.
   - `save()` stays the upsert used by PUT, merges and step 7.
2. **`main.py`:**
   - Line 16 imports `JSONResponse`.
   - One exception handler, `@app.exception_handler(FileExistsError)` → `409 {"detail": str(exc)}`, inserted right after the CORS block. That is +5 lines, a uniform shift for every line from 38 on.
   - `create_character`/`create_scene`: `save(...)` becomes `create(...)` (same line).
   - Refine create branches: `save` becomes `create`, and the existing `except` raises `HTTPException(409 if isinstance(e, FileExistsError) else 500, …)` (same line count). The refine 409 reads "Could not create character: Character 'x' already exists".
3. **`chapter_pipeline.py:81` and `:89`:** `save` becomes `create`, with no line shift. A collision lands in the existing `except`, which emits `warning "Could not save character profile: Character 'x' already exists"`. The existing profile is kept and stays in `chars_dict` for context. Step 7 still updates `last_seen_chapter` as before.
4. **Frontend:** no change. The 409 toast reads `Failed to save character: POST /characters failed: 409 — {"detail":"Character 'x' already exists"}`, the same raw-text format as every other error today.

## Contract / data impact
- **API:**
  - `POST /api/characters` and `POST /api/scenes` return **409** when the slug exists. They previously overwrote with 200.
  - The refine create branches return **409** (previously an overwrite).
  - No route, payload shape or field changes.
- **SSE:** no new event types. Step 3 now emits the existing `warning` event in one more case.
- **SemVer note:** POST no longer upserts. The bundled UI is the only client and treats it as an error. If you count third-party API clients, that is "incompatible", which matters when choosing the next version at release time.
- **`data/`:** no schema change.

## Docs to update (RULES §6)
- `docs/technical/04`: 409 on POST characters/scenes and on refine create; drop the "silently overwritten" warning.
- `docs/technical/02`: W3.3/W3.4 (step 3 keeps the existing profile → `warning`), W4 diagram create branch, W6 create row.
- `docs/technical/03`:
  - §2.3 managers table: `create()`
  - §3 error-handling row: 409 via the `FileExistsError` handler
  - step 3 note
- `docs/technical/05`: atomicity row (create is exclusive; save overwrites).
- `docs/technical/07`: replace the ⚠ overwrite notes with "a taken name shows an error; rename or edit the existing one".
- `docs/technical/08`: new FAQ entry for the 409 "already exists" error, appended as **A14** so nothing is renumbered.
- `docs/technical/09`: KI-036 → Fixed in Unreleased [plan 004]. If the empty-slug edge case below reproduces, log it as a new KI, not fixed here.
- **Line references:** every `main.py:N` with N ≥ 38 → N+5, in docs 01, 02, 03, 04, 06, 09, `docs/README.md` and `gotchas.md`. That is about 40 references, in the formats `N`, `N-M`, `N/M`, `N,M`, plus bare `` `:N` `` after a `main.py` mention on the same line.
  - A script applies the shift and prints every change for manual review.
  - `chapter_pipeline.py`, the managers and `app.js` keep their line numbers.
- `docs/CHANGELOG.md` → `[Unreleased]` → **Fixed**: one line `[plan 004] [KI-036]` that names the 409.
- `docs/ai/memory/`:
  - `gotchas.md`: replace the "POST create overwrites silently" entry with "create returns 409, so delete `zz_test_` entities before re-running tests".
  - `project-state.md`, `session-log.md`.
- Plan 004: status, execution log, outcome, then `reindex`.

## Verification
1. `py -m py_compile` on the changed backend files. `node --check app/frontend/app.js` (unchanged, sanity only).
2. **Sandbox as in plan 003:** a temp copy of `app/` + `data/`, plus the `ollama` stub. The stub additionally returns, for the pipeline:
   - an analysis that mentions one character
   - a resolution marking it `new` with slug `zz_test_hero`
   - a profile with slug `zz_test_hero`
3. **curl:**
   - POST a new name → 200.
   - POST the same name again, and a variant that slugifies the same (`"ZZ test  hero"`) → **409** `Character 'zz_test_hero' already exists`. The file's SHA-256 is unchanged.
   - The same checks for scenes.
   - PUT edit → still 200.
   - Refine create twice → 200, then **409**, with the existing file unchanged.
   - Refine with `existing_slug` (merge) → still 200.
   - `POST /api/generate-chapter` with the colliding profile → the stream contains `warning … already exists`, completes, and `zz_test_hero` keeps its profile (only `last_seen_chapter` changes).
   - Edge-case probe: POST name `"???"`, which slugifies to `""`. Record what happens, and log it as a KI if broken.
4. **UI in the browser pane** (temporary `.claude/launch.json` + launcher, deleted afterwards): **+ New Character** with an existing name → error toast with 409, modal stays open; rename → saves. Browser console clean.
5. **Cleanup:**
   - Stop the server.
   - Delete the sandbox, stub, launcher and `launch.json`.
   - `git status --porcelain data/` is empty.
   - `git status` shows only the intended files.
- **Not verifiable:** real LLM output (no Ollama).

## Risks & rollback
- **Catch-all handler.** The global `FileExistsError` → 409 handler also catches any other `FileExistsError` raised in a request. Nothing else raises it today: `mkdir` uses `exist_ok=True`. Documented in 03 §3.
- **"Upsert" callers.** Any external script relying on POST as an upsert now gets 409. Such scripts should use PUT.
- **Pipeline.** An LLM-misresolved "new" entity now keeps the old profile instead of overwriting it, which is the intended safe direction.
- **Rollback:** revert `main.py`, `chapter_pipeline.py`, the two managers and the doc edits. No data migration involved.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 004]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **Fixed-KI evidence kept as-is.** The evidence lines of KI-001 and KI-036 in doc 09 describe the pre-fix code, so the line-shift script skipped them on purpose. 32 other `main.py` refs were shifted.
- **Bytecode cleanup.** `py -m py_compile` created 13 `cpython-314` `.pyc` files under `app/`. They were deleted (RULES §9 cleanup); the pre-existing `cpython-313` caches were left alone.
- **KI-038 logged, not fixed.** The empty-slug probe reproduced a defect, logged as KI-038 (Low).

## Outcome
**Shipped** (uncommitted):
- `character_manager.create()` / `scene_manager.create()`, appended at the end of each file.
  - Exclusive `open(…, "x")`; raises `FileExistsError("Character 'x' already exists")`, without the path.
- `app/backend/main.py`:
  - imports `JSONResponse`
  - `file_exists_handler` (`FileExistsError` → 409) right after the CORS block (+5 lines)
  - POST characters/scenes call `create()`
  - refine create branches call `create()` and map `FileExistsError` → 409
- `app/backend/pipeline/chapter_pipeline.py:81,89`: `create()` (no line shift); a collision becomes the existing `warning` event.
- No frontend, SSE-type or data-schema change.

**Files changed:**
- `app/backend/main.py`
- `app/backend/managers/character_manager.py`
- `app/backend/managers/scene_manager.py`
- `app/backend/pipeline/chapter_pipeline.py`
- docs 01, 02, 03, 04, 05, 06, 07, 08, 09
- `docs/CHANGELOG.md`
- `docs/ai/memory/` (`gotchas.md`, `project-state.md`, `session-log.md`)

**KI fixed:** KI-036. **New:** KI-038 (Low, reproduced): a name without letters/digits gets an empty slug and is saved as `.json`, which can't be edited or deleted from the UI.

**CHANGELOG:** `[Unreleased]` → Fixed, one line `[plan 004] [KI-036]`.

**Verification** (2026-11-22):
1. `py -m py_compile` passed on all backend files.
2. Line counts: `main.py` 392 → 397, a uniform +5 from line 38 (the only other diffs are the 6 edited lines). `chapter_pipeline.py` stays at 249.
3. Sandbox: a temp copy of `app/` + `data/` served on `127.0.0.1:8000` through the browser-pane launcher. The stub `ollama` returned canned refine JSON plus a step-2/3 collision on `zz_test_hero`.
4. curl:
   - POST a new character → 200.
   - These all returned **409** `Character '…' already exists`, with the file's SHA-256 unchanged:
     - the same name
     - `"ZZ test  hero!"`
     - an explicit slug `ZZ_TEST_HERO` (case-only, NTFS)
   - Scenes: 200, then 409, file unchanged.
   - PUT → 200.
   - Refine character create → 200, then **409** `Could not create character: …`, file unchanged. The same for scene. Refine merge with `existing_slug` → 200.
   - Generate chapter → the stream had `warning "Could not save character profile: Character 'zz_test_hero' already exists"` and then `complete`. The profile kept `arc_notes='edited via PUT'`, with `appearance` not overwritten.
5. UI:
   - **+ New Character** "Zz Test Hero" showed the toast `✕ Failed to save character: POST /characters failed: 409 — {"detail":"Character 'zz_test_hero' already exists"}`. The modal stayed open with the input kept, and the existing file was untouched.
   - Renaming to "Zz Test Hero Two" saved it, and the modal closed.
   - Console: only the browser's own network log of the deliberate 409. No script errors.
6. Cleanup:
   - The sandbox, stub, launcher, `.claude/launch.json` and temp files were deleted, and port 8000 is free.
   - `git status --porcelain data/` is empty.

**Not verified:** real LLM output (no Ollama).

**Follow-ups:**
- KI-038: reject an empty derived slug with 422.
- Optional polish: show `detail` instead of the raw JSON in error toasts (affects every API error, not just 409).
- When releasing: decide SemVer for "POST no longer upserts".
