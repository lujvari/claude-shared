## ADDED Requirements

### Requirement: myEntryPoint test database opt-in

`run.sh` SHALL forward `POSTGRES_TEST_URL` into the container only when the user passes `--mepdb`. The value SHALL come from the host environment when set there; otherwise `run.sh` SHALL resolve `CLAUDE_DOCKER_MEPDB_OP_REF` with `op read` on the host. `CLAUDE_DOCKER_MEPDB_OP_REF` SHALL default to `op://claude-docker/brain-test-postgres/dsn` when unset, and an explicitly empty value SHALL disable the 1Password path. There SHALL be no bind mount and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `mepdb` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `POSTGRES_TEST_URL` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Default reference is used with no configuration

- **GIVEN** `POSTGRES_TEST_URL` and `CLAUDE_DOCKER_MEPDB_OP_REF` are both unset on the host
- **AND** the host `op` can read `op://claude-docker/brain-test-postgres/dsn`
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** `POSTGRES_TEST_URL` inside the container is non-empty
- **AND** `CLAUDE_DOCKER_FLAGS` contains `mepdb`

#### Scenario: Host env var wins over the default reference

- **GIVEN** `POSTGRES_TEST_URL=<dsn>` is exported on the host
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** `POSTGRES_TEST_URL` inside the container equals the host value
- **AND** no `op read` is issued for this flag

#### Scenario: Empty reference switches the 1Password path off

- **GIVEN** `POSTGRES_TEST_URL` is unset and `CLAUDE_DOCKER_MEPDB_OP_REF=""` on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** `run.sh` issues no `op read` for this flag, names `--mepdb` on stderr, and exits non-zero without starting a container

#### Scenario: No flag, no DSN

- **GIVEN** `POSTGRES_TEST_URL` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--mepdb`
- **THEN** `POSTGRES_TEST_URL` is not set inside the container

#### Scenario: Help lists the flag and its default

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--mepdb` and `op://claude-docker/brain-test-postgres/dsn`
