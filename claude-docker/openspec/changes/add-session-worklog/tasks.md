## 1. Hook

- [x] 1.1 Create `claude-docker/hooks/session-worklog.py` — stdlib-only Python 3, argv dispatch (`start`/`stop`) mirroring `worktree-guard.py`'s `event()` / `sid()` / `git()` / `repo_paths()` shape.
- [x] 1.2 `start`: stamp `{sid, repo, start_head, start_ts}` to `/tmp/claude-worklog-<sid>.json`; no-op when cwd is not in a repo.
- [x] 1.3 `stop`: for the start-stamp repo and the end-cwd repo, append one NDJSON record per repo to `<repo>/.git/claude-sessions/worklog.ndjson` with sid, branch, end HEAD, uncommitted/untracked counts, ahead/behind; add start HEAD + `commits_this_session` + `diff --stat` summary when a same-repo stamp exists.
- [x] 1.4 On `SessionEnd` only, warn to stderr when the tree is dirty or commits are unpushed; stay silent on a clean, pushed tree.
- [x] 1.5 `diff --stat` only (paths + counts, never content); wrap everything so any error is swallowed to stderr and the hook exits zero; remove the stamp on `SessionEnd`.

## 2. Wiring

- [x] 2.1 `examples/settings.docker.json`: add a `SessionStart` block running `session-worklog.py start`, guarded by `[ -f /root/.claude/hooks/session-worklog.py ]`.
- [x] 2.2 `examples/settings.docker.json`: add a second `SessionEnd` hook entry running `session-worklog.py stop`, alongside the existing `worktree-guard.py stop`. Do NOT wire it on `Stop` (avoid a record per turn).
- [x] 2.3 Confirm the new hook ships into the container via the existing `run.sh:638` mount of `hooks/` at `/root/.claude/hooks:ro` (no Dockerfile/run.sh change needed).

## 3. Docs

- [x] 3.1 Add a "Session work log (session-worklog)" subsection to `README.md` after the worktree-guard section: what it logs, where, the log+warn-only bright line, SessionStart/SessionEnd wiring, and the deliberate omissions (no Stop, no fsck, start/end repos only).
- [x] 3.2 Add `__pycache__/` to `.gitignore`.

## 4. Validation

- [x] 4.1 `python3 -m py_compile hooks/session-worklog.py` passes.
- [x] 4.2 `python3 -c "import json; json.load(open('examples/settings.docker.json'))"` passes (valid JSON after edit).
- [x] 4.3 Throwaway-repo smoke: `start` stamps; `stop` on a repo with one commit + a dirty tracked file + an untracked file appends a record with `commits_this_session: 1`, `dirty_tracked: 1`, `untracked: 1`, and warns to stderr; a clean tree stays silent; a non-repo cwd no-ops; the stamp is cleaned up on SessionEnd.
- [x] 4.4 `openspec validate add-session-worklog --strict` exits 0.
- [ ] 4.5 In-container check (deferred to next image build): a real session ending dirty prints the warning and writes `worklog.ndjson`; a clean session is silent.
