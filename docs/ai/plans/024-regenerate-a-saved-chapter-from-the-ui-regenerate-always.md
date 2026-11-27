---
id: 024
title: "Regenerate a saved chapter from the UI (⟳ Regenerate), always through a draft; reject chapter numbers below 1 (KI-045)"
status: done
approved: 2026-11-27T14:24:36+05:30
session: 32bc173e-8379-4b33-8399-61be0df4d69b
source_file: "C:\\Users\\2466921\\.claude\\plans\\moonlit-wandering-stearns.md"
sha256: dc4b9a624a308060df0aa47cd8d0302b5974056c266b1ada4db84cdbf75fded9
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Regenerate a saved chapter from the UI (⟳ Regenerate), always through a draft; reject chapter numbers below 1 (KI-045)

## Goal
Add a **⟳ Regenerate** button for a saved chapter. Plan 022 made regenerating an earlier chapter correct, but it is API-only (`chapter_number` on `POST /api/generate-chapter`; the UI never sends it).

User decisions (2026-11-27):
- **Load the prompt to edit:** the button puts the chapter's prompt into the plot box in a "Regenerating Chapter N" mode. You can change it, then press Generate. A ✕ leaves the mode.
- **Always as a draft:** a regeneration always sends `review: true`, even with "Review each chapter as a draft" off. The saved chapter stays as it is until the new draft is approved, and Discard keeps the old chapter.

## Context / evidence
- **Backend already supports it.** `generate_chapter` uses `req.chapter_number or chapter_manager.get_next_number()` (`app/backend/main.py:219`). Since plan 022, step 4 and step 7 handle later chapters (KI-043/KI-044). `finalize_chapter` overwrites `chapters/NNN.json` via `save_chapter` (atomic) and keeps `total_chapters` with `max()` (`chapter_pipeline.py:182`). A waiting draft makes generate return 409 (`main.py:215`).
- **Frontend today:**
  - `generateChapter()` (`app/frontend/app.js:464`) sends `{plot, review: novelMeta.review_drafts !== false, ...taggedEntities(plot)}` and shows `nextChapterNumber()` only for display. If a draft waits, it first asks to discard it (`discardDraft(question)`). Its `finally` hard-codes the button text 'Generate Chapter'.
  - `viewChapter(n)` shows a saved chapter in the output section through `showChapterOutput` (or in the Full View while a draft is open).
  - The Full View modal is `openChapterViewModal(ch)` (`app.js:1463`), with "Prompt used" and `reusePrompt()` (`app.js:1523`, the pattern to reuse). The draft is shown in it through `draftAsChapter()` (`app.js:1767`).
  - The draft badge is set in `showDraft()` (`app.js:699`), approval is `approveDraft()` (`app.js:862`), and the hint and label come from `updateChapterHint()` (`app.js:398`).
  - `init()` loads chapters before the draft (`app.js:121-128`).
- **KI-045 (new, Low, found while reading).** `GenerateChapterRequest.chapter_number: Optional[int] = None` (`app/backend/models.py:169`) has no lower bound. `-1` passes `req.chapter_number or …` and is saved as `data/chapters/-01.json` (`f"{n:03d}"` in `chapter_manager.save_chapter`). `0` silently means "next".

## Design
- **State:** `state.regenerate = null | { chapter_number, title }`.
- **Entry points** (one handler, `startRegeneration(ch)`):
  - `#btn-regenerate-chapter` "⟳ Regenerate" in the output header next to "⛶ Full View". It is shown only while the output section shows a saved chapter: set in `showChapterOutput()` and after a one-click `complete`, hidden when a generation starts and in `showDraft()`.
  - `#btn-view-regenerate` "⟳ Regenerate this chapter" in the Full View header. It is hidden when the modal shows a draft (`draftAsChapter()` gets `is_draft: true`) or a number that isn't a saved chapter.
- **`startRegeneration(ch)`:**
  - While a generation runs: a toast, and nothing else happens.
  - If the plot box holds other text: confirm the replacement, like `reusePrompt()`.
  - Then close the modal, `switchMode('plot')`, put `ch.plot_input` in the plot box (it may be empty: a toast says to describe the new version), `state._mentions = []`, set `state.regenerate`, `updateRegenerateUi()`, and focus the plot box.
- **`updateRegenerateUi()`:**
  - Shows or hides the plot-section notice `#regenerate-notice`: "⟳ Regenerating Chapter N · "title". The saved chapter stays until you approve the new draft." with a `✕ New chapter instead` button (`stopRegeneration()`).
  - Sets the Generate button text: "Regenerate Chapter N" or "Generate Chapter". `generateChapter()`'s `finally` uses the same helper.
  - Calls `updateChapterHint()`, which shows `CHAPTER N` and "Will regenerate Chapter N as a draft".
