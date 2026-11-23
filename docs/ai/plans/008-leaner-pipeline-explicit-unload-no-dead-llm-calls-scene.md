---
id: 008
title: "Leaner pipeline: explicit unload, no dead LLM calls, scene updates, whole-chapter summaries (KI-012, KI-013, KI-014)"
status: done
approved: 2026-11-23T15:16:59+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: d84b2075d054c60a950dd6356cfa0c76fe3608c391389f04f972dc38fb52582b
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Leaner pipeline: explicit unload, no dead LLM calls, scene updates, whole-chapter summaries (KI-012, KI-013, KI-014)

## Context
The user asked to fix KI-012, KI-013 and KI-014. All three are in the chapter pipeline and the specialist (read this session):
- **KI-012:** step 5 calls `specialist.predict_updates` (`chapter_pipeline.py:183`), a full LLM generation whose result (`update_predictions`) is never read. It exists only to send `keep_alive=0`, so that the specialist is unloaded before the writer loads.
- **KI-013:**
  - Step 7 passes `scene_profiles=[]` to `post_write_update` (`:216`), and the LLM's `scene_updates` are never applied, so locations never evolve.
  - `analyze_plot(plot, novel_meta, model)` never uses `novel_meta`.
  - Step 4's `select_context` LLM call (`:141-147`) is told to apply exactly the rules that the code then applies itself as a "fallback" (`:150-174`), so it is a second wasted round trip that can only add inconsistency (or crash on a non-dict reply).
- **KI-014:** `post_write_update` sends `chapter_text[:3000]` (`specialist.py:245`). A ~2000-word chapter is ~11–12k characters, so the summariser **never sees the ending hook** it is asked to summarise. Continuity then rests on summaries of chapter openings.
- **Library facts** (read from the ollama 0.4.0 and 0.6.3 wheels):
  - `AsyncClient.generate(model, prompt='', …, keep_alive=…)` builds its body with `model_dump(exclude_none=True)`, so `generate(model=m, keep_alive=0)` sends `{"model": m, "prompt": "", "keep_alive": 0, "stream": false}`.
  - That is Ollama's documented "unload a model" request (an empty prompt with `keep_alive` 0 unloads, done_reason `unload`). It generates nothing.

**Done means:**
- Step 5 unloads the specialist without generating anything.
- Step 4 is deterministic (no LLM call).
- Step 7 summarises the whole chapter (or opening + ending when it's too long) and updates featured locations.
- Each chapter costs 2 specialist calls fewer than today, with the same VRAM choreography (specialist unloaded before the writer loads, then again after step 7).

## Approach
1. **`agents/specialist.py`:**
   - **KI-012:** replace `predict_updates` with `async def unload(model)`: `await ollama.AsyncClient().generate(model=model, keep_alive=0)` (same missing-package guard as `_call`).
   - **KI-013:**
     - remove `select_context` (no callers left)
     - `analyze_plot(plot, model)` loses the unused `novel_meta` argument; the prompt is unchanged
     - `post_write_update` adds a `SCENE PROFILES (before this chapter)` block (slug, name, significance) next to the character block, so the `scene_updates` template has real slugs to refer to
   - **KI-014:** new `_chapter_excerpt(text)`.
     - It returns the whole text when it fits about **5000 tokens**: estimated as ¼ token per ASCII char and 1 per other char, so CJK chapters are counted safely.
     - Otherwise it returns the opening (40 % of the budget) + `[… middle of the chapter omitted …]` + the ending (60 %), so the ending hook is always included.
     - 5000 leaves ~3000 of the specialist's 8192 tokens for instructions, profiles and the JSON answer. A 2000-word English chapter (~2700 tokens) is always sent whole.
     - The prompt label changes from `CHAPTER TEXT (first 3000 chars):` to `CHAPTER TEXT:`.
   - `num_ctx`, `temperature` and `keep_alive` are unchanged.
2. **`pipeline/chapter_pipeline.py`:**
   - Step 1 calls `analyze_plot(plot, spec_model)`.
   - Step 4 drops the `select_context` call and the now-unused `chapters_brief`/`involved_*` lists. The existing rule loops build `char_detail`, `scene_detail` and `chapter_tiers` from empty dicts. Same status messages.
   - Step 5:
     - `await specialist.unload(spec_model)`, best-effort: an exception becomes a `warning` event (an existing SSE type) and generation continues.
     - Same status messages; `primary_chars`/`main_scenes` are computed as before.
   - Step 7:
     - pass the featured scene profiles (`main_scenes` found in `scenes_dict`)
     - apply `scene_updates`: for a featured scene with a non-empty string `new_significance`, set `significance` and `save()`, guarding non-dict and non-string values
     - character updates unchanged
3. **No frontend change.** Event types, the 7 steps and the status-message shape are all unchanged.

## Contract / data impact
- **API:** none.
- **SSE:** no new types; step 5 may now emit `warning` if the unload fails.
- **`data/`:** no schema change. Featured scenes' `significance` can now change after a chapter (intended KI-013 behaviour, like characters' `arc_notes`).
- **LLM behaviour:**
  - 2 fewer specialist calls per chapter (`select_context`, `predict_updates`); the step-7 prompt gets the whole chapter and a scene block.
  - VRAM invariant kept: the specialist is unloaded at step 5 (explicit `keep_alive=0`) and after step 7 (`keep_alive=0`), and the writer keeps `keep_alive=300`.

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-012, KI-013, KI-014 → Fixed [plan 008], status lines.
- **`docs/technical/02`:**
  - W3.3 rows for steps 1, 4, 5 and 7 (no LLM at step 4, explicit unload at step 5, whole chapter + scene updates at step 7)
  - the sequence diagram (`predict_updates` / "first 3000 chars")
  - the fallback-rules heading
