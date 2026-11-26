---
id: 022
title: "Regenerating an earlier chapter: later chapters in their own prompt section, no profile rollback (KI-043, KI-044)"
status: done
approved: 2026-11-26T22:12:05+05:30
session: 32bc173e-8379-4b33-8399-61be0df4d69b
source_file: "C:\\Users\\2466921\\.claude\\plans\\moonlit-wandering-stearns.md"
sha256: 6357dc20935bfbffaac8bd3b9b86cc93cf3a401ac6bac38cfa5a21b0b3366497
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Regenerating an earlier chapter: later chapters in their own prompt section, no profile rollback (KI-043, KI-044)

## Goal
Do the next follow-up from plan 019's "Not included". When an earlier chapter is regenerated (API `chapter_number` = an existing chapter, with later chapters on disk):
- the writer must not be told that later chapters already happened;
- it must not see the old version of the chapter it rewrites;
- step 7 must not roll the profiles back to that earlier point in the story.

User decision (2026-11-26): later chapters go into a **separate "later" section** with an instruction to stay consistent without revealing them.

## Context / evidence
- **KI-043 (new, Medium): the prompt mixes the future into "STORY SO FAR".**
  - Step 4's tiering (`app/backend/pipeline/chapter_pipeline.py:276-289`) maps every chapter with `N − n ≤ 0` to `micro`, including the chapter being rewritten (`n = N`) and all later ones.
  - `build_master_prompt` (`app/backend/pipeline/context_builder.py:136-143`) then lists every chapter, ascending, under `=== STORY SO FAR ===`.
  - So when chapter 3 of 10 is rewritten, the writer reads chapters 4–10 as past events and also gets the old chapter 3's summary.
  - The behaviour was documented as a caveat (docs/technical/02 W3.3 note under the tier table) and listed as plan 019's follow-up, but had no KI.
- **KI-044 (new, Medium): step 7 rolls profiles back.**
  - `finalize_chapter` sets `last_seen_chapter = N` unconditionally (`chapter_pipeline.py:122`, `:139-144`): a character last seen in chapter 10 drops to 3.
  - It also overwrites `arc_notes`, `cultivation_level` and relationship descriptions (`:123-131`), and a location's `significance` (`:146-153`), with chapter 3's state. Chapters 4–10 had already moved those on.
- **Scope note:** only the API can regenerate (the UI never sends `chapter_number`). Overwriting chapter *N* itself stays the documented behaviour (`docs/technical/04`).

## Design
- **Step 4 tiers** for chapter *n*, when writing *N*:
  - `n < N`: as today (`full_text` / `full` / `short` / `micro` by distance);
  - `n = N`: **`skip`** (the old version is left out);
  - `n > N`: **`later`**.
  - The status line counts the chapters that are included.
- **`build_master_prompt`:**
  - `skip` is omitted.
  - `later` chapters (micro summaries, ascending) go into a new section after STORY SO FAR:
    ```text
    === LATER IN THE STORY ===
    These chapters come after the one you are writing and are already written. Keep this chapter consistent with them, but do not reveal, anticipate or foreshadow their events.
    Chapter 5 — Title: micro summary
    ```
  - A missing tier still defaults to `micro`, so the call stays backward compatible.
  - With no later chapters the prompt is byte-for-byte what it is today.
- **`finalize_chapter`:**
  - `last_seen_chapter = max(current, N)`, always. For a new last chapter that is N, as today.
  - **When later chapters exist:** don't apply `arc_notes`, `cultivation_level`, `relationship_updates` or a location's `new_significance`, because the later chapters already describe the newer state. Still add `new_abilities` (union, no loss).
  - Add one warning saying what was kept. It is shown as a toast in the UI and logged.

## Steps
1. Branch `fix/regenerate-earlier-chapter` from `main` (`1044e73`); plan 022 → `in-progress`, `reindex`; snapshot `data/`.
2. **Tests first**, run on the old code (they must fail for the stated reasons):
   - `test_pipeline.py`, through the API with the fake `ollama`:
     - **prompt:** chapters 1–5 on disk, then regenerate 3 → the writer prompt has ch1–2 under STORY SO FAR, ch4–5 only under LATER IN THE STORY with the instruction, and no old ch3 summary. A normal new chapter has no LATER section.
     - **profiles:** regenerate 3 with chapter 5 on disk → `last_seen` stays 5; arc, level, relationships and the location's significance stay unchanged; the new ability is added; the warning is shown; the chapter 3 file has the new text.
     - **normal case:** `last_seen` goes 1 → 2 for a new chapter 2.
   - A small unit test of `build_master_prompt` with `skip`/`later` tiers.
