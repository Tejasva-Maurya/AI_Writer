# 07 — Setup & Usage Guide

> **Applies to:** v1.0.0 + [Unreleased]. **Last verified against code:** 2026-11-23.
> For known defects that affect individual steps, see [09 — Known Issues](09-known-issues-and-tech-debt.md). Workarounds are noted inline with ⚠.

**Where things are:** the tool lives in **`app/`** (launcher `app/start.bat`, code in `app/backend/` and `app/frontend/`). Your novel lives in **`data/`**. Documentation lives in **`docs/`**.

## 1. Prerequisites

| Requirement | Details |
|---|---|
| OS | Windows 10/11 for `app/start.bat`. The backend also runs on macOS/Linux with the manual steps below. |
| Python | 3.11+ (per the user guide). Developed on 3.13 and seen on 3.14. Tick **"Add Python to PATH"** when installing. |
| Ollama | Install from https://ollama.com. The Ollama service must be running (tray icon or `ollama serve`). It listens on `localhost:11434`. |
| Hardware | A GPU with ≥ 8 GB VRAM for the default `gemma3:12b` writer. ≈ 3–6 GB works with smaller models (see [06 §2.4](06-configuration.md#24-model-catalogue-shown-in-settings)). CPU-only works but is slow. |
| Disk | Several GB per model. |
| Browser | Any modern Chromium/Firefox/Edge (uses `fetch` streaming and `AbortSignal.timeout`). |
| Internet | Needed once to install packages and pull models. The UI fonts load from Google Fonts but fall back gracefully when offline. |

## 2. Installation

### 2.1 Pull models

```bash
ollama pull gemma3:12b
```
```bash
ollama pull phi4-mini:3.8b
```
(These are the defaults: writer `gemma3:12b`, specialist `phi4-mini:3.8b`. You can also pull later from **⚙ Settings → Available Models → ⬇ Pull**.)

### 2.2 Install Python dependencies (recommended: virtual environment)

From the repository root:

```bash
python -m venv venv
```
```bash
venv\Scripts\activate
```
```bash
pip install -r app/requirements.txt
```

`app/requirements.txt` lists lower bounds (FastAPI, Uvicorn, Pydantic ≥ 2.9, httpx, ollama ≥ 0.4), so pip installs current versions. On Python 3.11–3.14 everything comes as ready-made wheels. If an older `ollama` (< 0.4) is installed, the same command upgrades it.
`app/start.bat` does this for you: on every launch it checks each package (and that `ollama` is at least 0.4), installs or upgrades when needed, and stops with the manual command if that fails. (In v1.0.0 the pins were stale and the launcher only checked FastAPI: KI-003 and KI-004, fixed in plan 005.)

### 2.3 Verify

```bash
python -c "import fastapi, uvicorn, pydantic, httpx, ollama; print('ok')"
```
```bash
ollama list
```

## 3. Running

### Option A — Windows launcher
Double-click **`app/start.bat`**. It detects Python, installs dependencies if FastAPI is missing, starts the server in a minimised window **NovelForge-Backend**, waits for `/api/health`, and opens `http://127.0.0.1:8000`.
**To stop:** close the NovelForge-Backend window.

### Option B — Manual (any OS)
Run from `app/backend/`, because uvicorn resolves `main:app` from the working directory (from the repo root, add `--app-dir app/backend` instead):

```bash
cd app/backend
```
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
Development with auto-reload: `python main.py` (runs uvicorn with `reload=True`), or add `--reload` to the command above.

Then open **http://127.0.0.1:8000**. Use `127.0.0.1`, not `localhost`: the frontend calls `http://127.0.0.1:8000/api` explicitly.

### Smoke test
```bash
curl http://127.0.0.1:8000/api/health
```
```bash
curl http://127.0.0.1:8000/api/models
```
`ollama_running: true` in the second response confirms the backend can reach Ollama. Interactive API docs: **http://127.0.0.1:8000/docs**.

## 4. First-run checklist

1. **⚙ Settings** (button or `Alt+S`): set title/genre/author. Make sure both model dropdowns show models that are actually installed (the status bar should say "Ollama running — N model(s) installed"). **Save Settings**.
2. **World Build** tab: describe your world in free text (cultivation realms, magic, factions…) → **Integrate into World Settings**. The snapshot above the box shows the merged result.
3. **Character Build** / **Scene Build** tabs: describe your main cast and key locations → **Refine & Save**. They appear in the sidebars after a moment.
4. **Plot Writing** tab: write your first chapter plot → **▶ Generate Chapter**.

## 5. Using the application

### 5.1 Screen layout

```
┌───────────────────────────── Header ─────────────────────────────┐
│ ✦ NovelForge AI   [ Novel Title ✎ ]      📖 N chapters ⚙ Settings 📤 Export ▾ │
├──────────────┬──────────────────────────────────┬────────────────┤
│ CHARACTERS   │ [✍ Plot][👤 Character][🏔 Scene][🌐 World] │ LOCATIONS      │
│  MAIN CAST   │  mode panel (input + action button)        │  scene cards   │
│  cards…      │  ⚡ GENERATION PIPELINE (7 steps)           │                │
│  SUPPORTING  │  Chapter output (streaming) ⛶ Full View    │                │
│  cards…      │  📚 HISTORY  [Ch.1][Ch.2]…                  │ + New Location │
│ + New Char.  │                                            │ 🌐 World Sett. │
└──────────────┴──────────────────────────────────┴────────────────┘
```
Colour code: **purple** = characters, **gold** = locations, **mint** = world.

### 5.2 Writing chapters (Plot Writing tab)

1. The label shows **CHAPTER N** (N = highest existing chapter number + 1, the number the backend will use).
2. Describe *what happens*, not prose. Name characters and places explicitly. That is how the pipeline finds them in the database or creates new profiles. Example:
   > *Xiao Fan discovers a cultivation technique hidden in the Azure Cave. Practising it causes a spiritual explosion that draws Elder Wu and two inner disciples to investigate.*
3. Press **▶ Generate Chapter**, `Ctrl+Enter` (in the textarea) or `Alt+G` (anywhere).
4. Watch the 7 steps: Analyze Plot → Extract Entities → Build Profiles → Optimize Context → Prepare Model → Write Chapter (text streams in) → Summarize & Save. Newly discovered characters/locations pop up as tags and toasts, and they appear in the sidebars. A yellow ⚠ toast means a non-fatal problem in a step (e.g. a profile that couldn't be saved); the chapter still completes ([08 A13b](08-faq-and-troubleshooting.md)).
5. When the run completes, the title and word count are filled in, the chapter is added to **HISTORY**, and the plot box clears.
6. To stop a run, press **✕ Cancel** next to the Generate button (shown only while generating). The steps reset and a "Generation cancelled" toast appears. Nothing is saved unless the last step had already run. Character/location profiles created in step 3 stay.

Tips:
- First generation is slow while models load into VRAM. Within 5 minutes the writer stays warm.
- One chapter is generated at a time. If another tab (or a script) is already generating, **Generate** shows "A chapter is already being generated. Wait for it to finish or cancel it." Closing the tab that started a generation also stops it.
- If the plot clearly spans several chapters, you'll see a notice. Only the current chapter is written. Split the plot yourself.
- Chapter quality depends heavily on the summaries of earlier chapters. Use a capable specialist model if summaries look poor.
- There is no "regenerate" or "delete chapter" button. To redo the last chapter, delete `data/chapters/NNN.json` while the server runs, reload the page, and generate again.

### 5.3 Characters

- **Auto-created** during generation when a new name appears in the plot.
- **Character Build tab:** free-text description, optional name, optional **Update Existing** (merges into that character: non-empty AI fields overwrite, lists are replaced, name/slug are kept).
- **Sidebar card:** click or **View** → profile. **Edit** → form modal. **Delete** → confirm. Editing keeps the fields the form doesn't show (first/last chapter).
- **+ New Character** (or `Alt+N`) → form modal. The file name (slug) is derived from the name. If a character with that slug already exists, saving shows an error ("409 … already exists") and the form stays open: pick a different name, or close it and **Edit** the existing character. Nothing is overwritten. The same applies to the Character Build tab without **Update Existing**.
- MAIN CAST = `type: main`. SUPPORTING = everything else (`temporary`).
- Card meta "Ch. A — B" = first appeared / last seen chapter.

### 5.4 Locations

Same as characters: the **Scene Build** tab, sidebar cards, **+ New Location** (a taken name shows the same "already exists" error). Locations marked as background in a chapter are not sent to the writer.

### 5.5 World

- **World Build tab:** add any aspect in free text. Lists (genres, professions, hierarchy, factions) are appended; text fields are replaced when the AI returns a value.
- **🌐 World Settings** (right sidebar or `Alt+W`): edit every field directly. Tag fields: type and press **Enter** or **,**. **Backspace** on an empty field removes the last tag, **×** removes a specific one.

### 5.6 Reading and exporting

- Click a **HISTORY** pill to load a chapter. **⛶ Full View** opens a distraction-free reader with featured characters/locations (shown as slugs).
- **📤 Export → .txt / .md** downloads the whole novel in chapter order. A copy is also written into `data/`.

### 5.7 Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Enter` (in plot box) | Generate chapter |
| `Alt+G` | Generate chapter |
| `Alt+N` | New character modal |
| `Alt+S` | Settings modal |
| `Alt+W` | World settings modal |
| `Escape` | Close the open modal |
| `Enter` / `,` in a tag field | Add tag |

The `Alt` shortcuts work with Caps Lock on or Shift held (since plan 013, KI-032).

## 6. Backup, reset and multiple novels

- **Everything is in `data/`.** Back up by copying the folder while the server is stopped.
- **Start a new novel:** stop the server, move `data/` somewhere else (e.g. `data_my_first_novel/`), and start again. The managers recreate empty folders and the defaults.
- **Switch novels:** stop the server, swap folder names, start again.
- **Edit by hand:** the JSON files can be edited with any editor (keep them valid JSON and keep the required fields `name`/`slug`/`chapter_number`). Invalid files are hidden from the UI without any error.

## 7. Developer quick reference

| Task | How |
|---|---|
| Run with reload | `cd app/backend` then `python main.py` |
| API docs | http://127.0.0.1:8000/docs |
| Syntax-check backend | `python -m py_compile app/backend/main.py app/backend/models.py app/backend/agents/*.py app/backend/managers/*.py app/backend/pipeline/*.py` |
| Syntax-check frontend | `node --check app/frontend/app.js` |
| Watch generation events raw | `curl -N -X POST http://127.0.0.1:8000/api/generate-chapter -H "Content-Type: application/json" -d '{"plot":"…"}'` |
| Frontend changes | Just reload the browser (no build step; `index.html` is re-read on each request) |
| Tests | None exist yet (KI-025) |
