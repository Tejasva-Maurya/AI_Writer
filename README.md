# ✦ NovelForge AI — Local Light Novel Writer

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
- 📚 **Chapter History** — Navigate and review any previously written chapter
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
├── backend/
│   ├── main.py
│   └── ...
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── start.bat
└── README.md
```

### Step 2 — Pull AI Models with Ollama

Open a terminal and pull your preferred models:

```cmd
REM Recommended writer model (best quality)
ollama pull gemma3:12b

REM Recommended specialist model
ollama pull gemma3:12b

REM Or lighter alternatives:
ollama pull llama3.1:8b
ollama pull mistral-nemo:12b
ollama pull phi4-mini:3.8b
```

> **Note:** Models will download several GB each. Keep them running in the background — Ollama handles model management automatically.

### Step 3 — Launch NovelForge AI

Simply **double-click `start.bat`** in the project root.

The launcher will:
1. Verify Python is installed
2. Install backend dependencies (`requirements.txt`)
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

**Recommended setup:** Use `gemma3:12b` for both Writer and Specialist models for best quality. If you have limited VRAM, use `llama3.1:8b` for writing and `phi4-mini:3.8b` for the specialist tasks.

---

## Usage Guide

### Starting a New Novel

1. Click the **novel title** in the header to edit it inline
2. Click **⚙ Settings** to configure your novel metadata (title, genre, author) and select AI models
3. Click **🌐 World Settings** (right sidebar) to set up your world, magic system, and lore
4. Optionally add characters and locations manually using the **+ New Character** / **+ New Location** buttons

### Writing Chapters

1. In the center **Plot Input** area, describe what happens in the next chapter
   - Be descriptive but don't worry about prose — the AI handles that
   - Example: *"Xiao Fan discovers a mysterious cultivation technique hidden in the cave. He attempts to practice it, causing a spiritual energy explosion that attracts the attention of the sect elders."*
2. Click **▶ Generate Chapter** (or press **Ctrl+Enter**)
3. Watch the 7-step pipeline animate as the AI:
   - Analyzes your plot
   - Extracts character and location references
   - Creates/updates character profiles
   - Optimizes the context window
   - Loads the specialist model
   - Writes the chapter (you'll see text appear in real time)
   - Summarizes for future continuity
4. When complete, the chapter appears below with word count
5. Use **⛶ Full View** to open the chapter in a distraction-free reading modal

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

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Generate chapter (from plot textarea) |
| `Alt+G` | Generate chapter (anywhere) |
| `Alt+N` | New character |
| `Alt+S` | Open settings |
| `Alt+W` | Open world settings |
| `Escape` | Close open modal |

### Exporting Your Novel

Click **📤 Export** in the top-right header:
- **Export as .txt** — Plain text, one chapter after another
- **Export as .md** — Markdown format with headings and formatting

---

## Data Structure

The backend stores all data in a local database. Here's what's tracked:

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
- Ensure `start.bat` was run and the backend window is open
- Check that port 8000 is not blocked by another application
- Try visiting `http://127.0.0.1:8000/api/novel-meta` directly in your browser

### Generation fails or hangs
- Ensure Ollama is running: `ollama list`
- Ensure your selected models are pulled: `ollama pull gemma3:12b`
- Check the backend terminal window for error messages
- The Ollama service must be running: look for it in the system tray or run `ollama serve`

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
├── backend/          FastAPI server (Python)
│   ├── main.py       API routes and SSE streaming
│   ├── models.py     Pydantic data models
│   ├── storage.py    JSON/SQLite persistence layer
│   ├── pipeline.py   7-step generation pipeline
│   └── ollama.py     Ollama API client
├── frontend/         Pure HTML/CSS/JS (no build step)
│   ├── index.html    Application shell
│   ├── style.css     Premium dark design system
│   └── app.js        All application logic
├── data/             Auto-created — your novel data
│   ├── characters/
│   ├── scenes/
│   ├── chapters/
│   └── world.json
├── requirements.txt  Python dependencies
└── start.bat         Windows launcher
```

---

## License

This project is for personal creative use. The AI models are governed by their respective licenses (Llama, Gemma, Mistral, Phi).

---

*Made with ✦ by NovelForge AI*
