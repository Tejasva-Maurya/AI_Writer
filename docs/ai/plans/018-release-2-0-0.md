---
id: 018
title: "Release 2.0.0"
status: done
approved: 2026-11-24T15:35:28+05:30
session: 8e82db1f-b2c4-4901-8528-5594118a09fb
source_file: "C:\\Users\\2466921\\.claude\\plans\\drifting-questing-parnas.md"
sha256: f8a21a79fa141aac3da479901642d6edf07b483cc23a38e7f0907e34ea6190fa
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Release 2.0.0

## Context
The user asked for a release. All 40 catalogued known issues are fixed (plans 001–017), everything is committed and pushed (`0ca15eb`), and CI is green.

**Facts read this session:**
- **Release rules:** `docs/CHANGELOG.md` (lines 5–15) and RULES §7: rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`, bump `version=` in `app/backend/main.py`, add a fresh empty `[Unreleased]`, update the compare links, and update `project-state.md`.
  - The CHANGELOG defines **MAJOR** as "incompatible change to the data files in `data/` or to the HTTP API contract".
  - The comment above the compare links says: "On release, add a tag … and point the links at tags."
- **Version:** `app/backend/main.py:39` has `version="1.0.0"`. It is also quoted in `docs/technical/03` §2.2 (line 53) and RULES §1 (line 30). No test, frontend file or launcher contains the version.
- **Git state:** no tags exist locally or on `origin`. The 1.0.0 commit `dead3e3` (2026-07-13) is an ancestor of `main`. The current links are `[Unreleased]: compare/dead3e3...HEAD` and `[1.0.0]: compare/0f22226...dead3e3`.
- **"Unreleased" in the docs:**
  - **doc 09:** 123 mentions, nearly all `Fixed in Unreleased [plan NNN]`. Its header (line 5) prescribes renaming them to `Fixed in vX.Y.Z` at release.
  - **doc 08:** 5 `fixed in [Unreleased]` notes.
  - **docs 01–08:** a header saying `Applies to: v1.0.0 + [Unreleased]`.
  - **Process text** (RULES, AGENTS, plan template) refers to `[Unreleased]` as a concept and stays.
- **Pushing:** `git push` is blocked by the proxy. The github-push script pushes over REST with `$GH_PUSH_TOKEN` (`Tejasva-Maurya`, can push). Plain `urllib` calls to the API work, so tags and a release can be created the same way.

**User decisions (asked this session):**
- **Version 2.0.0**, because three HTTP API behaviours changed since 1.0.0:
  - create returns 409 instead of overwriting (plan 004)
  - no CORS, and a foreign `Host` gets 400 (plan 007)
  - generate returns 409 while a generation runs (plan 010)
- **Tags and a GitHub Release:** annotated tags `v1.0.0` (on `dead3e3`) and `v2.0.0`, plus a GitHub Release page for 2.0.0.

## Steps
1. **`docs/CHANGELOG.md`:**
   - Insert a fresh, empty `## [Unreleased]`. Rename the current section to `## [2.0.0] - 2026-11-24`.
   - Open 2.0.0 with a short **Upgrading from 1.0.0** list:
     - launch with `app/start.bat` (plan 002)
     - the API changes: 409 on create, server-derived slugs, same-origin only, 409 while generating, the new cancel endpoint
     - `data/` is no longer in git, so back it up
     - 1.0.0 data files still load
   - End the section with `### Known issues at release`: none open (doc 09).
   - **Links:** `[Unreleased]: compare/v2.0.0...HEAD`, `[2.0.0]: compare/v1.0.0...v2.0.0`, `[1.0.0]: releases/tag/v1.0.0`. Reword the link comment to describe the tag-based links.
2. **Version:** `app/backend/main.py:39` → `version="2.0.0"`. Same in `docs/technical/03` (§2.2 row) and RULES §1.
3. **doc 09:**
   - `Fixed in Unreleased` → `Fixed in v2.0.0` in every row, status line and heading.
   - Also: "40 fixed in [Unreleased]" → "40 fixed in v2.0.0", and "corrected in [Unreleased]" → "corrected in v2.0.0".
   - **Line 5** (the rule that prescribes the rename) stays as it is.
   - Line 4: "through plan 018 (release 2.0.0)".
