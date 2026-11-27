# 0005 — cd-kits launcher

**Status:** done

## Purpose

Kit-content work (skills and rules in laslo/kits) lands on cd-tools, whose box also carries the launcher and claude-docker work, so the two queue behind each other. A dedicated cd-kits box takes pure kit work. cd-tools keeps kits mounted because agent-bus and the hooks span both repos.

## Requirements

- REQ-1: `cd-kits` SHALL launch a box with `laslo/kits` as its only and primary workspace (mailbox key `laslo.kits`), forwarding `--claude-auth --gh` and nothing else.
- REQ-2: `cd-tools`' header and `launchers/README.md` SHALL say that pure kit work routes to cd-kits, that cd-tools keeps kits for work spanning both repos, and that both boxes share the one kits checkout, so commits go by path, never `git add -A`.
- REQ-3: `cd-up` SHALL include cd-kits in its fleet, in the `q1` window.

## Scenarios

### Scenario: Launch
- **Given** the owner runs `cd-kits`
- **When** the box starts
- **Then** its working directory is `/workspaces/kits`, it can push to GitHub, and no other tree is mounted

### Scenario: After a reboot
- **Given** no box running
- **When** the owner runs `cd-up`
- **Then** cd-kits opens as a tab in the `cd-q1` window with the others

## Decisions

- No claude-shared mount: `run.sh --ro` is all-or-nothing, so it could only be read-write, and pure kit work does not need it. `cd-kits +tools/claude-shared` adds it for a one-off.
- In the fleet: with agent-bus auto-wake off (kits 0017), an open box's status-line mail count is how the owner sees that kit mail has arrived.

## Out of scope

- Linking `~/bin/cd-kits` (host).
