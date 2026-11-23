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
| Backend bind host | `127.0.0.1` | `app/start.bat:66` (`--host`), `main.py:478` | Edit both. Do **not** bind `0.0.0.0` without adding auth (there is no authentication; `TrustedHostMiddleware` would also reject other host names). |
| Backend port | `8000` | `app/start.bat:13` (`PORT`), `main.py:478` | Change **both** together. The frontend uses the relative `/api` (since plan 007), so it follows automatically. |
| Frontend API base | `/api` (same origin) | `app.js:6` | Works for `http://127.0.0.1:8000` and `http://localhost:8000` alike (KI-021, fixed in plan 007). |
| Ollama base URL (model list / pull) | `http://localhost:11434` | `main.py:281`, `main.py:319` | Edit the source. |
| Ollama base URL (chat / generation) | ollama-python default (`http://localhost:11434`; the library honours the `OLLAMA_HOST` env var) | `specialist.py` / `writer.py` use library defaults | Setting `OLLAMA_HOST` moves **generation only**, not the model list or pull (KI-033). |
| Allowed `Host` headers | `127.0.0.1`, `localhost` (any port) | `main.py:34` (`TrustedHostMiddleware`) | No CORS middleware: cross-origin browser calls are blocked (KI-010, plan 007). Add a host here only if you serve the UI under another local name. |
| Uvicorn reload | off via `app/start.bat`; on via `python main.py` | `app/start.bat:66`, `main.py:478` | — |
| Health polling (launcher) | every 2 s, 15 tries | `app/start.bat:72-80` | — |

### 2.2 LLM parameters

| Parameter | Specialist | Writer | Location |
|---|---|---|---|
| `num_ctx` (context window, tokens) | 8192 | 32768 | `specialist.py:53`, `writer.py:63` |
| `temperature` | 0.1 | 0.8 | same |
| `top_p` | (Ollama default) | 0.9 | `writer.py:63` |
| `keep_alive` | `-1` (keep loaded) by default. `0` in `unload` (step 5, no generation) and `post_write_update` | `300` s | `specialist.py:41,197,237`, `writer.py:62` |
| Streaming | no | yes | — |
| JSON mode (`format="json"`) | **on** for every specialist call (plan 009, KI-016) | not used (prose) | `specialist.py:52` |

> `num_ctx 32768` on a 12B model can need much more VRAM than the model weights alone. If you hit out-of-memory errors, lowering this is the first knob to try, together with picking a smaller model.

### 2.3 Prompt / content knobs

| Knob | Value | Location |
|---|---|---|
| Target chapter length | ~2000 words (stated twice) | `writer.py:23`, `writer.py:48` |
| Narrative perspective | third-person limited unless world settings say otherwise | `writer.py:24` |
| Writer persona and style rules | `WRITER_SYSTEM` | `writer.py:11-26` |
| Tone vocabulary | action/dark/romantic/comedic/tense/mysterious/epic | `specialist.py:77` |
| Previous-chapter excerpt length | last **400 words** | `context_builder.py:85-86` |
| Chapter tier windows | N−1 full_text · N−2..4 full · N−5..8 short · older micro | `chapter_pipeline.py:153-165` (the only copy since plan 008) |
| Compressed character fallback | `personality[:80]` | `context_builder.py:59` |
| Post-write chapter budget | whole chapter up to ~**5000 tokens** (estimate: ¼ per ASCII char, 1 per other char); longer chapters → opening 40 % + ending 60 % | `specialist.py:175` (`_chapter_excerpt`) |
| Summary lengths requested | micro 15–20 words, short 80–100, full 180–220 | `specialist.py:219-221` |

### 2.4 Model catalogue (shown in Settings)

`RECOMMENDED_MODELS` (`main.py:265-272`):

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
| Toast default duration | 4000 ms (8000 ms for the connection error) | `app.js:1326`, `app.js:1469` |
| Connection check timeout | 3000 ms | `app.js:1467` |
| Sidebar reload delay after a new entity | 300 ms | `app.js:481,482` |
| Pipeline fade after completion | 2000 ms → opacity 0.4 | `app.js:700-702` |
| Refine status auto-clear | 5000 ms | `app.js:1607` etc. |
| Frontend fallback meta (when the backend is unreachable) | writer `gemma3:12b`, **specialist `gemma3:12b`** (differs from the backend default) | `app.js:167-174` (`loadNovelMeta`; the second fallback, in `openSettingsModal`, was removed in plan 006) |

### 2.6 Launcher (`app/start.bat`)

| Variable | Value |
|---|---|
| `BACKEND_DIR` | `%~dp0backend` |
| `PORT` | `8000` |
| `REQ_FILE` | `%~dp0requirements.txt` |
| `DEP_CHECK` | Python one-liner run with `-c`: imports `fastapi, uvicorn, pydantic, httpx, ollama` and exits 1 when the installed `ollama` is older than 0.4 (`importlib.metadata.version`). |
| Python detection order | `py`, then `python` |
| Dependency probe | `DEP_CHECK`; on failure `pip install -r %REQ_FILE% -q`, then `DEP_CHECK` again; still failing → error, `pause`, `exit /b 1` (plan 005; v1.0.0 probed only `import fastapi`) |
| Window title | `NovelForge AI` (launcher), `NovelForge-Backend` (server, minimised) |

## 3. Dependencies (`app/requirements.txt`)

Lower bounds, not exact pins (KI-004, fixed in plan 005; policy in decision D-009). The file's header comment records the verified versions.

| Requirement | Why this bound | Verified 2026-11-22 (Python 3.14.5) |
|---|---|---|
| `fastapi>=0.111` | Oldest version the app was written against. | runs on 0.141.1; a fresh install resolves 0.165.0 |
| `uvicorn[standard]>=0.30` | As above. `[standard]` adds httptools, watchfiles and websockets (all have wheels for 3.14). | runs on 0.52.3; resolves 0.54.0 |
| `pydantic>=2.9,<3` | v2 API (`model_dump()`), and `ollama>=0.4` itself requires `pydantic>=2.9`. | runs on 2.13.4; resolves 2.14.4 |
| `httpx>=0.27` | Imported directly by `main.py` (model list and pull). Was missing in v1.0.0. | 0.28.1 |
| `ollama>=0.4,<1` | Typed responses (`response.message.content`) and `AsyncClient` with this signature exist from 0.4.0 (checked in the 0.4.0 and 0.6.3 sources). | runs on 0.6.3 (isolated `--target` install) |

Removed in plan 005: `aiofiles` (Starlette no longer uses it; the app ran without it) and `python-multipart` (only needed for form or file uploads, which the app does not have). A fresh `pip install --dry-run -r app/requirements.txt` on Python 3.14.5 resolves 23 packages, all as wheels (no compiler needed).

A future "config" improvement (not implemented) would move host/port/Ollama URL/LLM parameters into a single settings module, using environment variables or a `config.json`. If you implement it, update this page and the doc-impact matrix in `docs/ai/RULES.md`.
