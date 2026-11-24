---
id: 019
title: "Review chapter drafts, AI rewrites, prompt reuse and @-mentions (port of the improvement branch)"
status: done
approved: 2026-11-24T16:37:36+05:30
session: 32bc173e-8379-4b33-8399-61be0df4d69b
source_file: "C:\\Users\\2466921\\.claude\\plans\\moonlit-wandering-stearns.md"
sha256: 843323d6cf3178adc10782c34ca1ee9136175d820fecbc9b4a5893bda8527457
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Review chapter drafts, AI rewrites, prompt reuse and @-mentions (port of the improvement branch)

## Goal
Bring the four features from the `improvement` branch into the current 2.0.0 code: **draft → review → approve**, **AI rewrite of a selected passage**, **"Prompt used" in chapter history**, and **@-mention autocomplete** in the plot box. Re-implement them on the 2.0.0 architecture, fix the branch's defects on the way, add the improvements listed below, and finish with a PR to `main`.

User decisions (2026-11-24): drafts are stored **on the server** · the one-click flow stays as a **setting** · drafts are edited in a **plain-text editor** · the branch's `data/chapters/001.json` **stays on the branch** (nothing in `data/` changes).

## Context / evidence

**The branch** (`origin/improvement`, 1 commit `0506f6d`) forks from `dead3e3` (v1.0.0), before all 2.0.0 work. It changes `backend/{main,models}.py`, `backend/agents/writer.py`, `backend/pipeline/chapter_pipeline.py`, `frontend/{app.js,index.html}`, and adds `New-Feature-Docs/001-{plan,walkthrough}.md`, `.pyc` files and `data/chapters/001.json`.

**Why the branch can't be merged:** it uses the 1.0.0 layout (`backend/` at the repo root), tracks `.pyc` files and `data/` (that would re-add the novel to git and undo plan 017), and conflicts with plans 002–018. The work is therefore **re-implemented on a new branch from `main`**. `improvement` is left untouched for reference. `New-Feature-Docs/` is not carried over (RULES §1: no new top-level folders); plan 019 and the updated docs replace it.

**Defects in the branch code that the port must not carry over:**
| Branch code | Problem on 2.0.0 |
|---|---|
| `approve_chapter` calls `specialist.post_write_update(...)` without `await` | The specialist has been async since plan 005, so `post_data` would be a coroutine and the approve call would crash |
| `revise_text` passes no `num_ctx` | Ollama's default context (2–4 k tokens) silently truncates a ~2,000-word draft |
| `revise_text` returns `"[Error: …]"` with HTTP 200 | The UI would replace the user's text with the error message |
| No `ollama is None` guard in `revise_text` | Re-opens KI-003 |
| Autocomplete builds `innerHTML` from unescaped `entity.name` | HTML injection (KI-011 class) |
| JS regex `@([\w\s-]*)` | No `u` flag, so non-Latin names such as 林凡 never match |
| No CSS for the new elements | `.draft-actions`, `.btn-approve`, `.autocomplete-dropdown` are unstyled; `hidden` on a panel with a `display` rule doesn't hide it (gotcha, KI-037) |
| Approve trusts the client's `characters_featured`, `scenes_featured` and `chapter_number` | The client decides which profiles get changed |
| Approve updates characters by in-place mutation and `set()` | Bypasses validation (KI-016), loses ability order, ignores scenes (KI-013) |
| No concurrency guard | Approve or rewrite can run during a generation (KI-031 class) |
| Toast container loses `aria-atomic` | Small accessibility regression |

**New defect found in `main` (becomes KI-041, Medium):** if step 7 fails (for example Ollama stops, or the specialist model is missing), the written chapter is lost. `post_write_update` is awaited at `app/backend/pipeline/chapter_pipeline.py:217`, the chapter is saved only afterwards at `:233`, and the generic `except` at `:289-291` just emits `error`. Saving the draft right after step 6 fixes this.

