---
id: 025
title: "Keep older versions of a regenerated chapter (newest 5), with read, restore and delete in the Full View"
status: done
approved: 2026-11-27T17:54:58+05:30
session: 32bc173e-8379-4b33-8399-61be0df4d69b
source_file: "C:\\Users\\2466921\\.claude\\plans\\moonlit-wandering-stearns.md"
sha256: 6adbd15c8e4d3f82eef86f748c87ee1cddcdc47cf2aa95024a2d48c614a7007d
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Keep older versions of a regenerated chapter (newest 5), with read, restore and delete in the Full View

## Goal
When a regenerated chapter is approved, keep the text it replaces as an **older version**, instead of losing it for good. In the chapter's Full View, you can **read**, **restore** or **delete** each older version.

User decisions (2026-11-27):
- read, restore and delete;
- keep only the **newest 5** versions per chapter: saving a 6th deletes the oldest.

## Context / evidence
- **Where the overwrite happens.** `finalize_chapter()` (`app/backend/pipeline/chapter_pipeline.py`) builds the new `Chapter` and calls `chapter_manager.save_chapter(chapter)`, an atomic replace of `data/chapters/{n:03d}.json`.
  - It runs for draft approval (`POST /api/draft/approve`) and for one-click API generations.
  - Nothing awaits between the summary call and the save, so reading the old chapter just before the save is safe (KI-042 rule).
  - A raise there keeps the draft on disk (KI-041), so approving again retries.
- **Storage helpers.** `managers/storage.py`:
  - `write_json(path, data, exclusive=True)` never replaces an existing file;
  - `read_all(folder, label, build)` globs `*.json` in one folder, without recursion, and logs unreadable files.
  - `chapter_manager.get_all()` reads only `data/chapters/*.json`, so versions kept in another folder never show up as chapters or in an export.
- **Manager conventions.** Each manager has `_data_dir()`/`_path()` and validates names (`[\w-]+`, KI-010). The test fixture `data_dir` in `app/tests/conftest.py` redirects every manager (RULES §3: add new managers there).
- **The UI today:**
  - The Full View is `openChapterViewModal(ch)` (`app.js`), with the "Prompt used" `<details>` as the pattern to follow and `draftAsChapter()` giving `is_draft`.
  - `approveDraft()` asks "Approving replaces the saved Chapter N … The old text can't be recovered" (plan 024).
- **Guard.** `_busy_reason()` (`main.py`) is non-null while a generation, approval, rewrite or refine runs.

## Design
- **Storage:** `data/chapter_versions/{n:03d}-{version_id}.json`.
  - `version_id` = `YYYYMMDD-HHMMSS-ffffff`, taken when the version is replaced. It sorts chronologically; on a collision it is moved on by 1 µs.
  - The file holds the old chapter plus `version_id` and `replaced_at`.
- **Model:** `ChapterVersion(Chapter)` in `models.py`, adding `version_id: str = ""` and `replaced_at: str = ""`. Both have defaults, and `Chapter` is unchanged.
- **New manager** `app/backend/managers/version_manager.py`:
  - `KEEP = 5`;
  - `_data_dir()`, and `_path(number, version_id)`, which validates `number >= 1` and `version_id` against `\d{8}-\d{6}-\d{6}` and raises `ValueError` otherwise;
  - `archive(chapter, prune=True) -> ChapterVersion` (an exclusive write);
  - `get_all(number, include_text=False)`, newest first;
  - `get(number, version_id)`, `delete(number, version_id) -> bool`, and `prune(number)`, which deletes all but the newest `KEEP`.
  - `storage.read_all` gets an optional `pattern="*.json"` argument, so a chapter's versions can be listed by prefix.
- **Pipeline:** in `finalize_chapter`, right before `save_chapter`: `old = chapter_manager.get_chapter(n)`. If `old` exists and its `full_text` differs from the new text, call `version_manager.archive(old)`.
  - If the archive fails, it raises and the draft stays: the old text is never overwritten without its copy.
  - The same text approved again (a retry after a late failure) doesn't create a duplicate.
- **Routes** (`main.py`, a new "CHAPTER VERSIONS" section). An invalid number or id, or a missing version, gets 404:
  - `GET /api/chapters/{number}/versions` → `ChapterVersion[]` without `full_text`, newest first (`[]` when none).
  - `GET /api/chapters/{number}/versions/{version_id}` → the full version.
  - `DELETE /api/chapters/{number}/versions/{version_id}` → `{"success": true}`.
  - `POST /api/chapters/{number}/versions/{version_id}/restore` → **409** while `_busy_reason()` is set, otherwise `{"chapter": Chapter, "kept_version": id | null}`. The order never loses text:
    1. read the version into memory;
    2. archive the current chapter with `prune=False`;
    3. save the version as the chapter (its own fields, `chapter_number` = n);
    4. delete the restored version's file;
    5. `prune(n)`.

    Profiles and `total_chapters` are not changed.
