# Changelog

All notable changes to **NovelForge AI** are recorded here.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/):
- **MAJOR**: incompatible change to the data files in `data/` or to the HTTP API contract.
- **MINOR**: new user-visible feature, backwards compatible.
- **PATCH**: bug fix, documentation, internal refactor.

**Rules (enforced for AI assistants via `docs/ai/RULES.md` and a Stop hook):**
- Every change under `app/` (code, dependencies, launch script) adds a line under **[Unreleased]** in the same change set.
- Use the sections `Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`. Write one line per change, from the user's perspective, and add references in brackets: `[plan 003]`, `[KI-001]`, file names where useful.
- On release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, bump `version=` in `app/backend/main.py`, add a fresh empty `[Unreleased]`, and update the compare links at the bottom.
- Paths in released sections are as they were **at that release** (e.g. 1.0.0 had `backend/` at the root, now `app/backend/`).

---

## [Unreleased]

### Added
- Technical documentation set in `docs/technical/` describing the v1.0.0 state: overview & architecture, workflows (incl. the SSE event contract), low-level design, API reference, data model & storage, configuration, setup & usage, FAQ & troubleshooting, known issues & tech debt (`KI-001`…`KI-035`). [plan 001]
- `docs/CHANGELOG.md` (this file), with history reconstructed from git. [plan 001]
- AI-assistant governance: `docs/ai/RULES.md` (rules, guardrails, doc-impact matrix, definition of done), loaded by a root `CLAUDE.md`, plus a root `AGENTS.md` pointer for non-Claude tools. [plan 001] [plan 002]
- AI development workspace `docs/ai/`: `plans/` (sequentially numbered plans `NNN-slug.md` + auto-generated `INDEX.md`), `memory/` (project state, decisions log, gotchas, session log), `templates/`. [plan 001]
- Claude Code project hooks (`.claude/settings.json`, `.claude/hooks/ai_workflow.py`):
  - **PostToolUse / ExitPlanMode**: approved plans are saved automatically to `docs/ai/plans/NNN-slug.md` and indexed (first saved live: plan 002).
  - **Stop**: blocks finishing (once) when files under `app/` changed but `docs/CHANGELOG.md` was not updated.
  [plan 001] [plan 002]

### Changed
- Specialist calls use Ollama's JSON mode (`format="json"`), and auto-created characters default to supporting (`temporary`) unless the model marks them as central. Character, location and world fields accept near-miss types (e.g. `"age": 17`, `"type": "supporting"`, a single string for a list) and store them coerced, instead of rejecting them. [plan 009] [KI-016]
- Each chapter makes two fewer specialist-model calls: step 4 (Optimize Context) now applies its rules directly instead of asking the model to restate them, and step 5 unloads the specialist with Ollama's unload request instead of a full prediction prompt whose answer was never used. A failed unload is reported as a warning and no longer stops the chapter. [plan 008] [KI-012] [KI-013]
- `POST /api/characters` and `/api/scenes` always store a server-derived slug (`make_slug(slug or name)`: lowercase, `_` separators, letters of any script kept), so a client-supplied `"Elder-Wu"` becomes `elder_wu`. The API is same-origin only: no CORS, and the `Host` must be `127.0.0.1` or `localhost`. [plan 007] [KI-009] [KI-010]
- `app/requirements.txt` uses lower bounds instead of stale exact pins: `fastapi>=0.111`, `uvicorn[standard]>=0.30`, `pydantic>=2.9,<3`, `httpx>=0.27` (was missing), `ollama>=0.4,<1` (was 0.3.3, incompatible with the code). `pip install -r app/requirements.txt` works again on Python 3.11–3.14. [plan 005] [KI-004]
- **Repository reorganized into three areas** [plan 002]:
  - `app/`: the application. `backend/`, `frontend/`, `start.bat` and `requirements.txt` moved here from the root. **Launch with `app/start.bat`**. Manual runs: `cd app/backend`, then `python -m uvicorn main:app`.
  - `data/`: the novel data. Unchanged location (repo root), now explicitly outside the application.
  - `docs/`: all supporting documents. The original root `README.md` became `docs/user-guide.md`. Technical docs live in `docs/technical/`, the changelog in `docs/CHANGELOG.md`, the AI workspace in `docs/ai/`.
  - Root keeps only `README.md` (new short repository map), `CLAUDE.md`, `AGENTS.md`, `.claude/` and `.gitignore`.