**Main-side facts used:** `plot_input` is already saved on every chapter (`chapter_pipeline.py:223`), so "prompt history" is UI-only. One-generation guard: `main.py:171-227`. Atomic writes: `managers/storage.py:18`. An explicit `chapter_number` overwriting an existing chapter is documented behaviour (`docs/technical/04:112`) and stays as is.

## Design (summary)
- **One draft at a time**, stored in `data/draft.json`. It is written right after step 6 in **every** mode (this is the KI-041 fix).
  - Review mode: the pipeline stops there and emits `draft_complete`.
  - One-click mode: step 7 runs at once, deletes the draft and emits `complete` as today.
- **Step 7 becomes one reusable function**, `finalize_chapter(draft, spec_model) -> (Chapter, warnings)`. Both the one-click pipeline and `POST /api/draft/approve` call it. It reloads profiles from disk, so profile edits made during review are kept.
- **A pending draft blocks new generations** (409). The UI first offers to discard it.
- **One LLM job at a time:** generate, approve and rewrite share one busy guard (409). Cancel still stops only a generation. Approve can't be cancelled.
- **@-mentions do more than insert a name:** the plot box remembers which entities were picked. The pipeline forces those into context as existing primary characters / main locations, so the writer always gets their full profile and step 3 never re-profiles them.

## Steps
1. **Branch and plan status.** `git switch -c feature/draft-review` from `main`. Set plan 019 `status: in-progress`, then `reindex`.
2. **Models** (`app/backend/models.py`), all new fields with defaults:
   - `Draft`: `chapter_number`, `plot_input`, `full_text`, `title`, `characters_featured`, `scenes_featured`, `new_characters`, `new_scenes`, `created_at`, `updated_at`.
   - Request models `UpdateDraftRequest{full_text, title}`, `RewriteRequest{text, start, end, instruction}`, `ApproveDraftRequest{full_text?, title?}`.
   - `GenerateChapterRequest` gains `review: bool = False`, `tagged_characters: List[str] = []`, `tagged_scenes: List[str] = []`.
   - `NovelMeta` gains `review_drafts: bool = True`.
3. **Draft storage.** New `app/backend/managers/draft_manager.py` (`load()`, `save()`, `delete()`), using the existing data-path pattern and `storage.write_json`. An unreadable file is logged and treated as no draft. Export it from `managers/__init__.py` and add it to the `data_dir` fixture in `app/tests/conftest.py`.
4. **Writer** (`app/backend/agents/writer.py`): add `REVISE_SYSTEM` and `async revise_passage(before, passage, after, instruction, plot, model) -> str`.
   - Options: `num_ctx` 32768, `temperature` 0.7, `top_p` 0.9, `keep_alive` 300.
   - `before`/`after` are trimmed to fit the context.
   - Code fences are stripped from the reply.
   - It raises instead of returning error text, and has the `ollama is None` guard.
5. **Pipeline** (`app/backend/pipeline/chapter_pipeline.py`):
   - `_apply_tags()` runs after `_canonical_entities`. A tagged slug that exists becomes existing primary/main; unknown slugs are ignored and logged.
   - After step 6, save the `Draft` (including the slugs created in step 3).
   - Review mode: emit `draft_complete` (`chapter_number`, `full_text`, `word_count`, `characters`, `scenes`, `new_characters`, `new_scenes`) and stop.
   - Otherwise call `finalize_chapter()`, emit its warnings and then `complete` (payload unchanged).
   - `finalize_chapter()` holds today's step-7 code unchanged: validated updates, scene significance, `total_chapters`. Its last action is `draft_manager.delete()`.
