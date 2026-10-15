## ADDED Requirements

### Requirement: SonarCloud credential opt-in

`run.sh` SHALL forward `SONAR_TOKEN` and `SONAR_HOST_URL` into the container only when the user passes `--sonar`, each only when non-empty. `SONAR_TOKEN` SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_SONAR_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host. `SONAR_HOST_URL` is not a secret and SHALL have no `op read` path. There SHALL be no built-in default reference, no bind mount, no CLI-login fallback, and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `sonar` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `SONAR_TOKEN` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Host env vars are forwarded

- **GIVEN** `SONAR_TOKEN=faketoken` and `SONAR_HOST_URL=https://sonarcloud.io` are exported on the host
- **WHEN** the user runs `claude-docker --sonar ~/repo`
- **THEN** both variables are set inside the container with the host values
- **AND** `CLAUDE_DOCKER_FLAGS` contains `sonar`

#### Scenario: Token is read from 1Password when unset on the host

- **GIVEN** `SONAR_TOKEN` is not set on the host
- **AND** `CLAUDE_DOCKER_SONAR_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --sonar ~/repo`
- **THEN** `SONAR_TOKEN` inside the container is non-empty

#### Scenario: No flag, no token

- **GIVEN** `SONAR_TOKEN` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--sonar`
- **THEN** neither `SONAR_TOKEN` nor `SONAR_HOST_URL` is set inside the container

#### Scenario: Host URL alone does not satisfy the flag

- **GIVEN** only `SONAR_HOST_URL` is set on the host and `CLAUDE_DOCKER_SONAR_OP_REF` is unset
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --sonar ~/repo`
- **THEN** `run.sh` names `--sonar` on stderr and exits non-zero without starting a container

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--sonar` and `CLAUDE_DOCKER_SONAR_OP_REF`
