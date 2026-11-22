#!/usr/bin/env python3
"""
AI workflow automation for NovelForge AI (Claude Code hooks + manual CLI).

Subcommands
-----------
  save-plan                 PostToolUse(ExitPlanMode) hook. Reads the hook JSON from stdin and saves
                            the approved plan to docs/ai/plans/NNN-<slug>.md, then rebuilds INDEX.md.
  save-plan --from-file P   Manual save of a plan stored in markdown file P (other AI tools / fallback).
  stop-check                Stop hook. Blocks finishing ONCE when source files have uncommitted
                            changes but docs/CHANGELOG.md does not.
  reindex                   Rebuild docs/ai/plans/INDEX.md from each plan's front-matter.
  next-id                   Print the next free plan number (3 digits).

Design rules
------------
* Standard library only (runs on any Python 3.8+).
* Never breaks the session: every error is appended to .claude/hooks/hook-errors.log and the
  process exits 0 (a broken hook must not block the user).
* stdout carries ONLY hook-protocol JSON (ASCII-escaped, safe on any Windows code page).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[2]          # <repo>/.claude/hooks/ai_workflow.py
PLANS_DIR = ROOT / "docs" / "ai" / "plans"
CHANGELOG_REL = "docs/CHANGELOG.md"          # repo-relative, POSIX
INDEX_FILE = PLANS_DIR / "INDEX.md"
ERROR_LOG = ROOT / ".claude" / "hooks" / "hook-errors.log"

PLAN_FILE_RE = re.compile(r"^(\d{3,})-.*\.md$")
ACTIVE_STATUSES = {"approved", "in-progress"}

# Source paths that require a CHANGELOG entry when changed (prefix match, POSIX separators).
SOURCE_PREFIXES = ("app/",)                    # all application code lives in app/
SOURCE_FILES: set = set()                       # extra root-level files, none today
IGNORED_PARTS = ("__pycache__/",)
IGNORED_SUFFIXES = (".pyc", ".pyo")

# Doc-impact hints (mirror of docs/ai/RULES.md section 6), used in the Stop-hook message.
DOC_HINTS = [
    ("app/backend/main.py", ["docs/technical/04-api-reference.md", "docs/technical/02-workflows.md"]),
    ("app/backend/models.py", ["docs/technical/05-data-model-and-storage.md", "docs/technical/04-api-reference.md"]),
    ("app/backend/pipeline/", ["docs/technical/02-workflows.md", "docs/technical/03-low-level-design.md"]),
    ("app/backend/agents/", ["docs/technical/03-low-level-design.md", "docs/technical/06-configuration.md"]),
    ("app/backend/managers/", ["docs/technical/05-data-model-and-storage.md", "docs/technical/03-low-level-design.md"]),
    ("app/frontend/", ["docs/technical/03-low-level-design.md", "docs/technical/07-setup-and-usage.md"]),
    ("app/requirements.txt", ["docs/technical/07-setup-and-usage.md", "docs/technical/06-configuration.md"]),
    ("app/start.bat", ["docs/technical/07-setup-and-usage.md", "docs/technical/06-configuration.md"]),
]


# ───────────────────────────── helpers ─────────────────────────────
def log_error(msg: str) -> None:
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"[{now_iso()}] {msg}\n")
    except Exception:
        pass


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def emit(obj: dict) -> None:
    """Write hook-protocol JSON to stdout (ASCII only)."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=True))
    sys.stdout.flush()


def read_stdin_json() -> dict:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError as exc:
        log_error(f"stdin is not JSON: {exc}")
        return {}


