#!/usr/bin/env python3
"""worktree-guard: stop concurrent Claude sessions from stomping the same repo.

Registry lives inside each repo at <repo>/.git/claude-sessions/<sid>.json so
any container with that repo bind-mounted can see it. Stale entries (no
heartbeat for 30 minutes) get pruned on the next check.

Dispatch via argv[1]:
  check  PreToolUse on Edit/Write — block if another live session is on this
         repo and we're not in our own linked worktree.
  touch  PostToolUse on Edit/Write — refresh our heartbeat.
  stop   SessionEnd/Stop — remove every registry entry this session wrote.
  start  SessionStart — no-op; we don't know which repo we'll touch yet.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

STALE_SECONDS = 30 * 60


def event() -> dict:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def sid(ev: dict) -> str:
    return ev.get("session_id") or os.environ.get("CLAUDE_SESSION_ID") or "unknown"


def git(cwd: str, *args: str) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", cwd, *args], stderr=subprocess.DEVNULL, text=True
        ).strip()
        return out or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def repo_of(path: str) -> tuple[str, str] | None:
    """Return (worktree_root, common_git_dir) for the repo containing `path`."""
    here = path if os.path.isdir(path) else os.path.dirname(path) or "."
    top = git(here, "rev-parse", "--show-toplevel")
    common = git(here, "rev-parse", "--git-common-dir")
    if not top or not common:
        return None
    if not os.path.isabs(common):
        common = os.path.abspath(os.path.join(here, common))
    return top, common


def in_linked_worktree(top: str, common: str) -> bool:
    """True if `top` is a linked worktree, not the main checkout.

    In a worktree, `git rev-parse --git-dir` points at .git/worktrees/<name>,
    while --git-common-dir points at the main .git. In the main checkout the
    two paths resolve to the same place.
    """
    g = git(top, "rev-parse", "--git-dir")
    if not g:
        return False
    if not os.path.isabs(g):
        g = os.path.abspath(os.path.join(top, g))
    return os.path.realpath(g) != os.path.realpath(common)


def reg_dir(common: str) -> Path:
    d = Path(common) / "claude-sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stamp(common: str, my_sid: str, cwd: str) -> None:
    """Write/refresh our entry and remember it for cleanup on session end."""
    entry = reg_dir(common) / f"{my_sid}.json"
    entry.write_text(json.dumps({
        "session_id": my_sid,
        "cwd": cwd,
        "last_seen": time.time(),
    }))
    idx = Path(f"/tmp/claude-wg-{my_sid}.idx")
    seen = set(idx.read_text().splitlines()) if idx.exists() else set()
    if str(entry) not in seen:
        with idx.open("a") as f:
            f.write(f"{entry}\n")


def live_others(reg: Path, my_sid: str) -> list[dict]:
    """Sessions in `reg` other than mine that have heartbeat within STALE_SECONDS."""
    now = time.time()
    out: list[dict] = []
    for f in reg.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("session_id") == my_sid:
            continue
        if now - float(data.get("last_seen", 0)) > STALE_SECONDS:
            try:
                f.unlink()
            except OSError:
                pass
            continue
        out.append(data)
    return out


def handle_check(ev: dict) -> int:
    tin = ev.get("tool_input") or {}
    target = tin.get("file_path") or tin.get("path") or tin.get("notebook_path")
    if not target:
        return 0
    paths = repo_of(target)
    if not paths:
        return 0
    top, common = paths
    my_sid = sid(ev)
    others = live_others(reg_dir(common), my_sid)
    if not others or in_linked_worktree(top, common):
        stamp(common, my_sid, top)
        return 0
    summary = ", ".join(
        f"{o['session_id'][:8]} (cwd={o.get('cwd','?')})" for o in others
    )
    short = my_sid[:8]
    sys.stderr.write(
        f"worktree-guard: another Claude session is active in {top}: {summary}.\n"
        f"This session is in the main checkout; create your own worktree first:\n"
        f"  git -C {top} worktree add /tmp/claude-wt-{short} -b claude-{short}\n"
        f"  cd /tmp/claude-wt-{short}\n"
        f"Then retry the edit from inside that worktree.\n"
    )
    return 2


def handle_touch(ev: dict) -> int:
    tin = ev.get("tool_input") or {}
    target = tin.get("file_path") or tin.get("path") or tin.get("notebook_path")
    if not target:
        return 0
    paths = repo_of(target)
    if not paths:
        return 0
    top, common = paths
    stamp(common, sid(ev), top)
    return 0


def handle_stop(ev: dict) -> int:
    my_sid = sid(ev)
    idx = Path(f"/tmp/claude-wg-{my_sid}.idx")
    if not idx.exists():
        return 0
    for line in idx.read_text().splitlines():
        try:
            Path(line).unlink()
        except (OSError, FileNotFoundError):
            pass
    try:
        idx.unlink()
    except OSError:
        pass
    return 0


HANDLERS = {
    "check": handle_check,
    "touch": handle_touch,
    "stop": handle_stop,
    "start": lambda _ev: 0,
}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in HANDLERS:
        return 0
    try:
        return HANDLERS[mode](event())
    except Exception as e:
        sys.stderr.write(f"worktree-guard {mode}: {e}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
