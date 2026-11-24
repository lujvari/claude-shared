<!-- plan version: v2. v1 assumed the box submits a compose file once; Gate 5 showed the box
     edits compose files, Dockerfiles, env files and stage.json in its rw workspace. Rewritten, not patched. -->
## Why

Boxed agents (`--cap-drop ALL`, `--no-new-privileges`, no Docker socket) cannot bring up the
project's full stack to verify a change, so the owner does the real testing by hand. Mounting
`docker.sock` gives the box host root. Fixed host ports (myEntryPoint uses 47300-47304) also
stop two boxes running a stack at once.

## Trust model

The box is untrusted and can edit everything in its workspace. Two kinds of content:

- **Runtime definition** (compose files: ports, mounts, privileges, env, networks, images):
  owner-approved by hash. A change is held until the owner approves it.
- **Code under test** (app source, Dockerfiles, build contexts): box-owned. It runs in
  containers with no host mounts, no socket, no vault credentials. The accepted risk: box
  code runs in a container on the host daemon.

## What Changes

- `tools/stage-broker/` (host, WSL, stdlib Python + `docker compose config --format json`),
  a sibling of `tools/slack-outbox` (gates, audit, pending/approve/deny).
- Verbs from a box over agent-bus: `up`, `down`, `logs [svc]`, `reset`, `status`, `url`.
- Approval record per project: file set, merged-config hash, lint result, kept in the broker
  dir. Drift = hash mismatch = `up` held with a diff; `stage-broker approve|deny <project>`.
- Lint at approve time (failures cannot be approved): unremappable host port bindings,
  privileged, host network/pid/ipc/uts/userns, cap_add, devices, security_opt, sysctls,
  volumes_from, `network_mode: container:`/`service:`, external networks/volumes, docker.sock,
  bind or volume-driver mounts whose realpath is outside the project dir, secrets/configs
  `file:`, env interpolation of anything but the stage env file.
- Run from a broker-owned snapshot of the approved files. Ports rewritten to ephemeral
  loopback (`!override`), `container_name` stripped (`!reset`), compose project name
  `stage-<project>-<key>`, own network.
- Staging env comes from a host-side stage env file (dummy or scoped values) in the broker
  dir. `op run` is not used; the vault token never reaches a stack.
- Limits: TTL, teardown on box exit, per-box caps on stacks, CPU, RAM.
- `claude-docker`: `--stage` flag, registry write. Skill in `laslo/kits`. Pilot: myEntryPoint
  using `docker-compose.yml` + `docker-compose.e2e.yml` (the existing `override.yml` mounts
  docker.sock and C:/dev and is excluded).

Out of scope: remote staging VM, image scanning, LLM judge, production deploys, other projects.
Known limitation: boxes can reach each other's mapped loopback ports (personal use; revisit for work).