- **`generateChapter()`** with `state.regenerate`:
  - The displayed number is N.
  - `body.chapter_number = N` and `body.review = true`.
  - The discard question names the regeneration.
- **When the mode ends:** `showDraft()` calls `stopRegeneration()`, because the draft now carries the number. An error or a Cancel before any draft keeps the mode, so you can retry.
- **Draft badge:** "Draft · Chapter N · replaces the saved chapter" when N is a saved chapter. It is computed by one helper, used in `showDraft()` and refreshed in `loadChapters()`.
- **`approveDraft()`:** when the draft replaces a saved chapter, it asks for confirmation first ("Approving replaces the saved Chapter N … can't be recovered"). This also protects a draft left over from an earlier visit.
- **Backend (KI-045):** `chapter_number: Optional[int] = Field(default=None, ge=1)`, so 0 or a negative number gets **422**. No other backend change.

## Steps
1. Branch `feat/regenerate-chapter-button` from `main` (`de5c98c`). Plan → `in-progress`, `reindex`. Snapshot `data/` (SHA-256, sizes, mtimes, folders).
2. **Test first:** in `app/tests/test_regenerate.py`, `chapter_number` 0 and -1 → 422, and no chapter file is written. Run it on the old code: it must fail.
3. `app/backend/models.py`: the `ge=1` bound.
4. `app/frontend/index.html`: the output-header button, the Full View button, and the plot-section notice.
   `app/frontend/style.css`: a `.regenerate-notice` rule (`:root` tokens) plus `.regenerate-notice[hidden] { display: none; }` (gotcha KI-037/039).
5. `app/frontend/app.js`:
   - state and DOM refs;
   - `startRegeneration`, `stopRegeneration`, `updateRegenerateUi`, the draft-badge helper;
   - changes in `generateChapter`, `updateChapterHint`, `showChapterOutput`, `showDraft`, `loadChapters`, `openChapterViewModal`, `draftAsChapter` and `approveDraft`;
   - event wiring in `bindStaticEvents`.
6. **Docs:**
   - `docs/technical/02`: a new W13 "Regenerate a chapter", plus a W3 note.
   - `03` §4 (frontend state and functions) and §2.1 (the request bound).
   - `04`: `chapter_number` (the UI sends it with `review: true`; < 1 → 422).
   - `05` (the request field, if listed), `07` (usage and test list), `08` (an FAQ: how to rewrite an earlier chapter).
   - `09`: KI-045, found and fixed.
   - `docs/user-guide.md`, `docs/CHANGELOG.md` (Added: the button; Fixed: KI-045).
   - New decision **D-019** (regenerations always go through a draft, and approving one asks first).
   - Memory: project-state, session-log. Plan log and outcome. "Last verified" dates.
7. **Sandbox UI check** (a copy of `app/` and `data/`, a stub `ollama`, the Browser pane):
   - generate chapters 1 and 2 first;
   - the header button and the Full View button; the notice; ✕ leaves the mode; the prompt can be edited;
   - Generate → "Draft · Chapter 1 · replaces the saved chapter";
   - Discard → chapter 1 unchanged;
   - regenerate again → Approve → confirm → chapter 1 replaced, still 2 chapters;
   - with review off, it still opens as a draft;
   - a waiting draft → the discard question;
   - console clean; the `[hidden]` audit snippet returns nothing; a narrow window.
8. Verify, commit, push with the github-push skill, open the PR with the personal token, and ask before merging.

## Contract / data impact
- **API:** `POST /api/generate-chapter` now rejects `chapter_number` < 1 with 422. Before, 0 meant "next" and a negative number created a stray file. No route or field change.
- **SSE:** none.
- **`data/`:** none. Approving a regeneration overwrites `chapters/NNN.json`, as the API already did.

## What improves / downsides
- **Improves:**
  - Earlier chapters can be regenerated from the UI with an edited prompt.
  - The old chapter is safe until you approve the new draft.
  - A stray `-01.json` can no longer be created.
- **Downsides:**
  - A regeneration always needs an Approve click, even with review off (by choice).
  - One more confirmation when approving a draft that replaces a chapter.
  - Approving a regenerated chapter still overwrites the old text: there is no version history.

## Verification
- `py -m pytest app/tests` (the new test fails first on the old code), `py -m ruff check app` (temp `--target`), `py_compile`, `node --check app/frontend/app.js`.
- The sandbox UI check from step 7.
- Real `data/` listing before and after.
- **Not verifiable here:** the quality of a real model's regeneration (stub only).

