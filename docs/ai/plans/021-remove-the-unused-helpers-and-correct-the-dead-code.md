---
id: 021
title: "Remove the unused helpers and correct the dead-code inventory"
status: done
approved: 2026-11-26T13:03:18+05:30
session: 32bc173e-8379-4b33-8399-61be0df4d69b
source_file: "C:\\Users\\2466921\\.claude\\plans\\moonlit-wandering-stearns.md"
sha256: 22593098ba68fabd2ac714da42de29d11efb56347fe414c403eb004a74017a0c
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Remove the unused helpers and correct the dead-code inventory

## Goal
Do the next follow-up from plan 019's "Not included": delete the code nothing uses, and make `docs/technical/03` §6 ("Dead / unused code") and the docs that echo it accurate again. No behaviour change.

## Context / evidence (checked 2026-11-26)
- **Dead Python helpers** (grep across `app/`, tests included: no caller):
  - `chapter_manager.get_recent_n` (`app/backend/managers/chapter_manager.py:45`; it also ignores its `include_text` argument)
  - `character_manager.get_as_dict` (`character_manager.py:69`)
  - `scene_manager.get_as_dict` (`scene_manager.py:69`)
  - After removal, `Dict` is unused in those two modules' `typing` imports.
- **Write-only frontend state** (a scan of every `state.<key>` in `app.js`: assigned, never read):
  - `state._profileContext` (declared `app.js:33`, assigned `:1184`, `:1317`)
  - `state.activeMode` (assigned `:1879`, not declared)
- **Nothing else is dead.**
  - Every other Python function referenced only once is a FastAPI route or the exception handler (registered by decorators).
  - No JS function is referenced only once, and every `DOM` cache key is used.
  - The pipeline/pagination scans are in the session.
- **Stale doc rows that claim dead code:**
  - 03 §6 lists the `/static` mount (`main.py:52-53`). It serves the self-hosted fonts since plan 014: `index.html:9` links `/static/fonts/fonts.css`, whose `src` URLs are under `/static/fonts/`.
  - 03 §6 also lists unused imports (`Dict` in main.py, `Character`/`Scene` in specialist.py, `Optional` in context_builder.py). Those were removed in plan 016 (ruff F401); `Dict` in main.py is used by `_generation`/`_job`.
  - The same "/static unused" claim is in 03 §2.2 and in the 04 endpoint index.

## Steps
1. Branch `chore/remove-unused-helpers` from `main` (`3f26de5`); plan 021 → `in-progress`, `reindex`; snapshot `data/`.
2. `app/backend/managers/chapter_manager.py`: delete `get_recent_n`.
3. `app/backend/managers/character_manager.py`, `scene_manager.py`: delete `get_as_dict`, and drop `Dict` from the `typing` import.
4. `app/frontend/app.js`:
   - delete the `_profileContext` state entry and its two assignments in `viewCharacterProfile` / `viewSceneProfile`;
   - delete `state.activeMode = newMode;` in `switchMode`.
5. Docs:
   - `docs/technical/03`:
     - §2.2 `/static` row: it serves the fonts.
     - §2.3: drop the two removed functions from the manager rows.
     - §4.2: drop `_profileContext` and the `activeMode` comment.
     - §6: replace the table with "none known (checked 2026-11-26)", one line on how it was checked, and a note that the `/static` mount is used.
   - `docs/technical/04` endpoint index: `/static/{file}` = self-hosted fonts (`fonts.css` + woff2).
   - "Last verified" bumps.
   - `docs/CHANGELOG.md` `[Unreleased]` → **Removed** (unused internal helpers, no behaviour change) + **Changed** (docs).
   - `docs/ai/memory/project-state.md` (follow-ups list), `session-log.md`.
   - Plan Execution log and Outcome.
6. Verify (below), commit, push with the github-push skill, open the PR with the personal token, and ask before merging.

## Contract / data impact
None: no route, payload, SSE event, model field or file changes. Internal Python functions are removed, but nothing imports them (no plugins; the app is a single process).

## What improves / downsides
- **Improves:** less code to maintain, and the dead-code inventory and the `/static` docs are true again.
- **Downsides:** none expected. If a future feature needs "recent n chapters" or a slug→entity dict, it can be rebuilt in one line (`{c.slug: c for c in get_all()}`, as the pipeline already does).

## Verification
- `py -m pytest app/tests` (116 should still pass), `py -m ruff check app` (catches a leftover unused import), `node --check app/frontend/app.js`, `py_compile` of the changed modules.
- `grep` for the removed names across `app/` and `docs/technical` → only historical mentions.
- UI, a sandbox copy of `app/` with synthetic `zz` data (no LLM needed):
  - open a character profile and a location profile (View, then Edit from the profile);
  - switch all four mode tabs (Character/Scene tabs fill their dropdowns, World shows the snapshot);
  - console clean.
- Real `data/`: SHA-256/size/mtime listing before and after.

## Risks & rollback
- Risk: something uses a removed name dynamically. Ruled out: no `getattr`/string lookups of these names in `app/` (grep), and no test imports them.
- Rollback: revert the PR.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress) on branch `chore/remove-unused-helpers` from `main` (`3f26de5`)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 021]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status: no KI involved)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- None in substance.
- In `app.js` the old `// Profile view context` comment went away with `_profileContext`. The two `_editing…Slug` keys that followed it now have their own comment ("Edit modals: the slug being edited, null = create mode").
- Wording fix: in *Context*, the line "The pipeline/pagination scans are in the session." should read "The scans were run in this session". The saved text is kept as approved.

## Outcome
**Shipped (branch `chore/remove-unused-helpers`, for a PR to `main`):**
- Deleted `chapter_manager.get_recent_n`, `character_manager.get_as_dict` and `scene_manager.get_as_dict` (plus `Dict` from those two modules' imports).
- In `app.js`, deleted `state._profileContext` (the declaration and 2 assignments) and `state.activeMode` (1 assignment).

**Files:**
- Code: `app/backend/managers/{chapter,character,scene}_manager.py`, `app/frontend/app.js`
- Docs: `docs/technical/03` (§2.2 `/static`, §2.3, §4.2, §6 rewritten to "none known" with the method), `docs/technical/04` (`/static` row), `docs/CHANGELOG.md` (Removed + Changed), `docs/ai/memory/{project-state, session-log}.md`

**KIs:** none.

**Verification (2026-11-26):**
- Tests: `py -m pytest app/tests` **116 passed**.
- Lint and syntax: `ruff check app` clean (temp `--target`; it would flag a leftover `Dict` import); `node --check` and `py_compile` OK.
- `grep` across `app/`: the removed names remain only in stale, git-ignored `__pycache__` `.pyc` files.
- Sandbox UI (synthetic `zz` data, no LLM):
  - character profile → Edit, and location profile → Edit, both opened with the right data;
  - all four mode tabs switched; the Character/Scene dropdowns filled; the World snapshot showed;
  - no console messages; `[hidden]` audit empty.
- Real `data/`: SHA-256, sizes and mtimes identical.

**Follow-ups:** the remaining plan 019 items are context tiers when regenerating an earlier chapter, and keeping partial text as a draft when the writer fails mid-stream.