4. **Docs 01–08 headers:** `Applies to: v1.0.0 + [Unreleased]` → `Applies to: v2.0.0 + [Unreleased]`.
   - Doc 01 keeps its baseline as `(first documented at v1.0.0, commit dead3e3)`.
   - "Last verified" dates stay, since no behaviour changed.
   - Doc 08's five `fixed in [Unreleased]` → `fixed in v2.0.0`.
   - Historical "in v1.0.0 …" sentences stay.
5. **Memory:**
   - **`project-state.md`:** rewrite the Version section. Released **2.0.0** (plans 001–017, see CHANGELOG); collapse the per-plan `[Unreleased]` lines to stay under ~40 lines; `[Unreleased]` is empty; no open KIs.
   - **`decisions.md`:** D-015 (2.0.0 by the CHANGELOG's MAJOR rule; tags and Releases via the REST API; `v1.0.0` retro-tagged on `dead3e3`).
   - **`session-log.md`:** a new entry.
   - **Plan 018:** status, execution log, outcome, then `reindex`.
6. **Stop and wait.** Commit only when the user says so ("Release 2.0.0"; no AI trailer, personal identity).
7. **After the user says "Push it":**
   - **Push** with the github-push script (preflight, dry run, push), then a mixed reset to `origin/main`. The tree is checked against the remote first, and a mixed reset keeps uncommitted notes.
   - **Tag and release** with a temp Python script using `urllib` and `$GH_PUSH_TOKEN`, without printing the token:
     - annotated tag objects plus refs: `v1.0.0` → `dead3e3`, `v2.0.0` → the **remote** release commit (its SHA differs from the local one after an API push). Tagger: Tejasva_Maurya <mauryatejasva512004@gmail.com>.
     - a GitHub Release `NovelForge AI 2.0.0` on `v2.0.0`, marked latest. Its notes are the CHANGELOG 2.0.0 section, with relative doc links made absolute (`blob/v2.0.0/docs/...`).
   - **Finish:** `git fetch --tags`; record the release URL in memory (uncommitted, for the next commit).

## Contract / data impact
- **None in the code.** The only change is the version string, which shows in `/openapi.json` and `/docs`.
- **`data/`** is not touched.
- **Outward-facing:** tags and a Release page on GitHub, approved by the user, and created only after "Push it".

## Docs to update
`docs/CHANGELOG.md`, `docs/technical/01`–`09` (headers, doc 03 §2.2, doc 08 notes, doc 09 statuses), `docs/ai/RULES.md` §1, and the memory files (`project-state.md`, `decisions.md`, `session-log.md`).

## Verification
- **Version:** `cd app/backend && py -c "import main; print(main.app.version)"` prints `2.0.0` (works without ollama).
- **Suite:** `py -m pytest app/tests` and `py -m ruff check app` (tools in a temp `--target` folder); `node --check app/frontend/app.js`.
- **Greps:**
  - no `Fixed in Unreleased` in doc 09 except line 5
  - no `Applies to: v1.0.0`
  - exactly one `## [Unreleased]` and one `## [2.0.0] - 2026-11-24` in the CHANGELOG
  - the 2.0.0 section keeps every line that was under `[Unreleased]` (line count before and after)
- **`data/`:** a before/after listing (paths, sizes, mtimes) is identical.
- **After the push:**
  - `git ls-remote --tags origin`: `v1.0.0^{}` = `dead3e3`, `v2.0.0^{}` = the remote release commit
  - `GET /repos/.../releases/tags/v2.0.0` returns the release
  - the CI run for the release commit, if it has finished when checked (one look, no polling)

## Risks & rollback
- **Tags on the wrong commit:** deleting a tag ref via the API fixes it, and nothing depends on the tags yet. The script tags the SHA read back from `origin/main` after the push, not the local one.
- **Release notes rendering:** the Release can be edited on GitHub or via the API.
- **Rollback before the push:** revert the working-tree edits. **After:** delete the Release and the tags, and add a revert commit.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 018]`): released as `[2.0.0] - 2026-11-24`
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run
- [x] Commit, push, tags and GitHub Release (steps 6–7), each on the user's word

**Deviations from the plan:**
- **RULES §7 and the CHANGELOG rules** now include the tag step. The releasing bullet says to tag the **pushed** release commit and publish the Release through the REST API (D-015), so the next release repeats this.
- **Docs map fixed (`docs/README.md`).** It still linked `../data/`, which plan 017 removed from the repository; it now says the folder is local and git-ignored. Its header also names the current release.
- **Line endings.** Setting the plan's status with `sed -i` turned this file's CRLF into LF (a known gotcha); converted back.

## Outcome
- **Shipped (working tree):**
  - **`docs/CHANGELOG.md`:**
    - `[Unreleased]` became `[2.0.0] - 2026-11-24`, with every former line kept.
    - The section opens with "Upgrading from 1.0.0" (`app/start.bat`, the four API changes, `data/` out of git, 1.0.0 data still loads) and ends with "Known issues at release: none open".
    - A fresh, empty `[Unreleased]`.
    - Links: `[Unreleased]` `v2.0.0...HEAD`, `[2.0.0]` `v1.0.0...v2.0.0`, `[1.0.0]` `releases/tag/v1.0.0`.
  - **`app/backend/main.py:39`:** `version="2.0.0"`, also quoted in doc 03 §2.2 and RULES §1.
  - **Doc 09:** 120 `Fixed in Unreleased` → `Fixed in v2.0.0` (line 5's rule kept), "40 fixed in v2.0.0", "corrected in v2.0.0", "through plan 018 (release 2.0.0)".
  - **Docs 01–08:** headers say `Applies to: v2.0.0 + [Unreleased]` (doc 01 keeps "first documented at v1.0.0, commit `dead3e3`"), and doc 08's five notes say `fixed in v2.0.0`.
  - **Memory:** D-015, session-log entry, and project-state condensed from 49 to 34 lines.
- **Files changed:**
  - **Code:** `app/backend/main.py`.
  - **Docs:** `docs/CHANGELOG.md`, `docs/README.md`, `docs/ai/RULES.md`, `docs/technical/01`–`09`.
  - **Memory:** `docs/ai/memory/decisions.md`, `project-state.md`, `session-log.md`.
  - **Plans:** this plan, plus plan 017's CI note from the previous push.
- **KIs:** none changed (all 40 fixed, none open).
- **Verification:**
  - `py -c "import main; print(main.app.version)"` → `2.0.0`.
  - `py -m pytest app/tests` → 71 passed; `py -m ruff check app` → all checks passed (tools in a temp `--target` folder); `node --check app/frontend/app.js` OK.
  - **Greps:**
    - doc 09 has one `Fixed in Unreleased` (line 5, the rule)
    - no `Applies to: v1.0.0` left
    - one `## [Unreleased]`, and `## [2.0.0] - 2026-11-24` at line 20
    - no `version="1.0.0"` in `app/`, RULES or the technical docs
  - The old `[Unreleased]` body against the new 2.0.0 body: only additions.
  - The `data/` listing (5 files: paths, sizes, mtimes) was identical before and after.
  - **Release (2026-11-24, on the user's word):**
    - **Commit and push:** committed as `8913a7b` and pushed with the github-push script; GitHub has `03312e5` with the identical tree (`bb9ac06`). Local `main` was realigned with a mixed reset.
    - **Tags:** annotated `v1.0.0` → `dead3e3` and `v2.0.0` → `03312e5`, tagger Tejasva_Maurya (`git ls-remote --tags` confirms both).
    - **Release:** "NovelForge AI 2.0.0", latest, not a draft. Its notes are the 98-line CHANGELOG section with absolute doc links: https://github.com/Tejasva-Maurya/AI_Writer/releases/tag/v2.0.0
    - **CI:** green on all 4 jobs for `main` (https://github.com/Tejasva-Maurya/AI_Writer/actions/runs/45373445469) and for the `v2.0.0` tag (https://github.com/Tejasva-Maurya/AI_Writer/actions/runs/45373845132).
- **Follow-ups:** none. New work goes under `[Unreleased]`, and new defects start at KI-041.
