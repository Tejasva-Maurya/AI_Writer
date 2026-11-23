---
id: 010
title: "Honest model-pull results, one generation at a time with Cancel (KI-019, KI-031)"
status: done
approved: 2026-11-23T16:37:05+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: f73a302e5f4b006aefbeb6ecf06fde1de1dbe716f8477bd16771d6a987fc753f
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Honest model-pull results, one generation at a time with Cancel (KI-019, KI-031)

## Context
The user asked to fix KI-019 and KI-031 (read this session):
- **KI-019:** `pull_model` (`main.py:266-300`) ignores `resp.status_code`, swallows every JSON error (`except Exception: pass`) and **always ends with `{"status": "success"}`**. An unknown model, an Ollama error line (`{"error": …}`) or a truncated download shows "✓ installed" in Settings although nothing was installed.
- **KI-031:** `generate_chapter` (`main.py:160-177`) has no guard. Two tabs (or an API client) can run two pipelines at once; both number the chapter from disk at request time, so **both write the same chapter file** and race on character/meta updates. There is also no way to stop a running generation except closing the tab.
- **Facts checked:**
  - uvicorn 0.52 reports ASGI `spec_version` 2.3. For that, Starlette 1.6's `StreamingResponse` runs the stream next to `listen_for_disconnect` and **cancels the stream when the client disconnects**, so closing the tab cancels the pipeline at its current `await`.
  - `asyncio.CancelledError` is not caught by the pipeline's `except Exception` or the writer's, so a cancel propagates cleanly and closes the open Ollama HTTP request.
  - `.btn-small` sets no `display`, so the `hidden` attribute works on it (unlike KI-037).

**Done means:**
- A pull reports success only when Ollama says `success`; any HTTP error, `error` line or missing confirmation is reported as an error.
- Only one generation can run; a second request gets 409 with a clear message.
- The UI has a **Cancel** button that stops the running generation within a moment.
- Closing the tab still stops the generation, and the guard is always released.

## Approach
1. **KI-019, `main.py` `pull_model`:**
   - A non-200 response → `{"status": "error", "message": <Ollama "error" text or body>}`.
   - Each line is parsed. A line with `"error"` → error event and stop. `status == "success"` is remembered; other lines are progress as now. Unparseable lines are skipped.
   - After the stream: success only if Ollama sent it, else an error: "Ollama ended the download without confirming success".
   - The frontend's `pullModel` already handles `status: "error"`.
2. **KI-031, `main.py`: one job at a time.**
   - A module-level `_generation = {"task": None}`.
   - `POST /api/generate-chapter`: if the task is running → **409** "A chapter is already being generated. Wait for it to finish or cancel it." Otherwise run `run_pipeline` in its own `asyncio.Task` that feeds an `asyncio.Queue`; the SSE stream reads the queue.
   - **Cancel → the job.** If the task is cancelled, it queues `error {message: "Generation cancelled", cancelled: true}` before ending.
   - **Disconnect → the stream.** If the client disconnects, the stream's `finally` cancels the job. That keeps today's "closing the tab stops it", releases the guard and closes the Ollama request.
   - The guard can't leak: it is "task running", not a flag to reset.
   - **New route `POST /api/generate-chapter/cancel`** → `{"cancelled": true|false}` (false when nothing is running).
3. **KI-031, UI (`index.html`, `app.js`):**
   - A `#btn-cancel-generate` button (existing `btn-small` class, `hidden`) next to **Generate**, shown only while generating. Clicking it posts to the cancel route and disables itself.
   - The `error` handler: `cancelled` → an info toast "Generation cancelled" without red step styling; otherwise as now.
   - A non-OK response shows the server's `detail` (so the 409 message reads well), instead of "Server returned 409: Conflict".
   - Both refs go in the `DOM` cache.

## Contract / data impact
- **API:**
  - New route `POST /api/generate-chapter/cancel`.
  - `POST /api/generate-chapter` can return **409** while another generation runs.
  - The pull SSE now ends with `error` instead of a false `success` on failures.
- **SSE contract:** no new event type. `error` gains an optional `cancelled: true` (backward compatible; the UI and docs are updated).
- **`data/`:** none. A cancelled generation saves nothing beyond what earlier steps already wrote (step-3 profiles), the same as any failure.
- **Ports, models, LLM params:** unchanged.