6. **Routes** (`app/backend/main.py`):
   - Generalise `_generation_running()` into a busy check that also covers approve and rewrite.
   - `POST /api/generate-chapter`: 409 while a draft is pending; pass the new fields to `run_pipeline`.
   - New routes:
     - `GET /api/draft` returns the draft, or 404.
     - `PUT /api/draft` saves edits.
     - `DELETE /api/draft` discards it.
     - `POST /api/draft/rewrite` → `{"replacement"}`. 404 without a draft, 422 for bad offsets or an empty instruction, 409 while busy, 500 if the writer fails.
     - `POST /api/draft/approve` → `{"chapter", "warnings"}`. It saves the sent text and title first, then finalizes. 404 / 409 / 422 (empty text) / 500 (specialist failure, draft kept).
7. **HTML** (`app/frontend/index.html`):
   - Output section: a draft toolbar with an optional title, a rewrite instruction plus "✨ Rewrite selection", "↶ Undo rewrite", "🗑 Discard", "✓ Approve & save", and an autosave status line. Plus a `<textarea id="draft-editor">`.
   - Settings: a "Review each chapter as a draft before saving" checkbox.
   - Full View modal: a `<details>` "Prompt used" box with a "Use this prompt again" button.
   - Plot box: an autocomplete `role="listbox"` and its ARIA attributes.
   - Keep the toast's `aria-atomic`.
8. **CSS** (`app/frontend/style.css`, in the matching banner sections, using existing tokens): draft editor in the reading font; toolbar; autocomplete items (purple for characters, gold for locations); prompt box; a `[hidden] { display: none }` rule for each toggled element; narrow-window rules.
9. **JS** (`app/frontend/app.js`):
   - **Draft mode:** enter and exit it. Autosave 1 s after typing stops, and flush with `keepalive` on `pagehide`. `GET /api/draft` on load restores a draft. After an `error` or a cancel, check for a draft too (the KI-041 case).
   - **Rewrite:** uses the textarea's exact selection; the editor is read-only while it runs; `setRangeText` selects the new text; there is an undo stack.
   - **Discard:** confirm first, then offer to delete the profiles that draft created.
   - **Approve:** shows step 7 in the pipeline panel, then the saved chapter in reading mode, reloads lists and meta, and clears the plot and mentions.
   - **Generating with a pending draft:** confirm the discard first.
   - **Generate payload** gets `review` (from `novelMeta.review_drafts`) and the tagged slugs whose names are still in the plot.
   - **Settings** checkbox round-trip.
   - **Full View:** prompt box plus reuse. `state.currentChapter.plot_input` is set after `complete`.
   - **@-autocomplete:** triggers on an `@` at the start of a word; Unicode-aware; ranks starts-with matches first; ↑/↓, Enter/Tab, Esc; closes on blur; positioned at the caret (mirror div) and kept inside the viewport; `escHtml` everywhere.
10. **Tests:**
    - `conftest.py`: `draft_manager` in the fixture; `FakeOllama` can raise an exception queued in `json_replies`.
    - `test_pipeline.py`:
      - review mode writes a draft and no chapter, and skips step 7
      - keep-alive choreography in review mode
      - one-click mode deletes the draft
      - a step-7 failure keeps the draft (KI-041)
      - a tagged character reaches `characters_featured` even when the specialist misses it
      - an unknown tag is ignored
    - New `test_draft.py`:
      - GET, PUT and DELETE, with 404s
      - generate returns 409 while a draft is pending
      - rewrite: offsets validated (422), writer called with `num_ctx` 32768, 409 while busy, writer error gives 500
      - approve saves the edited text and title, deletes the draft, updates `last_seen_chapter` and `total_chapters`
      - approve: specialist failure gives 500 and keeps the draft
      - `review_drafts` round-trip
11. **Docs and paper trail:** every doc listed below, CHANGELOG `[Unreleased]`, new KI-041 marked Fixed, new decision D-016 (server-side single draft, review toggle, @-tags force context), `project-state.md`, `session-log.md`, and the plan's Execution log and Outcome.
12. **Verify** (see Verification), then **commit** on `feature/draft-review` (repo-local identity, no AI trailers), **push** through the github-push skill (`git push` is blocked by the proxy), and **open the PR** to `main`. I'll show you the diff summary and ask before the push.