- The backend locates `data/` from its new position: the five managers' path helpers and the export route use `Path(__file__).resolve().parents[N] / "data"` (single-line edits; no behaviour change). [plan 002]
- User guide (formerly `README.md`): corrected the *Architecture* section (it listed non-existent `storage.py`, `pipeline.py`, `ollama.py`, `data/world.json`, "JSON/SQLite"), corrected the storage description (JSON files, not a database), and added a *Documentation* section. [plan 001] [KI-023]
- `.gitignore`: ignore Claude Code local settings, the hook error log, and the local CodeAssist index (`.codeassist/`). [plan 001]
- `docs/technical/09`: the summary is split into **Open** and **Fixed** tables, and fixed issues are marked **✅ Fixed** in their headings, so fixed KIs no longer read as open. KI-022 is marked fixed (no bytecode tracked since the plan 002 commit). [KI-022]
- AI rules: commits and PRs carry no AI `Co-Authored-By` / "Generated with" attribution (`docs/ai/RULES.md` §8, decision D-008). The already-published docs/reorganisation commit was reworded without the trailer (`02d6e6d` → `14dd6aa`, same content; since re-credited as `3e61415`, see the next line).
- Repository history: the four commits published on 2026-11-22 were authored with the global work identity, so GitHub credited the work account. They were re-credited to the personal account (Tejasva_Maurya) with the same content, messages and dates (`14dd6aa`→`3e61415`, `5960228`→`058caae`, `eedf02f`→`78ab1ea`, `d1e3f85`→`2b4f3c2`). This repo now sets its own git identity (decision D-010).

### Removed
- The specialist's `select_context` and `predict_updates` prompts, and the unused `novel_meta` argument of `analyze_plot`. [plan 008] [KI-012] [KI-013]
- Unused dependencies `aiofiles` and `python-multipart` from `app/requirements.txt` (nothing imports them). [plan 005] [KI-004]
- Compiled `__pycache__/*.pyc` files are no longer tracked: they moved with the code into `app/backend/`, where `.gitignore` excludes them, so committing the move drops the old tracked copies. [plan 002] [KI-022]

### Fixed
- Saving a character or location from the **+ New Character / + New Location** and **Edit** modals no longer fails with HTTP 422: the form now sends the `slug` (empty on create, so the server derives it from the name). [plan 003] [KI-001]
- The Character/Scene Build tabs now show the created name instead of "undefined". After a **World Build**, the World Settings modal opens with the merged world, and saving it no longer wipes `world_settings.json`. (`apiPost` in `app/frontend/app.js` now returns parsed JSON.) [plan 003] [KI-002]
- Editing a character or location keeps the fields the form doesn't show (first/last chapter). The character list also reloads after each generated chapter, so an edit can't write back outdated profile values. [plan 003] [KI-027]
- Creating a character or location can no longer overwrite an existing one with the same slug (e.g. "Elder Wu" vs "elder wu"):
  - **API:** `POST /api/characters` and `/api/scenes` and the Build tabs' create path now return **409 Conflict** ("… already exists"). They previously replaced the file with 200. The UI shows the error and keeps the form open.
  - **Pipeline:** step 3 keeps the existing profile and emits a `warning`.
  - **Implementation:** new `create()` in the character/scene managers, using an exclusive file open.
  - [plan 004] [KI-036]
