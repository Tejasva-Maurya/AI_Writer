---
id: 005
title: "Fix startup without ollama, dependency pins, and event-loop blocking (KI-003, KI-004, KI-005)"
status: done
approved: 2026-11-22T23:15:30+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 6f42b5a6e2bef198cffff2468b519d13245e3b5eac0e9da0ef7cf30f77031b91
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Fix startup without ollama, dependency pins, and event-loop blocking (KI-003, KI-004, KI-005)

## Context
The user asked to fix KI-003, KI-004 and KI-005 together. They are linked:
- **KI-003:** `agents/writer.py:5` imports `ollama` unguarded, so the whole server fails to start (`import main` → `ModuleNotFoundError`) whenever the package is missing. `app/start.bat:39` only checks `import fastapi`, so it never installs `ollama` when FastAPI already exists.
- **KI-004:** `app/requirements.txt` pins `ollama==0.3.3`, but the code needs ≥ 0.4: `response.message.content` (`specialist.py:54`, `writer.py:59`) is attribute access on the typed responses introduced in 0.4. It also pins `pydantic==2.7.1` (no wheels for current Pythons), omits `httpx` (imported in `main.py:7`), and pins two packages nothing imports.
- **KI-005:** the specialist uses the **synchronous** `ollama.chat` (`specialist.py:45`) inside async code: pipeline steps 1–5 and 7, and the three refine routes. While a call runs (seconds to minutes), the server can't answer anything, not even `/api/health` or sidebar loads.

**Done means:**
- The server starts even without `ollama`, and generation and refine then fail with a clear message.
- `start.bat` installs or upgrades whenever any dependency is missing or `ollama` is older than 0.4.
- `pip install -r app/requirements.txt` gives a working install on Python 3.11–3.14.
- Other requests are served while the specialist is working.

## Evidence (verified this session, read-only)
- **Real `ollama` source** (wheels 0.4.0 and 0.6.3 downloaded to a temp folder, not installed):
  - `AsyncClient.chat(model, messages, *, …, options=, keep_alive: float|str)` returns `ChatResponse`, the same in both versions. The streaming form is the one `writer.py` already uses.
  - `ollama==0.4.0` requires `pydantic>=2.9` and `httpx>=0.27,<0.28`. So the pydantic floor must be **2.9**, not the 2.7 the KI note guessed.
  - The latest release is 0.6.3.
- **`pip install --dry-run --ignore-installed`** of the proposed file on Python 3.14.5 resolves 23 packages, **all wheels**: fastapi 0.165.0, starlette 1.10.0, uvicorn 0.54.0 (+ httptools 0.9.0, watchfiles 1.3.0, websockets 17.4), pydantic 2.14.4, httpx 0.28.1, ollama 0.6.3.
- **Unused packages:** `aiofiles` is not installed, and the app ran fine without it all session; Starlette 1.6 never imports it. `python-multipart` is used only by Starlette's form parser, and the app has no form or file routes.
- **Call sites:** specialist calls at `chapter_pipeline.py:46,64,76,118,160,193` and `main.py:318,347,374`. The writer is already async (`ollama.AsyncClient`, `writer.py:48`).

## Approach
1. **KI-005: make the specialist async instead of thread-offloading** (`agents/specialist.py`). The real async client is cleaner than `asyncio.to_thread` and matches the writer. It needs no new imports and **shifts no line numbers** anywhere:
   - `def _call` → `async def _call`
   - `ollama.chat(` → `await ollama.AsyncClient().chat(` (same arguments)
   - every public `def` → `async def`, and `return _call(…)` → `return await _call(…)`
   - the guard's error text becomes `"ollama Python package not installed: run pip install -r app/requirements.txt"`
   - Callers only gain `await`: the 6 calls in `pipeline/chapter_pipeline.py` and the 3 refine calls in `main.py`, all on the same lines.
2. **KI-003, server side** (`agents/writer.py`):
   - Guard the import exactly like `specialist.py:11-14` (`try: import ollama / except ImportError: ollama = None`).
   - At the top of `stream_chapter`, `yield ("error", "<same message>"); return` when `ollama is None`.
   - That is +6 lines, so `writer.py` line references in the docs shift.
3. **KI-003, launcher** (`app/start.bat`):
   - Add one `set "DEP_CHECK=import fastapi, uvicorn, pydantic, httpx, ollama; from importlib.metadata import version; v = tuple(int(x) for x in version('ollama').split('.')[:2]); raise SystemExit(v < (0, 4))"` next to the other `set` lines.
   - The check runs `%PYTHON_EXE% -c "%DEP_CHECK%"`. If it fails, `pip install -r` installs or upgrades, then the check runs **again**. If it still fails, print the manual command, `pause`, and `exit /b 1`, instead of starting a server that can't work.
   - Line refs after the edit shift (+1 / +8).
4. **KI-004** (`app/requirements.txt`): lower bounds instead of exact pins, plus a comment recording the tested versions:
   ```
   fastapi>=0.111
   uvicorn[standard]>=0.30
   pydantic>=2.9,<3
   httpx>=0.27
   ollama>=0.4,<1
   ```
   `aiofiles` and `python-multipart` are dropped. The Python requirement stays 3.11+.