def slugify(text: str, max_len: int = 60) -> str:
    s = text.lower()
    s = re.sub(r"[`*_#>\[\]()]", " ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rsplit("-", 1)[0] or s[:max_len]
    return s or "plan"


def extract_title(plan: str, fallback: str) -> str:
    for line in plan.splitlines():
        m = re.match(r"^\s{0,3}#{1,3}\s+(.+?)\s*#*\s*$", line)
        if m:
            title = re.sub(r"^(plan|implementation plan)\s*[:\-–]\s*", "", m.group(1).strip(), flags=re.I)
            return title.strip() or m.group(1).strip()
    for line in plan.splitlines():
        if line.strip():
            return line.strip()[:80]
    return fallback


# ─────────────────────── plan front-matter I/O ───────────────────────
def parse_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    meta: dict = {}
    for i in range(1, len(lines)):
        line = lines[i].rstrip("\r\n")
        if line.strip() == "---":
            return meta, "".join(lines[i + 1:])
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                try:
                    val = json.loads(val) if val[0] == '"' else val[1:-1]
                except Exception:
                    val = val[1:-1]
            meta[key] = val
    return {}, text  # no closing fence -> treat as no front-matter


def set_front_matter_value(path: pathlib.Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(rf"(?m)^{re.escape(key)}:.*$", f"{key}: {value}", text, count=1)
    if n == 0 and text.startswith("---"):
        new = text.replace("---\n", f"---\n{key}: {value}\n", 1)
    path.write_text(new, encoding="utf-8")


def load_plans() -> list[dict]:
    plans = []
    if not PLANS_DIR.exists():
        return plans
    for p in sorted(PLANS_DIR.iterdir()):
        m = PLAN_FILE_RE.match(p.name)
        if not (p.is_file() and m):
            continue
        try:
            meta, _ = parse_front_matter(p.read_text(encoding="utf-8"))
        except Exception as exc:
            log_error(f"cannot read {p.name}: {exc}")
            meta = {}
        plans.append({"num": int(m.group(1)), "path": p, "meta": meta})
    plans.sort(key=lambda d: d["num"])
    return plans


def next_number(plans: list[dict]) -> int:
    return (max((p["num"] for p in plans), default=0)) + 1


# ───────────────────────────── reindex ─────────────────────────────
def reindex() -> pathlib.Path:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plans = load_plans()
    rows = []
    active = []
    for p in plans:
        meta = p["meta"]
        num = f"{p['num']:03d}"
        title = str(meta.get("title") or p["path"].stem).replace("|", "\\|")
        status = str(meta.get("status") or "unknown")
        approved = str(meta.get("approved") or "")[:10] or "—"
        sup = str(meta.get("supersedes") or "").strip() or "—"
        rows.append(f"| {num} | [{title}]({p['path'].name}) | `{status}` | {approved} | {sup} |")
        if status in ACTIVE_STATUSES:
            active.append(f"{num} — {title} (`{status}`)")
    nxt = f"{next_number(plans):03d}"
    out = [
        "# Plans index",
        "",
        "> **Auto-generated** by `.claude/hooks/ai_workflow.py` from each plan's front-matter. Do not edit by hand:",
        "> change `status:` inside the plan file, then run `python .claude/hooks/ai_workflow.py reindex`.",
        "> Status lifecycle: `approved` → `in-progress` → `done` | `abandoned` | `superseded`.",
        "",
        f"**Active:** {'; '.join(active) if active else 'none'}  ",
        f"**Next number:** {nxt}  ",
        f"**Total plans:** {len(plans)}",
        "",
        "| # | Title | Status | Approved | Supersedes |",
        "|---|---|---|---|---|",
        *(rows or ["| — | _no plans yet_ | — | — | — |"]),
        "",
    ]
    INDEX_FILE.write_text("\n".join(out), encoding="utf-8")
    return INDEX_FILE


# ──────────────────────────── save-plan ────────────────────────────
def _plan_from_payload(payload: dict) -> tuple[str, str]:
    """Return (plan_markdown, source_file) from a PostToolUse(ExitPlanMode) payload."""
    resp = payload.get("tool_response")
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except Exception:
            resp = {"plan": resp}
    if not isinstance(resp, dict):
        resp = {}
    tin = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}

    plan = resp.get("plan") or tin.get("plan") or ""
    src = resp.get("filePath") or resp.get("file_path") or tin.get("planFilePath") or tin.get("filePath") or ""
    if not plan and src:
        try:
            plan = pathlib.Path(src).expanduser().read_text(encoding="utf-8")
        except Exception as exc:
            log_error(f"plan text missing and cannot read source file {src!r}: {exc}")
    return str(plan or ""), str(src or "")


def save_plan(plan: str, source_file: str, session: str) -> dict:
    plan = plan.lstrip("\ufeff").strip()  # drop a UTF-8 BOM if present
    if not plan:
        return {"saved": False, "reason": "empty plan"}
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plans = load_plans()
    digest = hashlib.sha256(plan.encode("utf-8")).hexdigest()

    for p in plans:  # exact duplicate (e.g. hook fired twice)
        if p["meta"].get("sha256") == digest:
            return {"saved": False, "reason": "duplicate", "path": p["path"], "num": p["num"]}

    supersedes = None
    if source_file and source_file != "manual":
        for p in reversed(plans):
            if p["meta"].get("source_file") == source_file and p["meta"].get("status") in ACTIVE_STATUSES:
                supersedes = p
                break

    num = next_number(plans)
    fallback = pathlib.Path(source_file).stem if source_file else f"plan-{num:03d}"
    title = extract_title(plan, fallback)
    path = PLANS_DIR / f"{num:03d}-{slugify(title)}.md"

    fm = [
        "---",
        f"id: {num:03d}",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        "status: approved",
        f"approved: {now_iso()}",
        f"session: {session or 'unknown'}",
        f"source_file: {json.dumps(source_file or 'manual', ensure_ascii=False)}",
    ]
    if supersedes:
        fm.append(f"supersedes: {supersedes['num']:03d}")
    fm += [f"sha256: {digest}", "---", ""]

    body = [
        "> Auto-saved on approval by `.claude/hooks/ai_workflow.py`. Keep `status:` current "
        "(approved → in-progress → done | abandoned | superseded) and run `reindex` after changing it.",
        "",
        plan,
        "",
        "---",
        "",
        "## Execution log",
        "<!-- Claude: set status to in-progress when you start; tick items; note deviations from the plan. -->",
        "- [ ] Implementation started (status → in-progress)",
        "- [ ] Code changes complete",
        "- [ ] Verified (RULES.md §9)",
        f"- [ ] docs/CHANGELOG.md [Unreleased] updated (cite `[plan {num:03d}]`)",
        "- [ ] Docs updated per RULES.md §6 (+ docs/technical/09 KI status)",
        "- [ ] docs/ai/memory/project-state.md updated",
        "- [ ] Status → done (or abandoned with reason) and `reindex` run",
        "",
        "## Outcome",
        "_Fill in when finished: what shipped, files changed, KIs fixed, CHANGELOG line(s), verification results, follow-ups._",
        "",
    ]
    path.write_text("\n".join(fm + body), encoding="utf-8")

    if supersedes:
        try:
            set_front_matter_value(supersedes["path"], "status", "superseded")
        except Exception as exc:
            log_error(f"could not mark {supersedes['path'].name} superseded: {exc}")
    reindex()
    return {"saved": True, "path": path, "num": num, "supersedes": supersedes["num"] if supersedes else None}


def cmd_save_plan(argv: list[str]) -> None:
    if "--from-file" in argv:
        i = argv.index("--from-file")
        src = argv[i + 1] if i + 1 < len(argv) else ""
        plan = pathlib.Path(src).read_text(encoding="utf-8") if src else ""
        res = save_plan(plan, "manual", "manual")
        rel = res.get("path").relative_to(ROOT).as_posix() if res.get("path") else ""
        print(f"saved={res['saved']} reason={res.get('reason', '')} path={rel}".strip())
        return

    payload = read_stdin_json()
    if payload.get("tool_name") not in (None, "ExitPlanMode"):
        return
    plan, src = _plan_from_payload(payload)
    if not plan:
        log_error("save-plan: no plan content in payload; keys="
                  f"{sorted(payload.keys())} tool_response_type={type(payload.get('tool_response')).__name__}")
        return
    res = save_plan(plan, src, str(payload.get("session_id") or ""))
    path = res.get("path")
    rel = path.relative_to(ROOT).as_posix() if path else "?"
    num = f"{res.get('num', 0):03d}"
    if res.get("saved"):
        extra = f" It supersedes plan {res['supersedes']:03d} (marked superseded)." if res.get("supersedes") else ""
        msg = (f"Approved plan auto-saved to {rel} (plan {num}).{extra} Per docs/ai/RULES.md section 8: set its "
               f"front-matter status to in-progress when you start, keep its Execution log current, cite "
               f"[plan {num}] in CHANGELOG lines, and at the end set status done, fill Outcome, and run "
               f"`python .claude/hooks/ai_workflow.py reindex`.")
    else:
        msg = f"This approved plan was already saved as {rel} (plan {num}); continue updating that file."
    emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}})


