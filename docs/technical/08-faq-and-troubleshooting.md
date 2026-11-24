# 08 — FAQ & Troubleshooting

> **Applies to:** v2.0.0 + [Unreleased]. **Last verified against code:** 2026-11-24.

## Part A — Troubleshooting

### A1. The browser shows "⚠ Cannot connect to backend. Is the server running on port 8000?"
1. Is the **NovelForge-Backend** window open? If it closed immediately, the server crashed at startup. Run it manually to see the error:
   ```bash
   cd app/backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
2. **A missing Python package** (`ModuleNotFoundError: No module named '…'`): run `pip install -r app/requirements.txt` from the repo root. Since plan 005, `app/start.bat` checks every package on launch and installs or upgrades as needed. The backend also starts without `ollama`; generation then fails with the message in A2.
3. **`Error loading ASGI app. Could not import module "main"`**: you ran `uvicorn main:app` from the wrong folder. Run it from `app/backend/`, or from the repo root with `--app-dir app/backend`.
4. **Port in use** (`[Errno 10048]` / `address already in use`): another process holds port 8000, often an old backend window. Close it, or change the port in all three places ([06 §2.1](06-configuration.md#21-network--process)).
5. `http://localhost:8000` and `http://127.0.0.1:8000` both work (the UI calls `/api` on its own origin since plan 007). Other host names (e.g. your machine name) get **400 Invalid host header** by design.

### A2. Generation fails immediately with "Pipeline error: …"
| Message contains | Cause | Fix |
|---|---|---|
| `Connection refused`, `ConnectError`, `Failed to connect to Ollama` | Ollama is not running | Start Ollama (`ollama serve` or the tray app) |
| `model "xyz" not found` / 404 | Selected model not pulled | `ollama pull xyz`, or choose an installed model in Settings |
| `'dict' object has no attribute 'message'` | ollama-python < 0.4 installed | `pip install -r app/requirements.txt` (upgrades it; `start.bat` does this automatically) |
| `ollama Python package not installed: run pip install -r app/requirements.txt` | `ollama` package missing (the server still starts) | Run that command, then restart the backend |
| model name is empty (`model is required`) | Settings were saved with empty model fields by v1.0.0 (KI-006, fixed in plan 006) | Open Settings, pick both models, Save |