## Contract / data impact
- **None** for the API, SSE, data and models. Request and response shapes are unchanged; the specialist's return values are identical.
- **Dependencies change** (approved through this plan). Installing now pulls current releases instead of exact 2024 pins, and existing environments with `ollama<0.4` get upgraded by `start.bat`.

## Docs to update (RULES §6)
- **`docs/technical/09`:** move KI-003, KI-004 and KI-005 to the **Fixed** table (`Fixed in Unreleased [plan 005]`), mark their headings ✅, and add status lines. Note the pydantic ≥ 2.9 finding.
- **`docs/technical/06` §3:** the dependency table becomes lower bounds + tested versions, and the unused rows are removed. §2: the `start.bat` variables gain `DEP_CHECK`.
- **`docs/technical/07` §2–3:** `pip install -r app/requirements.txt` is the recommended manual route again. Drop the ⚠ "why not requirements" and "only checks fastapi" notes.
- **`docs/technical/08`:**
  - A1/A2: no `ModuleNotFoundError` at startup any more; describe the new message.
  - A3: the server is no longer frozen during specialist steps.
  - The error table and B (Python versions) updated.
- **`docs/technical/01`:**
  - the technology table (versions, the unused-pins row, the "environment drift" note)
  - §7 tree comment
  - "Async, with blocking parts" (specialist now async; file I/O is still sync)
- **`docs/technical/02`:** W1 launch flowchart (dependency check + re-check), W3 note that specialist calls are awaited.
- **`docs/technical/03`:** §2.4 specialist (async), §2.5 writer (guard), §3 error-handling row, §5 the unused-pins row.
- **`docs/technical/04`:** refine section ("synchronous" → the call is awaited and the server stays responsive).
- **`docs/user-guide.md`:** install step (drop the ⚠ stale-pins note).
- **`docs/ai/RULES.md`:**
  - §4: "prefer `asyncio.to_thread` (see KI-005)" becomes "the specialist and writer use `ollama.AsyncClient`; wrap other blocking calls with `asyncio.to_thread`"
  - §1 stack line unchanged
- **Line references:** a script, as in plan 004, shifts `writer.py:N` and `start.bat:N` refs in the living docs. It skips the historical evidence of the now-fixed KIs. `specialist.py`, `chapter_pipeline.py` and `main.py` keep their lines.
- **`docs/CHANGELOG.md` `[Unreleased]`:**
  - **Fixed:** KI-003 (server starts without ollama; launcher re-checks), KI-005 (non-blocking specialist)
  - **Changed:** KI-004 (requirements are lower bounds; httpx added)
  - **Removed:** `aiofiles` and `python-multipart`
  - Each line tagged `[plan 005]`.
- **`docs/ai/memory/`:**
  - `gotchas.md`: drop the "ollama must be ≥ 0.4 / unguarded import" trap, which no longer exists. Keep "two Pythons".
  - `decisions.md`: D-009, dependency policy (lower bounds + tested-versions comment, why not exact pins).
  - `project-state.md` (next up), `session-log.md`.
