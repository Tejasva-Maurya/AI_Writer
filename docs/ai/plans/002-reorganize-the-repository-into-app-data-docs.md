---
id: 002
title: "Reorganize the repository into `app/` · `data/` · `docs/`"
status: done
approved: 2026-11-22T20:17:09+05:30
session: 446c84a1-3a9d-4b7a-b672-924b178b5ca1
source_file: "C:\\Users\\2466921\\.claude\\plans\\glittery-sniffing-spark.md"
sha256: 04589ea502ef6a722a639338f1b4c049fa84cfe191876478bfc0d6c83fa38bad
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Reorganize the repository into `app/` · `data/` · `docs/`

## Context
Right now the repo root mixes three kinds of things: the original application (backend, frontend, launcher, requirements), the user's novel data (`data/`), and everything created in plan 001 (docs, CHANGELOG, AI rules, plans, memory). Before the first commit of plan 001's work, the user wants a layout where it is obvious **which folder to open for which kind of work**. Nothing has been committed yet, so every step is reversible.

## Target layout
```
AI_Writer/
├── app/                    APPLICATION: everything that runs or installs the tool
│   ├── backend/            ← ./backend
│   ├── frontend/           ← ./frontend
│   ├── start.bat           ← ./start.bat   (double-click this to launch)
│   └── requirements.txt    ← ./requirements.txt
├── data/                   NOVEL DATA: characters/, scenes/, chapters/, novel_meta.json, world_settings.json, exports
│                            (stays where it is; it is already separate)
├── docs/                   SUPPORTING DOCUMENTS: everything written *about* the tool
│   ├── README.md           map of docs/ (what is where, reading paths)
│   ├── CHANGELOG.md        ← ./CHANGELOG.md
│   ├── user-guide.md       ← ./README.md (original end-user guide, paths updated)
│   ├── technical/          ← ./docs/01…09 (architecture, workflows, LLD, API, data, config, setup, FAQ, known issues)
│   └── ai/                 ← ./.ai/ (AI workspace)
│       ├── README.md
│       ├── RULES.md        ← ./CLAUDE.md (full AI rules)
│       ├── plans/          NNN-slug.md + generated INDEX.md
│       ├── memory/         project-state, decisions, gotchas, session-log
│       └── templates/
├── .claude/                Claude Code settings + hooks (must stay at root: Claude reads it there)
├── CLAUDE.md               loader of a few lines that imports docs/ai/RULES.md (must stay at root to auto-load)
├── AGENTS.md               short pointer for other AI tools (must stay at root)
├── README.md               NEW short "where does what live" map (GitHub landing page)
└── .gitignore
```
**Which folder for what:** change or fix the tool → `app/` · write, back up or inspect your novel → `data/` · read or update documentation, plans or the changelog → `docs/`.

Decisions you can change by rejecting with feedback: folder names (`app`/`data`/`docs`). No root `start.bat` shortcut (root stays clean). Root README is a short map, and the long guide moves to `docs/user-guide.md`.

## Steps
1. **Move files.** Plain filesystem moves (no `git mv` and no index changes; git detects renames at commit time): `backend/`, `frontend/`, `start.bat`, `requirements.txt` → `app/`. `docs/0*.md` → `docs/technical/`. `.ai/*` → `docs/ai/`. `CHANGELOG.md` → `docs/`. `README.md` → `docs/user-guide.md`. `CLAUDE.md` → `docs/ai/RULES.md`.
2. **Fix code paths.** Only what the move breaks, as single-line edits so the `path:line` citations in the docs stay valid:
   - `app/backend/managers/{character,scene,chapter}_manager.py` `_data_dir()` and `{world,novel_meta}_manager.py` `_path()`: `Path(__file__).parent.parent.parent / "data"` → `Path(__file__).resolve().parents[3] / "data"` (repo-root `data/`).
   - `app/backend/main.py:210` export path → `Path(__file__).resolve().parents[2] / "data"`. Update the docstring run hint (line 3).
   - Unchanged and still correct: `main.py:40` `FRONTEND_DIR` (backend and frontend stay siblings), `start.bat` (`%~dp0backend`, `%~dp0requirements.txt` are siblings), and the `sys.path` patches.
3. **Hook script** (`.claude/hooks/ai_workflow.py`): plans dir → `docs/ai/plans`, CHANGELOG check → `docs/CHANGELOG.md`, source prefixes → `app/`, doc hints → `docs/technical/…`, messages → `docs/ai/RULES.md`. `.claude/settings.json` is unchanged.
4. **Rewrite references** in every moved or new Markdown file with an ordered, scripted replacement, then manual review: `backend/` → `app/backend/`, `frontend/` → `app/frontend/`, `start.bat`/`requirements.txt` → `app/…`, `docs/0N-…` → `docs/technical/0N-…`, `.ai/` → `docs/ai/`, `CLAUDE.md` (rules) → `docs/ai/RULES.md`, plus relative links. Rewrite by hand: root `README.md` (new map), root `CLAUDE.md` (imports `@docs/ai/RULES.md`; RULES.md imports memory/INDEX), `AGENTS.md`, `docs/README.md` (map of docs/), and the directory trees in `docs/technical/01` and `docs/user-guide.md`.
5. **Records.** CHANGELOG `[Unreleased]` → Changed: repo reorganized `[plan 002]` (+ note that tracked `__pycache__` drops out of git once committed, KI-022). Decision **D-007** (layout). Update `project-state.md` and `session-log.md`. Add a note to plan 001's Outcome: "paths reorganized by plan 002". Update the KI-022 status.

