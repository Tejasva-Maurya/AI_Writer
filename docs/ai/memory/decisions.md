# Decision log

> ADR-lite. One entry per non-obvious architectural or process decision. Numbered `D-NNN`, never deleted. Reversed decisions get `Status: Superseded by D-NNN`.
> Entries D-001…D-004 record decisions **inferred from the v1.0.0 code** (original rationale not written down by the author). Treat their "context" as reconstruction.

---

## D-001 — Local-only LLMs via Ollama, with a two-model split
- **Date:** 2026-07-13 (v1.0.0, inferred) · **Status:** Accepted
- **Context:** Personal creative tool. Privacy, no API cost, consumer GPU.
- **Decision:** All inference goes through a local Ollama server. A small *specialist* model (JSON tasks, temp 0.1) and a large *writer* model (prose, temp 0.8). `keep_alive` choreography keeps only one model resident while writing.
- **Consequences:** Quality and speed depend on local hardware. Small specialists produce unreliable JSON, so every consumer must be defensive. No cloud provider abstraction exists.

## D-002 — JSON files instead of a database
- **Date:** 2026-07-13 (v1.0.0, inferred) · **Status:** Accepted
- **Context:** Single user, small data volume, human-readable and hand-editable storage.
- **Decision:** One JSON file per character, scene and chapter under `data/`, plus `novel_meta.json` and `world_settings.json`. Pydantic models double as the file schema.
- **Consequences:** Zero setup and easy backup. No transactions, locking or migrations. Schema changes must be additive with defaults.

## D-003 — No-build vanilla frontend served by FastAPI
- **Date:** 2026-07-13 (v1.0.0, inferred) · **Status:** Accepted
- **Decision:** `index.html` + `style.css` + a single `app.js`, served by FastAPI routes. No framework, bundler or npm.
- **Consequences:** Trivial to run and edit. A large single script (1.9k LOC) with a global `state`. Keep it vanilla unless the user decides otherwise.

## D-004 — SSE over a POST response for pipeline progress
- **Date:** 2026-07-13 (v1.0.0, inferred) · **Status:** Accepted
- **Decision:** `StreamingResponse` emitting `data: {json}\n\n` lines, parsed manually in the browser with `fetch` + `ReadableStream` (not `EventSource`, which cannot POST).
- **Consequences:** Simple and unidirectional. Errors arrive as events (HTTP status is always 200). The event contract must be kept in sync on both sides (CLAUDE.md §3).

## D-005 — Documentation set, CHANGELOG and AI governance
- **Date:** 2026-11-22 · **Status:** Accepted · **Plan:** 001
- **Context:** Development is moving to AI-assisted iterations. We need a trustworthy baseline and guardrails against hallucinated changes and undocumented drift.
- **Decision:** `docs/technical/01–09` describe the current state, with permanent `KI-NNN` IDs for defects. `docs/CHANGELOG.md` uses Keep a Changelog + SemVer. `docs/ai/RULES.md` is the canonical rules file (`AGENTS.md` points to it). `docs/ai/` holds plans and memory.
- **Alternatives considered:** a single large doc (harder to keep current per change); docs in a wiki (not versioned with code).
- **Consequences:** Each change must update the CHANGELOG and the matrix-listed docs (enforced by docs/ai/RULES.md, and for the CHANGELOG by a Stop hook).

## D-006 — Plans auto-saved by hook, numbered `NNN-slug.md` with a generated index
- **Date:** 2026-11-22 · **Status:** Accepted · **Plan:** 001
- **Context:** The user wants every approved plan stored in order, without having to ask the AI to save it.
- **Decision:** A Claude Code `PostToolUse` hook on `ExitPlanMode` runs `.claude/hooks/ai_workflow.py save-plan`. It reads `tool_response.plan`/`filePath`, writes `docs/ai/plans/NNN-<slug>.md` with front-matter (status lifecycle approved → in-progress → done/abandoned/superseded), de-duplicates by sha256, links revisions via `supersedes`, and regenerates `INDEX.md`. A `Stop` hook blocks finishing once when source changed without a CHANGELOG update.
- **Alternatives considered:** relying on instructions only (not deterministic); date-prefixed filenames (less readable sequence); a single plans file (merge-conflict-prone, no per-plan outcome).
- **Consequences:** Deterministic capture for Claude Code. Other tools must use `save-plan --from-file`. Behaviour on plan *rejection* is not documented by Claude Code; the hook only saves when a plan body is present, and supersede/dedupe logic absorbs any stray save.
- **Evidence it works:** plan 002 was auto-saved by the hook on real approval (2026-11-22).

