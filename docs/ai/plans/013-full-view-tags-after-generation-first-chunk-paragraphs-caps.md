---
id: 013
title: "Full View tags after generation, first-chunk paragraphs, Caps-Lock-proof shortcuts, 5-minute specialist keep-alive (KI-032, KI-029)"
status: done
approved: 2026-11-23T22:02:32+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: e541951a9235adb5416bc713660ab1c6f07299e7e383003fd4e48095d3ccb209
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Full View tags after generation, first-chunk paragraphs, Caps-Lock-proof shortcuts, 5-minute specialist keep-alive (KI-032, KI-029)

## Context
The user asked to fix KI-032 and KI-029 (both Low). Read this session:
- **KI-032, three frontend glitches in `app/frontend/app.js`:**
  1. **Empty Full View tags.** The `complete` handler sets `state.currentChapter = {chapter_number, title, word_count}` (`:533-537`). `openChapterViewModal()` renders `characters_featured`/`scenes_featured` (`:1120-1135`), so **⛶ Full View** right after a generation shows no tags. The `complete` event already carries `characters` and `scenes` (`chapter_pipeline.py:278-279`): the same slug lists that are saved as `characters_featured`/`scenes_featured` (`:221-222`).
  2. **Lost first chunk.** In the `token` handler, a chunk containing `\n\n` is split only `if (currentParagraph)` (`:498`). If the very first chunk contains `\n\n`, nothing is shown until a later chunk with `\n\n`, or never if none comes. The saved text is fine.
  3. **Shortcuts and Caps Lock.** The Alt shortcuts compare `e.key === 'g' | 'n' | 's' | 'w'` (`:1441-1456`). With Caps Lock on, or Shift held, `e.key` is upper-case, so they don't fire.
- **KI-029:** `specialist._call()` defaults to `keep_alive=-1` (`specialist.py:41`), used by the three refine functions (`:273, 303, 336`) and by pipeline steps 1–3 (`:82, 115, 172`).
  - After a Build-tab call the specialist stays in VRAM until Ollama restarts.
  - A generation that fails or is cancelled (plan 010) before step 5's explicit unload also leaves it loaded indefinitely.
  - **User decisions, asked this session** (`keep_alive` is a RULES §5 guarded parameter):
    - **5 minutes** (`300`, the same as the writer)
    - applied to **`_call`'s default**, so refine and steps 1–3 both get it
  - Step 5 (`unload`, `0`) and step 7 (`post_write_update`, `0`) stay explicit, so normal generations are unchanged.

**Done means:**
- Full View right after a generation lists the chapter's characters and locations, the same as after reopening it from History.
- A first chunk with `\n\n` renders at once.
- Alt+G/N/S/W work with Caps Lock or Shift.
- The specialist leaves VRAM 5 minutes after a Build-tab call or an interrupted generation.

## Approach
1. **`app.js`, `complete` handler:** add `characters_featured: data.characters || []` and `scenes_featured: data.scenes || []` to `state.currentChapter`. The payload is unchanged; the backend already sends both fields.
2. **`app.js`, `token` handler:** in the `\n\n` branch, create and append `currentParagraph` first when there is none (as the other branch does), then split as today. The guard goes away; there is no change for later chunks.
3. **`app.js`, keyboard shortcuts:** `const key = e.key.toLowerCase();` once at the top of the listener, and compare `key` instead of `e.key`.
   - The same four letters, so no new shortcuts.
   - `toLowerCase` respects the keyboard layout (unlike `e.code`).
4. **`app/backend/agents/specialist.py`:** `_call(..., keep_alive: int = 300)`, with a one-line comment.
   - The module docstring's "last call uses keep_alive=0" stays true.
   - No other call sites change.

## Contract / data impact
- **None:** no API, SSE, `data/` or model-name change, and no new shortcuts.
- **LLM parameter, approved by the user:** the specialist's default `keep_alive` goes from `-1` to `300` (refine and steps 1–3). Step 5 and step 7 stay `0`; the writer stays `300`.

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-029 and KI-032 → Fixed [plan 013]; update the counts.
- **KI-029:**
  - `docs/technical/01` §6 (role table, gantt "Steps 1-3 (keep_alive -1)")
  - `02` (W3.5 sequence `keep_alive=-1`, W4 refine note)
  - `03` §2.4 (`keep_alive` column)
  - `04` (refine: "stays loaded")
  - `06` §2.2 (`keep_alive` row)
  - `08` A4 (`ollama stop` workaround)
  - `docs/ai/RULES.md` §3 VRAM invariant: add the 300 s default
- **KI-032:**
  - `03`: §4.2 (`currentChapter` comment), §4.5 (the Caps Lock note), §4.6 (the held-back edge case)
  - `02` W3.4 (`complete` row: `state.currentChapter` fields)
  - `07` §5.7 and `docs/user-guide.md`: the shortcuts work regardless of Caps Lock (shortcut docs per RULES §6)
- **Line references:** remap for `app.js` and `specialist.py`.
- **`docs/CHANGELOG.md`:**
  - **Fixed:** Full View tags, first paragraph, shortcuts [plan 013] [KI-032]
  - **Changed:** specialist unloads after 5 min idle [plan 013] [KI-029]
