# Session log

> Append-only. One entry per working session, newest at the bottom. 3–6 lines each: date · tool/model · goal · outcome · plan · open threads.

---

### 2026-11-22 — Claude Code (Opus 5.5) — baseline analysis & AI workflow
- **Goal:** Analyse the repo; produce detailed current-state docs, a CHANGELOG, AI rules/guardrails, and a self-maintaining plans/memory system.
- **Outcome:** Read every source file. Verified KI-001 (422 on manual save), KI-003 (backend import fails without `ollama`) and KI-016 (int age / unknown type rejected) by execution. Wrote `docs/01–09` + index, `CHANGELOG.md`, `CLAUDE.md`, `AGENTS.md`, `.ai/` workspace, and `.claude` hooks (auto-save approved plans; Stop-hook CHANGELOG guard). Fixed the README architecture section. An independent agent fact-checked docs 02/03/04/06/09 against the code: all constants, routes and KIs were confirmed, and 7 minor wording fixes were applied. That check also uncovered the refine-merge unvalidated `setattr` bug (added to KI-016, verified).
- **Plan:** 001 (retroactive; this session did not use plan mode).
- **Open threads:** The hooks were tested with synthetic payloads only. First real plan approval should be checked (does `.ai/plans/002-*.md` appear?). The pipeline was not exercised (no Ollama on this machine).
  - _(Resolved in the next entry: yes, the hook saved plan 002 live.)_ Paths above are from before plan 002's reorganisation.

### 2026-11-22 — Claude Code (Opus 5.5) — repository reorganisation (plan 002)
- **Goal:** Before committing, separate the application, the novel data and the supporting documents so it's obvious which folder to open for which work.
- **Outcome:** Used plan mode. On approval, the ExitPlanMode hook auto-saved plan 002 (first live proof of the hook). Moved code to `app/`, docs to `docs/technical/`, `.ai/` to `docs/ai/`, CHANGELOG to `docs/`, old README to `docs/user-guide.md`, CLAUDE.md content to `docs/ai/RULES.md` (root CLAUDE.md is now a loader). Fixed six data-path lines (no line shifts). Updated the hook constants, every doc reference and the anchors. Wrote a new root README map and decision D-007. Verified: compile, path resolution, TestClient smoke against the real `data/` (ollama stubbed), hooks in a sandbox, link checker (26 files, 0 problems).
- **Plan:** 002 (done).
- **Open threads:** Committed to `main` at the user's request (not pushed). `git ls-files | grep pyc` should be empty after the commit (KI-022). `app/start.bat` not executed (static review only).
