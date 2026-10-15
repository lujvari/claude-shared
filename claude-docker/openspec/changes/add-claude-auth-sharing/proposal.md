> Retroactive record: implemented in ff89abb on 2026-06-21, written 2026-10-15 to close spec drift.

## Why

A container keeps its own copy of the Claude OAuth credential. When the user
logs in again on the host, the account token rotates and the container's copy
goes stale, so the in-container session fails with a 401 / "run /login" until
the user logs in again inside the box. Doing that every time is friction. It
goes away if host and container share one credential file, so that a refresh
on either side is seen by both.

## What Changes

- **Add `--claude-auth`**: bind-mounts `<config-dir>/.credentials.json`
  read-write over `/root/.claude/.credentials.json`. `<config-dir>` is the
  host Claude config directory (`CLAUDE_DOCKER_CONFIG_DIR`, same source as the
  other host-config mounts).
- **Fail fast**: if the file does not exist on the host, `run.sh` prints
  "--claude-auth set but <path> not found; run 'claude' and /login on the host
  first" and exits 1 without starting a container.
- **Statusline**: the flag adds `auth` to `CLAUDE_DOCKER_FLAGS`.
- **Off by default.** Help states the security trade-off: a `--yolo`
  container can read and write the user's real Claude credential, so a
  prompt-injected workspace file could exfiltrate it.
- **Help and README** document the flag.

Out of scope (deliberately):

- Copying or syncing the credential; the mount is live, not a snapshot.
- Any change to the other host-config mounts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `host-config-parity`: adds an opt-in, read-write mount of the host Claude
  credential file.

## Impact

- **Code**: `claude-docker/run.sh`.
- **Docs**: `claude-docker/README.md`.
- **Specs**: delta to `host-config-parity`.
- **Security**: with the flag set, the container holds a live, writable copy
  of the host's Claude OAuth credential. Without it, nothing changes.