## D-007 — Repository split into `app/` · `data/` · `docs/`
- **Date:** 2026-11-22 · **Status:** Accepted · **Plan:** 002
- **Context:** The root mixed application code, novel data and the newly created documentation/AI files. The user wants to know at a glance which folder to open for which kind of work.
- **Decision:** `app/` holds everything that runs or installs the tool (`backend/`, `frontend/`, `start.bat`, `requirements.txt`). `data/` holds the novel (unchanged location, outside `app/`). `docs/` holds all supporting documents (`user-guide.md`, `technical/`, `CHANGELOG.md`, `ai/` with `RULES.md`, plans, memory, templates). The root keeps only files tools require there: `.claude/`, a loader `CLAUDE.md` that imports `docs/ai/RULES.md`, `AGENTS.md`, a short `README.md` map, and `.gitignore`.
- **Alternatives considered:** `data/` inside `app/` (mixes user content with code; risk of shipping or overwriting it); full rules kept in the root `CLAUDE.md` (clutters the root); root `start.bat` shortcut (rejected to keep the root clean).
- **Consequences:** The backend locates data via `Path(__file__).resolve().parents[3]` (managers) and `parents[2]` (export), so moving `app/backend/` again means changing these six lines. The launcher is `app/start.bat`. New top-level folders are discouraged (RULES.md §1). Paths in the 1.0.0 CHANGELOG section stay historical.

