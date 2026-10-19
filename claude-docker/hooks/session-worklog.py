#!/usr/bin/env python3
"""session-worklog: record how each Claude session left its repos, and warn on a dirty exit.

STRICTLY observational: it reads git state and appends a record. It NEVER
commits, pushes, stashes, prunes, cleans, resets, or removes anything.

It closes the gap that once stranded finished-but-uncommitted work unnoticed
across a context reset: a session that ends with a dirty tree or unpushed
commits now leaves a visible warning plus a state record, instead of silence.
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
inside .git).

Dispatch via argv[1]:
  start   SessionStart — record the cwd repo (if any), then `report` on it.
  report  PreToolUse on Edit/Write — surface a previous session's dirty exit
          for the edited file's repo, once per repo per session.
  touch   PostToolUse on Edit/Write — record the edited file's repo on first
          sighting; cheap and idempotent thereafter.
  stop    SessionEnd — for every repo the session touched (plus the end cwd
          repo), append a state record (branch, dirty/untracked/unpushed
          counts — exactly what `report` reads) and warn on dirty/unpushed.

Deliberately cheap: no `git fsck`. Dangling-commit scanning is too slow to run
on a 9p bind mount, and that clutter auto-expires; the high-value, low-cost
signals are an uncommitted tree and unpushed commits. The hot path (report and
touch, on every edit) caches directory -> repo per session, so only the first
edit in a directory pays for git.
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


def _existing_dir(path: str) -> str:
    """Nearest existing directory at or above `path`. A Write into a new
    directory fires PreToolUse before that directory exists."""
    here = path if os.path.isdir(path) else (os.path.dirname(path) or ".")
    while not os.path.isdir(here):
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return here


def _repo_paths_at(here: str) -> tuple[str, str] | None:
    """(worktree_top, git_common_dir) for the repo containing directory `here`,
    in a single git call (each one costs ~45 ms on a 9p bind mount)."""
    out = git(here, "rev-parse", "--show-toplevel", "--git-common-dir")
    lines = out.splitlines() if out else []
    if len(lines) != 2:
        return None
    top, common = lines
    if not os.path.isabs(common):
        common = os.path.abspath(os.path.join(here, common))
    return top, common


def _load_json(p: Path, kind: type):
    try:
        data = json.loads(p.read_text())
        if isinstance(data, kind):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return kind()


def _save_json(p: Path, data) -> None:
    """Write via rename so a concurrent reader never sees a torn file."""
    tmp = p.with_name(f"{p.name}.{os.getpid()}")
    try:
        tmp.write_text(json.dumps(data))
        os.replace(tmp, p)
    except OSError:
        pass


def _dirs_path(my_sid: str) -> Path:
    """Per-session cache of directory -> [top, common] (or null: not a repo)."""
    return Path(f"/tmp/claude-worklog-dirs-{my_sid}.json")


def repo_paths(path: str, my_sid: str) -> tuple[str, str] | None:
    """Return (worktree_top, git_common_dir) for the repo containing `path`.

    Cached per directory for the session, so repeat edits in a directory cost
    no git call at all. A directory that becomes a repo mid-session (git init)
    stays cached as "not a repo" — an accepted trade for the hot path."""
    here = _existing_dir(path)
    p = _dirs_path(my_sid)
    cache = _load_json(p, dict)
    if here in cache:
        hit = cache[here]
        return (hit[0], hit[1]) if hit else None
    paths = _repo_paths_at(here)
    cache[here] = list(paths) if paths else None
    _save_json(p, cache)
    return paths


def idx_path(my_sid: str) -> Path:
    """Per-session index of touched repos: {top: {common}}."""
    return Path(f"/tmp/claude-worklog-{my_sid}.json")


def _remember(my_sid: str, path: str) -> None:
    """Record the repo containing `path` on first sighting. Idempotent."""
    paths = repo_paths(path, my_sid)
    if not paths:
        return
    top, common = paths
    p = idx_path(my_sid)
    idx = _load_json(p, dict)
    if top not in idx:
        idx[top] = {"common": common}
        _save_json(p, idx)


def handle_start(ev: dict) -> int:
    """Record the cwd repo, then report on it — one process and one repo
    lookup instead of separate `start` and `report` hooks."""
    cwd = ev.get("cwd") or os.getcwd()
    _remember(sid(ev), cwd)
    return _report(ev, cwd)


def handle_touch(ev: dict) -> int:
    tin = ev.get("tool_input") or {}
    target = tin.get("file_path") or tin.get("path") or tin.get("notebook_path")
    if target:
        _remember(sid(ev), target)
    return 0


def _record_for(top: str, ev: dict) -> dict:
    """Exactly what `report` reads, from one `git status --porcelain=v2
    --branch` call: branch, ahead/behind (only when an upstream is set), and
    tracked vs untracked change counts. Paths are counted, never logged."""
    rec = {
        "sid": sid(ev),
        "ts": time.time(),
        "event": ev.get("hook_event_name") or "",
        "repo": top,
        "branch": None,
        "dirty_tracked": 0,
        "untracked": 0,
        "ahead": None,
        "behind": None,
    }
    out = git(top, "status", "--porcelain=v2", "--branch") or ""
    for line in out.splitlines():
        if line.startswith("# branch.head "):
            rec["branch"] = line[len("# branch.head "):]
        elif line.startswith("# branch.ab "):
            ahead, behind = line.split()[2:4]  # "+A", "-B"
            rec["ahead"], rec["behind"] = int(ahead), -int(behind)
        elif line.startswith("? "):
            rec["untracked"] += 1
        elif not line.startswith("#"):
            rec["dirty_tracked"] += 1
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
    idx = _load_json(p, dict)

    # Fold in the end-of-session cwd repo (covers a session that only ran git
    # via Bash and never triggered an Edit/Write touch).
    end = repo_paths(ev.get("cwd") or os.getcwd(), my_sid)
    if end and end[0] not in idx:
        idx[end[0]] = {"common": end[1]}

    is_end = ev.get("hook_event_name") == "SessionEnd"
    for top, meta in idx.items():
        common = meta.get("common") or ""
        rec = _record_for(top, ev)
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
        for f in (p, _dirs_path(my_sid), _reported_path(my_sid)):
            try:
                f.unlink()
            except OSError:
                pass
    return 0


def _reported_path(my_sid: str) -> Path:
    """Per-session set of repos already nagged about (dedup: once per repo)."""
    return Path(f"/tmp/claude-worklog-reported-{my_sid}.json")


def _last_record(log: Path) -> dict | None:
    """Last NDJSON record in a worklog file, or None. Reads only the tail: the
    log grows by a line per session, forever."""
    try:
        with log.open("rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 16384))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    # A partial first line fails to parse and is skipped.
    for ln in reversed(tail.splitlines()):
        if not ln.strip():
            continue
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
    return _report(ev, target)


def _report(ev: dict, target: str) -> int:
    my_sid = sid(ev)
    paths = repo_paths(target, my_sid)
    if not paths:
        return 0  # not in a repo (e.g. the /workspaces/dev parent) — skip per design
    top, common = paths

    rp = _reported_path(my_sid)
    reported = _load_json(rp, list)
    if top in reported:
        return 0
    reported.append(top)
    _save_json(rp, sorted(reported))

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
