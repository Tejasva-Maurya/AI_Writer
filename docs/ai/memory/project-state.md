# Project state

> Auto-loaded into every Claude session (root `CLAUDE.md` → `docs/ai/RULES.md` → this file). Keep under ~40 lines. Update at the end of every working session.

**Last updated:** 2026-11-24

## Repository layout (plan 002, D-007)
- `app/` = application (`backend/`, `frontend/`, `start.bat`, `requirements.txt`) · `data/` = the novel · `docs/` = user guide, `technical/`, `CHANGELOG.md`, `ai/` (RULES, plans, memory, templates).
- Root: `README.md` (map), `CLAUDE.md` (loader), `AGENTS.md`, `.claude/` (settings + hooks), `.gitignore`.

## Version
- Released: **2.0.0** (2026-11-24, plan 018, D-015). `app/backend/main.py` says `version="2.0.0"`. Major because the HTTP API changed: create returns 409 instead of overwriting, same-origin only, generate returns 409 while one runs.
- 2.0.0 contains plans 001–017 and fixes all 40 known issues; per-plan detail lives in `docs/CHANGELOG.md` and `docs/ai/plans/`. 1.0.0 was 2026-07-13 (`dead3e3`).
- Pushed 2026-11-24 (`03312e5` on GitHub). Annotated tags `v1.0.0` (`dead3e3`) and `v2.0.0` (`03312e5`); GitHub Release https://github.com/Tejasva-Maurya/AI_Writer/releases/tag/v2.0.0 (latest). CI green on `main` and on the tag.
- `[Unreleased]` holds plan 019 (draft review, AI rewrite, @-mentions, prompt reuse; KI-041 fixed; additive) and plan 020 (refines join the job guard; KI-042 fixed). Plan 020 adds a 409 to the refine routes: read like D-015, the next release would be **3.0.0**, not 2.1.0 (D-017; the user decides at release time).
- Commits carry **no AI attribution trailers** (RULES §8.7, D-008) and are authored as **Tejasva_Maurya <mauryatejasva512004@gmail.com>** via repo-local git config, so GitHub credits the personal account Tejasva-Maurya (D-010). Every commit on `main` is credited to it.

## Active work
- Plans 001–021 are done; no active plan. Plan 021 (dead-code removal, no behaviour change) was merged into `main` on 2026-11-26 through PR https://github.com/Tejasva-Maurya/AI_Writer/pull/3 (rebase merge, `febf1d2`; CI green, 8/8). Its branch `chore/remove-unused-helpers` was deleted on 2026-11-26 at the user's request (fully merged first; GitHub has only `main`). Plan 020 (D-017) was merged into `main` on 2026-11-24 through PR https://github.com/Tejasva-Maurya/AI_Writer/pull/2 (rebase merge, `d0494b8`; CI green, 8/8). Its branch `fix/refine-busy-guard` was deleted on 2026-11-26 at the user's request (fully merged first; GitHub has only `main`). Plan 019 (D-016) was merged into `main` on 2026-11-24 through PR https://github.com/Tejasva-Maurya/AI_Writer/pull/1 (rebase merge, `88c05c6`; CI green on the PR). It re-implements the old `improvement` branch (based on 1.0.0, not mergeable). Both branches were deleted on 2026-11-24 at the user's request, without a backup: GitHub has only `main`, and the generated chapter 1 that existed only on `improvement` is gone.
- PRs: push the branch with the github-push skill, then open and merge the PR with `GH_TOKEN="$GH_PUSH_TOKEN" gh pr …`, so the personal account (not `gh`'s work login) is the PR author. Auto-fix can't be enabled for such PRs, because `gh` is signed in as the work account.
- New since plan 019: `data/draft.json` (one draft at a time, `draft_manager`), `/api/draft*` routes, SSE `draft_complete`, `novel_meta.review_drafts` (default on).
- CI (`.github/workflows/ci.yml`) runs on every push; the push token has the Workflows permission.
- `data/` is git-ignored since plan 017, so `git status` no longer shows novel changes (gotchas).

## Suggested next up
1. Test draft review with a real Ollama (not possible on this machine): rewrite quality, approval timing, VRAM.
2. Remaining follow-ups from plan 019 "Not included": context tiers when regenerating an earlier chapter, keeping partial text as a draft when the writer fails mid-stream. (Done: refine under the busy guard in plan 020, unused helpers in plan 021.)
3. No KI is open (42 fixed). New defects get KI-043 onwards.

## Environment facts (dev machine, verified 2026-11-22)
- Windows 11, Git Bash. `py` → Python 3.14.5 (has fastapi 0.141.1, pydantic 2.13.4, uvicorn 0.52.3, httpx 0.28.1). `python` → Python 3.14.0 (separate install).
- **`ollama` Python package NOT installed; `ollama` CLI not on PATH**, so the real pipeline cannot be exercised. To test against the real library without touching site-packages: `py -m pip install --target <temp> --no-deps "ollama==X"` and put `<temp>` on `PYTHONPATH` (plan 005). pip reaches PyPI through the proxy. For HTTP smoke tests, stub `ollama` on `PYTHONPATH` (see plan 002 Outcome). For UI tests, plan 003's Outcome describes a sandbox copy of `app/`+`data/` plus a stub that returns canned refine JSON and streams fake chapter tokens.
- Browser pane: can't attach to a URL on this install. `.claude/launch.json` needs a command (`runtimeExecutable`), so use a temp launcher script and delete the file afterwards.
- Node v24 available (`node --check` for JS syntax).
- Tests and lint: `py -m pytest app/tests`, `py -m ruff check app`. pytest is installed in `py` (9.1.1, seen 2026-11-24); ruff is **not**. Use `py -m pip install -r app/requirements-dev.txt`, or install them into a temp `--target` folder on `PYTHONPATH` (plan 016).
- Git: branch `main`, remote `origin` = https://github.com/Tejasva-Maurya/AI_Writer.git. Tags `vX.Y.Z` from 2.0.0 on (created via the API).
- Hooks are live: the ExitPlanMode auto-save fired on plan 002's approval.
