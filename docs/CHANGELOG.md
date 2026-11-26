# Changelog

All notable changes to **NovelForge AI** are recorded here.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/):
- **MAJOR**: incompatible change to the data files in `data/` or to the HTTP API contract.
- **MINOR**: new user-visible feature, backwards compatible.
- **PATCH**: bug fix, documentation, internal refactor.

**Rules (enforced for AI assistants via `docs/ai/RULES.md` and a Stop hook):**
- Every change under `app/` (code, dependencies, launch script) adds a line under **[Unreleased]** in the same change set.
- Use the sections `Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`. Write one line per change, from the user's perspective, and add references in brackets: `[plan 003]`, `[KI-001]`, file names where useful.
- On release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, bump `version=` in `app/backend/main.py`, add a fresh empty `[Unreleased]`, update the compare links at the bottom, and tag the release commit `vX.Y.Z`.
- Paths in released sections are as they were **at that release** (e.g. 1.0.0 had `backend/` at the root, now `app/backend/`).

---

## [Unreleased]

### Added
- **Draft review before saving:** a new chapter opens as an editable draft (**Draft · Chapter N**) instead of being saved at once. **✓ Approve & save** summarizes it, updates the profiles and adds it to the history; **🗑 Discard** deletes it and offers to remove the characters/locations created for it. The draft is autosaved to `data/draft.json`, so it survives a reload, a closed tab or a restart. One draft at a time: Generate asks to discard a waiting one. New routes `GET/PUT/DELETE /api/draft` and `POST /api/draft/approve`, new SSE event `draft_complete`, new optional `review` field on `POST /api/generate-chapter` (default off, so API clients keep the old behaviour). Ported from the `improvement` branch and rebuilt on 2.0.0 [plan 019]
- **AI rewrite of a selected passage** in the draft: select text, say how it should change, press Enter or **✨ Rewrite selection**; only the selection is replaced, with **↶ Undo rewrite**. Uses the writer model with its full 32k context (`POST /api/draft/rewrite`) [plan 019]
- **@-mentions in the plot box:** type `@` to insert an existing character or location by its exact name (any script, keyboard and mouse). Mentioned entities are sent as `tagged_characters` / `tagged_scenes` and always reach the writer with their full profile, even when the AI misses them [plan 019]
- **Prompt used** in the Full View: the plot a chapter was written from, with **↺ Use this prompt again** [plan 019]
- Setting **Review each chapter as a draft before saving** in ⚙ Settings (`novel_meta.review_drafts`, default on); off = the previous one-click flow [plan 019]

### Changed
- Generation, draft approval and passage rewrites run one at a time (409 while another runs), and step 7 now applies all updates without pausing, so a cancel can no longer leave them half done [plan 019]
- API errors in the UI show the server's own message (`detail`) for the new draft actions [plan 019]
- The test guard `real_data_untouched` also compares folder mtimes, so it catches a file created and deleted in the real `data/` during a test run; `draft_manager` is redirected like the other managers [plan 019]
- Docs: technical/02 (W3, new W11 draft review and W12 @-mentions), 03, 04, 05, 06, 07, 08 (A16–A18), 09 and the user guide describe the draft flow; stale `keep_alive -1` and "no JSON mode" notes corrected [plan 019]
- The Build-tab refines (`POST /api/refine/character|scene|world`) now wait their turn with the other AI jobs: while a chapter is generated, a draft approved or rewritten, or another refine runs, they return **409** with the reason, shown in the Build tab, instead of loading the second model next to the writer; and generate/approve/rewrite return 409 for the few seconds a refine runs. ⚠ A new 409 on existing routes: under the rule D-015 applied, the next release would be 3.0.0 [plan 020]
- Build-tab refine errors show the server's message instead of raw JSON [plan 020]
- Docs: the dead-code inventory (technical/03 §6) is accurate again ("none known", with how it was checked), and technical/03 §2.2 and 04 no longer call the `/static` mount unused: it serves the self-hosted fonts [plan 021]

### Removed
- Unused internal helpers `chapter_manager.get_recent_n`, `character_manager.get_as_dict` and `scene_manager.get_as_dict`, and the write-only frontend state `state._profileContext` and `state.activeMode`. No behaviour change [plan 021]

