## ADDED Requirements

### Requirement: Session work is recorded at session end

On `SessionEnd`, the `session-worklog` hook SHALL append one NDJSON record per repository the session is known to have touched (the repo stamped at `SessionStart` and the repo containing the end-of-session working directory) to `<repo>/.git/claude-sessions/worklog.ndjson`. Each record SHALL carry the session id, the branch, the end `HEAD`, the count of uncommitted tracked changes, the count of untracked files, and the ahead/behind counts versus the tracked upstream (null when no upstream is configured). When a `SessionStart` stamp exists for the same repo, the record SHALL also carry the start `HEAD`, the number of commits made during the session, and a one-line `git diff --stat` summary of those commits.

The log directory is the same shared `<repo>/.git/claude-sessions/` that the session registry uses, so it is visible across every container that mounts the repo and is never committed (it lives inside `.git`). When the working directory is not inside a git repository, the hook SHALL write no record and SHALL exit without error.

#### Scenario: A session that committed and left changes is recorded

- **GIVEN** a repo in which `session-worklog start` was run at `SessionStart`
- **AND** the session then made one commit, left one tracked file modified, and created one untracked file
- **WHEN** `session-worklog stop` runs on `SessionEnd`
- **THEN** a new line is appended to `<repo>/.git/claude-sessions/worklog.ndjson`
- **AND** that record reports `commits_this_session: 1`, `dirty_tracked: 1`, and `untracked: 1`, plus the branch, start and end HEADs, and a `diff --stat` summary line

#### Scenario: Non-repository working directory is a no-op

- **WHEN** `session-worklog stop` runs with a working directory that is not inside any git repository
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

### Requirement: No secret material is logged

The per-session record SHALL describe changes only as file paths and line counts (via `git diff --stat`); it SHALL NOT include file contents or diff hunks. This keeps secret values that may sit in changed files out of the shared, multi-container work log.

#### Scenario: Changed file content is not written to the log

- **GIVEN** a session that modified a file containing a secret value
- **WHEN** `session-worklog stop` records the session
- **THEN** the work-log record contains the file's path and its insertion/deletion counts
- **AND** the work-log record does not contain the file's contents or any diff hunk