- **`docs/technical/03`:**
  - §2.4 table: `analyze_plot` signature, `unload` replaces `predict_updates`, `select_context` removed, `post_write_update`, `_chapter_excerpt`
  - §3 prompt catalogue: two prompts gone, the post-write prompt updated
  - §5 dead-code rows removed (`update_predictions`, `scene_profiles`, `novel_meta`)
- **`docs/technical/01` §6 VRAM choreography:** the unload mechanism.
- **`docs/technical/05`:** scene `significance` now updated by step 7.
- **`docs/technical/06` §2.2–2.3:** `keep_alive` row (step-5 unload), the post-write text budget.
- **`docs/ai/RULES.md` §3:** the VRAM invariant wording.
- **Line references:** run the plan 007 multi-file remap (prefixed refs) plus the bare-ref remap of 02 W3.3. Check the 03 tables by hand.
- **`docs/CHANGELOG.md` `[Unreleased]`:**
  - **Fixed:** KI-014 (summaries see the whole chapter, ending hook included), KI-013 (locations evolve)
  - **Changed:** KI-012/KI-013 (2 fewer specialist calls per chapter: explicit unload, deterministic step 4)
  - **Removed:** `select_context`/`predict_updates` prompts
  - Each line tagged `[plan 008]`.
- **`docs/ai/memory/`:** `project-state.md`, `session-log.md`; `gotchas.md` if something new turns up.
- **Plan 008:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py_compile` on all backend files.
2. **Unit checks** (`py` one-off script, no server):
   - `_chapter_excerpt` returns a 12k-char English chapter whole.
   - A 40k-char English chapter → opening + marker + ending, with the final sentence present and an estimated cost ≤ 5000.
   - A 12k-char CJK chapter → excerpted (cost estimate), with the ending present.
3. **Real ollama client** (0.6.3 in a temp `--target` folder). A tiny fake Ollama HTTP server on 127.0.0.1:11434 logs request bodies and answers `/api/generate` and `/api/chat`.
   - `specialist.unload("m")` must send exactly `{"model":"m","prompt":"","keep_alive":0,"stream":false}` (plus nothing that generates) and parse the `done_reason: "unload"` reply.
   - A full sandbox pipeline run (sandbox copy of `app/` + `data/`, backend on 8012) through that fake server:
     - The server log shows the exact call sequence: chat ×3 (steps 1–3; step 3 only when new entities exist), then `generate` unload, then the streamed writer chat, then the post-write chat. No `select_context` / `predict_updates` prompts.
     - The post-write prompt contains the chapter's **last sentence** and the scene block.
     - A `scene_updates` reply updates only the featured scene's `significance` on disk.
     - A non-dict `scene_updates` is ignored without error.
4. **Unload failure:** the fake server returns 500 for `generate` → the stream contains `warning` and still completes.
5. **Cleanup:** stop the servers (8012, 11434); delete the sandbox, the temp ollama install and `cpython-314` bytecode. `git status --porcelain data/` is empty.
- **Not verifiable:** a real Ollama actually freeing VRAM (no Ollama or GPU here; the request matches the documented unload call); real summary quality.

## Risks & rollback
- **Prompt too long.** A summariser prompt above `num_ctx` would be truncated by Ollama. The 5000-token budget, with a conservative per-character estimate, keeps the total around 6.5k of 8192.
- **Step 4 is now purely rule-based.** This is what the removed prompt asked for anyway. If smarter selection is wanted later, it belongs in a separate design.
- **Unload is best-effort.** If it fails, the writer may load while the specialist is still resident (as before, if Ollama mis-handled the old call); the run continues with a warning.
- **Rollback:** revert `specialist.py`, `chapter_pipeline.py` and the doc edits. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 008]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **Unload request body.** It has **no `prompt` key**: `{"model": …, "stream": false, "keep_alive": 0}`, not `{…, "prompt": "", …}` as the plan expected. Both ollama 0.4.0 and 0.6.3 drop the empty prompt. This is exactly Ollama's documented unload example.
- **A broken string during the edit.** A heredoc turned the excerpt marker's `\n` into real newlines (a syntax error). `py_compile` caught it, and it was fixed with an exact edit before any test.
- **Test harness slip.** `PYTHONPATH="$DIR\\$s"` in Git Bash produced a literal `$s` and a false "ollama not installed"; a forward slash fixed it. Logged as a gotcha.

## Outcome
**Shipped** (uncommitted):
- `agents/specialist.py`:
  - `predict_updates` → `unload(model)` (`generate(model, keep_alive=0)`)
  - `select_context` removed
  - `analyze_plot(plot, model)`
  - new `_chapter_excerpt(text, budget=5000)`
  - `post_write_update` gets a `SCENE PROFILES` block and `CHAPTER TEXT:` from the excerpt
- `pipeline/chapter_pipeline.py`:
  - step 1 call updated
  - step 4 deterministic (no LLM; dead lists removed)
  - step 5 best-effort unload with a `warning` on failure
  - step 7 passes featured scene profiles and applies `scene_updates` to featured scenes (non-empty text only, type-guarded)
- No frontend, API or SSE-type change. `num_ctx`, `temperature` and `keep_alive` are unchanged.

**KIs fixed:** KI-012, KI-013, KI-014.

**CHANGELOG:**
- Changed: 2 fewer specialist calls
- Removed: the two prompts and the unused argument
- Fixed: whole-chapter summaries (KI-014), locations evolve (KI-013)

**Docs updated:**
- technical 01 (§6 table, gantt and note), 02 (W3.3 rows for steps 4/5/7, step-4 rules heading, scene note, sequence diagram), 03 (§2.4 rows, §3 prompt catalogue, §5 dead-code rows), 05, 06, 09
- `RULES.md` §3 VRAM invariant
- memory: `project-state.md`, `gotchas.md`, `session-log.md`
- line refs remapped: 12 (prefixed + W3.3 bare); 7 refs into changed code rewritten by hand

**Verification** (2026-11-23):
1. `py_compile` passed.
2. **`_chapter_excerpt` unit checks:**
   - 12k-char English chapter → whole (~3020 est. tokens)
   - 40k-char English chapter → 20k chars (~5011 est.) with opening, marker and ending
   - 12k-char CJK chapter → 5k chars (~5011 est.) with the ending
3. **Real ollama 0.6.3 client** (isolated `--target`) against a logging fake Ollama on 11434, committed (8011) vs fixed (8012) sandboxes:
   - Committed: analyze, resolve, **select_context**, **predict_updates** (`keep_alive` 0), writer, post_write = 6 generations. The post-write prompt was 3979 chars with **no ending** and no scene block, and the scene was unchanged.
   - Fixed: analyze, resolve, `generate` unload, writer, post_write = 4 generations plus one unload. The post-write prompt was 13415 chars with the ending and the scene block. The featured scene's `significance` → "Zz: where the experiment went wrong"; the update for a non-featured scene was ignored.
4. **Failure paths** (fixed code): long chapter + unload returning 500 + string `scene_updates`:
   - a `warning` "Could not unload the specialist model: …", then `complete`
   - the post-write prompt was 21202 chars with the marker and the ending
   - the scene was unchanged; chapter 002 saved (5931 words)
5. **ollama 0.4.0** (the requirements floor) sends the identical unload body and parses the reply.
6. **Cleanup:** ports 8011/8012/11434 stopped, temp sandboxes and ollama installs removed, `cpython-314` bytecode deleted, `data/` untouched.

**Not verified:**
- a real Ollama actually freeing VRAM (no Ollama or GPU here; the request is Ollama's documented unload call)
- real summary quality

**Follow-ups:** none required. KI-018 (the UI ignores `warning` events) now also hides a failed unload; worth fixing next with KI-015.
