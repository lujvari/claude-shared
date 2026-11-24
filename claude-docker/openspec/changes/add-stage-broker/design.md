## Placement
Broker + lint in `tools/stage-broker/` (dev root; precedent `tools/slack-outbox`: gates, audit,
queue protocol, pending/approve/deny, stdlib only). `claude-docker` gets only `--stage` and the
registry write (`launchers/_lib.sh`, `run.sh`). Agent skill in `laslo/kits`. Per-project file
set and E2E command live in the broker's host-side config for that project, never in the workspace.

## Request handling
Requests are files in `<bus>/<key>/.stage/req/<id>.json`, replies in `.stage/res/<id>.json`.
Identity = the mailbox key the file was found under; project comes from the registry. Broker
refuses symlinks, hardlinks, non-regular files, files over 64 KB, duplicate ids and symlinked
queue dirs, handles 10 requests per box per pass, and is single-threaded (no per-key lock
needed). Args validated (`service` matches `[a-z0-9_-]+` and exists
in the resolved config). Refusals are JSON `{refused, reason, service?}`.

## Registry
`stage_broker.py register KEY PROJECT` (called by the launcher, host side) writes
`<bus>/.stage/registry/<key>.json` = `{"project", "at"}` and creates the box's queue dirs
`<bus>/<key>/.stage/{req,res}`; `unregister KEY` removes it at box exit. The project name maps
to host config `stacks/<project>/stage.json`, so the registry never carries paths. `register`
refuses an existing entry unless `--force`; the launcher must check for a live box with that key
first (two boxes sharing a key share a mailbox, which the broker cannot tell apart). The registry
dir is outside the box's `/bus` mount (spike 0.2). Residual: a box can swap `.stage/req|res` for
a symlink between the broker's check and its write; the broker re-checks before every write and
never follows links on the request file, so the window is a race, not a standing hole.

## Up flow
1. Resolve the file set from host config; run `docker compose config --format json` on the
   workspace files with the stage env only (no vault token) -> normalized JSON.
2. Hash it; compare with the approval. Mismatch: hold, store the diff, reply `held`.
3. Lint (also run at approve time). Fail: refuse.
4. The snapshot is the approved resolved config itself (absolute paths, so later edits cannot
   change it). Rewrite it to a run config in Python (ports -> `127.0.0.1:0`, `container_name`,
   project, network and volume names dropped; no YAML tags needed); `docker compose -p stage-<project>-<key> up -d --wait`.
5. Reply with the `docker compose port` map.
Build contexts resolve into the workspace (realpath-checked), so the box's code is what runs.

## Logs and secrets
Stacks only ever hold stage-env values. `logs` returns raw output; scrubbing is not relied on.

## Box to stack
`host.docker.internal:<mapped port>`. Unproven for dynamic loopback ports: spike 0.1.
