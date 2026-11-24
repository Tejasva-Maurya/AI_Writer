---
id: 014
title: "Self-hosted fonts so the app is truly offline, accurate model-browser copy and model recommendations (KI-034, KI-023)"
status: done
approved: 2026-11-24T11:27:34+05:30
session: 8e82db1f-b2c4-4901-8528-5594118a09fb
source_file: "C:\\Users\\2466921\\.claude\\plans\\drifting-questing-parnas.md"
sha256: 8ee9f5d1a6c2742644a304b32edad26cb84442af8a87f018066ef7038a47d752
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Self-hosted fonts so the app is truly offline, accurate model-browser copy and model recommendations (KI-034, KI-023)

## Context
The user asked to fix KI-023 and KI-034 (both Low). Read this session:
- **KI-034:** the user guide's tagline says "fully offline" (`docs/user-guide.md:5`), but the page loads its three fonts from Google, twice:
  - preconnects plus a stylesheet `<link>` (`app/frontend/index.html:9-11`)
  - an `@import` of the same URL (`app/frontend/style.css:6`)

  So every page load contacts `fonts.googleapis.com`/`fonts.gstatic.com`; offline, the fonts fall back to Georgia/Consolas.
  - **User decision (asked this session):** self-host the fonts.
  - **Checked (read-only):** Google's CSS for these families has 27 `@font-face` blocks over **14 woff2 files**, about **247 KB** for all subsets (latin 125 KB, latin-ext 80 KB, the rest small).
  - The SIL OFL licence texts are reachable on GitHub, and Python's `mimetypes` serves `.woff2` as `font/woff2`.
  - `app/frontend/` is already served at `/static` (`main.py:42-44`), so no backend change is needed.
- **KI-023 (remaining parts):**
  - The Settings model-browser subtitle says "Click a model to set as writer. Shift+click to set as specialist." (`index.html:766`), but only explicit **Set Writer / Set Specialist / ⬇ Pull** buttons exist.
  - The user guide recommends `gemma3:12b` as the specialist (Step 2 pulls it twice, `user-guide.md:64-68`; "Recommended setup", `:99`), while the default specialist is `phi4-mini:3.8b` (`models.py:148`). The VRAM design (docs/technical/01 §6) assumes a small specialist.
  - The README architecture part was already fixed in plan 001.

**Done means:**
- The UI makes no request outside the machine and looks the same online and offline.
- The fonts' licences ship with them.
- The subtitle describes the real buttons, and the user guide recommends the default models.

## Approach
1. **New `app/frontend/fonts/`:**
   - **Font files:** the 14 woff2 files, downloaded once from the exact Google Fonts URL the page uses today. They get readable names: `<family>[-italic]-<subset>.woff2`, e.g. `cinzel-latin.woff2`, `crimson-pro-italic-latin-ext.woff2`.
   - **`fonts.css`:** Google's 27 `@font-face` blocks, kept as they are (`font-display: swap`, `unicode-range`, weights), with each `src` rewritten to `/static/fonts/<file>.woff2`. A header comment records the source URL, the date and how to regenerate.
   - **Licences:** `OFL-Cinzel.txt`, `OFL-CrimsonPro.txt`, `OFL-JetBrainsMono.txt` (SIL OFL 1.1, which requires shipping the licence and copyright notice with the fonts).
   - **The download script is not committed.** It is a one-off; the steps go in the CSS header and the plan outcome.
2. **`index.html`:** replace the three Google lines (`:9-11`) with `<link rel="stylesheet" href="/static/fonts/fonts.css">`.
3. **`style.css`:** delete the `@import` (`:6`) and keep the fonts banner comment, now pointing to `fonts/fonts.css`. The `--font-*` tokens and their fallbacks are unchanged.
4. **`index.html:766` (KI-023):** the subtitle becomes "Use Set Writer / Set Specialist on an installed model, or ⬇ Pull to download one."
5. **`docs/user-guide.md` (KI-023):**
   - **Step 2:** the specialist is `ollama pull phi4-mini:3.8b` (the default); the lighter alternatives become `llama3.1:8b` and `mistral-nemo:12b`.
   - **"Recommended setup":** the defaults, `gemma3:12b` writer + `phi4-mini:3.8b` specialist. It notes that a larger specialist can improve summaries at the cost of speed and VRAM, and gives `llama3.1:8b` + `phi4-mini:3.8b` for low VRAM.

## Contract / data impact
- **None:** no API, SSE, `data/` or model change; no new Python dependency (static assets only); no backend change. The new files are served through the existing `/static` mount.

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-023 and KI-034 → Fixed [plan 014]; KI-023 leaves the "partly fixed" note; update the counts.
- **`docs/technical/01`:**
  - §3 "Local-only" row (no more Google Fonts)
  - §4 stack row (fonts self-hosted, OFL)
  - §5 diagram: drop the `fonts.googleapis.com` edge
- **`docs/technical/03`** §4.1: the `index.html`/`style.css` rows, plus a `fonts/` row.
- **`docs/technical/07`** §1: the Internet row (fonts no longer need it).
- **`docs/technical/08`** FAQ "Does anything leave my machine?": no web fonts any more.
- **`docs/user-guide.md`:** the architecture tree gets `fonts/`, plus the KI-023 edits above.
- **`docs/CHANGELOG.md`:**
  - **Changed:** fonts bundled; nothing loads from Google [plan 014] [KI-034]
  - **Fixed:** model-browser copy and the user guide's model recommendation [plan 014] [KI-023]
- **`docs/ai/memory/`:**
  - `decisions.md`: D-012, self-hosted fonts (licence and regeneration notes)
  - `project-state.md`, `session-log.md`
