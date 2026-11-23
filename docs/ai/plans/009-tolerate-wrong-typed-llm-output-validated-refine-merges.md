---
id: 009
title: "Tolerate wrong-typed LLM output, validated refine merges, visible warnings (KI-015, KI-016, KI-018)"
status: done
approved: 2026-11-23T16:01:22+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 7b5a52caa8cd5f1aa43984850be89e6e79f02cdad34ab3a109f42aee0854a931
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Tolerate wrong-typed LLM output, validated refine merges, visible warnings (KI-015, KI-016, KI-018)

## Context
The user asked to fix KI-015, KI-016 and KI-018. All three come from LLM output with the wrong type or shape (read this session):
- **KI-015, the pipeline crashes on wrong types:**
  - `if estimated_chapters > 1` (`chapter_pipeline.py:74`) raises for `"2"`/`null`.
  - `entity_mentions.get(...)` and the `+` of its lists break when the analysis isn't the expected shape.
  - `_extract_json` can return a JSON **list**, so `.get` fails.
  - In step 7, `Chapter(title=None)` raises **after the chapter was written**, so the whole chapter text is lost.
  - `char_updates.items()`, `updates.get(...)` and `char.abilities + "text"` crash on non-dict or non-list values.
- **KI-016, entities are dropped or corrupted:**
  - `Character(type="supporting")` and `Character(age=17)` raise (re-verified this session), so step-3 profiles are dropped and refine create returns 500.
  - Refine **merge** uses `setattr` without validation (`main.py:327`, `:357`), so invalid values are saved and the file stops loading: the character vanishes from the sidebar and later edits return 500.
  - Step 7 assigns `arc_notes`/`cultivation_level` the same way, and `relationships.update()` mutates in place.
  - The step-3 template hard-codes `"type": "main"` and `"age": "17"`, which biases auto-created characters to MAIN CAST.
- **KI-018:** `warning` events (step 3 profile failures, step 5 unload failure) have no handler in `generateChapter` (`app.js:466-550`), so they are silently dropped.
- **Facts checked this session:**
  - Pydantic 2.13.4: `field_validator(mode="before")` coerces, and `ConfigDict(validate_assignment=True)` runs the same validators on attribute assignment and raises `ValidationError` for invalid values or unknown attributes.
  - `py -I` hides the user-site Pydantic, so non-isolated `py` is used for checks.

**Done means:**
- Wrong-typed LLM values are coerced into valid models: no dropped profiles, no unloadable files.
- No pipeline step crashes on wrong types: the chapter is always saved once written.
- Files that older versions saved with wrong types load again.
- Warnings reach the user as toasts.

## Approach
1. **`app/backend/models.py`: coercion in one place.**
   - Module-level helpers: `as_text` (None→"", numbers→str, list→"a, b", dict→"k: v; …"), `as_optional_text` (None/""/"null"/"none"→None), `as_str_list` (None→[], "x"→["x"], items→text, empties dropped), `as_str_dict` (dict→str keys/values, else {}), `as_int(v, default)` (int/float/numeric str, else default).
   - `mode="before"` validators on **Character**, **Scene** and **WorldSettings**:
     - text fields → `as_text`
     - `age`/`cultivation_level` → `as_optional_text`
     - list fields → `as_str_list`
     - `relationships` → `as_str_dict`
     - chapter ints → `as_int(…, 1)`
     - `type` → `main` if it reads "main", otherwise `temporary`
     - `name`/`slug` keep None (still a validation error, nothing is invented)
   - `validate_assignment=True` on Character and Scene, so every `setattr` is validated and coerced.
   - No field added, renamed or removed, and valid values pass unchanged. To be verified against the real `data/` files, read-only.
2. **`agents/specialist.py`:**
   - `_call` returns `{}` unless the parsed JSON is a dict.
   - Specialist chats pass `format="json"` (Ollama JSON mode, the fix the KI suggests); the writer is unchanged.
   - Step-3 template: `"type": "temporary"` plus one rule line ("main" only for central recurring characters), and `"age": "age as text, or null"`.
   - No `num_ctx`/`temperature`/`keep_alive` change.
