---
id: 016
title: "Test suite, lint, CI and logging; atomic data writes with logged skips (KI-025, KI-026)"
status: done
approved: 2026-11-24T13:07:32+05:30
session: 8e82db1f-b2c4-4901-8528-5594118a09fb
source_file: "C:\\Users\\2466921\\.claude\\plans\\drifting-questing-parnas.md"
sha256: 4f34a31789fd3270b378fdcd615b4877713ceec4a0efa29401eb25f576d6fd0f
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Test suite, lint, CI and logging; atomic data writes with logged skips (KI-025, KI-026)

## Context
The user asked to fix KI-025 (Medium) and KI-026 (Low). Read this session:
- **KI-026:** the five managers write `data/` files with a plain `open(path, "w")` + `json.dump`:
  - `character_manager.save`, `scene_manager.save`, `chapter_manager.save_chapter`, `world_manager.save`, `novel_meta_manager.save`; `create()` uses `open(path, "x")`.
  - **A crash, kill or full disk mid-write truncates the file.**
  - **Silent skips:** `get_all()` in the character, scene and chapter managers then skips it with `except Exception: pass`, so the character, location or chapter silently disappears from the UI.
- **KI-025:** there are no tests, no linter, no CI and no `logging` anywhere. Every check so far was an ad-hoc sandbox script.
- **User decisions (asked this session; RULES §5 and §1):**
  - **Dev tools:** pytest + ruff as dev-only dependencies in a new `app/requirements-dev.txt`. `app/requirements.txt` and `start.bat` are unchanged.
  - **CI:** add a GitHub Actions workflow. That needs `.github/workflows/` at the repo root (an approved exception to RULES §1), and the push token needs the **Workflows** permission or GitHub refuses the push.
- **Facts checked:**
  - The agents import `ollama` optionally (`specialist.py:12-14`, `writer.py:6-8`), so tests can supply a fake module.
  - Each manager's path comes from a module function (`_data_dir()`, or `_path()` for world and meta), so tests can redirect them to a temp folder.
  - `TrustedHostMiddleware` allows only `127.0.0.1`/`localhost`, so `TestClient` must use `base_url="http://127.0.0.1"`.
  - `.gitignore` already ignores `*.tmp` and `.pytest_cache/`.
  - PyYAML is available locally to syntax-check the workflow.

**Done means:**
- A data file is replaced all-or-nothing, and an unreadable file is logged, not silently dropped.
- `py -m pytest app/tests` and `py -m ruff check app` pass locally.
- CI runs both on push.
- The server logs warnings and errors to the console.

## Approach
1. **Atomic storage (KI-026), new `app/backend/managers/storage.py`:**
   - **`write_json(path, data, *, exclusive=False)`:**
     - Serialise first (UTF-8, `indent=2, ensure_ascii=False`, as today).
     - Write to a temp file in the same folder (`.<stem>.<random>.tmp`), then `flush` + `fsync`.
     - Move it into place:
       - Normal saves use `os.replace` (atomic).
       - `exclusive=True` uses `os.link` (atomic, and raises `FileExistsError` if the name is taken). If the filesystem has no hard links, it falls back to today's `open(path, "x")`.
     - The temp file is always removed.
   - **`read_all(folder, model, label)`:** loads every `*.json` and logs `WARNING Skipped unreadable <label>/<file>: <error>` for each one that fails, instead of `pass`.
   - **Managers:** each `save*`/`create` calls `write_json`; the `get_all` loops use the logged skip. Function names and signatures are unchanged (RULES §3), and `create()` keeps its equivalent-slug check and 409 messages.
2. **Logging (KI-025):**
   - **`main.py`:** `logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`. Uvicorn's own loggers are unaffected.
   - **Module loggers** (`logging.getLogger(__name__)`):
     - managers: skipped files
     - `chapter_pipeline._sse`: every `warning`/`error` event is also logged; errors include the traceback detail
     - `specialist._call`: a reply that isn't a JSON object
     - `main.pull_model`: pull errors
