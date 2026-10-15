> Retroactive record: implemented in 210c557 on 2026-06-23 (narrowed the same day in b95c7fa), written 2026-10-15 to close spec drift.

## Why

A broad workspace mount, such as all of the dev root, also sweeps in the
claude-docker launcher directory (under `tools/`). A `--yolo` container could
then rewrite the host launcher or the hooks it ships, and the host would run
the modified code on the next start. That is a sandbox escape through the
filesystem. The launcher directory has to be read-only from inside unless the
user explicitly wants to edit it.

## What Changes

- **Read-only overlay of the launcher's own directory by default**: when a
  workspace argument strictly contains the launcher directory (`SELF_DIR`),
  `run.sh` adds a read-only bind mount of that directory over its path inside
  the workspace. 210c557 first overlaid the workspace's whole top-level
  `tools/` subdirectory; b95c7fa narrowed it to the launcher's own directory,
  so everything else under `tools/` stays writable.
- **Skipped when redundant**: the overlay is not added under `--ro` (already
  read-only) or when the workspace is the launcher directory itself (a
  deliberate mount of it stays writable).
- **Add `--tools`** to skip the overlay and keep the launcher directory
  writable, for editing the launcher from inside a container.
- **Help and README** document `--tools`; the README threat model lists the
  overlay.

Out of scope (deliberately):

- Protecting other host-executed paths under a broad mount.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `multi-workspace-mounts`: adds the default read-only overlay of the launcher
  directory and the `--tools` opt-out.

## Impact

- **Code**: `claude-docker/run.sh`.
- **Docs**: `claude-docker/README.md` (flag row, threat model).
- **Specs**: delta to `multi-workspace-mounts`.
- **Behaviour change**: a container with a broad mount can no longer write the
  launcher directory unless `--tools` is passed.
