# ✦ NovelForge AI — User Guide

> End-user guide (this was the original root README; the root [README](../README.md) is now a short map of the repository). Technical details: [docs map](README.md). Known defects and workarounds: [technical/09](technical/09-known-issues-and-tech-debt.md).

> **An AI-powered, fully offline light novel writing assistant** that runs entirely on your machine using local LLMs through Ollama. Write immersive chapters, manage characters and locations, and build your world — all driven by open-source AI.

---

## Overview

NovelForge AI is a complete creative writing pipeline for light novels. You describe what happens in a chapter, and the AI handles everything else: setting the scene, writing dialogue, building emotions, and maintaining continuity with your existing characters and world.

**Key Features:**
- 🧠 **7-Step Generation Pipeline** — Plot analysis → entity extraction → character profiling → context optimization → model priming → chapter writing → summarization
- 👤 **Persistent Character Profiles** — Automatically discovers new characters, tracks appearance chapters, maintains backstory and relationships
- 🗺️ **Location Management** — Tracks all scenes, atmospheres, and inhabitants
- 🌐 **World Settings** — Magic systems, cultivation levels, factions, lore
- 📡 **Real-time Streaming** — Watch the chapter write itself word by word
- ✏️ **Draft Review** — Edit the new chapter, let the AI rewrite any passage you select, then approve it (or discard it)
- @ **Mentions** — Type `@` in the plot to insert a character or location by its exact name and make sure the AI uses its profile
- 📚 **Chapter History** — Navigate and review any previously written chapter, with the prompt it was written from
- 📤 **Export** — Download your entire novel as `.txt` or `.md`

---

## Prerequisites

