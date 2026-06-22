#!/usr/bin/env python3
"""worktree-guard: stop concurrent Claude sessions from stomping the same repo.

Both the session registry and the per-session worktrees live inside the repo's
shared .git, so every container with that repo bind-mounted sees a consistent
view:
  * registry:  <repo>/.git/claude-sessions/<sid>.json   (heartbeats)
  * worktrees: <repo>/.git/claude-worktrees/claude-<sid8>/

Putting worktrees under the shared .git — never in container-local /tmp — is
what keeps a peer container from seeing them as missing and reaping them with
`git worktree prune`. Stale registry entries (no heartbeat for 30 minutes) are
pruned on the next check.

Dispatch via argv[1]:
  check       PreToolUse on Edit/Write — block if another live session is on
              this repo and we're not in our own linked worktree; point the
              caller at a worktree under the shared .git.
  touch       PostToolUse on Edit/Write — refresh our heartbeat.
  bash-guard  PreToolUse on Bash — refuse `git worktree prune` / `git worktree
              remove` that would delete a live peer's worktree out from under
              it (git offers no registry-aware guard for those, and a bare
              `prune` ignores gc.worktreePruneExpire).
  stop        SessionEnd/Stop — remove every registry entry this session wrote.
              On SessionEnd only, also garbage-collect linked worktrees of the
              repos this session touched that are safe to reap: clean, unlocked,
              holding no live session, and already landed (merged into
              origin/main or tracking a now-gone upstream — squash-on-merge).
  start       SessionStart — no-op; we don't know which repo we'll touch yet.
"""

import json
import os
import re
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


def worktree_path(common: str, short: str) -> str:
    """Per-session worktree dir, under the shared .git so every container sees
    it — and so no peer's `git worktree prune` treats it as a missing dir."""
    return os.path.join(common, "claude-worktrees", f"claude-{short}")