## D-008 — No AI attribution trailers in commits or PRs
- **Date:** 2026-11-22 · **Status:** Accepted · **Plan:** — (user request)
- **Context:** Commit `02d6e6d` (plans 001 + 002) carried `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. GitHub turns co-author trailers into repository contributors, so Claude appeared in the repo's contributor list. The owner wants only human contributors listed.
- **Decision:** Commits and PR descriptions carry no AI `Co-Authored-By` trailers and no "Generated with …" lines (RULES.md §8 item 7). The published commit was reworded to drop the trailer (same tree, author and date): `02d6e6d` → `14dd6aa` (later re-credited as `3e61415`, D-010). Because the corporate proxy resets `git push`, this was done through the GitHub REST API: create the commit, then force-update `refs/heads/main` after checking that it still pointed at the old SHA (a lease).
- **Alternatives considered:** leave history as-is (contributor stays listed); `git push --force-with-lease` (blocked by the proxy); a revert commit (does not remove the trailer from history).
- **Consequences:** `main`'s history was rewritten once. Any other clone must `git fetch && git reset --hard origin/main` (or re-clone) before pulling. GitHub may take a while to refresh its cached contributor list. Tool defaults that add attribution must be overridden in this repo.

## D-009 — Dependencies as lower bounds plus a verified-versions comment
- **Date:** 2026-11-22 · **Status:** Accepted · **Plan:** 005
- **Context:** v1.0.0 pinned exact versions (`ollama==0.3.3`, `pydantic==2.7.1`, …) that matched no working environment: ollama 0.3.3 is incompatible with the code (no typed responses) and pydantic 2.7.1 has no wheels for current Pythons. `httpx` was used but missing.
- **Decision:** `app/requirements.txt` lists only what the code imports, as lower bounds at the oldest API the code needs (`ollama>=0.4` for typed responses and `AsyncClient`; `pydantic>=2.9` because ollama 0.4 requires it), with major-version caps where an API break is likely (`pydantic<3`, `ollama<1`). A header comment records the versions verified and the date. `app/start.bat` enforces the same floor (`ollama >= 0.4`) at launch.
- **Alternatives considered:** exact pins (reproducible but rot quickly, and the user's Python moves faster than the pins: this is what broke v1.0.0); a lock file (`pip-tools`/`uv`) (more tooling than this single-user app needs).
- **Consequences:** fresh installs get current releases; a future breaking release of FastAPI or Uvicorn (uncapped) could need a fix. When upgrading, re-run the plan 005 checks and update the header comment.

## D-010 — Commits in this repo use the owner's personal git identity
- **Date:** 2026-11-23 · **Status:** Accepted · **Plan:** — (user request)
- **Context:** The global git config on the dev machine is the work identity (`Tejasva-Maurya-Cognizant <Tejasva.Maurya@cognizant.com>`). GitHub credits a commit to the account that owns its **author email**, not to the token that pushes it, and the github-push skill preserves author metadata. So the four commits published on 2026-11-22 were credited to the work account, although the push token belongs to the personal account Tejasva-Maurya. The original commits (`0f22226`, `dead3e3`) used `Tejasva_Maurya <mauryatejasva512004@gmail.com>`, which GitHub maps to Tejasva-Maurya.
- **Decision:** This repository sets a **repo-local** identity (`git config user.name "Tejasva_Maurya"`, `git config user.email "mauryatejasva512004@gmail.com"`); the global work identity stays for other repos. The four commits were re-credited on 2026-11-23 through the REST API (same tree, message and dates; author/committer name and email changed; `refs/heads/main` force-updated after a lease check): `14dd6aa`→`3e61415`, `5960228`→`058caae`, `eedf02f`→`78ab1ea`, `d1e3f85`→`2b4f3c2`. Verified: the API maps all six commits on `main` to Tejasva-Maurya.
- **Alternatives considered:** change the global identity (would mis-credit work repos); add the personal email to the work account (mixes accounts); leave history as-is (work account stays a contributor).
- **Consequences:** `.git/config` is not versioned, so a **fresh clone must set the identity again** (gotchas.md). `main` was rewritten a second time: other clones need `git fetch && git reset --hard origin/main`. GitHub may take a while to refresh its cached contributor list.

## D-011 — Specialist calls keep the model loaded for 5 idle minutes by default
- **Date:** 2026-11-23 · **Status:** Accepted · **Plan:** 013 (user choice, asked during planning)
- **Context:** `specialist._call()` defaulted to `keep_alive=-1`, so after a Build-tab call (refine) the specialist stayed in VRAM until Ollama restarted (KI-029). The same default was used by pipeline steps 1–3, so a generation that failed or was cancelled (plan 010) before step 5's explicit unload also left it loaded indefinitely. `keep_alive` is a guarded LLM parameter (RULES §5).
- **Decision:** `_call()` defaults to `keep_alive=300`, the writer's value. Step 5 (`unload`, an empty `generate`) and step 7 (`post_write_update`) keep sending `0`, so the VRAM choreography of a normal generation is unchanged.
- **Alternatives considered:** `0` for refine (frees VRAM at once, but every build reloads the model from disk); `120` (KI-029's suggestion; a shorter warm window than the writer's); changing refine only (failed or cancelled generations would still pin the specialist).
- **Consequences:** consecutive builds stay fast for 5 minutes; an idle specialist frees VRAM by itself. A step-1–3 call more than 5 minutes after the previous one would reload the model (only a delay; these calls run back to back).

## D-012 — Web fonts are self-hosted
- **Date:** 2026-11-24 · **Status:** Accepted · **Plan:** 014 (user choice, asked during planning)
- **Context:** The user guide calls the app "fully offline", but the page loaded Cinzel, Crimson Pro and JetBrains Mono from Google Fonts on every load (twice: an `index.html` `<link>` and a `style.css` `@import`), contacting Google and falling back to system fonts offline (KI-034).
- **Decision:** Bundle the fonts in `app/frontend/fonts/`: the 14 woff2 files Google serves for these families (all subsets, ~247 KB), a `fonts.css` with the same 27 `@font-face` rules pointing at `/static/fonts/`, and the three SIL OFL 1.1 licences (required when redistributing). `index.html` links `/static/fonts/fonts.css`; the existing `/static` mount serves it, so the backend is unchanged.
- **Alternatives considered:** keep Google Fonts and reword the claim (no new files, but the page still contacts Google and looks different offline); only the latin subsets (smaller, but names with other scripts would switch to fallback fonts).
- **Consequences:** No outside request from the UI. The fonts are frozen at the 2026-11-24 versions; the `fonts.css` header says how to regenerate them. Keep the OFL files next to the fonts.

## D-013 — Tests with pytest, lint with ruff, CI on GitHub Actions, logging to the console
- **Date:** 2026-11-24 · **Status:** Accepted · **Plan:** 016 (user choices, asked during planning)
- **Context:** KI-025: no tests, linter, CI or logging; every change was checked with ad-hoc sandbox scripts, and a Python 3.11 syntax error (KI-040) reached `main` unnoticed because the dev machine runs 3.14.
- **Decision:**
  - **Tools:** pytest and ruff as dev-only dependencies in `app/requirements-dev.txt` (the runtime `requirements.txt` and `start.bat` are unchanged). Tool settings live in `app/pyproject.toml`; ruff's rule set is pinned to `E4, E7, E9, F` with target `py311`.
  - **Tests:** in `app/tests/`, using FastAPI's `TestClient` on `127.0.0.1`, a recording fake `ollama` module, and an autouse fixture that points every manager at a temp folder, plus a session guard on the real `data/`.
  - **CI:** `.github/workflows/ci.yml` runs lint, tests and `node --check` on Ubuntu and Windows × Python 3.11 and 3.14. `.github/` is an approved exception to "no new top-level folders" (GitHub requires the location).
  - **Logging:** `logging.basicConfig` in `main.py`, with module loggers.
- **Alternatives considered:**
  - stdlib `unittest` (no new dependencies, but less convenient)
  - pytest only (no linter)
  - skipping CI (avoids the root folder and the token permission, but nothing checks Python 3.11)
- **Consequences:** every change can be verified with two commands. Pushing a commit that touches `.github/workflows/` needs a token with the Workflows permission. A new manager must be added to the `data_dir` test fixture.

## D-014 — The novel (`data/`) is not tracked in git
- **Date:** 2026-11-24 · **Status:** Accepted · **Plan:** 017 (user choice, asked during planning)
- **Context:** KI-030: `data/` (the user's novel) had been tracked since the first commit, so every story change would land in the public history of the GitHub repository.
- **Decision:**
  - `.gitignore` ignores `/data/`, and `git rm -r --cached data/` removed the 5 tracked files from the index only. The files stay on disk.
  - **No history rewrite:** commits before plan 017 still contain those 5 files.
  - **No seed or sample folder:** the app already starts from nothing (managers create their folders lazily; meta and world loaders return defaults).
- **Alternatives considered:**
  - keep tracking `data/` (the status quo, a git backup, but public)
  - a `data.sample/` seed folder (more to maintain, and the app doesn't need it)
  - also purging the files from history (rewrites every commit and needs a force push)
- **Consequences:**
  - Git no longer backs up the novel; the docs tell the user to copy `data/` (07 §6).
  - Other clones lose the 5 files from their working copy when they pull the plan 017 commit.
  - "User data untouched" checks need a before/after listing of `data/`, because `git status` can't see it (RULES §9).
  - Rollback: `git add -f data/`.

## D-015 — Release 2.0.0, tagged and published through the GitHub API
- **Date:** 2026-11-24 · **Status:** Accepted · **Plan:** 018 (user choices, asked during planning)
- **Context:** The first release after 1.0.0. Three HTTP API behaviours changed since 1.0.0: create returns 409 instead of overwriting (plan 004), no CORS and a foreign `Host` gets 400 (plan 007), and generate returns 409 while one runs (plan 010). The CHANGELOG defines MAJOR as an incompatible change to the data files or the HTTP API contract. The repository had no tags, and `git push` is blocked by the proxy.
- **Decision:**
  - **Version 2.0.0**, applying the CHANGELOG's MAJOR rule literally. Data files from 1.0.0 still load.
  - **Annotated tags** `v1.0.0` (retroactively, on `dead3e3`) and `v2.0.0`, plus a **GitHub Release** for 2.0.0 whose notes are the CHANGELOG section.
  - Tags and Releases are created through the REST API after the API push, on the **remote** release commit (an API push gives commits new SHAs).
  - The CHANGELOG compare links point at the tags.
- **Alternatives considered:**
  - 1.1.0 (treat the API changes as defect fixes; the only client is the bundled UI)
  - tags without a Release page
  - no tags (SHA-based links; the release commit's SHA isn't known until after the API push)
- **Consequences:** future releases follow the same steps (RULES §7). The `[Unreleased]` section restarts empty, and doc 09 statuses read `Fixed in v2.0.0`.
