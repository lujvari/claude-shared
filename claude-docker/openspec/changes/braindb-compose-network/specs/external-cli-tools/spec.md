## MODIFIED Requirements

### Requirement: Brain test database opt-in

`run.sh` SHALL forward `BRAIN_TEST_DSN` into the container only when the user passes `--braindb`. The value SHALL come from the host environment when set there; otherwise `run.sh` SHALL resolve `CLAUDE_DOCKER_BRAINDB_OP_REF` with `op read` on the host. `CLAUDE_DOCKER_BRAINDB_OP_REF` SHALL default to `op://claude-docker/laslo-brain-test-postgres/dsn` when unset, and an explicitly empty value SHALL disable the 1Password path. There SHALL be no bind mount and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `braindb` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `BRAIN_TEST_DSN` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

When the flag is set, `run.sh` SHALL run the container on the single docker network the running `brain-test-postgres` container is attached to, and SHALL rewrite the host and port of `BRAIN_TEST_DSN` to `brain-test-postgres:5432` inside the container, keeping its scheme, credentials, database and query string. `run.sh` SHALL abort before `docker run`, naming `--braindb` on stderr and without printing the DSN, when `brain-test-postgres` is not running, when it is attached to no network or to more than one, when `BRAIN_TEST_DSN` is set but is not a `scheme://` URL, or when a network is already chosen via `--host-net` or `CLAUDE_DOCKER_NETWORK`.

#### Scenario: Default reference is used with no configuration

- **GIVEN** `BRAIN_TEST_DSN` and `CLAUDE_DOCKER_BRAINDB_OP_REF` are both unset on the host
- **AND** the host `op` can read `op://claude-docker/laslo-brain-test-postgres/dsn`
- **AND** `brain-test-postgres` is running
- **WHEN** the user runs `claude-docker --braindb ~/repo`
- **THEN** `BRAIN_TEST_DSN` inside the container is non-empty
- **AND** `CLAUDE_DOCKER_FLAGS` contains `braindb`

#### Scenario: Box reaches the database over its compose network

- **GIVEN** `brain-test-postgres` is running on network `brain-test_default`
- **AND** the host DSN is `postgresql://u:p@127.0.0.1:47401/laslo_brain_test`
- **WHEN** the user runs `claude-docker --braindb ~/repo`
- **THEN** the container is attached to `brain-test_default`
- **AND** `BRAIN_TEST_DSN` inside the container is `postgresql://u:p@brain-test-postgres:5432/laslo_brain_test`

#### Scenario: Database container not running

- **GIVEN** `brain-test-postgres` is stopped or does not exist
- **WHEN** the user runs `claude-docker --braindb ~/repo`
- **THEN** `run.sh` names `--braindb` and `brain-test-postgres` on stderr and exits non-zero without starting a container

#### Scenario: Conflicting network choice

- **WHEN** the user runs `claude-docker --braindb --host-net ~/repo`
- **THEN** `run.sh` names both flags on stderr and exits non-zero without starting a container

#### Scenario: Empty reference switches the 1Password path off

- **GIVEN** `BRAIN_TEST_DSN` is unset and `CLAUDE_DOCKER_BRAINDB_OP_REF=""` on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --braindb ~/repo`
- **THEN** `run.sh` issues no `op read` for this flag, names `--braindb` on stderr, and exits non-zero without starting a container

#### Scenario: Both database flags on one launch

- **WHEN** the user runs `claude-docker --mepdb --braindb ~/repo`
- **THEN** `POSTGRES_TEST_URL` and `BRAIN_TEST_DSN` are both set inside the container, each from its own reference

#### Scenario: No flag, no DSN

- **GIVEN** `BRAIN_TEST_DSN` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--braindb`
- **THEN** `BRAIN_TEST_DSN` is not set inside the container
