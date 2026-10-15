## ADDED Requirements

### Requirement: Opt-in shared Claude credential

`run.sh` SHALL bind-mount the host file `<config-dir>/.credentials.json` read-write at `/root/.claude/.credentials.json` only when the user passes `--claude-auth`, where `<config-dir>` is the host Claude config directory resolved from `CLAUDE_DOCKER_CONFIG_DIR`. When the flag is set, `run.sh` SHALL add `auth` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and the host file does not exist, `run.sh` SHALL print an error naming the path and telling the user to run `claude` and `/login` on the host, and SHALL exit 1 before `docker run`. Without the flag, the host credential file SHALL NOT be mounted.

#### Scenario: Host and container share one credential

- **GIVEN** `<config-dir>/.credentials.json` exists on the host
- **WHEN** the user runs `claude-docker --claude-auth ~/repo`
- **THEN** `/root/.claude/.credentials.json` inside the container is the host file, mounted read-write
- **AND** `CLAUDE_DOCKER_FLAGS` contains `auth`

#### Scenario: Host re-login reaches the container

- **GIVEN** a container launched with `--claude-auth`
- **WHEN** the user logs in again on the host and the token rotates
- **THEN** the in-container session uses the new token without a 401 or a prompt to run `/login`

#### Scenario: Missing host credential aborts

- **GIVEN** `<config-dir>/.credentials.json` does not exist on the host
- **WHEN** the user runs `claude-docker --claude-auth ~/repo`
- **THEN** `run.sh` prints an error naming the missing path
- **AND** exits 1 without starting a container

#### Scenario: Off by default

- **WHEN** the user runs `claude-docker ~/repo` without `--claude-auth`
- **THEN** the host `.credentials.json` is not mounted into the container

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--claude-auth` and states that a `--yolo` container can then read and write the host Claude credential
