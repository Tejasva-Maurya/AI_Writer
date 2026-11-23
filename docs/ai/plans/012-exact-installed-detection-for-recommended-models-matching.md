---
id: 012
title: "Exact \"installed\" detection for recommended models, matching frontend fallback specialist (KI-020, KI-028)"
status: done
approved: 2026-11-23T19:49:50+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 38c2f9515bd3710e79b95ed955f6c03af58e167676111e772f4fab6db7fcd66a
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Exact "installed" detection for recommended models, matching frontend fallback specialist (KI-020, KI-028)

## Context
The user asked to fix KI-020 and KI-028. Both are Low. Read this session:
- **KI-020:** `get_models()` (`main.py:288-296`) marks a recommended model as installed when *any* installed name matches exactly **or** shares its family prefix (`inst.startswith(rec["name"].split(":")[0] + ":")`).
  - Example: with only `gemma3:4b` pulled, `gemma3:12b` shows **✓ Installed** in Settings → Available Models, and **Set Writer** is offered instead of **⬇ Pull**.
  - Choosing it saves a model Ollama doesn't have, so the next generation fails at step 1.
  - `llama3.1:latest` likewise marks `llama3.1:8b` as installed.
  - The frontend has no prefix logic of its own: `populateModelSelects` uses an exact `installed.includes(m)` (`app.js:1725`), and `renderModelBrowser` shows the backend's `installed` flag (`app.js:1773`) and lists installed names that aren't recommended as extra "Installed" entries (`:1758`). So this fix is backend-only.
- **KI-028:** `loadNovelMeta()`'s fallback, used when `/api/novel-meta` can't be loaded (`app.js:167-174`), sets `specialist_model: 'gemma3:12b'`. The backend default is `phi4-mini:3.8b` (`models.py:148`).

**Done means:**
- A recommended model is "installed" only if Ollama lists that exact model. A name without a tag counts as `:latest`, as Ollama treats it.
- The frontend fallback uses the backend's default models.

## Approach
1. **`app/backend/main.py`** (KI-020): add a small module-level helper next to `RECOMMENDED_MODELS`:
   ```python
   def _model_key(name: str) -> str:
       """Ollama treats a name without a tag as name:latest (KI-020)."""
       return name if ":" in name.rsplit("/", 1)[-1] else f"{name}:latest"
   ```
   - The `rsplit` keeps a registry host's `:port` from counting as a tag.
   - In `get_models()`: `installed_keys = {_model_key(n) for n in installed}`, and `rec_copy["installed"] = _model_key(rec["name"]) in installed_keys`. The family-prefix test is dropped.
   - The response shape is unchanged.
2. **`app/frontend/app.js`** (KI-028): the fallback's `specialist_model: 'gemma3:12b'` → `'phi4-mini:3.8b'`, matching `NovelMeta` (`writer_model` is already `gemma3:12b`, the same as the backend).

**Not changing:** a tagged name with a different tag (e.g. `llama3.1:latest` vs `llama3.1:8b`) is "not installed" even when Ollama's registry happens to point both at the same weights. Names can't show that, and calling it installed is exactly the defect.

