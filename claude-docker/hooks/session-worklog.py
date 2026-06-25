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

Repos are discovered by **edit location**, not by the session's working
directory: a `PostToolUse` `touch` records the repo of each edited file into a
per-session index. This matters because sessions commonly run from a
multi-repo parent (e.g. `/workspaces/dev`, which is not itself a repo) and edit
several subrepos — keying on cwd alone would see none of them. The session's
start cwd and end cwd are also folded in when they are repos.

Records land one NDJSON line per touched repo in:
    <repo>/.git/claude-sessions/worklog.ndjson
shared across containers via the bind-mounted .git, never committed (it sits
inside .git). The directory is shared with worktree-guard's session registry.

Dispatch via argv[1]:
  start   SessionStart — record the cwd repo (if any) and its HEAD baseline.
  touch   PostToolUse on Edit/Write — record the edited file's repo + HEAD
          baseline on first sighting; cheap and idempotent thereafter.
  stop    SessionEnd — for every repo the session touched (plus the end cwd
          repo), append a work record and warn on dirty/unpushed state.

Deliberately cheap: no `git fsck`. Dangling-commit scanning is too slow to run
on a 9p bind mount, and that clutter auto-expires; the high-value, low-cost
signals are an uncommitted tree and unpushed commits.
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


def idx_path(my_sid: str) -> Path:
    """Per-session index of touched repos: {top: {common, start_head}}."""
    return Path(f"/tmp/claude-worklog-{my_sid}.json")


def _load_idx(p: Path) -> dict:
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _remember(my_sid: str, path: str) -> None:
    """Record the repo containing `path` (with its current HEAD as the session
    baseline) on first sighting. Idempotent: a repo already in the index keeps
    its original baseline."""
    paths = repo_paths(path)
    if not paths:
        return
    top, common = paths
    p = idx_path(my_sid)
    idx = _load_idx(p)
    if top not in idx:
        idx[top] = {"common": common, "start_head": git(top, "rev-parse", "HEAD") or ""}
        try:
            p.write_text(json.dumps(idx))
        except OSError:
            pass


def handle_start(ev: dict) -> int:
    _remember(sid(ev), ev.get("cwd") or os.getcwd())
    return 0


def handle_touch(ev: dict) -> int:
    tin = ev.get("tool_input") or {}
    target = tin.get("file_path") or tin.get("path") or tin.get("notebook_path")
    if target:
        _remember(sid(ev), target)
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
        # `@{u}...HEAD`: left = upstream-only (behind), right = HEAD-only (ahead).
        behind, ahead = (int(x) for x in out.split())
    except ValueError:
        return None
    return ahead, behind


def _record_for(top: str, start_head: str, ev: dict) -> dict:
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
    if start_head:
        rec["start_head"] = start_head[:12]
        cnt = git(top, "rev-list", "--count", f"{start_head}..HEAD")
        rec["commits_this_session"] = int(cnt) if cnt and cnt.isdigit() else None
        # `diff --stat` is filenames + line counts only (never content), so it
        # is safe to log — no secret values land in the work log.
        stat = git(top, "diff", "--stat", f"{start_head}..HEAD")
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
        + ".\nCommit / push / stash before it's forgotten; the work is safe in "
        + "the tree, but nothing else will flag it.\n"
    )


def handle_stop(ev: dict) -> int:
    my_sid = sid(ev)
    p = idx_path(my_sid)
    idx = _load_idx(p)

    # Fold in the end-of-session cwd repo (covers a session that only ran git
    # via Bash and never triggered an Edit/Write touch).
    end = repo_paths(ev.get("cwd") or os.getcwd())
    if end and end[0] not in idx:
        idx[end[0]] = {"common": end[1], "start_head": ""}

    is_end = ev.get("hook_event_name") == "SessionEnd"
    for top, meta in idx.items():
        common = meta.get("common") or ""
        rec = _record_for(top, meta.get("start_head") or "", ev)
        if common:
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
            p.unlink()
        except OSError:
            pass
    return 0


def _reported_path(my_sid: str) -> Path:
    """Per-session set of repos already nagged about (dedup: once per repo)."""
    return Path(f"/tmp/claude-worklog-reported-{my_sid}.json")


def _load_reported(p: Path) -> set:
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list):
                return set(data)
        except (json.JSONDecodeError, OSError):
            pass
    return set()


def _last_record(log: Path) -> dict | None:
    """Last NDJSON record in a worklog file, or None."""
    try:
        lines = [ln for ln in log.read_text().splitlines() if ln.strip()]
    except OSError:
        return None
    for ln in reversed(lines):
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            return rec
    return None


def handle_report(ev: dict) -> int:
    """Surface the PREVIOUS session's unshown dirty/unpushed warning for the
    repo this event lands in — the cwd repo on SessionStart, or the edited
    file's repo on PreToolUse. Once per repo per session.

    Read-only: it reads the repo's worklog.ndjson (written by a prior session's
    SessionEnd) and, if that last record was dirty/unpushed, emits the warning
    via the additionalContext channel (verified visible on SessionStart and
    PreToolUse) — the surface SessionEnd never had. It does NOT re-check live
    git state (that would drag git into the hot path), so a warning the user
    has since resolved without ending a session may nag once — an accepted
    trade. The additionalContext JSON must be the only thing on stdout.
    """
    tin = ev.get("tool_input") or {}
    target = (
        tin.get("file_path") or tin.get("path") or tin.get("notebook_path")
        or ev.get("cwd") or os.getcwd()
    )
    paths = repo_paths(target)
    if not paths:
        return 0  # not in a repo (e.g. the /workspaces/dev parent) — skip per design
    top, common = paths

    rp = _reported_path(sid(ev))
    reported = _load_reported(rp)
    if top in reported:
        return 0
    reported.add(top)
    try:
        rp.write_text(json.dumps(sorted(reported)))
    except OSError:
        pass

    rec = _last_record(Path(common) / "claude-sessions" / "worklog.ndjson")
    if not rec:
        return 0
    dirty = int(rec.get("dirty_tracked") or 0)
    untracked = int(rec.get("untracked") or 0)
    ahead = int(rec.get("ahead") or 0)
    if not (dirty or untracked or ahead):
        return 0  # last session left it clean — nothing to nag about

    when = ""
    ts = rec.get("ts")
    if isinstance(ts, (int, float)):
        when = time.strftime(" (%Y-%m-%d %H:%M)", time.localtime(ts))
    bits = []
    if dirty or untracked:
        bits.append(f"{dirty} uncommitted + {untracked} untracked file(s)")
    if ahead:
        bits.append(f"{ahead} commit(s) not pushed")
    msg = (
        f"[session-worklog] A previous session{when} ended in {top} on "
        f"'{rec.get('branch')}' with " + "; ".join(bits)
        + ". This may be unfinished work that was never shown live (SessionEnd "
        "has no console); surface it to the user so it isn't forgotten."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": ev.get("hook_event_name") or "SessionStart",
            "additionalContext": msg,
        }
    }))
    return 0


HANDLERS = {
    "start": handle_start,
    "touch": handle_touch,
    "stop": handle_stop,
    "report": handle_report,
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