- **Plan 005:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py -m py_compile` on all backend files.
2. **KI-003, without `ollama`** (the dev machine has none):
   - `cd app/backend && py -c "import main"` succeeds.
   - Sandbox server (a temp copy of `app/` + `data/`): `/api/health` returns 200.
   - The `generate-chapter` stream ends with `error "Pipeline error: ollama Python package not installed: run pip install …"`.
3. **Real `ollama` 0.6.3** (`pip install --target <temp> --no-deps`, on `PYTHONPATH`; the user's site-packages untouched):
   - `import main` works.
   - With no Ollama server running, generation fails cleanly (a connection error event), proving the real `AsyncClient` path is used.
   - Refine returns a 500 with no hang.
4. **KI-005, responsiveness.** A stub `ollama` whose `AsyncClient.chat` (non-stream) does `await asyncio.sleep(4)`:
   - Start a generation and a refine in the background.
   - Meanwhile, `/api/health` and `/api/characters` must answer in < 0.5 s (timed with `curl -w %{time_total}`).
   - **Contrast:** the committed HEAD code with a sync stub (`time.sleep(4)`) shows health latency ≈ 4 s.
5. **Launcher check.** A temp `.bat` holding the exact new `DEP_CHECK` and check/re-check block, with `pip` replaced by `echo` and stdin piped for `pause`, run with:
   - no ollama → install branch → "still missing" error and exit 1
   - `PYTHONPATH` with real ollama 0.6.3 → "Dependencies ready"
   - `PYTHONPATH` with ollama 0.3.3 → install branch
   - The real `start.bat` is **not** run: it would pip-install into your Python, open a server window and a browser.
6. **Requirements:** `pip install --dry-run --ignore-installed -r app/requirements.txt` resolves with wheels only.
7. **Cleanup:** temp dirs, servers on port 8000, and `cpython-314` `.pyc`. `git status --porcelain data/` is empty.
- **Not verifiable here:** real LLM output (no Ollama server/models); `start.bat` end-to-end.

## Risks & rollback
- **Lower bounds** mean future major releases could break the app. Mitigated by `<3` / `<1` caps on pydantic and ollama, plus the tested-versions comment. FastAPI and Uvicorn have no upper cap, as the KI recommends.
- **Per-call clients.** `AsyncClient()` is created per specialist call (the writer already does this); each call still makes one HTTP request.
- **First launch after updating.** On machines with `ollama 0.3.3`, the first `start.bat` run upgrades packages, which needs network access. If it fails, the launcher now stops with the manual command instead of starting a broken server.
- **Rollback:** revert the four code files plus `requirements.txt` and `start.bat`. No data change.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 005]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **Where the writer's guard went.** It sits right after the docstring of `stream_chapter` (the plan said "at the top"; same effect). `writer.py` shifts +3 for old lines 6–35 and +6 from old line 36. Doc refs were updated in 03, 06 and 08.
- **Line endings.** `start.bat` and `requirements.txt` keep CRLF in the working tree (checked byte-wise: 94 and 11 CRLF lines, 0 bare LF).
- **Refine without the `ollama` package** returns a plain 500 "Internal Server Error". Generation gives the clear message; refine does not. Accepted as planned and documented in 04.
- **Tooling.** Doc edits ran from temp script files (deleted afterwards), because inline heredocs with apostrophes break the Bash tool. Logged in `gotchas.md`.

## Outcome
**Shipped** (uncommitted):
- `agents/specialist.py`: every function except `_extract_json` is `async def`. `_call` uses `await ollama.AsyncClient().chat(...)`, and the error text names the install command. No line shifts.
- `pipeline/chapter_pipeline.py` (6 calls) and `main.py` (3 refine calls) await the specialist. No line shifts.
- `agents/writer.py`: `try/except ImportError` around `import ollama`; `stream_chapter` yields a clear error when the package is missing.
- `app/start.bat`: `DEP_CHECK` (imports all runtime packages, requires `ollama >= 0.4`), then install, re-check, and on failure an error with the manual command, `pause`, `exit /b 1`.
- `app/requirements.txt`: `fastapi>=0.111`, `uvicorn[standard]>=0.30`, `pydantic>=2.9,<3`, `httpx>=0.27`, `ollama>=0.4,<1`, plus a verified-versions comment. `aiofiles` and `python-multipart` removed.

**KIs fixed:** KI-003, KI-004, KI-005.

**Decision:** D-009 (dependency policy).

**CHANGELOG `[Unreleased]`:**
- Changed: KI-004
- Removed: the unused packages
- Fixed: KI-003, KI-005

**Docs updated:**
- technical 01, 02 (W1 flowchart and notes), 03 (§2.4, §2.5, §5), 04, 06 (§2.6, §3, refs), 07 (§2.2), 08 (A1, A2, A3, B), 09 (Open/Fixed tables)
- `user-guide.md`
- `RULES.md` §4
- memory: `gotchas.md`, `decisions.md`, `project-state.md`, `session-log.md`

**Verification** (2026-11-22, Python 3.14.5):
1. `py_compile` passed on all backend files.
2. **No `ollama` installed:** the fixed code imports, while the committed code raised `ModuleNotFoundError`. The server answers health and characters with 200. Generation ends with `Pipeline error: ollama Python package not installed: run pip install -r app/requirements.txt`, and creates no chapter. Refine → 500.
3. **Real ollama 0.6.3** (isolated `--target` install):
   - `import main` works.
   - With no Ollama server, generation fails in about 4.2 s with the library's "Failed to connect to Ollama" message. The traceback runs through `await specialist.analyze_plot` → `await ollama.AsyncClient().chat(`.
   - Refine → 500 in about 4.3 s, with no hang.
4. **Responsiveness** (stub specialist call = 4 s):
   - Fixed code: 20 requests to `/api/health` and `/api/characters` during a generation plus a refine took at most **0.07 s** (0.03 s average), and the generation completed.
   - Committed code with a sync stub: at most **14.9 s**.
5. **Launcher.** The real `start.bat` lines 1–55 were extracted, with pip replaced by an echo:
   - no ollama → install branch → "still missing" → exit code 1 (read via `call`)
   - ollama 0.6.3 → "Dependencies ready"
   - ollama 0.3.3 → install branch
6. **`pip install --dry-run --ignore-installed -r app/requirements.txt`:** 23 packages, all wheels (fastapi 0.165.0, uvicorn 0.54.0, pydantic 2.14.4, httpx 0.28.1, ollama 0.6.3). `aiofiles` and `python-multipart` are not pulled in.
7. **Cleanup:**
   - Temp sandboxes, the temp `ollama` installs and the test servers (port 8011) were removed.
   - The `cpython-314` bytecode was deleted.
   - Your Python still has no `ollama`, and `data/` is untouched.

**Not verified:**
- real LLM output (no Ollama server or models)
- `start.bat` end to end (it would install into the user's Python and open a server window and a browser)

**Follow-ups:** none required. Optional: map a missing `ollama` package to a clear 503 in the refine routes.
