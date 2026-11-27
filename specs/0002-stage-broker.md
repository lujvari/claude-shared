# 0002 — Stage broker

**Status:** draft

## Purpose

Boxed agents are locked down (no extra privileges, no container-engine socket), so they cannot bring up the project's full stack to verify a change, and the owner does that testing by hand. Handing a box the engine socket would give it host root, and fixed host ports stop two boxes running a stack at once. A host-side broker lets a box start, inspect and stop its own project's stack under owner-approved limits.

## Requirements

- REQ-1: A box SHALL only be able to request `up`, `down`, `logs`, `reset`, `status` and `url`, and only for its own project.
- REQ-2: A stack definition with any lint violation (privileged mode, host namespaces, added capabilities, devices, the container-engine socket, host-path or out-of-project mounts, external networks or volumes, unremappable ports) SHALL NOT be approved or run.
- REQ-3: A change to the merged runtime configuration SHALL hold `up` until the owner approves it; a change to application source or image build files SHALL NOT.
- REQ-4: Two stacks wanting the same host port or container name SHALL both start with distinct mappings.
- REQ-5: A stack SHALL be removed when its box exits, crashes or its time limit expires, and a box SHALL NOT exceed its stack cap.
- REQ-6: A stack SHALL receive only the host-side stage environment values, and the vault service-account token SHALL NOT reach it.
- REQ-7: Every request, hold, approval and refusal SHALL be appended to a hash-chained audit log.

## Scenarios

### Scenario: Unknown verb
- **Given** a registered box
- **When** the box requests `exec`
- **Then** the request is refused and nothing runs

### Scenario: Bad service
- **Given** a registered box with a running stack
- **When** the box requests `logs` for a service not in its stack
- **Then** the request is refused naming the service

### Scenario: Socket mount
- **Given** a compose service mounting the container-engine socket
- **When** the owner runs `approve`
- **Then** approval is refused with the service named

### Scenario: Compose edited by the box
- **Given** an approved stack definition
- **When** the box adds a volume to a service and requests `up`
- **Then** the reply is `held` with a diff, and no container starts

### Scenario: Source edited
- **Given** an approved stack definition
- **When** the box edits application source only and requests `up`
- **Then** the stack builds and starts

### Scenario: Two boxes, same port
- **Given** two boxes whose stacks publish port 8080
- **When** both request `up`
- **Then** both run and `url` returns different host ports

### Scenario: Box killed
- **Given** a box with a running stack
- **When** the box container is killed
- **Then** its stack is gone within the reaper interval

### Scenario: Stack cap
- **Given** a box already at its stack cap
- **When** it requests another stack
- **Then** the request is refused

### Scenario: Env check
- **Given** a running stack
- **When** the stack runs `env`
- **Then** no variable from the host vault or the broker's own environment is present

### Scenario: Tamper
- **Given** an audit log with records
- **When** an audit record is edited
- **Then** `verify` reports the chain broken

## Constraints

- The box is untrusted and can edit everything in its workspace; only the runtime definition is owner-approved, and application code under test runs in containers with no host mounts and no vault credentials.
- Out of scope: remote staging host, image scanning, LLM judge, production deploys, projects other than the pilot.
- Known limitation: boxes can reach each other's mapped loopback ports (accepted for personal use; revisit for work).

## Open Questions

- Does a box reach a stack's dynamic loopback port from inside the box? Default: yes, verified by spike (route stands).
