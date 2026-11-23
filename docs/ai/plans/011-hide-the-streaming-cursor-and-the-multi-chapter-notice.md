---
id: 011
title: "Hide the streaming cursor and the multi-chapter notice, reset the pipeline panel between runs (KI-037, KI-024, KI-039)"
status: done
approved: 2026-11-23T19:12:01+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 292c6181073f6f6f51cad4de34d9f0255e0ed351e85113b5f833dd990061411f
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Hide the streaming cursor and the multi-chapter notice, reset the pipeline panel between runs (KI-037, KI-024, KI-039)

## Context
The user asked to fix KI-037 and KI-024. Both are Low, cosmetic, and frontend-only. Read this session:
- **KI-037:** `.text-cursor { display: inline; }` (`style.css:1191-1196`) overrides the browser's `[hidden] { display: none }`. Every `DOM.textCursor.hidden = true` (`app.js:402, 529, 556, 571`) has no effect, so the blinking `▍` stays after a chapter completes, after an error, and under every past chapter that is viewed.
- **KI-024:** `resetPipeline()` (`app.js:641-653`) leaves two styles from the previous run:
  - The 0.4 opacity that `completePipeline()` sets 2 s after completion (`app.js:692-695`), so later runs show a dimmed panel. If a new run starts within those 2 s, the pending timer dims the *new* run.
  - The inline red `borderColor`/`background` that `setStepError()` puts on the failed step (`app.js:709-710`). Inline styles beat the `.step-is-active`/`.step-is-done` classes, so that step stays red in later runs.
- **New, same root cause as KI-037 (proposed as KI-039):** `.multi-chapter-notice { display: flex; }` (`style.css:1199`) also overrides `[hidden]`.
  - `DOM.multiChapterNotice.hidden = true` (`app.js:439`) never hides it.
  - The notice "This plot may span multiple chapters" is visible from page load, whether or not a `multi_chapter` event was sent. It showed in plan 010's UI screenshots, where the stub never sent that event.
  - It is not in `docs/technical/09`.
  - Only `.modal-overlay[hidden]` (`style.css:1301`) and `.mode-panel[hidden]` (`:1958`) have `[hidden]` overrides today. The step icons (`.step-pending/-active/-done`) set no `display`, so they hide correctly.

**Done means:**
- The cursor shows only while text streams.
- The notice shows only after a `multi_chapter` event and is hidden at the start of every run.
- Every run starts with a full-opacity panel and no red step, including a run started within 2 s of the previous one finishing.

## Approach
1. **`app/frontend/style.css`** (KI-037, KI-039): add `[hidden]` overrides next to each rule, in the existing `.mode-panel[hidden]` pattern:
   - `.text-cursor[hidden] { display: none; }` after `.text-cursor`
   - `.multi-chapter-notice[hidden] { display: none; }` after `.multi-chapter-notice`

   Specificity (0,2,0) beats the class rule (0,1,0), so no `!important` is needed. I'm deliberately not adding a global `[hidden] { display: none !important }`: it would change every element at once, which is a larger change than these fixes need.
2. **`app/frontend/app.js`, PIPELINE CONTROL section** (KI-024):
   - A module-level `let _pipelineFadeTimer = null;` (the same style as `_cachedModels`). `completePipeline()` stores its `setTimeout` id there.
   - `resetPipeline()` adds:
     - `clearTimeout(_pipelineFadeTimer)` and `DOM.pipelineSection.style.opacity = ''`
     - per step, `step.style.borderColor = ''` and `step.style.background = ''`
   - `setStepError()` and the fade itself are unchanged.
   - `resetPipeline()` already runs at the start of every generation and on cancel (plan 010), so both paths get the fix.

## Contract / data impact
- None: no API, SSE or `data/` change, and no new DOM ids, classes or keyboard shortcuts.

## Docs to update (RULES §6)
- **`docs/technical/09`:**
  - KI-024 and KI-037 → Fixed [plan 011].
  - Add **KI-039** (Low, Frontend, "Multi-chapter notice never hides (CSS `display: flex` overrides `[hidden]`)") as Fixed [plan 011], with evidence.
  - Update the summary counts.
- **`docs/technical/08` A13:** the dimmed panel / red step workaround is obsolete. Say it's fixed and keep the history.
- **`docs/technical/03`:** §4.4 (`completePipeline`/`setStepError` notes that mention KI-024) and the §5 frontend row.
- **`docs/technical/02`:** W3.4 `complete` row (the cursor hides) and `multi_chapter` row (the notice is hidden at the start of each run).
- **`docs/technical/06`:** the fade line ref.
- **Line references:** remap script for `app.js`/`style.css`, applied only to doc lines unchanged since HEAD, as in plan 010.
- **`docs/CHANGELOG.md` `[Unreleased]` → Fixed:**
  - cursor hides [plan 011] [KI-037]
  - notice hides [plan 011] [KI-039]
  - panel resets between runs [plan 011] [KI-024]
