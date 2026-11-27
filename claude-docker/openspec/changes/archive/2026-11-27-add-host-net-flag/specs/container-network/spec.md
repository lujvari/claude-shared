## ADDED Requirements

### Requirement: Selectable container network

`run.sh` SHALL pass `--network <name>` to `docker run` when a network is selected, and SHALL pass no `--network` argument otherwise. The network SHALL be taken from `CLAUDE_DOCKER_NETWORK`, and `--host-net` SHALL set it to `host`. When a network is selected, `run.sh` SHALL add `net:<name>` to `CLAUDE_DOCKER_FLAGS`. Selecting a network SHALL NOT change the filesystem mounts, dropped capabilities or `no-new-privileges` setting.

#### Scenario: --host-net uses the host network namespace

- **WHEN** the user runs `claude-docker --host-net ~/repo`
- **THEN** the container is started with `--network host`
- **AND** `CLAUDE_DOCKER_FLAGS` contains `net:host`

#### Scenario: Environment selects a named network

- **GIVEN** `CLAUDE_DOCKER_NETWORK=mynet` is set on the host
- **WHEN** the user runs `claude-docker ~/repo`
- **THEN** the container is started with `--network mynet`
- **AND** `CLAUDE_DOCKER_FLAGS` contains `net:mynet`

#### Scenario: Default bridge

- **GIVEN** `CLAUDE_DOCKER_NETWORK` is unset or empty
- **WHEN** the user runs `claude-docker ~/repo` without `--host-net`
- **THEN** no `--network` argument is passed to `docker run`

#### Scenario: Help lists the flag and the trade-off

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--host-net` and `CLAUDE_DOCKER_NETWORK`
- **AND** states that the container loses network isolation