- **`docs/ai/memory/`:** `project-state.md`, `session-log.md`. A `decisions.md` entry (D-011) is needed only if the keep-alive policy counts as a non-obvious choice. It does (a guarded parameter), so add it.
- **Plan 013:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py_compile` (backend) and `node --check app/frontend/app.js`.
2. **KI-029 with the real ollama client:**
   - Install ollama 0.6.3 into a temp `--target` dir on `PYTHONPATH`, as in plan 008.
   - Run a logging fake Ollama on 127.0.0.1:11434 that records each request's `keep_alive` and returns canned JSON for `/api/chat`.
   - Call `refine_character` and `analyze_plot` directly (`asyncio.run`) on old and new code. Expected: old sends `-1`, new sends `300`.
   - `post_write_update` sends `0` on both, and `unload` sends `0` on both.
3. **KI-032 in the browser pane:**
   - Sandboxes (HEAD on 8011, working tree on 8012), each with a copy of `data/`. A stub `ollama` whose writer's **first** chunk is `"Opening line.\n\nSecond"` and whose step-7 reply is empty (slugs come from step 2/3).
   - Seed a sandbox character mentioned in the plot so `characters` is non-empty.
   - On each:
     - Right after the first token: old shows no text, new shows "Opening line."
     - After completion, open Full View: old has no character tags, new lists the featured slugs.
     - Dispatch `keydown` `{key: 'S', altKey: true}` (Caps Lock or Shift): old opens nothing, new opens Settings. The same for `'W'`.
     - Lower-case `'s'` still works on both.
   - Console clean.
4. **Cleanup:** stop the servers and fake Ollama; delete the sandboxes, temp packages and `launch.json`; delete `cpython-314` bytecode. `git status --porcelain data/` is empty.
- **Not verifiable:** real VRAM release after 5 minutes. Ollama's handling of `keep_alive` isn't observable here; the check is that the right value is sent.

## Risks & rollback
- **VRAM during a normal run:** the specialist still unloads at step 5, as before. With a very slow CPU-only specialist, a gap of more than 5 minutes between steps 1–3 *calls* would reload it (only a delay). Those calls run back to back, so this doesn't happen in practice.
- **Shortcuts:** `toLowerCase` also makes Shift+Alt+letter trigger. There are no Shift+Alt bindings, so nothing conflicts.
- **Rollback:** revert the two files and the docs.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 013]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **UI stub:** the plan suggested seeding a sandbox character. Instead, the stub's step-2 reply matched the character and location the sandbox copy of `data/` already had, by slug only; the novel content was not read. The effect is the same: `characters`/`scenes` were non-empty.
- **Keep-alive check:** extended to all three refine calls and to step 2, not just refine_character and step 1.
- **Shortcuts:** the key is read as `(e.key || '').toLowerCase()` to guard against an undefined `key`.
- **Docs:** `_call`'s docstring records the reason and D-011.

## Outcome
- **Shipped:**
  - **`app/frontend/app.js` (KI-032):**
    - The `complete` handler stores `characters_featured: data.characters || []` and `scenes_featured: data.scenes || []` (`:535-541`).
    - The `token` handler creates the first `<p>` before splitting on `\n\n` (`:498-501`; the `if (currentParagraph)` guard is gone).
    - The Alt shortcuts compare the lower-cased key (`:1444`).
  - **`app/backend/agents/specialist.py` (KI-029):** `_call(..., keep_alive: int = 300)` (`:41`), with a docstring. Steps 5 and 7 still pass `0`.
- **Files:**
  - Code: `app/frontend/app.js`, `app/backend/agents/specialist.py`.
  - Docs:
    - `docs/technical/09`: KI-029 and KI-032 fixed; counts updated.
    - `01` §6 (table, gantt, header), `02` (W3.4 `complete`, W3.5 sequence, W4 note), `03` (§2.4 `keep_alive` column, §4.2, §4.5, §4.6), `04` (refine), `06` (`keep_alive` row, header), `07` §5.7, `08` A4, `docs/user-guide.md` (shortcuts note), `docs/ai/RULES.md` §3 (VRAM invariant).
    - Line refs remapped in 02, 03 and 06.
    - `docs/CHANGELOG.md`, `docs/ai/memory/decisions.md` (D-011), and memory (project-state, session-log).
- **KIs fixed:** KI-029, KI-032.
- **CHANGELOG:**
  - Fixed: Full View tags, first paragraph, shortcuts [plan 013] [KI-032]
  - Changed: specialist unloads after 5 idle minutes [plan 013] [KI-029]
- **Verification:**
  - `py_compile` of `specialist.py` and `node --check` of `app.js`: OK.
  - **KI-029:** the real ollama 0.6.3 client (temp `--target`) against a logging fake Ollama, calling the specialist functions directly on old and new code.
    - refine_character, refine_scene, refine_world, analyze_plot and resolve_entities sent `keep_alive=-1` on old and `300` on new.
    - `unload` (`/api/generate`) and `post_write_update` sent `0` on both.
  - **KI-032:** browser pane, old (8011) vs new (8012), with a stub whose writer's first chunk was `"Opening line.\n\nSecond"` and whose step 2 matched the sandbox's existing character and location.

    | Check | Old | New |
    |---|---|---|
    | Text 0.6 s into writing | empty | "Opening line." + "Second" |
    | Final paragraphs | 3 | the same 3 |
    | Full View tags after generation | none | character + location slugs, identical to the chapter reopened from History |
    | Alt+`S` / Alt+`W` (upper case) | nothing | Settings / World |
    | Alt+`s` | Settings | Settings |

  - The new page's console was empty.
  - **Cleanup:** sandboxes, temp packages, fake Ollama and the temp `.claude/launch.json` removed. `git status --porcelain data/` empty.
- **Not verified:** that Ollama actually unloads after 300 idle seconds (Ollama-side behaviour). The verified part is that the client sends `keep_alive=300`.
- **Follow-ups:** none.
