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
- POST no longer upserts (409). When releasing, decide whether that counts as an API break for SemVer.
- Commits carry **no AI attribution trailers** (RULES §8.7, D-008).

## Active work
- Plans 003 and 004 are done (see `docs/ai/plans/INDEX.md`). No active plan.

## Suggested next up (from `docs/technical/09`, by impact)
1. KI-016: refine merge saves unvalidated LLM values (entity becomes unloadable).
2. KI-003/KI-004: dependency pins and launcher check (the backend can't start without `ollama`).
3. KI-005: event loop blocked by the sync specialist. KI-014: summariser sees only 3000 chars.
4. Quick Low fixes: KI-038 (empty slug → `.json`), KI-037 (cursor never hides, a one-line CSS fix), KI-006/KI-007 (Settings save).

## Environment facts (dev machine, verified 2026-11-22)
- Windows 11, Git Bash. `py` → Python 3.14.5 (has fastapi 0.141.1, pydantic 2.13.4, uvicorn 0.52.3, httpx 0.28.1). `python` → Python 3.14.0 (separate install).
- **`ollama` Python package NOT installed; `ollama` CLI not on PATH**, so the real pipeline cannot be exercised. For HTTP smoke tests, stub `ollama` on `PYTHONPATH` (see plan 002 Outcome). For UI tests, plan 003's Outcome describes a sandbox copy of `app/`+`data/` plus a stub that returns canned refine JSON and streams fake chapter tokens.
- Browser pane: can't attach to a URL on this install. `.claude/launch.json` needs a command (`runtimeExecutable`), so use a temp launcher script and delete the file afterwards.
- Node v24 available (`node --check` for JS syntax).
- Git: branch `main`, remote `origin` = https://github.com/Tejasva-Maurya/AI_Writer.git. No tags yet.
- Hooks are live: the ExitPlanMode auto-save fired on plan 002's approval.
