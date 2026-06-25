#!/usr/bin/env python3
"""session-worklog: record what each Claude session did, and warn on a dirty exit.

A companion to worktree-guard.py, kept separate so logging can never
destabilise the stomp-guard. STRICTLY observational: it reads git state and
appends a record. It NEVER commits, pushes, stashes, prunes, cleans, resets,
or removes anything.

It closes the gap that once stranded finished-but-uncommitted work unnoticed
across a context reset: a session that ends with a dirty tree or unpushed
commits now leaves a visible warning plus an audit record, instead of silence.
(The work always survived in the bind-mounted tree — the failure was that
nothing flagged it.)

Records land one NDJSON line per touched repo in:
    <repo>/.git/claude-sessions/worklog.ndjson
shared across containers via the bind-mounted .git, never committed (it sits
inside .git). The directory is shared with worktree-guard's session registry.

Dispatch via argv[1]:
  start   SessionStart — stamp {sid, repo, head, ts} to /tmp so `stop` can
          compute the session's commit delta.
  stop    SessionEnd — for each repo this session is known to have touched,
          append a work record and (on SessionEnd) warn on dirty/unpushed
          state.

Deliberately cheap: no `git fsck`. Dangling-commit scanning is too slow to run
on every session end over a 9p bind mount, and that clutter auto-expires; the
high-value, low-cost signals are uncommitted tree + unpushed commits.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


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
        return out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def repo_paths(path: str) -> tuple[str, str] | None:
    """Return (worktree_top, git_common_dir) for the repo containing `path`."""
    here = path if os.path.isdir(path) else (os.path.dirname(path) or ".")
    top = git(here, "rev-parse", "--show-toplevel")
    common = git(here, "rev-parse", "--git-common-dir")
    if not top or not common:
        return None
    if not os.path.isabs(common):
        common = os.path.abspath(os.path.join(here, common))
    return top, common


def stamp_path(my_sid: str) -> Path:
    return Path(f"/tmp/claude-worklog-{my_sid}.json")


def handle_start(ev: dict) -> int:
    cwd = ev.get("cwd") or os.getcwd()
    paths = repo_paths(cwd)
    if not paths:
        return 0
    top, _common = paths
    try:
        stamp_path(sid(ev)).write_text(json.dumps({
            "sid": sid(ev),
            "repo": top,
            "start_head": git(top, "rev-parse", "HEAD") or "",
            "start_ts": time.time(),
        }))
    except OSError:
        pass
    return 0


def _porcelain_counts(top: str) -> tuple[int, int]:
    """(tracked_changes, untracked_files) from `git status --porcelain`."""
    out = git(top, "status", "--porcelain")
    if not out:
        return 0, 0
    tracked = untracked = 0
    for line in out.splitlines():
        if line.startswith("??"):
            untracked += 1
        else:
            tracked += 1
    return tracked, untracked


def _ahead_behind(top: str) -> tuple[int, int] | None:
    """(ahead, behind) vs the tracked upstream, or None when there is none."""
    out = git(top, "rev-list", "--count", "--left-right", "@{u}...HEAD")
    if not out:
        return None
    try:
        # --left-right with `@{u}...HEAD`: left = upstream-only (behind),
        # right = HEAD-only (ahead).
        behind, ahead = (int(x) for x in out.split())
    except ValueError:
        return None
    return ahead, behind


def _record_for(top: str, ev: dict, stamp: dict | None) -> dict:
    head = git(top, "rev-parse", "HEAD") or ""
    tracked, untracked = _porcelain_counts(top)
    ab = _ahead_behind(top)
    rec = {
        "sid": sid(ev),
        "ts": time.time(),
        "event": ev.get("hook_event_name") or "",
        "repo": top,
        "branch": git(top, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": head[:12],
        "dirty_tracked": tracked,
        "untracked": untracked,
        "ahead": ab[0] if ab else None,
        "behind": ab[1] if ab else None,
    }
    if stamp and stamp.get("repo") == top and stamp.get("start_head"):
        start = stamp["start_head"]
        rec["start_head"] = start[:12]
        cnt = git(top, "rev-list", "--count", f"{start}..HEAD")
        rec["commits_this_session"] = int(cnt) if cnt and cnt.isdigit() else None
        # `diff --stat` is filenames + line counts only (never content), so it
        # is safe to log — no secret values land in the work log.
        stat = git(top, "diff", "--stat", f"{start}..HEAD")
        rec["session_diffstat"] = stat.splitlines()[-1].strip() if stat else ""
    return rec


def _warn(rec: dict) -> None:
    parts = []
    if rec["dirty_tracked"] or rec["untracked"]:
        parts.append(
            f"{rec['dirty_tracked']} uncommitted + {rec['untracked']} untracked file(s)"
        )
    if rec.get("ahead"):
        parts.append(f"{rec['ahead']} commit(s) not pushed")
    if not parts:
        return
    sys.stderr.write(
        f"session-worklog: ending in {rec['repo']} on '{rec['branch']}' with "
        + "; ".join(parts)
        + ".\nCommit / push / stash before it's forgotten — the work is safe in "
        + "the tree, but nothing else will flag it.\n"
    )


def handle_stop(ev: dict) -> int:
    sp = stamp_path(sid(ev))
    stamp = None
    if sp.exists():
        try:
            stamp = json.loads(sp.read_text())
        except (json.JSONDecodeError, OSError):
            stamp = None

    # Repos this session is known to have touched: the start-stamp repo and
    # the end cwd's repo (usually the same). Single-repo is the common case;
    # mid-session hops to other repos beyond these two are not tracked, by
    # design (this hook only fires at start/end, not per edit).
    repos: dict[str, str] = {}  # top -> common
    for cand in (stamp.get("repo") if stamp else None, ev.get("cwd") or os.getcwd()):
        if not cand:
            continue
        paths = repo_paths(cand)
        if paths:
            repos[paths[0]] = paths[1]

    is_end = ev.get("hook_event_name") == "SessionEnd"
    for top, common in repos.items():
        rec = _record_for(top, ev, stamp)
        reg = Path(common) / "claude-sessions"
        try:
            reg.mkdir(parents=True, exist_ok=True)
            with (reg / "worklog.ndjson").open("a") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError as e:
            sys.stderr.write(f"session-worklog: could not write log: {e}\n")
        if is_end:
            _warn(rec)

    if is_end:
        try:
            sp.unlink()
        except OSError:
            pass
    return 0


HANDLERS = {
    "start": handle_start,
    "stop": handle_stop,
}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in HANDLERS:
        return 0
    try:
        return HANDLERS[mode](event())
    except Exception as e:  # never fail or delay a session on a logging hook
        sys.stderr.write(f"session-worklog {mode}: {e}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