## Contract / data impact
API, SSE and JSON schema: none. Novel data stays at `<repo>/data/` (same files, same location). **Launcher moves to `app/start.bat`**, and manual runs become `cd app/backend` then `python -m uvicorn main:app`.

## Verification
- `py -m py_compile` on all `app/backend` files. `node --check app/frontend/app.js`.
- Import the managers from `app/backend` and print `_data_dir()`/`_path()`. All must resolve to `<repo>/data/…`.
- **Server smoke test without Ollama:** put a stub `ollama.py` in a temp dir on `PYTHONPATH`, use FastAPI `TestClient` → `GET /`, `/app.js`, `/style.css`, `/api/health`, `/api/characters` (must return the existing *Xiao Fan* from `data/`), `/api/scenes`, `/api/novel-meta`, `/api/chapters`. Read-only, so no user data is touched.
- Hooks: rerun the sandbox tests (save-plan into `docs/ai/plans`; stop-check blocks on an `app/` change without `docs/CHANGELOG.md`; passes on `data/`/`docs/` changes).
- Markdown: link/anchor checker over all `.md`. Grep for stale paths (`.ai/`, `docs/0`, `../CLAUDE.md`, bare `backend/` not preceded by `app/`).
- Not run: double-clicking `start.bat` (it opens a server window and browser). It is reviewed statically instead.

## Risks & rollback
Stale references in docs (mitigated by grep and the link checker). Personal shortcuts to the old `start.bat`. Rollback: nothing is committed, so moving folders back and reverting the edits restores the current state.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9). See Outcome.
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 002]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done and `reindex` run

**Note:** this plan was auto-saved under the old path `.ai/plans/` (the hook constants pointed there at approval time) and moved to `docs/ai/plans/` in step 1. The execution-log items above were generated with the old paths and were updated by hand.

**Deviations from plan:**
- Changed-heading anchors (`W1 … (app/start.bat)`, `2.6 app/backend/…`, `W3.3 … app/backend/…`) had to be re-linked. The link checker caught them.
- `--app-dir backend` hints corrected to `--app-dir app/backend`.
- `docs/technical/05` §1 now documents how `app/` finds `data/`. RULES.md gained a "Repository layout" section (§1) and a layout row in the doc-impact matrix.
- CHANGELOG `[Unreleased]` lines from plan 001 were rewritten to final paths (unreleased). The 1.0.0 section keeps historical paths.

## Outcome
- **Moved:** `backend/`, `frontend/`, `start.bat`, `requirements.txt` → `app/`. `docs/0*.md` → `docs/technical/`. `.ai/{README.md,plans,memory,templates}` → `docs/ai/`. `CHANGELOG.md` → `docs/`. `README.md` → `docs/user-guide.md`. `CLAUDE.md` → `docs/ai/RULES.md`. `data/` unchanged.
- **New:** root `README.md` (repository map), root `CLAUDE.md` (loader: `@docs/ai/RULES.md`), rewritten `AGENTS.md`, `docs/README.md` (docs map), decision D-007.
- **Code:** single-line data-path edits in the five managers (`parents[3]`) and `main.py:210` (`parents[2]`), plus the `main.py:3` docstring. Line counts unchanged, so the docs' `path:line` citations stay valid. `.claude/hooks/ai_workflow.py` constants and messages moved to the new paths.
- **KIs:** KI-022 resolved once committed (the tracked `.pyc` files drop out; the new location is ignored).
- **CHANGELOG:** `[Unreleased]` → Changed (repository reorganised, data-path lines) + Removed (tracked bytecode).
- **Verification (all passed):** `py_compile` on all backend modules; `node --check app.js`; the five managers resolve to `<repo>/data/…` and export to `<repo>/data`; FastAPI `TestClient` with a stub `ollama` returned 200 for `/`, `/app.js`, `/style.css`, `/api/health`, `/api/characters` (*Xiao Fan*), `/api/scenes`, `/api/novel-meta`, `/api/world`, `/api/chapters`; `git status data/` clean (the empty `data/chapters/` created by the GET was removed); hook sandbox: save-plan → `docs/ai/plans/001-…`, stop-check blocks an `app/` change without `docs/CHANGELOG.md`, allows `data/`-only and changelog-updated cases, still blocks if the changelog is edited at the wrong (root) path; link/anchor checker: 26 Markdown files, 0 problems; all `@imports` resolve.
- **Not verified:** running `app/start.bat` (opens a server window and browser; reviewed statically: `%~dp0backend` and `%~dp0requirements.txt` are siblings inside `app/`). The LLM pipeline (no Ollama).
- **Follow-ups:** user decides on the commit. After committing, check `git ls-files | grep pyc` is empty.
