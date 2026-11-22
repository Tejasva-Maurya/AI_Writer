# `docs/ai/` — AI development workspace

This folder is the **versioned memory and planning record** of AI-assisted development on NovelForge AI. It is committed with the code, so every session, tool and human reviewer sees the same history. Commands below are run from the **repository root**.

```
docs/ai/
├── README.md              ← you are here
├── RULES.md               ← canonical rules for AI assistants (root CLAUDE.md imports it; root AGENTS.md points to it)
├── plans/
│   ├── INDEX.md           ← AUTO-GENERATED table of all plans (do not hand-edit)
│   └── NNN-<slug>.md      ← one file per approved plan, numbered 001, 002, … (never renumbered)
├── memory/
│   ├── project-state.md   ← where the project is right now (auto-loaded into every Claude session)
│   ├── gotchas.md         ← verified traps (auto-loaded)
│   ├── decisions.md       ← decision log D-001, D-002, … (ADR-lite)
│   └── session-log.md     ← one dated entry per working session (append-only)
└── templates/
    ├── plan-template.md      ← for manual plan saves (non-Claude tools / hook fallback)
    └── decision-template.md
```

## How plans get saved, without anyone asking

1. You ask Claude Code for a non-trivial change. Per `RULES.md` §8 it works in **plan mode** and presents a plan.
2. You click **approve**.
3. A Claude Code **PostToolUse hook on `ExitPlanMode`** (configured in `.claude/settings.json`) runs `.claude/hooks/ai_workflow.py save-plan`. It:
   - takes the approved plan text (`tool_response.plan`) and its source file path,
   - assigns the **next sequential number** and writes `docs/ai/plans/NNN-<slug-from-title>.md` with front-matter (`id`, `title`, `status: approved`, `approved` timestamp, `session`, `source_file`, `supersedes`, `sha256`),
   - appends an *Execution log* and an *Outcome* section for Claude to fill in,
   - skips duplicates. A revised re-approval of the same plan gets a new number and marks the older one `superseded`,
   - regenerates `plans/INDEX.md`,
   - tells Claude the saved path, so it can keep the status current.
4. While implementing, Claude moves `status:` through `in-progress → done` (or `abandoned`), fills the *Outcome*, and runs `reindex`.

Errors in the hook never block your session. They are written to `.claude/hooks/hook-errors.log` (git-ignored).

A second hook (**Stop**) blocks Claude once from finishing a turn when files under `app/` changed but `docs/CHANGELOG.md` did not.

**Proven in practice:** plan 002 was saved by this hook automatically when the user approved it (2026-11-22).

### Why numbered files plus a generated index (instead of dates or a single file)?
- `NNN-` prefixes sort chronologically in every file browser and stay stable when titles change.
- One file per plan keeps diffs small and lets a plan carry its own execution log and outcome.
- Status lives in each plan's front-matter (single source of truth), and `INDEX.md` is rebuilt from it, so the overview can't drift.
- `supersedes:` links revisions together without renumbering anything.
- CHANGELOG lines and commits cite `[plan NNN]`, which connects *intent → change → release*.

## Commands

```bash
python .claude/hooks/ai_workflow.py reindex                      # rebuild plans/INDEX.md after editing a plan's status
python .claude/hooks/ai_workflow.py next-id                      # print the next free plan number
python .claude/hooks/ai_workflow.py save-plan --from-file x.md   # manual save (other AI tools, or hook fallback)
```
(On Windows, `py -3` works in place of `python`.)

## Memory rules (summary of `RULES.md` §10)
- One fact per bullet, absolute dates, cite evidence, no secrets, never copy novel content from `data/`.
- `project-state.md`, `gotchas.md` and `plans/INDEX.md` are imported into every Claude session (root `CLAUDE.md` → `RULES.md` → these files), so keep them short.
- Decisions and plans are never deleted. Mark them `superseded`/`abandoned` instead.
