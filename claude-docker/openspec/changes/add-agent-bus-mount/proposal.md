> Retroactive record: implemented in 2a666b0 on 2026-10-12, written 2026-10-15 to close spec drift.

## Why

Boxed sessions need a way to post messages to the host (and to the host's
Slack broker) and to read host replies. A shared directory mounted into every
box would let one box read another's mail — ASR and Aegon boxes must stay
apart — and would let a compromised session plant mail "from the host" for
its next session. The mailbox has to be per box, with the box's identity
chosen by the host rather than claimed by the box, and with the inbound side
read-only.

## What Changes

- **Per-box mailbox mount, on by default when configured.** When
  `CLAUDE_DOCKER_BUS_DIR` names an existing host directory, `run.sh` derives a
  key from the first workspace: its path relative to the bus dir's parent with
  `/` → `.` (e.g. `laslo/ringrecipe` → `laslo.ringrecipe`), or its basename
  when it is not under that parent. It creates `<bus>/<key>/in` and
  `<bus>/<key>/out`, mounts `<bus>/<key>` at `/bus` read-write and overlays
  `<bus>/<key>/in` at `/bus/in` read-only.
- **Environment**: sets `AGENT_BUS_DIR=/bus`, `AGENT_BUS_SELF=<key>` and
  `SLACK_OUTBOX_QUEUE=/bus/.slack-outbox/queue` (a queue the host Slack broker
  watches).
- **Fail open, with a warning**: an unset `CLAUDE_DOCKER_BUS_DIR` mounts
  nothing, silently, so a wrapper without one behaves exactly as before. A
  set-but-missing directory, or a key that is empty, starts with `.` or holds
  characters outside `A-Za-z0-9._-`, prints a warning and launches without a
  mailbox.
- **Applies under `--ro` and `--ephemeral`**: the bus is not the workspace.
- **Add `--no-bus`** to skip the mailbox for one launch.
- **Launchers** (`launchers/_lib.sh`) default `CLAUDE_DOCKER_BUS_DIR` to
  `<dev-root>/.agent-bus`.
- **Example settings** (`examples/settings.docker.json`) wire the agent-bus
  notice and watch hooks.
- **README**: `--no-bus` row in the hardening-flags table. **Help**: `--no-bus`
  entry and `CLAUDE_DOCKER_BUS_DIR` under Environment.

Out of scope (deliberately):

- A statusline tag; the bus is not added to `CLAUDE_DOCKER_FLAGS`.
- The agent-side skill and the host broker, which live outside this repo.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `multi-workspace-mounts`: adds a per-box agent-bus mount derived from the
  first workspace, and the `--no-bus` opt-out.

## Impact

- **Code**: `claude-docker/run.sh`, `claude-docker/launchers/_lib.sh`.
- **Config examples**: `claude-docker/examples/settings.docker.json`.
- **Docs**: `claude-docker/README.md` (one row).
- **Specs**: delta to `multi-workspace-mounts`.
- **Behaviour change for launcher users**: launches through `launchers/` now
  get a mailbox by default whenever `<dev-root>/.agent-bus` exists. Direct
  `run.sh` use without `CLAUDE_DOCKER_BUS_DIR` is unchanged.
