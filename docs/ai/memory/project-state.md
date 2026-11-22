# Project state

> Auto-loaded into every Claude session (root `CLAUDE.md` → `docs/ai/RULES.md` → this file). Keep under ~40 lines. Update at the end of every working session.

**Last updated:** 2026-11-22

## Repository layout (plan 002, D-007)
- `app/` = application (`backend/`, `frontend/`, `start.bat`, `requirements.txt`) · `data/` = the novel · `docs/` = user guide, `technical/`, `CHANGELOG.md`, `ai/` (RULES, plans, memory, templates).
- Root: `README.md` (map), `CLAUDE.md` (loader), `AGENTS.md`, `.claude/` (settings + hooks), `.gitignore`.

## Version
- Released: **1.0.0** (2026-07-13, commits `0f22226`, `dead3e3`). `app/backend/main.py` says `version="1.0.0"`.
- `[Unreleased]`: documentation set, CHANGELOG, AI governance + hooks (plan 001); repo reorganisation (plan 002). Only code change: data-path lines in managers/`main.py`. Committed to `main` on 2026-11-22 (plans 001 + 002), not pushed.

## Active work
- Plan 002 (reorganise repo) is done (see `docs/ai/plans/INDEX.md`). No active plan.

## Suggested next up (from `docs/technical/09`, by impact)
1. KI-001 manual character/location save → 422 (missing `slug`) and KI-027 (edit = full replace).
2. KI-002 `apiPost` returns a raw Response (refine UI bugs + world-wipe risk).
3. KI-016 refine-merge saves unvalidated LLM values (entity becomes unloadable).
4. KI-003/KI-004 dependency pins & launcher check (backend cannot start without `ollama`).
5. KI-005 event loop blocked by the sync specialist; KI-014 summariser sees only 3000 chars.

## Environment facts (dev machine, verified 2026-11-22)
- Windows 11, Git Bash. `py` → Python 3.14.5 (has fastapi 0.141.1, pydantic 2.13.4, uvicorn 0.52.3, httpx 0.28.1). `python` → Python 3.14.0 (separate install).
- **`ollama` Python package NOT installed; `ollama` CLI not on PATH**, so the real pipeline cannot be exercised. For HTTP smoke tests, stub `ollama` on `PYTHONPATH` (see plan 002 Outcome).
- Node v24 available (`node --check` for JS syntax).
- Git: branch `main`, remote `origin` = https://github.com/Tejasva-Maurya/AI_Writer.git. No tags yet.
- Hooks are live: the ExitPlanMode auto-save fired on plan 002's approval.