## What improves
- You can read, edit and AI-polish a chapter before it changes any profile, summary or chapter count. Rewrites replace exactly the text you selected.
- **No more lost chapters:** the text is on disk as soon as step 6 ends. A step-7 failure, a browser crash or a closed tab no longer loses it (KI-041; the branch would still lose it).
- Approval uses the **current** profiles, including edits made during review, so summaries and updates match the final text.
- @-mentions give exact spellings and **guarantee** the tagged characters and locations are in the writer's context.
- "Prompt used" plus "Use this prompt again" make it easy to iterate on a chapter idea.
- The branch's defects are fixed (table above), and the new parts get tests (the branch had none).

## Disadvantages and possible degradation
- **One extra click per chapter** in review mode, and the ~10–60 s summarising wait moves from right after writing to the Approve button. *Mitigation:* the setting switches back to today's flow.
- **A pending draft blocks the next generation** until it is approved or discarded (one draft at a time; no parallel drafts).
- **Step 3 still creates new profiles at draft time.** Discarding the draft leaves them unless you accept the offered cleanup.
- **Plain-text editing:** paragraphs show as blank lines while editing (the formatted view returns after approval). A rewrite can't be undone with the browser's Ctrl+Z; the "Undo rewrite" button covers that.
- **VRAM:** a rewrite loads the writer model (~7 GB). Today step 7 already runs while the writer stays loaded for 5 minutes, so the pattern doesn't change.
- **API:** additive. Old clients (`review` absent = false) keep today's behaviour, except a new 409 when a draft is pending, which can only happen after review mode or a step-7 failure. When released this is a **minor** version (2.1.0). No data migration: old files load, and `review_drafts` defaults to true.
- **Size:** about 450 more lines in `app.js`, ~200 in Python plus tests. Autosave adds small atomic writes while you type.

## Contract / data impact
- **API:** new `/api/draft` routes (GET/PUT/DELETE, `/rewrite`, `/approve`). `generate-chapter` gains optional `review`, `tagged_characters`, `tagged_scenes`, and a 409 reason. No route or field is removed or renamed.
- **SSE:** new event `draft_complete`; the other 8 events are unchanged. RULES §3 invariant list updated.
- **`data/`:** new `data/draft.json`, which exists only while a draft is pending. `novel_meta.json` gains `review_drafts`. The `Chapter` schema is unchanged. The real `data/` is not touched by this work.

## Docs to update (RULES §6, and bump "Last verified")
`docs/technical/01` (draft stage, new manager) · `02` (W3 split, a new W-flow for review/rewrite/approve, §W3.4 `draft_complete`, §W3.6 failures, W9 prompt box) · `03` (§2.1, §2.3, §2.4, §2.6–2.7, §3 rewrite prompt, §4 frontend, §5 tests) · `04` (new routes, new generate fields, 409) · `05` (`draft.json`, `review_drafts`) · `06` (§2.3 rewrite LLM params) · `07` (usage, tests) · `08` (FAQ: "my chapter isn't in history yet", "a draft is waiting") · `09` (KI-041) · `docs/user-guide.md` · `docs/ai/RULES.md` §1/§3 · `docs/CHANGELOG.md` · `docs/ai/memory/{project-state,session-log,decisions}.md`.

## Not included (possible follow-ups)
- Refine endpoints still run during a generation (VRAM contention). Adding them to the busy guard would change their behaviour, so it should be a separate decision.
- Unused helpers `chapter_manager.get_recent_n`, `character/scene_manager.get_as_dict`, `state._profileContext`, `state.activeMode` (unrelated cleanup).
- When regenerating an earlier chapter through the API, later chapters get the "micro" context tier.
- Keeping partial text as a draft when the writer fails mid-stream.