3. **Tests (KI-025), new `app/tests/`:**
   - **`conftest.py`:**
     - Puts `app/backend` on `sys.path`.
     - Installs a recording fake `ollama` in `sys.modules` before any app import: `AsyncClient.chat` (JSON or streamed chunks, per-test configurable) and `generate`.
     - **Autouse fixture:** redirects all five managers' paths to `tmp_path`, so no test can touch `data/`.
     - **Session guard:** fails the run if the real `data/` changed (names, sizes, mtimes).
     - **`client` fixture:** `TestClient(main.app, base_url="http://127.0.0.1")`, with the generation guard reset between tests.
   - **`test_storage.py` (KI-026):**
     - Save writes the right JSON and leaves no `.tmp` files.
     - A failure during the final move leaves the old file intact and removes the temp file (the old code truncated it).
     - `create` never replaces.
     - A corrupt file is skipped **with a logged warning** (`caplog`), and stray `.tmp` files are ignored.
   - **`test_api.py`:**
     - health
     - character create / 409 (including the equivalent slug) / update / delete; scenes once
     - a path-traversal slug gives 404 and writes nothing (KI-010)
     - a foreign `Host` header gives 400
     - novel-meta round trip keeps every field
     - export writes no file and sanitises the name (KI-017)
     - generate-cancel when idle returns `{"cancelled": false}`
     - `/api/models` via `httpx.MockTransport`: exact installed match (KI-020); an unreachable Ollama names the address (KI-033)
     - pull reports `success` only after Ollama's own, and errors on HTTP 404, an error line or a truncated stream (KI-019)
   - **`test_pipeline.py`:** a full `POST /api/generate-chapter` with the fake ollama.
     - Statuses 1–7, tokens and `complete`; the chapter is saved with its featured slugs.
     - `keep_alive` is 300 for steps 1–2 and 0 for the unload and step 7; the writer uses 300 (D-011).
     - A string `estimated_chapters: "2"` gives `multi_chapter` instead of a crash (KI-015).
   - **`test_helpers.py`:**
     - `_ollama_base_url`: the library's doctest cases, hard-coded
     - `_export_filename`, `_model_key`
     - model coercion: `age: 17` → `"17"`, `type: "supporting"` → `temporary`, a string → a one-item list
4. **Lint (KI-025):**
   - **New `app/pyproject.toml`**, holding only tool config:
     - `[tool.pytest.ini_options]` with `testpaths = ["tests"]`.
     - `[tool.ruff]` with the default rules (pyflakes + core pycodestyle) and `target-version = "py311"`.
     - Ignore `E402` (module imports after the deliberate `sys.path` patch, RULES §3).
   - Fix whatever real findings ruff reports (e.g. unused imports) with minimal edits, and list them in the outcome.
   - `.gitignore` gets `.ruff_cache/`.
5. **CI, new `.github/workflows/ci.yml`:**
   - Runs on push and pull request.
   - **Matrix:** `ubuntu-latest` and `windows-latest` × Python `3.11` and `3.14`.
   - **Steps:** checkout → setup-python (pip cache) → `pip install -r app/requirements-dev.txt` → `ruff check app` → `pytest app/tests` → `node --check app/frontend/app.js`.
6. **`app/requirements-dev.txt`:** `-r requirements.txt`, `pytest>=8`, `ruff>=0.6`, with a header comment ("dev only; not needed to run the app").

## Contract / data impact
- **None for the API or SSE.** The on-disk JSON format is byte-for-byte the same; only the way it is written changes.
- **Repo layout:** a new root folder `.github/` (user-approved; recorded in RULES §1 and decision D-013), plus the new `app/tests/`, `app/pyproject.toml` and `app/requirements-dev.txt`.
- **Dependencies:** pytest and ruff, dev-only (user-approved).

## Docs to update (RULES §6)
- **`docs/technical/09`:** KI-025 and KI-026 → Fixed [plan 016]; update the counts.
- **`docs/technical/01`:** §7 tree (`.github/`, `app/tests/`, `pyproject.toml`, `requirements-dev.txt`, `managers/storage.py`) and §8 (logging).
- **`docs/technical/03`:** §2.3 managers (`storage.py`, atomic writes, logged skips), §5 error handling (logging), and a short testing note.
- **`docs/technical/05`:** the atomicity row (temp file + replace) and skipped files are logged.
- **`docs/technical/06`:** logging, dev tooling and §3 dependencies (`requirements-dev.txt`).
- **`docs/technical/07`:** a new "run tests and lint" section, and the developer quick reference.
- **`docs/technical/08`:** A9 ("added by hand doesn't show up": now a console warning names the file).
- **`docs/ai/RULES.md`:**
  - §1 root list (`.github/`)
  - §2.5 and §9 (there is now a test suite: run it, `py -m pytest app/tests` and `py -m ruff check app`)
  - §3 (`managers/storage.py`, `app/tests/`)
  - §5 (dev dependencies too)
  - §6 (tests and CI rows)
- **Root `README.md`** map (`.github/`) and **`AGENTS.md`**, if they mention verification.
- **`docs/CHANGELOG.md`:**
  - **Added:** tests, lint, CI, logging [plan 016] [KI-025]
  - **Fixed:** atomic writes, logged skips [plan 016] [KI-026]
