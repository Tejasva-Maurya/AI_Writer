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
- **Decision:** Commits and PR descriptions carry no AI `Co-Authored-By` trailers and no "Generated with …" lines (RULES.md §8 item 7). The published commit was reworded to drop the trailer (same tree, author and date): `02d6e6d` → `14dd6aa`. Because the corporate proxy resets `git push`, this was done through the GitHub REST API: create the commit, then force-update `refs/heads/main` after checking that it still pointed at the old SHA (a lease).
- **Alternatives considered:** leave history as-is (contributor stays listed); `git push --force-with-lease` (blocked by the proxy); a revert commit (does not remove the trailer from history).
- **Consequences:** `main`'s history was rewritten once. Any other clone must `git fetch && git reset --hard origin/main` (or re-clone) before pulling. GitHub may take a while to refresh its cached contributor list. Tool defaults that add attribution must be overridden in this repo.