## Contract / data impact
- **API:** `GET /api/models` keeps the same fields; only the value of `recommended[].installed` becomes exact.
- **No other change:** no SSE or `data/` change, and no new UI elements.

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-020 and KI-028 → Fixed [plan 012]; update the summary counts.
- **`docs/technical/04`:** `GET /api/models`, the `installed` note.
- **`docs/technical/02`:** W8 step 2.
- **`docs/technical/03`:** §2.2 (`get_models` row, new `_model_key` row, line column regenerated).
- **`docs/technical/06`:** the "Frontend fallback meta" row.
- **`docs/technical/08`:** A8, the installed-badge note.
- **Line references:** remap for `main.py` (`app.js` doesn't shift).
- **`docs/CHANGELOG.md` → Fixed:**
  - exact "installed" badges [plan 012] [KI-020]
  - fallback specialist [plan 012] [KI-028]
- **`docs/ai/memory/`:** `project-state.md` (also commits the plan-011 "pushed" lines), `session-log.md`.
- **Plan 012:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py_compile app/backend/main.py`, `node --check app/frontend/app.js`.
2. **Helper:** with `py -c "from main import _model_key"` (in `app/backend/`), check:
   - `gemma3` → `gemma3:latest`; `gemma3:12b` unchanged
   - `host:5000/ns/model` → `host:5000/ns/model:latest`; `host:5000/ns/model:7b` unchanged
3. **API, old vs new:**
   - **Setup:** sandboxes (HEAD on 8011, working tree on 8012), each with a copy of `data/`, plus a fake Ollama on 127.0.0.1:11434 whose `/api/tags` lists `gemma3:4b`, `llama3.1:latest`, `phi4-mini:3.8b`, `mistral-nemo:12b-instruct-2407-q4_0`.
   - **Old:** `gemma3:12b`, `llama3.1:8b`, `mistral-nemo:12b` and `phi4-mini:3.8b` are all flagged installed.
   - **New:** only `phi4-mini:3.8b` is.
   - **`installed` list:** identical on both.
4. **UI (browser pane, both servers):**
   - **Settings → Available Models:**
     - Old: `gemma3:12b` shows ✓ Installed + Set Writer.
     - New: it shows ⬇ Pull, and `gemma3:4b` appears as an extra installed entry with Set Writer/Set Specialist.
   - **KI-028:** make `/api/novel-meta` fail (stub `fetch` for that URL in the page), then call `loadNovelMeta()`. `state.novelMeta.specialist_model` is `gemma3:12b` on old and `phi4-mini:3.8b` on new.
   - The console is clean on new.
5. **Cleanup:** stop the servers and fake Ollama; delete the sandboxes and the temp `launch.json`; delete `cpython-314` bytecode. `git status --porcelain data/` is empty.
- **Not verifiable:** a real Ollama's `/api/tags` (the fake follows the documented `{"models": [{"name": …}]}` shape).

## Risks & rollback
- **Badge changes:** users who relied on the loose match (e.g. `gemma3:4b` installed, `gemma3:12b` shown as installed) now see Pull for the recommended entry. Their actual model still appears as its own "Installed" entry, so nothing becomes unselectable.
- **Rollback:** revert the two lines/blocks and the docs.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 012]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:** none in the code. Docs: doc 06's header gets a scoped "verified" date (only the fallback row was re-checked), as doc 01 did in plan 010. The project-state next-up list was refreshed.

## Outcome
- **Shipped:**
  - **`app/backend/main.py` (KI-020):**
    - `_model_key(name)` (`:275-277`) adds `:latest` when the last path segment has no tag; a registry `:port` is not a tag.
    - `get_models()` (`:280-307`) builds `installed_keys` and flags a recommended model only when `_model_key(rec["name"])` is in it. The family-prefix match is gone.
  - **`app/frontend/app.js` (KI-028):** the `loadNovelMeta` fallback specialist is `'phi4-mini:3.8b'` (`:173`).
- **Files:**
  - Code: `app/backend/main.py`, `app/frontend/app.js`.
  - Docs:
    - `docs/technical/09`: KI-020 and KI-028 fixed; counts updated.
    - `04` (`GET /api/models`), `02` (W8 step 2), `03` (§2.2: new `_model_key` row, `get_models` row, line column), `06` (fallback row, header), `08` (A8).
    - Line refs remapped in 01, 02, 03, 06 and 09.
    - `docs/CHANGELOG.md`, and memory (project-state, session-log).
- **KIs fixed:** KI-020, KI-028.
- **CHANGELOG (Fixed):**
  - exact installed badges [plan 012] [KI-020]
  - fallback specialist [plan 012] [KI-028]
- **Verification:**
  - `py_compile` of `main.py` and `node --check` of `app.js`: OK.
  - **Helper:** `_model_key` gave the expected key for `gemma3`, `gemma3:12b`, `host:5000/ns/model`, `host:5000/ns/model:7b` and `hf.co/user/repo`.
  - **API:** sandboxes (HEAD on 8011, working tree on 8012) behind a fake `/api/tags` listing `gemma3:4b`, `llama3.1:latest`, `phi4-mini:3.8b` and `mistral-nemo:12b-instruct-2407-q4_0`.
    - Old flagged `gemma3:12b`, `llama3.1:8b`, `mistral-nemo:12b` and `phi4-mini:3.8b` as installed; new flags only `phi4-mini:3.8b`.
    - The `installed` lists are identical.
  - **UI (Settings model browser):**
    - Old showed those 3 as "Installed" with Set buttons.
    - New shows **⬇ Pull** for them. `gemma3:4b`, `llama3.1:latest` and `mistral-nemo:12b-instruct-…` stay listed as "Installed" entries with Set Writer/Set Specialist on both.
  - **Fallback:** with `/api/novel-meta` made to fail in the page, the specialist was `gemma3:12b` on old and `phi4-mini:3.8b` on new; the writer was `gemma3:12b` on both.
  - **Console:** only the expected "Could not load novel meta" warning from the simulated failure.
  - **Cleanup:** sandboxes, fake Ollama and the temp `.claude/launch.json` removed. `git status --porcelain data/` empty.
- **Not verified:** a real Ollama's `/api/tags` (the fake follows the documented `{"models": [{"name": …}]}` shape).
- **Follow-ups:** none.