### Fixed
- A failure while summarizing (step 7), e.g. Ollama stopping, no longer loses the chapter that was just written: it is kept as a draft, and Approve retries [plan 019] [KI-041]
- Edits to a character or location saved while a chapter is being summarized, and World Settings saved while a World Build refine runs, are no longer overwritten; a character deleted meanwhile is no longer written back [plan 020] [KI-042]

## [2.0.0] - 2026-11-24

**Upgrading from 1.0.0.** This is a major release because the HTTP API changed (details under *Changed*, *Fixed* and *Security*):
- Launch with `app/start.bat`: the application moved into `app/` (plan 002).
- `POST /api/characters` and `/api/scenes` return **409** when the name's slug is taken, instead of overwriting, and always store a server-derived slug (plans 004, 007).
- The API is same-origin only: no CORS, and a `Host` other than `127.0.0.1` or `localhost` gets **400** (plan 007).
- `POST /api/generate-chapter` returns **409** while another generation runs; `POST /api/generate-chapter/cancel` is new (plan 010).
- `data/` is no longer in git, so back it up yourself (plan 017).
- Data files written by 1.0.0 still load; no migration is needed.

### Added
- Technical documentation set in `docs/technical/` describing the v1.0.0 state: overview & architecture, workflows (incl. the SSE event contract), low-level design, API reference, data model & storage, configuration, setup & usage, FAQ & troubleshooting, known issues & tech debt (`KI-001`…`KI-035`). [plan 001]
- `docs/CHANGELOG.md` (this file), with history reconstructed from git. [plan 001]
- AI-assistant governance: `docs/ai/RULES.md` (rules, guardrails, doc-impact matrix, definition of done), loaded by a root `CLAUDE.md`, plus a root `AGENTS.md` pointer for non-Claude tools. [plan 001] [plan 002]
- AI development workspace `docs/ai/`: `plans/` (sequentially numbered plans `NNN-slug.md` + auto-generated `INDEX.md`), `memory/` (project state, decisions log, gotchas, session log), `templates/`. [plan 001]
- Claude Code project hooks (`.claude/settings.json`, `.claude/hooks/ai_workflow.py`):
  - **PostToolUse / ExitPlanMode**: approved plans are saved automatically to `docs/ai/plans/NNN-slug.md` and indexed (first saved live: plan 002).
  - **Stop**: blocks finishing (once) when files under `app/` changed but `docs/CHANGELOG.md` was not updated.
  [plan 001] [plan 002]
- **✕ Cancel** button next to **Generate Chapter**, and `POST /api/generate-chapter/cancel`: stops the running generation within a moment; nothing is saved unless the last step had already run. [plan 010] [KI-031]
- **Tests, lint, CI and logging:**
  - a pytest suite in `app/tests/` (71 tests: API, storage, the pipeline with a fake Ollama, helpers; it never touches `data/`)
  - ruff lint, settings in `app/pyproject.toml`
  - a GitHub Actions workflow running both on Ubuntu and Windows with Python 3.11 and 3.14
  - console logging of warnings and errors (skipped data files, pipeline warnings, failed pulls)
  - Dev-only tools are in `app/requirements-dev.txt`; run `py -m pytest app/tests` and `py -m ruff check app`. [plan 016] [KI-025]