def ensure_repo_config(common: str) -> None:
    """Best-effort repo config that hardens worktree lifecycle for concurrent
    containers. Idempotent; only writes when the value actually differs.

      gc.worktreePruneExpire=never   — keep background `git gc` from reaping a
        worktree whose dir merely looks missing. (A bare `git worktree prune`
        ignores this, which is why bash-guard exists too.)
      worktree.useRelativePaths=true — relative link files round-trip across
        containers/host (git >= 2.48; harmless no-op on older git).
    """
    main = os.path.dirname(common)  # git-common-dir is always <main>/.git
    for key, val in (
        ("gc.worktreePruneExpire", "never"),
        ("worktree.useRelativePaths", "true"),
    ):
        if git(main, "config", "--get", key) != val:
            git(main, "config", key, val)


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
    ensure_repo_config(common)
    my_sid = sid(ev)
    others = live_others(reg_dir(common), my_sid)
    if not others or in_linked_worktree(top, common):
        stamp(common, my_sid, top)
        return 0
    summary = ", ".join(
        f"{o['session_id'][:8]} (cwd={o.get('cwd','?')})" for o in others
    )
    short = my_sid[:8]
    wt = worktree_path(common, short)
    sys.stderr.write(
        f"worktree-guard: another Claude session is active in {top}: {summary}.\n"
        f"This session is in the main checkout; create your own worktree on the\n"
        f"shared .git first (NOT /tmp — peer containers can't see /tmp, and would\n"
        f"reap the worktree as 'missing'):\n"
        f"  git -C {top} worktree add {wt} -b claude-{short}\n"
        f"  cd {wt}\n"
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
    ensure_repo_config(common)
    stamp(common, sid(ev), top)
    return 0


def live_peer_under(others: list[dict], path: str) -> bool:
    """True if any live peer session's cwd is at or under `path`."""
    rp = os.path.realpath(path)
    for o in others:
        cwd = os.path.realpath(o.get("cwd", ""))
        if cwd == rp or cwd.startswith(rp + os.sep):
            return True
    return False


# Matches a `git ... worktree ... (prune|remove)` within one simple command
# segment (stops at ; | &), so it won't fire across an unrelated chained cmd.
_WT_DESTRUCTIVE = re.compile(r"\bgit\b[^\n;|&]*\bworktree\b[^\n;|&]*\b(prune|remove)\b")


def _remove_targets(cmd: str) -> list[str]:
    """Path args of a `git worktree remove` (non-flag tokens after `remove`).
    Best-effort shell-naive split — good enough to tell which worktree is hit."""
    toks = cmd.split()
    try:
        i = toks.index("remove")
    except ValueError:
        return []
    return [t for t in toks[i + 1:] if not t.startswith("-")]


def handle_bash_guard(ev: dict) -> int:
    """Block a `git worktree prune`/`remove` that would yank a live peer's
    worktree. The shared-.git location already stops a *bare* prune from seeing
    peer worktrees as missing; this also covers an explicit `remove <path>` and
    a `prune` aimed at a repo where peers are live."""
    cmd = (ev.get("tool_input") or {}).get("command") or ""
    m = _WT_DESTRUCTIVE.search(cmd)
    if not m:
        return 0
    action = m.group(1)
    cwd = ev.get("cwd") or os.getcwd()
    paths = repo_of(cwd)
    if not paths:
        return 0
    top, common = paths
    others = live_others(reg_dir(common), sid(ev))
    if not others:
        return 0
    # `remove <path>`: only block when a live peer sits under a targeted path —
    # removing your own or a genuinely dead worktree stays allowed.
    if action == "remove":
        targets = _remove_targets(cmd)
        rooted = [t if os.path.isabs(t) else os.path.join(cwd, t) for t in targets]
        if targets and not any(live_peer_under(others, t) for t in rooted):
            return 0
    summary = ", ".join(
        f"{o['session_id'][:8]} (cwd={o.get('cwd','?')})" for o in others
    )
    sys.stderr.write(
        f"worktree-guard: refusing `git worktree {action}` — another Claude session "
        f"is live in {top}: {summary}.\n"
        f"That can delete a peer session's worktree registration and break it "
        f"mid-run.\n"
        f"Peer worktrees live under {common}/claude-worktrees/ and their registry "
        f"entries self-expire after 30 min idle, so there is nothing to reap by "
        f"hand while a peer is active.\n"
        f"To remove a specific dead worktree, target its exact path and confirm no "
        f"live session cwd sits under it.\n"
    )
    return 2


def worktrees(main: str) -> list[dict]:
    """Parse `git worktree list --porcelain` from the main checkout.

    First record is the main worktree; the rest are linked. `locked` and
    `detached` are flagged when present. branch is the short ref name.
    """
    out = git(main, "worktree", "list", "--porcelain")
    if not out:
        return []
    trees: list[dict] = []
    cur: dict = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if cur:
                trees.append(cur)
            cur = {"path": line[len("worktree "):], "locked": False,
                   "detached": False, "branch": None}
        elif line.startswith("branch "):
            cur["branch"] = line[len("branch "):].replace("refs/heads/", "", 1)
        elif line == "detached":
            cur["detached"] = True
        elif line.startswith("locked"):
            cur["locked"] = True
    if cur:
        trees.append(cur)
    return trees


def upstream_gone(main: str, branch: str) -> bool:
    """True if `branch` tracks a remote ref that no longer exists.

    This is the `[gone]` marker in `git status -sb`. In a squash-on-merge
    workflow with delete-source-branch, this is the canonical "the MR landed,
    the remote branch was cleaned up" signal — and the ONLY reliable one,
    since a squash collapses the branch's commits into one whose patch-id
    won't match (so cherry alone reports such a branch as unmerged forever).
    Requires an upstream to have been configured; an unpushed local-only
    branch has none and returns False.
    """
    # %(upstream:track) is exactly what `git status -sb` renders as [gone];
    # it stays correct even after the remote-tracking ref is pruned, whereas
    # <branch>@{upstream} just errors once that ref is gone.
    track = git(main, "for-each-ref", "--format=%(upstream:track)",
                f"refs/heads/{branch}")
    return track == "[gone]"


def merged_into_main(main: str, branch: str) -> bool:
    """True if `branch` is safe to reap as already-landed work.

    Two independent signals, either sufficient:
      * every commit has a patch-id equivalent in origin/main
        (`git cherry`) — covers fast-forward / rebase / non-squash merges;
      * its tracked upstream is gone — covers squash-on-merge, where cherry
        can't see the equivalence.
    Any failure to resolve returns False so we never remove on uncertainty.
    No fetch — a stale origin/main only ever errs toward keeping a worktree.
    """
    if upstream_gone(main, branch):
        return True
    if not git(main, "rev-parse", "--verify", "-q", "origin/main"):
        return False
    out = git(main, "cherry", "origin/main", branch)
    if out is None:
        return False
    return not any(ln.startswith("+") for ln in out.splitlines())


def fresh_heartbeat_under(common: str, path: str) -> bool:
    """True if a live session's cwd sits inside `path` (don't reap it)."""
    reg = Path(common) / "claude-sessions"
    if not reg.is_dir():
        return False
    now = time.time()
    rp = os.path.realpath(path)
    for f in reg.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if now - float(data.get("last_seen", 0)) > STALE_SECONDS:
            continue
        cwd = os.path.realpath(data.get("cwd", ""))
        if cwd == rp or cwd.startswith(rp + os.sep):
            return True
    return False


# Gitignored files git would silently delete on `worktree remove` — losing
# these is unrecoverable, so their presence vetoes a reap. Regenerable caches
# (node_modules, __pycache__, dist, …) are deliberately NOT listed: a worktree
# whose only ignored content matches none of these is still safe to reap.
SENSITIVE_IGNORED = (
    ".env", ".env.*", "*.tfstate", "*.tfstate.*", ".terraform",
    "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_dsa",
    "id_ecdsa", "id_ed25519", "credentials", "*.secret",
)


def has_sensitive_ignored(path: str) -> bool:
    """True if the worktree holds gitignored files worth protecting.

    `git status --porcelain --ignored` prefixes ignored entries with '!! ';
    directories come through as a single 'dir/' entry. We match each entry's
    basename against SENSITIVE_IGNORED so an ignored .env / *.tfstate / key
    blocks the reap, while a node_modules-only worktree does not.
    """
    import fnmatch
    out = git(path, "status", "--porcelain", "--ignored")
    if not out:
        return False
    for line in out.splitlines():
        if not line.startswith("!! "):
            continue
        base = os.path.basename(line[3:].rstrip("/"))
        if any(fnmatch.fnmatch(base, pat) for pat in SENSITIVE_IGNORED):
            return True
    return False


def sweep(common: str) -> None:
    """Remove linked worktrees that are safe to reap: clean, merged into
    origin/main, unlocked, not detached, holding no live session, and not the
    dir we're running from. Conservative — any doubt and we leave it."""
    main = os.path.dirname(common)  # git-common-dir is always <main>/.git
    trees = worktrees(main)
    if len(trees) < 2:
        return
    self_cwd = os.path.realpath(os.getcwd())
    for wt in trees[1:]:  # skip [0] = main checkout
        path, branch = wt["path"], wt["branch"]
        if wt["locked"] or wt["detached"] or not branch:
            continue
        rp = os.path.realpath(path)
        if self_cwd == rp or self_cwd.startswith(rp + os.sep):
            continue
        if git(path, "status", "--porcelain"):  # dirty / untracked → keep
            continue
        if has_sensitive_ignored(path):  # gitignored .env / tfstate / key → keep
            continue
        if fresh_heartbeat_under(common, path):
            continue
        if not merged_into_main(main, branch):
            continue
        if git(main, "worktree", "remove", path) is None:
            continue  # remove refused (raced / untracked files); leave it
        # `-d` (not `-D`): delete the branch only when git is certain it is
        # merged. For squash-merges git can't see the equivalence, so it
        # refuses and the branch ref lingers harmlessly — never force-delete
        # commits that might be unique (e.g. an abandoned, never-merged branch
        # whose remote was deleted, which also shows up as [gone]).
        git(main, "branch", "-d", branch)
        sys.stderr.write(f"worktree-guard: reaped merged worktree {path} ({branch})\n")


def handle_stop(ev: dict) -> int:
    my_sid = sid(ev)
    idx = Path(f"/tmp/claude-wg-{my_sid}.idx")
    commons: set[str] = set()
    if idx.exists():
        for line in idx.read_text().splitlines():
            # idx line = <common>/claude-sessions/<sid>.json
            commons.add(str(Path(line).parents[1]))
            try:
                Path(line).unlink()
            except (OSError, FileNotFoundError):
                pass
        try:
            idx.unlink()
        except OSError:
            pass
    # Garbage-collect stale worktrees only when the session truly ends, not on
    # every turn-end Stop (which would race a still-running idle session).
    if ev.get("hook_event_name") == "SessionEnd":
        for common in commons:
            try:
                sweep(common)
            except Exception as e:
                sys.stderr.write(f"worktree-guard sweep: {e}\n")
    return 0


HANDLERS = {
    "check": handle_check,
    "touch": handle_touch,
    "bash-guard": handle_bash_guard,
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
