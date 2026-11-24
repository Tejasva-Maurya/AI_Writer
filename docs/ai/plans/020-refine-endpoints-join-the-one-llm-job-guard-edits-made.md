---
id: 020
title: "Refine endpoints join the one-LLM-job guard; edits made during a summary or world refine are no longer overwritten (KI-042)"
status: done
approved: 2026-11-24T18:19:59+05:30
session: 32bc173e-8379-4b33-8399-61be0df4d69b
source_file: "C:\\Users\\2466921\\.claude\\plans\\moonlit-wandering-stearns.md"
sha256: 057d91e8d489a6c3f0d3d2b75c8ed4b04edc806ff0b91ada459c67d86805bf8b
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Refine endpoints join the one-LLM-job guard; edits made during a summary or world refine are no longer overwritten (KI-042)

## Goal
Do the first follow-up from plan 019's "Not included": the three Build-tab refine endpoints (`POST /api/refine/character|scene|world`) take part in the "one LLM job at a time" guard. While doing that, fix the lost-update defect found in the same code (KI-042).

## Context / evidence
- **Refine ignores the guard.** `_busy_reason()` (`app/backend/main.py:187-190`) covers generation, approval and rewrite only (`_JOB_BUSY`, `:176-179`). The refine routes (`main.py:534-633`) call the specialist at any time. Consequences:
  - During step 6 a refine reloads the specialist next to the ~7 GB writer, undoing step 5's deliberate unload (RULES §3 VRAM choreography, docs/technical/01 §6). On small GPUs that can mean out-of-memory or a crawl.
  - Two specialist jobs (refine + step 1–3/7, or two refines) can run at once.
- **KI-042 (new, Medium): edits made during an AI call are silently overwritten.** Two places read data before an `await` and save it afterwards:
  - `finalize_chapter` reads every character and location at `app/backend/pipeline/chapter_pipeline.py:85-86`, then awaits the summary (`:90`), then saves the featured profiles from those copies. A manual **Edit** or an **Update Existing** refine of a featured character/location saved during the summary (seconds; a minute or more on CPU) is reverted.
  - `refine_world` loads the world at `main.py:611`, awaits the specialist (`:612`), and saves its merge of the *old* copy (`:616-632`). A World Settings save made meanwhile is lost.
  - `refine_character`/`refine_scene` already read the existing profile *after* the await (`:546`, `:582`), so they are fine.
  - The guard alone can't close KI-042, because manual saves (PUT) aren't LLM jobs. The fix re-reads after the await, which is safe because nothing after the await yields (single event loop).
- **UI errors are raw:** the refine handlers show `e.message` (`app/frontend/app.js:1987-1988, 2032-2033, 2069-2070`), i.e. `POST /refine/character failed: 409 — {"detail":…}`. Plan 019 added `errorText(e)` for this.