# ──────────────────────────── stop-check ────────────────────────────
def git_changed_files() -> list[str] | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain=v1", "-z", "-uall"],
            capture_output=True, timeout=15,
        )
    except Exception as exc:
        log_error(f"git status failed: {exc}")
        return None
    if out.returncode != 0:
        return None
    tokens = out.stdout.decode("utf-8", errors="replace").split("\0")
    files, i = [], 0
    while i < len(tokens):
        entry = tokens[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        files.append(path.replace("\\", "/"))
        if "R" in xy or "C" in xy:  # rename/copy: next token is the original path
            i += 1
    return files


def is_source(path: str) -> bool:
    if any(part in path for part in IGNORED_PARTS) or path.endswith(IGNORED_SUFFIXES):
        return False
    return path.startswith(SOURCE_PREFIXES) or path in SOURCE_FILES


def cmd_stop_check() -> None:
    payload = read_stdin_json()
    if payload.get("stop_hook_active"):
        return  # already continuing because of a stop hook -> never block twice
    changed = git_changed_files()
    if not changed:
        return
    src = [f for f in changed if is_source(f)]
    if not src or CHANGELOG_REL in changed:
        return
    docs = sorted({d for f in src for prefix, ds in DOC_HINTS if f.startswith(prefix) for d in ds})
    shown = ", ".join(src[:12]) + (f" (+{len(src) - 12} more)" if len(src) > 12 else "")
    reason = (
        "Workflow guard (docs/ai/RULES.md sections 6-7): files under app/ have uncommitted changes but docs/CHANGELOG.md "
        f"has none. Changed: {shown}. Before finishing: (1) add or refine a line under '## [Unreleased]' "
        "in docs/CHANGELOG.md citing [plan NNN] / [KI-NNN]; (2) review these docs for needed updates: "
        f"{', '.join(docs) or 'see docs/ai/RULES.md section 6'} (and docs/technical/09 if a KI changed); (3) update the active "
        "plan's status/Execution log in docs/ai/plans/ (then run reindex) and docs/ai/memory/project-state.md. "
        "If these changes are not yours or are a deliberate throwaway experiment, say so to the user instead "
        "of writing a changelog entry."
    )
    emit({"decision": "block", "reason": reason})


# ─────────────────────────────── main ───────────────────────────────
def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "save-plan":
        cmd_save_plan(argv[2:])
    elif cmd == "stop-check":
        cmd_stop_check()
    elif cmd == "reindex":
        print(f"rebuilt {reindex().relative_to(ROOT).as_posix()}")
    elif cmd == "next-id":
        print(f"{next_number(load_plans()):03d}")
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:
        log_error(f"unhandled error in {' '.join(sys.argv[1:])}:\n{traceback.format_exc()}")
    sys.exit(0)