- **`docs/ai/memory/`:**
  - `decisions.md`: D-013, tooling and the `.github/` exception
  - `gotchas.md`:
    - `TestClient` needs the 127.0.0.1 base URL
    - tests are isolated from `data/` by an autouse fixture
    - the "no test suite" lines are gone
  - `project-state.md`: how to run tests; next up
  - `session-log.md`
- **Line references:** remap for every changed source file.
- **Plan 016:** status, execution log, outcome, then `reindex`.

## Verification
1. **Tools:** install pytest + ruff into a temp `--target` folder (not the user's site-packages) and put it on `PYTHONPATH`. Delete the leftover empty `nf016probe` temp folder from planning.
2. **The suite:** `py -m pytest app/tests -q` all passes, and the session guard confirms the real `data/` was untouched. `py -m ruff check app` is clean. `node --check app/frontend/app.js` and `py_compile` pass.
3. **The tests catch the bugs:** temporarily point `test_storage`'s crash test at a naive in-place writer (or run it against HEAD's `character_manager`); it must fail (truncated file).
4. **KI-026 old vs new**, with a script on sandbox copies (HEAD vs working tree):
   - Simulate a crash mid-save (patch `json.dump` / `os.replace` to raise after a partial write). Old: the character file is truncated and `get_all()` silently loses it. New: the original is intact and no temp file is left.
   - Put a corrupt `zz_test_broken.json` in the sandbox: old skips it silently; new logs `Skipped unreadable characters/zz_test_broken.json`.
5. **Server smoke:** a sandbox uvicorn with the corrupt file; the console shows the warning in the new format; `/api/health` works. Stop it afterwards.
6. **CI:**
   - `yaml.safe_load` of the workflow.
   - Not runnable locally: it is exercised on the first push. If GitHub refuses the push because of the workflow file, report it and ask the user to add the token's Workflows permission.
7. **Cleanup:** temp tool folder, sandboxes, `__pycache__`/`.pytest_cache`/`.ruff_cache` created by runs (ignored, but remove them from the working tree anyway). `git status --porcelain data/` is empty.

## Risks & rollback
- **Hard links:** `os.link` needs a filesystem with hard links (NTFS, ext4, APFS). Elsewhere it falls back to the old exclusive write (still never replaces).
- **Speed:** `fsync` adds a few milliseconds per save, which is negligible here.
- **Brittle redirection:** tests patch private path functions; a future manager must be added to the fixture. The session guard on `data/` catches a miss.
- **Ruff fixes** touch existing code (unused imports and the like); no behaviour change, listed in the outcome.
- **The push may be refused** because of the workflow file until the token has the Workflows permission.
- **Rollback:** revert the managers, `storage.py`, the logging lines and the new tooling files; the data format is unchanged.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 016]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **ruff rule set pinned.** ruff 0.17's default rule set is wider than the classic one (it flagged 114 items, mostly `Dict` → `dict` style), so `app/pyproject.toml` pins `select = ["E4", "E7", "E9", "F"]` (as intended, and stable across ruff versions).
- **KI-040 (new).** ruff (target `py311`) found that plan 015's `_export_filename` put a backslash inside an f-string expression, so `main.py` does not parse on Python 3.11. Fixed (the fallback is computed before the f-string) and catalogued as KI-040. The bug was present on `main` in `fa4332b`.
- **ruff fixes.** Five unused imports removed:
  - `typing.Any` in `models.py` and `specialist.py`
  - `models.Character` and `models.Scene` in `specialist.py`
  - `typing.Optional` in `context_builder.py`
- **Extra test and doc fixes.**
  - The fake `ollama` can make the step-5 unload fail, to test that pipeline warnings are logged.
  - Doc 03 §2.4 still said `keep_alive=-1` for `_call` (stale since plan 013); corrected.
  - `AGENTS.md` got the verify commands.
- **Not verified:** CI itself. It runs only on GitHub, on the first push.

