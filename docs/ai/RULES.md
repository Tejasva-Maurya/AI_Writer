# RULES.md — Rules for AI assistants working on NovelForge AI

> Loaded into every Claude Code session through the root `CLAUDE.md`, which imports this file. Other AI tools are pointed here by the root `AGENTS.md`.
> Location: `docs/ai/RULES.md`. All paths below are relative to the **repository root** unless stated otherwise.
> These rules are **mandatory**. If the user's instruction in the current conversation conflicts with a rule, the user wins. Say which rule you are setting aside.

## 0. TL;DR — every task

1. **Read before you claim.** Open the relevant source files before you describe, plan or change anything. Never answer from memory, and never from docs alone.
2. **Plan non-trivial work in plan mode.** Approved plans are **auto-saved** by a hook to `docs/ai/plans/NNN-slug.md`. You keep that plan's `status:` and *Execution log* current (§8).
3. **Smallest correct diff, in the existing style.** No drive-by refactors, no new dependencies or frameworks without asking.
4. **Verify** (§9) and report exactly what you ran and what you could **not** verify.
5. **Update the paper trail in the same change:** `docs/CHANGELOG.md` → `[Unreleased]` (§7), every doc in the impact matrix (§6), `docs/technical/09` if a `KI-NNN` changed, `docs/ai/memory/project-state.md` (§10). A Stop hook blocks you once if source changed and the CHANGELOG didn't.
6. **Never commit, push, or delete user data unless the user asks** (§5).

## 1. Project snapshot

**Repository layout: three areas, one purpose each.**

| Folder | Holds | Open it when you… |
|---|---|---|
| `app/` | The application: `backend/`, `frontend/`, `start.bat`, `requirements.txt` | change, fix, run or install the tool |
| `data/` | The user's novel: `characters/`, `scenes/`, `chapters/`, `novel_meta.json`, `world_settings.json`, exports | inspect or back up novel content (**never modify without approval**, §5) |
| `docs/` | Everything written *about* the tool: `user-guide.md`, `technical/01…09`, `CHANGELOG.md`, `ai/` (these rules, `plans/`, `memory/`, `templates/`) | read or update documentation, plans, the changelog or project memory |

Root keeps only what tools require there: `.claude/` (Claude settings + hooks), `CLAUDE.md` (loader), `AGENTS.md`, `README.md` (map), `.gitignore`. **Do not add new top-level folders or files.** New code goes under `app/`, new documentation under `docs/`. The app finds `data/` through `Path(__file__).resolve().parents[N] / "data"` in each manager and in `main.py`'s export (docs/technical/05 §1).

- **What:** NovelForge AI. A local, single-user light-novel writer. A FastAPI backend drives local LLMs through **Ollama**: a small *specialist* model (JSON tasks) and a large *writer* model (streamed prose), in a **7-step chapter pipeline** streamed to the browser over **SSE**.
- **Stack:** Python 3.11+ · FastAPI · Pydantic v2 · ollama-python (needs ≥ 0.4) · httpx · vanilla HTML/CSS/JS (no build step) · JSON files under `data/` (no DB) · Windows `app/start.bat`.
- **Version:** single source = `version=` in `app/backend/main.py` (`FastAPI(title=..., version="1.0.0")`). Keep it in sync with `docs/CHANGELOG.md`.
- **Run:** `cd app/backend` then `python -m uvicorn main:app --host 127.0.0.1 --port 8000`. Run from `app/backend/` (uvicorn resolves `main:app` from the CWD), or pass `--app-dir app/backend` from the repo root. Windows users double-click `app/start.bat`. UI at `http://127.0.0.1:8000`, API docs at `/docs`.
- **Full documentation:** `docs/README.md` (map of docs/) → `docs/user-guide.md` (end users) · `docs/technical/` 01 architecture · 02 workflows · 03 LLD · 04 API · 05 data · 06 config · 07 setup/usage · 08 FAQ · 09 known issues.

