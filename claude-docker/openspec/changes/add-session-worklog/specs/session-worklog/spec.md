## ADDED Requirements

### Requirement: Session work is recorded at session end

The `session-worklog` hook SHALL discover the repositories a session touched by **edit location**: on each `PostToolUse` for an Edit/Write tool, a `touch` invocation SHALL record the repository containing the edited file into a per-session index. The repository containing the working directory at `SessionStart` and at `SessionEnd` SHALL also be folded in when each is itself a repository.

On `SessionEnd`, for every repository in that set, the hook SHALL append one NDJSON record to `<repo>/.git/claude-sessions/worklog.ndjson`. Each record SHALL carry the session id, the branch, the count of uncommitted tracked changes, the count of untracked files, and the ahead/behind counts versus the tracked upstream (null when no upstream is configured) — exactly the state `report` reads, gathered in a single `git status` call. It SHALL NOT carry a per-session history (start/end HEADs, commit counts, diffstat): nothing reads it, and each field cost a git call on the session's way out.

The log directory is the same shared `<repo>/.git/claude-sessions/` that the session registry uses, so it is visible across every container that mounts the repo and is never committed (it lives inside `.git`). When neither the working directory nor any edited file is inside a git repository, the hook SHALL write no record and SHALL exit without error.

#### Scenario: A session that committed and left changes is recorded

- **GIVEN** a session that edited a file in a repo (so the repo was recorded via `touch`)
- **AND** the session left one tracked file modified and created one untracked file
- **WHEN** `session-worklog stop` runs on `SessionEnd`
- **THEN** a new line is appended to `<repo>/.git/claude-sessions/worklog.ndjson`
- **AND** that record reports `dirty_tracked: 1` and `untracked: 1`, plus the branch

#### Scenario: A subrepo edited from a non-repo parent is recorded

- **GIVEN** a session whose working directory is a multi-repo parent that is not itself a git repository (e.g. `/workspaces/dev`)
- **AND** the session edits a file inside one of its subrepositories
- **WHEN** `session-worklog stop` runs on `SessionEnd`
- **THEN** a record for that subrepository is appended to its `.git/claude-sessions/worklog.ndjson` (the non-repo parent does not suppress discovery)

#### Scenario: A session that touches no repository is a no-op

- **WHEN** `session-worklog stop` runs for a session that edited no file in any repository and whose start/end working directories are not inside any repository
- **THEN** no log file is created and the hook exits zero without error

### Requirement: A dirty or unpushed exit is surfaced

On `SessionEnd`, when a touched repository has uncommitted changes (tracked or untracked) or commits not present on its upstream, the hook SHALL write a human-readable warning to stderr naming the repository, the branch, and what is outstanding. When the tree is clean and no commits are unpushed, the hook SHALL emit no warning.

#### Scenario: Dirty tree triggers a warning

- **GIVEN** a session ending in a repo with uncommitted or untracked changes
- **WHEN** `session-worklog stop` runs on `SessionEnd`
- **THEN** a warning is written to stderr naming the repo and branch and the count of uncommitted/untracked files

#### Scenario: Clean, pushed tree is silent

- **GIVEN** a session ending in a repo whose tree is clean and whose HEAD is not ahead of its upstream
- **WHEN** `session-worklog stop` runs on `SessionEnd`
- **THEN** no warning is written to stderr

### Requirement: The work log never mutates repository state

The `session-worklog` hook SHALL NOT commit, push, stash, prune, clean, reset, or remove anything in any repository. Its only side effects SHALL be appending to the work-log file under `.git/claude-sessions/`, writing the per-session stamp under `/tmp`, and writing warnings to stderr. Any internal error SHALL be swallowed (logged to stderr) and the hook SHALL exit zero so it can never fail or delay a session.

#### Scenario: A dirty working tree is left untouched

- **GIVEN** a repo with uncommitted changes and unpushed commits
- **WHEN** `session-worklog stop` runs on `SessionEnd`
- **THEN** the working tree, the index, the branch refs, and the commit graph are byte-for-byte unchanged afterwards (only the work-log file and stderr are written)

### Requirement: A deferred warning is surfaced on the next session

Because `SessionEnd` output is never displayed, the warning it computes would otherwise go unseen. The hook SHALL provide a `report` mode that re-surfaces it. When run for a repository (the working-directory repo on `SessionStart`, or the edited file's repo on `PreToolUse`), `report` SHALL read that repository's last `worklog.ndjson` record and, when that record was dirty or had unpushed commits, emit a human-readable warning via the hook `additionalContext` output channel (which is visible on `SessionStart` and `PreToolUse`). It SHALL emit at most once per repository per session. It SHALL NOT run any mutating git command and SHALL NOT re-check live git state (so a warning the user resolved without ending a session MAY surface once). When the event is not scoped to a repository (e.g. the working directory is a non-repo parent and no file is being edited), `report` SHALL emit nothing. `start` SHALL perform the `report` for the working-directory repository itself, so `SessionStart` needs one hook invocation, not two. Because `report` and `touch` run on every Edit/Write, the repository lookup SHALL be cached per directory for the session, so only the first edit in a directory runs git.

#### Scenario: A subrepo edited from a non-repo parent surfaces its prior warning

- **GIVEN** a repository whose last `worklog.ndjson` record was left dirty by an earlier session
- **AND** the current session's working directory is a non-repo parent (e.g. `/workspaces/dev`)
- **WHEN** the session first edits a file inside that repository (PreToolUse `report`)
- **THEN** a warning naming the repository, branch, and outstanding counts is emitted via `additionalContext`
- **AND** a second edit in the same repository in the same session emits nothing (deduped)

#### Scenario: A clean repo surfaces nothing

- **GIVEN** a repository whose last `worklog.ndjson` record was clean (no uncommitted/untracked/unpushed)
- **WHEN** `report` runs for that repository
- **THEN** nothing is emitted

### Requirement: No secret material is logged

The per-session record SHALL describe changes only as counts; it SHALL NOT include file paths, file contents, or diff hunks. This keeps secret values that may sit in changed files out of the shared, multi-container work log.

#### Scenario: Changed file content is not written to the log

- **GIVEN** a session that modified a file containing a secret value
- **WHEN** `session-worklog stop` records the session
- **THEN** the work-log record counts the file as a tracked change
- **AND** the work-log record does not contain the file's path, contents, or any diff hunk