## Outcome
- **Shipped:**
  - **`app/backend/managers/storage.py` (new, KI-026):**
    - `write_json`: serialise; temp file `.<stem>.<random>.tmp` in the same folder; `fsync`; `os.replace`. With `exclusive=True` it uses `os.link` instead (FileExistsError if taken), falling back to `open(…, "x")` without hard links. The temp file is always removed, and the bytes are identical to the old writer.
    - `read_all`: logged skips.
    - All five managers use them; their function names are unchanged.
  - **Logging (KI-025):** `logging.basicConfig` + `log` in `main.py` (`:36-37`).
    - Pull errors go through `pull_error`; a cancelled generation is logged at INFO.
    - `chapter_pipeline._sse` logs `warning`/`error` events.
    - `specialist._call` logs replies without JSON.
  - **Tests (KI-025):** `app/tests/` holds `conftest.py` (fake ollama, temp data, real-data guard, `client` on 127.0.0.1) plus:
    - `test_storage.py`: 7 tests
    - `test_api.py`: 16 tests
    - `test_pipeline.py`: 5 tests
    - `test_helpers.py`: 43 tests, parametrised
    - **71 tests in total.**
  - **Tooling (KI-025):**
    - `app/requirements-dev.txt` (pytest>=8, ruff>=0.6)
    - `app/pyproject.toml`
    - `.github/workflows/ci.yml` (Ubuntu and Windows × Python 3.11 and 3.14; ruff, pytest, `node --check`)
    - `.gitignore` gets `.ruff_cache/`
  - **KI-040:** `main.py` `_export_filename` (`:243-248`).
- **Files:**
  - Code: `app/backend/main.py`, `models.py`, `agents/specialist.py`, `pipeline/chapter_pipeline.py`, `pipeline/context_builder.py`, `managers/{character,scene,chapter,world,novel_meta}_manager.py`, new `managers/storage.py`.
  - Tooling: new `app/tests/*`, `app/pyproject.toml`, `app/requirements-dev.txt`, `.github/workflows/ci.yml`; `.gitignore`.
  - Docs:
    - `docs/technical/09`: KI-025 and KI-026 fixed, KI-040 added (fixed); 2 open, 38 fixed.
    - `01` (§7 tree, §8 logging, header), `03` (§2.2 table regenerated with a logging row, §2.3 storage, §2.4 `_call`, §2.7 `_sse`, §5 logging and tests), `05` (atomicity and corruption rows), `06` (logging row, dev dependencies), `07` (§6 note, §7 row, new "Tests and lint"), `08` A9.
    - `docs/ai/RULES.md` §0, §1, §2.5, §3, §5, §6, §9; root `README.md`; `AGENTS.md`.
    - Line refs remapped in `docs/README.md`, 01, 02, 03, 04, 06 and `gotchas.md`.
    - `docs/CHANGELOG.md`; memory: `decisions.md` (D-013), `gotchas.md` (2 new), `project-state.md`, `session-log.md`.
- **KIs fixed:** KI-025, KI-026, KI-040 (new).
- **CHANGELOG:**
  - Added: tests, lint, CI, logging [plan 016] [KI-025]
  - Fixed: atomic saves and reported unreadable files [plan 016] [KI-026]
  - Fixed: Python 3.11 starts again [plan 016] [KI-040]
- **Verification:**
  - **Suite and lint:** pytest 9.2.0 and ruff 0.17.6 installed into a temp `--target` folder (removed afterwards).
    - `py -m pytest app/tests`: **71 passed**. The real-data session guard held, and `git status --porcelain data/` is empty.
    - `py -m ruff check app`: all checks passed.
    - `py_compile` and `node --check` are OK.
    - Committed `main.py` (HEAD) fails ruff's 3.11 syntax check (KI-040 evidence).
  - **Mutation:** with `write_json`/`read_all` replaced by the old in-place writer and a silent skip (sandbox copy), 3 storage tests fail: the old file is not preserved, and the two logged-skip tests fail.
  - **KI-026 old vs new**, crash simulated mid-save on sandbox copies of `app/backend` + `data/`:
    - Old: the file was CORRUPT (189 of 377 bytes) and `get_all()` dropped the character silently.
    - New: the file was valid and unchanged, still listed, and no temp file was left.
    - Corrupt `zz_test_broken.json`: old logged nothing; new logged `WARNING managers.storage: Skipped unreadable characters/zz_test_broken.json: JSONDecodeError: …`.
  - **Server smoke** (sandbox uvicorn): the warning appears in the console in the new format next to uvicorn's access log, with no duplicate lines. `/api/health` returns 200.
  - **CI:** `yaml.safe_load` OK (triggers push and pull_request, 2×2 matrix, 6 steps). It runs only on GitHub.
  - **Cleanup:** sandboxes and the temp tools removed; `__pycache__`, `.pytest_cache` and `.ruff_cache` removed from the working tree.
- **Follow-ups:**
  - The push adds `.github/workflows/ci.yml`; GitHub refuses it unless the push token has the **Workflows** permission.
  - After the first push, check that the CI run is green.