- **Line references:** remap for `index.html` and `style.css`.
- **Plan 014:** status, execution log, outcome, then `reindex`.

## Verification
1. **Font files:**
   - Each file starts with the woff2 signature `wOF2` and matches Google's `Content-Length`.
   - Every `url()` in `fonts.css` points to an existing file, and every file is referenced.
2. **Sandboxes:** HEAD on 8011, working tree on 8012, each with a copy of `data/`, no ollama needed. `GET /static/fonts/fonts.css` and each woff2 return 200, and the woff2 files come back as `font/woff2`.
3. **Browser pane, old vs new:**
   - **Network:** list the requests per page load. Old hits `fonts.googleapis.com` (`<link>` + `@import`) and `fonts.gstatic.com`; new makes none outside `127.0.0.1`.
   - **Fonts load:** after `document.fonts.ready`, check `document.fonts.check('16px Cinzel')`, `'16px "Crimson Pro"'`, `'italic 16px "Crimson Pro"'` and `'16px "JetBrains Mono"'`. Each loaded face must come from `/static/fonts/`.
   - **Same look:** compare screenshots of the header and a card.
   - **KI-023:** open Settings; the subtitle reads the new text.
   - The console is clean.
4. **Cleanup:** stop the servers; delete the sandboxes, download temp files and `launch.json`. `git status --porcelain data/` is empty.
- **Not verifiable:** a truly disconnected machine. The network log showing no external request stands in for it.

## Risks & rollback
- **Font versions:** the files are frozen at today's Google versions; they no longer update by themselves. The regeneration steps are in `fonts.css`.
- **Repository size:** about 250 KB of binary assets.
- **Push:** the GitHub API path handles binary blobs (base64). It can be flaky, as on 2026-11-23; retry later if so.
- **Rollback:** restore the three `<link>` lines and the `@import`, and delete `app/frontend/fonts/`.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 014]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **`document.fonts.check('16px Cinzel')`** was `false` on old and new alike. The page uses only Cinzel's 600/700 weights, so the 400 face is never requested. That is expected, not a regression. Instead, the set of *loaded* faces was compared: the same six on both.
- **Screenshots:** they caught both pages mid fade-in, so they show the same typefaces rather than pixel-identical frames.
- **Docs:** doc 01's header keeps its scoped dates (now also "§2–4 and §7 fonts, plan 014").

## Outcome
- **Shipped:**
  - **`app/frontend/fonts/` (new, KI-034):**
    - 14 woff2 files, named `<family>[-italic]-<subset>.woff2`, 247,252 bytes in all; each checked for the `wOF2` signature and against Google's `Content-Length`.
    - `fonts.css`: 27 `@font-face` rules as Google serves them (`font-display: swap`, `unicode-range`), `src` under `/static/fonts/`, with a header naming the source URL, the date and how to regenerate.
    - `OFL-Cinzel.txt`, `OFL-CrimsonPro.txt`, `OFL-JetBrainsMono.txt`.
    - The one-off download script was not committed (deleted).
  - **`index.html`:**
    - The two preconnects and the Google stylesheet became `<link rel="stylesheet" href="/static/fonts/fonts.css">` (`:9`).
    - The model-browser subtitle now describes the real buttons (`:764`, KI-023).
  - **`style.css`:** the Google `@import` was replaced by a pointer comment.
  - **`docs/user-guide.md` (KI-023):** Step 2 pulls `phi4-mini:3.8b` as the specialist, and "Recommended setup" recommends the defaults. The architecture tree lists `fonts/`.
- **Files:**
  - Code: `app/frontend/index.html`, `app/frontend/style.css`, plus the new `app/frontend/fonts/` (18 files).
  - Docs:
    - `docs/technical/09`: KI-023 and KI-034 fixed; there is no "partly fixed" any more; counts are 6 open, 33 fixed.
    - `01` (§2 local-only, §3 stack, §4 diagram, §7 tree, header), `03` (§4.1 `fonts/` and `style.css` rows; the line ref `style.css:7-60`), `07` §1 (Internet row), `08` (privacy FAQ), `docs/user-guide.md`.
    - `docs/CHANGELOG.md`, `docs/ai/memory/decisions.md` (D-012), and memory (project-state, session-log).
- **KIs fixed:** KI-034, KI-023 (fully; the README part was fixed in plan 001).
- **CHANGELOG:**
  - Changed: fonts bundled; the app is truly offline [plan 014] [KI-034]
  - Fixed: subtitle and model recommendation [plan 014] [KI-023]
- **Verification:**
  - **New sandbox server:**
    - `GET /static/fonts/fonts.css` returned 200 `text/css`.
    - The 14 referenced woff2 files are exactly the files on disk; each returned 200 `font/woff2` with the `wOF2` signature.
    - `index.html` has two `<link>` tags: `fonts.css` and `style.css`.
  - **Browser pane, old (8011) vs new (8012):**

    | Check | Old | New |
    |---|---|---|
    | Requests outside `127.0.0.1` | `fonts.googleapis.com/css2?…` | none |
    | Font requests | Google | `fonts.css` + four latin woff2 files from `/static/fonts/` |
    | Loaded faces | Cinzel 600/700, Crimson Pro 400 + italic 400, JetBrains Mono 400/500 | the same six |
    | Subtitle | old "Shift+click" text | new text |

  - Screenshots show the same typefaces, and the new page's console was empty.
  - **Cleanup:** sandboxes and the temp `.claude/launch.json` removed, servers stopped. `git status --porcelain data/` empty.
- **Not verified:** a physically disconnected machine. The network log showing no external request stands in for it.
- **Follow-ups:** none. To update the fonts later, follow the `fonts.css` header.
