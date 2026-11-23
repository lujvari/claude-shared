## Why

`laslo/architecture` is a new LikeC4 model of MEP, Brain and family-board. Its
`CLAUDE.md` says the session that changes an integration, data store, MCP
connection or deployment in one of those repos updates the model in the same
session. The `cd-mep`, `cd-brain` and `cd-board` boxes mount only their own
repo, so they can't see the model, let alone update it.

## What Changes

- **`cd-mep`, `cd-brain` and `cd-board` mount `laslo/architecture`** as a
  second workspace at `/workspaces/architecture`, read-write (read-only under
  `--ro`, like every workspace). They follow `cd-tools`, `cd-asr` and
  `cd-inat`: the project's `cd_workspace` comes first and each path is kept in
  a named variable, so the test-database helpers in `cd-mep` and `cd-brain`
  use the project path by name, not whatever `$ws` last held.
- **The project stays first.** `run.sh` derives the box's working directory,
  its agent-bus mailbox key and its uv venv key from the first workspace, and
  `--continue` resumes by working directory, so all of these stay the
  project's own (`/workspaces/brain` and `laslo.brain`, and so on).
- **A missing checkout stops the launch**, as `cd_workspace` does for every
  workspace (`cd-tools` with `laslo/kits` today): it names the path rather
  than mounting the wrong tree.
- **Docs**: the launchers README's multi-workspace paragraph names these
  launchers and the shared-tree caveat below.

Accepted by the owner (2026-11-23), not solved here:

- **One shared working tree.** `cd-up` opens `mep` and `brain` together, so
  two or three boxes share the model's working tree, index and branch. Per
  the main README's "Concurrent Claude sessions on one checkout", a model edit
  is committed by path (`git add <files>`), never `git add -A` / `commit -a`.
- **A shared writable tree between boxes.** Any of the three boxes, `cd-board`
  included, can write files there that a session in another box might load
  (a `.claude/skills` entry, say). The owner accepted this for three personal
  repos.

Handed over, not in this repo:

- **The rule doesn't load by itself.** Claude Code reads `CLAUDE.md` from an
  extra workspace only when `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` is
  set, and nothing sets it; setting it would widen the cross-box path above.
  So each project's own `CLAUDE.md` gets a one-line pointer to the model's
  rule. Those three repos aren't mounted here; the pointer request goes back
  to cd-dev with the hand-off.

Out of scope:

- Other launchers. Only the three repos the model covers need it.
- Pushing the model from a box: that depends on `laslo/architecture`'s remote
  and the `--gh` token's repo scope, checked on the host (tasks 4.3).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `launchers`: the three personal service launchers mount the architecture
  model beside their project.

## Impact

- **Code**: `claude-docker/launchers/cd-mep`, `cd-brain`, `cd-board`.
- **Docs**: `claude-docker/launchers/README.md`.
- **Specs**: delta to `launchers`.
- The launchers are symlinks into this checkout, so the change is live on the
  next launch; nothing to install.
- The basename `architecture` is now taken in these boxes: a `+PATH` naming a
  different tree called `architecture` fails `run.sh`'s collision check.
