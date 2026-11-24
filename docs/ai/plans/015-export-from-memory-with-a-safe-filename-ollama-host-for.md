---
id: 015
title: "Export from memory with a safe filename, OLLAMA_HOST for model list and pull (KI-017, KI-033)"
status: done
approved: 2026-11-24T11:54:24+05:30
session: 8e82db1f-b2c4-4901-8528-5594118a09fb
source_file: "C:\\Users\\2466921\\.claude\\plans\\drifting-questing-parnas.md"
sha256: 560511ee07e5fa118496926dc9b701476f43de9de8a060cf0b82cb3bb64765b6
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Export from memory with a safe filename, OLLAMA_HOST for model list and pull (KI-017, KI-033)

## Context
The user asked to fix KI-017 and KI-033 (both Low). Read this session:
- **KI-017:** `export_novel` (`main.py:233-255`) builds the text in memory, then writes it to `<repo>/data/{title}.{fmt}` and returns that file with `FileResponse`.
  - **Side effect:** every export leaves a file in the user's novel folder (e.g. `data/Untitled_Novel.txt`). It is the only code outside the managers that writes `data/` (RULES §3 lists it as the exception).
  - **Failure:** a title containing a character Windows forbids in filenames (`: ? * " < > |`) makes `write_text` fail, so the export returns 500.
  - The frontend just clicks `<a href="/api/export/{fmt}">` (`app.js:1166-1175`), so a server-side fix is enough.
- **KI-033:** the ollama-python client reads `OLLAMA_HOST` (`base_url=_parse_host(host or os.getenv('OLLAMA_HOST'))`, verified in 0.6.3; default `http://127.0.0.1:11434`).
  - `get_models` and `pull_model` hard-code `http://localhost:11434` (`main.py:287, 323`). With `OLLAMA_HOST` set, generation and Build use one server, while Settings lists and pulls models on another.
  - The Settings status line also hard-codes "Make sure it's running on localhost:11434" (`app.js:1749`).

**Done means:**
- Export downloads without writing anything to disk, for any title.
- The model list and pull go to the same Ollama as generation.
- An unreachable Ollama is reported with the address that was tried.

## Approach
1. **`main.py` export (KI-017):**
   - `_export_filename(title, fmt)`: spaces → `_` (as today); characters Windows forbids and control characters → `_`; trailing dots and spaces stripped; `novel` if no letter or digit is left.
   - `export_novel` returns `Response(content, media_type="text/plain" | "text/markdown")`; Starlette adds `charset=utf-8`.
   - The `Content-Disposition: attachment` header is built the way Starlette's `FileResponse` builds it: `filename="…"` for ASCII names, `filename*=utf-8''…` (percent-encoded) otherwise.
   - Nothing is written to `data/`; the `Path(...).parents[2] / "data"` line goes.
   - The route, the 400 for other formats and the body text are unchanged.
2. **`main.py` Ollama address (KI-033):**
   - `_ollama_base_url(host)`: a line-for-line port of ollama-python's `_parse_host`, so both resolve every form the same way:
     - defaults `127.0.0.1`/`11434`
     - `http` → `:80`, `https` → `:443`
     - IPv6 brackets, path kept
   - `OLLAMA_BASE_URL = _ollama_base_url(os.getenv("OLLAMA_HOST"))`, read once at startup.
   - `get_models` uses `f"{OLLAMA_BASE_URL}/api/tags"` and `pull_model` uses `f"{OLLAMA_BASE_URL}/api/pull"`.
   - `ollama_error` becomes `Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}`.
   - **Note:** with no `OLLAMA_HOST` the address changes from `localhost` to `127.0.0.1`. That is the client's default, and it avoids Windows trying `::1` first.
3. **`app.js:1749` (KI-033):** when Ollama isn't reachable, the status line shows `Ollama not reachable: ${data.ollama_error}` via `textContent` instead of the hard-coded address.

**Not touched:** the existing `data/Untitled_Novel.txt` left by earlier exports is user data (RULES §5). It stays, and the user is told it can be deleted.

## Contract / data impact
- **API:**
  - `GET /api/export/{fmt}`: the same route, status codes, body and attachment download. It no longer creates a file, and it succeeds for any title (500 before for forbidden characters).
  - `GET /api/models`: the `ollama_error` text now includes the address.
