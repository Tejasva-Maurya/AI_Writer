# AGENTS.md

This repository's rules for AI coding assistants live in **[docs/ai/RULES.md](docs/ai/RULES.md)**. That file is canonical for every tool (Claude Code loads it through `CLAUDE.md`; Codex, Cursor, Copilot, Gemini and others should read it in full before making changes).

**Repository layout:** `app/` = the application (backend, frontend, launcher, requirements) · `data/` = the user's novel · `docs/` = documentation, changelog, AI rules, plans and memory (`.github/` holds only the CI workflow). Don't create new top-level folders.

Minimum you must follow even if your tool cannot load the rules automatically:

1. **Code is the source of truth.** Read the files before you describe or change them, and cite `path:line`. Never invent APIs, fields, files or config.
2. **Docs:** `docs/README.md` is the map. Known defects have permanent IDs in `docs/technical/09-known-issues-and-tech-debt.md` (`KI-NNN`).
3. **Every change under `app/`** adds a line under `## [Unreleased]` in `docs/CHANGELOG.md` and updates the docs named in the impact matrix (RULES.md §6).
4. **Plans** live in `docs/ai/plans/NNN-slug.md` (sequential and never renumbered). Claude Code saves approved plans automatically via a hook. Other tools must save their plan manually: `python .claude/hooks/ai_workflow.py save-plan --from-file <plan.md>`, then keep its `status:` current and run `python .claude/hooks/ai_workflow.py reindex`.
5. **Project memory** lives in `docs/ai/memory/` (state, decisions, gotchas, session log). Update it at the end of a working session.
6. **Verify** with `py -m pytest app/tests` and `py -m ruff check app` (dev tools: `app/requirements-dev.txt`).
7. **Never** modify `data/` (the user's novel), commit/push, or add dependencies without the user's explicit approval.
