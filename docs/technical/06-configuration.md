# 06 — Configuration Reference

> **Applies to:** v1.0.0. **Last verified against code:** 2026-11-22.
> v1.0.0 has **no configuration file and reads no environment variables of its own**. Configuration is either **runtime** (stored in `data/novel_meta.json`, edited in the UI) or **hard-coded** in source. This page lists every knob and where it lives.

## 1. Runtime configuration (UI → `data/novel_meta.json`)

| Setting | UI location | Default | Effect |
|---|---|---|---|
| Writer model | ⚙ Settings → Writer Model | `gemma3:12b` | Ollama tag used for step 6 (chapter prose) |
| Specialist model | ⚙ Settings → Specialist Model | `phi4-mini:3.8b` | Ollama tag used for steps 1–5, 7 and all refine endpoints |
| Novel title | Header (click) or Settings | `Untitled Novel` | Header, page title, export title and filename |
| Genre / Author | Settings | "" | Stored only |

Models must already be pulled in Ollama (or pulled from the Settings model browser). The model name is read from disk **at the start of each request**, so changes apply to the next generation without a restart.

World settings (`data/world_settings.json`) are content, not configuration, but they directly shape every prompt. See [05 §2.4](05-data-model-and-storage.md#24-worldsettings--dataworld_settingsjson).

## 2. Hard-coded configuration

### 2.1 Network / process

| Setting | Value | Location(s) | To change it |
|---|---|---|---|
| Backend bind host | `127.0.0.1` | `app/start.bat:58` (`--host`), `main.py:397` | Edit both. Do **not** bind `0.0.0.0` without adding auth (no auth + CORS `*`). |
| Backend port | `8000` | `app/start.bat:13` (`PORT`), `main.py:397`, **`app/frontend/app.js:6`** (`API`) | Change **all three** together. The frontend talks to an absolute URL. |
| Frontend API base | `http://127.0.0.1:8000/api` | `app.js:6` | Opening the UI as `http://localhost:8000` makes API calls cross-origin (they work only because CORS is `*`). |
| Ollama base URL (model list / pull) | `http://localhost:11434` | `main.py:243`, `main.py:280` | Edit the source. |
| Ollama base URL (chat / generation) | ollama-python default (`http://localhost:11434`; the library honours the `OLLAMA_HOST` env var) | `specialist.py` / `writer.py` use library defaults | Setting `OLLAMA_HOST` moves **generation only**, not the model list or pull (KI-033). |
| CORS | `allow_origins=["*"]`, all methods/headers | `main.py:32-37` | Restrict to `http://127.0.0.1:8000` if hardening. |
| Uvicorn reload | off via `app/start.bat`; on via `python main.py` | `app/start.bat:58`, `main.py:397` | — |
| Health polling (launcher) | every 2 s, 15 tries | `app/start.bat:64-72` | — |

### 2.2 LLM parameters

| Parameter | Specialist | Writer | Location |
|---|---|---|---|
| `num_ctx` (context window, tokens) | 8192 | 32768 | `specialist.py:52`, `writer.py:57` |
| `temperature` | 0.1 | 0.8 | same |
| `top_p` | (Ollama default) | 0.9 | `writer.py:57` |
| `keep_alive` | `-1` (keep loaded) by default. `0` in `predict_updates` and `post_write_update` | `300` s | `specialist.py:41,232,268`, `writer.py:56` |
| Streaming | no | yes | — |
| JSON mode (`format="json"`) | **not used** | n/a | — |

> `num_ctx 32768` on a 12B model can need much more VRAM than the model weights alone. If you hit out-of-memory errors, lowering this is the first knob to try, together with picking a smaller model.

### 2.3 Prompt / content knobs

| Knob | Value | Location |
|---|---|---|
| Target chapter length | ~2000 words (stated twice) | `writer.py:20`, `writer.py:42` |
| Narrative perspective | third-person limited unless world settings say otherwise | `writer.py:21` |
| Writer persona and style rules | `WRITER_SYSTEM` | `writer.py:8-23` |
| Tone vocabulary | action/dark/romantic/comedic/tense/mysterious/epic | `specialist.py:76` |
| Previous-chapter excerpt length | last **400 words** | `context_builder.py:85-86` |
| Chapter tier windows | N−1 full_text · N−2..4 full · N−5..8 short · older micro | `chapter_pipeline.py:139-151` (+ duplicated in the `select_context` prompt, `specialist.py:197-201`) |
| Compressed character fallback | `personality[:80]` | `context_builder.py:59` |
| Post-write input truncation | first **3000 chars** of the chapter | `specialist.py:245` |
| Summary lengths requested | micro 15–20 words, short 80–100, full 180–220 | `specialist.py:250-252` |

### 2.4 Model catalogue (shown in Settings)

`RECOMMENDED_MODELS` (`main.py:227-234`):

| Model | Size (as listed) | Quality | Note |
|---|---|---|---|
| `gemma3:12b` | ~7 GB | Best | Recommended writer |
| `llama3.1:8b` | ~5 GB | Great | Fast, good quality |
| `mistral-nemo:12b` | ~7 GB | Great | Stable, no repetition |
| `phi4-mini:3.8b` | ~2.3 GB | Good | Specialist + low-end writer |
| `qwen2.5:7b` | ~4.7 GB | Great | Creative writing |
| `deepseek-r1:7b` | ~4.7 GB | Good | Strong reasoning |

README VRAM guidance: `gemma3:12b` / `mistral-nemo:12b` ≈ 8 GB, `llama3.1:8b` ≈ 6 GB, `phi4-mini:3.8b` ≈ 3 GB.
Low-VRAM suggestion from the README: writer `llama3.1:8b` + specialist `phi4-mini:3.8b`.

> ⚠ Reasoning models such as `deepseek-r1` emit `<think>…</think>` text. As a **specialist** this can break JSON extraction. As a **writer**, the thinking text would be streamed into the chapter. Not handled in v1.0.0.

### 2.5 Frontend constants

| Constant | Value | Location |
|---|---|---|
| Toast default duration | 4000 ms (8000 ms for the connection error) | `app.js:1276`, `app.js:1418` |
| Connection check timeout | 3000 ms | `app.js:1416` |
| Sidebar reload delay after a new entity | 300 ms | `app.js:472,478` |
| Pipeline fade after completion | 2000 ms → opacity 0.4 | `app.js:657-659` |
| Refine status auto-clear | 5000 ms | `app.js:1555` etc. |
| Frontend fallback meta (when the backend is unreachable) | writer `gemma3:12b`, **specialist `gemma3:12b`** (differs from the backend default) | `app.js:166-173`, `app.js:1023-1024` |

### 2.6 Launcher (`app/start.bat`)

| Variable | Value |
|---|---|
| `BACKEND_DIR` | `%~dp0backend` |
| `PORT` | `8000` |
| `REQ_FILE` | `%~dp0requirements.txt` |
| Python detection order | `py`, then `python` |
| Dependency probe | `python -c "import fastapi"` only |
| Window title | `NovelForge AI` (launcher), `NovelForge-Backend` (server, minimised) |

## 3. Dependencies (`app/requirements.txt`)

| Package | Pinned | Actually required? | Notes |
|---|---|---|---|
| fastapi | 0.111.0 | yes | Works with much newer versions (0.141.1 observed). |
| uvicorn[standard] | 0.30.1 | yes | |
| ollama | 0.3.3 | yes | ⚠ The code needs **≥ 0.4** (attribute-style responses, KI-004). |
| pydantic | 2.7.1 | yes (v2 API) | 2.7.1 has no wheels for Python ≥ 3.13; pip would try to build from source. |
| aiofiles | 23.2.1 | no | Not imported. |
| python-multipart | 0.0.9 | no | No form/file uploads. |
| httpx | — (missing) | **yes** (imported in `main.py`) | Only present as a transitive dependency of `ollama`. |

A future "config" improvement (not implemented) would move host/port/Ollama URL/LLM parameters into a single settings module, using environment variables or a `config.json`. If you implement it, update this page and the doc-impact matrix in `docs/ai/RULES.md`.