- **No other change:** no SSE change, no `data/` schema change, no new dependency.
- **Configuration:** the backend now honours `OLLAMA_HOST` for the model list and pull (it already did for generation).

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-017 and KI-033 → Fixed [plan 015]; update the counts.
- **`docs/technical/04`:** export (no file, filename rules) and `/api/models` (`OLLAMA_HOST`, the error text).
- **`docs/technical/02`:** W8 step 2 and W10 export.
- **`docs/technical/03`** §2.2: the `export_novel`, `get_models` and `pull_model` rows, new `_export_filename` / `_ollama_base_url` / `OLLAMA_BASE_URL` rows, line column regenerated.
- **`docs/technical/05`:** §1 (export no longer writes `data/`: five path lines, not six) and the tree row for export files.
- **`docs/technical/06`:**
  - the header ("reads no environment variables" → now reads `OLLAMA_HOST`)
  - the two Ollama base-URL rows
- **`docs/technical/01`:** §2 local-only row, §4 dependency rule (`main.py:253` exception), §7 tree (export files) and the data-path note.
- **`docs/technical/07`:** §1 Ollama row (`OLLAMA_HOST`), §5.6 export ("a copy is also written into `data/`").
- **`docs/technical/08`** A12 (the export-fails workaround is obsolete).
- **`docs/ai/RULES.md`:** §1 (data/ "exports", the "main.py's export" path) and §3 (the managers row's export exception).
- **Root `README.md`** map: the `data/` row ("exported .txt/.md files").
- **Line references:** remap for `main.py` and `app.js`.
- **`docs/CHANGELOG.md`:**
  - **Fixed:** export [plan 015] [KI-017]
  - **Fixed / Changed:** `OLLAMA_HOST` for list and pull [plan 015] [KI-033]
- **`docs/ai/memory/`:** `project-state.md`, `session-log.md`.
- **Plan 015:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py_compile` (backend) and `node --check app/frontend/app.js`.
2. **Parity with the library:** with `py -c` and the temp ollama 0.6.3 copy on `PYTHONPATH`, compare `_ollama_base_url` with `ollama._client._parse_host` for:
   - all 28 inputs in its doctests
   - plus `None`, `"localhost:1234"`, `"0.0.0.0"`, `"host:5000/sub/"`

   Expected: identical for all.
3. **Filenames:** `_export_filename` cases:
   - `Untitled Novel` → `Untitled_Novel.txt`
   - `A: B/C?` → `A__B_C_.txt`
   - `林凡传奇` → kept
   - `???` → `novel.md`
   - `End.` → `End.txt` (the trailing dot is stripped)
4. **API, old vs new:** sandboxes (HEAD on 8011, working tree on 8012), each with a copy of `data/`; scripts in Python (UTF-8 bodies).
   - **Export:** for the titles `Untitled Novel`, `Test: A/B?` and `林凡传奇` (set via `PUT /api/novel-meta` on the copy), record the status, `Content-Type`, `Content-Disposition`, body, and the sandbox `data/` listing and mtimes before and after.
     - Old: writes or rewrites a file; 500 for `Test: A/B?`.
     - New: 200 for all, no file created or changed, and the same body text as old where old worked.
   - **`OLLAMA_HOST`:** run a fake Ollama (`/api/tags`, `/api/pull`) on `127.0.0.1:11999`, and start both servers with `OLLAMA_HOST=127.0.0.1:11999`.
     - Old: `ollama_running: false`; the pull errors (it calls `:11434`).
     - New: lists the fake's models and the pull succeeds.
   - **Unreachable host:** new server with `OLLAMA_HOST=127.0.0.1:11998`; the error names `http://127.0.0.1:11998`.
5. **UI:** the browser pane on the new sandbox with an unreachable host. Settings shows "Ollama not reachable: Cannot reach Ollama at http://127.0.0.1:11998: …", and the console is clean.
6. **Cleanup:** stop the servers and the fake; delete the sandboxes, the temp packages and `launch.json`. `git status --porcelain data/` is empty.
- **Not verifiable:** a real remote Ollama (the fake follows the documented API).

## Risks & rollback
- **Default address:** `127.0.0.1` instead of `localhost`. Ollama's default bind is `127.0.0.1:11434`, so the default setup is unaffected. A setup where Ollama listens only on `::1` would need `OLLAMA_HOST=[::1]`, the same as generation already did.
- **Filename vs title:** the download name can differ from the title (forbidden characters become `_`); browsers sanitise names anyway.
- **Rollback:** revert `main.py`, `app.js` and the docs.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 015]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **Export line endings.** The body text is the same as before, but the line endings changed. The old code wrote the export with `Path.write_text` in text mode, so on Windows the download had CRLF line endings (LF elsewhere); the new code sends LF on every OS. Kept and documented: deterministic, and readable by every current editor and Notepad.
- **Parity inputs:** the library docstring holds 30 cases (the plan said 28); 35 inputs were tested in total.
- **Docs:**
  - Doc 05's header got a scoped "verified" date instead of a full bump.
  - Doc 06's ollama-python default was corrected from `localhost` to `127.0.0.1` (the library's real default).