3. **`pipeline/chapter_pipeline.py` (KI-015):**
   - Step 1: `estimated_chapters = as_int(…, 1)`; `tone` is text, defaulting to "action"; `entity_mentions` is rebuilt as `{characters: as_str_list, locations: as_str_list}` from a dict only.
   - Step 3: iterate only lists, and only dict entries.
   - Step 7:
     - `Chapter` text fields go through `as_text`, and an empty title → `Chapter N`.
     - `character_updates`/`scene_updates` are processed only as dicts, with per-entity `try` → `warning`.
     - Character changes are built and validated (`Character(**{...})`): abilities as an order-preserving union, relationships merged by assignment.
4. **`main.py` refine merges (KI-016):**
   - Character/scene: only known model fields (`model_fields`), minus slug/name/first_appeared_chapter. The merged dict is validated with `Character(**…)`/`Scene(**…)` before saving; a validation error → 500 "Could not merge …" and **nothing is saved**, so the existing file stays loadable.
   - World: values for list fields go through `as_str_list` before the de-duplicating merge, so a string can't replace the whole list. Then `WorldSettings(**…)` coerces the rest.
5. **`app/frontend/app.js` (KI-018):** add a `warning` handler to the `generateChapter` map: `showToast(data.message, 'warning', 6000)` and `console.warn`. The `toast-warning` style already exists (`style.css:1802`).

## Contract / data impact
- **API:** routes and shapes unchanged. Bodies are now coerced where they used to give 422 (e.g. `"age": 17` → `"17"`, `"type": "supporting"` → `temporary`). A refine merge that still can't validate returns 500 without saving (it used to save a broken file).
- **SSE:** unchanged. The UI now handles `warning` (already in the contract).
- **`data/`:** schema unchanged. Files with wrong types (e.g. from the old merge bug) load again, coerced, and are rewritten valid on their next save. Valid files load unchanged.
- **LLM:** specialist requests add `format: "json"`; the step-3 template defaults to `temporary`.

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-015, KI-016 and KI-018 → Fixed [plan 009], with status lines.
- **`docs/technical/05`:** the coercion rules per field; previously unloadable files now load.
- **`docs/technical/04`:** lenient bodies (examples); refine merge validated, 500 without saving.
- **`docs/technical/03`:**
  - §2.1: the validators and `validate_assignment`
  - §2.4: `_call`, `format="json"` and the profile template
  - §3 prompt catalogue
  - §4: the `warning` handler
- **`docs/technical/02`:** W3.3 (steps 1/3/7 coercion), W3.4 `warning` row, W4 merge semantics, W5 list merge.
- **`docs/technical/06` §2.2:** `format: "json"` on specialist calls.
- **`docs/technical/08`:**
  - A2 table: drop the "'>' not supported" row, add the warning toast
  - A9/A10 (vanishing entity) → now loads
- **`docs/technical/07`:** generation warnings are shown.
- **`docs/ai/RULES.md` §3:** the `specialist.py` row notes the model coercion.
- **`docs/ai/memory/gotchas.md`:**
  - remove "Refine merge saves unvalidated values" and "Pydantic v2 does not coerce int → str" (both fixed)
  - add "models coerce LLM values; `validate_assignment` on Character/Scene, so in-place mutation (`.update()`, `.append()`) bypasses validation"
