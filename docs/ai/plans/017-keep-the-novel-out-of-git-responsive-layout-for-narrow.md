---
id: 017
title: "Keep the novel out of git, responsive layout for narrow windows (KI-030, KI-035)"
status: done
approved: 2026-11-24T13:55:46+05:30
session: 8e82db1f-b2c4-4901-8528-5594118a09fb
source_file: "C:\\Users\\2466921\\.claude\\plans\\drifting-questing-parnas.md"
sha256: fff208a81cf825709cd0a407f8810b4d7889da6be3eeee3618078012b90e002d
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Keep the novel out of git, responsive layout for narrow windows (KI-030, KI-035)

## Context
The user asked to fix the last two open issues, KI-030 and KI-035 (both Low). Read this session:
- **KI-030:** `data/` (the user's novel) is tracked in git.
  - `git ls-files data` lists 5 files: `novel_meta.json`, `world_settings.json`, `characters/xiao-fan-scientist-inventor.json`, `scenes/neuroscience-lab-night-stormy-weather.json` and the old export `Untitled_Novel.txt`.
  - They have been there since the first commit `0f22226`, so every story change would land in the public history.
  - **User decision (asked this session):** stop tracking `data/` (`git rm -r --cached`, user-approved per RULES §5) and ignore it. **No history rewrite**: old commits keep today's 5 files.
  - **The app already starts from nothing:**
    - Managers create their folders lazily (`ensure_dir`, `storage.write_json`).
    - `novel_meta_manager.load()` and `world_manager.load()` return defaults when the file is missing.
    - Export no longer writes into `data/` (plan 015).
    - So a fresh clone needs no seed folder.
- **KI-035:** `style.css` has no `@media` rules. On a narrow window the writing area is squeezed to nothing:
  - The header's brand and actions each keep `min-width: 200px` (`:182`, `:278`).
  - `.app-layout` is a fixed full-height flex row (`:381-389`) with two `280px` sidebars that never shrink (`--sidebar-w`, `:43`; `.sidebar`, `:394-402`).
  - The pipeline uses a 7-column grid (`:969-973`), and modals are 560/760/880 px wide.
  - **User decision (asked this session):** CSS-only (media queries; no HTML or JS change).

**Done means:**
- Novel changes no longer show up in git, and a fresh clone starts with an empty, working novel. The user's files stay on disk, byte for byte.
- From ~375 px up, nothing overflows horizontally; the writer comes first and the sidebars stack below it on narrow screens.
- At ≥ 1201 px the layout is unchanged.

## Approach
1. **KI-030, `.gitignore`:**
   - Add a block that ignores the user's novel: `/data/` (root only), with a short comment.
   - Then `git rm -r --cached data/`. This removes the 5 files from the index only and leaves the files on disk.
   - Verify with hashes before and after.
2. **KI-035, `app/frontend/style.css`:** a new **RESPONSIVE LAYOUT** banner section at the end, using existing tokens and classes.
   - **`@media (max-width: 1200px)`:**
     - `--sidebar-w: 230px`
     - `.header-brand` and `.header-actions` get `min-width: 0`
     - slightly smaller center padding
   - **`@media (max-width: 900px)`: one scrolling column.**
     - `.app-layout` gets `flex-direction: column` and `overflow-y: auto`; it stays fixed under the header and scrolls as a whole.
     - `.center-panel` gets `order: -1`, `flex: none`, `overflow: visible`: the writer comes first.
     - `.sidebar`: `width: 100%`, `flex: none`, a bottom border instead of the side borders.
     - `.sidebar-scroll` gets `max-height: 40vh`, so a long cast scrolls inside its card.
     - `.pipeline-steps` uses 4 columns; `.form-grid-2` becomes 1 column.
     - The modal overlay gets small padding and modals use `max-height: 92vh`.
     - The header title truncates with an ellipsis.
   - **`@media (max-width: 600px)`:**
     - `.pipeline-steps` uses 2 columns.
     - `.brand-name` is hidden (the ✦ icon stays).
     - Header gaps and padding shrink; the mode tabs may wrap.
     - The toast container gets 12 px margins.
   - **The `[hidden]` trap (gotcha, KI-037/KI-039):** no `display` rule goes on elements the JS toggles with `hidden`.
3. **No backend, HTML, JS or data-format change.**

## Contract / data impact
- **None for the API, SSE or data format.**
- **Git:**
  - The next commit removes the 5 `data/` files from the repository (not from disk).
  - On any **other** clone, pulling that commit deletes those 5 files from its working copy, as for any file removed from git.
  - This clone keeps them, untracked and ignored.
- **`data/` no longer appears in `git status`.** The "user data untouched" check becomes a before/after listing (paths, sizes, mtimes; the tests' session guard already does this).

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-030 and KI-035 → Fixed [plan 017]; update the counts (0 open).
- **`docs/technical/05`:** §1 and the "sample data" section (`data/` is local and git-ignored; a fresh clone starts empty; the old files remain in history up to plan 017).
- **`docs/technical/07`:**
  - §6 Backup: git no longer backs up the novel, so copy `data/`.
  - §1/§5.1 layout notes, where they describe the window.
- **`docs/technical/08`:** the FAQ "Where is my novel stored?" (not in git).
- **`docs/technical/03`:** §4.1 (`style.css`: "No `@media` queries" → the responsive section) and §4.7 layout.
- **`docs/technical/01`:** §7 tree (`data/` local, git-ignored) and §2, if it mentions the desktop-only layout.
- **`docs/user-guide.md`:** backup note; works on narrow windows.
- **Root `README.md`** map (`data/` is not in git).
- **`docs/ai/RULES.md`:**
  - §1 (`data/` is local and git-ignored)
  - §9/§11: how to check that user data was untouched now that git can't see it
- **`docs/CHANGELOG.md`:**
  - **Changed:** `data/` is no longer tracked [plan 017] [KI-030]
  - **Fixed:** responsive layout [plan 017] [KI-035]
- **`docs/ai/memory/`:**
  - `decisions.md`: D-014 (untrack `data/`, no history rewrite)
  - `gotchas.md`: the `data/` entry (git-ignored, so use a listing)
  - `project-state.md`, `session-log.md`
- **Line references:** remap for `style.css` (the new section is appended, so existing refs don't move).
- **Plan 017:** status, execution log, outcome, then `reindex`.

## Verification
1. **KI-030:**
   - Hash every file in `data/` (SHA-256), run `git rm -r --cached data/`, and hash again: identical, nothing deleted.
   - `git status` shows exactly the 5 `data/` files as staged deletions plus `.gitignore`.
   - `git check-ignore -v data/novel_meta.json` names the new rule.
   - A temp file created in `data/` and removed again never appears in `git status`.
2. **Fresh clone:**
   - Copy only `app/` to a temp folder (no `data/`) and start uvicorn there.
   - `GET /api/novel-meta` returns the defaults; `/api/characters`, `/api/scenes` and `/api/chapters` return `[]`; `/api/world` returns the defaults; `/api/export/txt` returns 200.
   - `POST /api/characters` creates `data/characters/...` in the temp folder.
   - Stop the server.
3. **Suite:** `py -m pytest app/tests` (it needs no `data/`) and `py -m ruff check app`, with the dev tools in a temp folder. `node --check app/frontend/app.js` too.
4. **KI-035 in the browser pane**, old (HEAD) vs new, each on a sandbox copy:
   - **Widths:** 375×812 (mobile), 768×1024 (tablet), 1100×800 and desktop (≥ 1280).
   - **Per width, record:**
     - horizontal overflow (`document.documentElement.scrollWidth > innerWidth`)
     - the width of `#center-panel`
     - whether the sidebars come below the center (`getBoundingClientRect().top`)
     - the computed `grid-template-columns` of `.pipeline-steps`
     - whether the header overflows (`.app-header` `scrollWidth > clientWidth`)
     - whether the Settings modal fits the viewport
   - **Expected:**
     - Old at 375 px: a center column of a few px (or overflow).
     - New: no overflow, the center at full width, sidebars below; 4 pipeline columns at 768 px and 2 at 375 px.
     - At desktop width the new values equal the old ones (sidebars 280 px, row layout).
   - Screenshots at each width; the console is clean.
   - Reset the viewport to desktop afterwards.
5. **Cleanup:**
   - Remove the sandboxes, temp tools, `launch.json` and caches.
   - Confirm the real `data/` with the before/after listing and hashes (git no longer can).
- **Not verifiable:** a real phone or touch device (the pane's mobile emulation stands in).

## Risks & rollback
- **No more git backup:** the user must back up `data/` themselves; the docs say so prominently.
- **Old history:** commits before this one still contain the 5 files (no rewrite, as chosen). A later history purge stays possible.
- **Other clones:** they lose the 5 files from their working copy on pull; back them up first.
- **Layout breakpoints** are heuristics; desktop ≥ 1201 px is untouched.
- **Rollback:** `git add -f data/` restores tracking; revert the CSS section and the docs.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 017]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **More header rules at ≤ 600 px.** The first version still overflowed the header at 375 px (the action buttons took 345 px). The header buttons now show only their icons (they keep their `title` and `aria-label`) and the chapter badge drops its label: the actions take 150 px and nothing overflows.
- **`.generate-row` wraps at ≤ 600 px.** The "Will generate Chapter N" hint was squeezed next to the Generate button at 375 px.
- **Ignore check.** The plan's "temp file in `data/`" was `data/zz_probe.json`: created, confirmed ignored by `git status`, then deleted.
- **CI-style check added:** the suite also ran in a copy of `app/` with no `data/`, as a fresh CI checkout now is.
- **Doc 01 §9 corrected in passing** (RULES §2.1): its security table still said slugs were unchecked (KI-010) and the world snapshot and model browser unescaped (KI-011), both fixed in plan 007.

## Outcome
- **Shipped:**
  - **KI-030:**
    - `.gitignore` gained a top block that ignores `/data/` (`.gitignore:1-3`).
    - `git rm -r --cached data/` staged the removal of the 5 tracked files (user-approved; no history rewrite; D-014): `novel_meta.json`, `world_settings.json`, `characters/xiao-fan-scientist-inventor.json`, `scenes/neuroscience-lab-night-stormy-weather.json` and `Untitled_Novel.txt`.
    - The files stay on disk, untracked and ignored.
  - **KI-035:** a *Responsive layout* section at the end of `app/frontend/style.css` (`:2385-2439`), CSS only:
    - **≤ 1200 px:** `--sidebar-w: 230px`; the brand and actions may shrink; less center padding.
    - **≤ 900 px:** a scrolling column with the writer first (`order: -1`) and full-width sidebars (lists capped at `40vh`); 4 pipeline columns; 1 form column; modals capped at `92vh`; an ellipsis title.
    - **≤ 600 px:** a compact, icon-only header; 2 pipeline columns; wrapping mode tabs and Generate row; full-width toasts.
- **Files changed:**
  - **Git and code:** `.gitignore`, the 5 `data/` files (index only), `app/frontend/style.css`.
  - **Technical docs:** `docs/technical/09`, `05`, `07`, `08`, `03`, `01`.
  - **Other docs:** `docs/user-guide.md`, `README.md`, `docs/ai/RULES.md`, `docs/CHANGELOG.md`.
  - **Memory:** `docs/ai/memory/decisions.md` (D-014), `gotchas.md`, `project-state.md`, `session-log.md`.
- **KIs fixed:** KI-030, KI-035. None is open now (40 fixed).
- **CHANGELOG:**
  - Changed: "Your novel is no longer stored in git…" [plan 017] [KI-030], plus the doc 01 §9 correction [plan 017].
  - Fixed: "The app is usable in narrow windows…" [plan 017] [KI-035].
- **Verification:**
  - **KI-030:**
    - SHA-256, size and mtime of all 5 files in the real `data/` were identical before the `git rm --cached` and at the end of the session.
    - `git status` showed exactly the 5 staged deletions plus `.gitignore`.
    - `git check-ignore -v data/novel_meta.json` → `.gitignore:3:/data/`, and the probe file was ignored.
  - **Fresh clone (port 8013):** a copy of `app/` with no `data/` answered `GET` novel-meta, characters, scenes, chapters, world and `export/txt` with 200 and defaults. `POST /api/characters` created `data/characters/zz_test_hero.json` in the copy.
  - **KI-035 in the browser pane, HEAD (8011) vs working tree (8012):**
    - **375×812:** writer 40 → 370 px. The page and header no longer overflow sideways; the sidebars move below; 2 pipeline columns; Settings fits.
    - **768×1024:** writer 208 → 762 px; sidebars below; 4 pipeline columns; Settings fits.
    - **1100×800:** writer 540 → 640 px; sidebars 280 → 230 px; still a row; no overflow.
    - **1400×900:** all 521 elements have the same position and size, except the animated orbs and button shimmer.
    - The console stayed clean.
  - **Suite:** `py -m pytest app/tests` → 71 passed; `py -m ruff check app` → all checks passed (pytest and ruff in a temp `--target` folder); `node --check app/frontend/app.js` OK. The suite also passed (71) in a copy of `app/` with no `data/`.
  - **CI after the push** (2026-11-24): the run for `0ca15eb`, the first checkout without `data/`, was green on all four jobs, Ubuntu and Windows × Python 3.11 and 3.14 (https://github.com/Tejasva-Maurya/AI_Writer/actions/runs/45366046705).
  - **Not verified:** a real phone or touch device.
- **Follow-ups:**
  - **Other clones:** pulling this commit deletes the 5 `data/` files from their working copy, so back them up there first.
  - **History:** older commits still hold those files. Purging them would need a history rewrite and a force push.
  - **Release:** every catalogued KI is fixed, so a release is next.