The full traceback is in the SSE `error.detail` field. Watch it with the `curl -N` command in [07 §7](07-setup-and-usage.md#7-developer-quick-reference) or in the browser DevTools → Network → the `generate-chapter` response.

### A3. Generation hangs on one step
- Each specialist step (1–5 and 7) waits for the model, and large models on CPU can take minutes per step. The rest of the app stays usable meanwhile: sidebars and other pages still load (since plan 005, KI-005).
- First use of a model includes loading it from disk into VRAM. Check `ollama ps` to see what is loaded.
- If the writer step never starts, VRAM may be exhausted. See A4.

### A4. Out of memory / VRAM errors, or the system becomes very slow
- Use smaller models (e.g. writer `llama3.1:8b`, specialist `phi4-mini:3.8b`).
- The writer requests `num_ctx 32768`. Lowering it in `writer.py:63` greatly reduces memory use.
- After using the Build tabs, the specialist stays loaded for 5 idle minutes, then Ollama unloads it (since plan 013, KI-029; before, it stayed until Ollama restarted). To free it at once, run `ollama stop <model>`.
- Close other GPU-heavy applications.

### A5. "Failed to save character: … 422 …" when using the New Character / Edit modal
A v1.0.0 defect (KI-001), **fixed in v2.0.0 (plan 003)**: the form now sends a `slug`, and edits keep the chapter-tracking fields (KI-027). If you still see a 422, your browser is running an old cached `app.js`. Hard-reload the page (`Ctrl+F5`).

### A6. After World Build, the World Settings modal is empty / my world got wiped
A v1.0.0 defect (KI-002), **fixed in v2.0.0 (plan 003)**: the World Settings modal now opens with the merged world. If you saved the empty modal while still on 1.0.0, the world file was overwritten. Restore `data/world_settings.json` from a backup. Git can't help here: `data/` is not in git since plan 017 (KI-030).

### A7. The Build tab says "✓ Created: undefined"
A cosmetic v1.0.0 side effect of KI-002, **fixed in v2.0.0 (plan 003)**. The tab now shows the created name.

### A8. A model pull says "installed" but the model is not there, or "Pull failed: …"
- Since plan 010 (KI-019) a pull reports success only when Ollama confirms it. Otherwise you see "Pull failed:" plus Ollama's reason:
  - "Ollama returned 404: pull model manifest: file does not exist": the name or tag is wrong.
  - "max retries exceeded …": a network problem.
  - "Ollama ended the download without confirming success": the download stopped early. Pull again.
  - "All connection attempts failed": Ollama isn't running.
- Before plan 010 every pull ended with "installed".
- "Installed" badges match the exact model since plan 012 (KI-020). Before, any tag of the same family counted, so `gemma3:12b` could show as installed when only `gemma3:4b` was pulled. Verify with `ollama list`, and pull manually with `ollama pull <exact:tag>`.

### A9. A character/location I added by hand doesn't show up
`get_all()` skips files that are invalid JSON or have no `name`/`slug`, and since plan 016 the server console says which one and why (`WARNING managers.storage: Skipped unreadable characters/<file>: <error>`). Wrong-typed values (an unknown `type`, a numeric `age`, a string for a list) are coerced since plan 009, so such files load again. Validate the file: start Python in `app/backend/` and run `Character(**json.load(open(path)))`.

### A10. The same character exists twice with different slugs
Since plan 007 new slugs are always `make_slug(name)`, the pipeline maps the specialist's matches onto existing slugs, and creating an equivalent slug (`xiao-fan` vs `xiao_fan`) is refused, so new duplicates should not appear. Duplicates created by older versions remain: merge them by hand (keep one file, delete the other, and fix `characters_featured` in the chapters that used the deleted slug).

### A11. Chapter numbers look wrong / a chapter was overwritten
Since plan 006 the backend numbers new chapters as *highest existing number + 1*, so a gap (e.g. `002.json` deleted while `003.json` exists) just stays a gap, and nothing is overwritten. Chapters overwritten before that came from v1.0.0, which used *count + 1* (KI-008); restore them from a backup.

### A12. Export fails
Fixed in v2.0.0 (plan 015, KI-017): any title exports now; characters Windows forbids in file names (`: ? * " < > |`) become `_` in the download name, and nothing is written into `data/`. A `.txt`/`.md` file already in `data/` was left by an older version and can be deleted. If you still get a server error, the browser may be using an old page: hard-reload (`Ctrl+F5`).

### A13. The pipeline panel looks dimmed or a step stays red on the next run
Fixed in v2.0.0 (plan 011, KI-024): every run now starts with a full-opacity panel and no red step. If you still see it, your browser is running an old cached `app.js`; hard-reload the page (`Ctrl+F5`). The same plan fixed the blinking `▍` cursor staying after a chapter (KI-037) and the "may span multiple chapters" notice that never went away (KI-039).

### A13b. A yellow ⚠ toast appears during generation
It is a pipeline `warning` (shown since plan 009, KI-018): something non-fatal failed and the chapter continued. Typical messages: "Could not save character profile: …" (the specialist returned a profile without a name), "Could not update character '…'" (an update the model couldn't validate; the character keeps its old values), "Could not unload the specialist model: …" (Ollama didn't confirm the unload; watch VRAM). The same text is in the browser console.

### A14. "Failed to save character: … 409 … already exists"
Creating never overwrites an existing character or location (since plan 004, KI-036). The name you typed turns into the same file name (slug) as an existing entry. For example, "Elder Wu", "elder  wu" and "Elder-Wu!" all become `elder_wu`. **Either** give the new one a distinct name, **or** close the form and use **Edit** on the existing card. In the Build tabs, choose it under **Update Existing**. During chapter generation the same situation is handled silently: the existing profile is kept.
A name made only of symbols (e.g. `???`) is refused with **422** "name must contain at least one letter or digit" (since plan 007, KI-038). A `data/characters/.json` (or `data/scenes/.json`) left by an older version can't be edited or deleted from the UI; delete that file by hand.

### A15. "Failed to generate chapter: A chapter is already being generated…"
Only one chapter is generated at a time (since plan 010, KI-031). Another tab or a script (API **409**) is still generating.
- Wait for it to finish, or press **✕ Cancel** in the tab that started it.
- A script can call `POST /api/generate-chapter/cancel`.
- Closing the tab that started it also stops it.
- If no generation should be running, restart the server: the guard lives in memory.

## Part B — FAQ

**Does anything leave my machine?**
No. The backend talks only to Ollama on `localhost`, and the page loads everything, fonts included, from the local server (since plan 014; before, the browser fetched web fonts from Google, without any novel content). Only pulling models downloads from the Ollama registry.

**Where is my novel stored?**
In `data/` as plain JSON. See [05 — Data Model & Storage](05-data-model-and-storage.md). There is no database.

**Can I use OpenAI / Claude / another cloud API?**
Not in v1.0.0. All LLM calls go through `ollama-python` to a local Ollama server. Adding a provider means touching `agents/specialist.py` (`_call`), `agents/writer.py` and the model-management endpoints.

**Can I use any Ollama model?**
Yes. Pick it in Settings (it must be pulled). Specialist models must follow "output only JSON" instructions reliably. Very small or "reasoning" models (`deepseek-r1`, which emits `<think>` blocks) can break JSON parsing or leak thinking text into chapters.

**Why two models?**
JSON extraction and summarisation don't need a big model. Prose quality does. The specialist runs at temperature 0.1 for consistency, the writer at 0.8 for creativity. The pipeline unloads the specialist before writing to save VRAM ([01 §6](01-overview-and-architecture.md#6-the-dual-model-design-and-vram-strategy)).

**How does the AI remember earlier chapters?**
Through tiered summaries: the last 400 words of the previous chapter, full summaries of the 3 before that, short summaries of the 4 before those, and one-line summaries of everything older. Plus profiles of the characters/locations involved. See [02 §W3.3](02-workflows.md#w33-pipeline-steps-appbackendpipelinechapter_pipelinepy).

**Can I regenerate or edit a chapter?**
Not from the UI. You can edit `data/chapters/NNN.json` by hand (`full_text` and the summaries). To regenerate, call the API with an explicit `chapter_number` (it overwrites), or delete the file and generate again.

**Can I write in another language?**
Nothing prevents it. Write plots and profiles in that language and choose a model that handles it. The prompts themselves are English.

**How long is a chapter?**
The writer targets ~2,000 words. Actual length depends on the model.

**Can several people use it at once / over the network?**
It is designed for one user on one machine. It binds to `127.0.0.1` and has no authentication. Don't expose it on a network as-is.

**Does it work in a narrow window?**
Yes, since plan 017 (KI-035). Below 900 px the page becomes one scrolling column, with the writer first and the sidebars below. A phone or tablet can't reach the app, though: it only accepts connections from the same machine.

**Is there an undo?**
No. Back up `data/` regularly (copy the folder; see [07 §6](07-setup-and-usage.md#6-backup-reset-and-multiple-novels)). The app's own git repository ignores `data/` since plan 017 (KI-030), so it never saves your novel. For version history, make `data/` a separate private repository (`git init` inside it).

**Where are logs?**
Only the backend console window (uvicorn access log and Python tracebacks) and the browser DevTools console. There is no log file (KI-025).

**Which Python version should I use?**
3.11 or newer. `pip install -r app/requirements.txt` was verified on 3.14.5 (every package installs as a wheel) and pulls current versions on 3.11–3.13 too.
