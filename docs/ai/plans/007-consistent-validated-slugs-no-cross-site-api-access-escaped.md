---
id: 007
title: "Consistent, validated slugs, no cross-site API access, escaped HTML (KI-009, KI-010, KI-011)"
status: done
approved: 2026-11-23T14:12:44+05:30
session: 19a87af8-3d49-4cb0-93e3-581fa1ac5540
source_file: "C:\\Users\\2466921\\.claude\\plans\\happy-toasting-flame.md"
sha256: 0654b8edd1e6a874d2bd600ffed442c7220bfa956eb58eaa2702842f9ccc30d4
---

> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current (approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.

# Consistent, validated slugs, no cross-site API access, escaped HTML (KI-009, KI-010, KI-011)

## Context
The user asked to fix KI-009, KI-010 and KI-011. Reading the code this session:
- **KI-009 (inconsistent slugs):**
  - POST keeps any client-supplied slug as-is (`main.py:77-78`).
  - Refine create (`main.py:334`/`:361`) and pipeline step 3 (`chapter_pipeline.py:80`/`:88`) save the **LLM's slug verbatim**.
  - Step 2 trusts the LLM's "existing/new" verdict (`:65-69`): if it writes `xiao_fan_scientist_inventor` for the real `xiao-fan-scientist-inventor`, or calls a known character "new", the character isn't recognised and a **duplicate** is profiled.
  - `c["name"]` (`:68`) raises `KeyError` when the LLM omits a name.
- **KI-010 (security):**
  - **Path traversal.** The managers build `_data_dir() / f"{slug}.json"` from any slug. On Windows a backslash is a path separator, and Starlette decodes `%5C` in path parameters, so `DELETE /api/characters/..%5Cnovel_meta` should delete `data/novel_meta.json`. To be confirmed on a sandbox copy before the fix.
  - **CORS.** `allow_origins=["*"]` (`main.py:31-37`) lets any website open in the browser call every endpoint, including DELETE.
  - **DNS rebinding** (a malicious domain re-pointed at 127.0.0.1) would bypass a CORS restriction alone, because the server accepts any `Host` header.
- **KI-011 (XSS):** `renderWorldSnapshot` (`app.js:1481-1490`), `populateModelSelects` (`:1688-1689`) and `renderModelBrowser` (`:1746-1766`) put world fields (which can come from LLM output) and model names (from Ollama) into `innerHTML` unescaped.
- **Facts checked this session:**
  - Python's `\w` is Unicode-aware, so `make_slug` keeps CJK and accented names. The KI's suggested `^[a-z0-9_-]+$` would reject them.
  - On this Windows 11, `con.json`, `nul.json` etc. are ordinary files (tested), so reserved device names need no special case.
  - Pydantic's `ValidationError` subclasses `ValueError`, so no app-wide `ValueError` handler.
  - FastAPI (≥ 0.65.2, the floor is 0.111) parses JSON only for JSON content types, so a cross-site `text/plain` "simple" POST can't deliver a body. To be verified.

**Done means:**
- Every slug the server writes is derived server-side (`make_slug`).
- Slugs that aren't `[\w-]+` can never reach the file system.
- A new entity that matches an existing one by name or slug (ignoring case and `-`/`_`) is treated as that entity, not duplicated.
- No other website can call the API.
- LLM or Ollama text can't inject HTML.

## Approach
1. **Managers** (`managers/character_manager.py`, `scene_manager.py`, same change in both):
   - Add `_SLUG_RE = re.compile(r"[\w-]+")`, `is_valid_slug(slug) -> bool` and `_path(slug)`, which raises `ValueError` if the slug is invalid.
   - Use them in `get_by_slug` (invalid → `None` → the route's 404), `delete` (invalid → `False` → 404), `save` and `create` (invalid → `ValueError`).
   - `create` additionally refuses a slug *equivalent* to an existing file stem (`_slugify(stem) == _slugify(slug)`), raising `FileExistsError("Character '<existing stem>' already exists")`. This means 409, and catches `Xiao Fan Scientist Inventor` vs the existing `xiao-fan-scientist-inventor`. The exclusive `open(…, "x")` stays as the atomic guard.
2. **`main.py`:**
   - POST characters/scenes: `slug = make_slug(slug or name)` (always canonical). An empty result → **422** "name must contain at least one letter or digit". This also fixes **KI-038**: `???` no longer saves `.json`.
   - Refine create: slug = `make_slug(LLM name)` before constructing the model, with the same 422 check outside the `try`. The existing 409/500 mapping stays.
   - **Remove `CORSMiddleware`**, so the browser blocks cross-origin calls; DELETE and JSON POSTs need a preflight that now fails.
   - Add `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])` against DNS rebinding; any other `Host` gets 400.
3. **`app/frontend/app.js`:**
   - `const API = '/api'` (same origin). This works whether the page is opened as 127.0.0.1 or localhost, so no CORS is needed, and fixes **KI-021** too.
   - **KI-011:** wrap every interpolated value in `escHtml()`: world fields in `renderWorldSnapshot` (escaped after truncation), option value/label in `populateModelSelects`, and name, `data-model`, size/quality/note and the `pb-/pf-/ps-` ids in `renderModelBrowser`. `pullModel` looks the ids up unchanged, because the parsed attribute equals the unescaped id.
4. **`pipeline/chapter_pipeline.py`:**
   - New module-level `_canonical_entities(entries, existing, make_slug)` applied to the step-2 result for characters and scenes. Entries without a usable name, and repeats, are dropped; this also removes the `KeyError` crash.
   - An entry whose slug **or** name normalises to an existing entity's slug or name becomes `existing` with that entity's real slug. Everything else becomes `new` with `slug = make_slug(name)`.
   - Step 3 builds each profile with `slug = make_slug(profile name)`, so the new file matches the step-2 slug, and a profile of an existing entity hits the 409 guard (warning, profile kept).

## Contract / data impact
- **API:**
  - POST now normalises client slugs (`"Elder-Wu"` → `elder_wu`).
  - New **422** for names without letters or digits.
  - 409 now also covers `-`/`_`/case-equivalent slugs.
  - PUT/DELETE/refine `existing_slug` with an invalid slug → 404.
  - **No cross-origin access** (CORS removed), and the `Host` must be `127.0.0.1` or `localhost`.
  - Routes and payload shapes are unchanged.
- **SSE:** unchanged.
- **`data/`:** no change. Existing slugs (`xiao-fan-scientist-inventor`, `neuroscience-lab-night-stormy-weather`) match `[\w-]+` and stay fully usable. Old `.json` files from KI-038 stay listed but unchanged (manual delete, as documented).
- **Port/URL invariant:** `app.js` no longer hard-codes the URL, so `8000`/`127.0.0.1` now live in 2 places (start.bat, `main.py`).

## Docs to update (RULES §6)
- **`docs/technical/09`:**
  - KI-009, KI-010, KI-011 → Fixed [plan 007], with status lines; KI-010 gets the confirmed traversal evidence.
  - Also fixed by the same change: KI-021 (same-origin API) and KI-038 (empty slug → 422).
- **`docs/technical/04`:** base URL / CORS note, POST slug normalisation + 422, 409 equivalence, 404 for invalid path slugs, Host restriction.
- **`docs/technical/02`:** W3.3 step 2/3 (canonical slugs, dedupe), W6 create row.
- **`docs/technical/03`:**
  - §1 middleware rows
  - §2.3 managers (`is_valid_slug`, `_path`, the `create` equivalence check)
  - §2.7 pipeline helper
  - §4 API constant
- **`docs/technical/05`:** identity and slug rules.
- **`docs/technical/06` §2.1:** API base row, the CORS row → TrustedHost, port locations.
- **`docs/technical/01`:** security section (CORS row) and the port invariant.
- **`docs/technical/08`:**
  - A1.5: localhost now fully works
  - A14: `???` → 422; the existing `.json` workaround stays
- **`docs/ai/RULES.md` §3:** port/URL invariant (2 places), `app.js` row.
- **Line references:** remap the `main.py`, managers, `chapter_pipeline.py` and `app.js` refs with the `difflib` script from plan 006, extended to several files. The historical evidence of fixed KIs stays.
- **`docs/CHANGELOG.md` `[Unreleased]`:**
  - **Security:** traversal and CORS/Host (KI-010), HTML escaping (KI-011)
  - **Fixed:** slugs and duplicates (KI-009), KI-021, KI-038
  - **Changed:** POST normalises slugs
  - Each line tagged `[plan 007]`.
- **`docs/ai/memory/`:**
  - `gotchas.md`: slug and 409 entries updated; "API is same-origin; CORS removed"
  - `project-state.md`, `session-log.md`
- **Plan 007:** status, execution log, outcome, then `reindex`.

## Verification
1. **Static checks:** `py -m py_compile` (all backend), `node --check app/frontend/app.js`.
2. **Two sandboxes**, temp copies of `app/` + `data/`: one with the **committed** code (for "before" evidence) and one with the fixed code. Both use a stub `ollama`. No server ever points at the real `data/`.
3. **Traversal:**
   - Old code: `curl -X DELETE …/api/characters/..%5Cnovel_meta` → expect `novel_meta.json` deleted (documents the bug).
   - Fixed code: the same request → 404 and the file intact. `..%5C..%5Cx`, `a.b` and `x%2Fy` variants → 404. PUT with a backslash → 404.
4. **Cross-site:**
   - `OPTIONS` preflight with `Origin: http://evil.example` and `Access-Control-Request-Method: DELETE`: old → `access-control-allow-origin: *`; fixed → no allow-origin header.
   - `POST /api/characters` with `Content-Type: text/plain` and a JSON body → 422 (no write).
   - `Host: evil.example` → 400; `Host: 127.0.0.1:8000` and `localhost:8000` → 200.
5. **Slugs:**
   - POST `"Zz Test Hero"` → `zz_test_hero`. POST slug `"Zz-Test-Two!"` → `zz_test_two`.
   - POST `"Xiao Fan Scientist Inventor"` → **409** naming `xiao-fan-scientist-inventor`.
   - POST `"???"` → **422** and no `.json`.
   - The existing hyphenated character and scene still load, edit (PUT) and delete through the API.
6. **Pipeline dedupe** (stub):
   - Step 2 marks "Xiao Fan Scientist Inventor" as `new` with slug `xiao_fan_scientist_inventor` and adds `Zz New Hero` with slug `Zz-New-Hero!`, plus a nameless entry; step 3 profiles both named ones.
   - Fixed code: one `new_character` event (`zz_new_hero`), no duplicate Xiao file, and the chapter's `characters_featured` contains `xiao-fan-scientist-inventor` and `zz_new_hero`.
   - Old code: a duplicate `xiao_fan_scientist_inventor.json` appears (contrast), and the nameless entry raises `KeyError`.
7. **XSS (UI in the browser pane):**
   - The world has `world_name = <img src=x onerror="window.__x1=1">` and a genre tag containing `<b>`. The World Build snapshot must show the literal text, with no `<img>`/`<b>` element and `__x1` undefined.
   - A fake Ollama on port 11434 (tiny stdlib server; only if the port is free) returns an installed model named `<img src=x onerror="window.__x2=1">:latest`, and the writer model is set to a similar string. Opening Settings must show both as text in the selects and the model browser, with `__x2` undefined.
8. **Regression (UI):** the page loads via `localhost:8000` with `API='/api'`; the sidebars load; create character, generate (stub) and Settings save all work; the console is clean.
9. **Cleanup:** stop the servers (8000, 8011, 11434), delete the sandboxes, stubs and `launch.json`, delete `cpython-314` bytecode. `git status --porcelain data/` is empty.
- **Not verifiable:** real LLM output; real Ollama.

## Risks & rollback
- **Opening the UI another way.** It now has to be served by the app (`/api` same-origin). Opening `index.html` from disk never worked anyway (fonts and `app.js` were already served by the backend).
- **Third-party tools.** Anything that called the API from a browser page on another origin stops working, by design. curl and scripts are unaffected, as long as they connect to 127.0.0.1 or localhost.
- **Normalised slugs.** API clients that relied on hyphenated slugs get `_` slugs for new entities. Existing files are untouched.
- **Rollback:** revert the five code files and the doc edits. No data migration.

---

## Execution log
<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->
- [x] Implementation started (status → in-progress)
- [x] Code changes complete
- [x] Verified (RULES.md §9)
- [x] docs/CHANGELOG.md [Unreleased] updated (cite `[plan 007]`)
- [x] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)
- [x] docs/ai/memory/project-state.md updated
- [x] Status → done (or abandoned with reason) and `reindex` run

**Deviations from the plan:**
- **The traversal was worse than "one file".** On the committed code, both `DELETE /api/characters/..%5Cnovel_meta` and `DELETE /api/scenes/..%5Cworld_settings` succeeded (200), deleting the two root data files of the sandbox copy.
- **Stale doc tables, not only today's shifts.**
  - Doc 03 §2.2 (the `main.py` symbol table) still carried v1.0.0 line numbers, because its line column has no `main.py:` prefix and the plan 004–006 remaps skipped it. It was regenerated from the current file with `ast`.
  - Doc 02 W3.3 uses bare `` `:N` `` refs for `chapter_pipeline.py`; these were remapped by section (+23 after the new helper).
- **Test harness, not code.** A CJK POST via curl in Git Bash returned 422 because the shell mangled the argument to `??`. The same request sent as UTF-8 from Python created `林凡.json`. Logged as a gotcha.
- **`scene_manager.py` generated, not edited.** It was produced from `character_manager.py` by substitution, and its diff against the old file was checked to contain only the plan-007 changes.

## Outcome
**Shipped** (uncommitted):
- `managers/character_manager.py`, `scene_manager.py`:
  - `_SLUG_RE` (`[\w-]+`), `is_valid_slug()`, `_path()`. `get_by_slug`/`delete` → not found for invalid slugs; `save`/`create` → `ValueError`.
  - `create()` refuses an equivalent stem (409) before the exclusive open.
- `main.py`:
  - `CORSMiddleware` replaced by `TrustedHostMiddleware(["127.0.0.1","localhost"])`.
  - POST stores `make_slug(slug or name)`, 422 if empty.
  - Refine create uses `make_slug(profile name)`, 422 if empty.
- `pipeline/chapter_pipeline.py`: `_canonical_entities()` for step 2; step 3 slugs from the profile name.
- `app/frontend/app.js`: `API = '/api'`; `escHtml` in `renderWorldSnapshot`, `populateModelSelects`, `renderModelBrowser`.
- Line endings preserved: the CRLF files stay CRLF; the managers stay LF in the working tree, as before.

**KIs fixed:** KI-009, KI-010, KI-011, plus KI-021 and KI-038 by the same change.

**CHANGELOG:**
- Changed: slug normalisation, same-origin API
- Fixed: KI-009, KI-021, KI-038
- new **Security** section: traversal, CORS/Host, XSS

**Docs updated:**
- technical 01, 02, 03 (§2.2 regenerated, §2.3, §2.7, §4), 04, 05, 06, 08, 09
- `RULES.md` §3 (port/URL in 2 places, slug invariant)
- memory: `gotchas.md` (slugs, 409, same-origin API, curl encoding), `project-state.md`, `session-log.md`
- line refs remapped: 36 prefixed + 14 bare, plus the regenerated table

**Verification** (2026-11-23). Two sandboxes (committed code on 8011, fixed code on 8012) plus a stub `ollama`. The real `data/` was never served.
1. `py_compile` and `node --check` passed.
2. **Traversal:**
   - Committed code: both deletes returned 200 and the files were gone.
   - Fixed code: 404 and the files intact. `..%5C..%5Cx`, `a.b`, `x%2Fy`, `..%5C..%5Capp%5Cbackend%5Cmain` and a backslash PUT were all 404.
3. **Cross-site:**
   - Preflight from `evil.example`: committed 200 with `ACAO: *`; fixed 405 with no ACAO.
   - GET with a foreign Origin: committed `ACAO: *`; fixed none.
   - `Host: evil.example`: committed 200; fixed 400. `127.0.0.1:8000`, `localhost:8000` and `localhost` → 200.
   - A `text/plain` cross-site POST was rejected with no file written.
4. **Pipeline:**
   - Committed code: 2 "new" characters, a duplicate `xiao_fan_scientist_inventor.json` and `Zz-New-Hero!.json`, featured slugs `['xiao_fan_scientist_inventor', 'Zz-New-Hero!']`.
   - Fixed code: 1 new (`zz_new_hero`), a warning refusing the Xiao duplicate, featured `['xiao-fan-scientist-inventor', 'zz_new_hero']`.
   - Nameless entry: committed `Pipeline error: 'name'`; fixed completes.
5. **Slugs:**
   - `Zz Test Hero` → `zz_test_hero`; `Zz-Test-Two!` → `zz_test_two`.
   - `Xiao Fan Scientist Inventor` → 409 naming the hyphenated file.
   - `???` and scene `!!!` → 422, no `.json`.
   - `林凡` → `林凡.json`; `Élodie Brontë` → `élodie_brontë`.
   - Refine with LLM slug `Totally/Bad\Slug` → `zz_refined_hero`, then 409.
   - The hyphenated character listed and PUT fine; the hyphenated scene deleted fine.
6. **UI** (browser pane on the fixed sandbox; fake Ollama on 11434 serving a hostile model name):
   - World snapshot and the Settings selects/browser rendered every payload as text: 0 injected elements, no flags set.
   - Set Writer, Settings save, New Character (`zz_ui_char`) and a 7-step generation all worked.
   - Console clean.
7. **Cleanup:**
   - Servers on 8000/8011/8012/11434 stopped.
   - Sandboxes, stubs, launcher and `.claude/launch.json` removed; `cpython-314` bytecode deleted.
   - `data/` untouched.

**Not verified:**
- real LLM output
- a real Ollama model list (the fake one served `/api/tags` only)

**Follow-ups:** none required. Opening the UI under another host name (e.g. the machine name) now gets 400 by design; add that name to `allowed_hosts` if ever needed.