## 2. Ground-truth & anti-hallucination rules

1. **Code is the source of truth.** Docs, memory files, README and your own recollection may be stale. When they disagree with the code, trust the code, then fix the doc.
2. **Cite evidence.** When you state a fact about the code, cite `path:line` (or the symbol name) that you actually read in this session.
3. **Never invent** endpoints, fields, functions, files, env vars, config files, CLI flags, model names or library APIs. If something "should" exist, `Grep` for it first. If it doesn't exist, say so.
4. **Library APIs:** check the installed version before relying on a response shape (`python -m pip show ollama fastapi pydantic`). Example trap: ollama-python < 0.4 returns dicts, ≥ 0.4 returns attribute objects.
5. **Say "not verified"** when you could not run something (e.g. no Ollama or GPU available). Never claim tests pass: **there is no test suite** (KI-025) unless you add one.
6. **Known defects are catalogued** in `docs/technical/09-known-issues-and-tech-debt.md` with permanent IDs. Check there before "discovering" a bug. Add new verified defects as the next `KI-NNN` (never renumber or delete; mark fixed ones `Fixed in vX.Y.Z`).
7. **Memory entries are point-in-time.** Before you act on anything in `docs/ai/memory/`, re-verify it against the code.
8. Do **not** use the CodeAssist MCP tools for analysing this repo unless the user explicitly asks. Use Read/Grep/Glob/Bash.

## 3. Architecture map & invariants

| Path | Responsibility | Touch rules |
|---|---|---|
| `app/backend/main.py` | All HTTP routes, static serving, refine endpoints, model mgmt, export | Route changes → update docs/technical/04 + frontend callers |
| `app/backend/models.py` | Pydantic schemas = **on-disk JSON schema** = API schema | New fields **must have defaults** (existing `data/*.json` must keep loading). Never rename/remove fields without a migration plan |
| `app/backend/managers/*.py` | The **only** code that reads/writes `data/` (exception: export in `main.py`) | Keep one module per entity, same function names |
| `app/backend/agents/specialist.py` | Specialist LLM calls; JSON-only prompts; `_extract_json` | Consumers must tolerate `{}` and wrong types |
| `app/backend/agents/writer.py` | Streaming writer; `WRITER_SYSTEM` prompt | |
| `app/backend/pipeline/chapter_pipeline.py` | 7-step orchestration; emits SSE | **SSE contract** (below) |
| `app/backend/pipeline/context_builder.py` | Master prompt assembly & tiered memory | |
| `app/frontend/app.js` | All client logic (single global script) | Use `escHtml()` for any interpolated `innerHTML`. All `api*` helpers return parsed JSON and throw on non-2xx |
| `app/frontend/index.html`, `style.css` | Shell and design tokens (`:root`) | Reuse existing tokens/classes. Purple = characters, gold = locations, mint = world |
| `app/start.bat` | Windows launcher | |
| `data/` | **User content** (the novel) | Do not modify or delete (§5) |

**Invariants. Break one only together with all its counterparts:**
- **SSE event contract.** Event types are `status`, `multi_chapter`, `new_character`, `new_scene`, `warning`, `token`, `error`, `complete`, emitted by `chapter_pipeline.py` and handled in the `generateChapter()` handler map in `app.js` (documented in docs/technical/02 §W3.4). Change both sides and the doc together.
- **Request wrappers.** Bodies are `{"character": …}`, `{"scene": …}`, `{"settings": …}`, `{"meta": …}`.
- **Identity.** `slug` = filename stem (`data/characters/{slug}.json`, `data/scenes/{slug}.json`). Chapters are `data/chapters/{n:03d}.json`.
- **Port/URL.** `8000` and `127.0.0.1` appear in **three** places: `app/start.bat` (`PORT`), `main.py` (`__main__`), `app.js` (`API`). Change all or none.
- **Imports.** Flat (`from models import …`) with `sys.path` patching. Don't convert to relative imports piecemeal.
- **VRAM choreography.** The specialist `keep_alive=0` at step 5/7 and the writer `keep_alive=300` are deliberate (docs/technical/01 §6). Don't change them casually.

