# 08 — FAQ & Troubleshooting

> **Applies to:** v1.0.0. **Last verified against code:** 2026-11-22.

## Part A — Troubleshooting

### A1. The browser shows "⚠ Cannot connect to backend. Is the server running on port 8000?"
1. Is the **NovelForge-Backend** window open? If it closed immediately, the server crashed at startup. Run it manually to see the error:
   ```bash
   cd app/backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
2. **`ModuleNotFoundError: No module named 'ollama'`** (from `agents/writer.py`): install it with `pip install "ollama>=0.4"`. `app/start.bat` skips installation whenever FastAPI is already present (KI-003).
3. **`Error loading ASGI app. Could not import module "main"`**: you ran `uvicorn main:app` from the wrong folder. Run it from `app/backend/`, or from the repo root with `--app-dir app/backend`.
4. **Port in use** (`[Errno 10048]` / `address already in use`): another process holds port 8000, often an old backend window. Close it, or change the port in all three places ([06 §2.1](06-configuration.md#21-network--process)).
5. You opened `http://localhost:8000` instead of `http://127.0.0.1:8000`. That usually still works (CORS is open), but prefer `127.0.0.1`.

### A2. Generation fails immediately with "Pipeline error: …"
| Message contains | Cause | Fix |
|---|---|---|
| `Connection refused`, `ConnectError`, `Failed to connect to Ollama` | Ollama is not running | Start Ollama (`ollama serve` or the tray app) |
| `model "xyz" not found` / 404 | Selected model not pulled | `ollama pull xyz`, or choose an installed model in Settings |
| `'dict' object has no attribute 'message'` | ollama-python < 0.4 installed | `pip install -U "ollama>=0.4"` (KI-004) |
| `ollama library not installed` | `ollama` package missing (specialist guard) | `pip install "ollama>=0.4"` |
| `'>' not supported between instances of 'str' and 'int'` | Specialist returned `estimated_chapters` as text (KI-015) | Retry, or use a stronger specialist model |
| model name is empty (`model is required`) | Settings were saved with empty model fields (KI-006) | Open Settings **with the button**, pick models, Save |

The full traceback is in the SSE `error.detail` field. Watch it with the `curl -N` command in [07 §7](07-setup-and-usage.md#7-developer-quick-reference) or in the browser DevTools → Network → the `generate-chapter` response.

### A3. Generation hangs on one step
- Steps 1–5 and 7 call the specialist **synchronously**. While a call runs, the whole server is busy, and even sidebar reloads wait (KI-005). Large models on CPU can take minutes per step.
- First use of a model includes loading it from disk into VRAM. Check `ollama ps` to see what is loaded.
- If the writer step never starts, VRAM may be exhausted. See A4.

### A4. Out of memory / VRAM errors, or the system becomes very slow
- Use smaller models (e.g. writer `llama3.1:8b`, specialist `phi4-mini:3.8b`).
- The writer requests `num_ctx 32768`. Lowering it in `writer.py:57` greatly reduces memory use.
- After using the Build tabs, the specialist stays loaded (`keep_alive=-1`). Run `ollama stop <model>` or restart Ollama to free it.
- Close other GPU-heavy applications.

### A5. "Failed to save character: … 422 …" when using the New Character / Edit modal
Known v1.0.0 defect (KI-001): the form does not send a `slug`, which the backend requires. **Workaround:** use the **Character Build** tab (it can also update an existing character), or edit `data/characters/<slug>.json` by hand. Locations have the same issue (use **Scene Build**).

### A6. After World Build, the World Settings modal is empty / my world got wiped
Known defect (KI-002). The World Build call **did** save correctly on the server, but the page's in-memory copy is broken. **Reload the page before opening World Settings.** If you already saved the empty modal, the world file was overwritten. Restore `data/world_settings.json` from a backup or from git (`git checkout -- data/world_settings.json` if it was committed).

### A7. The Build tab says "✓ Created: undefined"
Cosmetic side effect of KI-002. The entity was created. It appears in the sidebar after the automatic reload.

### A8. A model pull says "installed" but the model is not there
The pull progress stream does not detect Ollama errors (KI-019), and "installed" badges match any tag of the same family (KI-020). Verify with `ollama list`. Pull manually with `ollama pull <exact:tag>`.

### A9. A character/location I added by hand doesn't show up
`get_all()` silently skips files that are invalid JSON or fail validation (missing `name`/`slug`, `type` not `main`/`temporary`, non-string `age`). Validate the file. The fastest check is to start Python in `app/backend/` and run `Character(**json.load(open(path)))`.

### A10. The same character exists twice with different slugs
Slugs come from two sources: `make_slug()` gives `xiao_fan`, while LLM-generated slugs vary (e.g. `xiao-fan-scientist-inventor`). Entity resolution is done by the LLM and can miss a match (KI-009). Merge them by hand: keep one file, delete the other, and fix `characters_featured` in chapters if you care about those tags.

### A11. Chapter numbers look wrong / a chapter was overwritten
The UI numbers new chapters as *count + 1*. If a chapter file is missing in the middle (e.g. `002.json` deleted while `003.json` exists), the next generation reuses an existing number and **overwrites** that chapter (KI-008).

### A12. Export fails
Titles containing `: ? * " < > |` produce an invalid Windows filename (KI-017). Rename the novel (click the header title) and export again.

### A13. The pipeline panel looks dimmed or a step stays red on the next run
Cosmetic (KI-024): fade and error styles are not reset between runs. Reload the page.

## Part B — FAQ

**Does anything leave my machine?**
No novel content does. The backend talks only to Ollama on `localhost`. The browser fetches web fonts from Google (no content is sent). Pulling models downloads from the Ollama registry.

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

**Is there an undo?**
No. Back up `data/` regularly, or commit it to a private git repo.

**Where are logs?**
Only the backend console window (uvicorn access log and Python tracebacks) and the browser DevTools console. There is no log file (KI-025).

**Which Python version should I use?**
3.11–3.14 all work with current FastAPI/Pydantic, provided you install a current `ollama` (≥ 0.4). Avoid the stale pins in `app/requirements.txt` until KI-004 is fixed.