## Verification
- `py -m pytest app/tests` (all existing tests plus the new ones); `py -m ruff check app` (ruff from a temp `--target`); `node --check app/frontend/app.js`; `py -m py_compile` on the changed modules.
- **UI**, in a sandbox copy of `app/` with its own copied `data/`, plus a stub `ollama` on `PYTHONPATH` (canned JSON, streamed tokens, canned rewrite), launched through a temporary `.claude/launch.json` entry in the Browser pane:
  - review flow: generate → draft → edit → autosave → reload restores it → rewrite plus undo → approve → history shows "Prompt used" → reuse
  - discard flow, including profile cleanup
  - one-click flow with the setting off
  - simulated step-7 failure → draft restored
  - @-autocomplete with mouse, keyboard and a Chinese name
  - narrow window
  - console clean; the `[hidden]` audit snippet from gotchas returns nothing
- **Real `data/` untouched:** SHA-256 listing before and after (pytest's `real_data_untouched` guard also covers test runs).
- **Not verifiable here:** real Ollama models (the `ollama` package and CLI are not installed). Rewrite quality and real step-7 timing are "not verified with a real model".

## Risks & rollback
- All work is on `feature/draft-review`; rolling back means closing or reverting the PR. `main` and `improvement` stay as they are.
- If a draft ever gets stuck, deleting `data/draft.json` (or clicking Discard) returns to normal. Old data files load unchanged.
- Risk: the busy guard or draft gate blocks generation unexpectedly. Covered by 409 tests and clear UI messages naming the reason.
- Risk: positioning the autocomplete at the caret on narrow screens. It falls back to directly below the plot box.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress) on branch `feature/draft-review` from `main` (`cc09c77`)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 019]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
1. **`RewriteRequest` carries text pieces, not offsets.** The plan's `{text, start, end, instruction}` became `{before, passage, after, instruction}`: JavaScript selection offsets count UTF-16 code units and Python indexes code points, so an emoji or a CJK Extension-B character before the selection would have shifted the cut. The server no longer needs offset validation (422 is for an empty passage or instruction).
2. **`GET /api/draft` returns `200 null`** when no draft waits, instead of 404. "No draft" is the normal state at every page load, and a 404 logs a red console error each time. PUT/DELETE/rewrite/approve still return 404 without a draft.
3. **`finalize_chapter` doesn't log its warnings.** The caller does: the pipeline through `_sse("warning")`, the approve route through `log.warning`. Otherwise each warning would be logged twice.
4. **A failed step 7 in one-click mode** emits a dedicated `error` ("Summary failed: … The chapter is kept as a draft …", `draft_saved: true`) instead of the generic "Pipeline error".
5. **Extra, not in the plan:**
   - `real_data_untouched` now also compares folder mtimes. The first test run, before `draft_manager` was in the `data_dir` fixture, created and deleted `data/draft.json` in the real `data/`, and the old guard couldn't see that. All novel files stayed byte-identical (SHA-256 checked); only the folder mtime changed.
   - `FakeOllama` can raise an exception queued in `json_replies` and records `chat_options`/`chat_messages`.
   - `apiError` adds `status`/`detail` to the API helpers' errors.
   - Stale doc notes fixed while verifying: 02 W3.3 `keep_alive -1` → 300; 03 §3 "no JSON mode"; 04 "skipped silently"; 03 §6 lost the removed `featured_scene_slugs` row.

## Outcome
**Shipped (on `feature/draft-review`, for a PR to `main`):**
- **Draft review.**
  - `data/draft.json` via the new `managers/draft_manager.py`. Written after step 6 in every mode; deleted last by `finalize_chapter()` (step 7, shared by the one-click pipeline and `POST /api/draft/approve`).
  - Routes `GET/PUT/DELETE /api/draft`, `POST /api/draft/rewrite`, `POST /api/draft/approve`.
  - `GenerateChapterRequest.review/tagged_characters/tagged_scenes`, `NovelMeta.review_drafts` (default true), and the SSE event `draft_complete`. 409 while a draft waits.
  - One LLM job at a time (`_busy_reason`, `_job`).
