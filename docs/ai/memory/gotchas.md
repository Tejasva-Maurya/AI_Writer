# Gotchas (verified traps)

> Auto-loaded into every Claude session. Only verified, still-true traps. Delete an entry once the code no longer has the trap (and note that in `docs/CHANGELOG.md` and `docs/technical/09`).

- **Run uvicorn from `app/backend/`** (or pass `--app-dir app/backend`). `uvicorn main:app` resolves `main` from the CWD. The flat imports work anyway because `main.py:13` patches `sys.path`, and data paths come from `__file__`. (2026-11-22)
- **Refine "merge" saves unvalidated values.** `setattr` in `main.py:324/351` bypasses Pydantic, so a bad LLM value gets saved and the entity then fails to load (vanishes from lists, 500 on edit). Verified (KI-016). (2026-11-22)
- **`ollama` must be ≥ 0.4.** The code uses `response.message.content` (`agents/specialist.py:54`, `agents/writer.py:59`), but `app/requirements.txt` pins 0.3.3 (KI-004). `writer.py` imports it unguarded, so a missing package = server won't start (KI-003). (2026-11-22)
- **`slug` is required** in `Character`/`Scene`. Frontend save payloads omit it, so you get a 422 (KI-001). Verified by validating the payload against `models.py`. (2026-11-22)
- **`apiPost` (frontend) returns the raw `Response`**, unlike `apiGet`/`apiPut`, which return JSON. Always `await res.json()` (KI-002). (2026-11-22)
- **Pydantic v2 does not coerce int → str.** An LLM returning `"age": 17` or `"type": "supporting"` fails `Character(**…)`, and the entity is silently dropped (KI-016). (2026-11-22)
- **Two Pythons on the dev machine.** `py` (3.14.5) has the web deps; `python` (3.14.0) is a different install. Use `py` for backend checks. Running `py -I` hides user-site packages. (2026-11-22)
- **Git Bash noise.** Every Bash call on this machine prints `/etc/mtab`, `/etc/hosts` … "Permission denied" lines from the shell profile. They are harmless; ignore them. (2026-11-22)
- **`data/` is the user's novel.** Never use it as a scratch area. Test with `zz_test_` entities and delete them afterwards. (2026-11-22)