- **UI:**
  - **Full View of a saved chapter:** an "Older versions (N)" `<details>` under "Prompt used", hidden when there are none. Each row reads "Replaced {date} · "title" · N words", with **Read**, **↺ Restore** and **🗑 Delete**. It is loaded by `loadChapterVersions(n)`, and every value goes in through `textContent`.
  - **Read:** opens the version in the same modal, with the badge "Chapter N · older version", no ⟳ Regenerate and no versions list. A notice says "Older version, replaced {date}", with **← Current version**, **↺ Restore** and **🗑 Delete**.
  - **Restore:** `confirm()` ("… The current text is kept as an older version."), then POST. Then: a toast; `loadChapters()`; if the output section shows chapter n (no draft open), `showChapterOutput(restored)`; and the modal reopens on the restored chapter with its list refreshed. A 409 shows the server's message.
  - **Delete:** `confirm()` ("… can't be recovered"), then DELETE, then refresh the list, or go back to the current chapter if you were reading the deleted version.
  - **Approve confirmation** (plan 024) now reads: "Approving replaces the saved Chapter N ("title") with this draft. The current text is kept as an older version in its Full View (the newest 5 are kept). Replace it?"

## Steps
1. Branch `feat/chapter-versions` from `main` (`8870d6c`). Plan → `in-progress`, `reindex`. Snapshot `data/`.
2. **Tests first:** a new `app/tests/test_versions.py`, and `version_manager` in the `data_dir` fixture. The tests:
   - approving a regeneration keeps the old text as a version;
   - a new chapter, or the same text again, keeps none;
   - a 6th version drops the oldest;
   - the list strips the text and is newest first; GET one returns the text;
   - DELETE, then 404; an unknown or invalid id gets 404;
   - restore swaps the texts, keeps the count, and gets 409 while a job runs;
   - restoring the oldest of 5 loses nothing;
   - a failing archive keeps the draft and the chapter (500).

   Run them on the old code first: they must fail.
3. Backend: `models.py` (`ChapterVersion`), `managers/version_manager.py` (new), `managers/storage.py` (`pattern`), `pipeline/chapter_pipeline.py` (archive before the save), `main.py` (4 routes).
4. Frontend: `index.html` (the versions `<details>` and the older-version notice in `modal-chapter`), `style.css` (rules with `[hidden]` overrides), `app.js` (`loadChapterVersions`, `renderChapterVersions`, `openChapterVersion`, `restoreChapterVersion`, `deleteChapterVersion`, the `is_version` handling in `openChapterViewModal`, the approve text).
5. **Docs:**
   - `docs/technical/02`: a new W14 "Older chapter versions", plus W9 and W13 step 6.
   - `03`: §2.1, §2.2, §2.3, §2.7, §4, §5.
   - `04`: the 4 routes and the endpoint index.
   - `05`: the `chapter_versions/` layout, the `ChapterVersion` entity, and pruning.
   - `06`: `KEEP = 5`.
   - `01`: the module list and the data folders. `07`: usage and tests. `08`: the FAQ.
   - `docs/user-guide.md`, `docs/CHANGELOG.md` (Added).
   - `docs/ai/RULES.md` §1: `data/` now holds `chapter_versions/` too.
   - New decision **D-020**. Memory: project-state, session-log. Plan log and outcome.
6. **Sandbox UI check** (a stub `ollama`):
   - generate chapter 1, then regenerate and approve it 6 times → 5 versions, the oldest dropped;
   - Read a version, ← Current version;
   - Restore → the texts swap and the output section updates;
   - Delete from the list and from the version view;
   - Restore while a generation runs → the 409 message;
   - console clean; the `[hidden]` audit snippet returns nothing; a narrow window.
7. Verify, commit, push with the github-push skill, open the PR with the personal token, and ask before merging.

## Contract / data impact
- **API:** 4 new routes, additive. No change to existing routes or payloads.
- **SSE:** none.
- **`data/`:**
  - a new folder `data/chapter_versions/`, created only when a chapter is replaced, with a new file type `ChapterVersion`;
  - existing files are unchanged, and no migration is needed.

## What improves / downsides
- **Improves:** approving a regeneration no longer destroys the old text. You can compare, restore or delete versions, and a restore keeps the replaced text too.
- **Downsides:**
  - Up to 5 extra files per regenerated chapter.
  - Only the newest 5 versions are kept: a 6th regeneration deletes the oldest without asking (the approve confirmation says so).
  - A restore doesn't roll profiles back (as in plan 022).
  - Versions aren't exported.

## Verification
- `py -m pytest app/tests` (the new tests fail first), `py -m ruff check app` (temp `--target`), `py_compile`, `node --check app/frontend/app.js`.
- The sandbox UI check from step 6.
- Real `data/` listing before and after.
- **Not verifiable here:** real models (stub only).

