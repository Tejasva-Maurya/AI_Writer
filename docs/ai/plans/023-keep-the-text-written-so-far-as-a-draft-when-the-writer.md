---
id: 023
title: "Keep the text written so far as a draft when the writer fails or the tab closes mid-chapter"
status: done
approved: 2026-11-27T12:03:13+05:30
session: 32bc173e-8379-4b33-8399-61be0df4d69b
source_file: "C:\\Users\\2466921\\.claude\\plans\\moonlit-wandering-stearns.md"
sha256: 63176d8afd3c0b227b7bc28032be28dd3d25d569745e698d5c8c5a5c65d2c46d
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Keep the text written so far as a draft when the writer fails or the tab closes mid-chapter

## Goal
Do the last follow-up from plan 019's "Not included". When step 6 stops halfway, save the text written so far as the draft (`data/draft.json`) instead of losing it, in two cases:
- the writer model fails (Ollama stops, out of memory, a model error);
- the browser disconnects (the tab is closed or reloaded).

An explicit **✕ Cancel** still discards the text, as today.

User decision (2026-11-27): writer failures **and** closed tabs; only Cancel discards.

## Context / evidence
- **Writer failure.** Step 6 (`app/backend/pipeline/chapter_pipeline.py`, "STEP 6: WRITE CHAPTER") streams tokens into `full_text`. On the writer's `("error", …)` it emits `error "Writer error: …"` and **returns before the draft is saved**, so the text written so far exists only in the browser. `writer.stream_chapter` turns any exception into that tuple (`agents/writer.py:68-69`).
- **Disconnect vs Cancel.** Both end in `task.cancel()`:
  - a closed tab through `event_stream()`'s `finally` in `generate_chapter` (`app/backend/main.py`);
  - **✕ Cancel** through `POST /api/generate-chapter/cancel`.

  The pipeline can't tell them apart today. `CancelledError` reaches step 6 at the writer's `await` (the only await in the loop), and nothing in between catches it (`except Exception` doesn't catch `CancelledError`).
- **UI.** The `error` and cancelled-`error` handlers in `generateChapter()` already call `loadDraft()` (plan 019), and `init()` calls `loadDraft()` on page load. So a saved partial draft opens on its own: after the error toast, or on the next visit. **No frontend change is needed.**
- **Today's docs:** 02 W3.3 step 6 ("`error` → pipeline returns early, nothing saved") and W3.6 (Writer error and "Browser tab closed" rows).

## Design
- **`run_pipeline(…, keep_partial_on_cancel: Optional[Callable[[], bool]] = None)`.**
  - A small helper `_save_draft(...)` builds and saves the `Draft` (the same fields as the normal path). Three places use it.
  - **Writer error with text:** save the draft, then `error {"message": "Writer error: … The N words written so far are kept as a draft: finish them, rewrite them, or discard them.", "draft_saved": true}`. Without text: as today. Step 7 is never run on partial text, in either mode.
  - **Cancelled during step 6 with text,** and `keep_partial_on_cancel()` is true: save the draft (synchronous, so safe while cancelling), log it, and re-raise `CancelledError`.
  - The default `None` keeps today's behaviour for any other caller.
- **`main.py`:**
  - A flag `_cancel = {"by_user": False}`. `generate_chapter` resets it and passes `keep_partial_on_cancel=lambda: not _cancel["by_user"]`.
  - `cancel_generation` sets it to `True` before `task.cancel()`.
  - So a closed tab keeps the text, and Cancel discards it.
- **Unchanged:**
  - A cancel or disconnect during steps 1–5 (no text yet) saves nothing.
  - During step 7 the draft already exists.
  - The SSE contract is unchanged: `error.draft_saved` already exists since plan 019.

## Steps
1. Branch `feat/keep-partial-chapter` from `main` (`a42d8e7`); plan 023 → `in-progress`, `reindex`; snapshot `data/`.
2. **Tests first** (run on the old code; they must fail):
   - `conftest.py`: `FakeOllama.chunks` may contain an exception, which is raised mid-stream (the fake writer stream already yields chunks).
   - New `app/tests/test_partial.py`:
     - **writer failure after text** (review and one-click) → `error` with `draft_saved`; the draft holds exactly the text so far; no chapter file; step 7 not called.
     - **writer failure before any text** → today's error, no draft.
     - **disconnect:** a `TestClient` stream that is dropped after the first token, with a blocking fake writer → the draft holds the partial text.
     - **explicit cancel:** the cancel endpoint while streaming → no draft.
     - **pipeline level** (`asyncio.run` on `run_pipeline` with a blocking writer, then cancel): `keep_partial_on_cancel` true keeps the text, false or `None` saves nothing.
3. `app/backend/pipeline/chapter_pipeline.py`: `_save_draft`, the writer-error branch, and the `CancelledError` branch around the step-6 loop.
4. `app/backend/main.py`: the `_cancel` flag (reset in generate, set in cancel), passed to `run_pipeline`.
5. Docs:
   - `docs/technical/02`: W3.2 (stopping), W3.3 step 6, W3.4 `error` row, W3.6 rows, W11 intro.
   - `03` §2.2 and §2.7.
   - `04`: generate errors, cancel vs closed tab.
   - `01` §8.
   - `07` §5.2: Cancel vs closing the tab.
   - `08` A17: writer error kept as a draft.
   - `docs/user-guide.md`: Cancel and closed tab.
   - `docs/CHANGELOG.md` Changed.
   - New decision **D-018** (a closed tab keeps the partial chapter, Cancel discards it; reverses part of plan 010's "closing the tab stops the generation and saves nothing").
   - Memory: `project-state` (all plan 019 follow-ups done), `session-log`.
   - Plan log/outcome; "Last verified" bumps.
6. **UI check** in a sandbox with a stub `ollama` (slow stream; one variant fails mid-stream):
   - writer failure → error toast, then the draft opens with the partial text;
   - reload the page mid-chapter → the draft with the partial text opens on the reload;
   - **✕ Cancel** mid-chapter → no draft.
7. Verify, commit, push with the github-push skill, open the PR with the personal token, and ask before merging.

## Contract / data impact
- **API:** no route or payload change. Behaviour change: a writer failure or a disconnect during step 6 now leaves `data/draft.json` (with `error.draft_saved: true` for the writer failure). A following generate then gets the existing 409 "a draft is waiting" until it is approved or discarded.
- **SSE:** no new event or field.
- **`data/`:** no schema change. The draft can now hold an unfinished chapter.

## What improves / downsides
- **Improves:**
  - No more lost half-chapters when Ollama crashes, or when you close or reload the tab by accident.
  - You can finish the text by hand, extend it with AI rewrites, approve it, or discard it.
- **Downsides:**
  - A reload or closed tab mid-chapter now leaves a draft that must be discarded before the next generation. Before, it simply vanished.
  - Right after a reload, the page may load a moment before the server has saved the draft; it then shows up on the next action (Generate answers "a draft is waiting" and opens it).

## Verification
- `py -m pytest app/tests` (the new tests fail first on the old code, then everything passes), `py -m ruff check app` (temp `--target`), `py_compile`, `node --check` (sanity; no frontend change).
- The sandbox UI check from step 6.
- Real `data/`: SHA-256/size/mtime listing before and after.
- **Not verifiable here:** a real Ollama failure (simulated with the stub).

## Risks & rollback
- Risk: the `CancelledError` handling swallows the cancel. It re-raises, and a test asserts the task ends cancelled and the guard is free.
- Risk: Cancel and disconnect race (Cancel, then the tab closes). The flag is set before the cancel, so Cancel wins.
- Rollback: revert the PR. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 023]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations:**
- **Disconnect and Cancel tests don't use `TestClient`.** Starlette's `TestClient` buffers the whole streamed response, so a test can't drop a stream that never ends; those tests hung. `test_partial.py` calls `main.generate_chapter(...)` inside `asyncio.run`, reads `response.body_iterator` up to the first token, then closes it (closed tab) or awaits `main.cancel_generation()` (Cancel). Every wait has a timeout.
- **`conftest.FakeOllama.chunks`** accepts the `BLOCK` sentinel (the stream waits forever, so a cancel lands during step 6) as well as exceptions.
- **No KI entry.** The lost half-chapter was a known follow-up of plan 019, not a catalogued defect, so docs/technical/09 is unchanged.
- **A failed save while cancelling is logged, not raised** (found in the final diff review). Without the guard, an `OSError` from `_save_draft` inside the `CancelledError` handler replaced the cancel, the pipeline's outer `except Exception` turned it into an `error` event, and the cancelled task carried on. The added test `test_a_failed_save_while_cancelling_does_not_swallow_the_cancel` failed on the unguarded code with that `OSError`.
- **The first sandbox reload check was invalid.** Because of tool latency, the generation had finished before the reload (the draft held all 46 words). It was redone in one step (generate, wait for 6 words, `location.reload()`), and the server logged "stopped while writing: 5 words kept as a draft".

## Outcome
- **Shipped:**
  - When the writer fails mid-chapter, the text written so far is saved as the draft. The `error` event carries `draft_saved: true` and a message with the word count. Step 7 is never run on partial text.
  - When the stream is dropped (tab closed or reloaded) during step 6, the text is kept as well.
  - An explicit **✕ Cancel** still discards it, and a stop during steps 1–5 still saves nothing.
  - No route, field or SSE change.
  - Decision D-018.
- **Files:**
  - Code: `app/backend/pipeline/chapter_pipeline.py` (`_save_draft`, the writer-error branch, `CancelledError` handling, the `keep_partial_on_cancel` parameter) and `app/backend/main.py` (`_cancel["by_user"]`).
  - Tests: `app/tests/conftest.py` (`BLOCK`, exceptions in `chunks`) and the new `app/tests/test_partial.py` (9 tests).
  - Docs: `docs/technical/01` §8, `02` W3.2/W3.3/W3.4/W3.6/W11, `03` §2.2/§2.7/§5, `04` (generate errors, cancel vs a dropped connection), `07` §5 step 9 and §7, `08` (A15, new A17b), and `docs/user-guide.md`.
  - Changelog and memory: `docs/CHANGELOG.md`, `docs/ai/memory/decisions.md` (D-018), `project-state.md`, `session-log.md`.
- **KIs:** none (no catalogued defect; see Deviations).
- **CHANGELOG:** `[Unreleased]` → Changed: "A chapter that stops halfway is kept as a draft … [plan 023]".
- **Verification (2026-11-27):**
  - `py -m pytest app/tests`: 130 passed (121 before plus 9 new). On the old code the new tests failed for the right reasons, except the explicit-Cancel test, which passes before and after by design.
  - `py -m ruff check app` (ruff from a temp `--target`): all checks passed. `py_compile` OK, `node --check app/frontend/app.js` OK (no frontend change).
  - Sandbox UI check (a copy of `app/` and `data/`, a stub `ollama`, the Browser pane):
    - A writer failure mid-stream showed a toast ("…The 10 words written so far are kept as a draft…") and opened the draft.
    - A reload mid-chapter opened a 5-word draft after the reload.
    - **✕ Cancel** showed "Cancelled (not saved)" and left no draft.
    - The console was clean.
  - Real `data/`: SHA-256, sizes and mtimes are the same before and after.
  - **Not verified:** a real Ollama failure (simulated with the stub).
- **Follow-ups:** none from this plan. The UI "Regenerate chapter" button from plan 022 is still open.