## Docs to update (RULES §6)
- **`docs/technical/04`:** the new cancel route, 409 on generate, the `error.cancelled` field, honest pull results.
- **`docs/technical/02`:** W3.1/W3.2 (job + guard + cancel + disconnect), W3.4 `error` row, W8 pull steps 4.
- **`docs/technical/03`:**
  - §2.2 `main.py` table (the routes and the `_generation` holder)
  - §4 function catalogue (cancel), DOM cache
  - §4.5 bindings (Cancel button)
- **`docs/technical/07`:** usage (Cancel button; one generation at a time).
- **`docs/user-guide.md`:** the Cancel button.
- **`docs/technical/08`:** A8 ("pull says installed but it isn't" → now an error message), and a new FAQ entry for "A chapter is already being generated".
- **`docs/technical/09`:** KI-019 and KI-031 → Fixed [plan 010], status lines.
- **Line references:** the remap script (`main.py`, `app.js`, `index.html`) plus the doc 03 §2.2 regeneration.
- **`docs/CHANGELOG.md` `[Unreleased]`:**
  - **Added:** Cancel button and cancel route
  - **Fixed:** KI-019, KI-031
  - Each line tagged `[plan 010]`.
- **`docs/ai/memory/`:** `project-state.md`, `session-log.md`; `gotchas.md` (one generation at a time; tests must wait or cancel).
- **Plan 010:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py_compile` (all backend), `node --check app/frontend/app.js`.
2. **Two sandboxes** (committed code on 8011, fixed on 8012), temp copies of `app/` + `data/`.
3. **KI-019:** a fake Ollama on 127.0.0.1:11434 whose `/api/pull` behaves by model name. Call `/api/models/pull` on both servers:
   - **`zz-ok`:** progress then `success`; both report success.
   - **`zz-missing`:** HTTP 404 `{"error": …}`; old reports success, new reports an error with Ollama's text.
   - **`zz-stream-error`:** 200, progress, then an `{"error": …}` line; old success, new error.
   - **`zz-truncated`:** 200, progress, no success line; old success, new the "without confirming success" error.
4. **KI-031**, with a stub `ollama` whose specialist calls each take ~2 s and whose writer streams slowly:
   - **Concurrent:** start generation A in the background, then B immediately.
     - Old: both 200, both `complete` **with the same chapter number**.
     - New: B → 409 with the message, and A completes normally.
   - **Cancel:**
     - `POST /cancel` during A → the stream ends with `error {cancelled: true}` within ~1 s, and no chapter file is written.
     - A second `/cancel` → `{"cancelled": false}`.
     - The next generation is accepted (200).
   - **Disconnect:** `curl --max-time 1` aborts A; a new generation is accepted within a few seconds, and A's chapter is not written (the cancel took effect).
5. **UI (browser pane, fixed sandbox):**
   - Generate → the **Cancel** button appears; click → "Generation cancelled" info toast, the button hides, and **Generate** is re-enabled.
   - Generate again while a curl generation runs → the toast shows the 409 message.
   - The console is clean.
6. **Cleanup:** stop the servers (8000/8011/8012/11434); delete the sandboxes, stubs and `launch.json`; delete `cpython-314` bytecode. `git status --porcelain data/` is empty.
- **Not verifiable:** a real Ollama pull, and a real Ollama stopping generation on cancel (the client closes the HTTP request, which is how Ollama stops; not observable here).

## Risks & rollback
- **Single-user by design.** The guard is per server process. Running two backend processes on the same `data/` is not supported (the port allows only one anyway).
- **Disconnect still stops the generation** (unchanged behaviour, now explicit). Letting it finish in the background would need a status/reattach UI: a separate feature.
- **Cancel during step 7** can leave the chapter saved but some character updates unapplied. It is rare (seconds-long window) and the result is a valid state.
- **Rollback:** revert `main.py`, `app.js`, `index.html` and the docs. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 010]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- `cancel_generation` also waits up to 5 s for the task to end (`asyncio.wait`), so a new generation is accepted as soon as the cancel call returns.
- The pull no longer forwards Ollama's own `success` line as a progress event. Before, it was re-emitted, so the stream carried two `success` events.
- The UI also resets the pipeline steps on cancel and sets the output title to "Cancelled (not saved)".
- One CSS rule was added (`.generate-row .btn-small { white-space: nowrap; }`): in a narrow window "✕ Cancel" wrapped onto two lines.
- While editing doc 02 W3.2/W3.6 and doc 03 §5, stale statements were corrected:
  - "frontend always sends a number" (plan 006)
  - the KI-015/KI-018 failure rows (plan 009)
  - "after the CORS setup" (plan 007)
- Doc 07 §5.2's "N = existing chapters + 1" was also corrected (plan 006).

## Outcome
- **Shipped:**
  - **KI-019:** `pull_model` (`main.py:306-364`) reports an error for a non-200 status (with Ollama's `error` text), for an `{"error": …}` line, and for a stream without Ollama's `success`. An unreachable Ollama was already an error. `success` is sent only after Ollama confirms it.
  - **KI-031, backend:** `generate_chapter` (`main.py:171-207`) runs the pipeline as an `asyncio.Task` in `_generation` that feeds an `asyncio.Queue`.
    - It returns 409 while that task runs.
    - A cancel queues `error {message: "Generation cancelled", cancelled: true}`.
    - `event_stream()`'s `finally` cancels the task when the client disconnects.
    - New `POST /api/generate-chapter/cancel` (`main.py:210-217`) returns `{"cancelled": true|false}`.
  - **KI-031, UI:** a `#btn-cancel-generate` button (`index.html:170`, shown only while generating) calls `cancelGeneration()` (`app.js:583-592`). The `error` handler treats `cancelled` as an info toast. A non-OK response shows the server's `detail`.
