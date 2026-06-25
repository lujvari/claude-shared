## 1. Hook

- [x] 1.1 Create `claude-docker/hooks/session-worklog.py` — stdlib-only Python 3, argv dispatch (`start`/`touch`/`stop`) mirroring `worktree-guard.py`'s `event()` / `sid()` / `git()` / `repo_paths()` shape.
- [x] 1.2 Per-session index `/tmp/claude-worklog-<sid>.json` mapping `{repo_top: {common, start_head}}`; `_remember()` adds a repo on first sighting with its current HEAD as the baseline, idempotent thereafter.
- [x] 1.3 `start`: remember the cwd repo (no-op when cwd is not in a repo). `touch` (PostToolUse): remember the edited file's repo — this is the primary discovery path so sessions run from a non-repo parent still record the subrepos they edit.
- [x] 1.4 `stop`: for every repo in the index (plus the end-cwd repo when it is a repo), append one NDJSON record to `<repo>/.git/claude-sessions/worklog.ndjson` with sid, branch, end HEAD, uncommitted/untracked counts, ahead/behind; add start HEAD + `commits_this_session` + `diff --stat` summary when a baseline HEAD was captured.
- [x] 1.5 On `SessionEnd`, warn to stderr per repo when its tree is dirty or commits are unpushed; stay silent on a clean, pushed tree.
- [x] 1.6 `diff --stat` only (paths + counts, never content); wrap everything so any error is swallowed to stderr and the hook exits zero; remove the index on `SessionEnd`.

## 2. Wiring

- [x] 2.1 `examples/settings.docker.json`: add a `SessionStart` block running `session-worklog.py start`, guarded by `[ -f /root/.claude/hooks/session-worklog.py ]`.
- [x] 2.2 `examples/settings.docker.json`: add a second `PostToolUse` Edit/Write hook entry running `session-worklog.py touch`, alongside `worktree-guard.py touch`.
- [x] 2.3 `examples/settings.docker.json`: add a second `SessionEnd` hook entry running `session-worklog.py stop`, alongside `worktree-guard.py stop`. Do NOT wire it on `Stop` (avoid a record per turn).
- [x] 2.4 Confirm the new hook ships into the container via the existing `run.sh:638` mount of `hooks/` at `/root/.claude/hooks:ro` (no Dockerfile/run.sh change needed).

## 3. Docs

- [x] 3.1 Add/maintain the "Session work log (session-worklog)" subsection in `README.md`: edit-location discovery (PostToolUse), the log+warn-only bright line, SessionStart/PostToolUse/SessionEnd wiring, and the deliberate omissions (no Stop, no fsck, Bash-only changes not seen).
- [x] 3.2 Add `__pycache__/` to `.gitignore`.

## 4. Validation

- [x] 4.1 `python3 -m py_compile hooks/session-worklog.py` passes.
- [x] 4.2 `python3 -c "import json; json.load(open('examples/settings.docker.json'))"` passes (valid JSON after edit).
- [x] 4.3 Throwaway-repo smoke: from a NON-repo parent, a `touch` on a file inside a subrepo records that subrepo; after a commit + dirty file + untracked file, `stop` appends a record with `commits_this_session: 1`, `dirty_tracked: 1`, `untracked: 1` and warns to stderr; index cleaned up on SessionEnd; a session touching no repo no-ops.
- [x] 4.4 `openspec validate add-session-worklog --strict` exits 0.
- [ ] 4.5 In-container check (deferred to next image build + seed sync): a real session run from `/workspaces/dev` that edits a subrepo and leaves it dirty prints the warning and writes `worklog.ndjson` in that subrepo; a clean session is silent.
