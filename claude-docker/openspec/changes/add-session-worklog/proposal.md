## Why

A session can finish real work and leave it **uncommitted** in the
bind-mounted tree. The work isn't lost — the tree persists across the
`--rm` container — but nothing flags it, so it goes unnoticed across a
`/clear` or a session redirect and surfaces much later as "why didn't
this reach `main`?". Observed failure: a session implemented a complete
feature across an evening, the context was cleared and pointed at other
work before the commit step ran, and the finished edits sat
uncommitted for a day with no signal.

`worktree-guard.py` already tracks a per-session heartbeat registry and,
on `SessionEnd`, reaps only *clean, already-landed* worktrees — it
deliberately leaves a dirty or unmerged worktree alone. That's correct,
but it means a dirty exit is **silent**: the guard keeps the work and
says nothing. There is no record of what a session did and no warning
when it ends with outstanding changes.

The fix is observability, not automation. Auto-committing or
auto-pushing on exit would be worse than the gap it closes — it would
publish half-finished or unwanted work (a backed-out commit, a
debugging spike) without a human in the loop. So the guardrail must
**log and warn only**, never mutate.

## What Changes

- **Add `hooks/session-worklog.py`** — a new hook, kept separate from
  `worktree-guard.py` so logging can never destabilise the stomp-guard.
  Two modes:
  - `start` (SessionStart): stamp `{sid, repo, head, ts}` to
    `/tmp/claude-worklog-<sid>.json` so the end handler can compute the
    session's commit delta.
  - `stop` (SessionEnd): for each repo the session is known to have
    touched, append one NDJSON record to
    `<repo>/.git/claude-sessions/worklog.ndjson` and, on `SessionEnd`,
    warn to stderr when the tree is dirty or commits are unpushed.
- **Wire it in `examples/settings.docker.json`** — `SessionStart` →
  `start`, and add `stop` to the existing `SessionEnd` block alongside
  `worktree-guard.py`. Deliberately NOT on `Stop` (per-turn), so there
  is one record per real session, not one per turn.
- **Document it in README** under a new "Session work log" subsection.

Strictly observational. The hook NEVER commits, pushes, stashes,
prunes, cleans, resets, or removes anything — that bright line is the
whole point.

Out of scope (deliberately):
- Any git mutation on exit (commit / push / stash / prune / clean /
  reset). The hook only reads and reports.
- `git fsck` / dangling-commit scanning. Too slow to run on every
  session end over a 9p bind mount, and that clutter auto-expires;
  uncommitted-tree + unpushed-commits are the high-value, low-cost
  signals.
- Mid-session repo hops. The hook fires only at start and end, so it
  records the start-stamp repo and the end-cwd repo; repos touched only
  in between are not tracked.
- Worktree reaping / old-session cleanup. That already exists in
  `worktree-guard.py` (clean + merged + no-live-heartbeat) and is not
  duplicated here.

## Capabilities

### New Capabilities

- `session-worklog`: per-session, append-only work logging plus a
  dirty/unpushed-exit warning, driven by `SessionStart`/`SessionEnd`
  hooks. Purely observational — reads git state, writes a log line and
  a stderr warning, mutates nothing.

### Modified Capabilities

None. The change adds a new hook and extends the example settings; it
does not alter `worktree-guard.py` or any existing capability's
behaviour.

## Impact

- **Code**: new `claude-docker/hooks/session-worklog.py` (stdlib-only
  Python 3, mirrors `worktree-guard.py`'s argv-dispatch + `git()`
  helper shape). It ships into every container via the existing
  `run.sh:638` mount of `hooks/` at `/root/.claude/hooks:ro`.
- **Config**: `claude-docker/examples/settings.docker.json` gains a
  `SessionStart` block and a second `SessionEnd` hook entry. Users who
  maintain their own `~/.claude/settings.docker.json` seed copy the new
  block over from the example.
- **Docs**: `claude-docker/README.md` gains a "Session work log"
  subsection; `.gitignore` gains `__pycache__/`.
- **No breaking changes.** The example settings guard each hook with
  `[ -f .../session-worklog.py ]`, so an older seed without the hook
  file is a no-op. `worktree-guard.py` is untouched.
- **Dependencies**: none. stdlib Python + `git`, already in the image.
