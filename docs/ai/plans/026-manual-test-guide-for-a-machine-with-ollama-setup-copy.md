---
id: 026
title: "Manual test guide for a machine with Ollama: setup, copy-paste prompts and a checklist"
status: done
approved: 2026-11-27T20:21:10+05:30
session: 2e66752c-73fd-46f2-92a8-9e7d7a4da1b5
source_file: "C:\\Users\\2466921\\.claude\\plans\\soft-wobbling-goblet.md"
sha256: ebf75d74d8bb66e506ef44df0f5b83d9d7ff59e83bd8926fc21ceb5e658f7e2d
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Manual test guide for a machine with Ollama: setup, copy-paste prompts and a checklist

## Goal
This machine has no Ollama, so every LLM-dependent feature since plan 019 has been checked only with a stub. Open threads from the plans:
- rewrite quality, approval timing and VRAM (plan 019);
- whether models honour "don't reveal later chapters" (plan 022);
- a real writer failure (plan 023);
- the quality of a real regeneration (plans 024, 025).

The user asked for a guide to test the tool on a machine that has Ollama. It should cover where and how to run the tool there, ready-to-paste prompts, and a checklist.

## Context / evidence (read this session)
- **Setup:**
  - `app/start.bat` (Python detection, dependency check incl. `ollama>=0.4`, uvicorn on `127.0.0.1:8000`, polls `/api/health`);
  - `app/requirements.txt`;
  - `docs/technical/07` §2–4.
- **Models.** The defaults are `gemma3:12b` (writer) and `phi4-mini:3.8b` (specialist) (`models.py` `NovelMeta`). `RECOMMENDED_MODELS` is in `main.py`, and `OLLAMA_HOST` is read by `_ollama_base_url`.
- **Routes.** `GET /api/models` returns `ollama_running` and `ollama_error`, and `GET /api/health` returns `{status, timestamp}`.
- **LLM settings:**
  - writer: `num_ctx` 32768, `temperature` 0.8, rewrite 0.7, `keep_alive` 300;
  - specialist: `num_ctx` 8192, `temperature` 0.1, `keep_alive` 300; it is unloaded at step 5 and with `keep_alive=0` after step 7 (`agents/*.py`).
- **UI labels** (`index.html`):
  - mode tabs Plot Writing / Character Build / Scene Build / World Build;
  - **Refine & Save Character**, **Refine & Save Location**, **Integrate into World Settings**, **Update Existing**;
  - **✨ Rewrite selection**, **↶ Undo rewrite**, **✓ Approve & save**, **🗑 Discard**;
  - **⛶ Full View**, **↺ Use this prompt again**;
  - **⟳ Regenerate**, **⟳ Regenerate this chapter**, **✕ New chapter instead**;
  - Older versions **Read / ↺ Restore / 🗑 Delete / ← Current version**;
  - **✕ Cancel**, **📤 Export**;
  - shortcuts `Ctrl+Enter`, `Alt+G/N/S/W`.
- **The pipeline:** the step names (Analyze Plot … Write Chapter, then step 7), the multi-chapter notice (`estimated_chapters > 1`) and the console log lines (plan 016).
- **`data/` is git-ignored** (D-014), so a fresh clone starts with an empty novel, which is right for testing.
- **A stale line found:** `docs/technical/07` §3 says "Use `127.0.0.1`, not `localhost`: the frontend calls `http://127.0.0.1:8000/api` explicitly". Since plan 007 the API is the relative `'/api'`, and `TrustedHostMiddleware` allows both hosts.

