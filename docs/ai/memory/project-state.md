# Project state

> Auto-loaded into every Claude session (root `CLAUDE.md` → `docs/ai/RULES.md` → this file). Keep under ~40 lines. Update at the end of every working session.

**Last updated:** 2026-11-22

## Repository layout (plan 002, D-007)
- `app/` = application (`backend/`, `frontend/`, `start.bat`, `requirements.txt`) · `data/` = the novel · `docs/` = user guide, `technical/`, `CHANGELOG.md`, `ai/` (RULES, plans, memory, templates).
- Root: `README.md` (map), `CLAUDE.md` (loader), `AGENTS.md`, `.claude/` (settings + hooks), `.gitignore`.

## Version
- Released: **1.0.0** (2026-07-13, commits `0f22226`, `dead3e3`). `app/backend/main.py` says `version="1.0.0"`.
- `[Unreleased]`: documentation set, CHANGELOG, AI governance + hooks (plan 001); repo reorganisation (plan 002). **Pushed** as `14dd6aa`; it was reworded on 2026-11-22 to drop the Claude co-author trailer (was `02d6e6d`, D-008).
- `[Unreleased]`: plans 003 + 004 committed and **pushed** on 2026-11-22 as `5960228` (via the github-push API; the local SHA was `c02ce8a`, realigned).
  - plan 003: frontend fixes for KI-001, KI-002 and KI-027
  - plan 004: KI-036, so create returns 409 instead of overwriting
- `[Unreleased]`: plan 005 (committed and pushed 2026-11-22, see `git log origin/main`) fixes KI-003 (server starts without ollama; launcher `DEP_CHECK`), KI-004 (requirements are lower bounds, D-009) and KI-005 (async specialist).
- POST no longer upserts (409). When releasing, decide whether that counts as an API break for SemVer.
- Commits carry **no AI attribution trailers** (RULES §8.7, D-008).

## Active work
- Plans 003–005 are done (see `docs/ai/plans/INDEX.md`). No active plan. Everything is committed and pushed.

## Suggested next up (from `docs/technical/09`, by impact)
1. KI-016: refine merge saves unvalidated LLM values (entity becomes unloadable).
2. KI-014: the summariser sees only the first 3000 chars (continuity loses chapter endings).
3. KI-010/KI-011: unvalidated slugs as filenames, open CORS, unescaped `innerHTML`.
4. Quick Low fixes: KI-038 (empty slug → `.json`), KI-037 (cursor never hides, a one-line CSS fix), KI-006/KI-007 (Settings save).

## Environment facts (dev machine, verified 2026-11-22)
- Windows 11, Git Bash. `py` → Python 3.14.5 (has fastapi 0.141.1, pydantic 2.13.4, uvicorn 0.52.3, httpx 0.28.1). `python` → Python 3.14.0 (separate install).
- **`ollama` Python package NOT installed; `ollama` CLI not on PATH**, so the real pipeline cannot be exercised. To test against the real library without touching site-packages: `py -m pip install --target <temp> --no-deps "ollama==X"` and put `<temp>` on `PYTHONPATH` (plan 005). pip reaches PyPI through the proxy. For HTTP smoke tests, stub `ollama` on `PYTHONPATH` (see plan 002 Outcome). For UI tests, plan 003's Outcome describes a sandbox copy of `app/`+`data/` plus a stub that returns canned refine JSON and streams fake chapter tokens.
- Browser pane: can't attach to a URL on this install. `.claude/launch.json` needs a command (`runtimeExecutable`), so use a temp launcher script and delete the file afterwards.
- Node v24 available (`node --check` for JS syntax).
- Git: branch `main`, remote `origin` = https://github.com/Tejasva-Maurya/AI_Writer.git. No tags yet.
- Hooks are live: the ExitPlanMode auto-save fired on plan 002's approval.
