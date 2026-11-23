# Gotchas (verified traps)

> Auto-loaded into every Claude session. Only verified, still-true traps. Delete an entry once the code no longer has the trap (and note that in `docs/CHANGELOG.md` and `docs/technical/09`).

- **Run uvicorn from `app/backend/`** (or pass `--app-dir app/backend`). `uvicorn main:app` resolves `main` from the CWD. The flat imports work anyway because `main.py:13` patches `sys.path`, and data paths come from `__file__`. (2026-11-22)
- **Refine "merge" saves unvalidated values.** `setattr` in `main.py:327/357` bypasses Pydantic, so a bad LLM value gets saved and the entity then fails to load (vanishes from lists, 500 on edit). Verified (KI-016). (2026-11-22)
- **The specialist is async.** Every `specialist.*` function is `async def`; call it with `await` (a missing `await` returns a coroutine, not a dict, and `.get()` then fails). Never use the sync `ollama.chat` in async code (KI-005, plan 005). (2026-11-22)
- **Slugs are server-derived and validated.** `slug` is still a required body field (send `""`), but POST stores `make_slug(slug or name)`; an empty result is 422. Managers accept only `[\w-]+` via `_path()`; never build `data/` paths from request or LLM strings (KI-009/KI-010, plan 007). (2026-11-23)
- **Create returns 409 for a taken or equivalent slug** (same `_slugify`: case, `-` vs `_`; e.g. `xiao-fan-scientist-inventor` blocks `Xiao Fan Scientist Inventor`). POST, refine create; step 3 emits a `warning`. Delete `zz_test_` entities before re-running tests (KI-036/KI-009). (2026-11-23)
- **`save()` is an upsert, `create()` is exclusive** (managers). Use `create()` for any new create path, or you reintroduce KI-036. (2026-11-22)
- **Pydantic v2 does not coerce int → str.** An LLM returning `"age": 17` or `"type": "supporting"` fails `Character(**…)`, and the entity is silently dropped (KI-016). (2026-11-22)
- **Two Pythons on the dev machine.** `py` (3.14.5) has the web deps; `python` (3.14.0) is a different install. Use `py` for backend checks. Running `py -I` hides user-site packages. (2026-11-22)
- **Inline scripts with apostrophes break the Bash tool.** A heredoc Python script containing `'` inside strings (e.g. "doesn't") fails with "unexpected EOF while looking for matching `''", and nothing runs. Write the script to a temp file and run that instead. (2026-11-22)
- **Git identity is per clone.** The machine-wide git identity is the work account; this repo overrides it in `.git/config` (D-010). Check `git config user.email` = `mauryatejasva512004@gmail.com` before committing, and set it again after a fresh clone, or GitHub credits the work account. (2026-11-23)
- **The API is same-origin only.** No CORS; `TrustedHostMiddleware` allows `Host` 127.0.0.1/localhost only (other hosts → 400). Test with `http://127.0.0.1:<port>`; a page on another origin can't call the API (plan 007). (2026-11-23)
- **Git Bash curl mangles non-ASCII arguments.** `curl -d '{"name":"林凡"}'` arrives as `??` (looked like a 422 bug). Send UTF-8 bodies from a Python script (`urllib`), and run it without `-I` with `PYTHONIOENCODING=utf-8` to print them. (2026-11-23)
- **Git Bash noise.** Every Bash call on this machine prints `/etc/mtab`, `/etc/hosts` … "Permission denied" lines from the shell profile. They are harmless; ignore them. (2026-11-22)
- **`data/` is the user's novel.** Never use it as a scratch area. Test with `zz_test_` entities and delete them afterwards. (2026-11-22)