3. `app/backend/pipeline/chapter_pipeline.py`: the step-4 tier rules, and in `finalize_chapter` the `later` check, `max()` for `last_seen` and the skipped state updates with their warning.
4. `app/backend/pipeline/context_builder.py`: the `skip`/`later` handling, the LATER IN THE STORY section, and the comment on the `chapter_tiers` parameter.
5. Docs:
   - `docs/technical/02` W3.3: step-4 tier table, the note under it, step-7 update rules.
   - `03` §2.6 (sections) and §2.7.
   - `04`: the generate `chapter_number` paragraph.
   - `05` §4 (context table).
   - `06` §2.3 (chapter tier knob).
   - `08`: FAQ "Can I regenerate…".
   - `09`: KI-043, KI-044 (new, fixed).
   - `docs/CHANGELOG.md` Fixed ×2.
   - Memory: `project-state` follow-ups, `session-log`.
   - Plan log/outcome; "Last verified" bumps.
6. Verify, commit, push with the github-push skill, open the PR with the personal token, and ask before merging.

## Contract / data impact
- **API / SSE / data schema:** none. Regeneration still overwrites `chapters/NNN.json`. Step 7 can emit one more `warning` message text; the event type already exists.
- **Prompt:** the writer's master prompt gains the LATER IN THE STORY section **only** when later chapters exist, and drops the old version of the chapter being rewritten. New chapters get the same prompt as today.

## What improves / downsides
- **Improves:**
  - A regenerated earlier chapter is written as part of the past: it no longer treats future events as history.
  - It stays consistent with later events.
  - It doesn't copy its old version.
  - Character and location profiles keep their latest state.
- **Downsides:**
  - A rewritten earlier chapter can't update arc notes, levels, relationships or significance. If a rewrite really changes them, edit the profile by hand; the warning says so.
  - Small models may still hint at later events despite the instruction (not verifiable here without Ollama).

## Not included
A UI "Regenerate this chapter" button. Regeneration stays API-only, as today.

## Verification
- `py -m pytest app/tests` (the new tests fail first on the old code, then everything passes), `py -m ruff check app` (temp `--target`), `py_compile`. No frontend change, so `node --check` only as a sanity check.
- Real `data/`: SHA-256/size/mtime listing before and after.
- **Not verifiable here:** how real models follow the "don't reveal" instruction (no Ollama).

## Risks & rollback
- Risk: the skip/later rules could change the prompt for normal generation. A test asserts that a new chapter's prompt has no LATER section and keeps every earlier chapter.
- Rollback: revert the PR. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress) on branch `fix/regenerate-earlier-chapter` from `main` (`1044e73`)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 022]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- The tests went into a new `app/tests/test_regenerate.py` instead of `test_pipeline.py`, to keep them together. The normal-case `last_seen` 1 → 2 is already covered by `test_draft.py::test_approve_saves_the_final_text_and_runs_step_7`. A new `test_last_seen_never_moves_backwards` covers the second `last_seen` loop (featured characters without an update).
- Extra doc fix: `docs/technical/07` §7 didn't list `test_refine.py` from plan 020. It is added now, together with `test_regenerate.py`.
- The project-state PR notes now include the REST fallback for `gh pr create` (seen in plan 021).

## Outcome
**Shipped (branch `fix/regenerate-earlier-chapter`, for a PR to `main`):**
- **Step 4** (`chapter_pipeline.py`): chapter N's old version gets the tier `skip`, and later chapters get `later`. The status line counts only the chapters included.
- **`context_builder.build_master_prompt`:** `skip` is left out; `later` chapters (micro summaries) go into `=== LATER IN THE STORY ===` with "Keep this chapter consistent with them, but do not reveal, anticipate or foreshadow their events." Prompts for new chapters are unchanged (pinned by a test).
- **`finalize_chapter`:** `last_seen_chapter = max(current, N)` in both loops. When later chapters exist (`last_later`), it skips arc notes, level, relationships and scene significance, still adds new abilities, and returns a warning.

**Files:**
- Code: `app/backend/pipeline/chapter_pipeline.py`, `app/backend/pipeline/context_builder.py`
- Tests: `app/tests/test_regenerate.py` (new, 5 tests)
- Docs: `docs/technical/{02,03,04,05,06,07,08,09}`, `docs/CHANGELOG.md`, `docs/ai/memory/{project-state, session-log}.md`

**KIs:** KI-043 and KI-044 found and fixed (both Medium).

**CHANGELOG:** Fixed ×3 (KI-043, KI-044, the 07 §7 test list).

**Verification (2026-11-26):**
- The new tests were run on the old code first: 4 of 5 failed for the KI reasons (chapter 4 in STORY SO FAR; `last_seen` 5 → 3 and 4 → 2; the arc overwritten). The new-chapter prompt test passed before and after.
- After the fix: `py -m pytest app/tests` **121 passed**; `ruff check app` clean (temp `--target`); `py_compile` and `node --check` OK.
- The real `data/` was unchanged (SHA-256, size, mtime).
- **Not verified:** whether real models honour "don't reveal" (no Ollama here).

**Follow-ups:**
- The last plan 019 item: keep partial text as a draft when the writer fails mid-stream.
- Possible: a UI "Regenerate chapter" button (regeneration is API-only).