- **Files:**
  - Code: `app/backend/main.py`, `app/frontend/app.js`, `app/frontend/index.html`, `app/frontend/style.css`.
  - Docs:
    - `docs/technical/01` §8, 02 (W3.1, W3.2, W3.4, W3.6, W8), 03 (§2.2 table regenerated, §4.2, §4.4, §4.5, §5), 04 (index, generate 409, cancel route, error.cancelled, pull), 07 §5.2, 08 (A8, new A15), 09 (KI-019, KI-031 → Fixed)
    - `docs/user-guide.md`, `docs/CHANGELOG.md`
    - memory files (project-state, gotchas, session-log)
    - line references remapped in docs/README, 01, 02, 03, 06, 09 and gotchas
- **KIs fixed:** KI-019, KI-031.
- **CHANGELOG:**
  - Added: the Cancel button and cancel route [plan 010] [KI-031]
  - Fixed: honest pull results [plan 010] [KI-019]
  - Fixed: one generation at a time [plan 010] [KI-031]
- **Verification:**
  - `py_compile` of every backend module and `node --check app/frontend/app.js`: OK.
  - **Setup:** two sandboxes (committed code on 8011, fixed code on 8012), each with a copy of `data/`. A slow `ollama` stub: 1.5 s per specialist call, 20 streamed tokens. A fake Ollama `/api/pull` on 127.0.0.1:11434.
  - **KI-019:**
    - `zz-ok`: both versions report success. The old one sent 2 `success` events, the new one sends 1.
    - `zz-missing` (HTTP 404): old says success; new says `Ollama returned 404: pull model manifest: file does not exist`.
    - `zz-stream-error`: old says success; new says `max retries exceeded: unexpected EOF`.
    - `zz-truncated`: old says success; new says `Ollama ended the download without confirming success`.
    - With no Ollama running, new reports `All connection attempts failed`.
    - In the browser, `pullModel` showed each message as "Pull failed: …".
  - **KI-031, concurrent:** on old, both generations got 200 and both completed as chapter 1 (one `001.json`: one overwrote the other). On new, the second got 409 with the message, and the first completed.
  - **KI-031, cancel:**
    - Cancel returned at once, and the stream ended after 2.5 s with `error {cancelled: true}`. No chapter file was written.
    - A second cancel returned `{"cancelled": false}`.
    - The next generation was accepted (200) and then cancelled too.
  - **KI-031, disconnect:** `curl --max-time 2` disconnected. Right after, cancel returned `false` (the guard was already free). After 10 s, no chapter had been written. The old code also stops on disconnect, so that behaviour is unchanged.
  - **UI (browser pane, fixed sandbox):**
    - **✕ Cancel** appears while generating. Clicking it ended the run in about 0.1 s with the info toast "Generation cancelled". The steps reset, the button hid, and Generate was re-enabled.
    - Generating while another generation ran showed the toast "Failed to generate chapter: A chapter is already being generated. Wait for it to finish or cancel it."
    - The console showed only the expected 409 lines.
  - **Server log:** no tracebacks or unretrieved-task warnings.
  - **Cleanup:** sandboxes, stub, fake server and the temp `.claude/launch.json` deleted; servers stopped; `cpython-314` bytecode removed; `git status --porcelain data/` empty.
- **Not verified:** a real Ollama pull, and that a real Ollama stops generating when the cancelled client closes its request.
- **Follow-ups:** none required. Optional: a "status/reattach" API so closing the tab doesn't stop the generation (a separate feature).
