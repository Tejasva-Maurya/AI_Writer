---
id: NNN
title: "Short imperative title"
status: approved
approved: YYYY-MM-DDTHH:MM:SS+05:30
session: manual
source_file: manual
sha256: ""
---

> Plan file format used by `.claude/hooks/ai_workflow.py`. Prefer `python .claude/hooks/ai_workflow.py save-plan --from-file <plan.md>`, which fills the front-matter and the number for you.
> If you copy this template by hand: get the number from `python .claude/hooks/ai_workflow.py next-id`, name the file `NNN-<slug>.md`, then run `reindex`.
> Status lifecycle: approved → in-progress → done | abandoned | superseded

# Short imperative title

## Goal
What the user asked for and what "done" means.

## Context / evidence
- Files read (`path:line`), relevant `KI-NNN`, constraints from docs/ai/RULES.md.

## Steps
1. … (files: `app/backend/...`)
2. …

## Contract / data impact
API routes · SSE events · `data/` JSON schema · config. Write "none" if none.

## Docs to update (CLAUDE.md §6)
- `docs/…`
- `docs/CHANGELOG.md` → [Unreleased] / Added|Changed|Fixed…

## Verification
Exact commands and manual checks (see docs/ai/RULES.md §9). Say what cannot be verified.

## Risks & rollback
…

---

## Execution log
<!-- Update as you work: set front-matter status to in-progress when starting; note deviations from the plan. -->
- [ ] Implementation started (status → in-progress)
- [ ] Code changes complete
- [ ] Verified (CLAUDE.md §9)
- [ ] docs/CHANGELOG.md [Unreleased] updated (cite this plan)
- [ ] Docs updated per docs/ai/RULES.md §6 (+ docs/technical/09 KI status)
- [ ] docs/ai/memory/project-state.md updated
- [ ] Status → done (or abandoned with reason) and `reindex` run

## Outcome
_Fill in when finished: what shipped, files changed, KIs fixed, CHANGELOG line(s), verification results, follow-ups._