- **Line references:** the remap script with `models.py`, `specialist.py`, `chapter_pipeline.py`, `main.py` and `app.js` as sources, plus the W3.3 bare refs.
- **`docs/CHANGELOG.md` `[Unreleased]`:** Fixed KI-015/016/018 and Changed (`format=json`, the template default), each tagged `[plan 009]`.
- **`docs/ai/memory/`:** `project-state.md`, `session-log.md`.
- **Plan 009:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py_compile` (all backend), `node --check app/frontend/app.js`.
2. **Unit checks** (`py`, non-isolated):
   - **Coercion table:** `type` "supporting"/"Main", `age` 17, `abilities` "fly", `relationships` {"Bob": 3}, `cultivation_level` "null", `first_appeared_chapter` "3"/None, `micro_summary` None/list.
   - **Assignment:** `c.age = 20` → "20"; `c.nope = 1` → error.
   - **Missing name:** `name=None` → still a ValidationError.
   - **Real `data/` (read-only):** every character, scene and the world file loads, and `model_dump()` equals the stored JSON, so valid data is unchanged.
3. **Sandbox, old vs new** (temp copies; a stub `ollama` with modes, recording kwargs):
   - **Analysis is a JSON list:** old crashes; new completes.
   - **`estimated_chapters` "2" and `entity_mentions` a string:** old raises `TypeError`; new emits `multi_chapter` (2) and completes.
   - **Profile with `type` "supporting", `age` 17, `abilities` "flying":** old gives a warning and drops it; new creates it (`temporary`, "17", ["flying"]).
   - **Post-write with `chapter_title` None, `micro_summary` a list, `character_updates` holding a list `arc_notes`, a string `new_abilities` and a numeric relationship, plus a non-dict entry:** old crashes and **the chapter is not saved**; new saves the chapter as "Chapter N", the character is updated and still loads, and the bad entry is skipped.
   - **Refine merge with `type` "supporting", `age` 17:** old returns 200 and the character vanishes from `GET /api/characters`; new returns 200 and the character is listed with coerced values.
   - **A pre-existing broken file** (`type` "supporting" written to disk): old list skips it; new lists it.
   - **World refine with `genre_tags` a string:** old replaces the list (or 500s); new appends the string.
   - **The stub log** shows `format="json"` on specialist chats and not on the writer.
4. **UI (browser pane):** a generation whose step 3 fails and whose unload fails shows **warning toasts** with the messages; the console is clean.
5. **Cleanup:** stop the servers; delete the sandboxes, stubs and `launch.json`; delete `cpython-314` bytecode. `git status --porcelain data/` is empty.
- **Not verifiable:** real model behaviour with `format="json"` (no Ollama).

## Risks & rollback
- **Coercion can hide a genuinely wrong value**, e.g. a list flattened to "a, b". This is preferred over losing the entity or the chapter, and the values stay visible and editable in the UI.
- **`validate_assignment`** makes a wrong-typed assignment raise, where it used to save silently. All current assignments pass valid types; LLM-driven ones are wrapped in `try`/warning.
- **`format="json"`** could change output for some models. It is Ollama's documented JSON mode, the prompts already demand JSON, and `_extract_json` stays as a fallback.
- **Rollback:** revert `models.py`, `specialist.py`, `chapter_pipeline.py`, `main.py`, `app.js` and the docs. No data migration; coerced saves are valid under the old models too.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 009]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **Annotated types instead of per-field validators.** Coercion is implemented as reusable `Annotated[..., BeforeValidator(...)]` types (`Text`, `RequiredText`, `OptionalText`, `StrList`, `StrDict`, `ChapterNumber`). Same effect, fewer lines; field names, defaults and JSON schema unchanged.
- **One extra fix in step 7.** The "`last_seen` for featured characters" loop now checks the value rather than "has an update entry", so a character whose update was rejected still gets `last_seen_chapter` (found while writing the code).
- **Test harness.**
  - The first post-write-only run reused a stub module already imported by the running servers, so the new mode wasn't active. The servers were restarted, then the run was repeated.
  - The UI run showed the unload warning; the step-3 warning didn't fire because the hostile character already existed in that sandbox.
- **Doc 08 A10** (duplicate characters) still described the pre-plan-007 behaviour; corrected in passing.

## Outcome
**Shipped** (uncommitted):
- `models.py`:
  - coercion helpers (`as_text`, `as_required_text`, `as_optional_text`, `as_str_list`, `as_str_dict`, `as_int`, `as_character_type`) as annotated types on Character, Scene and WorldSettings
  - `validate_assignment=True` on Character/Scene
  - no field added, renamed or removed
- `agents/specialist.py`:
  - `_call` uses `format="json"` and returns dicts only
  - the step-3 template defaults to `temporary` (with a rule) and `age` "as text, or null"
- `pipeline/chapter_pipeline.py`:
  - step 1 coerces `tone`/`estimated_chapters`/`entity_mentions`
  - step 3 iterates only lists of dicts
  - step 7 coerces the title and summaries, and validates character updates (order-preserving abilities union, relationships by assignment) with a warning on failure
- `main.py`:
  - refine merges: known fields only, validated before saving (500 and no save on failure)
  - world merge: list fields read via `as_str_list`; `WorldSettings` validation wrapped
- `app/frontend/app.js`: `warning` handler (toast + `console.warn`).

**KIs fixed:** KI-015, KI-016, KI-018.

**CHANGELOG:** Changed (`format=json`, the template default, coercion) and Fixed (KI-015, KI-016, KI-018).

**Docs updated:**
- technical 02 (W3.3 step 1 and update rules, W3.4 `warning`, W4 merge, W5 list merge), 03 (§2.1, §2.2 table regenerated, `_call`, prompt catalogue, §4 catalogue), 04 (coercion note, refine merge), 05 (`type`/`age` rows, coercion row), 06 (JSON mode row), 07, 08 (A2 row removed, A9, A10, new A13b), 09
- `RULES.md` §3 `specialist.py` row
- gotchas: 2 obsolete traps removed, 1 added
- line refs remapped: 49, plus 4 regenerated table rows and 1 by hand

**Verification** (2026-11-23):
1. `py_compile` and `node --check` passed.
2. **Unit checks** (`py`, non-isolated):
   - all coercions as specified (`type` supporting→temporary, "Main"/"main character"→main, `age` 17→"17", "fly"→["fly"], `{"Bob": 3}`→`{"Bob": "3"}`, "null"→None, "3"→3, None→1, list→"a, b", dict→"goal: revenge")
   - assignment coerced (`age = 20` → "20")
   - `name=None`, missing name, `slug=None` and unknown attributes → ValidationError
   - **real `data/` files** (1 character, 1 scene, the world): load and `model_dump()` equals the stored JSON (read-only)
3. **Sandboxes** (committed code on 8011, fixed on 8012) + a hostile stub:
   - **Legacy file** with `type` "supporting", `age` 17, `abilities` "glowing": old not listed; new listed as temporary/"17"/["glowing"].
   - **Analysis as a JSON list:** old `'list' object has no attribute 'get'`; new completes.
   - **Hostile run** (`estimated_chapters` "2", string mentions, profile with wrong types + "junk" + a nameless one, post-write with null title, list/number/dict summaries, wrong-typed character updates, non-dict entries):
     - old: `'>' not supported…`, nothing saved
     - new: `multi_chapter` (2), `zz_hostile_hero` created (temporary, "17", ["flying"], {"Xiao Fan": "1"}), a warning for the nameless profile
     - new chapter saved with title "Chapter 2", micro "a, b", short "5", full "k: v"
     - Xiao updated (arc "x, y", cultivation "7", +telepathy, Bob "3", `last_seen` 2) and still listed
   - **Post-write-only hostile:** old streamed the chapter and then failed (`4 validation errors for Chapter`, no file); new saved it.
   - **Refine merge** (`type` supporting, `age` 17):
     - old 200, then the character vanished and its PUT returned 500; the unknown field gave 500
     - new 200 and listed (temporary/"17"), PUT 200, unknown field ignored (200)
   - **World refine** (`genre_tags` "grimdark", `factions` null): old 500; new 200 with `['grimdark']`.
   - **Stub log:** `format="json"` on analyze, resolve, profile and post-write; none on the writer.
4. **UI (browser pane):** with the unload failing, a "⚠ Could not unload the specialist model: …" toast plus `console.warn`; the chapter completed with all 7 steps.
5. **Cleanup:** servers stopped; sandboxes, stub, launcher and `launch.json` removed; `cpython-314` bytecode deleted; `data/` untouched.

**Not verified:** real model output with `format="json"` (no Ollama).

**Follow-ups:** none required.
