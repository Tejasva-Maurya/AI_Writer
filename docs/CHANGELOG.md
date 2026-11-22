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
- **Repository reorganized into three areas** [plan 002]:
  - `app/`: the application. `backend/`, `frontend/`, `start.bat` and `requirements.txt` moved here from the root. **Launch with `app/start.bat`**. Manual runs: `cd app/backend`, then `python -m uvicorn main:app`.
  - `data/`: the novel data. Unchanged location (repo root), now explicitly outside the application.
  - `docs/`: all supporting documents. The original root `README.md` became `docs/user-guide.md`. Technical docs live in `docs/technical/`, the changelog in `docs/CHANGELOG.md`, the AI workspace in `docs/ai/`.
  - Root keeps only `README.md` (new short repository map), `CLAUDE.md`, `AGENTS.md`, `.claude/` and `.gitignore`.
- The backend locates `data/` from its new position: the five managers' path helpers and the export route use `Path(__file__).resolve().parents[N] / "data"` (single-line edits; no behaviour change). [plan 002]
- User guide (formerly `README.md`): corrected the *Architecture* section (it listed non-existent `storage.py`, `pipeline.py`, `ollama.py`, `data/world.json`, "JSON/SQLite"), corrected the storage description (JSON files, not a database), and added a *Documentation* section. [plan 001] [KI-023]
- `.gitignore`: ignore Claude Code local settings, the hook error log, and the local CodeAssist index (`.codeassist/`). [plan 001]

### Removed
- Compiled `__pycache__/*.pyc` files are no longer tracked: they moved with the code into `app/backend/`, where `.gitignore` excludes them, so committing the move drops the old tracked copies. [plan 002] [KI-022]

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