- The backend starts even when the `ollama` Python package is missing; generation and the Build tabs then report "ollama Python package not installed: run pip install -r app/requirements.txt". `app/start.bat` now checks every runtime package (and `ollama` >= 0.4) on each launch, installs or upgrades when needed, and stops with the manual command if that fails, instead of only checking FastAPI. [plan 005] [KI-003]
- The app no longer freezes while the specialist model works: specialist calls use the async Ollama client, so sidebars, settings and other requests are served during generation and refine steps. [plan 005] [KI-005]
- **Alt+S** opens Settings with the model lists filled, like the ⚙ button, so saving can no longer blank the writer or specialist model. [plan 006] [KI-006]
- Saving Settings or renaming the novel no longer resets `total_chapters` and `created_at` in `novel_meta.json`, including right after a generation (novel settings now reload when a chapter completes). [plan 006] [KI-007]
- New chapters are numbered highest + 1 by the backend instead of count + 1 by the page, so a gap in the numbering no longer makes the next generation overwrite an existing chapter. [plan 006] [KI-008]
- No more duplicate characters or locations from slug mismatches: the pipeline maps the specialist's matches onto real slugs (ignoring case and `-`/`_`), saves new profiles under a server-derived slug, and no longer crashes on a nameless match; creating anything whose slug is equivalent to an existing one returns 409. [plan 007] [KI-009]
- The UI works the same when opened as `http://localhost:8000` (the frontend calls `/api` on its own origin). [plan 007] [KI-021]
- A name with no letters or digits (e.g. `???`) is refused with 422 instead of being saved as `.json`. [plan 007] [KI-038]
- Chapter summaries now cover the whole chapter, including the ending hook: the summariser gets the full text, or the opening and the ending of very long chapters, instead of only the first 3000 characters. [plan 008] [KI-014]
- Locations evolve with the story: after each chapter, the significance of the locations featured in it is updated from the summariser's `scene_updates` (previously ignored). [plan 008] [KI-013]
- Chapter generation no longer fails, or loses an already-written chapter, when the specialist returns a value with the wrong type (text where a number is expected, a list instead of an object, an empty title). [plan 009] [KI-015]
- Building or updating a character or location can no longer make it disappear: refine merges are validated before saving, auto-profiles with near-miss values are kept instead of dropped, and files saved with wrong types by older versions load again. [plan 009] [KI-016]
- Pipeline warnings (a profile that couldn't be saved, a failed unload, a rejected update) are shown as warning toasts instead of being ignored. [plan 009] [KI-018]


### Security
- Path traversal: a backslash in a URL slug (e.g. `DELETE /api/characters/..%5Cnovel_meta`) could delete files outside the character/scene folders, such as `novel_meta.json` and `world_settings.json` (confirmed on a copy). Slugs are now validated (`[\w-]+`) before any file access. [plan 007] [KI-010]
- Other websites can no longer call the local API: CORS (previously `*`) is removed, and requests with a foreign `Host` header (DNS rebinding) get 400. [plan 007] [KI-010]
- World settings (which can come from the AI) and Ollama model names are HTML-escaped in the World Build snapshot, the model dropdowns and the model browser. [plan 007] [KI-011]

---

## [1.0.0] - 2026-07-13

Initial release, committed as **"Version 01"** (`0f22226`), followed the same day by **"added gitignore file"** (`dead3e3`). Version string: `FastAPI(version="1.0.0")` in `backend/main.py`.

### Added
- **FastAPI backend** (`backend/main.py`) serving the SPA and a JSON + SSE API on `127.0.0.1:8000`, with CORS open.
- **7-step chapter generation pipeline** (`backend/pipeline/chapter_pipeline.py`), streamed as Server-Sent Events: analyse plot → resolve entities → profile new entities → select context → predict updates (unloads specialist) → stream chapter → summarise & update profiles.
- **Dual-model agents** through local Ollama: *specialist* (`backend/agents/specialist.py`, default `phi4-mini:3.8b`, JSON output, temp 0.1, ctx 8192) and *writer* (`backend/agents/writer.py`, default `gemma3:12b`, streaming, temp 0.8, ctx 32768, ~2000-word chapters). VRAM managed with `keep_alive`.
- **Tiered chapter memory** (`backend/pipeline/context_builder.py`): previous chapter's last 400 words, full/short/micro summaries by distance, full or compressed character profiles, main-location profiles, world settings.
- **Automatic entity discovery**: new characters and locations mentioned in a plot are profiled and saved. Character arc notes, cultivation level, abilities, relationships and last-seen chapter are updated after each chapter.
- **Builder modes** in the UI: Character Build, Scene Build, World Build (free text → structured profile, create or merge) via `/api/refine/{character|scene|world}`.
- **CRUD API** for characters, scenes, world settings and novel metadata. Chapter list/read endpoints.
- **JSON-file persistence** (`backend/managers/*`) under `data/` (one file per character, scene and chapter).
- **Ollama model management**: list installed + recommended models (`/api/models`) and pull models with streamed progress (`/api/models/pull`).
- **Export** of the whole novel as `.txt` or `.md` (`/api/export/{fmt}`).
- **Vanilla JS frontend** (`frontend/index.html`, `app.js`, `style.css`): 3-column dark glass UI, live 7-step pipeline visualisation, token streaming, chapter history pills, full-view reader, character/location/world/settings modals, tag inputs, relationship editor, toasts, keyboard shortcuts (`Ctrl+Enter`, `Alt+G/N/S/W`, `Esc`).
- **Windows launcher** `start.bat`: Python detection, first-run dependency install, server start, health polling, browser open.
- `README.md` with setup, model recommendations, usage guide, data structure and troubleshooting.
- `.gitignore` for bytecode, virtualenvs, IDE folders, env files, logs, OS files, build output, SQLite and coverage artefacts (`dead3e3`).

### Known issues at release
- Recorded after the fact in [`docs/technical/09-known-issues-and-tech-debt.md`](technical/09-known-issues-and-tech-debt.md). Most important: KI-001 (manual character/location save → 422), KI-002 (refine responses mishandled; world wipe risk), KI-003/KI-004 (dependency/launcher problems), KI-005 (event loop blocked by specialist calls).
- `backend/**/__pycache__/*.pyc` were committed before `.gitignore` existed and are still tracked (KI-022).

---

<!-- Compare links. On release, add a tag (e.g. v1.0.1) and point the links at tags. -->
[Unreleased]: https://github.com/Tejasva-Maurya/AI_Writer/compare/dead3e3...HEAD
[1.0.0]: https://github.com/Tejasva-Maurya/AI_Writer/compare/0f22226...dead3e3