## Design
- Refine becomes job kind `"refine"` (`_JOB_BUSY["refine"] = "A profile is being refined with AI. Wait for it to finish."`). It is **rejected with 409, not queued**: a queued refine could wait minutes behind a generation inside one HTTP request.
- It is **symmetric**: while a refine runs, generate, approve, rewrite and another refine get 409 too.
- **Not blocked:** refines while a draft merely waits for review (that's a valid moment to fix a profile), manual CRUD, and all reads.
- A small context manager `_llm_job(kind)` in `main.py`: it raises 409 if busy, sets `_job["kind"]`, and always releases. It is used by refine ×3 and replaces the hand-written set/try/finally in rewrite and approve. Rewrite and approve keep their early `_busy_reason()` check, so their response order (409 before 404/422) is unchanged.

## Steps
1. Branch `fix/refine-busy-guard` from `main` (`884a9ea`); plan 020 → `in-progress`, `reindex`.
2. `app/backend/main.py`:
   - Add `"refine"` to `_JOB_BUSY` and update the comment.
   - Add the `_llm_job(kind)` context manager next to `_busy_reason()`.
   - Wrap the specialist call in each refine route with `with _llm_job("refine"):`.
   - In `refine_world`, re-load the world **after** the call and merge into that fresh copy; the pre-call copy still feeds the prompt.
   - Switch `rewrite_draft_passage` and `approve_draft` to `_llm_job` (behaviour unchanged).
3. `app/backend/pipeline/chapter_pipeline.py` → `finalize_chapter`: keep the pre-await read for the prompt briefs, and re-read `chars_dict`/`scenes_dict` right after `post_write_update` returns, before applying the updates (KI-042). Docstring note.
4. `app/frontend/app.js`: the three refine `catch` blocks show `errorText(e)` (the server's message, e.g. the 409) in the status line and the toast.
5. Tests, in a new `app/tests/test_refine.py`:
   - Each of the 3 refine routes returns **409** while a generation runs, or while an approve, rewrite or refine job runs, and doesn't call the specialist.
   - A refine holds the `"refine"` slot during its call and releases it afterwards, also when the specialist raises.
   - Generate, approve and rewrite get 409 while a refine runs.
   - A happy-path create and merge, since refine has no tests yet.
   - KI-042: a character edited *during* the step-7 summary keeps the edit and still gets the step-7 update.
   - KI-042: a world edited during a world refine keeps the edit and gets the merged values.
6. Docs (RULES §6):
   - `docs/technical/02` (W3.2/W3.6 guard rows, W4/W5 409 and the post-call re-read, W11 guards)
   - `03` (§2.2 refine rows, `_llm_job`, `_JOB_BUSY`; §2.7 re-read; §5 409s)
   - `04` (refine 409; the guard list under generation)
   - `01` §8
   - `08` A15 (the refine message) and a note in A9/A14 if they apply
   - `09` KI-042 (new, fixed)
   - `docs/user-guide.md` troubleshooting line
   - `docs/ai/RULES.md` §3 invariant (add refine)
   - `docs/CHANGELOG.md` `[Unreleased]` (Changed + Fixed)
   - `docs/ai/memory/{project-state, session-log, decisions (D-017)}.md`
   - Plan Execution log and Outcome
   - "Last verified" bumps
7. Verify (below), commit, push with the github-push skill, open the PR with the personal token, and ask before merging.

## Contract / data impact
- **API:** the 3 refine routes can now return **409** `{"detail": "<reason>"}` while another LLM job runs. While a refine runs, generate/approve/rewrite return 409 with the refine message. No route, field or payload shape changes.
- **SSE:** none. **`data/`:** none (same files, same schema).
- **Versioning note:** D-015 counted "generate returns 409 while one runs" toward MAJOR. Read the same way, a new 409 on refine is an API-contract change, so the next release would be **3.0.0** rather than 2.1.0. I'll flag this in the CHANGELOG and project-state; the version is decided only when you release.

## What improves / downsides
- **Improves:**
  - Step 5's VRAM saving can no longer be undone by a refine during writing.
  - No overlapping specialist jobs.
  - Profile and world edits are never silently reverted by a summary or world refine (KI-042).
  - Clear error messages in the Build tabs.
- **Downsides:**
  - A Build-tab refine can't run while a chapter is generating (minutes), being approved, or rewritten; you get a clear "wait" message and retry. Before, it ran (slowly, and VRAM-heavy).
  - Generating right after starting a refine gets 409 for a few seconds.

## Verification
- `py -m pytest app/tests` (93 existing + new), `py -m ruff check app` (temp `--target`), `node --check app/frontend/app.js`, `py_compile`.
- The KI-042 tests must fail on the current code and pass after the fix: run them once before step 3.
- UI, sandbox copy with a stub `ollama` (slow streaming), real `data/` never touched:
  - start a generation, then click **Refine & Save** in Character Build → the status shows "A chapter is already being generated…";
  - after it ends, the refine works;
  - console clean.
- Real `data/`: SHA-256/size/mtime listing before and after.
- **Not verifiable here:** VRAM behaviour with real models (no Ollama on this machine).

## Risks & rollback
- Risk: the slot is never released after an unexpected exception. `_llm_job` releases in `finally` (tested); a restart also clears it.
- Risk: the re-read in `finalize_chapter` picks up a profile deleted during the summary; the existing `if slug in chars_dict` checks skip it (tested by construction).
- Rollback: revert the PR. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress) on branch `fix/refine-busy-guard` from `main` (`884a9ea`)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 020]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- No change of approach.
- One extra test: `test_a_profile_deleted_during_the_summary_stays_deleted`. It showed a second KI-042 symptom: the old code wrote a deleted character back to disk.
- `08` got a new entry A15b (a Build tab refused with a "wait" message) rather than notes in A9/A14, which didn't apply.
- `07` needed no change: its refine text doesn't mention concurrency.
- The rewrite and approve routes now raise their 500 inside `with _llm_job(...)` (no behaviour change; the slot is still released).

## Outcome
**Shipped (branch `fix/refine-busy-guard`, for a PR to `main`):**
- `main.py`:
  - Job kind `"refine"` with its 409 message.
  - The `_llm_job(kind)` context manager (409 if busy; claims and always releases the slot).
  - All three refine routes hold the slot during the specialist call; rewrite and approve use the same helper.
  - `refine_world` merges into the world re-read after the call.
- `chapter_pipeline.finalize_chapter` re-reads characters and scenes after the summary call.
- `app.js`: the refine errors show `errorText(e)`.

**Files:**
- Code: `app/backend/main.py`, `app/backend/pipeline/chapter_pipeline.py`, `app/frontend/app.js`
- Tests: `app/tests/test_refine.py` (new, 23 tests)
- Docs: `docs/technical/{01,02,03,04,08,09}`, `docs/user-guide.md`, `docs/ai/RULES.md`, `docs/CHANGELOG.md`, `docs/ai/memory/{decisions (D-017), project-state, session-log}.md`

**KIs:** KI-042 found and fixed (Medium).

**CHANGELOG:** Changed ×2 (refine waits for other AI jobs, flagged ⚠ as a new 409; readable refine errors), Fixed ×1 (KI-042).

**Verification (2026-11-24):**
- The new tests were run first on the old code: 19 of 23 failed, for the expected reasons (no 409; reverted edit; deleted character written back; lost world edit).
- After the fix: `py -m pytest app/tests` **116 passed**; `ruff check app` clean (temp `--target`); `node --check` and `py_compile` OK.
- UI, sandbox copy with a stub `ollama` (slow stream) on port 8765:
  - **Refine & Save** during step 6 → status "✗ Error: A chapter is already being generated…" and the same toast;
  - once the draft was waiting, the same refine → "✓ Created: Zz Elder Lan";
  - console: only that expected 409.
- The real `data/` was unchanged (SHA-256, size, mtime).
- **Not verified:** VRAM behaviour with real models (no Ollama here).

**Follow-ups:**
- Remaining plan 019 items: unused helpers, context tiers when regenerating an earlier chapter, keeping partial text when the writer fails mid-stream.
- Release type (3.0.0 vs 2.1.0) at release time (D-017).