### 1. Python 3.11+
Download from [python.org](https://www.python.org/downloads/). Make sure to check **"Add Python to PATH"** during installation.

Verify with:
```cmd
python --version
```

### 2. Ollama (Local LLM Runtime)
Download from [ollama.com](https://ollama.com/).

After installation, verify:
```cmd
ollama --version
```

---

## Setup

### Step 1 — Clone or Download the Project
```
AI_Writer/
├── app/                 ← the application
│   ├── backend/         (main.py, …)
│   ├── frontend/        (index.html, style.css, app.js)
│   ├── requirements.txt
│   └── start.bat        ← double-click to launch
├── data/                ← your novel (created by the app; never committed to git)
├── docs/                ← this guide, technical docs, changelog
└── README.md
```

### Step 2 — Pull AI Models with Ollama

Open a terminal and pull your preferred models:

```cmd
REM Recommended writer model (best quality)
ollama pull gemma3:12b

REM Recommended specialist model (the default: small and fast, for the JSON analysis steps)
ollama pull phi4-mini:3.8b

REM Or other writers:
ollama pull llama3.1:8b
ollama pull mistral-nemo:12b
```

> **Note:** Models will download several GB each. Keep them running in the background — Ollama handles model management automatically.

### Step 3 — Launch NovelForge AI

Simply **double-click `app/start.bat`** (inside the `app` folder).

The launcher will:
1. Verify Python is installed
2. Check the backend dependencies (`app/requirements.txt`) and install or update them if anything is missing or too old. The first launch needs an internet connection for this. If the install fails, the launcher stops and shows the command to run by hand.
3. Start the FastAPI backend server on port 8000
4. Open your browser to `http://127.0.0.1:8000`

---

## Model Recommendations

| Model | VRAM Required | Best For | Speed |
|-------|--------------|----------|-------|
| `gemma3:12b` | ~8 GB | Narrative quality, emotional depth | Medium |
| `mistral-nemo:12b` | ~8 GB | Creative writing, analytical tasks | Medium |
| `llama3.1:8b` | ~6 GB | Fast drafts, general writing | Fast |
| `phi4-mini:3.8b` | ~3 GB | Low-VRAM systems | Very Fast |

**Recommended setup:** the defaults, `gemma3:12b` as the Writer and `phi4-mini:3.8b` as the Specialist. The specialist only does short analysis and summary tasks, so a small model is enough and leaves VRAM for the writer. A larger specialist (e.g. `gemma3:12b`) can give better chapter summaries, at the cost of speed and VRAM. If you have limited VRAM, use `llama3.1:8b` for writing and keep `phi4-mini:3.8b` for the specialist.

---

## Usage Guide

The app is laid out for a desktop browser window. In a narrow window (below about 900 px) it becomes one scrolling column: the writing area first, then the character and location lists.

### Starting a New Novel

1. Click the **novel title** in the header to edit it inline
2. Click **⚙ Settings** to configure your novel metadata (title, genre, author) and select AI models
3. Click **🌐 World Settings** (right sidebar) to set up your world, magic system, and lore
4. Optionally add characters and locations manually using the **+ New Character** / **+ New Location** buttons

### Writing Chapters

1. In the center **Plot Input** area, describe what happens in the next chapter
   - Be descriptive but don't worry about prose — the AI handles that
   - Example: *"Xiao Fan discovers a mysterious cultivation technique hidden in the cave. He attempts to practice it, causing a spiritual energy explosion that attracts the attention of the sect elders."*
   - **Type `@`** to mention an existing character or location: a list appears as you type (any language). Use **↑/↓** and **Enter** (or click) to insert the exact name. Mentioned characters and locations always reach the AI with their full profile.
2. Click **▶ Generate Chapter** (or press **Ctrl+Enter**)
3. Watch the pipeline animate as the AI:
   - Analyzes your plot
   - Extracts character and location references
   - Creates/updates character profiles
   - Optimizes the context window
   - Loads the specialist model
   - Writes the chapter (you'll see text appear in real time)
4. **Review the draft.** The chapter opens as an editable **Draft**; nothing is final yet.
   - Fix anything by typing in the text. Your edits are saved automatically, so the draft is still there if you close the tab or restart.
   - To have the AI redo a part: **select** it, type what should change (e.g. *"make the dialogue angrier"*), and press **Enter** or **✨ Rewrite selection**. Not happy? **↶ Undo rewrite**.
   - Optionally type a title (or leave it empty and the AI suggests one).
   - Click **✓ Approve & save**. The AI now summarizes the chapter for future continuity, updates the character profiles, and adds it to the history.
   - Or click **🗑 Discard** to throw the draft away and try again with the same plot. You can also delete any characters or locations the AI created for it.
5. Use **⛶ Full View** to open the chapter (or the draft) in a distraction-free reading modal
6. Changed your mind mid-run? Click **✕ Cancel** next to the Generate button. The run stops and nothing is saved (new character/location profiles already created stay). One chapter is generated at a time, so a second tab gets "A chapter is already being generated" until the first finishes or is cancelled.
7. Prefer the old one-click flow? In **⚙ Settings**, untick **Review each chapter as a draft before saving**: chapters are then summarized and saved right after writing.

### Managing Characters

- Characters are automatically created when first mentioned in generated chapters
- Click any character card to view their full profile
- Hover over a card to reveal **Edit** and **Delete** buttons
- **MAIN CAST** = characters with `type: main`
- **SUPPORTING** = temporary/supporting characters

### Managing Locations

- Locations are automatically discovered during generation
- Right sidebar shows all known locations
- Click a location to view its full profile (atmosphere, textures, inhabitants, significance)

### Chapter History

- The bottom bar shows all generated chapters as clickable pills
- Click any chapter pill to load and display it
- The currently active chapter is highlighted in purple
- In **⛶ Full View**, open **Prompt used** to see the plot you wrote for that chapter, and click **↺ Use this prompt again** to copy it back into the plot box

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Generate chapter (from plot textarea) |
| `Alt+G` | Generate chapter (anywhere) |
| `Alt+N` | New character |
| `Alt+S` | Open settings |
| `Alt+W` | Open world settings |
| `Escape` | Close open modal |
| `@` (in the plot box) | Mention a character or location: `↑`/`↓` to choose, `Enter`/`Tab` to insert, `Escape` to close |
| `Enter` (in the draft's rewrite box) | Rewrite the selected draft text with AI |

The `Alt` shortcuts also work with Caps Lock on.

### Exporting Your Novel

Click **📤 Export** in the top-right header:
- **Export as .txt** — Plain text, one chapter after another
- **Export as .md** — Markdown format with headings and formatting

---

## Data Structure

The backend stores all data as plain JSON files under `data/` (no database). See [technical/05-data-model-and-storage.md](technical/05-data-model-and-storage.md) for the full schema. Here's what's tracked:

> **Back up `data/` yourself.** Your novel stays on your machine: git ignores `data/`, so a commit, a push or a fresh clone never includes it. To keep a backup, copy the folder while the server is stopped.

### Character Fields
| Field | Description |
|-------|-------------|
| `name` | Full character name |
| `type` | `main` or `temporary` |
| `age` | Age or "Unknown" |
| `appearance` | Physical description |
| `personality` | Character traits |
| `speech_style` | How they speak |
| `abilities` | List of powers/skills |
| `cultivation_level` | Power rank in the system |
| `backstory` | Origin and history |
| `relationships` | Map of other characters → relationship type |
| `habits` | Behavioral patterns |
| `arc_notes` | Writer notes for character development |
| `micro_summary` | One-line summary for AI context optimization |
| `first_appeared_chapter` | Chapter number of first appearance |
| `last_seen_chapter` | Most recent chapter appearance |

### Scene/Location Fields
| Field | Description |
|-------|-------------|
| `name` | Location name |
| `scene_type` | Category (Mountain, Realm, City, etc.) |
| `description` | Full description |
| `atmosphere` | Mood and ambiance |
| `textures` | Sensory details |
| `known_inhabitants` | Characters who live/frequent this place |
| `significance` | Plot relevance |
| `micro_summary` | One-line for context optimization |

### World Settings
| Field | Description |
|-------|-------------|
| `world_name` | Name of the world/continent |
| `genre_tags` | Genre identifiers |
| `magic_system` | Description of how magic works |
| `cultivation_system` | Power leveling system |
| `professions` | Available character classes |
| `hierarchy_levels` | Power ranking levels (e.g., Qi Condensation, Foundation...) |
| `factions` | Major groups and sects |
| `rules_of_the_world` | Fundamental laws |
| `lore_notes` | Additional world lore |

---

## Troubleshooting

### "Cannot connect to backend" message
- Ensure `app/start.bat` was run and the backend window is open
- Check that port 8000 is not blocked by another application
- Try visiting `http://127.0.0.1:8000/api/novel-meta` directly in your browser

### Generation fails or hangs
- Ensure Ollama is running: `ollama list`
- Ensure your selected models are pulled: `ollama pull gemma3:12b`
- Check the backend terminal window for error messages
- The Ollama service must be running: look for it in the system tray or run `ollama serve`
- "A chapter is already being generated": another tab is still generating. Wait, or click **✕ Cancel** there
- "A draft of chapter N is waiting for review": approve or discard the draft first (Generate offers to discard it)
- A Build tab says "A chapter is already being generated" (or that a draft is being approved): AI jobs run one at a time, so the refine waits its turn. Try again when the chapter is done; nothing was changed. Likewise, Generate says "A profile is being refined with AI" for the few seconds a Build-tab refine runs
- "Summary failed … kept as a draft" or "Could not approve the draft": your chapter text is safe in the draft. Start Ollama (or pull the specialist model), then click **✓ Approve & save** again
- A model pull in **⚙ Settings** says "Pull failed: …": the message is Ollama's reason (e.g. a misspelt model name, or a network problem). Check the name and try again

### Out of memory / VRAM errors
- Switch to a smaller model in **⚙ Settings**
- Close other GPU-intensive applications
- `phi4-mini:3.8b` requires only ~3 GB VRAM

### Slow generation
- First generation is slower as the model loads into VRAM
- Subsequent chapters are faster as the model stays in memory
- Consider using `llama3.1:8b` for faster generation

---

## Architecture

```
AI_Writer/
├── app/                            THE APPLICATION
│   ├── backend/                    FastAPI server (Python) — run with app/backend/ as working directory
│   │   ├── main.py                 API routes, SSE streaming, static serving, model mgmt, refine, export
│   │   ├── models.py               Pydantic data models (also the on-disk JSON schema)
│   │   ├── agents/
│   │   │   ├── specialist.py       Small-model JSON tasks (analysis, entities, summaries, refine)
│   │   │   └── writer.py           Large-model streaming chapter writer
│   │   ├── managers/               JSON-file persistence (characters, scenes, chapters, world, meta)
│   │   └── pipeline/
│   │       ├── chapter_pipeline.py 7-step generation pipeline (emits SSE)
│   │       └── context_builder.py  Master prompt / tiered chapter memory
│   ├── frontend/                   Pure HTML/CSS/JS (no build step)
│   │   ├── index.html              Application shell
│   │   ├── style.css               Dark glass design system
│   │   ├── app.js                  All application logic
│   │   └── fonts/                  Bundled web fonts (no internet needed)
│   ├── requirements.txt            Python dependencies
│   └── start.bat                   Windows launcher
├── data/                           YOUR NOVEL (JSON files, created on demand; git-ignored)
│   ├── characters/{slug}.json
│   ├── scenes/{slug}.json
│   ├── chapters/{NNN}.json
│   ├── novel_meta.json
│   └── world_settings.json
└── docs/                           SUPPORTING DOCUMENTS (this guide, technical docs, changelog, AI workspace)
```

See [technical/01-overview-and-architecture.md](technical/01-overview-and-architecture.md) for diagrams and details.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [docs map](README.md) | Map of all documentation |
| [technical/](technical/01-overview-and-architecture.md) | Architecture, workflows, low-level design, API, data model, configuration, setup & usage, FAQ, known issues |
| [technical/09-known-issues-and-tech-debt.md](technical/09-known-issues-and-tech-debt.md) | Verified defects with workarounds. **Read this before relying on a feature** |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [ai/RULES.md](ai/RULES.md) | Rules for AI coding assistants (loaded via the root `CLAUDE.md`, pointed to by `AGENTS.md`) |
| [ai/](ai/README.md) | AI development workspace: numbered plans and project memory |

---

## License

This project is for personal creative use. The AI models are governed by their respective licenses (Llama, Gemma, Mistral, Phi).

---

*Made with ✦ by NovelForge AI*