## Risks & rollback
- Risk: a restore racing an approval of the same chapter. Prevented by the 409 guard, and the restore has no `await`.
- Risk: path injection through `version_id`. A strict regex in `_path()`, and an invalid id gets 404.
- Risk: pruning deletes the version being restored. The restore holds it in memory and prunes last.
- Rollback: revert the PR. Versions already in `data/chapter_versions/` are inert files and can be deleted by hand.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 025]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations:**
- **`archive(chapter, prune_old=True)`**, not `prune=True`: the module also has a `prune(number)` function, and a parameter of the same name would hide it inside `archive`.
- **Tests before the code, in two stages.** `test_versions.py` imports `version_manager`, and the `data_dir` fixture must redirect it, so the model, `storage.read_all(pattern)` and the manager came first. The tests were then run before the pipeline change and the routes existed: 10 of 14 failed (no routes; nothing kept). The 4 invalid-id 404 cases passed only because no route existed.
- **`managers/__init__.py` re-exports `version_manager`** like the other six (not in the plan; imports worked without it).
- **The Full View header wraps on narrow windows** (`.chapter-view-top`, `.chapter-view-header { flex: 1 1 220px }`, `.chapter-view-meta` wraps). Found in the sandbox at 375 px: plan 024's **⟳ Regenerate this chapter** button made the badge, title, word count and button overlap, and this plan's longer badge ("Chapter N · older version") made it worse. Logged under CHANGELOG Fixed, not as a KI (it was never released).
- **Small doc corrections found on the way:** 05 §2.3 said `plot_input` is "not displayed anywhere" (it has been the Full View's "Prompt used" since plan 019); the 01 file tree and the README map didn't list `draft.json`.
- **Handed over mid-plan.** The original session handed the task to a side session after the code and tests were written (so the user could keep talking there). The side session ran the sandbox check, wrote the docs and finished the plan.

## Outcome
- **Shipped:**
  - Approving a regeneration (or a one-click API regeneration) keeps the replaced text in `data/chapter_versions/{NNN}-{YYYYMMDD-HHMMSS-ffffff}.json`, the newest 5 per chapter. The copy is written before the save; a failed copy keeps the draft and the old chapter.
  - The Full View lists **Older versions (N)** with **Read**, **↺ Restore** and **🗑 Delete**, and shows an older-version notice (← Current version / ↺ Restore / 🗑 Delete) while one is read.
  - Restore keeps the current text as a version in turn, is refused with 409 while an AI job runs, and refreshes the output section.
  - The approve confirmation says the current text is kept.
  - The Full View header wraps on narrow windows.
  - Decision D-020.
- **Files:**
  - Backend: `app/backend/models.py`, `app/backend/managers/version_manager.py` (new), `app/backend/managers/__init__.py`, `app/backend/managers/storage.py`, `app/backend/pipeline/chapter_pipeline.py`, `app/backend/main.py`.
  - Frontend: `app/frontend/app.js`, `index.html`, `style.css`.
  - Tests: `app/tests/test_versions.py` (new), `app/tests/conftest.py`.
  - Docs: `docs/technical/01`, `02` (W14, W9, W13), `03`, `04`, `05` (§1, §2.3, §2.7), `06`, `07`, `08`, `docs/user-guide.md`, `README.md`, `docs/ai/RULES.md` §1.
  - Changelog and memory: `docs/CHANGELOG.md`, `docs/ai/memory/decisions.md` (D-020), `project-state.md`, `session-log.md`.
- **KIs:** none.
- **CHANGELOG:** Added "Older versions of a regenerated chapter … [plan 025]"; Fixed "The Full View header no longer overlaps itself in narrow windows … [plan 025]".
- **Verification (2026-11-27):**
  - `py -m pytest app/tests`: **146 passed** (132 before plus 14 in `test_versions.py`).
  - `py -m ruff check app` (ruff from a temp `--target`): all checks passed. `py_compile` OK, `node --check app/frontend/app.js` OK.
  - Sandbox UI check (a copy of `app/` and `data/`, a stub `ollama` that numbers its fake chapters, the Browser pane):
    - Chapter 1 regenerated and approved 6 times → 5 versions, newest first (Version 6 … Version 2); Version 1 dropped.
    - The list renders, built with `textContent`. Read showed Version 6 with the "older version" badge and notice, and without the list or ⟳ Regenerate. ← Current version went back.
    - Restore from the notice: the saved chapter, the output section and the Full View all showed Version 6; Version 7 was kept; still 5 versions.
    - Delete from the list (5 → 4) and from the version view (4 → 3, back to the saved chapter).
    - Restore while a generation streamed → toast "Could not restore the older version: A chapter is already being generated…", nothing changed.
    - A new chapter has no versions (the box is hidden).
    - A UI regeneration and approval showed the new confirmation text and kept the replaced text as the newest version.
    - Layouts at 375 px (after the header fix: no overlaps, measured), 1024 px and wide.
    - The `[hidden]` audit returned nothing. The console's only entry was the browser logging the deliberate 409.
  - Real `data/`: SHA-256, sizes and file and folder mtimes are the same before and after.
  - **Not verified:** real models (stub only).
- **Follow-ups:** none required.
