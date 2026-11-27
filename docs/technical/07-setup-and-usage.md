# 07 — Setup & Usage Guide

> **Applies to:** v2.0.0 + [Unreleased] (plan 019: draft review, @-mentions, prompt reuse; §7 test list: plans 020, 022, 023, 024, 025; plan 023: a chapter that stops halfway is kept; plan 024: ⟳ Regenerate; plan 025: older versions; plan 026: §3 localhost note, link to the Ollama test guide). **Last verified against code:** 2026-11-27.
> For known defects that affect individual steps, see [09 — Known Issues](09-known-issues-and-tech-debt.md). Workarounds are noted inline with ⚠.

**Where things are:** the tool lives in **`app/`** (launcher `app/start.bat`, code in `app/backend/` and `app/frontend/`). Your novel lives in **`data/`**. Documentation lives in **`docs/`**.

## 1. Prerequisites

| Requirement | Details |
|---|---|
| OS | Windows 10/11 for `app/start.bat`. The backend also runs on macOS/Linux with the manual steps below. |
| Python | 3.11+ (per the user guide). Developed on 3.13 and seen on 3.14. Tick **"Add Python to PATH"** when installing. |
| Ollama | Install from https://ollama.com. The Ollama service must be running (tray icon or `ollama serve`). It listens on `127.0.0.1:11434`. To use another address (e.g. Ollama on another machine), set `OLLAMA_HOST` before starting the app; generation, the model list and pulls all use it. |
| Hardware | A GPU with ≥ 8 GB VRAM for the default `gemma3:12b` writer. ≈ 3–6 GB works with smaller models (see [06 §2.4](06-configuration.md#24-model-catalogue-shown-in-settings)). CPU-only works but is slow. |
| Disk | Several GB per model. |
| Browser | Any modern Chromium/Firefox/Edge (uses `fetch` streaming and `AbortSignal.timeout`). |
| Internet | Needed once to install packages and pull models. After that the app runs fully offline: the UI fonts are bundled (plan 014). |

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

Then open **http://127.0.0.1:8000** (`http://localhost:8000` works too: the page calls the API at its own address, `/api`, and the server accepts both host names since plan 007). To test with real models, follow [the Ollama test guide](../testing-with-ollama.md).

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
│  SUPPORTING  │  Chapter output / draft editor ⛶ Full View │                │
│  cards…      │  📚 HISTORY  [Ch.1][Ch.2]…                  │ + New Location │
│ + New Char.  │                                            │ 🌐 World Sett. │
└──────────────┴──────────────────────────────────┴────────────────┘
```
Colour code: **purple** = characters, **gold** = locations, **mint** = world.

**Narrow windows** (since plan 017, KI-035):
- **Below 1200 px** the sidebars get narrower.
- **Below 900 px** the page becomes one scrolling column: the writer first, then Characters, then Locations. Each list scrolls inside its own card.
- **Below 600 px** the header buttons show only their icons (hover for the name).

### 5.2 Writing chapters (Plot Writing tab)

1. The label shows **CHAPTER N** (N = highest existing chapter number + 1, the number the backend will use).
2. Describe *what happens*, not prose. Name characters and places explicitly. That is how the pipeline finds them in the database or creates new profiles. Example:
   > *Xiao Fan discovers a cultivation technique hidden in the Azure Cave. Practising it causes a spiritual explosion that draws Elder Wu and two inner disciples to investigate.*
3. **@-mentions** (plan 019): type `@` and a few letters to pick an existing character (👤) or location (📍). **↑/↓** choose, **Enter** or **Tab** insert the exact name, **Esc** closes. A picked entity is sure to reach the writer with its full profile, even if the AI would have missed it.
4. Press **▶ Generate Chapter**, `Ctrl+Enter` (in the textarea) or `Alt+G` (anywhere).
5. Watch the steps: Analyze Plot → Extract Entities → Build Profiles → Optimize Context → Prepare Model → Write Chapter (text streams in). Newly discovered characters/locations pop up as tags and toasts, and they appear in the sidebars. A yellow ⚠ toast means a non-fatal problem in a step (e.g. a profile that couldn't be saved); the chapter still completes ([08 A13b](08-faq-and-troubleshooting.md)).
6. **Review the draft** (the default since plan 019): the chapter opens in an editor, marked **Draft · Chapter N**, and step 7 waits.
   - **Edit** the text directly. It is saved automatically about a second after you stop typing ("Saved"), and it is still there after a reload or a restart.
   - **Rewrite with AI:** select a passage, type how it should change (e.g. *make the dialogue angrier*), press **Enter** or **✨ Rewrite selection**. Only the selection is replaced, and the new text stays selected. **↶ Undo rewrite** brings the old text back.
   - **Title:** optional; leave it empty to let the AI suggest one.
   - **✓ Approve & save** runs step 7 (summary, profile updates) and saves the chapter to **HISTORY**; the plot box clears. If the summary fails (e.g. Ollama stopped), the draft stays: approve again later.
   - **🗑 Discard** deletes the draft. If the AI created new characters or locations for it, you are asked whether to delete them too. The plot stays in the box, so you can adjust it and generate again.
   - Only one draft at a time: **Generate** with a draft waiting first asks to discard it.
7. **Without review** (⚙ Settings → untick **Review each chapter as a draft before saving**): step 7 runs right after writing and the chapter is saved at once, as before plan 019. If step 7 fails, the chapter is kept as a draft anyway (KI-041).
8. To stop a run, press **✕ Cancel** next to the Generate button (shown only while generating). The steps reset and a "Generation cancelled" toast appears. Cancel while the text is being written discards it. A cancel during the summary keeps the written chapter as a draft. Character/location profiles created in step 3 stay.
9. **A chapter that stops halfway is kept** (plan 023):
   - If the writer fails mid-chapter (Ollama stops, out of memory), or you close or reload the tab while it writes, the text written so far is kept as a draft.
   - After a failure it opens at once, with a "words written so far are kept" message. After a closed tab it opens on your next visit.
   - Finish it by hand or with AI rewrites and approve it, or discard it. Only **✕ Cancel** throws it away.
10. **Regenerate a saved chapter** (plan 024): open it from the history bar and press **⟳ Regenerate** in its header, or **⟳ Regenerate this chapter** in the Full View.
   - Its prompt goes into the plot box. A notice says which chapter you are regenerating, and the button reads **Regenerate Chapter N**. Change the prompt if you like, then press it. **✕ New chapter instead** leaves this mode.
   - The new version **always opens as a draft**, even with review turned off. The saved chapter stays as it is until you approve the draft; **🗑 Discard** keeps the old one.
   - **✓ Approve & save** asks before it replaces the saved chapter. Profiles keep what later chapters established (plan 022).
   - The replaced text is **kept as an older version** (plan 025): the chapter's Full View lists **Older versions (N)**, the newest 5. **Read** shows one (with **← Current version** to go back), **↺ Restore** makes it the saved chapter again (the current text then becomes an older version, so nothing is lost; refused while the AI works), and **🗑 Delete** removes it for good. A 6th regeneration deletes the oldest version. Older versions are not exported.

Tips:
- First generation is slow while models load into VRAM. Within 5 minutes the writer stays warm.
- One chapter is generated at a time. If another tab (or a script) is already generating, **Generate** shows "A chapter is already being generated. Wait for it to finish or cancel it." Closing the tab that started a generation also stops it, and keeps what was written so far as a draft (plan 023).
- If the plot clearly spans several chapters, you'll see a notice. Only the current chapter is written. Split the plot yourself.
- Chapter quality depends heavily on the summaries of earlier chapters. Use a capable specialist model if summaries look poor.
- To redo a chapter before it is saved, discard its draft and generate again (the plot stays in the box). To redo a saved chapter, use **⟳ Regenerate** (step 10); its old text stays available under **Older versions**. There is no "delete chapter" button: to remove the last saved chapter, delete `data/chapters/NNN.json` while the server runs and reload the page.

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

- Click a **HISTORY** pill to load a chapter (while a draft waits, the chapter opens in the Full View instead, so the draft stays put). **⛶ Full View** opens a distraction-free reader with featured characters/locations (shown as slugs). In draft mode it shows the draft.
- **Prompt used** (plan 019): the Full View has a collapsed box with the plot the chapter was written from. **↺ Use this prompt again** copies it into the plot box.
- **📤 Export → .txt / .md** downloads the whole novel in chapter order. Nothing is written into `data/` (since plan 015), and any title works: characters not allowed in file names become `_` in the download name.

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
| `@` in the plot box, then `↑`/`↓`, `Enter`/`Tab`, `Esc` | Pick a character or location to insert (plan 019) |
| `Enter` in the draft's rewrite instruction box | Rewrite the selected draft text (plan 019) |

The `Alt` shortcuts work with Caps Lock on or Shift held (since plan 013, KI-032).

## 6. Backup, reset and multiple novels

- **Everything is in `data/`.** Back up by copying the folder while the server is stopped. A chapter waiting for review is `data/draft.json` (plan 019); it is part of the backup too.
- **Git does not back it up.** `data/` is git-ignored since plan 017 (KI-030), so a commit or a fresh clone never includes your novel. Keep your own copies.
- **Start a new novel:** stop the server, move `data/` somewhere else (e.g. `data_my_first_novel/`), and start again. The managers recreate empty folders and the defaults.
- **Switch novels:** stop the server, swap folder names, start again.
- **Edit by hand:** the JSON files can be edited with any editor (keep them valid JSON and keep the required fields `name`/`slug`/`chapter_number`). A file that can't be read is left out of the UI, and the server console logs a warning naming it (since plan 016).

## 7. Developer quick reference

| Task | How |
|---|---|
| Run with reload | `cd app/backend` then `python main.py` |
| API docs | http://127.0.0.1:8000/docs |
| Syntax-check backend | `python -m py_compile app/backend/main.py app/backend/models.py app/backend/agents/*.py app/backend/managers/*.py app/backend/pipeline/*.py` |
| Syntax-check frontend | `node --check app/frontend/app.js` |
| Watch generation events raw | `curl -N -X POST http://127.0.0.1:8000/api/generate-chapter -H "Content-Type: application/json" -d '{"plot":"…"}'` |
| Frontend changes | Just reload the browser (no build step; `index.html` is re-read on each request) |
| Tests and lint | See below; CI runs the same on every push (`.github/workflows/ci.yml`) |

### Tests and lint

Since plan 016 (KI-025). From the repository root, once:

```bash
py -m pip install -r app/requirements-dev.txt
```

Then:

```bash
py -m pytest app/tests
py -m ruff check app
```

- **What the tests cover:** they need no Ollama (a fake `ollama` module records the calls) and never touch `data/`. Every manager is pointed at a temp folder, and the run fails if the real `data/` changed (also a file created and deleted again, plan 019).
  - `test_api.py`: CRUD, slugs and host checks, export, model list and pull.
  - `test_storage.py`: atomic writes and logged skips.
  - `test_pipeline.py`: a full generation with the fake, including the `keep_alive` choreography, review mode, a failed step 7 keeping the draft (KI-041) and @-tags.
  - `test_draft.py`: the draft routes (edit, discard, rewrite, approve), the one-job-at-a-time guard and the `review_drafts` setting (plan 019).
  - `test_refine.py`: the Build-tab refine routes, their place in the one-job-at-a-time guard, and edits made during an AI call (plan 020, KI-042).
  - `test_regenerate.py`: regenerating an earlier chapter, i.e. the writer's prompt with later chapters and no profile rollback (plan 022, KI-043/KI-044), and chapter numbers below 1 rejected (plan 024, KI-045).
  - `test_versions.py`: older chapter versions, i.e. keeping the replaced text, the limit of 5, read, delete and restore, the 409 during an AI job, and a failed copy keeping the draft (plan 025).
  - `test_partial.py`: a chapter that stops halfway, i.e. a writer failure or a closed tab keeps the text as a draft, and ✕ Cancel discards it (plan 023).
  - `test_helpers.py`: Ollama address parsing, export names, model coercion.
- **Lint:** ruff checks for real bugs (undefined names, unused imports, syntax that the minimum Python 3.11 can't parse); the rules are pinned in `app/pyproject.toml`.
- **CI** (`.github/workflows/ci.yml`) runs lint, tests and `node --check app/frontend/app.js` on Ubuntu and Windows with Python 3.11 and 3.14.