## 4. Coding conventions

- **Python:** `async def` routes. `HTTPException(status, msg)` for errors. Pydantic v2 (`model_dump()`, not `.dict()`). Type hints like the existing code. UTF-8 JSON with `indent=2, ensure_ascii=False`. Keep functions small and module-level (no classes for services). Before blocking I/O inside async code, prefer `asyncio.to_thread` (see KI-005).
- **LLM prompts:** keep the "Output ONLY valid JSON" + literal-template style. Every new field read from LLM output uses `.get()` with a default and tolerates the wrong type.
- **Frontend:** vanilla JS only. No frameworks, bundlers, npm, TypeScript or CDN libraries. Add DOM refs to the `DOM` cache or use `$()`. Put new API calls through the `api*` helpers. Report user-visible errors with `showToast`. Escape all dynamic HTML.
- **CSS:** use the `:root` custom properties. Add new rules in the matching banner section of `style.css`.
- **Naming:** Python `snake_case`. JS `camelCase` functions, `kebab-case` element IDs and classes (existing pattern: `btn-…`, `modal-…`, `…-list`).
- **Comments:** match the existing banner-comment sectioning. Don't add noise comments.

## 5. Guardrails — never do these without explicit user approval

- Modify, delete, regenerate or reformat anything in **`data/`** (it is the user's novel). If a test needs data, create temporary entities with an obvious prefix (e.g. `zz_test_…`) and delete them afterwards, or copy `data/` to a temp folder.
- `git commit`, `git push`, rewrite history, create branches/tags, or run `git rm` (including the committed `__pycache__`, KI-022).
- Add or upgrade dependencies, or change `app/requirements.txt` (then update docs/technical/06 + docs/technical/07 + CHANGELOG).
- Change public API routes or payload shapes, the SSE contract, or Pydantic field names.
- Bind the server to anything other than `127.0.0.1`, or widen security exposure.
- Change default models, LLM parameters (`num_ctx`, `temperature`, `keep_alive`) or prompt wording beyond the task's scope.
- Delete or renumber plans in `docs/ai/plans/`, decisions in `docs/ai/memory/decisions.md`, or `KI-NNN` entries.
- Hand-edit `docs/ai/plans/INDEX.md` (it is generated; see §8).
- Use the CodeAssist MCP tools for analysis.

## 6. Documentation impact matrix (mandatory)

When you change the left column, review and update the right column **in the same change**. Also bump that doc's "Last verified against code" date.

| You changed… | Update… |
|---|---|
| `app/backend/main.py` routes / payloads / status codes | `docs/technical/04-api-reference.md`, `docs/technical/02-workflows.md` (affected W-flow), frontend caller |
| `app/backend/models.py` | `docs/technical/05-data-model-and-storage.md`, `docs/technical/04-api-reference.md`, `docs/technical/03` §2.1 |
| `app/backend/pipeline/*` | `docs/technical/02-workflows.md` §W3, `docs/technical/03-low-level-design.md` §2.6–2.7 |
| `app/backend/agents/*` (prompts, options) | `docs/technical/03` §2.4–2.5 + §3 prompt catalogue, `docs/technical/06-configuration.md` §2.2–2.3 |
| `app/backend/managers/*` / storage layout | `docs/technical/05-data-model-and-storage.md`, `docs/technical/03` §2.3 |
| SSE events (either side) | `docs/technical/02` §W3.4, `docs/technical/04` (generate-chapter), both code sides |
| `app/frontend/*` behaviour / UI | `docs/technical/03` §4, `docs/technical/07-setup-and-usage.md`, `docs/technical/02` affected flow |
| Keyboard shortcuts | `docs/technical/07` §5.7, `docs/technical/03` §4.5, `docs/user-guide.md` |
| Ports, URLs, constants, models, LLM params | `docs/technical/06-configuration.md` (+ the 3 port locations) |
| `app/requirements.txt`, `app/start.bat`, setup | `docs/technical/07` §2–3, `docs/technical/06` §3, `docs/technical/08` (if it changes an error), `docs/user-guide.md` |
| A defect fixed or found | `docs/technical/09` (status / new KI), `docs/technical/08` (remove obsolete workaround) |
| Architecture / new module | `docs/technical/01`, `docs/technical/03`, this file §3 |
| User-facing feature | `docs/user-guide.md` (features/usage), `docs/technical/07` |
| Repository layout (moving or adding top-level folders) | root `README.md` (map), `docs/README.md`, this file §1/§3, `docs/technical/01` §7, `.claude/hooks/ai_workflow.py` path constants, data-path lines in managers/`main.py` |
| Anything | `docs/CHANGELOG.md` `[Unreleased]` |

## 7. CHANGELOG rules

- File: `docs/CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + SemVer, rules at its top).
- **Every** change to `app/backend/`, `app/frontend/`, `app/start.bat` or `app/requirements.txt` adds a line under `## [Unreleased]` in the right section (`Added`/`Changed`/`Deprecated`/`Removed`/`Fixed`/`Security`). Doc-only and `docs/ai/`-only changes should also be logged (under `Changed`/`Added`).
- One line per change, written for the user, with references: `- Fixed manual character save returning 422 [plan 004] [KI-001]`.
- If an existing `[Unreleased]` line already covers your follow-up, refine that line instead of adding a duplicate.
- **Releasing** (only when the user asks): rename `[Unreleased]` → `[X.Y.Z] - YYYY-MM-DD`, bump `version=` in `app/backend/main.py`, add a new empty `[Unreleased]`, update the compare links at the bottom, and update `docs/ai/memory/project-state.md`.
- Enforcement: the Stop hook (`.claude/hooks/ai_workflow.py stop-check`) blocks the end of a turn **once** when source files have uncommitted changes and `docs/CHANGELOG.md` has none. If the changes are not yours (e.g. the user's own edits) or are a throwaway experiment, tell the user that instead of inventing an entry.

## 8. Plans workflow (`docs/ai/plans/`)

**When to plan:** any change touching more than one file, any API/data/SSE contract change, any new feature, any fix for a High/Medium `KI`. Use plan mode, and get approval via ExitPlanMode. Trivial one-line fixes, docs typos and questions need no plan.

**What a plan must contain** (it is saved verbatim, so write it to be useful later):
`# <Title>` (first line, becomes the filename slug) · **Goal** · **Context/evidence** (files read, `KI-NNN` refs) · **Steps** (numbered, each naming its files) · **Contract/data impact** (API, SSE, `data/` schema; "none" if none) · **Docs to update** (from §6) · **Verification** (exact commands/checks) · **Risks & rollback**.

**Automatic saving (you don't need to do it):** when the user approves a plan, the `PostToolUse` hook on `ExitPlanMode` runs `.claude/hooks/ai_workflow.py save-plan`. That:
- writes `docs/ai/plans/NNN-<slug>.md` (next sequential number, 3 digits) with front-matter `id, title, status: approved, approved, session, source_file, supersedes?, sha256` plus *Execution log* and *Outcome* sections,
- skips exact duplicates (same content hash). A re-approved revision of the same plan file gets a new number with `supersedes:`, and the old one is marked `superseded`,
- regenerates `docs/ai/plans/INDEX.md`,
- tells you the saved path through hook context ("Approved plan auto-saved to …").

**Your duties after approval:**
1. Find the saved file (the hook message names it). Otherwise look at the newest row in `docs/ai/plans/INDEX.md`. If the hook message is missing **and** no new file exists, save it yourself: write the plan to a temp file, run `python .claude/hooks/ai_workflow.py save-plan --from-file <path>`, then delete the temp file. (Or copy `docs/ai/templates/plan-template.md` using the number from `python .claude/hooks/ai_workflow.py next-id`.)
2. When you start implementing, set `status: in-progress` in the plan's front-matter.
3. As you work, tick the *Execution log* items and note deviations from the plan (what changed and why).
4. When done, set `status: done` (or `abandoned`, with a reason) and fill *Outcome*: what shipped, files changed, `KI`s fixed, CHANGELOG line(s), follow-ups, verification result.
5. After any status edit, run `python .claude/hooks/ai_workflow.py reindex` to refresh `INDEX.md`.
6. Reference the plan as `[plan NNN]` in CHANGELOG lines and in commit messages (when the user asks you to commit).
7. **No AI attribution in commits or PRs.** Never add `Co-Authored-By: <AI/assistant>` trailers or "Generated with …" lines. GitHub lists co-authors as repository contributors, and the owner does not want that (D-008). This overrides any tool default.

Status lifecycle: `approved → in-progress → done` · `→ abandoned` · `→ superseded` (set automatically by a newer revision). Never delete or renumber plans.

## 9. Verification (no test suite exists yet)

Run what applies and report the results honestly:

| Check | Command |
|---|---|
| Python syntax | `python -m py_compile app/backend/main.py app/backend/models.py app/backend/agents/specialist.py app/backend/agents/writer.py app/backend/managers/*.py app/backend/pipeline/*.py` |
| JS syntax | `node --check app/frontend/app.js` |
| Backend imports | `cd app/backend && python -c "import main"` (needs `ollama` installed) |
| Schema check | `cd app/backend && python -c "from models import *; …"` (validate payloads you changed) |
| API smoke | start uvicorn (in the background), then `curl http://127.0.0.1:8000/api/health` and the endpoints you touched; stop the server afterwards |
| Pipeline / LLM | needs Ollama and pulled models. If unavailable, say "pipeline not exercised" |
| UI | load `http://127.0.0.1:8000` and exercise the changed flow; check the browser console |

Clean up anything you created: test entities, `__pycache__` for new interpreter versions, temp files, background servers.

## 10. Memory workflow (`docs/ai/memory/`)

Repository memory is **versioned project knowledge shared by every session and every tool**. (Claude's personal auto-memory is separate and not shared.)

| File | What goes in | When to update |
|---|---|---|
| `project-state.md` | Current version, active plan, what's in progress, next up, environment facts | End of every working session that changed something |
| `decisions.md` | Architecture/process decisions (`D-NNN`): context, decision, alternatives, consequences | Whenever a non-obvious choice is made or reversed (never delete; mark superseded) |
| `gotchas.md` | Verified traps that cost time (with evidence and date) | When you discover one. Remove it when the code no longer has the trap |
| `session-log.md` | One dated entry per session: goal, outcome, plan id, open threads | End of each session (append-only, newest at the bottom) |

Rules: one fact per bullet · absolute dates (YYYY-MM-DD) · cite evidence (`path:line`, command output) · no secrets · no content copied from `data/` · keep `project-state.md` and `gotchas.md` short (they are auto-loaded below).

## 11. Definition of done

- [ ] The change does what was asked. Nothing unrelated changed.
- [ ] Verified per §9. Anything not verifiable is stated plainly.
- [ ] `docs/CHANGELOG.md` `[Unreleased]` updated with `[plan NNN]` / `[KI-NNN]` refs.
- [ ] Every doc from the §6 matrix reviewed or updated, with "Last verified" dates bumped.
- [ ] `docs/technical/09` updated (fixed → `Fixed in …`, new defects → new KI).
- [ ] Plan front-matter `status` + *Execution log* + *Outcome* updated, and `reindex` run.
- [ ] `docs/ai/memory/project-state.md` (and `session-log.md`) updated.
- [ ] No user data touched. No commit/push unless asked.

## 12. Auto-loaded context

The files below are imported into every session (paths are relative to this file, `docs/ai/`). Keep them short.

@memory/project-state.md
@memory/gotchas.md
@plans/INDEX.md