- **`docs/ai/memory/`:** `project-state.md` (next-up list), `session-log.md`.
- **Plan 011:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static check:** `node --check app/frontend/app.js`.
2. **Sandboxes:**
   - Two temp copies of `app/` + `data/`: old = `git archive HEAD`, new = the working tree.
   - A stub `ollama` on `PYTHONPATH`: fast specialist and writer. It raises when the plot contains `zz-fail` and returns `estimated_chapters: 2` when the plot contains `zz-multi`.
   - Both servers run through a temp `.claude/launch.json` (old on 8011, new on 8012), driven in the browser pane.
3. **Checks on both, recording old vs new:**
   - **Audit:** on page load, list every element with `hidden` whose computed `display` is not `none`. Expected: old reports the notice; new reports nothing. Anything else found gets reported and catalogued, not fixed.
   - **Cursor:**
     - After a completed run, the computed `display` of `#text-cursor`: old `inline`, new `none`.
     - The same after viewing a past chapter, and after an error run.
     - New only: the cursor is visible (`inline`) while tokens stream.
   - **Notice:** a `zz-multi` run shows it on both. The next normal run hides it on new and leaves it on old.
   - **Fade:**
     - Run, wait 2.5 s (panel opacity 0.4), start a second run: old stays 0.4, new is back to full.
     - Race: start a run within 1 s of the previous completion. Old dims the new run at 2 s; new stays at full opacity.
   - **Red step:** a `zz-fail` run paints the step red; the next run: old keeps the inline red, new clears it.
   - **Console:** clean on new.
4. **Cleanup:** stop the servers; delete the sandboxes, stub and `launch.json`. `git status --porcelain data/` is empty.

## Risks & rollback
- **CSS:** the two attribute rules only apply while `hidden` is set, so nothing visible changes except elements that were wrongly shown.
- **JS:** the reset only clears inline styles the code itself set. Elements without them are unaffected.
- **Rollback:** revert the two files and the docs.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 011]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- No change to the code approach.
- **"Cursor after an error" and "after viewing a chapter" mid-session:** in both versions the cursor element was detached from the page. A run clears the text area before the first token, and `showChapterOutput` replaces its contents, so there was nothing to compare. The past-chapter case was therefore checked on a fresh page instead, where the cursor is still in its original place: old `inline`, new `none`.
- **Docs:** doc 03 §5's frontend "gaps" cell had only listed now-fixed items, so it now names the remaining gap. Doc 08 A13 also mentions KI-037/KI-039. A gotcha about `display` vs `[hidden]` was added.

## Outcome
- **Shipped:**
  - **`app/frontend/style.css`:**
    - `.text-cursor[hidden] { display: none; }` (`:1197`, KI-037)
    - `.multi-chapter-notice[hidden] { display: none; }` (`:1210`, KI-039)
  - **`app/frontend/app.js`:**
    - `let _pipelineFadeTimer` (`:641`), which `completePipeline()` sets (`:700`)
    - `resetPipeline()` (`:643-660`) calls `clearTimeout(_pipelineFadeTimer)`, clears `pipelineSection.style.opacity`, and clears each step's inline `borderColor`/`background` (KI-024)
- **Files:**
  - Code: `app/frontend/style.css`, `app/frontend/app.js`.
  - Docs:
    - `docs/technical/09`: KI-024 and KI-037 fixed; KI-039 added as fixed; counts updated.
    - `docs/technical/08` A13; `docs/technical/03` §4.4 and §5; `docs/technical/02` W3.4 (`multi_chapter`, `complete`).
    - Line refs remapped in 02, 03 and 06.
    - `docs/CHANGELOG.md`, and memory (project-state, gotchas, session-log).
- **KIs fixed:** KI-024, KI-037, KI-039 (new).
- **CHANGELOG (Fixed):**
  - cursor hides [plan 011] [KI-037]
  - notice shows only when relevant [plan 011] [KI-039]
  - fresh pipeline panel per run [plan 011] [KI-024]
- **Verification:**
  - `node --check app/frontend/app.js`: OK.
  - **Setup:** two sandboxes (HEAD on 8011, working tree on 8012), each with a copy of `data/`, plus a stub `ollama` (`zz-fail` raises, `zz-multi` returns `estimated_chapters: 2`). The same script ran in the browser pane on both.

  | Check | Old | New |
  |---|---|---|
  | Wrongly visible `[hidden]` elements on load | `#text-cursor`, `#multi-chapter-notice` | none |
  | Cursor while streaming / after completion | `inline` / `inline` | `inline` / `none` |
  | Past chapter viewed on a fresh page | cursor `inline` | `none` |
  | Notice: on load / after a `zz-multi` run / during the next run | `flex` / `flex` / `flex` | `none` / `flex` / `none` |
  | Opacity after the fade / during the next run | `0.4` / `0.4` | `0.4` / full |
  | Run started 0.5 s after completion, sampled 1.8 s in | `0.4` | full |
  | Red step after a `zz-fail` run / during the next run | `step-1` / `step-1` | `step-1` / none |
  | Wrongly visible `[hidden]` elements at the end | notice | none |

  - The new page's console was empty.
  - **Cleanup:** sandboxes and the temp `.claude/launch.json` deleted, servers stopped. `git status --porcelain data/` empty.
- **Not verified:** nothing material. The change is frontend-only and was exercised end to end with a stubbed backend.
- **Follow-ups:**
  - None required.
  - Optional (KI-032-style polish): after an error, `setStepError()` leaves the failed step's `◉` icon blinking until the next run.
