# Gotchas (verified traps)

> Auto-loaded into every Claude session. Only verified, still-true traps. Delete an entry once the code no longer has the trap (and note that in `docs/CHANGELOG.md` and `docs/technical/09`).

- **Run uvicorn from `app/backend/`** (or pass `--app-dir app/backend`). `uvicorn main:app` resolves `main` from the CWD. The flat imports work anyway because `main.py:13` patches `sys.path`, and data paths come from `__file__`. (2026-11-22)
- **Refine "merge" saves unvalidated values.** `setattr` in `main.py:329/356` bypasses Pydantic, so a bad LLM value gets saved and the entity then fails to load (vanishes from lists, 500 on edit). Verified (KI-016). (2026-11-22)
- **`ollama` must be ≥ 0.4.** The code uses `response.message.content` (`agents/specialist.py:54`, `agents/writer.py:59`), but `app/requirements.txt` pins 0.3.3 (KI-004). `writer.py` imports it unguarded, so a missing package = server won't start (KI-003). (2026-11-22)
- **`slug` is a required body field** in `Character`/`Scene` (`models.py:13`, `:32`). Send `""` to have POST derive it from the name. A body without `slug` gets a 422. The UI sends it since plan 003. (2026-11-22)
- **Create returns 409 for a taken slug** (POST, refine create; step 3 emits a `warning`). This includes case-only differences on Windows. Re-running a test with the same `zz_test_` name fails, so delete test entities first (KI-036 fixed, plan 004). (2026-11-22)
- **`save()` is an upsert, `create()` is exclusive** (managers). Use `create()` for any new create path, or you reintroduce KI-036. (2026-11-22)
- **Pydantic v2 does not coerce int → str.** An LLM returning `"age": 17` or `"type": "supporting"` fails `Character(**…)`, and the entity is silently dropped (KI-016). (2026-11-22)
- **Two Pythons on the dev machine.** `py` (3.14.5) has the web deps; `python` (3.14.0) is a different install. Use `py` for backend checks. Running `py -I` hides user-site packages. (2026-11-22)
- **Git Bash noise.** Every Bash call on this machine prints `/etc/mtab`, `/etc/hosts` … "Permission denied" lines from the shell profile. They are harmless; ignore them. (2026-11-22)
- **`data/` is the user's novel.** Never use it as a scratch area. Test with `zz_test_` entities and delete them afterwards. (2026-11-22)
