# Project state

> Auto-loaded into every Claude session (root `CLAUDE.md` → `docs/ai/RULES.md` → this file). Keep under ~40 lines. Update at the end of every working session.

**Last updated:** 2026-11-27

## Repository layout (plan 002, D-007)
- `app/` = application (`backend/`, `frontend/`, `start.bat`, `requirements.txt`) · `data/` = the novel · `docs/` = user guide, `technical/`, `CHANGELOG.md`, `ai/` (RULES, plans, memory, templates).
- Root: `README.md` (map), `CLAUDE.md` (loader), `AGENTS.md`, `.claude/` (settings + hooks), `.gitignore`.

## Version
- Released: **2.0.0** (2026-11-24, plan 018, D-015). `app/backend/main.py` says `version="2.0.0"`. Major because the HTTP API changed: create returns 409 instead of overwriting, same-origin only, generate returns 409 while one runs.
- 2.0.0 contains plans 001–017 and fixes all 40 known issues; per-plan detail lives in `docs/CHANGELOG.md` and `docs/ai/plans/`. 1.0.0 was 2026-07-13 (`dead3e3`).
- Pushed 2026-11-24 (`03312e5` on GitHub). Annotated tags `v1.0.0` (`dead3e3`) and `v2.0.0` (`03312e5`); GitHub Release https://github.com/Tejasva-Maurya/AI_Writer/releases/tag/v2.0.0 (latest). CI green on `main` and on the tag.
- `[Unreleased]` holds plan 019 (draft review, AI rewrite, @-mentions, prompt reuse; KI-041 fixed; additive), plan 020 (refines join the job guard; KI-042 fixed), plan 021 (dead-code removal), plan 022 (regenerating an earlier chapter; KI-043, KI-044 fixed) plan 023 (a chapter that stops halfway is kept as a draft; D-018) plan 024 (⟳ Regenerate in the UI, always as a draft, D-019; KI-045 fixed: `chapter_number` < 1 → 422) and plan 025 (older versions of a regenerated chapter, the newest 5, to read, restore or delete; D-020; new `data/chapter_versions/`). Plan 020 adds a 409 to the refine routes: read like D-015, the next release would be **3.0.0**, not 2.1.0 (D-017; the user decides at release time).
- Commits carry **no AI attribution trailers** (RULES §8.7, D-008) and are authored as **Tejasva_Maurya <mauryatejasva512004@gmail.com>** via repo-local git config, so GitHub credits the personal account Tejasva-Maurya (D-010). Every commit on `main` is credited to it.

## Active work
- Plans 001–025 are done; no active plan. Plan 025 (older chapter versions; D-020) was merged into `main` on 2026-11-27 through PR https://github.com/Tejasva-Maurya/AI_Writer/pull/7 (rebase merge, `35ab933`; CI green, 8/8); its branch `feat/chapter-versions` still exists. Plan 024 (⟳ Regenerate a saved chapter from the UI; D-019, KI-045) was merged into `main` on 2026-11-27 through PR https://github.com/Tejasva-Maurya/AI_Writer/pull/6 (rebase merge, `b8ec124`; CI green, 8/8); its branch `feat/regenerate-chapter-button` was deleted on 2026-11-27 at the user's request (fully merged first; GitHub has only `main`). Plan 023 (a writer failure or a closed tab keeps the text written so far as a draft, only ✕ Cancel discards it; D-018) was merged into `main` on 2026-11-27 through PR https://github.com/Tejasva-Maurya/AI_Writer/pull/5 (rebase merge, `f684a79`; CI green, 8/8); its branch `feat/keep-partial-chapter` was deleted on 2026-11-27 at the user's request (fully merged first; GitHub has only `main`). Plans 019–022 were merged into `main` through PRs https://github.com/Tejasva-Maurya/AI_Writer/pull/1 to /pull/4 (rebase merges `88c05c6`, `d0494b8`, `febf1d2`, `fc75fc5`; CI green), and each branch was deleted afterwards at the user's request (GitHub has only `main`). The old `improvement` branch was deleted without a backup on 2026-11-24, so the generated chapter 1 that existed only there is gone.
- PRs: push the branch with the github-push skill, then open and merge the PR with `GH_TOKEN="$GH_PUSH_TOKEN" gh pr …`, so the personal account (not `gh`'s work login) is the PR author. If `gh pr create` (GraphQL) keeps failing on the network, first check that no PR was made, then use `gh api -X POST repos/…/pulls` (REST) instead (worked 2026-11-26). Auto-fix can't be enabled for such PRs, because `gh` is signed in as the work account.
- New since plan 019: `data/draft.json` (one draft at a time, `draft_manager`), `/api/draft*` routes, SSE `draft_complete`, `novel_meta.review_drafts` (default on).
- CI (`.github/workflows/ci.yml`) runs on every push; the push token has the Workflows permission.
- `data/` is git-ignored since plan 017, so `git status` no longer shows novel changes (gotchas).

## Suggested next up
1. Test draft review with a real Ollama (not possible on this machine): rewrite quality, approval timing, VRAM.
2. All plan 019 "Not included" follow-ups are done (plans 020–023), and plan 022's UI button is done (plan 024). Older versions of a regenerated chapter are kept since plan 025.
3. No KI is open (45 fixed). New defects get KI-046 onwards.

## Environment facts (dev machine, verified 2026-11-22)
- Windows 11, Git Bash. `py` → Python 3.14.5 (has fastapi 0.141.1, pydantic 2.13.4, uvicorn 0.52.3, httpx 0.28.1). `python` → Python 3.14.0 (separate install).
- **`ollama` Python package NOT installed; `ollama` CLI not on PATH**, so the real pipeline cannot be exercised. To test against the real library without touching site-packages: `py -m pip install --target <temp> --no-deps "ollama==X"` and put `<temp>` on `PYTHONPATH` (plan 005). pip reaches PyPI through the proxy. For HTTP smoke tests, stub `ollama` on `PYTHONPATH` (see plan 002 Outcome). For UI tests, plan 003's Outcome describes a sandbox copy of `app/`+`data/` plus a stub that returns canned refine JSON and streams fake chapter tokens.
- Browser pane: can't attach to a URL on this install. `.claude/launch.json` needs a command (`runtimeExecutable`), so use a temp launcher script and delete the file afterwards.
- Node v24 available (`node --check` for JS syntax).
- Tests and lint: `py -m pytest app/tests`, `py -m ruff check app`. pytest is installed in `py` (9.1.1, seen 2026-11-24); ruff is **not**. Use `py -m pip install -r app/requirements-dev.txt`, or install them into a temp `--target` folder on `PYTHONPATH` (plan 016).
- Git: branch `main`, remote `origin` = https://github.com/Tejasva-Maurya/AI_Writer.git. Tags `vX.Y.Z` from 2.0.0 on (created via the API).
- Hooks are live: the ExitPlanMode auto-save fired on plan 002's approval.