### Changed
- **Your novel is no longer stored in git.** `data/` is git-ignored, and the five files tracked until now (novel settings, world settings, one character, one location, an old export) were removed from the repository, **not from disk**. Back up `data/` yourself. A fresh clone starts with an empty novel. Older commits still contain those five files. Pulling this change into another clone deletes them from that clone's folder, so copy them first if you need them there. [plan 017] [KI-030]
- `docs/technical/01` §9: the security table now matches the code (slug validation and HTML escaping exist since plan 007). [plan 017]
- The app is now truly offline: its three fonts (Cinzel, Crimson Pro, JetBrains Mono) are bundled in `app/frontend/fonts/` with their SIL OFL licences, instead of being loaded from Google Fonts (twice) on every page load. The look is unchanged. [plan 014] [KI-034]
- The specialist model no longer stays in VRAM indefinitely after a Character/Scene/World Build or an interrupted generation: Ollama unloads it after 5 idle minutes (`keep_alive=300`, like the writer; it was `-1`). Normal generations are unchanged: it is still unloaded before writing and after the summary. [plan 013] [KI-029]
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
- Pulling a model in Settings no longer reports "installed" when the download failed: an unknown model name, an Ollama error or a download that stopped early now shows "Pull failed: …" with Ollama's reason. [plan 010] [KI-019]
- Only one chapter is generated at a time: a second request (another tab or a script) gets 409 "A chapter is already being generated" instead of running in parallel and overwriting the same chapter file. Closing the tab still stops the generation, and the next one is accepted at once. [plan 010] [KI-031]
- The blinking `▍` cursor disappears when a chapter finishes, fails or is opened from History, instead of staying under the text. [plan 011] [KI-037]
- The "This plot may span multiple chapters" notice appears only when the plot really does, and clears at the next generation (it was always visible). [plan 011] [KI-039]
- Each generation starts with a fresh pipeline panel: no longer dimmed from the previous chapter, and no step left red from an earlier error. [plan 011] [KI-024]
- Settings → Available Models marks a recommended model as installed only when that exact model is pulled; a different size of the same family (e.g. `gemma3:4b` for `gemma3:12b`) no longer counts, so **⬇ Pull** is offered instead of a model that would fail. [plan 012] [KI-020]
- When the backend can't be reached, the page's placeholder settings now use the same specialist model as the backend (`phi4-mini:3.8b`, was `gemma3:12b`). [plan 012] [KI-028]
- **⛶ Full View** right after a generation lists the chapter's characters and locations (it was empty until the chapter was reopened from History); text whose first piece already contains a paragraph break appears at once instead of being held back; and the `Alt+G/N/S/W` shortcuts work with Caps Lock on or Shift held. [plan 013] [KI-032]
- The Settings model browser no longer promises a "Shift+click" that doesn't exist; it points to the Set Writer / Set Specialist / ⬇ Pull buttons. The user guide now recommends the default models (`gemma3:12b` writer, `phi4-mini:3.8b` specialist) instead of `gemma3:12b` for both. [plan 014] [KI-023]
- **📤 Export** works for any novel title and no longer leaves a copy in `data/`: the file is sent straight from memory, and characters Windows forbids in file names (`: ? * " < > |`) become `_` in the download name. Exports now use LF line endings on every system. Older `data/*.txt|md` copies are left in place and can be deleted. [plan 015] [KI-017]
- Setting `OLLAMA_HOST` now applies to Settings' model list and **⬇ Pull** as well as generation, so all of them use the same Ollama; when it can't be reached, Settings names the address it tried. Without `OLLAMA_HOST` the address is `127.0.0.1:11434`, as generation already used. [plan 015] [KI-033]
- Saving a character, location, chapter, the world or the novel settings is now all-or-nothing. A crash or full disk mid-save can no longer leave a half-written file that then silently vanished from the app; a data file that can't be read is now reported in the server console. [plan 016] [KI-026]
- The server starts again on Python 3.11 (the stated minimum): plan 015's export code used syntax that only Python 3.12+ accepts. [plan 016] [KI-040]
- The app is usable in narrow windows. Below 1200 px the sidebars get narrower. Below 900 px the page becomes one scrolling column: the writer first, then characters and locations. Below 600 px the header buttons show only their icons. Wider windows look exactly as before. [plan 017] [KI-035]


### Security
- Path traversal: a backslash in a URL slug (e.g. `DELETE /api/characters/..%5Cnovel_meta`) could delete files outside the character/scene folders, such as `novel_meta.json` and `world_settings.json` (confirmed on a copy). Slugs are now validated (`[\w-]+`) before any file access. [plan 007] [KI-010]
- Other websites can no longer call the local API: CORS (previously `*`) is removed, and requests with a foreign `Host` header (DNS rebinding) get 400. [plan 007] [KI-010]
- World settings (which can come from the AI) and Ollama model names are HTML-escaped in the World Build snapshot, the model dropdowns and the model browser. [plan 007] [KI-011]

### Known issues at release
- None open: all 40 catalogued issues (KI-001 to KI-040) are fixed. See [`docs/technical/09-known-issues-and-tech-debt.md`](technical/09-known-issues-and-tech-debt.md).

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

<!-- Compare links point at release tags (vX.Y.Z). On release, tag the release commit, add a line for the new version and move [Unreleased] to start from its tag. -->
[Unreleased]: https://github.com/Tejasva-Maurya/AI_Writer/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/Tejasva-Maurya/AI_Writer/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/Tejasva-Maurya/AI_Writer/releases/tag/v1.0.0