## Outcome
- **Shipped:**
  - **`app/backend/main.py` (KI-017):**
    - `_export_filename` (`:237-240`) turns spaces, Windows-forbidden characters and control characters into `_`, drops trailing dots/spaces, and falls back to `novel`.
    - `export_novel` (`:243-266`) returns `Response(text, media_type=text/plain|text/markdown)` with `Content-Disposition: attachment` (`filename="…"`, or `filename*=utf-8''…` for non-ASCII names), and writes nothing to disk.
  - **`app/backend/main.py` (KI-033):**
    - `_ollama_base_url` (`:291-312`) is a port of ollama-python's `_parse_host`; `OLLAMA_BASE_URL` (`:315`) is computed once from `OLLAMA_HOST`.
    - `/api/tags` (`:325`) and `/api/pull` (`:361`) use it.
    - `ollama_error` is "Cannot reach Ollama at <url>: …".
    - New imports: `os`, `re`, `ipaddress`, `urllib.parse`, and `Response` (all standard library or FastAPI, no new dependency).
  - **`app/frontend/app.js` (KI-033):** the Settings status shows `Ollama not reachable: <ollama_error>` (`:1754`) instead of the fixed "localhost:11434".
- **Files:**
  - Code: `app/backend/main.py`, `app/frontend/app.js`.
  - Docs:
    - `docs/technical/09`: KI-017 and KI-033 fixed; 4 open, 35 fixed.
    - `01` (§2, §3, §4 diagram, §4 rule 2, §7 tree and data-path note, header), `02` (W8, W10), `03` §2.2 (line column regenerated, new `_export_filename` and `_ollama_base_url`/`OLLAMA_BASE_URL` rows), `04` (models, export), `05` (§1, tree, sample-data row, header), `06` (header and both Ollama rows), `07` (§1 Ollama row, §5.6), `08` A12.
    - `docs/ai/RULES.md` §1/§3 (the export exception gone), root `README.md` map.
    - Line refs remapped in `docs/README.md`, 01, 02, 03, 04, 06 and `gotchas.md`.
    - `docs/CHANGELOG.md`, and memory (project-state, session-log).
- **KIs fixed:** KI-017, KI-033.
- **CHANGELOG (Fixed):**
  - export [plan 015] [KI-017]
  - `OLLAMA_HOST` for list and pull [plan 015] [KI-033]
- **Verification:**
  - `py_compile` of `main.py` and `node --check` of `app.js`: OK.
  - **Parity:** `_ollama_base_url` vs `ollama._client._parse_host` (0.6.3, temp copy): **35/35 identical**. That covers all 30 docstring cases plus `None`, `localhost:1234`, `0.0.0.0`, `host:5000/sub/` and `https://example.com:8443/ollama/`. The default is `http://127.0.0.1:11434`.
  - **`_export_filename`:** 7/7, e.g. `A: B/C?` → `A__B_C_.txt`, `???` → `novel.md`, `林凡传奇` kept, `End.` → `End.txt`.
  - **Export, old (8011) vs new (8012)** on sandbox copies:

    | Title | Old | New |
    |---|---|---|
    | `Untitled Novel` | 200; rewrote `data/Untitled_Novel.txt`, created `Untitled_Novel.md` | 200, same headers, `data/` untouched |
    | `Test: A/B?` | **500**; nothing written | 200, `Test__A_B_.txt` / `.md` |
    | `林凡传奇` | 200 (`filename*=utf-8''…`); created both files | 200, same header, nothing written |

    The bodies are identical after CRLF→LF.
  - **`OLLAMA_HOST=127.0.0.1:11999`** with a fake Ollama there:
    - Old: `ollama_running: false` ("All connection attempts failed"), and the pull ended in error.
    - New: listed `zz-remote-model:7b` and `phi4-mini:3.8b`, and the pull ended in `success`.
  - **Browser, unreachable host:** with `OLLAMA_HOST=127.0.0.1:11998`, Settings showed "Ollama not reachable: Cannot reach Ollama at http://127.0.0.1:11998: All connection attempts failed" with the offline dot. The console was empty.
  - **Cleanup:** sandboxes, temp packages, the fake and the temp `.claude/launch.json` removed, servers stopped. `git status --porcelain data/` empty.
- **Not verified:** a real remote Ollama (the fake follows the documented API).
- **Follow-ups:** none required. The old export copy `data/Untitled_Novel.txt` remains (user data, tracked in git); the user may delete it.
