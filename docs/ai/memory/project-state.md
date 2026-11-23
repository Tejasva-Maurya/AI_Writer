# Project state

> Auto-loaded into every Claude session (root `CLAUDE.md` → `docs/ai/RULES.md` → this file). Keep under ~40 lines. Update at the end of every working session.

**Last updated:** 2026-11-23

## Repository layout (plan 002, D-007)
- `app/` = application (`backend/`, `frontend/`, `start.bat`, `requirements.txt`) · `data/` = the novel · `docs/` = user guide, `technical/`, `CHANGELOG.md`, `ai/` (RULES, plans, memory, templates).
- Root: `README.md` (map), `CLAUDE.md` (loader), `AGENTS.md`, `.claude/` (settings + hooks), `.gitignore`.

## Version
- Released: **1.0.0** (2026-07-13, commits `0f22226`, `dead3e3`). `app/backend/main.py` says `version="1.0.0"`.
- `[Unreleased]`: documentation set, CHANGELOG, AI governance + hooks (plan 001); repo reorganisation (plan 002). Pushed; now `3e61415` (reworded to drop the Claude trailer, D-008, then re-credited to the personal account, D-010).
- `[Unreleased]`: plans 003 + 004 pushed 2026-11-22; now `058caae` (re-credited, D-010).
  - plan 003: frontend fixes for KI-001, KI-002 and KI-027
  - plan 004: KI-036, so create returns 409 instead of overwriting
- `[Unreleased]`: plan 005 (pushed 2026-11-22; now `2b4f3c2`, re-credited, D-010) fixes KI-003 (server starts without ollama; launcher `DEP_CHECK`), KI-004 (requirements are lower bounds, D-009) and KI-005 (async specialist).
- `[Unreleased]`: plan 006 (committed and pushed 2026-11-23, see `git log origin/main`) fixes KI-006 (Alt+S Settings), KI-007 (Settings save kept fields) and KI-008 (backend numbers chapters highest + 1), all in `app/frontend/app.js`.
- `[Unreleased]`: plan 007 (committed and pushed 2026-11-23, see `git log origin/main`) fixes KI-009 (server-derived slugs, step-2 dedupe), KI-010 (slug validation stops path traversal; CORS removed; TrustedHost), KI-011 (escaped HTML), plus KI-021 and KI-038.
- `[Unreleased]`: plan 008 (committed and pushed 2026-11-23, see `git log origin/main`) fixes KI-012 (explicit unload at step 5), KI-013 (deterministic step 4, scene updates applied, dead args removed) and KI-014 (summariser sees the whole chapter).
- `[Unreleased]`: plan 009 (committed and pushed 2026-11-23, see `git log origin/main`) fixes KI-015 (type-safe pipeline), KI-016 (model coercion, validated merges, `format=json`) and KI-018 (warning toasts).
- `[Unreleased]`: plan 010 (done 2026-11-23, **not committed yet**) fixes KI-019 (pull ends with `success` only after Ollama's own) and KI-031 (one generation at a time: 409 while one runs; `POST /api/generate-chapter/cancel` + **✕ Cancel** button; disconnect cancels).
- POST no longer upserts (409) and now normalises slugs; the API is same-origin only. Generate can now return 409 too (plan 010). When releasing, decide whether that counts as an API break for SemVer.
- Commits carry **no AI attribution trailers** (RULES §8.7, D-008) and are authored as **Tejasva_Maurya <mauryatejasva512004@gmail.com>** via repo-local git config, so GitHub credits the personal account Tejasva-Maurya (D-010). Every commit on `main` is credited to it.

## Active work
- Plans 003–010 are done (see `docs/ai/plans/INDEX.md`). No active plan. Plans 003–009 are committed and pushed; plan 010 is in the working tree, waiting for the user to ask for a commit.

## Suggested next up (from `docs/technical/09`, by impact)
1. KI-025: no tests, lint, CI or logging (the only open Medium). A pytest + `TestClient` suite with a stubbed `ollama` would replace the ad-hoc sandbox checks.
2. Quick Low fixes: KI-037 (cursor never hides, a one-line CSS fix), KI-024 (pipeline panel styles not reset), KI-020 (exact-match "installed" detection).
3. KI-017 (export writes into `data/`; illegal filename characters), KI-026 (non-atomic writes), KI-033 (`OLLAMA_HOST` ignored by model list/pull).

## Environment facts (dev machine, verified 2026-11-22)
- Windows 11, Git Bash. `py` → Python 3.14.5 (has fastapi 0.141.1, pydantic 2.13.4, uvicorn 0.52.3, httpx 0.28.1). `python` → Python 3.14.0 (separate install).
- **`ollama` Python package NOT installed; `ollama` CLI not on PATH**, so the real pipeline cannot be exercised. To test against the real library without touching site-packages: `py -m pip install --target <temp> --no-deps "ollama==X"` and put `<temp>` on `PYTHONPATH` (plan 005). pip reaches PyPI through the proxy. For HTTP smoke tests, stub `ollama` on `PYTHONPATH` (see plan 002 Outcome). For UI tests, plan 003's Outcome describes a sandbox copy of `app/`+`data/` plus a stub that returns canned refine JSON and streams fake chapter tokens.
- Browser pane: can't attach to a URL on this install. `.claude/launch.json` needs a command (`runtimeExecutable`), so use a temp launcher script and delete the file afterwards.
- Node v24 available (`node --check` for JS syntax).
- Git: branch `main`, remote `origin` = https://github.com/Tejasva-Maurya/AI_Writer.git. No tags yet.
- Hooks are live: the ExitPlanMode auto-save fired on plan 002's approval.