## Steps
1. New `docs/testing-with-ollama.md` (under `docs/`, RULES §1; no new top-level folder). Sections:
   1. **Where to run it.** The machine: OS, Python 3.11+, Ollama, and the VRAM/RAM needed for the defaults, plus lighter models for small GPUs. Clone the repo; you get an empty novel (don't copy the real `data/`, or back it up first).
   2. **Setup.** Pull the models, then install and start (`start.bat`, or manual uvicorn on any OS). Smoke checks: `/api/health`, `/api/models` with `ollama_running: true`, and `ollama ps`. Optionally run `pytest`/`ruff` with `requirements-dev.txt`.
   3. **A test record:** environment, commit, model names and versions, GPU, and timings.
   4. **Test sessions T1–T14,** each with copy-paste prompts in code blocks, steps, what to expect, and what to note:
      - settings and models;
      - World Build; Character Build (×2, one name with Chinese characters) and Scene Build, plus Update Existing;
      - chapter 1 in review mode, with @-mentions and `ollama ps` at steps 5, 6 and 7;
      - draft review: edit, two AI rewrite instructions, undo, reload keeps the draft, approve, Full View;
      - chapter 2 introducing a new character, and a multi-chapter plot;
      - one-click mode;
      - Cancel / close tab / stop Ollama while writing, and stop Ollama during Approve;
      - the busy guard: a second tab, a refine during a generation;
      - regenerating an earlier chapter (needs 3 chapters): no foreshadowing, profiles kept, the warning;
      - older versions: read, restore, delete, the cap of 5 (optional), and restore during a generation;
      - export; non-ASCII names; narrow window; a short soak (5 chapters, quality drift, speed).
   5. **A prose-quality rubric** (1–5 scores).
   6. **The full checklist** (checkboxes, one line per check).
   7. **What to send back** (results, backend log, browser console, `ollama ps`, a copy of the test `data/`) and **cleanup**.
   - The prompts are original test content (no text from the user's `data/`).
2. `docs/README.md`: add the guide to the tree and to the "Which document do I need?" table.
3. `docs/technical/07` §3: correct the stale `127.0.0.1`/`localhost` sentence, link the guide, and bump "Last verified".
4. `docs/CHANGELOG.md` `[Unreleased]`, Added: "Docs: manual test guide for a machine with Ollama [plan 026]", and the 07 fix.
5. Memory: `project-state.md` (Suggested next up 1 points to the guide), `session-log.md`. Plan log and outcome; `reindex`.
6. Verify, commit, push and open a PR, as for the earlier plans (and ask before merging).

## Contract / data impact
None. Docs only: no code, API, SSE or `data/` change.

## Verification
- Every label, route, model name, setting and shortcut in the guide is grepped against the code (`index.html`, `app.js`, `main.py`, `models.py`, `agents/*.py`) before committing.
- The relative links in the new doc and `docs/README.md` resolve (a script checks the paths exist).
- `py -m pytest app/tests` still passes (sanity; nothing in `app/` changes). Real `data/` untouched.
- **Not verifiable here:** the guide's steps against a real Ollama. That is what the guide is for.

## Risks & rollback
- Risk: the guide goes stale as the UI changes. It cites plan numbers, and RULES §6 ("User-facing feature → user guide, 07") is the reminder; its header says which commit it matches.
- Rollback: revert the PR.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete (docs only)
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 026]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status: no change, no defect found)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations:**
- **Three first-draft claims were wrong, and the fact check fixed them:**
  - The model browser offers **⬇ Pull** only for the recommended models: there is no field for a custom name. T1.3 now pulls with Ollama stopped and expects an error.
  - With Ollama down before Generate, the specialist call raises: the toast says "Generation error: Pipeline error: …", not a step-1 message of its own.
  - "[NovelForge] Pipeline warning" is a browser-console line (`app.js`), not a backend log line. §7 lists it under the console, and names the specialist's "reply has no JSON object" warning for the backend log.
- **The guide is a single file under `docs/`,** linked from `docs/README.md` and from technical/07 §3. The root `README.md` already points at the docs map, so it is unchanged.

## Outcome
- **Shipped:** `docs/testing-with-ollama.md`, with:
  - **§1 the machine:** OS, Python, Ollama, VRAM for the 32k-context writer, lighter models; a fresh clone means an empty novel;
  - **§2 setup:** clone, pull, `start.bat` or manual uvicorn, smoke checks, optional pytest/ruff;
  - **§3** a test record;
  - **§4 the tests T1–T14**, with original copy-paste prompts for a small test novel (Mei Ashgrove, Captain Rho Tanvir, 林雪, Cinder Wharf, the sky-ship Wren), each with "Expect" and "Note" lines. They cover the Build tabs, chapter 1 with @-mentions and `ollama ps` per step, draft review and AI rewrites, new characters and the multi-chapter notice, one-click mode, stopping halfway (Cancel, closed tab, Ollama stopped while writing and during Approve), the one-job guard, regenerating with a no-foreshadowing check, older versions, export, layout and shortcuts, and a 5-chapter soak;
  - **§5** a prose-quality rubric Q1–Q8;
  - **§6** a checklist (S1–S3, T1.1–T14.1, Q);
  - **§7** what to send back, and cleanup.
- **Also:** technical/07 §3 no longer says the page needs `127.0.0.1` (out of date since plan 007).
- **Files:** `docs/testing-with-ollama.md` (new), `docs/README.md`, `docs/technical/07-setup-and-usage.md`, `docs/CHANGELOG.md`, `docs/ai/memory/project-state.md`, `docs/ai/memory/session-log.md`, this plan, `INDEX.md`.
- **KIs:** none.
- **CHANGELOG:** Added: "Docs: testing-with-ollama.md, a manual test guide … [plan 026]". Fixed: the technical/07 §3 note [plan 026].
- **Verification (2026-11-27):**
  - Every quoted UI label, toast, error and log text was found in `app/` (37 strings).
  - The model names, `num_ctx`/`temperature`/`keep_alive` values, routes and the export filename rule were read from the code.
  - Every relative link and in-page anchor in the changed docs resolves.
  - `py -m pytest app/tests`: all pass (nothing in `app/` changed).
  - **Not verified:** the guide against a real Ollama. Running it is its purpose.
- **Follow-ups:** run the guide on a machine with Ollama, and turn its failures into KI-046 onwards.