## Risks & rollback
- Risk: the mode outlives its purpose (for example, the chapter it targets is replaced in another tab). The badge and the approve confirmation are computed from the chapters loaded at that moment, and `loadChapters()` refreshes them.
- Risk: the Generate label gets stuck. One helper sets it, and the `finally` block uses it too.
- Rollback: revert the PR. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 024]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations:**
- **"Replaces the saved chapter" is in the title line, not the badge.** The plan put it in the draft badge. At 1024 px the badge (which never shrinks or wraps) then ran into the word count. The badge stays "Draft · Chapter N", as before, and `draftHeading()` sets the output title to "New version: approving replaces the saved chapter" when the draft has no title of its own. It truncates like any long title.
- **The output header wraps** (`.output-header { flex-wrap: wrap }`, `.output-title-row { flex: 1 1 260px }`). The extra button had squeezed a saved chapter's title to "Stub Ti…" at 1024 px. Now the buttons move below the title first.
- **The notice wraps too** (`flex-wrap`, text `flex: 1 1 240px`). On a phone its text was squeezed into a narrow column next to the button.
- **A stale sentence in docs/technical/04, fixed in passing:** "If the client disconnects … nothing is saved unless step 6 finished". It had been out of date since plan 023, which keeps the text written so far.
- **KI-045 evidence is stronger than the plan stated.** A throwaway test showed that after `-1` wrote `-01.json`, the next "highest + 1" was 0, so `chapter_number: 0` wrote `000.json`.

## Outcome
- **Shipped:**
  - **⟳ Regenerate** in the chapter header (shown while a saved chapter is displayed) and **⟳ Regenerate this chapter** in the Full View (a saved chapter, not the draft).
  - **Regenerate mode** in the plot box: the chapter's prompt, a notice with **✕ New chapter instead**, the label `CHAPTER N`, the button **Regenerate Chapter N**, and the hint "Will regenerate Chapter N as a draft".
  - Generate sends `chapter_number` and `review: true`, whatever the setting (D-019). The draft ends the mode. Its title line says that approving replaces the saved chapter, and Approve asks first (Cancel keeps the draft).
  - **KI-045:** `chapter_number` below 1 gets 422.
- **Files:**
  - Code: `app/backend/models.py` (`Field(ge=1)`); `app/frontend/app.js`, `index.html`, `style.css`.
  - Tests: `app/tests/test_regenerate.py`.
  - Docs: `docs/technical/02` (W13, W3, W9, W11), `03` (§2.1, §4.1, §4.2, §4.4, §4.5, §5), `04`, `05`, `07` (§5 step 10, tips, §7), `08` (FAQ), `09` (KI-045), `docs/user-guide.md`.
  - Changelog and memory: `docs/CHANGELOG.md`, `docs/ai/memory/decisions.md` (D-019), `project-state.md`, `session-log.md`.
- **KIs:** KI-045 found and fixed.
- **CHANGELOG:**
  - Added: "⟳ Regenerate a saved chapter from the UI … [plan 024]".
  - Fixed: "`POST /api/generate-chapter` rejects a `chapter_number` below 1 … [plan 024] [KI-045]", and the technical/04 doc fix.
- **Verification (2026-11-27):**
  - `py -m pytest app/tests`: **132 passed** (130 before plus `test_chapter_number_below_one_is_rejected[0]` and `[-1]`, which failed on the old code with 200).
  - `py -m ruff check app` (ruff from a temp `--target`): all checks passed. `py_compile` OK, `node --check app/frontend/app.js` OK.
  - Sandbox UI check (a copy of `app/` and `data/`, a stub `ollama` that numbers its fake chapters, the Browser pane), with chapters 1 and 2 generated first:
    - The header button and the Full View button work. The notice, label, button text and hint are right, and ✕ leaves the mode.
    - With review **off**, a regeneration still opened as a draft. Saved chapter 1 kept "Version 1".
    - Discard left chapter 1 unchanged.
    - With a regeneration draft of chapter 2 waiting, regenerating chapter 1 asked "Discard it and regenerate Chapter 1?".
    - Approve asked "Approving replaces the saved Chapter 1 ("Stub Title 3") …", then replaced it ("Version 5", new title), with still 2 chapters and `total_chapters` 2.
    - After a reload, a regeneration draft still showed the replace note. Answering Cancel to the approve question kept the draft and chapter 2.
    - ✕ Cancel during a regeneration left no draft and kept the mode.
    - A new chapter in one-click mode saved without a question, and the header button came back.
    - Layouts at 375 px, 1024 px and 1440 px. Console clean; the `[hidden]` audit snippet returned nothing.
  - Real `data/`: SHA-256, sizes and file and folder mtimes are the same before and after.
  - **Not verified:** regeneration quality with a real model (stub only).
- **Follow-ups:** none required. Possible: keep the old version of a regenerated chapter (approving overwrites it for good).
