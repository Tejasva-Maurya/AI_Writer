# Project state

> Auto-loaded into every Claude session (root `CLAUDE.md` → `docs/ai/RULES.md` → this file). Keep under ~40 lines. Update at the end of every working session.

**Last updated:** 2026-11-24

## Repository layout (plan 002, D-007)
- `app/` = application (`backend/`, `frontend/`, `start.bat`, `requirements.txt`) · `data/` = the novel · `docs/` = user guide, `technical/`, `CHANGELOG.md`, `ai/` (RULES, plans, memory, templates).
- Root: `README.md` (map), `CLAUDE.md` (loader), `AGENTS.md`, `.claude/` (settings + hooks), `.gitignore`.

## Version
- Released: **2.0.0** (2026-11-24, plan 018, D-015). `app/backend/main.py` says `version="2.0.0"`. Major because the HTTP API changed: create returns 409 instead of overwriting, same-origin only, generate returns 409 while one runs.
- 2.0.0 contains plans 001–017 and fixes all 40 known issues; per-plan detail lives in `docs/CHANGELOG.md` and `docs/ai/plans/`. 1.0.0 was 2026-07-13 (`dead3e3`).
- **Release commit not committed yet** (plan 018). Tags `v1.0.0` (on `dead3e3`) and `v2.0.0` plus a GitHub Release come after the push, via the REST API.
- `[Unreleased]` is empty.
- Commits carry **no AI attribution trailers** (RULES §8.7, D-008) and are authored as **Tejasva_Maurya <mauryatejasva512004@gmail.com>** via repo-local git config, so GitHub credits the personal account Tejasva-Maurya (D-010). Every commit on `main` is credited to it.

## Active work
- Plan 018 (release 2.0.0) is done in the working tree, waiting for commit, push, tags and Release. Plans 001–017 are done.
- CI (`.github/workflows/ci.yml`) runs on every push; the push token has the Workflows permission.
- `data/` is git-ignored since plan 017, so `git status` no longer shows novel changes (gotchas).

## Suggested next up
1. No KI is open (40 fixed). New defects get KI-041 onwards; new work goes under `[Unreleased]`.

## Environment facts (dev machine, verified 2026-11-22)
- Windows 11, Git Bash. `py` → Python 3.14.5 (has fastapi 0.141.1, pydantic 2.13.4, uvicorn 0.52.3, httpx 0.28.1). `python` → Python 3.14.0 (separate install).
- **`ollama` Python package NOT installed; `ollama` CLI not on PATH**, so the real pipeline cannot be exercised. To test against the real library without touching site-packages: `py -m pip install --target <temp> --no-deps "ollama==X"` and put `<temp>` on `PYTHONPATH` (plan 005). pip reaches PyPI through the proxy. For HTTP smoke tests, stub `ollama` on `PYTHONPATH` (see plan 002 Outcome). For UI tests, plan 003's Outcome describes a sandbox copy of `app/`+`data/` plus a stub that returns canned refine JSON and streams fake chapter tokens.
- Browser pane: can't attach to a URL on this install. `.claude/launch.json` needs a command (`runtimeExecutable`), so use a temp launcher script and delete the file afterwards.
- Node v24 available (`node --check` for JS syntax).
- Tests and lint: `py -m pytest app/tests`, `py -m ruff check app`. pytest and ruff are **not** installed in `py`'s site-packages here. Use `py -m pip install -r app/requirements-dev.txt`, or install them into a temp `--target` folder on `PYTHONPATH` (plan 016).
- Git: branch `main`, remote `origin` = https://github.com/Tejasva-Maurya/AI_Writer.git. Tags `vX.Y.Z` from 2.0.0 on (created via the API).
- Hooks are live: the ExitPlanMode auto-save fired on plan 002's approval.
