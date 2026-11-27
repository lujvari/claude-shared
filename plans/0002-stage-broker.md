# Plan 0002 — Stage broker

**Spec:** specs/0002-stage-broker.md
**Effort:** big
**Status:** draft

## Approach

Trust model: the box is untrusted and edits anything in its workspace. Runtime definition (compose files: ports, mounts, privileges, env, networks, images) is owner-approved by hash; drift holds `up` with a diff. Code under test (source, Dockerfiles, build contexts) is box-owned and runs in containers with no host mounts, socket or vault credentials.

Placement: broker and lint live in the dev-root `tools/stage-broker/` (stdlib Python plus `docker compose config --format json`; sibling of `tools/slack-outbox`: gates, audit, pending/approve/deny). `claude-docker` gets only the `--stage` flag and the registry write. The agent skill goes in `laslo/kits`. Per-project file set and E2E command live in host-side config (`stacks/<project>/stage.json`), never in the workspace.

Requests: files in `<bus>/<key>/.stage/req/<id>.json`, replies in `.stage/res/<id>.json`. Identity is the mailbox key; project comes from the registry. Broker refuses symlinks, hardlinks, non-regular files, files over 64 KB, duplicate ids, symlinked queue dirs; 10 requests per box per pass; single-threaded. `service` matches `[a-z0-9_-]+` and exists in the resolved config. Refusals are JSON `{refused, reason, service?}`.

Registry: `stage_broker.py register KEY PROJECT` (launcher, host side) writes `<bus>/.stage/registry/<key>.json` and creates the queue dirs; `unregister KEY` removes it. Refuses an existing entry unless `--force`; the launcher checks for a live box with that key first. The registry dir is outside the box's `/bus` mount. Launcher side (`claude-docker/lib/stage.sh`): KEY is the bus key; a live box is a held flock on `~/.cache/claude-docker/locks/stage-<key>.lock` (kept for the launcher's life) or a running container labelled `claude-docker.bus-key=<key>`; with neither, an existing entry is a crash leftover and is torn down before registering. Registration happens just before `docker run`; `teardown KEY` runs from the EXIT trap (also on HUP). Residual: a symlink swap race on queue dirs; the broker re-checks before every write and never follows links on the request file.

Up flow: resolve file set from host config, run `docker compose config --format json` with stage env only; hash and compare with the approval (mismatch: hold, store diff, reply `held`); lint (also at approve time); rewrite the approved resolved config into a run config (ports to `127.0.0.1:0`, `container_name`, project, network and volume names dropped); `docker compose -p stage-<project>-<key> up -d --wait`; reply with the port map. Build contexts resolve into the workspace (realpath-checked).

Lint rejects: unremappable host ports, privileged, host network/pid/ipc/uts/userns, cap_add, devices, security_opt, sysctls, volumes_from, `network_mode: container:`/`service:`, external networks/volumes, docker.sock, bind or volume-driver mounts outside the project dir, secrets/configs `file:`, interpolation of anything but the stage env file.

Secrets: stacks hold only stage-env values from a host-side file (dummy or scoped); `op run` is not used. Box-visible values (REQ-8): `stage.json` lists names in `box_env`; `up` and `url` replies carry `env: {name: value}` for those names that the stage env defines, nothing else. `logs` returns raw output; scrubbing is not relied on. Box to stack route: `host.docker.internal:<mapped port>`.

Built so far (tasks 0.x-2.2): spikes confirmed box-to-stack loopback routing, registry unreachable from the box, and compose `!reset`/`!override` merging; broker core (`lint.py`, `approval.py`, `stack.py`, `audit.py`, `stage_broker.py` CLI, `service.py` six verbs) and `test_e2e.py` are done with 72 tests green on Windows and WSL. Remaining: launcher integration and the myEntryPoint pilot.

## Changes

- `tools/stage-broker/` (dev root) — broker core, `teardown KEY`, reaper and caps done. Reaper (`watch` every `reap_interval`, or `reap`): a registry entry whose box has no running container labelled `claude-docker.bus-key=<key>` and is older than `grace_seconds` is torn down; a stack older than `ttl_hours` since its last `up` is removed; a `stage-*` stack no entry names is removed; a pass where `docker ps` fails reaps nothing. `up` is refused once `max_stacks` stage stacks exist (one stack per box by construction); every service gets `deploy.resources.limits` at the lower of its own and `cpus`/`memory`. Defaults 4 stacks, 8 h, 60 s, 2 CPUs, 2g per service; override in `<home>/broker.json`.
- `claude-docker/run.sh`, `claude-docker/launchers/_lib.sh` — `--stage <project>`: refuse if a live box has the key, register, set `STAGE_QUEUE=/bus/.stage` in the box, teardown on exit.
- `tools/stage-broker/stacks/myentrypoint/stage.json` and stage env file (host side) — pilot file set `docker-compose.yml` plus `docker-compose.e2e.yml`, never `override.yml` (docker.sock, C:/dev mounts), plus a host-owned overlay `stacks/myentrypoint/stage.yml`: the app images' `op run` entrypoint cannot work with a dummy vault token, so the overlay sets `/usr/bin/env` as entrypoint, drops the op-ref `.env` mounts, takes every value from `stage.env`, gives brain a named volume in place of `./.data`, and turns its scheduler off. No LLM key, so brain is slash-only and the spec-0042 multi-intent E2E is deselected on this stack.
- `laslo/kits` — skill: up, E2E harness, report, down, asking for approval on `held`.

## Dependencies

Docker Compose v5.6+ on the host. Stage env file must supply dummy `OP_SERVICE_ACCOUNT_TOKEN` and `POSTGRES_PASSWORD` (compose requires both). The ad-hoc test-postgres pre-start in `cd-mep` stays until the pilot passes.

## Acceptance Checklist

- [ ] REQ-5: `--stage <project>` registers the box, refuses a live duplicate key, sets `STAGE_QUEUE`, and tears the stack down on exit; kill the box and confirm the stack is gone.
- [ ] REQ-5: TTL reaper, crash cleanup and caps work; a stack count over the cap is refused (test).
- [x] REQ-2, REQ-6: Host config for the pilot file set lints clean with dummy env; `env` inside a stack shows no vault or broker variables. — verified: `approve myentrypoint` passed lint; the run config gives api/brain/ui/postgres/redis only stage-env and literal values (no `OP_SERVICE_ACCOUNT_TOKEN`), each capped at 2 CPUs / 2g; `up` from a registered box was healthy and spec-0042 E2E (hint, no-match) passed against the remapped ports.
- [x] REQ-1, REQ-3: Skill in `laslo/kits` covers up, E2E, report, down and how to ask for approval on `held`; an unknown verb is refused and a compose edit yields `held` with a diff. — verified: kits 0016 `stage-stack`, run against the real broker (unknown verb exit 2, unapproved `up` held with diff, approved `up` ok).
- [ ] REQ-4, REQ-7: Autonomous run on a small change in the pilot project with a second box on the same port; both stacks run on distinct ports, E2E is green, the report matches the owner's manual check, and `verify` reports the audit chain intact.
- [x] REQ-8: `up`/`url` replies carry exactly the `box_env` values (test).
- [ ] Tests pass