- **AI rewrite:** `writer.revise_passage` (`REVISE_SYSTEM`, `num_ctx` 32768, temperature 0.7, keep_alive 300, raises instead of returning error text).
- **@-mentions:** `_apply_tags` in step 2, plus the frontend autocomplete (Unicode, keyboard and mouse, caret placement, escaped HTML).
- **Prompt used** box in the Full View, with **Use this prompt again**.
- **UI:**
  - The draft panel: editor, rewrite and undo, title, discard (with step-3 profile cleanup), approve showing step 7.
  - Autosave (1 s, chained, `keepalive` on `pagehide`), restore on load, and restore after an error or cancel.
  - The Settings checkbox, and CSS in the matching sections with `[hidden]` rules.

**Files changed:**
- Backend: `app/backend/{main.py, models.py, agents/writer.py, managers/__init__.py, managers/draft_manager.py (new), pipeline/chapter_pipeline.py}`
- Frontend: `app/frontend/{app.js, index.html, style.css}`
- Tests: `app/tests/{conftest.py, test_pipeline.py, test_draft.py (new)}`
- Docs: `docs/technical/01–09`, `docs/user-guide.md`, `docs/CHANGELOG.md`, `docs/ai/RULES.md`, `docs/ai/memory/{project-state, decisions (D-016), gotchas, session-log}.md`

**KIs:** KI-041 found and fixed (Medium: a step-7 failure lost the written chapter).

**CHANGELOG:** `[Unreleased]` — Added ×5 (draft review, AI rewrite, @-mentions, prompt used, setting), Changed ×4, Fixed ×1 (KI-041).

**Verification (2026-11-24):**
- `py -m pytest app/tests`: **93 passed** (71 before + 6 new in `test_pipeline.py` + 16 in `test_draft.py`).
- `py -m ruff check app` (ruff from a temp `--target`): all checks passed.
- `node --check app/frontend/app.js` OK; `py_compile` on all backend modules OK.
- **UI**, in a sandbox copy of `app/` with synthetic `zz` data and a stub `ollama` on port 8765, through the Browser pane:
  - @-mentions with 林凡: list at the caret, ranking, ↑/↓/Enter/Esc, no-match close.
  - The tag reached `characters_featured` although the stub specialist missed it.
  - Review generation → draft, with step 7 "Waiting for your approval".
  - Edit → autosave → reload restored text and title.
  - Rewrite of a selection plus Undo, both autosaved.
  - Full View of the draft with the prompt.
  - Approve → chapter saved with the author's title, profiles updated, draft gone.
  - History pill → Full View → Use this prompt again.
  - Discard with step-3 profile cleanup, plot kept; Generate with a waiting draft asks to discard.
  - Setting off → one-click `complete`.
  - Step-7 failure → draft restored with the "kept as a draft" toast; approve fails and keeps the draft, then succeeds after the failure is turned off.
  - 375 px layout: no horizontal overflow.
  - `[hidden]` audit empty; the console showed only the deliberate 500 from the failure test.
- **Real `data/`:** SHA-256, sizes and mtimes of every file identical before and after.
- **Not verified:** real Ollama models (the package and CLI aren't installed here), so rewrite quality, real step-7 timing and VRAM behaviour with real models are untested.

**Follow-ups (not in this change):**
- Refine endpoints under the busy guard.
- Unused helpers (`get_recent_n`, `get_as_dict`, `_profileContext`, `activeMode`).
- Context tiers when regenerating an earlier chapter.
- Keeping partial text as a draft when the writer fails mid-stream.
- The `improvement` branch can be deleted once the PR is merged (the user's call).
