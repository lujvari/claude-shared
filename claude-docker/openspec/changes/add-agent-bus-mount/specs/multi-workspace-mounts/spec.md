## ADDED Requirements

### Requirement: Per-box agent-bus mailbox

When `CLAUDE_DOCKER_BUS_DIR` names an existing host directory and `--no-bus` is not passed, `run.sh` SHALL give the container exactly one mailbox, keyed by the first workspace argument. The key SHALL be that workspace's path relative to the parent of the bus directory with every `/` replaced by `.`, or its basename when it is not under that parent. `run.sh` SHALL create `<bus>/<key>/in` and `<bus>/<key>/out`, bind-mount `<bus>/<key>` at `/bus` read-write, and bind-mount `<bus>/<key>/in` at `/bus/in` read-only. It SHALL set `AGENT_BUS_DIR=/bus`, `AGENT_BUS_SELF=<key>` and `SLACK_OUTBOX_QUEUE=/bus/.slack-outbox/queue` in the container. No other box's mailbox and no parent of `<bus>/<key>` SHALL be mounted. The mailbox SHALL be mounted under `--ro` and `--ephemeral` as well.

When `CLAUDE_DOCKER_BUS_DIR` is unset or empty, `run.sh` SHALL mount no mailbox and print nothing. When it is set but the directory does not exist, or the key is empty, starts with `.`, or contains a character outside `A-Za-z0-9._-`, `run.sh` SHALL print a warning and launch without a mailbox.

#### Scenario: Box gets only its own mailbox

- **GIVEN** `CLAUDE_DOCKER_BUS_DIR=/dev-root/.agent-bus` exists on the host
- **WHEN** the user runs `claude-docker /dev-root/laslo/ringrecipe`
- **THEN** `/bus` inside the container is `/dev-root/.agent-bus/laslo.ringrecipe` on the host
- **AND** `echo $AGENT_BUS_SELF` inside the container prints `laslo.ringrecipe`
- **AND** no other directory under `/dev-root/.agent-bus` is visible inside the container

#### Scenario: Inbox is read-only from inside

- **GIVEN** a container launched with a mailbox
- **WHEN** a process inside writes a file under `/bus/in`
- **THEN** the write fails with a read-only filesystem error
- **AND** a write under `/bus/out` succeeds

#### Scenario: --no-bus skips the mailbox

- **GIVEN** `CLAUDE_DOCKER_BUS_DIR` names an existing host directory
- **WHEN** the user runs `claude-docker --no-bus ~/repo`
- **THEN** nothing is mounted at `/bus`
- **AND** `AGENT_BUS_DIR`, `AGENT_BUS_SELF` and `SLACK_OUTBOX_QUEUE` are not set by `run.sh`

#### Scenario: Missing bus directory warns and continues

- **GIVEN** `CLAUDE_DOCKER_BUS_DIR` names a path that does not exist
- **WHEN** the user runs `claude-docker ~/repo`
- **THEN** `run.sh` prints a warning that it is launching without a mailbox
- **AND** the container starts with nothing mounted at `/bus`

#### Scenario: Mailbox survives read-only mode

- **GIVEN** `CLAUDE_DOCKER_BUS_DIR` names an existing host directory
- **WHEN** the user runs `claude-docker --ro ~/repo`
- **THEN** the workspace is read-only and `/bus/out` is writable

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--no-bus` and `CLAUDE_DOCKER_BUS_DIR`
