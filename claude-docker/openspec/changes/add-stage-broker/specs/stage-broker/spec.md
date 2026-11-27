## ADDED Requirements

### Requirement: R1 Fixed verbs only
A box SHALL only be able to request `up`, `down`, `logs`, `reset`, `status`, `url` for its own project.

#### Scenario: Unknown verb
- **WHEN** a box requests `exec`
- **THEN** the request is refused and nothing runs

#### Scenario: Bad service
- **WHEN** a box requests `logs` for a service not in its stack
- **THEN** the request is refused naming the service

### Requirement: R2 Unsafe definitions cannot be approved
A definition with any lint violation (privileged, host namespaces, cap_add, devices, docker.sock, host-path or out-of-project mounts, external networks/volumes, unremappable ports) SHALL NOT be approved or run.

#### Scenario: Socket mount
- **GIVEN** a compose service mounting `/var/run/docker.sock`
- **WHEN** the owner runs `approve`
- **THEN** approval is refused with the service named

### Requirement: R3 Runtime changes need approval
A change to the merged runtime config SHALL hold `up` until the owner approves; changes to app source or Dockerfiles SHALL NOT.

#### Scenario: Compose edited by the box
- **WHEN** the box adds a volume to a service and requests `up`
- **THEN** the reply is `held` with a diff, and no container starts

#### Scenario: Source edited
- **WHEN** the box edits app source only and requests `up`
- **THEN** the stack builds and starts

### Requirement: R4 Port and name clashes do not block
Two stacks wanting the same host port or container name SHALL both start with distinct mappings.

#### Scenario: Two boxes, 8080
- **GIVEN** two boxes whose stacks publish 8080
- **WHEN** both request `up`
- **THEN** both run and `url` returns different host ports

### Requirement: R5 Stacks end with the box
A stack SHALL be removed when its box exits, crashes or its TTL expires, and a box SHALL NOT exceed its stack cap.

#### Scenario: Box killed
- **WHEN** the box container is killed
- **THEN** its stack is gone within the reaper interval

### Requirement: R6 No credentials in a stack
A stack SHALL receive only the host-side stage env values; the vault service-account token SHALL NOT reach it.

#### Scenario: Env check
- **WHEN** a stack runs `env`
- **THEN** no variable from the host vault or the broker's own environment is present

### Requirement: R7 Every action is audited
Every request, hold, approval and refusal SHALL be appended to a hash-chained log.

#### Scenario: Tamper
- **WHEN** an audit record is edited
- **THEN** `verify` reports the chain broken
