# 0008 — cd-stage launcher

**Status:** approved

## Purpose

Stage-broker work (spec 0002) has run in cd-tools (`cd-tools +tools/stage-broker`), so it queues behind small claude-docker fixes, and the broker's remaining work (moving its state out of the code tree, autostart, the live reaper check, per-project stacks such as CT) is now its own stream. A dedicated cd-stage box takes it. The broker itself keeps running in WSL: a box has no Docker, so the box is where broker code changes, not where the broker runs.

## Requirements

- REQ-1: `cd-stage` SHALL launch a box whose working directory and mailbox key come from `tools/stage-broker` (`tools.stage-broker`), with `tools/claude-shared` mounted second, forwarding `--claude-auth --gh` and no other flag; `claude-docker/` stays read-only in it.
- REQ-2: `cd-stage` SHALL refuse to launch when given `--stage`, naming why.
- REQ-3: `cd-tools`' header and `launchers/README.md` SHALL say that stage-broker work routes to cd-stage, that claude-docker changes stay in cd-tools, and that both boxes share the one claude-shared checkout, so commits go by path, never `git add -A`.

## Scenarios

### Scenario: Launch
- **Given** the owner runs `cd-stage`
- **When** the box starts
- **Then** its working directory is `/workspaces/stage-broker`, its mailbox key is `tools.stage-broker`, and `/workspaces/claude-shared/claude-docker` is read-only

### Scenario: No self-staging
- **Given** the owner runs `cd-stage --stage ct`
- **When** the launcher starts
- **Then** it exits non-zero before any container starts, saying a box that can edit the broker must not run a stack through it

### Scenario: Routing
- **Given** a stage-broker request arrives in cd-tools
- **When** the session reads the cd-tools header or the launchers README
- **Then** it is pointed to cd-stage

## Decisions

- Shared claude-shared checkout, not the second clone the parked OPEN item proposed: cd-tools/cd-kits already share kits this way, and a second clone means a host step and two trees to keep in sync. claude-shared is mounted for spec/plan 0002 and OPEN.md.
- No `--tools`: changes to `claude-docker/` (`lib/stage.sh`, `run.sh --stage`) stay in cd-tools, so two boxes never edit the launcher tooling at once.
- Refuses `--stage`: the box can write broker code and, until the state split lands, stack definitions and approvals; running a stack from the same box would let it approve its own stack.
- Broker state stays in the tree for now (owner decision, 2026-11-28): approvals, `stacks/*` (stage.json, stage env, overlays), `broker.json` and run snapshots sit inside `tools/stage-broker`, against spec 0002's "host-side config, never in the workspace". This is no wider than today's `cd-tools +tools/stage-broker`. Moving it to a host dir outside the dev root is the box's first job, before any other stage work (OPEN item). Broker code stays writable by design: the box exists to change it, and the owner restarting `watch` is the checkpoint.
- `--gh`: claude-shared pushes to github.com/lujvari from the box, as from cd-tools.
- Not in the `cd-up` fleet: stage work is on-demand.

## Out of scope

- The broker state split and autostart (OPEN items, broker-side work in the box).
- Linking `~/bin/cd-stage` (host).
