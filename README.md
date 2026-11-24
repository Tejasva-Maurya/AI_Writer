# ✦ NovelForge AI — Local Light Novel Writer

An AI-powered light-novel writing assistant that runs on your own machine through local LLMs (Ollama). Describe what happens in a chapter, and a multi-step AI pipeline writes it, keeping your characters, locations and world consistent.

## Where things live

This repository has **three areas**. Open the one that matches your task:

| Folder | What's inside | Open it when you want to… |
|---|---|---|
| **[`app/`](app/)** | **The application**: `backend/` (Python/FastAPI), `frontend/` (HTML/CSS/JS), `start.bat` (launcher), `requirements.txt` | run the tool, fix a bug, add a feature |
| **[`data/`](data/)** | **Your novel**: `characters/`, `scenes/`, `chapters/`, `novel_meta.json`, `world_settings.json` | look at or back up your story data |
| **[`docs/`](docs/README.md)** | **Supporting documents**: user guide, technical docs, changelog, AI rules, development plans and project memory | learn how the tool works, read the history, plan development |

```
AI_Writer/
├── app/        ← the application (code + launcher)
├── data/       ← your novel (written by the app)
├── docs/       ← documentation, changelog, plans, AI memory
├── .claude/    ← Claude Code settings + automation hooks (tool config, must stay here)
├── CLAUDE.md   ← loads the AI rules from docs/ai/RULES.md (must stay here)
└── AGENTS.md   ← pointer for other AI coding tools (must stay here)
```

## Quick start

1. Install **Python 3.11+** and **[Ollama](https://ollama.com)**, then pull the default models:
   ```bash
   ollama pull gemma3:12b
   ```
   ```bash
   ollama pull phi4-mini:3.8b
   ```
2. **Windows:** double-click **`app/start.bat`**. It installs dependencies, starts the server and opens `http://127.0.0.1:8000`.
   **Manually / other OS:** `cd app/backend`, then `python -m uvicorn main:app --host 127.0.0.1 --port 8000`.
3. Write a plot in the **Plot Writing** tab and press **▶ Generate Chapter**.

> ⚠ Read [docs/technical/09-known-issues-and-tech-debt.md](docs/technical/09-known-issues-and-tech-debt.md) first. v1.0.0 has some verified defects, with workarounds (dependency setup, manual character save, World Build).

## Documentation

| Start here | |
|---|---|
| [docs/README.md](docs/README.md) | Map of all documentation |
| [docs/user-guide.md](docs/user-guide.md) | Full end-user guide: setup, models, usage, shortcuts, troubleshooting |
| [docs/technical/](docs/technical/) | Architecture, workflows, low-level design, API, data model, configuration, FAQ, known issues |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Version history |
| [docs/ai/](docs/ai/README.md) | Rules for AI coding assistants, numbered development plans, project memory |

## License

For personal creative use. The AI models are governed by their own licenses (Llama, Gemma, Mistral, Phi).
