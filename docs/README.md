# NovelForge AI — Documentation map

Everything written **about** the tool lives in this `docs/` folder. The application itself is in [`../app/`](../app/), and the novel data in [`../data/`](../data/).
**Baseline:** v1.0.0 (git `dead3e3`), documented 2026-11-22 from a full read of the source code.

```
docs/
├── README.md          ← you are here (map)
├── user-guide.md      end-user guide: setup, models, usage, shortcuts, troubleshooting
├── CHANGELOG.md       version history (Keep a Changelog + SemVer)
├── technical/         how the tool works, for developers (01…09 below)
└── ai/                AI-assisted development workspace
    ├── README.md      how plans/memory/hooks work
    ├── RULES.md       canonical rules for AI coding assistants (loaded via root CLAUDE.md)
    ├── plans/         approved plans 001, 002, … + auto-generated INDEX.md
    ├── memory/        project-state, decisions (D-NNN), gotchas, session-log
    └── templates/     plan and decision templates
```

## Which document do I need?

| I want to… | Open |
|---|---|
| install and use the app | [user-guide.md](user-guide.md), then [technical/07 Setup & Usage](technical/07-setup-and-usage.md) |
| fix an error | [technical/08 FAQ & Troubleshooting](technical/08-faq-and-troubleshooting.md) |
| know what's broken before relying on it | [technical/09 Known Issues](technical/09-known-issues-and-tech-debt.md) |
| see what changed between versions | [CHANGELOG.md](CHANGELOG.md) |
| see what's being worked on / was planned | [ai/plans/INDEX.md](ai/plans/INDEX.md) and [ai/memory/project-state.md](ai/memory/project-state.md) |
| understand why something was designed this way | [ai/memory/decisions.md](ai/memory/decisions.md) |
| give rules to an AI assistant | [ai/RULES.md](ai/RULES.md) |

## Technical documents (`technical/`)

| # | Document | Read it when you want to… |
|---|---|---|
| 01 | [Overview & Architecture](technical/01-overview-and-architecture.md) | understand what the tool is, the tech stack, components, dependency rules, the dual-model VRAM strategy, repository layout and runtime model |
| 02 | [Workflows](technical/02-workflows.md) | follow any end-to-end flow (launch, boot, the 7-step chapter pipeline, refine builders, CRUD, settings, models, history, export), with sequence diagrams and the **SSE event contract** |
| 03 | [Low-Level Design](technical/03-low-level-design.md) | see every module, class and function, the LLM prompt catalogue, the master-prompt format, frontend state/functions/bindings, CSS tokens, error handling and dead code |
| 04 | [API Reference](technical/04-api-reference.md) | call or change an HTTP endpoint (request/response shapes, errors, side effects, curl examples) |
| 05 | [Data Model & Storage](technical/05-data-model-and-storage.md) | understand the JSON files in `data/`, every field (who writes and reads it), relationships, and how data becomes LLM context |
| 06 | [Configuration](technical/06-configuration.md) | change models, ports, URLs, LLM parameters, prompt knobs or dependencies, and find exactly where each one lives |
| 07 | [Setup & Usage](technical/07-setup-and-usage.md) | install, run, and use the app; keyboard shortcuts; backup/reset; developer quick reference |
| 08 | [FAQ & Troubleshooting](technical/08-faq-and-troubleshooting.md) | fix an error or answer a common question |
| 09 | [Known Issues & Tech Debt](technical/09-known-issues-and-tech-debt.md) | see every verified defect and risk (permanent IDs `KI-NNN`) before planning work |

Reading paths:
- **New developer:** 01 → 02 (W3) → 03 → 09
- **Fixing a bug:** 09 (find the KI) → 03 (module) → 02 (flow) → 04/05 (contracts)
- **End user:** user-guide → technical/07 → technical/08
- **AI assistant:** `ai/RULES.md` (auto-loaded via root `CLAUDE.md`) → the doc named in its impact matrix

## Conventions

- `path:line` references are repo-relative (e.g. `app/backend/main.py:29`, or the short form `main.py:29`) and point at the code version named in each doc header. Line numbers drift; search by symbol name if they don't match.
- ⚠ marks behaviour that differs from what a user would expect, usually with a `KI-NNN` link. "Verified ✔" means the claim was checked by execution.
- Mermaid diagrams render on GitHub/GitLab and in VS Code (with a Mermaid extension).

## Keeping the docs true

Docs are part of the change. Every change under `app/` must update the affected document(s) and [CHANGELOG.md](CHANGELOG.md). The mapping from files to docs is the **doc-impact matrix** in [ai/RULES.md](ai/RULES.md#6-documentation-impact-matrix-mandatory). When you update a document, also update its "Last verified against code" date.
